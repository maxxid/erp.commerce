"""Servicio de Compras: crear, agregar items, recibir, anular.

Reglas de negocio:
- Una compra empieza en estado "pendiente".
- Al recibir: ingresa stock, actualiza precio_costo del producto.
- Al anular (solo si está pendiente): no revierte stock porque nunca se ingresó.
- Número autoincremental: C-00000001.
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from app.models.compra import Compra, CompraItem
from app.models.producto import Producto
from app.services import stock_service


def generar_numero_compra(db: Session) -> str:
    ultima = db.query(Compra).order_by(Compra.id.desc()).first()
    if ultima:
        try:
            num = int(ultima.numero.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = ultima.id + 1
    else:
        num = 1
    return f"C-{num:08d}"


def crear_compra(
    db: Session,
    usuario_id: int,
    proveedor_id: int,
    sucursal_id: int = 1,
    notas: Optional[str] = None,
) -> Compra:
    numero = generar_numero_compra(db)
    compra = Compra(
        numero=numero,
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
        estado="pendiente",
        notas=notas,
    )
    db.add(compra)
    db.commit()
    db.refresh(compra)
    return compra


def agregar_item(
    db: Session,
    compra: Compra,
    producto_id: int,
    cantidad: float,
    precio_unitario: float,
) -> CompraItem:
    if compra.estado != "pendiente":
        raise ValueError("Solo se pueden modificar compras pendientes")

    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise ValueError(f"Producto {producto_id} no encontrado")

    subtotal = cantidad * precio_unitario
    item = CompraItem(
        compra_id=compra.id,
        producto_id=producto_id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        subtotal=subtotal,
    )
    db.add(item)
    db.flush()
    _recalcular_totales(db, compra)
    # Incrementar stock en tránsito
    producto.stock_transito = (producto.stock_transito or 0) + cantidad
    db.commit()
    db.refresh(item)
    return item


def quitar_item(db: Session, compra: Compra, item_id: int):
    if compra.estado != "pendiente":
        raise ValueError("Solo se pueden modificar compras pendientes")
    item = db.query(CompraItem).filter(CompraItem.id == item_id, CompraItem.compra_id == compra.id).first()
    if not item:
        raise ValueError("Ítem no encontrado en esta compra")
    # Decrementar stock en tránsito
    producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
    if producto:
        producto.stock_transito = max(0, (producto.stock_transito or 0) - item.cantidad)
    db.delete(item)
    db.flush()
    _recalcular_totales(db, compra)
    db.commit()


def recibir_compra(
    db: Session,
    compra: Compra,
    usuario_id: Optional[int] = None,
    cantidades: Optional[dict] = None,
) -> Compra:
    """Recibe la mercadería total o parcialmente: ingresa stock, actualiza costo.

    Args:
        cantidades: Dict opcional {item_id: cantidad_a_recibir}.
                    Si es None, recibe el pendiente completo de cada item.
                    Si se especifica, recibe exactamente esa cantidad (suma a la ya recibida).

    Raises:
        ValueError: Si no está pendiente o cantidad > pendiente recibir.
    """
    if compra.estado != "pendiente":
        raise ValueError("Solo se pueden recibir compras pendientes")

    uid = usuario_id or compra.usuario_id
    todos_recibidos = True
    algun_recibido = False

    for item in compra.items:
        pendiente = item.pendiente_recibir
        if pendiente <= 0:
            continue

        cantidad_recibir = pendiente
        if cantidades and str(item.id) in cantidades:
            qty = float(cantidades[str(item.id)])
            if qty < 0 or qty > pendiente:
                raise ValueError(
                    f"Cantidad inválida para item {item.id}: a recibir={qty}, pendiente={pendiente}"
                )
            cantidad_recibir = qty

        if cantidad_recibir > 0:
            algun_recibido = True

        item.cantidad_recibida = (item.cantidad_recibida or 0) + cantidad_recibir
        item.subtotal = item.cantidad_recibida * item.precio_unitario

        if item.pendiente_recibir > 0:
            todos_recibidos = False

        producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if producto:
            if cantidad_recibir > 0:
                stock_service.ajustar_stock(
                    db, producto_id=item.producto_id, cantidad=cantidad_recibir,
                    tipo="entrada", usuario_id=uid,
                    referencia_tipo="compra", referencia_id=compra.id,
                )
                if item.precio_unitario:
                    producto.precio_costo = item.precio_unitario
            producto.stock_transito = max(0, (producto.stock_transito or 0) - cantidad_recibir)

    if todos_recibidos:
        compra.estado = "recibida"
    elif algun_recibido:
        compra.estado = "parcial"
    _recalcular_totales(db, compra)
    db.commit()
    db.refresh(compra)
    return compra


def anular_compra(db: Session, compra: Compra) -> Compra:
    """Anula una compra pendiente o parcialmente recibida. Revierte stock en tránsito."""
    if compra.estado not in ("pendiente", "parcial"):
        raise ValueError("Solo se pueden anular compras pendientes o parcialmente recibidas")
    for item in compra.items:
        pendiente = item.pendiente_recibir
        if pendiente > 0:
            producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
            if producto:
                producto.stock_transito = max(0, (producto.stock_transito or 0) - pendiente)
    compra.estado = "anulada"
    db.commit()
    db.refresh(compra)
    return compra


def listar_compras(
    db: Session,
    estado: Optional[str] = None,
    proveedor_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Compra], int]:
    query = db.query(Compra)
    if estado: query = query.filter(Compra.estado == estado)
    if proveedor_id: query = query.filter(Compra.proveedor_id == proveedor_id)
    total = query.count()
    compras = query.order_by(Compra.fecha.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return compras, total


def obtener_compra(db: Session, compra_id: int) -> Optional[Compra]:
    return db.query(Compra).filter(Compra.id == compra_id).first()


def _recalcular_totales(db: Session, compra: Compra):
    db.flush()
    subtotal = sum(item.subtotal for item in compra.items)
    compra.subtotal = subtotal
    compra.total = subtotal + (compra.iva or 0)
