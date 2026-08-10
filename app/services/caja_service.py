"""Servicio de Caja: apertura, cierre por método, cierre total.

Reglas de negocio:
- Solo puede haber una caja abierta por sucursal a la vez.
- Para vender, la caja debe estar abierta.
- Cada medio de pago se cierra independientemente con su propio arqueo.
- Cierre total = cierra todos los métodos pendientes de una vez.
- Auto-cierre: si el día cambió desde la apertura, se cierra automáticamente con el saldo real.
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


def caja_abierta(db: Session, sucursal_id: int = 1) -> bool:
    """Verifica si hay una caja abierta (sin cierre total).
    
    Auto-cierre: si la apertura fue en un día diferente al actual (hora Argentina),
    cierra automáticamente con el saldo real.
    """
    ultimo = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
    # Caja cerrada si el último movimiento es "cierre" sin medio_pago (cierre total)
    if ultimo and ultimo.tipo == "cierre" and not ultimo.medio_pago:
        return False
    if ultimo is None:
        return False
    # Si es apertura o cierre_parcial, está abierta
    if ultimo.tipo == "apertura":
        # Verificar si la apertura fue en un día diferente al actual (hora Argentina)
        apertura_fecha = ultimo.created_at
        if apertura_fecha:
            # Convertir a datetime si es string
            if isinstance(apertura_fecha, str):
                try:
                    apertura_fecha = datetime.fromisoformat(apertura_fecha.replace('Z', '+00:00'))
                except:
                    return True
            apertura_local = _a_local(apertura_fecha)
            ahora_local = _ahora_local()
            # Comparar fechas (día, mes, año) en hora local
            if apertura_local.date() != ahora_local.date():
                # Auto-cierre: crear movimiento de cierre automático con saldo real
                _cierre_automatico(db, sucursal_id, ultimo)
                return False
    return True


def _cierre_automatico(db: Session, sucursal_id: int, apertura: MovimientoCaja):
    """Cierra automáticamente la caja cuando cambia el día.
    
    Usa el saldo real calculado en lugar de 0.
    """
    try:
        # Calcular saldo real antes de cerrar
        saldo_real = obtener_saldo_actual(db, sucursal_id)
        
        # Fecha local del día que corresponde (día de la apertura)
        apertura_local = _a_local(apertura.created_at)
        fecha_dia = apertura_local.strftime("%d/%m/%Y")
        
        movimiento = MovimientoCaja(
            tipo="cierre",
            monto=saldo_real,
            descripcion=f"Cierre automático del día {fecha_dia}. Saldo: ${saldo_real:,.2f}",
            usuario_id=apertura.usuario_id,
            sucursal_id=sucursal_id,
            medio_pago=None,
        )
        db.add(movimiento)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"[Caja] Error en cierre automático: {e}")


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
    fue_automatico = "automático" in (ultimo_cierre.descripcion or "").lower()
    
    return {
        "monto": ultimo_cierre.monto or 0.0,
        "fecha_utc": fecha_utc.isoformat() if fecha_utc else None,
        "fecha_local": fecha_local.isoformat() if fecha_local else None,
        "fecha_local_str": fecha_local.strftime("%d/%m/%Y %H:%M") if fecha_local else None,
        "descripcion": ultimo_cierre.descripcion,
        "fue_automatico": fue_automatico,
        "usuario_id": ultimo_cierre.usuario_id,
    }


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

    # Verificar que no esté ya cerrado este método en esta sesión
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
        # Verificar que el cierre no haya sido después de la última apertura
        desde_apertura = True
        movs = (
            db.query(MovimientoCaja)
            .filter(MovimientoCaja.sucursal_id == sucursal_id)
            .order_by(MovimientoCaja.id.desc())
            .all()
        )
        for m in movs:
            if m.id == ya_cerrado.id:
                break
            if m.tipo == "cierre" and not m.medio_pago:
                desde_apertura = False
                break
            if m.tipo == "apertura":
                desde_apertura = True
                break
        if desde_apertura:
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
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "ingreso",
            MovimientoCaja.referencia_tipo == "venta",
        )
        .order_by(MovimientoCaja.id.desc())
        .all()
    )

    desglose = {"efectivo": 0, "debito": 0, "credito": 0, "transferencia": 0}
    for m in movimientos:
        if m.tipo == "cierre" and not m.medio_pago:
            break
        if m.tipo == "ingreso" and m.referencia_tipo == "venta":
            mp = m.medio_pago or "efectivo"
            if mp in desglose:
                desglose[mp] += m.monto
            else:
                desglose[mp] = desglose.get(mp, 0) + m.monto

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

    egresos_total = 0
    for m in movimientos:
        if m.tipo == "cierre" and not m.medio_pago:
            break
        if m.tipo == "egreso":
            egresos_total += m.monto

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
