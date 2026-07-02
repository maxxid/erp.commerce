"""Servicio de integración con AFIP para Factura Electrónica usando zeep.

Usa zeep (cliente SOAP) para autenticación (WSAA) y emisión de
facturas (FECAESolicitar). La configuración se lee de la tabla
configuraciones (configurable desde UI) con fallback a env vars.

Instalación: pip install zeep
"""

import os
import base64
import logging
import tempfile
import subprocess
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.orm import Session as DbSession
import urllib.request, urllib.error

from app.models.factura_electronica import FacturaElectronica
from app.models.venta import Venta
from app.models.cliente import Cliente
from app.services.config_service import get_afip_config

logger = logging.getLogger(__name__)

_token_cache = {"token": None, "sign": None, "expires": None}


def _get_afip_config(db: DbSession) -> dict:
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


def _autenticar_zeep(db: DbSession) -> tuple[str, str]:
    """Autentica contra WSAA usando OpenSSL para crear el CMS signed request."""
    global _token_cache
    import logging
    logger = logging.getLogger(__name__)

    now = datetime.utcnow()
    if _token_cache["token"] and _token_cache["expires"] and now < _token_cache["expires"]:
        return _token_cache["token"], _token_cache["sign"]

    cfg = _get_afip_config(db)

    import tempfile
    import subprocess

    from app.services.afip_csr_service import _decrypt_key
    _encryption_secret = "erp-afip-key-encryption-v1"

    cert_val = cfg.get("cert", "") or os.getenv("AFIP_CERT", "")
    key_val = cfg.get("key", "") or os.getenv("AFIP_KEY", "")

    cert_path = cert_val if os.path.exists(cert_val) else None
    key_path = key_val if os.path.exists(key_val) else None

    if not cert_path and cert_val:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
            f.write(cert_val)
            cert_path = f.name
        logger.info(f"Temp cert written to {cert_path}, size={len(cert_val)}")
    if not key_path and key_val:
        try:
            decrypted_key = _decrypt_key(key_val, _encryption_secret)
        except Exception:
            decrypted_key = key_val.encode()
        with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as f:
            f.write(decrypted_key.decode())
            key_path = f.name
        logger.info(f"Temp key written to {key_path}, size={len(decrypted_key)}")
        key_verify = subprocess.run(
            ['/usr/bin/openssl', 'rsa', '-in', key_path, '-check', '-noout'],
            capture_output=True, text=True
        )
        logger.info(f"openssl rsa verify: rc={key_verify.returncode}, stderr={key_verify.stderr.strip()[:200]}")

    result_verify = subprocess.run(
        ['/usr/bin/openssl', 'x509', '-noout', '-in', cert_path],
        capture_output=True, text=True
    )
    logger.info(f"openssl x509 verify cert: rc={result_verify.returncode}, stdout={result_verify.stdout.strip()}, stderr={result_verify.stderr.strip()[:200]}")

    if not cert_path:
        raise ValueError("AFIP certificado no configurado. Configurarlo en Ajustes > AFIP.")
    if not key_path:
        raise ValueError("AFIP clave privada no configurada. Configurarla en Ajustes > AFIP.")

    result_modulus = subprocess.run(
        ['/usr/bin/openssl', 'x509', '-noout', '-modulus', '-in', cert_path],
        capture_output=True, text=True
    )
    key_modulus = subprocess.run(
        ['/usr/bin/openssl', 'rsa', '-noout', '-modulus', '-in', key_path],
        capture_output=True, text=True
    )
    if result_modulus.stdout.strip() != key_modulus.stdout.strip():
        logger.error(f"Cert modulus: {result_modulus.stdout.strip()[:64]}...")
        logger.error(f"Key modulus: {key_modulus.stdout.strip()[:64]}...")
        raise ValueError("AFIP cert y key no corresponden. Regenerar CSR y obtener nuevo cert.")

    unique_id = int(datetime.now().timestamp())
    now_arg = datetime.now(timezone(timedelta(hours=-3)))
    gen_time = now_arg.strftime("%Y-%m-%dT%H:%M:%S-03:00")
    exp_time = (now_arg + timedelta(hours=12)).strftime("%Y-%m-%dT%H:%M:%S-03:00")

    tra = f"""<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest>
  <header>
    <uniqueId>{unique_id}</uniqueId>
    <generationTime>{gen_time}</generationTime>
    <expirationTime>{exp_time}</expirationTime>
  </header>
  <service>wsfe</service>
</loginTicketRequest>"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(tra)
        tra_path = f.name

    with tempfile.NamedTemporaryFile(mode='wb', suffix='.cms', delete=False) as f:
        cms_path = f.name

    try:
        result = subprocess.run(
            ['/usr/bin/openssl', 'cms', '-sign', '-nodetach', '-outform', 'DER',
             '-inkey', key_path, '-signer', cert_path,
             '-in', tra_path, '-out', cms_path],
            capture_output=True, text=True, check=True
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Error firmando TRA con OpenSSL: {e.stderr}")

    with open(cms_path, 'rb') as f:
        cms_data = f.read()

    wsaa_url = _get_wsaa_url(cfg["mode"])

    soap_envelope = f"""<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns1="http://wsaa.view.sua.dvadac.desein.afip.gov">
  <SOAP-ENV:Body>
    <ns1:loginCms>
      <ns1:in0>{base64.b64encode(cms_data).decode()}</ns1:in0>
    </ns1:loginCms>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>"""

    session = requests.Session()
    session.cert = (cert_path, key_path)

    try:
        response = session.post(
            wsaa_url,
            data=soap_envelope.encode('utf-8'),
            headers={
                'Content-Type': 'text/xml; charset=utf-8',
                'SOAPAction': 'loginCms'
            },
            verify=True
        )
        logger.info(f"WSAA response status: {response.status_code}")
        logger.info(f"WSAA response body (first 1500): {response.text[:1500]}")
        if response.status_code != 200:
            raise RuntimeError(f"WSAA respondió {response.status_code}: {response.text[:500]}")
        soap_response = response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Error conectando a WSAA: {e}")

    import xml.etree.ElementTree as ET
    import html
    try:
        root = ET.fromstring(soap_response)
        ns = {'wsaa': 'http://wsaa.view.sua.dvadac.desein.afip.gov'}
        login_cms_return = root.find('.//wsaa:loginCmsReturn', ns)
        if login_cms_return is None:
            login_cms_return = root.find('.//loginCmsReturn')
        if login_cms_return is None:
            login_cms_return = root.find('.//{http://wsaa.view.sua.dvadac.desein.afip.gov}loginCmsReturn')
        inner_xml = login_cms_return.text if login_cms_return is not None else ''
        inner_xml = html.unescape(inner_xml)
        logger.info(f"Inner XML (first 500): {inner_xml[:500]}")
        inner_root = ET.fromstring(inner_xml)
        token = inner_root.find('.//token').text if inner_root.find('.//token') is not None else ''
        sign = inner_root.find('.//sign').text if inner_root.find('.//sign') is not None else ''
    except Exception as e:
        raise RuntimeError(f"Error parseando login ticket: {e}\nRespuesta: {soap_response[:500]}")

    if not token or not sign:
        raise RuntimeError(f"WSAA no retornó token/sign completos. token={bool(token)}, sign={bool(sign)}")

    os.unlink(tra_path)
    os.unlink(cms_path)

    _token_cache["token"] = token
    _token_cache["sign"] = sign
    _token_cache["expires"] = now + timedelta(hours=11)

    logger.info("AFIP WSAA autenticado exitosamente")
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


def _obtener_ultimo_comprobante(db: DbSession, wsfe_client, tipo_cbte: int, cfg: dict) -> int:
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


def _emitir_factura_zeep(db: DbSession, fe: FacturaElectronica, venta: Venta, tipo_cbte: int, cfg: dict):
    """Emite la factura usando SOAP manual con requests (sin zeep/WSDL)."""
    from app.services.afip_csr_service import _decrypt_key
    global _encryption_secret
    import xml.etree.ElementTree as ET

    token, sign = _autenticar_zeep(db)

    cert_val = cfg.get("cert", "") or os.getenv("AFIP_CERT", "")
    key_val = cfg.get("key", "") or os.getenv("AFIP_KEY", "")

    cert_path = cert_val if os.path.exists(cert_val) else None
    key_path = key_val if os.path.exists(key_val) else None

    if not cert_path and cert_val:
        try:
            decrypted_key = _decrypt_key(key_val, _encryption_secret)
            decrypted_key_str = decrypted_key.decode('utf-8')
        except Exception as exc:
            logger.warning(f"Key decryption failed ({exc}), trying raw key")
            decrypted_key = key_val.encode()
            decrypted_key_str = key_val
        cert_bytes = cert_val.encode('utf-8') if isinstance(cert_val, str) else cert_val
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.crt', delete=False) as f:
            f.write(cert_bytes)
            cert_path = f.name
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.key', delete=False) as f:
            f.write(decrypted_key)
            key_path = f.name
        logger.info(f"DEBUG cert_path={cert_path} cert_bytes={len(cert_bytes)}")
        r = subprocess.run(['openssl', 'x509', '-in', cert_path, '-noout', '-subject'],
                         capture_output=True, text=True)
        logger.info(f"DEBUG openssl x509: {r.stdout.strip() or r.stderr.strip()}")
        r2 = subprocess.run(['openssl', 'rsa', '-in', key_path, '-check', '-noout'],
                          capture_output=True, text=True)
        logger.info(f"DEBUG openssl rsa check: rc={r2.returncode} {r2.stderr.strip()}")
        if r2.returncode != 0:
            r3 = subprocess.run(['openssl', 'rsa', '-in', key_path, '-noout'],
                              capture_output=True, text=True)
            logger.warning(f"DEBUG openssl rsa (without check): rc={r3.returncode} {r3.stderr.strip()}")
            raise RuntimeError(f"Private key inválido para SSL: {r2.stderr.strip() or r3.stderr.strip()}")

    last_fe = db.query(FacturaElectronica).filter(
        FacturaElectronica.punto_venta == cfg["pto_vta"],
        FacturaElectronica.tipo == str(tipo_cbte),
        FacturaElectronica.resultado == 'A'
    ).order_by(FacturaElectronica.numero_fiscal.desc()).first()

    numero_fiscal = (last_fe.numero_fiscal + 1) if last_fe and last_fe.numero_fiscal else 1
    fecha = venta.fecha.strftime("%Y%m%d") if venta.fecha else datetime.now().strftime("%Y%m%d")
    tipo_doc = _map_tipo_doc(venta.cliente.tipo_documento if venta.cliente else None)
    nro_doc = venta.comprador_cuit or (venta.cliente.numero_documento if venta.cliente and venta.cliente.numero_documento else "0")
    iva_id = 5 if tipo_cbte == 1 else 10

    iva_xml = ""
    if tipo_cbte == 1:
        iva_xml = f"""<Iva>
          <AlicIva>
            <BaseImp>{round(fe.neto, 2)}</BaseImp>
            <Id>{iva_id}</Id>
            <Importe>{round(fe.iva, 2)}</Importe>
          </AlicIva>
        </Iva>"""

    fe_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:fev1="http://ar.gov.afip.dif.FEV1/">
  <soapenv:Body>
    <fev1:FECAESolicitar>
      <fev1:Auth>
        <fev1:Token>{token}</fev1:Token>
        <fev1:Sign>{sign}</fev1:Sign>
        <fev1:Cuit>{cfg["cuit"]}</fev1:Cuit>
      </fev1:Auth>
      <fev1:FeCAEReq>
        <fev1:FeCabReq>
          <fev1:CantReg>1</fev1:CantReg>
          <fev1:PtoVta>{cfg["pto_vta"]}</fev1:PtoVta>
          <fev1:CbteTipo>{tipo_cbte}</fev1:CbteTipo>
        </fev1:FeCabReq>
        <fev1:FeDetReq>
          <fev1:FECAEDetRequest>
            <fev1:DocNro>{nro_doc}</fev1:DocNro>
            <fev1:DocTipo>{tipo_doc}</fev1:DocTipo>
            <fev1:CbteDesde>{numero_fiscal}</fev1:CbteDesde>
            <fev1:CbteHasta>{numero_fiscal}</fev1:CbteHasta>
            <fev1:CbteFch>{fecha}</fev1:CbteFch>
            <fev1:ImpTotal>{round(fe.total, 2)}</fev1:ImpTotal>
            <fev1:ImpTotConc>0</fev1:ImpTotConc>
            <fev1:ImpNeto>{round(fe.neto, 2)}</fev1:ImpNeto>
            <fev1:ImpOpEx>0</fev1:ImpOpEx>
            <fev1:ImpTrib>0</fev1:ImpTrib>
            <fev1:ImpIVA>{round(fe.iva, 2)}</fev1:ImpIVA>
            <fev1:MonId>PES</fev1:MonId>
            <fev1:MonCotiz>1</fev1:MonCotiz>
            {iva_xml}
          </fev1:FECAEDetRequest>
        </fev1:FeDetReq>
      </fev1:FeCAEReq>
    </fev1:FECAESolicitar>
  </soapenv:Body>
</soapenv:Envelope>"""

    wsfe_url = _get_wsfe_url(cfg["mode"])
    xml_path = f"/tmp/wsfev1_req_{os.getpid()}.xml"
    resp_path = f"/tmp/wsfev1_resp_{os.getpid()}.xml"

    with open(xml_path, 'w') as f:
        f.write(fe_xml)

    try:
        result = subprocess.run(
            ['curl', '-skL', '--tlsv1.0', '--sslv3',
             '-E', f'{cert_path}', '--key', f'{key_path}',
             '-X', 'POST', '-H', 'Content-Type: text/xml; charset=utf-8',
             '-H', 'SOAPAction: FECAESolicitar',
             '-d', f'@{xml_path}',
             '-o', resp_path,
             wsfe_url],
            capture_output=True, text=True, check=True, timeout=30
        )
        with open(resp_path) as f:
            soap_response = f.read()
        logger.info(f"WSFE curl resp: {len(soap_response)} bytes")
        logger.info(f"WSFE response (first 2000): {soap_response[:2000]}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"curl WSFE falló (rc={e.returncode}): {e.stderr[:500]}")
    except FileNotFoundError:
        raise RuntimeError("curl no disponible en este servidor")
    except Exception as e:
        raise RuntimeError(f"Error conectando a WSFE: {e}")

    root = ET.fromstring(soap_response)
    ns = {'soap': 'http://schemas.xmlsoap.org/soap/envelope/', 'fev1': 'http://ar.gov.afip.dif.FEV1/'}
    body = root.find('soap:Body', ns)
    if body is None:
        body = root.find('.//Body') or root

    fecae_resp = body.find('.//FECAESolicitarResponse', ns) or body.find('.//fev1:FECAESolicitarResponse', ns)

    if fecae_resp is None:
        errores = []
        for err in body.findall('.//Errors') + body.findall('.//fev1:Errors'):
            code = (err.find('Code') or err.find('fev1:Code') or err).text
            msg = (err.find('Msg') or err.find('fev1:Msg') or err).text
            errores.append(f"{code}: {msg}")
        raise RuntimeError(f"AFIP Fault: {'; '.join(errores)}")

    result = fecae_resp.find('FECAESolicitarResult', ns) or fecae_resp.find('fev1:FECAESolicitarResult', ns)
    if result is None:
        raise RuntimeError(f"AFIP no retornó FECAESolicitarResult")

    fe_cab = result.find('FeCabResp', ns) or result.find('fev1:FeCabResp', ns)
    fe_det = result.find('FeDetResp', ns) or result.find('fev1:FeDetResp', ns)

    if fe_det is not None:
        det = fe_det.find('FECAEDetResponse', ns) or fe_det.find('fev1:FECAEDetResponse', ns)
        if det is not None:
            cae_el = det.find('CAE', ns) or det.find('fev1:CAE', ns)
            fe.cae = cae_el.text if cae_el is not None else ''
            cbte_desde = det.find('CbteDesde', ns) or det.find('fev1:CbteDesde', ns)
            if cbte_desde is not None:
                fe.numero_fiscal = int(cbte_desde.text)
            cae_fch = det.find('CAEFchVto', ns) or det.find('fev1:CAEFchVto', ns)
            if cae_fch is not None and cae_fch.text:
                try:
                    fe.vencimiento_cae = datetime.strptime(cae_fch.text.strip(), "%Y%m%d")
                except:
                    pass

    if fe_cab is not None:
        resultado = (fe_cab.find('Resultado', ns) or fe_cab.find('fev1:Resultado', ns) or fe_cab).text
        fe.resultado = resultado or 'R'
        fe.estado = "emitida" if resultado == 'A' else "rechazada"

        if resultado != 'A':
            errores = []
            for err in (result.find('Errors', ns) or result.find('fev1:Errors', ns) or []):
                code = (err.find('Code') or err.find('fev1:Code') or err).text
                msg = (err.find('Msg') or err.find('fev1:Msg') or err).text
                errores.append(f"{code}: {msg}")
            fe.error_message = "; ".join(errores) if errores else "Rechazada por AFIP"

    if fe.error_message and result is not None:
        obs_list = result.find('Observaciones', ns) or result.find('fev1:Observaciones', ns)
        if obs_list is not None:
            obs = []
            for o in obs_list:
                code = (o.find('Code') or o.find('fev1:Code') or o).text
                msg = (o.find('Msg') or o.find('fev1:Msg') or o).text
                obs.append(f"{code}: {msg}")
            fe.error_message += " | Obs: " + "; ".join(obs)

    fe.emitted_at = datetime.utcnow()
    db.commit()
    logger.info(f"FE #{fe.id}: resultado={fe.resultado} CAE={fe.cae}")


def emitir_factura(db: DbSession, venta: Venta, afip_cuit: str = None) -> FacturaElectronica:
    """Emite Factura Electrónica ante AFIP para una venta confirmada."""
    cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first() if venta.cliente_id else None
    cfg = _get_afip_config(db)

    tipo_cbte = 1 if _es_cliente_responsable_inscripto(cliente) else 11
    tipo_doc = _map_tipo_doc(cliente.tipo_documento if cliente else None)
    nro_doc = venta.comprador_cuit or (cliente.numero_documento if cliente and cliente.numero_documento else "0")

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

    cert_val = cfg.get("cert", "") or os.getenv("AFIP_CERT", "")
    key_val = cfg.get("key", "") or os.getenv("AFIP_KEY", "")

    cert_path = cert_val if os.path.exists(cert_val) else None
    key_path = key_val if os.path.exists(key_val) else None

    if not cert_path and cert_val:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.crt', delete=False) as f:
            f.write(cert_val)
            cert_path = f.name
    if not key_path and key_val:
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False) as f:
            f.write(key_val)
            key_path = f.name

    if not cert_path or not os.path.exists(cert_path):
        fe.estado = "pendiente"
        fe.observaciones = "AFIP no configurado. Ir a Ajustes > AFIP para configurar certificado y clave."
        db.commit()
        logger.warning(f"FE #{fe.id}: pendiente por falta de certificado AFIP")
        return fe

    cfg["cert"] = cert_path
    cfg["key"] = key_path

    try:
        _emitir_factura_zeep(db, fe, venta, tipo_cbte, cfg)
    except Exception as e:
        fe.estado = "rechazada"
        fe.error_message = str(e)
        db.commit()
        logger.error(f"FE #{fe.id}: error — {e}")

    return fe
