"""Servicio de Recargas: recargas de dinero digital (SUBE, saldo, etc.).

Modelo de negocio:
- El cliente pide cargar $1.000 y paga $1.100 (10% adicional).
- El negocio carga $1.000 desde su cuenta digital (MercadoPago / SmartPoint).
- Por eso la recarga genera: venta por $1.100, costo $1.000 (el adicional es
  margen) y un EGRESO real de caja de $1.000 por la cuenta de salida.

La configuración vive en la tabla `configuraciones` para poder ajustarla sin
tocar código (Ajustes → Servicio de Recargas).
"""

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.producto import Producto
from app.models.recarga import Recarga
from app.models.venta import Venta, VentaItem
from app.services import caja_service, config_service

CLAVE_MONTO_BASE = "recarga_monto_base"
CLAVE_ADICIONAL_PCT = "recarga_adicional_pct"
CLAVE_MEDIO_PAGO_CARGA = "recarga_medio_pago_carga"
CLAVE_PRODUCTO_ID = "recarga_producto_id"

DEFAULT_MONTO_BASE = 1000.0
DEFAULT_ADICIONAL_PCT = 10.0
DEFAULT_MEDIO_PAGO_CARGA = "smartpoint"

MEDIOS_PAGO_CARGA = [
    "smartpoint",
    "mercadopago_qr",
    "mercadopago_pos",
    "qr_interop",
    "debito",
    "credito",
    "transferencia",
    "efectivo",
]


def get_config(db: Session) -> dict:
    """Devuelve la configuración de recargas con defaults sensatos."""
    try:
        monto_base = float(config_service.get_config(db, CLAVE_MONTO_BASE) or DEFAULT_MONTO_BASE)
    except (TypeError, ValueError):
        monto_base = DEFAULT_MONTO_BASE

    try:
        adicional_pct = float(config_service.get_config(db, CLAVE_ADICIONAL_PCT) or DEFAULT_ADICIONAL_PCT)
    except (TypeError, ValueError):
        adicional_pct = DEFAULT_ADICIONAL_PCT

    producto_id = config_service.get_config(db, CLAVE_PRODUCTO_ID)
    try:
        producto_id = int(producto_id) if producto_id else None
    except (TypeError, ValueError):
        producto_id = None

    medio_pago_carga = (
        config_service.get_config(db, CLAVE_MEDIO_PAGO_CARGA) or DEFAULT_MEDIO_PAGO_CARGA
    )

    return {
        "monto_base": monto_base,
        "adicional_pct": adicional_pct,
        "medio_pago_carga": medio_pago_carga,
        "producto_id": producto_id,
        "precio_venta_unidad": precio_unidad(monto_base, adicional_pct),
        "adicional_unidad": round(monto_base * adicional_pct / 100, 2),
    }


def set_config(
    db: Session,
    monto_base: Optional[float] = None,
    adicional_pct: Optional[float] = None,
    medio_pago_carga: Optional[str] = None,
    producto_id: Optional[int] = None,
) -> dict:
    """Guarda la configuración. Solo cambia lo que viene informado."""
    if monto_base is not None:
        if monto_base <= 0:
            raise ValueError("El monto base debe ser mayor a 0")
        config_service.set_config(db, CLAVE_MONTO_BASE, str(float(monto_base)),
                                  "Monto de cada unidad de recarga (ej: 1000)")
    if adicional_pct is not None:
        if adicional_pct < 0 or adicional_pct > 100:
            raise ValueError("El adicional debe estar entre 0 y 100")
        config_service.set_config(db, CLAVE_ADICIONAL_PCT, str(float(adicional_pct)),
                                  "Porcentaje de adicional sobre la recarga")
    if medio_pago_carga is not None:
        if medio_pago_carga not in MEDIOS_PAGO_CARGA:
            raise ValueError(f"Medio de pago inválido. Opciones: {', '.join(MEDIOS_PAGO_CARGA)}")
        config_service.set_config(db, CLAVE_MEDIO_PAGO_CARGA, medio_pago_carga,
                                  "De qué cuenta sale el dinero para cargar")
    if producto_id is not None:
        producto = db.query(Producto).filter(Producto.id == producto_id).first()
        if not producto:
            raise ValueError("El producto de recarga no existe")
        producto.es_recarga = True
        producto.controla_stock = False
        db.commit()
        config_service.set_config(db, CLAVE_PRODUCTO_ID, str(producto_id),
                                  "Producto que representa la recarga en el POS")
    return get_config(db)


def precio_unidad(monto_base: float, adicional_pct: float) -> float:
    """Precio de venta de una unidad de recarga: base + adicional (1100)."""
    return round(monto_base * (1 + adicional_pct / 100), 2)


def calcular(unidades: float, cfg: Optional[dict] = None) -> dict:
    """Desglose de una recarga por unidades, para mostrarlo en el POS."""
    cfg = cfg or {}
    base = cfg.get("monto_base", DEFAULT_MONTO_BASE)
    pct = cfg.get("adicional_pct", DEFAULT_ADICIONAL_PCT)
    unidades = max(float(unidades or 0), 0)
    monto_cargado = round(base * unidades, 2)
    adicional = round(monto_cargado * pct / 100, 2)
    return {
        "unidades": unidades,
        "monto_cargado": monto_cargado,
        "adicional_pct": pct,
        "adicional_monto": adicional,
        "total_cobrar": round(monto_cargado + adicional, 2),
    }


def producto_recarga(db: Session) -> Optional[Producto]:
    """Producto configurado como servicio de recarga, si existe."""
    cfg = get_config(db)
    if cfg["producto_id"]:
        producto = db.query(Producto).filter(Producto.id == cfg["producto_id"]).first()
        if producto:
            return producto
    return db.query(Producto).filter(Producto.es_recarga == True, Producto.activo == True).first()


def registrar_venta_recarga(
    db: Session,
    venta: Venta,
    item: VentaItem,
    producto: Producto,
    usuario_id: int,
    cfg: Optional[dict] = None,
) -> Optional[Recarga]:
    """Registra la recarga de un ítem de venta ya confirmado.

    - Setea el costo del ítem al monto realmente cargado (así el adicional queda
      como margen en el Dashboard).
    - Genera el EGRESO de caja por el dinero que sale de la cuenta digital.
    """
    cfg = cfg or get_config(db)
    unidades = float(item.cantidad or 0)
    if unidades <= 0:
        return None

    monto_base = float(cfg["monto_base"])
    monto_cargado = round(monto_base * unidades, 2)
    adicional = round(item.subtotal - monto_cargado, 2)

    item.precio_costo = monto_base

    recarga = Recarga(
        venta_id=venta.id,
        venta_item_id=item.id,
        producto_id=producto.id,
        unidades=unidades,
        monto_base=monto_base,
        monto_cargado=monto_cargado,
        adicional_pct=cfg["adicional_pct"],
        adicional_monto=adicional,
        total_cobrado=item.subtotal,
        medio_pago_cobro=venta.medio_pago,
        medio_pago_carga=cfg["medio_pago_carga"],
        estado="confirmada",
        usuario_id=usuario_id,
        sucursal_id=venta.sucursal_id,
        fecha=venta.fecha,
    )
    db.add(recarga)
    db.flush()

    caja_service.registrar_egreso(
        db,
        monto=monto_cargado,
        descripcion=f"Recarga {producto.nombre} (venta {venta.numero})",
        usuario_id=usuario_id,
        referencia_tipo="recarga",
        referencia_id=recarga.id,
        sucursal_id=venta.sucursal_id,
        medio_pago=cfg["medio_pago_carga"],
    )

    db.commit()
    db.refresh(recarga)
    return recarga


def anular_recargas(db: Session, venta: Venta, usuario_id: int) -> int:
    """Revierte las recargas de una venta anulada: marca y devuelve el dinero."""
    recargas = (
        db.query(Recarga)
        .filter(Recarga.venta_id == venta.id, Recarga.estado == "confirmada")
        .all()
    )
    for r in recargas:
        r.estado = "anulada"
        caja_service.registrar_ingreso(
            db,
            monto=r.monto_cargado,
            descripcion=f"Anulación recarga (venta {venta.numero})",
            usuario_id=usuario_id,
            referencia_tipo="recarga_anulada",
            referencia_id=r.id,
            sucursal_id=venta.sucursal_id,
            medio_pago=r.medio_pago_carga or "efectivo",
        )
    if recargas:
        db.commit()
    return len(recargas)


def resumen(db: Session, desde: datetime, hasta: datetime, sucursal_id: Optional[int] = None) -> dict:
    """Totales de recargas confirmadas en el período, por día y por medio de pago."""
    query = db.query(Recarga).filter(
        Recarga.estado == "confirmada",
        Recarga.fecha >= desde,
        Recarga.fecha < hasta,
    )
    if sucursal_id:
        query = query.filter(Recarga.sucursal_id == sucursal_id)

    recargas = query.all()

    por_dia: dict = {}
    por_medio: dict = {}
    for r in recargas:
        dia = (r.fecha or datetime.now()).strftime("%Y-%m-%d")
        acc = por_dia.setdefault(dia, {
            "fecha": dia, "unidades": 0.0, "cargado": 0.0, "cobrado": 0.0, "ganancia": 0.0, "recargas": 0,
        })
        acc["unidades"] += r.unidades
        acc["cargado"] += r.monto_cargado
        acc["cobrado"] += r.total_cobrado
        acc["ganancia"] += r.ganancia
        acc["recargas"] += 1

        medio = r.medio_pago_cobro or "efectivo"
        m = por_medio.setdefault(medio, {"medio_pago": medio, "cargado": 0.0, "cobrado": 0.0, "recargas": 0})
        m["cargado"] += r.monto_cargado
        m["cobrado"] += r.total_cobrado
        m["recargas"] += 1

    def _redondear(d):
        return {k: (round(v, 2) if isinstance(v, float) else v) for k, v in d.items()}

    dias = [_redondear(v) for v in sorted(por_dia.values(), key=lambda x: x["fecha"], reverse=True)]
    medios = [
        _redondear(v) for v in sorted(por_medio.values(), key=lambda x: x["cobrado"], reverse=True)
    ]

    return {
        "totales": {
            "unidades": round(sum(r.unidades for r in recargas), 2),
            "monto_cargado": round(sum(r.monto_cargado for r in recargas), 2),
            "total_cobrado": round(sum(r.total_cobrado for r in recargas), 2),
            "ganancia": round(sum(r.ganancia for r in recargas), 2),
            "recargas": len(recargas),
        },
        "por_dia": dias,
        "por_medio_pago": medios,
    }
