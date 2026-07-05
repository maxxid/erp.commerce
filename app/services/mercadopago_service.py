"""Servicio de MercadoPago para cobros con QR y Smart Point.

Flujo QR:
1. crear_orden_qr() - Crea orden y obtiene QR
2. obtener_estado_orden() - Consulta estado del pago
3. procesar_webhook() - Procesa notificación de pago

Flujo Smart Point:
1. crear_orden_pos() - Envía orden al POS físico
2. esperar_pago_pos() - Polling del estado
3. procesar_webhook() - Notificación automática
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
        "store_id": config_service.get_config(db, "mercadopago_store_id") or "",
        "external_store_id": config_service.get_config(db, "mercadopago_external_store_id") or "",
        "pos_id_qr": config_service.get_config(db, "mercadopago_pos_id_qr") or "",
        "external_pos_id": config_service.get_config(db, "mercadopago_external_pos_id") or "",
        "pos_id_smart": config_service.get_config(db, "mercadopago_pos_id_smart") or "",
        "user_id": config_service.get_config(db, "mercadopago_user_id") or "",
        "mode": config_service.get_config(db, "mercadopago_mode") or "sandbox",
        "qr_fijo_modo": config_service.get_config(db, "mercadopago_qr_fijo_modo") or "dinamico",
        "webhook_secret": config_service.get_config(db, "mercadopago_webhook_secret") or "",
    }


def _get_api_base(mode: str) -> str:
    return "https://api.mercadopago.com"


def crear_orden_qr(
    db: Session,
    venta_id: int,
    venta_numero: str,
    monto: float,
    descripcion: str = "Cobro ERP",
    modo_qr: str = None,
) -> dict:
    """Crea una orden QR en MercadoPago usando la API v1.

    Args:
        modo_qr: 'dinamico', 'estatico', o 'hibrido'. Usa config si no se especifica.

    Returns:
        dict con {order_id, qr_data, qr_image_url, status}
    """
    import requests
    import uuid

    config = get_mercadopago_config(db)

    if not config["enabled"]:
        raise ValueError("MercadoPago no está habilitado")

    if not config["access_token"]:
        raise ValueError("MercadoPago access token no configurado")

    external_pos_id = config.get("external_pos_id")
    if not external_pos_id:
        raise ValueError("No se encontró external_pos_id. Creá una caja primero en Ajustes.")

    modo = modo_qr or config.get("qr_fijo_modo") or "dinamico"
    modo_map = {"dinamico": "dynamic", "estatico": "static", "hibrido": "hybrid"}
    modo_mp = modo_map.get(modo, "dynamic")

    base_url = _get_api_base(config["mode"])
    idempotency_key = str(uuid.uuid4())

    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": idempotency_key,
    }

    payload = {
        "type": "qr",
        "total_amount": str(monto),
        "description": descripcion[:150],
        "external_reference": f"venta_{venta_id}",
        "expiration_time": "PT15M",
        "config": {
            "qr": {
                "external_pos_id": external_pos_id,
                "mode": modo_mp,
            }
        },
        "transactions": {
            "payments": [
                {"amount": str(monto)}
            ]
        },
        "items": [
            {
                "title": descripcion[:100],
                "unit_price": str(monto),
                "quantity": 1,
                "unit_measure": "unit",
            }
        ],
    }

    logger.info(f"Creando orden MP QR para venta {venta_numero}, monto={monto}, modo={modo_mp}")

    try:
        response = requests.post(
            f"{base_url}/v1/orders",
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

    qr_data = None
    qr_image_url = None
    if data.get("type_response"):
        tr = data["type_response"]
        if tr.get("qr_data"):
            qr_data = tr["qr_data"]
        if tr.get("qr") and tr["qr"].get("image"):
            qr_image_url = tr["qr"]["image"]

    return {
        "order_id": data.get("id"),
        "status": data.get("status"),
        "qr_data": qr_data,
        "qr_image_url": qr_image_url,
        "external_reference": data.get("external_reference"),
    }


def crear_orden_pos(
    db: Session,
    venta_id: int,
    venta_numero: str,
    monto: float,
    descripcion: str = "Cobro ERP",
) -> dict:
    """Envía una orden de pago al Smart Point de MercadoPago.

    El cliente elige el medio de pago directamente en el dispositivo.
    Usa la API v1 de orders.
    Returns:
        dict con {order_id, status}
    """
    import requests
    import uuid

    config = get_mercadopago_config(db)

    if not config["enabled"]:
        raise ValueError("MercadoPago no está habilitado")

    if not config["access_token"]:
        raise ValueError("MercadoPago access token no configurado")

    external_pos_id = config.get("external_pos_id")
    if not external_pos_id:
        raise ValueError("No se encontró external_pos_id. Creá una caja primero.")

    base_url = _get_api_base(config["mode"])
    idempotency_key = str(uuid.uuid4())

    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
        "X-Idempotency-Key": idempotency_key,
    }

    payload = {
        "type": "qr",
        "total_amount": str(monto),
        "description": descripcion[:150],
        "external_reference": f"venta_{venta_id}",
        "expiration_time": "PT15M",
        "config": {
            "qr": {
                "external_pos_id": external_pos_id,
                "mode": "dynamic",
            }
        },
        "transactions": {
            "payments": [
                {"amount": str(monto)}
            ]
        },
        "items": [
            {
                "title": descripcion[:100],
                "unit_price": str(monto),
                "quantity": 1,
                "unit_measure": "unit",
            }
        ],
    }

    logger.info(f"Enviando orden MP POS para venta {venta_numero}, monto={monto}")

    try:
        response = requests.post(
            f"{base_url}/v1/orders",
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
    logger.info(f"Orden MP POS creada: {data}")

    return {
        "order_id": data.get("id"),
        "status": data.get("status"),
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


def validar_firma_webhook(
    x_signature: str | None,
    x_request_id: str | None,
    data_id: str | None,
    db: Session,
) -> bool:
    """Valida la firma de un webhook de MercadoPago usando HMAC-SHA256.

    Segun documentacion oficial de MP, el header X-Signature tiene el formato:
    ts=timestamp,v1=firma_hex

    El manifest se arma como:
    id:{data_id_lower};request-id:{x_request_id};ts:{timestamp};

    Args:
        x_signature: Header X-Signature de MercadoPago
        x_request_id: Header X-Request-Id de MercadoPago
        data_id: Query param data.id (el order_id)
        db: Sesion de DB para leer el secret

    Returns:
        True si la firma es valida o no hay secret configurado (se permite)
        False si la firma no coincide (posible intento de fraude)
    """
    import hashlib
    import hmac

    config = get_mercadopago_config(db)
    webhook_secret = config.get("webhook_secret", "")

    if not webhook_secret:
        logger.info("Webhook MP: no hay secret configurado, se omite validacion de firma")
        return True

    if not x_signature:
        logger.warning("Webhook MP: falta header X-Signature, se rechazara")
        return False

    ts = None
    hash_value = None
    for part in x_signature.split(","):
        if "=" not in part:
            continue
        key, _, value = part.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "ts":
            ts = value
        if key == "v1":
            hash_value = value

    if not ts or not hash_value:
        logger.warning(f"Webhook MP: X-Signature sin ts o hash: {x_signature}")
        return False

    if not data_id:
        logger.warning("Webhook MP: falta data.id para validar firma")
        return False

    data_id_lower = data_id.lower()

    parts = []
    parts.append(f"id:{data_id_lower}")
    if x_request_id:
        parts.append(f"request-id:{x_request_id}")
    parts.append(f"ts:{ts}")
    manifest = ";".join(parts) + ";"

    computed = hmac.new(
        webhook_secret.encode("utf-8"),
        manifest.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed, hash_value):
        logger.warning(
            f"Webhook MP: firma invalida. Computed={computed}, Received={hash_value}, "
            f"manifest={manifest}"
        )
        return False

    logger.info("Webhook MP: firma validada correctamente")
    return True


def procesar_webhook(db: Session, payload: dict) -> Optional[dict]:
    """Procesa notificación de pago desde MercadoPago.

    Args:
        payload: Datos del webhook (action, data.id, etc)

    Returns:
        dict con info del pago si se procesó correctamente, None si no aplica
    """
    action = payload.get("action", "")
    data = payload.get("data", {})
    order_id = data.get("id") or payload.get("id")
    external_ref = data.get("external_reference") or payload.get("external_reference") or payload.get("data_external_reference", "")

    logger.info(f"Webhook MP recibido: action={action}, order_id={order_id}, external_ref={external_ref}")

    if not order_id and not external_ref:
        logger.warning(f"Webhook MP sin order_id ni external_reference")
        return None

    if "order.processed" in action or "order.completed" in action or "payment.created" in action or "order_prepaid" in action or "order.processed" in action:
        if external_ref and external_ref.startswith("venta_"):
            parts = external_ref.split("_")
            if len(parts) >= 2:
                venta_id = int(parts[1])
                payment_id = None
                transactions = data.get("transactions", {})
                if transactions and transactions.get("payments"):
                    payment_id = transactions["payments"][0].get("id")
                status = data.get("status") or "processed"
                amount = data.get("total_paid_amount") or data.get("total_amount")

                logger.info(f"Webhook MP confirmando venta {venta_id} desde external_ref")
                return {
                    "venta_id": venta_id,
                    "order_id": order_id or external_ref,
                    "payment_id": payment_id,
                    "status": status,
                    "amount": amount,
                }

        if not external_ref or not external_ref.startswith("venta_"):
            logger.warning(
                f"Webhook MP sin external_reference valido (order_id={order_id}), "
                f"no se puede asociar a una venta. Ignorando (comun en simulaciones de prueba)."
            )
            return None

        if order_id:
            try:
                orden = obtener_estado_orden(db, str(order_id))
                status = orden.get("status")
                external_ref = orden.get("external_reference") or external_ref
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
            except Exception as e:
                logger.error(f"Error consultando orden en webhook: {e}")

    if "order.canceled" in action or "order.expired" in action:
        logger.info(f"Webhook MP: orden cancelada/expirada {order_id}")

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


def crear_sucursal_mp(
    db: Session,
    nombre: str,
    external_id: str,
    street_number: str = "0",
    street_name: str = "",
    city_name: str = "Ciudad",
    state_name: str = "Estado",
    latitude: float = -34.6037,
    longitude: float = -58.3816,
    reference: str = "",
) -> dict:
    """Crea una sucursal en MercadoPago.

    Returns:
        dict con {id, name, external_id, location, etc}
    """
    import requests

    config = get_mercadopago_config(db)

    if not config["enabled"]:
        raise ValueError("MercadoPago no está habilitado")

    if not config["access_token"]:
        raise ValueError("MercadoPago access token no configurado")

    base_url = _get_api_base(config["mode"])

    payload = {
        "name": nombre,
        "external_id": external_id,
        "business_hours": {
            "monday": [{"open": "08:00", "close": "20:00"}],
            "tuesday": [{"open": "08:00", "close": "20:00"}],
            "wednesday": [{"open": "08:00", "close": "20:00"}],
            "thursday": [{"open": "08:00", "close": "20:00"}],
            "friday": [{"open": "08:00", "close": "20:00"}],
            "saturday": [{"open": "09:00", "close": "14:00"}],
        },
        "location": {
            "street_number": street_number,
            "street_name": street_name,
            "city_name": city_name,
            "state_name": state_name,
            "latitude": latitude,
            "longitude": longitude,
            "reference": reference,
        },
    }

    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }

    user_id = config.get("user_id") or _get_mp_user_id(db)
    if not user_id:
        raise ValueError("No se pudo obtener el user_id de MercadoPago")

    logger.info(f"Creando sucursal MP: {nombre}, external_id={external_id}")

    try:
        response = requests.post(
            f"{base_url}/users/{user_id}/stores",
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
    logger.info(f"Sucursal MP creada: {data}")

    return data


def crear_caja_mp(
    db: Session,
    nombre: str,
    store_id: int,
    external_store_id: str,
    external_id: str,
    fixed_amount: bool = True,
    category: int = 621102,
) -> dict:
    """Crea una caja (POS) en MercadoPago.

    Args:
        store_id: ID de la sucursal creada previamente
        external_id: ID único para esta caja (ej: "MI_CAJA_001")
        fixed_amount: True para que el monto sea prefijado por el vendedor

    Returns:
        dict con {id, qr, status, etc}
    """
    import requests

    config = get_mercadopago_config(db)

    if not config["enabled"]:
        raise ValueError("MercadoPago no está habilitado")

    if not config["access_token"]:
        raise ValueError("MercadoPago access token no configurado")

    base_url = _get_api_base(config["mode"])

    payload = {
        "name": nombre,
        "fixed_amount": fixed_amount,
        "store_id": store_id,
        "external_store_id": external_store_id,
        "external_id": external_id,
        "category": category,
    }

    headers = {
        "Authorization": f"Bearer {config['access_token']}",
        "Content-Type": "application/json",
    }

    logger.info(f"Creando caja MP: {nombre}, store_id={store_id}, external_id={external_id}")

    try:
        response = requests.post(
            f"{base_url}/pos",
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
    logger.info(f"Caja MP creada: {data}")

    return data


def _get_mp_user_id(db: Session) -> Optional[str]:
    """Obtiene el user_id de MercadoPago desde la config o haciendo un request."""
    user_id = config_service.get_config(db, "mercadopago_user_id")
    if user_id:
        return user_id

    import requests
    config = get_mercadopago_config(db)

    if not config["access_token"]:
        return None

    base_url = _get_api_base(config["mode"])
    headers = {
        "Authorization": f"Bearer {config['access_token']}",
    }

    try:
        response = requests.get(
            f"{base_url}/users/me",
            headers=headers,
            timeout=15,
        )
        if response.status_code == 200:
            data = response.json()
            user_id = str(data.get("id", ""))
            if user_id:
                config_service.set_config(db, "mercadopago_user_id", user_id, "User ID de MercadoPago")
                return user_id
    except Exception:
        pass

    return None
