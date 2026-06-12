"""Servicio de Stock: movimientos y consultas de inventario.

Regla de negocio: el stock nunca se modifica directamente.
Siempre se registra un MovimientoStock que actualiza el saldo.
"""

from typing import Optional
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
) -> MovimientoStock:
    """Ajusta el stock de un producto registrando el movimiento.

    Args:
        cantidad: Positivo para entradas, negativo para salidas.
                  El movimiento registra el valor absoluto.
        tipo: 'entrada', 'salida', o 'ajuste'.

    Returns:
        El movimiento de stock creado.

    Raises:
        ValueError: Si no hay stock suficiente para una salida.
    """
    producto = db.query(Producto).filter(Producto.id == producto_id).first()
    if not producto:
        raise ValueError(f"Producto {producto_id} no encontrado")

    stock_anterior = producto.stock_actual
    stock_resultante = stock_anterior + cantidad

    if stock_resultante < 0:
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


def productos_stock_bajo(db: Session, umbral: Optional[float] = None):
    """Productos con stock igual o por debajo de su stock_minimo."""
    from app.config import settings

    umbral = umbral or settings.LOW_STOCK_THRESHOLD
    return (
        db.query(Producto)
        .filter(
            Producto.activo == True,
            Producto.stock_actual <= Producto.stock_minimo,
            Producto.stock_minimo > 0,
        )
        .order_by(Producto.stock_actual)
        .all()
    )
