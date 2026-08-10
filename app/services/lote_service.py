"""Servicio de Lotes: CRUD, FEFO, alertas y resumen.

Reglas de negocio:
- El stock real de un producto es la suma de `cantidad_actual` de sus lotes activos.
- FEFO (First Expired, First Out): al descontar, se elige el lote con menor
  `fecha_vencimiento` (NULLs last) y, como desempate, menor `created_at`.
- El campo `cantidad_actual` del producto se mantiene como cache para no romper
  los lugares que ya lo leen; se actualiza en cada cambio de lote.
"""

from typing import Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.lote import Lote
from app.models.producto import Producto


def _recalcular_stock_producto(db: Session, producto_id: int) -> float:
    """Recalcula y persiste producto.stock_actual como suma de lotes activos."""
    total = (
        db.query(func.coalesce(func.sum(Lote.cantidad_actual), 0.0))
        .filter(Lote.producto_id == producto_id, Lote.activo == True)
        .scalar()
    )
    total = float(total or 0)
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if producto:
        producto.stock_actual = total
    return total


def listar_lotes(
    db: Session,
    producto_id: Optional[int] = None,
    solo_activos: bool = True,
    solo_con_stock: bool = False,
    page: int = 1,
    page_size: int = 100,
) -> Tuple[List[Lote], int]:
    """Lista lotes con filtros y paginación. Ordena por vencimiento ASC (NULLs last)."""
    query = db.query(Lote)
    if producto_id:
        query = query.filter(Lote.producto_id == producto_id)
    if solo_activos:
        query = query.filter(Lote.activo == True)
    if solo_con_stock:
        query = query.filter(Lote.cantidad_actual > 0)

    total = query.count()
    lotes = (
        query.order_by(Lote.fecha_vencimiento.asc().nulls_last(), Lote.created_at.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return lotes, total


def obtener_lote(db: Session, lote_id: int) -> Optional[Lote]:
    return db.query(Lote).filter(Lote.id == lote_id).first()


def crear_lote(
    db: Session,
    producto_id: int,
    codigo_lote: Optional[str] = None,
    fecha_vencimiento: Optional[datetime] = None,
    fecha_fabricacion: Optional[datetime] = None,
    cantidad: float = 0,
    costo: Optional[float] = None,
    notas: Optional[str] = None,
    compra_id: Optional[int] = None,
    compra_item_id: Optional[int] = None,
) -> Lote:
    """Crea un lote manualmente (casos edge: mermas, ajustes, productos sin compra)."""
    lote = Lote(
        producto_id=producto_id,
        codigo_lote=codigo_lote,
        fecha_vencimiento=fecha_vencimiento,
        fecha_fabricacion=fecha_fabricacion,
        cantidad_inicial=cantidad,
        cantidad_actual=cantidad,
        costo=costo,
        notas=notas,
        activo=True,
        compra_id=compra_id,
        compra_item_id=compra_item_id,
    )
    db.add(lote)
    db.flush()
    _recalcular_stock_producto(db, producto_id)
    db.commit()
    db.refresh(lote)
    return lote


def actualizar_lote(db: Session, lote_id: int, data: dict) -> Lote:
    """Edita metadatos del lote. No se puede cambiar cantidad_actual desde acá."""
    lote = obtener_lote(db, lote_id)
    if not lote:
        raise ValueError(f"Lote {lote_id} no encontrado")

    campos_editables = [
        "codigo_lote", "fecha_fabricacion", "fecha_vencimiento",
        "costo", "activo", "notas",
    ]
    for campo in campos_editables:
        if campo in data and data[campo] is not None:
            setattr(lote, campo, data[campo])

    db.commit()
    db.refresh(lote)
    return lote


def desactivar_lote(db: Session, lote_id: int) -> Lote:
    """Soft delete del lote: no se borra, se marca inactivo. Recalcula stock del producto."""
    lote = obtener_lote(db, lote_id)
    if not lote:
        raise ValueError(f"Lote {lote_id} no encontrado")
    if lote.cantidad_actual > 0:
        raise ValueError(
            f"No se puede desactivar un lote con stock ({lote.cantidad_actual}). "
            "Ajustá el stock primero."
        )
    lote.activo = False
    db.commit()
    db.refresh(lote)
    return lote


def lotes_por_vencer(db: Session, dias: int = 30) -> List[Lote]:
    """Lotes activos con stock > 0 cuya fecha de vencimiento está dentro de `dias` días."""
    limite = datetime.now(timezone.utc) + timedelta(days=dias)
    return (
        db.query(Lote)
        .filter(
            Lote.activo == True,
            Lote.cantidad_actual > 0,
            Lote.fecha_vencimiento.isnot(None),
            Lote.fecha_vencimiento <= limite,
        )
        .order_by(Lote.fecha_vencimiento.asc())
        .all()
    )


def lotes_vencidos(db: Session) -> List[Lote]:
    """Lotes activos con stock > 0 ya vencidos."""
    ahora = datetime.now(timezone.utc)
    return (
        db.query(Lote)
        .filter(
            Lote.activo == True,
            Lote.cantidad_actual > 0,
            Lote.fecha_vencimiento.isnot(None),
            Lote.fecha_vencimiento < ahora,
        )
        .order_by(Lote.fecha_vencimiento.asc())
        .all()
    )


def resumen_producto(db: Session, producto_id: int) -> dict:
    """Resumen de stock por producto: total, lotes activos, alertas."""
    ahora = datetime.now(timezone.utc)
    limite_30 = ahora + timedelta(days=30)

    lotes = (
        db.query(Lote)
        .filter(Lote.producto_id == producto_id, Lote.activo == True)
        .order_by(Lote.fecha_vencimiento.asc().nulls_last())
        .all()
    )
    activos_con_stock = [l for l in lotes if l.cantidad_actual > 0]
    proximo_vto = None
    for l in lotes:
        if l.cantidad_actual > 0 and l.fecha_vencimiento:
            proximo_vto = l.fecha_vencimiento
            break

    por_vencer_30 = sum(
        1 for l in activos_con_stock
        if l.fecha_vencimiento and ahora <= l.fecha_vencimiento <= limite_30
    )
    vencidos = sum(
        1 for l in activos_con_stock
        if l.fecha_vencimiento and l.fecha_vencimiento < ahora
    )

    return {
        "producto_id": producto_id,
        "stock_actual": sum(l.cantidad_actual for l in activos_con_stock),
        "total_lotes": len(lotes),
        "lotes_activos": len(activos_con_stock),
        "proximo_vencimiento": proximo_vto,
        "lotes_por_vencer_30d": por_vencer_30,
        "lotes_vencidos": vencidos,
    }


def descontar_fefo(
    db: Session,
    producto_id: int,
    cantidad: float,
) -> List[Tuple[int, float]]:
    """Descuenta stock del producto siguiendo FEFO.

    Returns:
        Lista de tuplas (lote_id, cantidad_descontada) que luego el caller usa
        para registrar VentaItemLote o MovimientoStock.lote_id.

    Raises:
        ValueError: Si no hay stock suficiente.
    """
    if cantidad <= 0:
        raise ValueError("Cantidad debe ser positiva")

    lotes = (
        db.query(Lote)
        .filter(
            Lote.producto_id == producto_id,
            Lote.activo == True,
            Lote.cantidad_actual > 0,
        )
        .order_by(Lote.fecha_vencimiento.asc().nulls_last(), Lote.created_at.asc())
        .all()
    )

    disponible = sum(l.cantidad_actual for l in lotes)
    if disponible < cantidad:
        raise ValueError(
            f"Stock insuficiente en lotes: disponible={disponible}, requerido={cantidad}"
        )

    restante = cantidad
    consumos: List[Tuple[int, float]] = []
    for lote in lotes:
        if restante <= 0:
            break
        if lote.cantidad_actual <= 0:
            continue
        tomar = min(restante, lote.cantidad_actual)
        lote.cantidad_actual -= tomar
        restante -= tomar
        consumos.append((lote.id, tomar))

    if restante > 0:
        raise ValueError("Stock inconsistente: sobraron unidades sin asignar")

    _recalcular_stock_producto(db, producto_id)
    return consumos


def reingresar_en_lote(
    db: Session,
    producto_id: int,
    lote_id: int,
    cantidad: float,
) -> Lote:
    """Re-ingresa stock en un lote específico (usado al anular una venta)."""
    lote = obtener_lote(db, lote_id)
    if not lote:
        raise ValueError(f"Lote {lote_id} no encontrado")
    if lote.producto_id != producto_id:
        raise ValueError("Lote no pertenece al producto")
    lote.cantidad_actual += cantidad
    _recalcular_stock_producto(db, producto_id)
    db.commit()
    db.refresh(lote)
    return lote


def ajustar_lote(
    db: Session,
    producto_id: int,
    cantidad_delta: float,
    notas: Optional[str] = None,
) -> List[Tuple[int, float]]:
    """Ajusta stock manualmente: positivo=entrada, negativo=salida (FEFO)."""
    if cantidad_delta > 0:
        lote = crear_lote(
            db,
            producto_id=producto_id,
            codigo_lote="AJUSTE",
            cantidad=cantidad_delta,
            notas=notas or "Entrada por ajuste manual",
        )
        return [(lote.id, cantidad_delta)]
    elif cantidad_delta < 0:
        return descontar_fefo(db, producto_id, abs(cantidad_delta))
    return []
