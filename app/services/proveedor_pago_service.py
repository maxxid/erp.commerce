"""Servicio de cuentas corrientes con proveedores: deudas y pagos.

Es el análogo invertido de Cliente.saldo_cta_corriente, con una diferencia que
no existe del lado de los clientes: acá el pago puede o no tocar la caja.

Por qué importa la mitad de caja
--------------------------------
Si le pagás a un proveedor con plata del cajón, esa plata salió físicamente y
el esperado tiene que bajar, o el arqueo va a mostrar un faltante que en realidad
es un pago. Si le pagás con plata de afuera (un traspaso tuyo, un retiro de la
cuenta bancaria que no es del cajón), el pago existe contablemente pero NO puede
bajar el esperado del cajero, porque esa plata nunca estuvo en su cajón.

De ahí el campo afecta_arqueo en PagoProveedor. Cuando es True se genera un
MovimientoCaja espejo que sí participa del arqueo. Cuando es False no se toca
ningún saldo de caja.

Regla de seguridad: solo admin/encargado pueden registrar pagos que no tocan el
arqueo. Si el cajero que arquea también pudiera declarar "pagué con plata que no
está en mi cajón", el arqueo dejaría de poder distinguir un pago real de plata
faltante. Esa separación es la que hace que el arqueo sea verificable en vez de
meramente aparente.

El saldo de Proveedor es caché: recalcular_saldo() es el único que lo escribe y
siempre se deriva de las filas. Los pagos anulados no cuentan.
"""

from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.proveedor import Proveedor
from app.models.proveedor_pago import DeudaProveedor, PagoProveedor
from app.models.movimiento_caja import MovimientoCaja
from app.models.compra import Compra
from app.services.caja_service import (
    MEDIOS_INGRESO,
    caja_abierta,
    _exigir_sesion_arqueable,
    _recalcular_cierre,
)

ORIGENES = ("compra", "encargo", "manual")
ESTADOS_DEUDA = ("pendiente", "parcial", "cancelada")


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _redondear(valor: float) -> float:
    """Dos decimales, como el resto del sistema (Cliente.abonar usa round(...,2))."""
    return round(float(valor), 2)


# --------------------------------------------------------------------------
# Deudas
# --------------------------------------------------------------------------


def crear_deuda(
    db: Session,
    proveedor_id: int,
    monto: float,
    usuario_id: int,
    origen: str = "manual",
    compra_id: Optional[int] = None,
    detalle: str = "",
    fecha_vencimiento: Optional[datetime] = None,
    fecha_emision: Optional[datetime] = None,
) -> DeudaProveedor:
    """Registra una obligación con el proveedor.

    Con origen='compra' el vínculo a la compra es obligatorio: es lo que evita
    que una deuda quede apuntando a una compra que no existe.
    """
    if not proveedor_id:
        raise ValueError("Elegí un proveedor.")
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if proveedor is None:
        raise ValueError("El proveedor no existe.")

    monto = float(monto)
    if monto <= 0:
        raise ValueError("El monto de la deuda tiene que ser mayor a 0.")

    if origen not in ORIGENES:
        raise ValueError(f"Origen inválido. Opciones: {', '.join(ORIGENES)}")
    if origen == "compra" and not compra_id:
        raise ValueError("Una deuda de compra tiene que estar asociada a una compra.")
    if compra_id is not None:
        compra = db.query(Compra).filter(Compra.id == compra_id).first()
        if compra is None:
            raise ValueError("La compra no existe.")

    # Una compra no genera dos deudas: si ya tiene una, se devuelve la misma.
    # Así una compra reenviada o duplicada por red no duplica la deuda.
    if compra_id is not None:
        existente = (
            db.query(DeudaProveedor)
            .filter(DeudaProveedor.compra_id == compra_id)
            .first()
        )
        if existente is not None:
            return existente

    deuda = DeudaProveedor(
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        origen=origen,
        compra_id=compra_id,
        detalle=(detalle or "").strip() or None,
        monto_original=_redondear(monto),
        saldo=_redondear(monto),
        fecha_emision=fecha_emision or _ahora(),
        fecha_vencimiento=fecha_vencimiento,
        estado="pendiente",
    )
    db.add(deuda)
    db.flush()
    recalcular_saldo(db, proveedor_id)
    return deuda


def sincronizar_deuda_compra(db: Session, compra: Compra) -> Optional[DeudaProveedor]:
    """Crea o ajusta la deuda de una compra para que siempre cuadre con el total.

    Se llama cada vez que cambian los ítems o el estado de la compra. La deuda
    nace sola: el usuario no tiene que acordarse de cargarla.

    El ajuste es sobre monto_original, y el saldo se recalcula como
    total - pagado. Así, si la compra crece después de un pago parcial, la deuda
    crece sólo por la diferencia y lo ya pagado no se pisa.
    """
    if compra.estado == "anulada":
        # Una compra anulada no debe nada. Se cancela su deuda, pero sólo si
        # nadie pagó contra ella: si ya pagaron, el saldo es a favor del
        # proveedor y lo tiene que resolver una anulación de pago explícita.
        deuda = (
            db.query(DeudaProveedor)
            .filter(DeudaProveedor.compra_id == compra.id)
            .first()
        )
        if deuda is not None and deuda.estado != "cancelada":
            if deuda.pagada > 0:
                raise ValueError(
                    f"La compra {compra.numero} ya tiene pagos aplicados "
                    f"(${deuda.pagada:,.2f}). Anulá el pago antes de anular la compra."
                )
            anular_deuda(db, deuda.id, compra.usuario_id)
        return None

    if (compra.total or 0.0) <= 0:
        # Compra recién creada, todavía sin ítems: no hay nada que deber.
        return None

    deuda = (
        db.query(DeudaProveedor)
        .filter(DeudaProveedor.compra_id == compra.id)
        .first()
    )
    if deuda is None:
        return crear_deuda(
            db,
            proveedor_id=compra.proveedor_id,
            monto=compra.total,
            usuario_id=compra.usuario_id,
            origen="compra",
            compra_id=compra.id,
            detalle=f"Compra {compra.numero}",
            fecha_emision=compra.fecha,
        )

    # El total cambió (agregar o quitar ítems): se ajusta la deuda. Si el
    # pago ya cubría todo, el saldo queda negativo, que es un anticipo a favor
    # del comercio y el estado sigue siendo 'parcial' hasta que se compense.
    pagada = deuda.pagada
    if abs(pagada - deuda.monto_original) > 0.005 or abs(deuda.saldo - (compra.total - pagada)) > 0.005:
        deuda.monto_original = _redondear(compra.total)
        nuevo_saldo = _redondear(compra.total - pagada)
        deuda.saldo = nuevo_saldo
        if abs(nuevo_saldo) < 0.01:
            deuda.saldo = 0.0
            deuda.estado = "cancelada"
        else:
            deuda.estado = "parcial" if pagada > 0 else "pendiente"
        db.flush()
        recalcular_saldo(db, compra.proveedor_id)

    return deuda


def obtener_deuda(db: Session, deuda_id: int) -> DeudaProveedor:
    deuda = db.query(DeudaProveedor).filter(DeudaProveedor.id == deuda_id).first()
    if deuda is None:
        raise ValueError("La deuda no existe.")
    return deuda


def anular_deuda(db: Session, deuda_id: int, usuario_id: int) -> DeudaProveedor:
    """Anula una deuda, por ejemplo una compra que se cayó.

    Solo si no tiene pagos aplicados: si ya se le pagó, anular la deuda dejaría
    el pago flotando sin causa y el saldo mintiendo.
    """
    deuda = obtener_deuda(db, deuda_id)
    pagos = (
        db.query(PagoProveedor)
        .filter(PagoProveedor.deuda_id == deuda.id, PagoProveedor.anulado.is_(False))
        .count()
    )
    if pagos:
        raise ValueError(
            "La deuda tiene pagos aplicados. Anulá los pagos primero para que "
            "el saldo quede consistente."
        )
    deuda.estado = "cancelada"
    deuda.saldo = 0.0
    db.flush()
    recalcular_saldo(db, deuda.proveedor_id)
    return deuda


def listar_deudas(
    db: Session,
    proveedor_id: Optional[int] = None,
    estado: Optional[str] = None,
    solo_vencidas: bool = False,
) -> List[DeudaProveedor]:
    """Deudas ordenadas por vencimiento, con la más antigua primero."""
    q = db.query(DeudaProveedor)
    if proveedor_id:
        q = q.filter(DeudaProveedor.proveedor_id == proveedor_id)
    if estado:
        if estado not in ESTADOS_DEUDA:
            raise ValueError(f"Estado inválido. Opciones: {', '.join(ESTADOS_DEUDA)}")
        q = q.filter(DeudaProveedor.estado == estado)
    else:
        # Por defecto sacamos las canceladas: son ruido en el día a día.
        q = q.filter(DeudaProveedor.estado != "cancelada")
    if solo_vencidas:
        q = q.filter(
            DeudaProveedor.fecha_vencimiento.isnot(None),
            DeudaProveedor.fecha_vencimiento < _ahora(),
        )
    return q.order_by(
        DeudaProveedor.fecha_vencimiento.is_(None),
        DeudaProveedor.fecha_vencimiento,
        DeudaProveedor.id,
    ).all()


# --------------------------------------------------------------------------
# Pagos
# --------------------------------------------------------------------------


def registrar_pago(
    db: Session,
    proveedor_id: int,
    monto: float,
    usuario_id: int,
    medio_pago: str = "efectivo",
    deuda_id: Optional[int] = None,
    comprobante_nro: str = "",
    descripcion: str = "",
    afecta_arqueo: bool = True,
    cierre_id: Optional[int] = None,
    sucursal_id: int = 1,
    fecha: Optional[datetime] = None,
) -> PagoProveedor:
    """Registra un pago a proveedor y su efecto en la caja.

    Args:
        afecta_arqueo: True si la plata salió de la sesión de caja. Genera el
            MovimientoCaja espejo que baja el esperado. False si la plata vino
            de afuera: el pago existe y reduce la deuda, pero no toca ningún
            saldo de caja, así el arqueo del cajero sigue siendo verídico.
        cierre_id: sesión donde se registra el movimiento espejo. Obligatorio si
            afecta_arqueo y la caja ya está cerrada (conciliación posterior).

    Raises:
        ValueError: validaciones de monto, medio de pago, deuda y sesión.
    """
    monto = _redondear(monto)
    if monto <= 0:
        raise ValueError("El monto del pago tiene que ser mayor a 0.")

    if medio_pago not in MEDIOS_INGRESO:
        raise ValueError(f"Medio de pago inválido. Opciones: {', '.join(MEDIOS_INGRESO)}")

    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if proveedor is None:
        raise ValueError("El proveedor no existe.")

    deuda = None
    if deuda_id is not None:
        deuda = obtener_deuda(db, deuda_id)
        if deuda.proveedor_id != proveedor_id:
            raise ValueError("La deuda pertenece a otro proveedor.")
        if deuda.estado == "cancelada":
            raise ValueError("La deuda está cancelada. No se le pueden aplicar pagos.")
        if monto > deuda.saldo + 0.005:
            raise ValueError(
                f"El pago (${monto:,.2f}) supera el saldo de la deuda "
                f"(${deuda.saldo:,.2f}). Bajá el monto o asigná el excedente a "
                "otra deuda o como anticipo."
            )

    cierre = None
    if afecta_arqueo:
        if cierre_id is not None:
            cierre, _ = _exigir_sesion_arqueable(db, cierre_id, sucursal_id)
        elif not caja_abierta(db, sucursal_id):
            raise ValueError(
                "No hay caja abierta. Abrí la caja, o registrá el pago con "
                "afecta_arqueo=False si la plata vino de afuera."
            )

    pago = PagoProveedor(
        proveedor_id=proveedor_id,
        usuario_id=usuario_id,
        monto=monto,
        medio_pago=medio_pago,
        fecha=fecha or _ahora(),
        deuda_id=deuda.id if deuda else None,
        proveedor_nombre=proveedor.nombre,
        comprobante_nro=(comprobante_nro or "").strip() or None,
        descripcion=(descripcion or "").strip() or None,
        afecta_arqueo=bool(afecta_arqueo),
        sesion_cierre_id=cierre.id if cierre else None,
        anulado=False,
    )

    # El movimiento espejo existe solo si el pago toca la caja. Sin esto, un
    # pago con plata de afuera no genera ningún movimiento y el arqueo del
    # cajero queda intacto.
    if afecta_arqueo:
        texto = f"Pago a proveedor: {proveedor.nombre}"
        if descripcion.strip():
            texto += f": {descripcion.strip()}"
        movimiento = MovimientoCaja(
            tipo="egreso",
            monto=monto,
            descripcion=texto[:200],
            medio_pago=medio_pago,
            referencia_tipo="pago_proveedor",
            referencia_id=proveedor_id,
            sesion_cierre_id=cierre.id if cierre else None,
            usuario_id=usuario_id,
            sucursal_id=sucursal_id,
        )
        db.add(movimiento)
        db.flush()
        pago.movimiento_caja_id = movimiento.id

    db.add(pago)
    db.flush()

    if deuda is not None:
        _aplicar_a_deuda(db, deuda, monto)

    recalcular_saldo(db, proveedor_id)

    if cierre is not None:
        _recalcular_cierre(db, cierre, sucursal_id)

    return pago


def _aplicar_a_deuda(db: Session, deuda: DeudaProveedor, monto: float) -> None:
    """Descuenta el pago de la deuda y actualiza su estado."""
    nuevo_saldo = _redondear(deuda.saldo - monto)
    deuda.saldo = nuevo_saldo
    # Tolerancia de un centavo para no dejar deudas de $0.01 colgadas por
    # redondeos binarios de float.
    if abs(nuevo_saldo) < 0.01:
        deuda.saldo = 0.0
        deuda.estado = "cancelada"
    else:
        deuda.estado = "parcial"


def anular_pago(
    db: Session,
    pago_id: int,
    usuario_id: int,
    motivo: str = "",
) -> PagoProveedor:
    """Anula un pago: devuelve el saldo al proveedor y saca el egreso de caja.

    No borra la fila. Un pago anulado tiene que quedar porque forma parte del
    historial de caja, y porque saber qué se anuló y cuándo es justamente lo que
    hace auditable un arqueo.
    """
    pago = db.query(PagoProveedor).filter(PagoProveedor.id == pago_id).first()
    if pago is None:
        raise ValueError("El pago no existe.")
    if pago.anulado:
        raise ValueError("El pago ya está anulado.")

    if pago.deuda_id:
        deuda = obtener_deuda(db, pago.deuda_id)
        # Sólo se devuelve a la deuda si el pago se aplicó a una deuda. Un pago
        # sin deuda asociada nunca bajó el saldo de ninguna.
        _aplicar_a_deuda(db, deuda, -pago.monto)

    if pago.afecta_arqueo and pago.movimiento_caja_id:
        movimiento = (
            db.query(MovimientoCaja)
            .filter(MovimientoCaja.id == pago.movimiento_caja_id)
            .first()
        )
        if movimiento is not None:
            if movimiento.sesion_cierre_id:
                cierre, _ = _exigir_sesion_arqueable(
                    db, movimiento.sesion_cierre_id, movimiento.sucursal_id
                )
                db.delete(movimiento)
                db.flush()
                _recalcular_cierre(db, cierre, movimiento.sucursal_id)
            else:
                # Sesión abierta: el movimiento sigue formando parte del
                # saldo de hoy, así que se borra como cualquier egreso.
                db.delete(movimiento)

    pago.anulado = True
    pago.anulado_por_id = usuario_id
    pago.anulado_at = _ahora()
    pago.motivo_anulacion = (motivo or "").strip() or None
    db.flush()

    recalcular_saldo(db, pago.proveedor_id)
    return pago


def listar_pagos(
    db: Session,
    proveedor_id: Optional[int] = None,
    solo_activos: bool = True,
    solo_sin_verificar: bool = False,
) -> List[PagoProveedor]:
    q = db.query(PagoProveedor)
    if proveedor_id:
        q = q.filter(PagoProveedor.proveedor_id == proveedor_id)
    if solo_activos:
        q = q.filter(PagoProveedor.anulado.is_(False))
    pagos = q.order_by(PagoProveedor.fecha.desc(), PagoProveedor.id.desc()).all()
    if solo_sin_verificar:
        pagos = [p for p in pagos if not p.verificado]
    return pagos


def pagos_sin_verificar(db: Session, sucursal_id: Optional[int] = None) -> List[PagoProveedor]:
    """Pagos sin causa o sin comprobante: los que el dueño tiene que mirar.

    Un pago sin deuda asociada es un anticipo, algo legítimo. Un pago sin
    comprobante es plata que salió sin respaldo. Ambos son válidos (el cajero
    no puede quedar trabado en el mostrador) pero quedan acá para revisar.
    """
    return listar_pagos(db, solo_sin_verificar=True)


# --------------------------------------------------------------------------
# Saldo
# --------------------------------------------------------------------------


def recalcular_saldo(db: Session, proveedor_id: int) -> float:
    """Recalcula el saldo cacheado del proveedor desde las filas reales.

    Saldo = suma de deudas pendientes - suma de pagos activos. Un anticipo
    (pago sin deuda) hace que el saldo baje de cero, que es lo correcto: le
    debemos menos que cero, o sea nos debe el proveedor.

    Esta función es la única que escribe en Proveedor.saldo_cta_corriente.
    """
    total_deudas = (
        db.query(func.coalesce(func.sum(DeudaProveedor.saldo), 0.0))
        .filter(DeudaProveedor.proveedor_id == proveedor_id)
        .scalar()
    )
    total_pagos = (
        db.query(func.coalesce(func.sum(PagoProveedor.monto), 0.0))
        .filter(
            PagoProveedor.proveedor_id == proveedor_id,
            PagoProveedor.anulado.is_(False),
        )
        .scalar()
    )
    saldo = _redondear(total_deudas - total_pagos)

    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if proveedor is not None:
        proveedor.saldo_cta_corriente = saldo
        db.flush()
    return saldo


def estado_cuenta(db: Session, proveedor_id: int) -> dict:
    """Estado de cuenta: qué se le debe, qué se le pagó y qué falta."""
    proveedor = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if proveedor is None:
        raise ValueError("El proveedor no existe.")

    recalcular_saldo(db, proveedor_id)
    deudas = listar_deudas(db, proveedor_id=proveedor_id)
    pagos = listar_pagos(db, proveedor_id=proveedor_id)

    total_deudas = sum(d.monto_original for d in deudas)
    total_pagado = sum(p.monto for p in pagos)
    vencidas = [d for d in deudas if d.fecha_vencimiento and d.fecha_vencimiento < _ahora()]

    return {
        "proveedor": {
            "id": proveedor.id,
            "nombre": proveedor.nombre,
            "cuit": proveedor.cuit,
        },
        "saldo": proveedor.saldo_cta_corriente,
        "total_deudas": _redondear(total_deudas),
        "total_pagado": _redondear(total_pagado),
        "deudas_pendientes": len([d for d in deudas if d.saldo > 0]),
        "deudas_vencidas": len(vencidas),
        "pagos_sin_verificar": len([p for p in pagos if not p.verificado]),
    }