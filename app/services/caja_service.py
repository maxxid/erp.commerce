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
import sqlalchemy as sa
from sqlalchemy.orm import Session
from app.models.movimiento_caja import MovimientoCaja
from app.services import config_service

# Zona horaria Argentina (UTC-3)
TZ_AR = timezone(timedelta(hours=-3))

# Medios de pago con cuenta digital externa (el saldo vive fuera de la caja).
# Se arquean por separado: el sistema calcula el saldo esperado de cada cuenta
# (saldo inicial + ingresos - egresos) y el operador carga el saldo real que
# muestra la app del proveedor.
MEDIOS_CUENTA = {
    "smartpoint": "SmartPoint",
    "mercadopago_qr": "MercadoPago QR",
    "mercadopago_pos": "MercadoPago POS",
    "qr_interop": "QR Interoperable",
}

# Medios de pago sin cuenta digital propia (tarjetas, transferencias, efectivo)
MEDIOS_INGRESO = {
    "efectivo": "Efectivo",
    "debito": "Débito",
    "credito": "Crédito",
    "transferencia": "Transferencia",
    **MEDIOS_CUENTA,
}

MEDIOS_ESPERADOS_ARQUEO = ["efectivo", "debito", "credito", "transferencia"]

# Egresos que se registran durante el cierre y cuyo referencia_id apunta al
# cierre al que pertenecen (o, con sesion_cierre_id, a su sesión). Los dos
# informan por igual el arqueo: bajan el esperado del medio de pago del que
# salió el dinero.
REFERENCIAS_EGRESO_CIERRE = ("retiro_cierre", "pago_proveedor")


def nombre_medio(medio_pago: Optional[str]) -> str:
    """Nombre legible del medio de pago."""
    if not medio_pago:
        return "Efectivo"
    return MEDIOS_INGRESO.get(medio_pago, medio_pago)


def _es_apertura_de_caja(m: MovimientoCaja) -> bool:
    """True si el movimiento es la apertura de la sesión (cajón)."""
    return m.tipo == "apertura" and not m.medio_pago


def _fila_saldo() -> dict:
    """Fila vacía de saldos por medio de pago."""
    return {"apertura": 0.0, "ingresos": 0.0, "egresos": 0.0, "esperado": 0.0}


def _calcular_esperados(saldos: dict) -> None:
    """Resuelve esperado = apertura + ingresos - egresos en cada medio."""
    for fila in saldos.values():
        fila["esperado"] = fila["apertura"] + fila["ingresos"] - fila["egresos"]



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


def _get_cambio_dia_hora(db: Session) -> int:
    """Obtiene la hora configurada para el cambio de día (default 6 AM)."""
    try:
        return config_service.get_caja_cierre_automatico_hora(db)
    except Exception:
        return 6


def _es_apertura_del_dia_actual(db: Session, fecha_utc: Optional[datetime]) -> bool:
    """True si la fecha (UTC) corresponde al día actual en zona Argentina.
    
    El día comercial va desde la hora configurada (default 06:00) hasta la misma hora del día siguiente.
    """
    if fecha_utc is None:
        return False
    ahora_local = _ahora_local()
    cambio_hora = _get_cambio_dia_hora(db)
    
    # Calcular el "día comercial" actual: si son las 05:00, todavía es el día anterior
    if ahora_local.hour < cambio_hora:
        dia_comercial = (ahora_local - timedelta(days=1)).date()
    else:
        dia_comercial = ahora_local.date()
    
    fecha_local = _a_local(fecha_utc)
    # Mismo ajuste para la fecha de la apertura
    if fecha_local.hour < cambio_hora:
        fecha_dia_comercial = (fecha_local - timedelta(days=1)).date()
    else:
        fecha_dia_comercial = fecha_local.date()
    
    return fecha_dia_comercial == dia_comercial


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
        if _es_apertura_de_caja(m):
            return _es_apertura_del_dia_actual(db, m.created_at)
    # Sin aperturas ni cierres registrados: caja cerrada
    return False


def cerrar_sesion_anterior_automaticamente(db: Session, sucursal_id: int = 1) -> bool:
    """Registra un cierre total automático si la última apertura quedó abierta
    un día anterior (zona Argentina). Devuelve True si se registró el cierre.

    Mantiene el historial consistente: cada jornada queda cerrada aunque el
    operador se haya olvidado de hacer el cierre manual al salir.
    """
    # Verificar si el cierre automático está habilitado en configuración
    if not config_service.get_caja_cierre_automatico(db):
        return False
    
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
        if _es_apertura_de_caja(m):
            apertura = m
            break
    if apertura is None:
        return False
    if _es_apertura_del_dia_actual(db, apertura.created_at):
        return False

    desglose = obtener_resumen_por_medio_pago(db, sucursal_id)
    total = desglose.get("saldo_medios_total", desglose.get("saldo_total"))
    desc = f"Cierre automático por cambio de día. Total esperado: ${total:,.2f}"
    cierre = MovimientoCaja(
        tipo="cierre",
        monto=total,
        monto_esperado=total,
        saldo_efectivo=round(desglose.get("saldo_efectivo", 0.0), 2),
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
    saldos_cuentas: Optional[dict] = None,
) -> MovimientoCaja:
    """Abre la caja con un monto inicial.
    
    Si hay monto_retiro > 0, crea automáticamente un egreso vinculado.
    
    Args:
        monto_inicial: Monto con el que se abre el cajón (sugerido del último cierre)
        monto_retiro: Monto que se aparta/retira al abrir (opcional)
        motivo_retiro: Motivo del retiro (ej: "Fondo para cambio", "Retiro de efectivo")
        saldos_cuentas: Saldo inicial de cada cuenta digital al abrir
            (ej: {"smartpoint": 5000, "mercadopago_qr": 1200})
    
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

    # Saldo inicial de cada cuenta digital: es el punto de partida del arqueo
    # de esa cuenta (apertura + ingresos - egresos = saldo esperado).
    for medio, monto in (saldos_cuentas or {}).items():
        if medio not in MEDIOS_CUENTA or not monto or float(monto) <= 0:
            continue
        db.add(
            MovimientoCaja(
                tipo="apertura",
                monto=float(monto),
                descripcion=f"Apertura de {nombre_medio(medio)}",
                medio_pago=medio,
                referencia_tipo="apertura_cuenta",
                referencia_id=movimiento.id,
                usuario_id=usuario_id,
                sucursal_id=sucursal_id,
            )
        )
    if saldos_cuentas:
        db.commit()
    
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


def obtener_saldos_cuentas_sugeridos(db: Session, sucursal_id: int = 1) -> dict:
    """Saldos con los que seSugiere abrir las cuentas digitales.

    Se toma el saldo real con el que quedó cada cuenta en el último cierre
    parcial, para que el operador solo tenga que confirmar el número que ve en
    la app del proveedor.
    """
    sugeridos: dict = {}
    for medio in MEDIOS_CUENTA:
        ultimo = (
            db.query(MovimientoCaja)
            .filter(
                MovimientoCaja.sucursal_id == sucursal_id,
                MovimientoCaja.tipo == "cierre_parcial",
                MovimientoCaja.medio_pago == medio,
            )
            .order_by(MovimientoCaja.id.desc())
            .first()
        )
        if ultimo is not None:
            sugeridos[medio] = ultimo.monto or 0.0
    return sugeridos


def obtener_ultimo_cierre(db: Session, sucursal_id: int = 1) -> Optional[dict]:
    """Obtiene información del último cierre de caja.
    
    Returns:
        dict con: monto, fecha (UTC y local), descripcion, fue_automatico
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

    # Usar directamente el campo booleano fue_automatico (no fallback a descripción)
    fue_automatico = bool(ultimo_cierre.fue_automatico)

    saldo_efectivo = ultimo_cierre.saldo_efectivo
    if saldo_efectivo is None:
        # Cierres anteriores a la columna: el efectivo de esa sesión se recalcula
        # desde su apertura, así la apertura siguiente no sugiere abrir el cajón
        # con la suma de todas las cuentas digitales.
        try:
            _, apertura_sesion = obtener_sesion_por_cierre(db, ultimo_cierre.id)
            saldos_sesion = _saldos_de_sesion(db, apertura_sesion, ultimo_cierre.id)
            saldo_efectivo = round(saldos_sesion.get("efectivo", {}).get("esperado", 0.0), 2)
        except ValueError:
            saldo_efectivo = None

    return {
        "monto": ultimo_cierre.monto or 0.0,
        "monto_esperado": ultimo_cierre.monto_esperado or ultimo_cierre.monto,
        "monto_confirmado": ultimo_cierre.monto_confirmado,
        "saldo_efectivo": saldo_efectivo,
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


def obtener_sesion_por_cierre(db: Session, cierre_id: int, sucursal_id: int = 1) -> Tuple[MovimientoCaja, MovimientoCaja]:
    """Devuelve (cierre, apertura) de la sesión que terminó en ese cierre total.

    El arqueo de una sesión ya cerrada (la que el sistema cerró sola al cambiar de
    día) se calcula entre su apertura y su cierre, no desde la última apertura.
    Así el cierre se puede completar aunque ya haya una caja nueva abierta.
    """
    cierre = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.id == cierre_id,
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "cierre",
            MovimientoCaja.medio_pago == None,
        )
        .first()
    )
    if not cierre:
        raise ValueError("El cierre no existe o no es un cierre total de caja.")

    anteriores = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id, MovimientoCaja.id < cierre.id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )
    for m in anteriores:
        if m.tipo == "cierre" and not m.medio_pago:
            break
        if _es_apertura_de_caja(m):
            return cierre, m
    raise ValueError("Ese cierre no tiene una apertura de caja asociada.")


def _exigir_sesion_arqueable(db: Session, cierre_id: int, sucursal_id: int = 1) -> Tuple[MovimientoCaja, MovimientoCaja]:
    """Como obtener_sesion_por_cierre, pero rechaza las sesiones ya conciliadas.

    Conciliar es el último paso del cierre: una vez que hay monto confirmado el
    resultado es inmutable, así que ni arqueos ni extracciones pueden tocarlo.
    """
    cierre, apertura = obtener_sesion_por_cierre(db, cierre_id, sucursal_id)
    if cierre.monto_confirmado is not None:
        raise ValueError("Este cierre ya fue conciliado: no se puede modificar.")
    return cierre, apertura


def _movimientos_de_sesion(db: Session, apertura: MovimientoCaja, cierre_id: int, sucursal_id: int = 1) -> List[MovimientoCaja]:
    """Movimientos que pertenecen a una sesión.

    Son los que caen entre su apertura y su cierre, más los que se le registraron
    después. Esto último pasa siempre que el sistema cierra solo: el arqueo
    diferido y las extracciones se guardan tomando el id del cierre como
    referencia, así que quedan con un id mayor al del cierre y no entrarían en el
    rango, y sin ellos el arqueo de esa sesión daría el saldo previo a la
    extracción.

    El pago a proveedor se anota con sesion_cierre_id porque su referencia_id
    lo ocupa el proveedor, así que entra por esa rama y no por la otra.
    """
    return (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            sa.or_(
                sa.and_(MovimientoCaja.id > apertura.id, MovimientoCaja.id < cierre_id),
                # Todo lo que se anotó tomando este cierre como referencia, sin
                # filtrar por tipo: el arqueo de un medio (cierre_total) y las
                # extracciones también entran así.
                sa.and_(
                    MovimientoCaja.id > cierre_id,
                    MovimientoCaja.referencia_id == cierre_id,
                ),
                # El pago a proveedor no puede usar referencia_id (lo ocupa el
                # proveedor), así que apunta a su sesión por otra columna.
                sa.and_(
                    MovimientoCaja.id > cierre_id,
                    MovimientoCaja.sesion_cierre_id == cierre_id,
                ),
            ),
        )
        .order_by(MovimientoCaja.id.desc())
        .all()
    )


def _saldos_de_sesion(db: Session, apertura: MovimientoCaja, cierre_id: int, sucursal_id: int = 1) -> dict:
    """Saldos por medio acotados a una sesión (lo que pasó entre su apertura y su cierre)."""
    saldos: dict = {}
    fila = saldos.setdefault("efectivo", _fila_saldo())
    fila["apertura"] += apertura.monto or 0.0

    for m in _movimientos_de_sesion(db, apertura, cierre_id, sucursal_id):
        if m.tipo == "apertura" and m.medio_pago:
            fila = saldos.setdefault(m.medio_pago, _fila_saldo())
            fila["apertura"] += m.monto or 0.0
        elif m.tipo == "ingreso":
            fila = saldos.setdefault(m.medio_pago or "efectivo", _fila_saldo())
            fila["ingresos"] += m.monto or 0.0
        elif m.tipo == "egreso":
            fila = saldos.setdefault(m.medio_pago or "efectivo", _fila_saldo())
            fila["egresos"] += m.monto or 0.0
        # cierre_parcial es informativo, no afecta el saldo

    _calcular_esperados(saldos)
    return saldos


def _cierres_parciales_de_sesion(db: Session, apertura: MovimientoCaja, cierre_id: int, sucursal_id: int = 1) -> dict:
    """Medios ya arqueados en la sesión: {medio: movimiento}, el más reciente de cada uno."""
    movimientos = [
        m for m in _movimientos_de_sesion(db, apertura, cierre_id, sucursal_id)
        if m.tipo == "cierre_parcial"
    ]
    return {m.medio_pago: m for m in movimientos if m.medio_pago}


def obtener_arqueo_sesion(db: Session, cierre_id: int, sucursal_id: int = 1) -> dict:
    """Arqueo por medio de una sesión, con lo que ya tiene registrado.

    Sirve para dos cosas: la pantalla de arqueo de la caja abierta y el cierre
    diferido de una sesión que el sistema ya cerró sola.
    """
    cierre, apertura = obtener_sesion_por_cierre(db, cierre_id, sucursal_id)
    por_medio = _armar_arqueo(_saldos_de_sesion(db, apertura, cierre.id, sucursal_id))

    cerrados = _cierres_parciales_de_sesion(db, apertura, cierre.id, sucursal_id)
    for fila in por_medio:
        mov = cerrados.get(fila["medio_pago"])
        fila["cerrado"] = mov is not None
        fila["monto_real"] = round(mov.monto or 0.0, 2) if mov else None
        fila["diferencia"] = round((mov.monto or 0.0) - fila["esperado"], 2) if mov else None
        fila["comentario"] = mov.descripcion if mov else ""

    retiros = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "egreso",
            MovimientoCaja.referencia_tipo.in_(REFERENCIAS_EGRESO_CIERRE),
            sa.or_(
                MovimientoCaja.referencia_id == cierre.id,
                MovimientoCaja.sesion_cierre_id == cierre.id,
            ),
        )
        .order_by(MovimientoCaja.id.desc())
        .all()
    )

    saldo_efectivo = next((f["esperado"] for f in por_medio if f["medio_pago"] == "efectivo"), 0.0)
    pendientes = [f["medio_pago"] for f in por_medio if f["esperado"] > 0 and not f["cerrado"]]
    return {
        "cierre_id": cierre.id,
        "apertura_id": apertura.id,
        "apertura_monto": round(apertura.monto or 0.0, 2),
        "apertura_fecha": apertura.created_at.isoformat() if apertura.created_at else None,
        "cierre_fecha": cierre.created_at.isoformat() if cierre.created_at else None,
        "fue_automatico": bool(cierre.fue_automatico),
        "confirmado": cierre.monto_confirmado is not None,
        "monto_confirmado": cierre.monto_confirmado,
        "confirmado_por_id": cierre.confirmado_por_id,
        "monto_esperado": round(cierre.monto_esperado if cierre.monto_esperado is not None else cierre.monto or 0.0, 2),
        "saldo_esperado": round(sum(f["esperado"] for f in por_medio), 2),
        "saldo_efectivo_esperado": round(saldo_efectivo, 2),
        "total_retiros": round(sum(m.monto or 0.0 for m in retiros), 2),
        "medios_pendientes": pendientes,
        "por_medio": por_medio,
        "retiros": _serializar_retiros(retiros),
    }


def _serializar_retiros(retiros: List[MovimientoCaja]) -> List[dict]:
    """Egresos de cierre ya registrados, para mostrarlos y borrarlos.

    Van juntos porque los dos se muestran en el mismo lugar del arqueo, pero
    cada uno lleva su tipo: el front usa eso para ofrecer el botón que
    corresponde y para no mandar a borrar un pago por la vía de las extracciones.
    """
    return [
        {
            "id": m.id,
            "tipo": m.referencia_tipo or "retiro_cierre",
            "monto": round(m.monto or 0.0, 2),
            "medio_pago": m.medio_pago or "efectivo",
            "descripcion": m.descripcion,
            "proveedor_id": m.referencia_id if m.referencia_tipo == "pago_proveedor" else None,
            "fecha": m.created_at.isoformat() if m.created_at else None,
        }
        for m in retiros
    ]


def _recalcular_cierre(db: Session, cierre: MovimientoCaja, sucursal_id: int = 1) -> None:
    """Recalcula el monto esperado del cierre cuando cambia algo de la sesión.

    El cierre guarda el total que el sistema esperaba al momento de cerrarse. Si
    después se registra (o se borra) una extracción, ese total quedaría desfasado
    y la conciliación mostraría una diferencia que no existe.
    """
    _, apertura = obtener_sesion_por_cierre(db, cierre.id, sucursal_id)
    por_medio = _armar_arqueo(_saldos_de_sesion(db, apertura, cierre.id, sucursal_id))
    total = round(sum(f["esperado"] for f in por_medio), 2)
    efectivo = next((f["esperado"] for f in por_medio if f["medio_pago"] == "efectivo"), 0.0)
    cierre.monto = total
    cierre.monto_esperado = total
    cierre.saldo_efectivo = round(efectivo, 2)
    db.commit()


def registrar_retiro_cierre(
    db: Session,
    monto: float,
    motivo: str,
    usuario_id: int,
    cierre_id: Optional[int] = None,
    sucursal_id: int = 1,
    medio_pago: str = "efectivo",
) -> MovimientoCaja:
    """Registra la plata que se saca del cajón al cerrar la jornada.

    Queda como egreso de la sesión con su motivo, igual que el retiro de apertura:
    el cajón no tiene por qué quedar lleno de plata al cerrar. Con `cierre_id` el
    egreso pertenece a una sesión ya cerrada y el monto esperado del cierre se
    recalcula; sin `cierre_id` es el retiro de la sesión abierta.
    """
    if monto <= 0:
        raise ValueError("El monto a extraer tiene que ser mayor a 0.")
    if medio_pago not in MEDIOS_INGRESO:
        raise ValueError("Medio de pago inválido para la extracción.")

    cierre = None
    if cierre_id is not None:
        cierre, _ = _exigir_sesion_arqueable(db, cierre_id, sucursal_id)
    elif not caja_abierta(db, sucursal_id):
        raise ValueError("No hay caja abierta para registrar la extracción.")

    descripcion = "Extracción de dinero al cerrar caja"
    if motivo:
        descripcion += f": {motivo}"

    movimiento = MovimientoCaja(
        tipo="egreso",
        monto=float(monto),
        descripcion=descripcion,
        medio_pago=medio_pago,
        referencia_tipo="retiro_cierre",
        referencia_id=cierre.id if cierre is not None else None,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)

    if cierre is not None:
        _recalcular_cierre(db, cierre, sucursal_id)
    return movimiento


def eliminar_retiro_cierre(db: Session, retiro_id: int, sucursal_id: int = 1) -> None:
    """Da de baja una extracción mal cargada, si su sesión todavía es arqueable."""
    movimiento = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.id == retiro_id,
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "egreso",
            MovimientoCaja.referencia_tipo == "retiro_cierre",
        )
        .first()
    )
    if not movimiento:
        raise ValueError("La extracción no existe.")

    cierre = None
    if movimiento.referencia_id is not None:
        cierre, _ = _exigir_sesion_arqueable(db, movimiento.referencia_id, sucursal_id)
    elif not caja_abierta(db, sucursal_id):
        raise ValueError("No hay caja abierta para modificar la extracción.")

    db.delete(movimiento)
    db.commit()

    if cierre is not None:
        _recalcular_cierre(db, cierre, sucursal_id)


def registrar_pago_proveedor(
    db: Session,
    monto: float,
    usuario_id: int,
    proveedor_id: Optional[int] = None,
    proveedor_nombre: str = "",
    descripcion: str = "",
    cierre_id: Optional[int] = None,
    medio_pago: str = "efectivo",
    sucursal_id: int = 1,
) -> MovimientoCaja:
    """Registra el pago a un proveedor hecho con plata de la caja.

    Es un egreso más de la sesión, así que baja el esperado del medio de pago
    del que salió el dinero y aparece junto a las extracciones en el arqueo.
    Lo que lo distingue es que guarda contra quién se pagó: el proveedor va en
    referencia_id y la sesión en sesion_cierre_id.

    El nombre del proveedor se copia a la descripción porque el arqueo se lee
    sin joins: si el proveedor se renombra después, el cierre del día anterior
    tiene que seguir diciendo a quién se le pagó.
    """
    if monto <= 0:
        raise ValueError("El monto del pago tiene que ser mayor a 0.")
    if medio_pago not in MEDIOS_INGRESO:
        raise ValueError(f"Medio de pago inválido. Opciones: {', '.join(MEDIOS_INGRESO)}")
    if proveedor_id is None and not proveedor_nombre:
        raise ValueError("Elegí un proveedor o escribí a quién le pagaste.")

    cierre = None
    if cierre_id is not None:
        cierre, _ = _exigir_sesion_arqueable(db, cierre_id, sucursal_id)
    elif not caja_abierta(db, sucursal_id):
        raise ValueError("No hay caja abierta para registrar el pago.")

    quien = (proveedor_nombre or "").strip()
    partes = []
    if quien:
        partes.append(quien)
    if descripcion.strip():
        partes.append(descripcion.strip())
    detalle = ": ".join(partes)
    texto = "Pago a proveedor"
    if detalle:
        texto += f": {detalle}"

    movimiento = MovimientoCaja(
        tipo="egreso",
        monto=float(monto),
        descripcion=texto,
        medio_pago=medio_pago,
        referencia_tipo="pago_proveedor",
        referencia_id=proveedor_id,
        sesion_cierre_id=cierre.id if cierre is not None else None,
        usuario_id=usuario_id,
        sucursal_id=sucursal_id,
    )
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)

    if cierre is not None:
        _recalcular_cierre(db, cierre, sucursal_id)
    return movimiento


def eliminar_pago_proveedor(db: Session, pago_id: int, sucursal_id: int = 1) -> None:
    """Da de baja un pago a proveedor mal cargado, si su sesión es arqueable."""
    movimiento = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.id == pago_id,
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "egreso",
            MovimientoCaja.referencia_tipo == "pago_proveedor",
        )
        .first()
    )
    if not movimiento:
        raise ValueError("El pago no existe.")

    cierre = None
    if movimiento.sesion_cierre_id is not None:
        cierre, _ = _exigir_sesion_arqueable(db, movimiento.sesion_cierre_id, sucursal_id)
    elif not caja_abierta(db, sucursal_id):
        raise ValueError("No hay caja abierta para modificar el pago.")

    db.delete(movimiento)
    db.commit()

    if cierre is not None:
        _recalcular_cierre(db, cierre, sucursal_id)


def cerrar_metodo_sesion(
    db: Session,
    cierre_id: int,
    medio_pago: str,
    monto_real: float,
    usuario_id: int,
    comentario: str = "",
    sucursal_id: int = 1,
) -> Tuple[MovimientoCaja, float, float]:
    """Arquea un medio de pago de una sesión que el sistema ya cerró sola.

    A diferencia de cerrar_metodo(), que exige la caja abierta, este completa el
    arqueo de una sesión cerrada por cambio de día. Volver a guardar un medio ya
    arqueado en esa sesión corrige el número en vez de duplicarlo.

    Returns:
        (movimiento, saldo_esperado, diferencia)
    """
    if monto_real < 0:
        raise ValueError("El monto real no puede ser negativo.")

    cierre, apertura = _exigir_sesion_arqueable(db, cierre_id, sucursal_id)
    arqueo = _armar_arqueo(_saldos_de_sesion(db, apertura, cierre.id, sucursal_id))
    fila = next((f for f in arqueo if f["medio_pago"] == medio_pago), None)
    if fila is None:
        raise ValueError(f"El medio '{nombre_medio(medio_pago)}' no tiene movimientos en esta sesión.")
    esperado = fila["esperado"]
    diferencia = round(monto_real - esperado, 2)

    desc = f"Cierre {nombre_medio(medio_pago)}. Esperado: ${esperado:,.2f}. Diferencia: ${diferencia:,.2f}"
    if comentario:
        desc += f" — {comentario}"

    movimiento = _cierres_parciales_de_sesion(db, apertura, cierre.id, sucursal_id).get(medio_pago)
    if movimiento is None:
        movimiento = MovimientoCaja(
            tipo="cierre_parcial",
            monto=float(monto_real),
            medio_pago=medio_pago,
            descripcion=desc,
            referencia_tipo="cierre_total",
            referencia_id=cierre.id,
            usuario_id=usuario_id,
            sucursal_id=sucursal_id,
        )
        db.add(movimiento)
    else:
        movimiento.monto = float(monto_real)
        movimiento.descripcion = desc
        movimiento.referencia_tipo = "cierre_total"
        movimiento.referencia_id = cierre.id
        movimiento.usuario_id = usuario_id
    db.commit()
    db.refresh(movimiento)
    return movimiento, esperado, diferencia


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

    arqueo = _construir_arqueo_por_medio(db, sucursal_id)
    fila = next((f for f in arqueo if f["medio_pago"] == medio_pago), None)
    if fila is None:
        raise ValueError(f"El medio '{medio_pago}' no tiene movimientos en esta sesión.")
    esperado = fila["esperado"]

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

    desc = f"Cierre {nombre_medio(medio_pago)}. Esperado: ${esperado:,.2f}. Diferencia: ${diferencia:,.2f}"
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
    total = desglose.get("saldo_medios_total", desglose.get("saldo_total"))

    desc = (
        f"Cierre total de caja. Total esperado de todos los medios: ${total:,.2f}"
    )
    if comentario:
        desc += f" — {comentario}"

    movimiento = MovimientoCaja(
        tipo="cierre",
        monto=total,
        monto_esperado=total,
        saldo_efectivo=round(desglose.get("saldo_efectivo", 0.0), 2),
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
    medio_pago: Optional[str] = None,
) -> MovimientoCaja:
    """Registra un egreso de dinero (ej: pago a proveedor, retiro, recarga).

    `medio_pago` indica de qué cuenta sale el dinero (para las recargas, la cuenta
    digital desde la que se carga). Si se deja None se comporta como antes.
    """
    movimiento = MovimientoCaja(
        tipo="egreso",
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


def obtener_saldo_por_medio(db: Session, sucursal_id: int = 1) -> dict:
    """Saldo de cada medio de pago desde la apertura de la sesión actual.

    Para cada medio devuelve:
        apertura: saldo inicial con el que arrancó el medio en esta sesión
        ingresos: total ingresado por el medio
        egresos: total salido del medio
        esperado: apertura + ingresos - egresos (con lo que debería haber)

    La suma de los esperados es el total de dinero bajo control de la sesión
    (cajón + cuentas digitales), sin mezclar fondos entre sí.
    """
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )

    saldos: dict = {}
    for m in movimientos:
        # Cierre total: fin del ciclo
        if m.tipo == "cierre" and not m.medio_pago:
            break
        # Apertura del cajón: fin de la sesión actual (su monto es el fondo inicial)
        if _es_apertura_de_caja(m):
            fila = saldos.setdefault("efectivo", _fila_saldo())
            fila["apertura"] += m.monto or 0.0
            break

        if m.tipo == "apertura" and m.medio_pago:
            # Saldo inicial de una cuenta digital
            fila = saldos.setdefault(m.medio_pago, _fila_saldo())
            fila["apertura"] += m.monto or 0.0
        elif m.tipo == "ingreso":
            fila = saldos.setdefault(m.medio_pago or "efectivo", _fila_saldo())
            fila["ingresos"] += m.monto or 0.0
        elif m.tipo == "egreso":
            # Un egreso de cierre con sesión asignada pertenece a la sesión de
            # ese cierre, no a la que está abierta: contarlo acá bajaría de
            # más el cajón de hoy (que ya se abrió con lo que quedó de la
            # anterior).
            #
            # Cada tipo marca su sesión distinto: la extracción lo tiene en
            # referencia_id, el pago a proveedor en sesion_cierre_id (porque
            # referencia_id lo ocupa el proveedor). Un pago a proveedor de la
            # sesión abierta tiene proveedor pero ninguna sesión, y sí cuenta.
            if m.referencia_tipo == "retiro_cierre" and m.referencia_id is not None:
                continue
            if m.referencia_tipo == "pago_proveedor" and m.sesion_cierre_id is not None:
                continue
            fila = saldos.setdefault(m.medio_pago or "efectivo", _fila_saldo())
            fila["egresos"] += m.monto or 0.0
        # cierre_parcial es informativo, no afecta el saldo

    _calcular_esperados(saldos)
    return saldos


def obtener_saldos_cuenta(db: Session, sucursal_id: int = 1) -> dict:
    """Saldos actuales de las cuentas digitales (SmartPoint, MP, etc.)."""
    saldos = obtener_saldo_por_medio(db, sucursal_id)
    return {
        medio: fila["esperado"]
        for medio, fila in saldos.items()
        if medio in MEDIOS_CUENTA
    }


def obtener_saldo_actual(db: Session, sucursal_id: int = 1) -> float:
    """Saldo del cajón (efectivo) desde la última apertura hasta ahora."""
    return obtener_saldo_por_medio(db, sucursal_id).get("efectivo", {}).get("esperado", 0.0)


def obtener_estado_caja(db: Session, sucursal_id: int = 1) -> dict:
    """Devuelve el estado actual de la caja con el cajón y las cuentas separados."""
    # Auto-cierre por cambio de día: si la última apertura es de un día anterior,
    # registrar el cierre automático para que hoy la caja arranque cerrada.
    cerrar_sesion_anterior_automaticamente(db, sucursal_id)
    abierta = caja_abierta(db, sucursal_id)
    saldos = obtener_saldo_por_medio(db, sucursal_id) if abierta else {}
    saldo_efectivo = saldos.get("efectivo", {}).get("esperado", 0.0)
    saldos_cuentas = {
        medio: fila["esperado"]
        for medio, fila in saldos.items()
        if medio in MEDIOS_CUENTA
    }
    metodos_cerrados = _metodos_ya_cerrados(db, sucursal_id) if abierta else []
    # Identidad de la sesion: el POS la usa para saber cuando arranco una caja
    # nueva (los carritos que quedaron abiertos cuentan su vida desde aca).
    apertura = _apertura_sesion_actual(db, sucursal_id) if abierta else None

    return {
        "abierta": abierta,
        "saldo_actual": saldo_efectivo,
        "saldo_efectivo": saldo_efectivo,
        "saldos_cuentas": saldos_cuentas,
        "saldo_cuenta_total": sum(saldos_cuentas.values()),
        "saldo_total": saldo_efectivo + sum(saldos_cuentas.values()),
        "metodos_cerrados": metodos_cerrados,
        "sesion_id": apertura.id if apertura else None,
        # Con "Z" explícito: created_at se guarda en UTC y el navegador lo parsea
        # como hora local si el string no dice nada, corriendo la sesión unas horas.
        "sesion_inicio": (
            apertura.created_at.isoformat() + "Z"
            if apertura and apertura.created_at
            else None
        ),
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
        # Primero: si es la apertura de la sesión actual, paramos (llegamos al inicio de la sesión)
        if _es_apertura_de_caja(m):
            break
        # Segundo: si hay un cierre total posterior, ya no es esta sesión
        if m.tipo == "cierre" and not m.medio_pago:
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
    egresos_por_medio: dict = {}
    for m in movimientos:
        # Cierre total: fin de la sesión actual
        if m.tipo == "cierre" and not m.medio_pago:
            break
        # Apertura: fin del ciclo de la sesión actual
        if _es_apertura_de_caja(m):
            break
        if m.tipo == "ingreso":
            mp = m.medio_pago or "efectivo"
            if m.referencia_tipo == "venta":
                desglose[mp] = desglose.get(mp, 0) + m.monto
        elif m.tipo == "egreso":
            # Las extracciones de sesiones ya cerradas se informan en su propio
            # arqueo: acá van solo las de la sesión abierta.
            if m.referencia_tipo == "retiro_cierre" and m.referencia_id is not None:
                continue
            egresos_total += m.monto
            if m.medio_pago:
                egresos_por_medio[m.medio_pago] = egresos_por_medio.get(m.medio_pago, 0) + m.monto
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

    por_medio = _construir_arqueo_por_medio(db, sucursal_id)
    saldo_efectivo = next(
        (f["esperado"] for f in por_medio if f["medio_pago"] == "efectivo"), 0.0
    )
    saldo_cuenta_total = sum(
        f["esperado"] for f in por_medio if f["es_cuenta_digital"]
    )
    # Total de todo lo que se arquea medio por medio. Es el que se usa como
    # monto esperado del cierre total, para que coincida con la suma de los
    # cierres parciales (débito/crédito/transferencia incluidos).
    saldo_medios_total = sum(f["esperado"] for f in por_medio)

    retiros = [
        m for m in movimientos
        if m.tipo == "egreso" and m.referencia_tipo == "retiro_cierre" and m.referencia_id is None
    ]
    return {
        "desglose": desglose,
        "total_ingresos": sum(desglose.values()),
        "total_egresos": egresos_total,
        "egresos_por_medio": egresos_por_medio,
        "cta_corriente": cta_corriente_total,
        "apertura": _obtener_monto_apertura(db, sucursal_id),
        "por_medio": por_medio,
        "saldo_efectivo": saldo_efectivo,
        "saldo_cuenta_total": saldo_cuenta_total,
        "saldo_total": saldo_efectivo + saldo_cuenta_total,
        "saldo_medios_total": saldo_medios_total,
        "total_retiros": round(sum(m.monto or 0.0 for m in retiros), 2),
        "retiros": _serializar_retiros(retiros),
    }


def _construir_arqueo_por_medio(db: Session, sucursal_id: int = 1) -> List[dict]:
    """Arma la lista de medios a arquear con su saldo esperado de la sesión abierta."""
    return _armar_arqueo(obtener_saldo_por_medio(db, sucursal_id))


def _armar_arqueo(saldos: dict) -> List[dict]:
    """Lista de medios a arquear a partir de sus saldos.

    Incluye siempre efectivo, débito, crédito y transferencia, más las cuentas
    digitales (SmartPoint, MP, etc.) que tengan movimiento o saldo inicial en la
    sesión. Cada medio se cuadra por separado: el saldo de una cuenta digital
    nunca se compensa con el del cajón.
    """
    medios = list(MEDIOS_ESPERADOS_ARQUEO)
    for medio in MEDIOS_CUENTA:
        fila = saldos.get(medio)
        if fila and (fila["apertura"] or fila["ingresos"] or fila["egresos"]):
            medios.append(medio)
    # Cualquier otro medio con movimiento (ej: ajustes manuales)
    for medio, fila in saldos.items():
        if medio not in medios and (fila["ingresos"] or fila["egresos"] or fila["apertura"]):
            medios.append(medio)

    arqueo = []
    for medio in medios:
        fila = saldos.get(medio, _fila_saldo())
        es_cuenta = medio in MEDIOS_CUENTA
        arqueo.append({
            "medio_pago": medio,
            "nombre": nombre_medio(medio),
            "es_cuenta_digital": es_cuenta,
            "apertura": round(fila["apertura"], 2),
            "ingresos": round(fila["ingresos"], 2),
            "egresos": round(fila["egresos"], 2),
            "esperado": round(fila["esperado"], 2),
            # Si la cuenta se movió pero se abrió sin saldo inicial, el esperado
            # no se puede comparar con el saldo de la app.
            "falta_saldo_inicial": bool(
                es_cuenta
                and not fila["apertura"]
                and (fila["ingresos"] or fila["egresos"])
            ),
        })
    return arqueo


def _es_posterior_a_apertura(db: Session, referencia_id: int, sucursal_id: int) -> bool:
    """Verifica si un ID de referencia es posterior a la última apertura de caja."""
    apertura = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "apertura",
            MovimientoCaja.medio_pago == None,
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
        if _es_apertura_de_caja(m):
            return m
    return None


def _obtener_monto_apertura(db: Session, sucursal_id: int = 1) -> float:
    """Obtiene el monto con el que se abrió el cajón en la sesión actual."""
    apertura = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == sucursal_id,
            MovimientoCaja.tipo == "apertura",
            MovimientoCaja.medio_pago == None,
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


def _iso_utc(dt: Optional[datetime]) -> Optional[str]:
    """ISO8601 en UTC con Z: la DB guarda datetimes naive en UTC y el front
    necesita saberlo para mostrar la hora argentina correcta."""
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.isoformat() + "Z"
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _movimientos_sesion_abierta(db: Session, sucursal_id: int = 1) -> List[MovimientoCaja]:
    """Movimientos de la sesión abierta, del más nuevo al más viejo, con su apertura.

    Recorre hacia atrás desde el último movimiento: el primer cierre total que
    encuentra cierra la ventana (no hay sesión abierta) y la apertura del cajón
    la cierra con ella, igual que recorre `obtener_saldo_por_medio`.
    """
    movimientos = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.sucursal_id == sucursal_id)
        .order_by(MovimientoCaja.id.desc())
        .all()
    )
    ventana: List[MovimientoCaja] = []
    for m in movimientos:
        if m.tipo == "cierre" and not m.medio_pago:
            return []
        ventana.append(m)
        if _es_apertura_de_caja(m):
            return ventana
    return []


def obtener_detalle_medio_sesion(
    db: Session,
    medio_pago: str,
    cierre_id: Optional[int] = None,
    sucursal_id: int = 1,
) -> dict:
    """Movimientos que componen el esperado de un medio de pago en una sesión.

    Sin `cierre_id` describe la sesión abierta; con él, la de ese cierre. El
    detalle sale del mismo rango de movimientos con el que se calcula el arqueo,
    así que la suma de los renglones coincide con el esperado de la fila.
    """
    from app.models.venta import Venta

    if cierre_id is not None:
        cierre, apertura = obtener_sesion_por_cierre(db, cierre_id, sucursal_id)
        movimientos = _movimientos_de_sesion(db, apertura, cierre.id, sucursal_id)
        saldos = _saldos_de_sesion(db, apertura, cierre.id, sucursal_id)
    else:
        movimientos = _movimientos_sesion_abierta(db, sucursal_id)
        if not movimientos:
            raise ValueError("No hay una sesión de caja abierta.")
        apertura = movimientos[-1]
        saldos = obtener_saldo_por_medio(db, sucursal_id)

    seleccion: List[tuple] = []
    for m in movimientos:
        if (m.medio_pago or "efectivo") != medio_pago:
            continue
        if m.tipo == "apertura":
            # La apertura del cajón se agrega aparte (es de la sesión, no un
            # movimiento dentro de ella); la de una cuenta digital sí cuenta.
            if not m.medio_pago:
                continue
            tipo = "apertura"
        elif m.tipo == "ingreso":
            tipo = "ingreso"
        elif m.tipo == "egreso":
            # En la sesión abierta se aplican las mismas exclusiones que
            # obtener_saldo_por_medio: un egreso que pertenece a otra sesión no
            # baja el esperado de esta.
            if cierre_id is None:
                if m.referencia_tipo == "retiro_cierre" and m.referencia_id is not None:
                    continue
                if m.referencia_tipo == "pago_proveedor" and m.sesion_cierre_id is not None:
                    continue
            tipo = "egreso"
        else:
            # cierre_parcial y cierre total son informativos, no mueven saldo
            continue
        seleccion.append((m, tipo))

    venta_ids = {
        m.referencia_id
        for m, _ in seleccion
        if m.referencia_tipo == "venta" and m.referencia_id
    }
    ventas = {}
    if venta_ids:
        for v in db.query(Venta).filter(Venta.id.in_(venta_ids)).all():
            ventas[v.id] = v

    filas: List[dict] = []
    for m, tipo in seleccion:
        venta = ventas.get(m.referencia_id) if m.referencia_tipo == "venta" else None
        filas.append({
            "id": m.id,
            "fecha": _iso_utc(m.created_at),
            "tipo": tipo,
            "monto": round(m.monto or 0.0, 2),
            "descripcion": m.descripcion or "",
            "venta_id": venta.id if venta else None,
            "numero": venta.numero if venta else None,
            "cliente": venta.cliente.nombre if venta and venta.cliente else None,
        })

    # La apertura del cajón es solo del efectivo: las cuentas digitales tienen
    # la suya propia, que sí viene como movimiento dentro de la sesión.
    if medio_pago == "efectivo":
        filas.append({
            "id": apertura.id,
            "fecha": _iso_utc(apertura.created_at),
            "tipo": "apertura",
            "monto": round(apertura.monto or 0.0, 2),
            "descripcion": "Apertura de caja",
            "venta_id": None,
            "numero": None,
            "cliente": None,
        })

    fila = saldos.get(medio_pago) or _fila_saldo()
    return {
        "medio_pago": medio_pago,
        "apertura": round(fila["apertura"], 2),
        "ingresos": round(fila["ingresos"], 2),
        "egresos": round(fila["egresos"], 2),
        "esperado": round(fila["esperado"], 2),
        "movimientos": filas,
    }
