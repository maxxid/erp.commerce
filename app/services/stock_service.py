"""Servicio de Stock: movimientos y consultas de inventario.

Regla de negocio: el stock nunca se modifica directamente.
Siempre se registra un MovimientoStock que actualiza el saldo.

A partir de Lotes/FEFO, el stock del producto se mantiene como cache derivado
de la suma de `lotes.cantidad_actual`. Ver `lote_service` para las operaciones
que crean/consumen stock de manera FEFO.
"""

from typing import Optional, List, Tuple
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from app.models.producto import Producto
from app.models.movimiento_stock import MovimientoStock


def ajustar_stock(
    db: Session,
    producto_id: int,
    cantidad: float,
    tipo: str,
    usuario_id: int,
    referencia_tipo: str = "ajuste_manual",
    referencia_id: Optional[int] = None,
    notas: Optional[str] = None,
    permitir_negativo: bool = False,
) -> MovimientoStock:
    """Ajusta el stock directo (sin pasar por lotes). Reservado para migraciones
    y casos donde aún no hay sistema de lotes. En operación normal usar
    `ajustar_stock_por_lote` o `lote_service`.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise ValueError(f"Producto {producto_id} no encontrado")

    stock_anterior = producto.stock_actual
    stock_resultante = stock_anterior + cantidad

    if stock_resultante < 0 and not permitir_negativo:
        raise ValueError(
            f"Stock insuficiente: actual={stock_anterior}, "
            f"intentando descontar={abs(cantidad)}"
        )

    movimiento = MovimientoStock(
        producto_id=producto_id,
        tipo=tipo,
        cantidad=abs(cantidad) if cantidad < 0 else cantidad,
        stock_anterior=stock_anterior,
        stock_resultante=stock_resultante,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        usuario_id=usuario_id,
        notas=notas,
    )
    db.add(movimiento)

    producto.stock_actual = stock_resultante

    db.commit()
    db.refresh(movimiento)

    return movimiento


def ajustar_stock_por_lote(
    db: Session,
    producto_id: int,
    cantidad_delta: float,
    tipo: str,
    usuario_id: int,
    referencia_tipo: str = "ajuste_manual",
    referencia_id: Optional[int] = None,
    notas: Optional[str] = None,
) -> Tuple[MovimientoStock, List[Tuple[int, float]]]:
    """Ajusta stock usando el sistema de lotes (FEFO para salidas).

    - cantidad_delta > 0: crea un nuevo lote 'AJUSTE' con esa cantidad.
    - cantidad_delta < 0: descuenta vía FEFO de los lotes existentes.

    Retorna el MovimientoStock creado y la lista de (lote_id, cantidad) afectada.
    """
    from app.services import lote_service

    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise ValueError(f"Producto {producto_id} no encontrado")

    stock_anterior = producto.stock_actual

    if cantidad_delta > 0:
        consumos = lote_service.ajustar_lote(
            db, producto_id, cantidad_delta, notas=notas
        )
        cantidad_real = cantidad_delta
    else:
        consumos = lote_service.ajustar_lote(
            db, producto_id, cantidad_delta, notas=notas
        )
        cantidad_real = abs(cantidad_delta)

    stock_resultante = producto.stock_actual

    lote_principal = consumos[0][0] if consumos else None
    movimiento = MovimientoStock(
        producto_id=producto_id,
        lote_id=lote_principal,
        tipo=tipo,
        cantidad=cantidad_real,
        stock_anterior=stock_anterior,
        stock_resultante=stock_resultante,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        usuario_id=usuario_id,
        notas=notas,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento, consumos


def obtener_movimientos(
    db: Session,
    producto_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
):
    """Lista movimientos de stock, opcionalmente filtrados por producto."""
    query = db.query(MovimientoStock).order_by(MovimientoStock.created_at.desc())

    if producto_id:
        query = query.filter(MovimientoStock.producto_id == producto_id)

    total = query.count()
    movimientos = query.offset((page - 1) * page_size).limit(page_size).all()

    return movimientos, total


def filtro_bajo(query):
    """Filtra productos bajo stock mínimo.

    Es la única definición de "stock bajo" del sistema: el producto está
    activo, controla stock, tiene mínimo definido (minimo > 0) y su stock ya
    lo alcanzó o lo pasó. El Dashboard, /productos/stock-bajo y el chip de
    Productos usan esta misma regla.

    Con mínimo en 0 no hay aviso: significa "no definí mínimo para este
    producto", no "está al límite".
    """
    return query.filter(
        Producto.activo == True,
        Producto.controla_stock == True,
        Producto.stock_minimo > 0,
        Producto.stock_actual <= Producto.stock_minimo,
    )


def filtro_agotado(query):
    """Productos activos que controlan stock y quedaron en cero o menos."""
    return query.filter(
        Producto.activo == True,
        Producto.controla_stock == True,
        Producto.stock_actual <= 0,
    )


def filtro_reposicion(query):
    """Productos a reponer: bajo mínimo o agotados.

    Es el alcance del endpoint /productos/stock-bajo, más ancho que
    filtro_bajo porque un producto agotado conviene comprarlo aunque nunca
    le hayan puesto mínimo.
    """
    return query.filter(
        Producto.activo == True,
        Producto.controla_stock == True,
        or_(
            Producto.stock_actual <= 0,
            and_(Producto.stock_minimo > 0, Producto.stock_actual <= Producto.stock_minimo),
        ),
    )


def productos_stock_bajo(db: Session) -> List[Producto]:
    """Lista los productos bajo stock mínimo, de lo más bajo a lo más alto."""
    return filtro_bajo(db.query(Producto)).order_by(Producto.stock_actual).all()
