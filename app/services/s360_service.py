"""Servicio de integración con Sistemas360 para Factura Electrónica."""

import logging
import requests
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session as DbSession

from app.models.factura_electronica import FacturaElectronica
from app.models.venta import Venta
from app.models.cliente import Cliente
from app.services.config_service import get_config

logger = logging.getLogger(__name__)
S360_BASE_URL = "https://api.sistemas360.ar"


def _map_tipo_doc(tipo_doc):
    if not tipo_doc:
        return "consumidor_final"
    t = str(tipo_doc).strip().upper()
    if t in ("CUIT", "80"):
        return "cuit"
    if t in ("CUIL", "86"):
        return "cuil"
    if t in ("DNI", "96"):
        return "dni"
    return "consumidor_final"


def _map_condicion_iva(cliente):
    if not cliente:
        return 5
    cond = getattr(cliente, 'condicion_iva', '').lower()
    if "responsable inscripto" in cond:
        return 1
    if "monotributo" in cond:
        return 6
    return 5


def _get_s360_token(db):
    return get_config(db, "s360_token") or ""


def _build_payload(fe, venta, cliente):
    tipo_cbte = int(fe.tipo) if fe.tipo else 11
    tipo_s360 = "factura_c"
    if tipo_cbte in (1, 6):
        tipo_s360 = "factura_a"
    elif tipo_cbte in (2, 3, 7, 8):
        tipo_s360 = "factura_b"

    doc_tipo = _map_tipo_doc(cliente.tipo_documento if cliente else None)
    doc_num = venta.comprador_cuit or (cliente.numero_documento if cliente else None)
    if doc_tipo == "consumidor_final":
        doc_num = None

    razon = "Consumidor Final"
    if cliente and getattr(cliente, 'nombre', None):
        razon = f"{getattr(cliente, 'apellido', '')}, {cliente.nombre}".strip(", ")
    elif venta.comprador_cuit:
        razon = f"CUIT {venta.comprador_cuit}"

    items = []
    total = round(float(venta.total or 0), 2)
    
    if tipo_s360 == "factura_c":
        items.append({"descripcion": "Venta", "cantidad": 1, "precio_unitario": total})
    else:
        neto = round(total / 1.21, 2)
        items.append({"descripcion": "Venta", "cantidad": 1, "precio_unitario": neto,
                      "tipo_impuesto": "gravado", "iva": 21})

    return {
        "tipo_comprobante": tipo_s360,
        "concepto": "productos",
        "fecha": datetime.now().strftime("%Y-%m-%d"),
        "referencia_externa": f"venta_{venta.numero}",
        "cliente": {
            "documento_tipo": doc_tipo,
            "documento_numero": doc_num,
            "razon_social": razon,
            "condicion_iva_receptor_id": _map_condicion_iva(cliente),
        },
        "items": items,
        "total": total,
        "moneda": "PES",
    }


def emitir_factura_s360(db, venta, fe):
    cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first() if venta.cliente_id else None
    
    token = _get_s360_token(db)
    if not token:
        fe.estado = "rechazada"
        fe.error_message = "S360: Token no configurado"
        db.commit()
        return fe

    payload = _build_payload(fe, venta, cliente)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json", "Content-Type": "application/json"}

    try:
        r = requests.post(f"{S360_BASE_URL}/api/comprobantes", json=payload, headers=headers, timeout=30)
        logger.info(f"S360 status: {r.status_code} - {r.text[:500]}")

        if r.status_code in (200, 201):
            data = r.json()
            if data.get("ok"):
                result = data["data"]
                fe.cae = result.get("cae", "")
                fe.numero_fiscal = result.get("numero_comprobante")
                fe.resultado = "A"
                fe.estado = "emitida"
                fe.observaciones = f"S360 ID: {result.get('id')}"
                if result.get("cae_vencimiento"):
                    try:
                        fe.vencimiento_cae = datetime.strptime(result["cae_vencimiento"], "%Y-%m-%d")
                    except:
                        pass
            else:
                err = data.get("error", {})
                fe.estado = "rechazada"
                fe.error_message = f"S360: {err.get('mensaje', 'Error')}"
        else:
            fe.estado = "rechazada"
            fe.error_message = f"S360 HTTP {r.status_code}"

    except Exception as e:
        logger.error(f"S360 error: {e}")
        fe.estado = "rechazada"
        fe.error_message = str(e)

    fe.emitted_at = datetime.utcnow()
    db.commit()
    return fe
