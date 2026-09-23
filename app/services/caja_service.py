"""Servicio de Caja: apertura, cierre por método, cierre total.

Reglas de negocio:
- Solo puede haber una caja abierta por sucursal a la vez.
- Para vender, la caja debe estar abierta.
- Cada medio de pago se cierra independientemente con su propio arqueo.
- Cierre total = cierra todos los métodos pendientes de una vez.
- Auto-cierre por cambio de día: si la última apertura quedó sin cierre total y
  correspondía a un día anterior (zona horaria Argentina), se registra un cierre
  total automático para que cada jornada arranque con la caja cerrada.
"""

from typing import Optional, List, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from app.models.movimiento_caja import MovimientoCaja

# Zona horaria Argentina (UTC-3)
TZ_AR = timezone(timedelta(hours=-3))


def _ahora_local() -> datetime:
    """Devuelve la hora actual en zona horaria Argentina."""
    return datetime.now(TZ_AR)


def _a_local(dt: datetime) -> datetime:
    """Convierte un datetime a zona horaria Argentina."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(TZ_AR)


def _es_apertura_del_dia_actual(fecha_utc: Optional[datetime]) -> bool:
    """True si la fecha (UTC) corresponde al día actual en zona Argentina."""
    if fecha_utc is None:
        return False
    return _a_local(fecha_utc).date() == _ahora_local().date()


def caja_abierta(db: Session, sucursal_id: int = 1) -> bool:
    """Verifica si hay una caja abierta para la jornada actual.

    - Cierre total manual: la caja queda cerrada.
    - Apertura del día actual (zona Argentina): caja abierta.
    - Apertura de un día anterior sin cierre total posterior: se considera
      automáticamente cerrada por cambio de día (caja cerrada para hoy).
    """
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )
    # Escanear desde el movimiento más reciente hacia atrás
    for m in movimientos:
        # Cierre total: la caja quedó cerrada
        if m.tipo == "cierre" and not m.medio_pago:
            return False
        # Apertura: caja abierta solo si corresponde al día actual
        if m.tipo == "apertura":
            return _es_apertura_del_dia_actual(m.created_at)
    # Sin aperturas ni cierres registrados: caja cerrada
    return False


def cerrar_sesion_anterior_automaticamente(db: Session, sucursal_id: int = 1) -> bool:
    """Registra un cierre total automático si la última apertura quedó abierta
    un día anterior (zona Argentina). Devuelve True si se registró el cierre.

    Mantiene el historial consistente: cada jornada queda cerrada aunque el
    operador se haya olvidado de hacer el cierre manual al salir.
    """
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )
    apertura = None
    for m in movimientos:
        # Si hay un cierre total reciente, no hay sesión abierta previa
        if m.tipo == "cierre" and not m.medio_pago:
            return False
        if m.tipo == "apertura":
            apertura = m
            break
    if apertura is None:
        return False
    if _es_apertura_del_dia_actual(apertura.created_at):
        return False

    desglose = obtener_resumen_por_medio_pago(db, sucursal_id)
    total = desglose["total_ingresos"]
    desc = f"Cierre automático por cambio de día. Total ingresos: ${total:,.2f}"
    cierre = MovimientoCaja(
        tipo="cierre",
        monto=total,
        monto_esperado=total,
        descripcion=desc,
        medio_pago=None,
        fue_automatico=True,
        usuario_id=apertura.usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(cierre)
    db.commit()
    db.refresh(cierre)
    return True


def abrir_caja(
    db: Session,
    monto_inicial: float,
    usuario_id: int,
    sucursal_id: int = 1,
    monto_retiro: float = 0.0,
    motivo_retiro: str = "",
) -> MovimientoCaja:
    """Abre la caja con un monto inicial.
    
    Si hay monto_retiro > 0, crea automáticamente un egreso vinculado.
    
    Args:
        monto_inicial: Monto con el que se abre la caja (sugerido del último cierre)
        monto_retiro: Monto que se aparta/retira al abrir (opcional)
        motivo_retiro: Motivo del retiro (ej: "Fondo para cambio", "Retiro de efectivo")
    
    Returns:
        MovimientoCaja de la apertura
    
    Raises:
        ValueError: Si ya hay una caja abierta.
    """
    # Auto-cierre por cambio de día antes de abrir una nueva jornada
    cerrar_sesion_anterior_automaticamente(db, sucursal_id)
    if caja_abierta(db, sucursal_id):
        raise ValueError("Ya hay una caja abierta. Ciérrela primero.")

    # Fecha local para la descripción
    ahora_local = _ahora_local()
    fecha_dia = ahora_local.strftime("%d/%m/%Y")
    
    movimiento = MovimientoCaja(
        tipo="apertura",
        monto=monto_inicial,
        descripcion=f"Apertura de caja del día {fecha_dia}",
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    
    # Si hay retiro, crear egreso automáticamente
    if monto_retiro > 0:
        descripcion_retiro = f"Retiro al abrir caja"
        if motivo_retiro:
            descripcion_retiro += f": {motivo_retiro}"
        
        egreso = MovimientoCaja(
            tipo="egreso",
            monto=monto_retiro,
            descripcion=descripcion_retiro,
            usuario_id=usuario_id,
            sucursal_id=sucursal_id,
            referencia_tipo="retiro_apertura",
            referencia_id=movimiento.id,
        )
        db.add(egreso)
        db.commit()
    
    return movimiento


def obtener_ultimo_cierre(db: Session, sucursal_id: int = 1) -> Optional[dict]:
    """Obtiene información del último cierre de caja.
    
    Returns:
        dict con: monto, fecha (UTC), fecha_local, descripcion, fue_automatico
        None si no hay cierres.
    """
    ultimo_cierre = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "cierre",
            MovimientoCaja.medio_pago == None,
        )
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
    
    if not ultimo_cierre:
        return None
    
    fecha_utc = ultimo_cierre.created_at
    fecha_local = _a_local(fecha_utc) if fecha_utc else None
    
    # Detectar si fue automático por la descripción
    fue_automatico = bool(ultimo_cierre.fue_automatico) or "automático" in (ultimo_cierre.descripcion or "").lower()
    
    return {
        "monto": ultimo_cierre.monto or 0.0,
        "monto_esperado": ultimo_cierre.monto_esperado or ultimo_cierre.monto,
        "monto_confirmado": ultimo_cierre.monto_confirmado,
        "fecha_utc": fecha_utc.isoformat() if fecha_utc else None,
        "fecha_local": fecha_local.isoformat() if fecha_local else None,
        "fecha_local_str": fecha_local.strftime("%d/%m/%Y %H:%M") if fecha_local else None,
        "descripcion": ultimo_cierre.descripcion,
        "fue_automatico": fue_automatico,
        "usuario_id": ultimo_cierre.usuario_id,
    }


def confirmar_cierre(
    db: Session,
    cierre_id: int,
    monto_confirmado: float,
    usuario_id: int,
    comentario: str = "",
    sucursal_id: int = 1,
) -> MovimientoCaja:
    """Confirma (o ajusta) un cierre de caja con el monto real contado.

    Conserva siempre el monto esperado (cálculo del sistema) y guarda aparte
    el monto confirmado más el autor y la fecha. Sirve tanto para cierres
    automáticos por cambio de día como para cierres manuales que requieren
    conciliación posterior.
    """
    cierre = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.id == cierre_id,
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "cierre",
            MovimientoCaja.medio_pago == None,  # cierre total
        )
        .first()
    )
    if not cierre:
        raise ValueError("Cierre no encontrado o no corresponde a un cierre total.")

    if monto_confirmado < 0:
        raise ValueError("El monto confirmado no puede ser negativo.")

    cierre.monto_confirmado = float(monto_confirmado)
    cierre.confirmado_por_id = usuario_id
    cierre.confirmado_at = datetime.now(timezone.utc)
    if comentario:
        cierre.comentario_concil = comentario
    db.add(cierre)
    db.commit()
    db.refresh(cierre)
    return cierre


def cerrar_metodo(
    db: Session,
    medio_pago: str,
    monto_real: float,
    usuario_id: int,
    comentario: str = "",
    sucursal_id: int = 1,
) -> Tuple[MovimientoCaja, float, float]:
    """Cierra un medio de pago específico con arqueo propio.

    Returns:
        (movimiento, saldo_esperado, diferencia)
    """
    if not caja_abierta(db, sucursal_id):
        raise ValueError("No hay caja abierta para cerrar.")

    desglose = obtener_resumen_por_medio_pago(db, sucursal_id)
    esperado = desglose["desglose"].get(medio_pago, 0)

    # Para efectivo: sumar el monto de apertura inicial
    if medio_pago == "efectivo":
        apertura_monto = _obtener_monto_apertura(db, sucursal_id)
        esperado += apertura_monto

    diferencia = monto_real - esperado

    # Verificar que no esté ya cerrado este método en la sesión actual
    ya_cerrado = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "cierre_parcial",
            MovimientoCaja.medio_pago == medio_pago,
        )
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
    if ya_cerrado:
        apertura_sesion = _apertura_sesion_actual(db, sucursal_id)
        if apertura_sesion and ya_cerrado.id > apertura_sesion.id:
            raise ValueError(f"El método '{medio_pago}' ya fue cerrado en esta sesión.")

    desc = f"Cierre {medio_pago}. Esperado: ${esperado:,.2f}. Diferencia: ${diferencia:,.2f}"
    if comentario:
        desc += f" — {comentario}"

    movimiento = MovimientoCaja(
        tipo="cierre_parcial",
        monto=monto_real,
        medio_pago=medio_pago,
        descripcion=desc,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento, esperado, diferencia


def cerrar_todo(
    db: Session,
    usuario_id: int,
    comentario: str = "",
    sucursal_id: int = 1,
) -> Tuple[MovimientoCaja, dict]:
    """Cierra la caja completamente. Marca el fin de la sesión.

    Returns:
        (movimiento_cierre_total, desglose_por_medio_pago)
    """
    if not caja_abierta(db, sucursal_id):
        raise ValueError("No hay caja abierta para cerrar.")

    desglose = obtener_resumen_por_medio_pago(db, sucursal_id)
    total = desglose["total_ingresos"]

    desc = f"Cierre total de caja. Total ingresos: ${total:,.2f}"
    if comentario:
        desc += f" — {comentario}"

    movimiento = MovimientoCaja(
        tipo="cierre",
        monto=total,
        monto_esperado=total,
        descripcion=desc,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
        medio_pago=None,  # null = cierre total
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento, desglose


def registrar_ingreso(
    db: Session,
    monto: float,
    descripcion: str,
    usuario_id: int,
    referencia_tipo: Optional[str] = None,
    referencia_id: Optional[int] = None,
    sucursal_id: int = 1,
    medio_pago: str = "efectivo",
) -> MovimientoCaja:
    """Registra un ingreso de dinero (ej: pago de una venta)."""
    movimiento = MovimientoCaja(
        tipo="ingreso",
        monto=monto,
        descripcion=descripcion,
        medio_pago=medio_pago,
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
    """Calcula el saldo actual desde la última apertura hasta ahora."""
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )

    saldo = 0.0
    for m in movimientos:
        # Cierre total: fin del ciclo
        if m.tipo == "cierre" and not m.medio_pago:
            saldo = 0.0
            break
        if m.tipo in ("apertura", "ingreso"):
            saldo += m.monto
        elif m.tipo == "egreso":
            saldo -= m.monto
        # Cierre parcial no afecta el saldo (es informativo)

    return saldo


def obtener_estado_caja(db: Session, sucursal_id: int = 1) -> dict:
    """Devuelve el estado actual de la caja."""
    # Auto-cierre por cambio de día: si la última apertura es de un día anterior,
    # registrar el cierre automático para que hoy la caja arranque cerrada.
    cerrar_sesion_anterior_automaticamente(db, sucursal_id)
    abierta = caja_abierta(db, sucursal_id)
    saldo = obtener_saldo_actual(db, sucursal_id) if abierta else 0.0
    metodos_cerrados = _metodos_ya_cerrados(db, sucursal_id) if abierta else []

    return {
        "abierta": abierta,
        "saldo_actual": saldo,
        "metodos_cerrados": metodos_cerrados,
    }


def _metodos_ya_cerrados(db: Session, sucursal_id: int = 1) -> list:
    """Lista qué medios de pago ya fueron cerrados en esta sesión."""
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )
    cerrados = set()
    for m in movimientos:
        if m.tipo == "cierre" and not m.medio_pago:
            break
        if m.tipo == "apertura":
            break
        if m.tipo == "cierre_parcial" and m.medio_pago:
            cerrados.add(m.medio_pago)
    return list(cerrados)


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


def obtener_resumen_por_medio_pago(db: Session, sucursal_id: int = 1) -> dict:
    """Devuelve el desglose de ingresos por medio de pago desde la última apertura."""
    from app.models.venta import Venta

    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )

    desglose = {"efectivo": 0, "debito": 0, "credito": 0, "transferencia": 0}
    egresos_total = 0
    for m in movimientos:
        # Cierre total: fin de la sesión actual
        if m.tipo == "cierre" and not m.medio_pago:
            break
        # Apertura: fin del ciclo de la sesión actual
        if m.tipo == "apertura":
            break
        if m.tipo == "ingreso":
            mp = m.medio_pago or "efectivo"
            if m.referencia_tipo == "venta":
                desglose[mp] = desglose.get(mp, 0) + m.monto
        elif m.tipo == "egreso":
            egresos_total += m.monto
        # cierre_parcial es informativo, no afecta el desglose

    # Ventas en cta_corriente (no generan MovimientoCaja, van directo a Venta)
    cta_corriente_total = 0.0
    ventas_cta = (
        db.query(Venta)
        .filter(
            Venta.sucursal_id == sucursal_id,
            Venta.medio_pago == "cta_corriente",
            Venta.estado == "confirmada",
        )
        .order_by(Venta.id.desc())
        .all()
    )
    for v in ventas_cta:
        # Solo contar las que están después de la última apertura
        if _es_posterior_a_apertura(db, v.id, sucursal_id):
            cta_corriente_total += v.total

    return {
        "desglose": desglose,
        "total_ingresos": sum(desglose.values()),
        "total_egresos": egresos_total,
        "cta_corriente": cta_corriente_total,
        "apertura": _obtener_monto_apertura(db, sucursal_id),
    }


def _es_posterior_a_apertura(db: Session, referencia_id: int, sucursal_id: int) -> bool:
    """Verifica si un ID de referencia es posterior a la última apertura de caja."""
    apertura = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "apertura",
        )
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
    if not apertura:
        return False
    # Verificar que no haya un cierre total entre la apertura y ahora
    cierre = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "cierre",
            MovimientoCaja.medio_pago == None,
            MovimientoCaja.id > apertura.id,
        )
        .first()
    )
    return not cierre


def _apertura_sesion_actual(db: Session, sucursal_id: int = 1) -> Optional[MovimientoCaja]:
    """Devuelve la apertura de la sesión actual (la más reciente sin cierre total posterior)."""
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )
    for m in movimientos:
        if m.tipo == "cierre" and not m.medio_pago:
            return None
        if m.tipo == "apertura":
            return m
    return None


def _obtener_monto_apertura(db: Session, sucursal_id: int = 1) -> float:
    """Obtiene el monto de la última apertura de caja."""
    apertura = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "apertura",
        )
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
    if apertura:
        # Verificar que no haya un cierre total después de esta apertura
        cierres_posteriores = (
            db.query(MovimientoCaja)
            .filter(
                MovimientoCaja.sucursal_id == sucursal_id,
                MovimientoCaja.tipo == "cierre",
                MovimientoCaja.medio_pago == None,
                MovimientoCaja.id > apertura.id,
            )
            .first()
        )
        if not cierres_posteriores:
            return apertura.monto or 0.0
    return 0.0
