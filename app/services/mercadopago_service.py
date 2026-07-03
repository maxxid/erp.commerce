"""Servicio de MercadoPago para cobros con QR.

Flujo:
1. crear_orden_qr() - Crea orden y obtiene QR
2. obtener_estado_orden() - Consulta estado del pago
3. confirmar_pago_webhook() - Procesa notificación de pago
"""

import logging
import time
from typing import Optional
from sqlalchemy.orm import Session
from app.models.configuracion import Configuracion
from app.services import config_service

logger = logging.getLogger(__name__)


def get_mercadopago_config(db: Session) -> dict:
    return {
        "enabled": config_service.get_config(db, "mercadopago_enabled") == "true",
        "access_token": config_service.get_config(db, "mercadopago_access_token") or "",
        "pos_id": config_service.get_config(db, "mercadopago_pos_id") or "",
        "mode": config_service.get_config(db, "mercadopago_mode") or "sandbox",
    }


def _get_api_base(mode: str) -> str:
    return "https://api.mercadopago.com" if mode == "prod" else "https://api.sandbox.mercadopago.com"


def crear_orden_qr(
    db: Session,
    venta_id: int,
    venta_numero: str,
    monto: float,
    descripcion: str = "Cobro ERP",
) -> dict:
    """Crea una orden QR en MercadoPago.

    Returns:
        dict con {order_id, qr_data, qr_expires, ticket_url}
    Raises:
        ValueError: Si MercadoPago no está configurado o falla la API
    """
    import requests

    config = get_mercadopago_config(db)

    if not config["enabled"]:
        raise ValueError("MercadoPago no está habilitado")

    if not config["access_token"]:
        raise ValueError("MercadoPago access token no configurado")

    if not config["pos_id"]:
        raise ValueError("MercadoPago POS ID no configurado")

    base_url = _get_api_base(config["mode"])
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }

    payload = {
        "external_reference": f"venta_{venta_id}",
        "notification_url": f"{config_service.get_config(db, 'base_url') or 'http://localhost:8000'}/api/pagos/mercadopago/webhook",
        "description": descripcion,
        "cash_out": {"amount": 0},
        "items": [
            {
                "sku_number": venta_numero,
                "category_id": "services",
                "title": descripcion,
                "description": f"Venta {venta_numero}",
                "quantity": 1,
                "unit_price": float(monto),
                "total_amount": float(monto),
            }
        ],
        "marketplace": "ERP_COMERCIO",
        "pos_id": config["pos_id"],
    }

    logger.info(f"Creando orden MP para venta {venta_numero}, monto={monto}")

    try:
        response = requests.post(
            f"{base_url}/instore/qr/seller/collectors/{config['pos_id']}/orders",
            headers=headers,
            json=payload,
            timeout=30,
        )
    except requests.RequestException as e:
        logger.error(f"Error de conexión a MercadoPago: {e}")
        raise ValueError(f"Error de conexión a MercadoPago: {e}")

    if response.status_code not in (200, 201):
        logger.error(f"MP API error: {response.status_code} - {response.text}")
        raise ValueError(f"Error de MercadoPago: {response.status_code} - {response.text[:200]}")

    data = response.json()
    logger.info(f"Orden MP creada: {data}")

    return {
        "order_id": data.get("id"),
        "qrs": data.get("qrs", []),
        "qr_data": (data.get("qrs") or [{}])[0].get("qr_data") if data.get("qrs") else None,
        "qr_image_url": (data.get("qrs") or [{}])[0].get("image_url") if data.get("qrs") else None,
        "ticket_url": (data.get("qrs") or [{}])[0].get("ticket_url") if data.get("qrs") else None,
    }


def obtener_estado_orden(
    db: Session,
    order_id: str,
) -> dict:
    """Consulta el estado de una orden de pago.

    Returns:
        dict con {status, payment_id, amount, etc}
    """
    import requests

    config = get_mercadopago_config(db)

    if not config["enabled"]:
        raise ValueError("MercadoPago no está habilitado")

    base_url = _get_api_base(config["mode"])
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(
            f"{base_url}/orders/{order_id}",
            headers=headers,
            timeout=15,
        )
    except requests.RequestException as e:
        logger.error(f"Error consultando orden MP: {e}")
        raise ValueError(f"Error de conexión: {e}")

    if response.status_code != 200:
        logger.error(f"MP API error: {response.status_code} - {response.text}")
        raise ValueError(f"Error de MercadoPago: {response.status_code}")

    return response.json()


def procesar_webhook(db: Session, payload: dict) -> Optional[dict]:
    """Procesa notificación de pago desde MercadoPago.

    Args:
        payload: Datos del webhook (action, data.id, etc)

    Returns:
        dict con info del pago si se procesó correctamente, None si no aplica
    """
    action = payload.get("action", "")
    order_id = payload.get("data", {}).get("id") or payload.get("order_id")

    logger.info(f"Webhook MP recibido: action={action}, order_id={order_id}")

    if not order_id:
        return None

    if "order_prepaid" in action or "order_completed" in action or "payment.created" in action:
        try:
            orden = obtener_estado_orden(db, str(order_id))
        except Exception as e:
            logger.error(f"Error consultando orden en webhook: {e}")
            return None

        status = orden.get("status")
        external_ref = orden.get("external_reference")

        logger.info(f"Orden {order_id} status={status}, external_ref={external_ref}")

        if status in ("approved", "processed"):
            parts = external_ref.split("_") if external_ref else []
            if len(parts) >= 2 and parts[0] == "venta":
                venta_id = int(parts[1])
                payment_id = orden.get("payments", [{}])[0].get("id") if orden.get("payments") else None
                return {
                    "venta_id": venta_id,
                    "order_id": order_id,
                    "payment_id": payment_id,
                    "status": status,
                    "amount": orden.get("total_amount"),
                }

    return None


def confirmar_venta_por_mp(db: Session, venta_id: int, order_id: str, payment_id: str | None = None) -> dict:
    """Confirma una venta que fue pagada via MercadoPago QR.

    Llama a venta_service.confirmar_venta() con medio_pago='mercadopago_qr'.
    """
    from app.services import venta_service
    from app.models.venta import Venta

    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        raise ValueError(f"Venta {venta_id} no encontrada")

    if venta.estado != "pendiente":
        logger.warning(f"Venta {venta_id} ya está en estado {venta.estado}, ignorando confirmación MP")
        return {"ya_procesada": True, "estado": venta.estado}

    venta_externa_ref = f"venta_{venta_id}"
    logger.info(f"Confirmando venta {venta_id} por pago MP, order_id={order_id}")

    venta = venta_service.confirmar_venta(
        db,
        venta,
        medio_pago="mercadopago_qr",
        descuento=0.0,
    )

    return {
        "ya_procesada": False,
        "venta_id": venta.id,
        "venta_numero": venta.numero,
        "order_id": order_id,
        "payment_id": payment_id,
        "estado": venta.estado,
    }
