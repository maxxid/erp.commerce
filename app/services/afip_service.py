"""Servicio de integración con AFIP para Factura Electrónica usando zeep.

Usa zeep (cliente SOAP) para autenticación (WSAA) y emisión de
facturas (FECAESolicitar). La configuración se lee de la tabla
configuraciones (configurable desde UI) con fallback a env vars.

Instalación: pip install zeep
"""

import os
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from urllib.request import urlretrieve

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


def _get_wsaa_wsdl(mode: str) -> str:
    if mode == "production":
        return "https://wsaa.afip.gov.ar/ws/services/LoginCms?wsdl"
    return "https://wsaahomo.afip.gov.ar/ws/services/LoginCms?wsdl"


def _get_wsfe_wsdl(mode: str) -> str:
    if mode == "production":
        return "https://servicios1.afip.gov.ar/wsfev1/service.asmx?wsdl"
    return "https://wswhomo.afip.gov.ar/wsfev1/service.asmx?wsdl"


def _dump_xml(obj, filename):
    """Debug: guardar XML de request/response."""
    with open(filename, 'w') as f:
        f.write(str(obj))


def _autenticar_zeep(db: Session) -> tuple[str, str]:
    """Autentica contra WSAA usando zeep y devuelve (token, sign)."""
    global _token_cache

    now = datetime.utcnow()
    if _token_cache["token"] and _token_cache["expires"] and now < _token_cache["expires"]:
        return _token_cache["token"], _token_cache["sign"]

    cfg = _get_afip_config(db)

    from zeep import Client
    from zeep.transports import Transport
    from requests import Session

    session = Session()
    transport = Transport(session=session)
    client = Client(wsdl=_get_wsaa_wsdl(cfg["mode"]), transport=transport)

    cert_path = cfg.get("cert", "") or os.getenv("AFIP_CERT", "")
    key_path = cfg.get("key", "") or os.getenv("AFIP_KEY", "")

    if cert_path and os.path.exists(cert_path):
        session.cert = cert_path
    if key_path and os.path.exists(key_path):
        pass

    if not cert_path or not os.path.exists(cert_path):
        raise ValueError("AFIP certificado no configurado. Configurarlo en Ajustes > AFIP.")
    if not key_path or not os.path.exists(key_path):
        raise ValueError("AFIP clave privada no configurada. Configurarla en Ajustes > AFIP.")

    params = {
        'in0': open(cert_path).read(),
        'in1': open(key_path).read(),
        'in2': '',
        'in3': 'wsfe',
    }

    try:
        result = client.service.loginCms(**params)
        token = result.get('token', '')
        sign = result.get('sign', '')
        if not token or not sign:
            raise RuntimeError(f"WSAA no retornó token/sign: {result}")
    except Exception as e:
        raise RuntimeError(f"Error en WSAA loginCms: {e}")

    _token_cache["token"] = token
    _token_cache["sign"] = sign
    _token_cache["expires"] = now + timedelta(hours=11)

    logger.info("AFIP WSAA autenticado exitosamente (zeep)")
    return token, sign


def _map_tipo_doc(doc_tipo: str | None) -> int:
    mapping = {"DNI": 96, "CUIT": 80, "CUIL": 86, "CI": 90, "LE": 89, "LC": 88}
    return mapping.get(doc_tipo or "", 99)


def _es_cliente_responsable_inscripto(cliente: Optional[Cliente]) -> bool:
    if not cliente:
        return False
    return bool(
        cliente.numero_documento
        and cliente.tipo_documento == "CUIT"
    )


def _obtener_ultimo_comprobante(db: Session, wsfe_client, tipo_cbte: int, cfg: dict) -> int:
    """Obtiene el último número de comprobante autorizado."""
    try:
        result = wsfe_client.service.FECompUltimoAuthorize(
            PtoVta=cfg["pto_vta"],
            CbteTipo=tipo_cbte
        )
        if result and hasattr(result, 'FeCabResp'):
            return result.FeCabResp.get('CbteNro', 0)
        return 0
    except Exception as e:
        logger.warning(f"No se pudo obtener último comprobante: {e}")
        return 0


def _emitir_factura_zeep(db: Session, fe: FacturaElectronica, venta: Venta, tipo_cbte: int, cfg: dict):
    """Emite la factura usando zeep directamente."""
    from zeep import Client
    from zeep.transports import Transport
    from requests import Session

    token, sign = _autenticar_zeep(db)

    session = Session()
    if cfg.get("cert") and os.path.exists(cfg["cert"]):
        session.cert = cfg["cert"]
    transport = Transport(session=session)
    client = Client(wsdl=_get_wsfe_wsdl(cfg["mode"]), transport=transport)

    ultimo = _obtener_ultimo_comprobante(db, client, tipo_cbte, cfg)
    numero_fiscal = (ultimo or 0) + 1
    fecha = venta.fecha.strftime("%Y%m%d") if venta.fecha else datetime.now().strftime("%Y%m%d")

    tipo_doc = _map_tipo_doc(venta.cliente.tipo_documento if venta.cliente else None)
    nro_doc = venta.cliente.numero_documento if venta.cliente and venta.cliente.numero_documento else "0"

    iva_id = 5 if tipo_cbte == 1 else 10

    request = {
        'FeCabReq': {
            'CantReg': 1,
            'PtoVta': cfg["pto_vta"],
            'CbteTipo': tipo_cbte,
        },
        'FeDetReq': [{
            'FECAEDetRequest': {
                'DocNro': nro_doc,
                'DocTipo': tipo_doc,
                'CbteDesde': numero_fiscal,
                'CbteHasta': numero_fiscal,
                'CbteFch': fecha,
                'ImpTotal': round(fe.total, 2),
                'ImpTotConc': 0,
                'ImpNeto': round(fe.neto, 2),
                'ImpIva': round(fe.iva, 2),
                'ImpTrib': 0,
                'MonId': 'PES',
                'MonCotiz': 1,
                'Iva': [{
                    'BaseImp': round(fe.neto, 2),
                    'Id': iva_id,
                    'Importe': round(fe.iva, 2),
                }],
            }
        }]
    }

    try:
        result = client.service.FECAESolicitar(
            Auth={'Token': token, 'Sign': sign, 'Cuit': cfg["cuit"]},
            FeCAEReq=request
        )
    except Exception as e:
        raise RuntimeError(f"Error en FECAESolicitar: {e}")

    if hasattr(result, 'FeDetResp') and result.FeDetResp:
        det = result.FeDetResp[0].FECAEDetResponse
        fe.cae = str(det.get('CAE', ''))
        fe.numero_fiscal = det.get('CbteDesde', numero_fiscal)
        if hasattr(det, 'CAEFchVto') and det.CAEFchVto:
            try:
                fe.vencimiento_cae = datetime.strptime(str(det.CAEFchVto), "%Y%m%d")
            except:
                pass

    if hasattr(result, 'FeCabResp'):
        cab = result.FeCabResp
        fe.resultado = cab.get('Resultado', 'R')
        fe.estado = "emitida" if cab.get('Resultado') == 'A' else "rechazada"

        if cab.get('Resultado') != 'A':
            errores = []
            if hasattr(result, 'Errors') and result.Errors:
                for err in result.Errors:
                    if hasattr(err, 'Code') and hasattr(err, 'Msg'):
                        errores.append(f"{err.Code}: {err.Msg}")
            fe.error_message = "; ".join(errores) if errores else "Rechazada por AFIP"
    else:
        fe.resultado = 'R'
        fe.estado = 'rechazada'
        fe.error_message = "AFIP no retornó respuesta válida"

    if hasattr(result, 'Observaciones') and result.Observaciones:
        obs = []
        for o in result.Observaciones:
            if hasattr(o, 'Code') and hasattr(o, 'Msg'):
                obs.append(f"{o.Code}: {o.Msg}")
        if fe.error_message:
            fe.error_message += " | Observaciones: " + "; ".join(obs)
        else:
            fe.error_message = "; ".join(obs)

    fe.emitted_at = datetime.utcnow()
    db.commit()
    logger.info(f"FE #{fe.id}: resultado={fe.resultado} CAE={fe.cae}")


def emitir_factura(db: Session, venta: Venta, afip_cuit: str = None) -> FacturaElectronica:
    """Emite Factura Electrónica ante AFIP para una venta confirmada."""
    cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first() if venta.cliente_id else None
    cfg = _get_afip_config(db)

    tipo_cbte = 1 if _es_cliente_responsable_inscripto(cliente) else 10
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

    cert_path = cfg.get("cert", "") or os.getenv("AFIP_CERT", "")
    key_path = cfg.get("key", "") or os.getenv("AFIP_KEY", "")

    if not cert_path or not os.path.exists(cert_path):
        fe.estado = "pendiente"
        fe.observaciones = "AFIP no configurado. Ir a Ajustes > AFIP para configurar certificado y clave."
        db.commit()
        logger.warning(f"FE #{fe.id}: pendiente por falta de certificado AFIP")
        return fe

    try:
        _emitir_factura_zeep(db, fe, venta, tipo_cbte, cfg)
    except Exception as e:
        fe.estado = "rechazada"
        fe.error_message = str(e)
        db.commit()
        logger.error(f"FE #{fe.id}: error — {e}")

    return fe
