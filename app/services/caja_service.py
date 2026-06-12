"""Servicio de Caja: apertura, cierre, movimientos de fondos.

Reglas de negocio:
- Solo puede haber una caja abierta por sucursal a la vez.
- Para vender, la caja debe estar abierta.
- El cierre calcula el saldo esperado vs el real (arqueo).
"""

from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from app.models.movimiento_caja import MovimientoCaja


def caja_abierta(db: Session, sucursal_id: int = 1) -> bool:
    """Verifica si hay una caja abierta (sin cerrar) en la sucursal."""
    ultimo = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
    return ultimo is not None and ultimo.tipo != "cierre"


def abrir_caja(
    db: Session,
    monto_inicial: float,
    usuario_id: int,
    sucursal_id: int = 1,
) -> MovimientoCaja:
    """Abre la caja con un monto inicial.

    Raises:
        ValueError: Si ya hay una caja abierta.
    """
    if caja_abierta(db, sucursal_id):
        raise ValueError("Ya hay una caja abierta. Ciérrela primero.")

    movimiento = MovimientoCaja(
        tipo="apertura",
        monto=monto_inicial,
        descripcion="Apertura de caja",
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def cerrar_caja(
    db: Session,
    monto_real: float,
    usuario_id: int,
    sucursal_id: int = 1,
) -> Tuple[MovimientoCaja, float, float]:
    """Cierra la caja con el arqueo.

    Args:
        monto_real: El monto contado físicamente en la caja.

    Returns:
        (movimiento_cierre, saldo_esperado, diferencia)

    Raises:
        ValueError: Si no hay caja abierta.
    """
    if not caja_abierta(db, sucursal_id):
        raise ValueError("No hay caja abierta para cerrar.")

    saldo = obtener_saldo_actual(db, sucursal_id)
    diferencia = monto_real - saldo

    movimiento = MovimientoCaja(
        tipo="cierre",
        monto=monto_real,
        descripcion=f"Cierre de caja. Esperado: ${saldo:,.2f}. Diferencia: ${diferencia:,.2f}",
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento, saldo, diferencia


def registrar_ingreso(
    db: Session,
    monto: float,
    descripcion: str,
    usuario_id: int,
    referencia_tipo: Optional[str] = None,
    referencia_id: Optional[int] = None,
    sucursal_id: int = 1,
) -> MovimientoCaja:
    """Registra un ingreso de dinero (ej: pago de una venta)."""
    movimiento = MovimientoCaja(
        tipo="ingreso",
        monto=monto,
        descripcion=descripcion,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def registrar_egreso(
    db: Session,
    monto: float,
    descripcion: str,
    usuario_id: int,
    referencia_tipo: Optional[str] = None,
    referencia_id: Optional[int] = None,
    sucursal_id: int = 1,
) -> MovimientoCaja:
    """Registra un egreso de dinero (ej: pago a proveedor, retiro)."""
    movimiento = MovimientoCaja(
        tipo="egreso",
        monto=monto,
        descripcion=descripcion,
        referencia_tipo=referencia_tipo,
        referencia_id=referencia_id,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


def obtener_saldo_actual(db: Session, sucursal_id: int = 1) -> float:
    """Calcula el saldo actual sumando todos los movimientos desde
    la última apertura hasta ahora (excluyendo el cierre si existe).

    Fórmula: SUM(ingresos) - SUM(egresos) + apertura_inicial.
    """
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )

    saldo = 0.0
    for m in movimientos:
        if m.tipo == "cierre":
            saldo = 0.0  # Empezar nuevo ciclo
            break
        if m.tipo in ("apertura", "ingreso"):
            saldo += m.monto
        elif m.tipo == "egreso":
            saldo -= m.monto

    return saldo


def obtener_estado_caja(db: Session, sucursal_id: int = 1) -> dict:
    """Devuelve el estado actual de la caja."""
    abierta = caja_abierta(db, sucursal_id)
    saldo = obtener_saldo_actual(db, sucursal_id) if abierta else 0.0

    return {
        "abierta": abierta,
        "saldo_actual": saldo,
    }


def listar_movimientos(
    db: Session,
    sucursal_id: int = 1,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[MovimientoCaja], int]:
    """Lista movimientos de caja con paginación."""
    query = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
    )
    total = query.count()
    movimientos = query.offset((page - 1) * page_size).limit(page_size).all()
    return movimientos, total
