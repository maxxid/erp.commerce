"""Servicio de Ventas: crear, modificar, confirmar, anular.

Reglas de negocio:
- Una venta empieza en estado "pendiente".
- Se agregan items (productos) con cantidad y precio.
- Al confirmar: descuenta stock, registra ingreso en caja.
- Al anular: revierte stock.
- Si medio_pago es "cta_corriente": actualiza saldo del cliente.
- Número de venta autoincremental: V-00000001, V-00000002...
"""

from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.venta import Venta, VentaItem
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.services import stock_service, caja_service


def generar_numero(db: Session, prefijo: str = "V") -> str:
    """Genera un número único autoincremental."""
    ultima = (
        db.query(Venta)
        .order_by(Venta.id.desc())
        .first()
    )
    if ultima:
        # Extraer el número de la última venta
        try:
            num = int(ultima.numero.split("-")[-1]) + 1
        except (ValueError, IndexError):
            num = ultima.id + 1
    else:
        num = 1
    return f"{prefijo}-{num:08d}"


def crear_venta(
    db: Session,
    usuario_id: int,
    cliente_id: Optional[int] = None,
    sucursal_id: int = 1,
    notas: Optional[str] = None,
) -> Venta:
    """Crea una venta vacía en estado pendiente."""
    numero = generar_numero(db)
    venta = Venta(
        numero=numero,
        cliente_id=cliente_id,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
        estado="pendiente",
        notas=notas,
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)
    return venta


def agregar_item(
    db: Session,
    venta: Venta,
    producto_id: int,
    cantidad: float,
    precio_unitario: Optional[float] = None,
) -> VentaItem:
    """Agrega un producto a la venta.

    Si no se especifica precio_unitario, usa el precio_venta del producto.

    Raises:
        ValueError: Si la venta no está pendiente o no hay stock.
    """
    if venta.estado != "pendiente":
        raise ValueError("Solo se pueden modificar ventas pendientes")

    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise ValueError(f"Producto {producto_id} no encontrado")

    if precio_unitario is None:
        precio_unitario = producto.precio_venta or producto.precio_referencia or 0

    subtotal = cantidad * precio_unitario

    item = VentaItem(
        venta_id=venta.id,
        producto_id=producto_id,
        cantidad=cantidad,
        precio_unitario=precio_unitario,
        precio_costo=producto.precio_costo,
        subtotal=subtotal,
    )
    db.add(item)

    # Recalcular totales de la venta
    _recalcular_totales(db, venta)

    db.commit()
    db.refresh(item)
    return item


def quitar_item(db: Session, venta: Venta, item_id: int):
    """Quita un ítem de la venta pendiente."""
    if venta.estado != "pendiente":
        raise ValueError("Solo se pueden modificar ventas pendientes")

    item = (
        db.query(VentaItem)
        .filter(VentaItem.id == item_id, VentaItem.venta_id == venta.id)
        .first()
    )
    if not item:
        raise ValueError("Ítem no encontrado en esta venta")

    db.delete(item)
    _recalcular_totales(db, venta)
    db.commit()


def confirmar_venta(
    db: Session,
    venta: Venta,
    medio_pago: str = "efectivo",
    descuento: float = 0.0,
    usuario_id: Optional[int] = None,
) -> Venta:
    """Confirma una venta pendiente.

    1. Verifica stock para cada ítem (no puede haber ventas parciales)
    2. Descuenta stock y genera MovimientoStock por cada ítem
    3. Aplica descuento
    4. Registra ingreso en caja si la caja está abierta
    5. Si es cta_corriente, actualiza saldo del cliente
    6. Cambia estado a "confirmada"

    Raises:
        ValueError: Si no hay stock, la caja no está abierta, o excede límite crédito.
    """
    if venta.estado != "pendiente":
        raise ValueError("La venta ya fue procesada")

    # Verificar stock
    for item in venta.items:
        producto = db.query(Producto).filter(Producto.id == item.producto_id).first()
        if not producto:
            raise ValueError(f"Producto {item.producto_id} no encontrado")
        if producto.stock_actual < item.cantidad:
            raise ValueError(
                f"Stock insuficiente para '{producto.nombre}': "
                f"disponible={producto.stock_actual}, requerido={item.cantidad}"
            )

    # Verificar caja abierta
    if not caja_service.caja_abierta(db, venta.sucursal_id):
        raise ValueError("La caja no está abierta. Ábrala para poder vender.")

    # Verificar límite de crédito si es cta_corriente
    if medio_pago == "cta_corriente" and venta.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first()
        if cliente:
            nuevo_saldo = cliente.saldo_cta_corriente + venta.subtotal - descuento
            if cliente.limite_credito > 0 and nuevo_saldo > cliente.limite_credito:
                raise ValueError(
                    f"Excede límite de crédito de {cliente.nombre}: "
                    f"límite=${cliente.limite_credito:,.2f}, "
                    f"adeudaría=${nuevo_saldo:,.2f}"
                )

    uid = usuario_id or venta.usuario_id

    # Descontar stock
    for item in venta.items:
        stock_service.ajustar_stock(
            db,
            producto_id=item.producto_id,
            cantidad=-item.cantidad,
            tipo="salida",
            usuario_id=uid,
            referencia_tipo="venta",
            referencia_id=venta.id,
        )

    # Aplicar descuento y actualizar total
    venta.descuento = descuento
    venta.total = venta.subtotal - descuento
    venta.medio_pago = medio_pago
    venta.estado = "confirmada"

    # Cta corriente
    if medio_pago == "cta_corriente" and venta.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first()
        if cliente:
            cliente.saldo_cta_corriente += venta.total

    # Registrar ingreso en caja (solo si no es cta_corriente, porque la plata
    # no entra físicamente en ese caso)
    if medio_pago != "cta_corriente":
        caja_service.registrar_ingreso(
            db,
            monto=venta.total,
            descripcion=f"Venta {venta.numero}",
            usuario_id=uid,
            referencia_tipo="venta",
            referencia_id=venta.id,
            sucursal_id=venta.sucursal_id,
            medio_pago=medio_pago,
        )

    db.commit()
    db.refresh(venta)
    return venta


def anular_venta(
    db: Session,
    venta: Venta,
    usuario_id: Optional[int] = None,
) -> Venta:
    """Anula una venta confirmada, revirtiendo stock y movimientos.

    Raises:
        ValueError: Si la venta no está confirmada.
    """
    if venta.estado != "confirmada":
        raise ValueError("Solo se pueden anular ventas confirmadas")

    uid = usuario_id or venta.usuario_id

    # Revertir stock
    for item in venta.items:
        stock_service.ajustar_stock(
            db,
            producto_id=item.producto_id,
            cantidad=item.cantidad,
            tipo="entrada",
            usuario_id=uid,
            referencia_tipo="venta_anulada",
            referencia_id=venta.id,
        )

    # Revertir cta corriente
    if venta.medio_pago == "cta_corriente" and venta.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first()
        if cliente:
            cliente.saldo_cta_corriente -= venta.total

    # Registrar egreso en caja por devolución
    if venta.medio_pago != "cta_corriente":
        caja_service.registrar_egreso(
            db,
            monto=venta.total,
            descripcion=f"Anulación venta {venta.numero}",
            usuario_id=uid,
            referencia_tipo="venta_anulada",
            referencia_id=venta.id,
            sucursal_id=venta.sucursal_id,
        )

    venta.estado = "anulada"
    db.commit()
    db.refresh(venta)
    return venta


def listar_ventas(
    db: Session,
    estado: Optional[str] = None,
    cliente_id: Optional[int] = None,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Venta], int]:
    """Lista ventas con filtros y paginación."""
    query = db.query(Venta)

    if estado:
        query = query.filter(Venta.estado == estado)
    if cliente_id:
        query = query.filter(Venta.cliente_id == cliente_id)

    total = query.count()
    ventas = (
        query.order_by(Venta.fecha.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ventas, total


def obtener_venta(db: Session, venta_id: int) -> Optional[Venta]:
    """Obtiene una venta con sus items."""
    return db.query(Venta).filter(Venta.id == venta_id).first()


def _recalcular_totales(db: Session, venta: Venta):
    """Recalcula subtotal y total sumando los items de la venta.

    Usa db.flush() si es necesario para que los items nuevos sean visibles
    en la relación. Luego suma desde los objetos en memoria.
    """
    db.flush()  # Persistir items nuevos sin hacer commit
    subtotal = sum(item.subtotal for item in venta.items)
    venta.subtotal = subtotal
    venta.total = subtotal - (venta.descuento or 0)
