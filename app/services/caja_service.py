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


def nombre_medio(medio_pago: Optional[str]) -> str:
    """Nombre legible del medio de pago."""
    if not medio_pago:
        return "Efectivo"
    return MEDIOS_INGRESO.get(medio_pago, medio_pago)


def _es_apertura_de_caja(m: MovimientoCaja) -> bool:
    """True si el movimiento es la apertura de la sesión (cajón)."""
    return m.tipo == "apertura" and not m.medio_pago


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
        if _es_apertura_de_caja(m):
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
        if _es_apertura_de_caja(m):
            apertura = m
            break
    if apertura is None:
        return False
    if _es_apertura_del_dia_actual(apertura.created_at):
        return False

    desglose = obtener_resumen_por_medio_pago(db, sucursal_id)
    total = desglose.get("saldo_medios_total", desglose.get("saldo_total"))
    desc = f"Cierre automático por cambio de día. Total esperado: ${total:,.2f}"
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
            fila = saldos.setdefault(
                "efectivo",
                {"apertura": 0.0, "ingresos": 0.0, "egresos": 0.0, "esperado": 0.0},
            )
            fila["apertura"] += m.monto or 0.0
            break

        if m.tipo == "apertura" and m.medio_pago:
            # Saldo inicial de una cuenta digital
            fila = saldos.setdefault(
                m.medio_pago,
                {"apertura": 0.0, "ingresos": 0.0, "egresos": 0.0, "esperado": 0.0},
            )
            fila["apertura"] += m.monto or 0.0
        elif m.tipo == "ingreso":
            fila = saldos.setdefault(
                m.medio_pago or "efectivo",
                {"apertura": 0.0, "ingresos": 0.0, "egresos": 0.0, "esperado": 0.0},
            )
            fila["ingresos"] += m.monto or 0.0
        elif m.tipo == "egreso":
            fila = saldos.setdefault(
                m.medio_pago or "efectivo",
                {"apertura": 0.0, "ingresos": 0.0, "egresos": 0.0, "esperado": 0.0},
            )
            fila["egresos"] += m.monto or 0.0
        # cierre_parcial es informativo, no afecta el saldo

    for fila in saldos.values():
        fila["esperado"] = fila["apertura"] + fila["ingresos"] - fila["egresos"]

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

    return {
        "abierta": abierta,
        "saldo_actual": saldo_efectivo,
        "saldo_efectivo": saldo_efectivo,
        "saldos_cuentas": saldos_cuentas,
        "saldo_cuenta_total": sum(saldos_cuentas.values()),
        "saldo_total": saldo_efectivo + sum(saldos_cuentas.values()),
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
        if _es_apertura_de_caja(m):
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
    }


def _construir_arqueo_por_medio(db: Session, sucursal_id: int = 1) -> List[dict]:
    """Arma la lista de medios a arquear con su saldo esperado.

    Incluye siempre efectivo, débito, crédito y transferencia, más las cuentas
    digitales (SmartPoint, MP, etc.) que tengan movimiento o saldo inicial en la
    sesión. Cada medio se cuadra por separado: el saldo de una cuenta digital
    nunca se compensa con el del cajón.
    """
    saldos = obtener_saldo_por_medio(db, sucursal_id)

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
        fila = saldos.get(medio, {"apertura": 0.0, "ingresos": 0.0, "egresos": 0.0, "esperado": 0.0})
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
