"""Servicio de integración con AFIP para Factura Electrónica.

Usa pyafipws (WSFEv1) para autenticación (WSAA) y emisión de
facturas (FECAESolicitar). La configuración se lee de la tabla
configuraciones (configurable desde UI) con fallback a env vars.
"""

import os
import logging
import tempfile
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.factura_electronica import FacturaElectronica
from app.models.venta import Venta
from app.models.cliente import Cliente
from app.services.config_service import get_afip_config

logger = logging.getLogger(__name__)

_token_cache = {"token": None, "sign": None, "expires": None}


def _get_afip_config(db: Session) -> dict:
    return get_afip_config(db)


def _get_wsaa_url(mode: str) -> str:
    if mode == "production":
        return "https://wsaa.afip.gov.ar/ws/services/LoginCms"
    return "https://wsaahomo.afip.gov.ar/ws/services/LoginCms"


def _get_wsfe_url(mode: str) -> str:
    if mode == "production":
        return "https://servicios1.afip.gov.ar/wsfev1/service.asmx"
    return "https://wswhomo.afip.gov.ar/wsfev1/service.asmx"


def _autenticar(db: Session) -> tuple[str, str]:
    """Autentica contra WSAA y devuelve (token, sign)."""
    global _token_cache

    now = datetime.utcnow()
    if _token_cache["token"] and _token_cache["expires"] and now < _token_cache["expires"]:
        return _token_cache["token"], _token_cache["sign"]

    cfg = _get_afip_config(db)
    from pyafipws.wsaa import WSAA

    wsaa = WSAA()
    wsaa.Conectar("", _get_wsaa_url(cfg["mode"]))

    # Escribir cert y key a archivos temporales
    cert_data = cfg.get("cert", "")
    key_data = cfg.get("key", "")
    cert_path = key_path = ""

    if cert_data:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".crt", delete=False) as f:
            f.write(cert_data)
            cert_path = f.name
    else:
        cert_path = os.getenv("AFIP_CERT", "")

    if key_data:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
            f.write(key_data)
            key_path = f.name
    else:
        key_path = os.getenv("AFIP_KEY", "")

    if not cert_path or not os.path.exists(cert_path):
        raise ValueError("AFIP certificado no configurado. Configurarlo en Ajustes > AFIP.")
    if not key_path or not os.path.exists(key_path):
        raise ValueError("AFIP clave privada no configurada. Configurarla en Ajustes > AFIP.")

    t = wsaa.Autenticar("wsfe", cert_path, key_path)
    if not t:
        raise RuntimeError(f"Error WSAA: {wsaa.ErrorMsg}")

    token = wsaa.Token
    sign = wsaa.Sign
    _token_cache["token"] = token
    _token_cache["sign"] = sign
    _token_cache["expires"] = now + timedelta(hours=11)

    # Limpiar archivos temporales
    try:
        if cert_data and os.path.exists(cert_path):
            os.unlink(cert_path)
        if key_data and os.path.exists(key_path):
            os.unlink(key_path)
    except OSError:
        pass

    logger.info("AFIP WSAA autenticado exitosamente")
    return token, sign


def _map_tipo_doc(doc_tipo: str | None) -> int:
    mapping = {"DNI": 96, "CUIT": 80, "CUIL": 86, "CI": 90, "LE": 89, "LC": 88}
    return mapping.get(doc_tipo or "", 99)


def emitir_factura(db: Session, venta: Venta) -> FacturaElectronica:
    """Emite Factura Electrónica ante AFIP para una venta confirmada."""
    cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first() if venta.cliente_id else None
    cfg = _get_afip_config(db)

    if cliente and cliente.numero_documento and cliente.tipo_documento == "CUIT":
        tipo_cbte = 1  # Factura A
    else:
        tipo_cbte = 11  # Factura C

    tipo_doc = _map_tipo_doc(cliente.tipo_documento if cliente else None)
    nro_doc = cliente.numero_documento if cliente and cliente.numero_documento else "0"

    neto = round(venta.total / 1.21, 2)
    iva = round(venta.total - neto, 2)

    fe = FacturaElectronica(
        venta_id=venta.id,
        venta_numero=venta.numero,
        tipo=str(tipo_cbte),
        punto_venta=cfg["pto_vta"],
        total=venta.total,
        neto=neto,
        iva=iva,
        tipo_doc_comprador=tipo_doc,
        nro_doc_comprador=nro_doc,
        estado="pendiente",
    )
    db.add(fe)
    db.flush()

    if not cfg["cert"] and not os.getenv("AFIP_CERT"):
        fe.estado = "pendiente"
        fe.observaciones = "AFIP no configurado. Ir a Ajustes > AFIP."
        db.commit()
        logger.warning(f"FE #{fe.id}: pendiente por falta de certificado AFIP")
        return fe

    try:
        _emitir_con_afip(db, fe, venta, tipo_cbte, tipo_doc, nro_doc, cfg)
    except Exception as e:
        fe.estado = "rechazada"
        fe.error_message = str(e)
        db.commit()
        logger.error(f"FE #{fe.id}: rechazada — {e}")

    return fe


def _emitir_con_afip(db, fe, venta, tipo_cbte, tipo_doc, nro_doc, cfg):
    from pyafipws.wsfev1 import WSFEv1

    token, sign = _autenticar(db)

    wsfe = WSFEv1()
    wsfe.Conectar("", _get_wsfe_url(cfg["mode"]))
    wsfe.Cuit = cfg["cuit"]
    wsfe.SetTicketAcceso(token, sign)

    ultimo = wsfe.CompUltimoAutorizado(cfg["pto_vta"], tipo_cbte)
    if ultimo is None:
        raise RuntimeError(f"No se pudo obtener último comprobante: {wsfe.ErrMsg}")

    numero_fiscal = (ultimo or 0) + 1
    fecha = venta.fecha.strftime("%Y%m%d") if venta.fecha else datetime.now().strftime("%Y%m%d")

    wsfe.CrearFactura(
        concepto=1,
        tipo_doc=tipo_doc,
        nro_doc=nro_doc,
        tipo_cbte=tipo_cbte,
        punto_vta=cfg["pto_vta"],
        cbte_desde=numero_fiscal,
        cbte_hasta=numero_fiscal,
        cbte_fch=fecha,
        imp_total=fe.total,
        imp_tot_conc=0,
        imp_neto=fe.neto,
        imp_op_ex=0,
        imp_iva=fe.iva,
        imp_trib=0,
        moneda_id="PES",
        moneda_cotiz=1,
    )

    wsfe.AgregarIva(Id=5, BaseImp=fe.neto, Importe=fe.iva)

    for item in venta.items or []:
        producto = item.producto
        nombre = producto.nombre if producto else f"Producto #{item.producto_id}"
        wsfe.AgregarItem(
            u_mx=1, cod_mx=str(item.producto_id),
            ds=nombre[:200], qty=item.cantidad,
            precio=item.precio_unitario, bonif=0.0, desp=None,
        )

    resultado = wsfe.FECAESolicitar()
    if resultado is None:
        errores = []
        for err in getattr(wsfe, "Errores", []) or []:
            errores.append(f"{err.Codigo}: {err.Descripcion}")
        for obs in getattr(wsfe, "Observaciones", []) or []:
            errores.append(f"Obs {obs.Codigo}: {obs.Descripcion}")
        raise RuntimeError(f"AFIP rechazó la factura: {'; '.join(errores)}")

    fe.numero_fiscal = numero_fiscal
    fe.cae = wsfe.CAE
    if wsfe.Vencimiento:
        fe.vencimiento_cae = datetime.strptime(str(wsfe.Vencimiento), "%Y%m%d")
    fe.resultado = wsfe.Resultado
    fe.estado = "emitida" if wsfe.Resultado == "A" else "rechazada"
    fe.emitted_at = datetime.utcnow()

    if wsfe.Resultado != "A":
        obs = []
        for o in getattr(wsfe, "Observaciones", []) or []:
            obs.append(f"{o.Codigo}: {o.Descripcion}")
        fe.error_message = "; ".join(obs)

    db.commit()
    logger.info(f"FE #{fe.id}: emitida CAE={wsfe.CAE} resultado={wsfe.Resultado}")
