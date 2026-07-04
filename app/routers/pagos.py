"""Router de Pagos: MercadoPago QR."""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Header, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.services import mercadopago_service
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/pagos", tags=["Pagos"])
logger = logging.getLogger(__name__)


class CrearOrdenQRRequest(BaseModel):
    venta_id: int
    descripcion: Optional[str] = "Cobro ERP"


class CrearOrdenPOSRequest(BaseModel):
    venta_id: int
    descripcion: Optional[str] = "Cobro ERP"


class WebhookPayload(BaseModel):
    action: Optional[str] = None
    data: Optional[dict] = None
    order_id: Optional[str] = None
    id: Optional[str] = None


class CrearSucursalRequest(BaseModel):
    nombre: str
    external_id: str
    street_number: str = "0"
    street_name: str = ""
    city_name: str = "Ciudad"
    state_name: str = "Estado"
    latitude: float = -34.6037
    longitude: float = -58.3816
    reference: str = ""


class CrearCajaRequest(BaseModel):
    nombre: str
    external_id: str
    external_store_id: str
    fixed_amount: bool = True
    category: int = 621102


@router.post("/mercadopago/crear-orden")
def crear_orden_qr(
    req: CrearOrdenQRRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Genera una orden QR de MercadoPago para una venta pendiente.

    El QR se puede mostrar al cliente para cobrar.
    """
    from app.services import venta_service

    venta = venta_service.obtener_venta(db, req.venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    if venta.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Venta en estado {venta.estado}, no se puede cobrar")

    if not venta.items:
        raise HTTPException(status_code=400, detail="Venta sin productos")

    try:
        result = mercadopago_service.crear_orden_qr(
            db,
            venta_id=venta.id,
            venta_numero=venta.numero,
            monto=venta.subtotal,
            descripcion=req.descripcion or f"Venta {venta.numero}",
        )
        return {
            "success": True,
            "order_id": result["order_id"],
            "qr_data": result.get("qr_data"),
            "qr_image_url": result.get("qr_image_url"),
            "ticket_url": result.get("ticket_url"),
            "venta_id": venta.id,
            "venta_numero": venta.numero,
            "monto": venta.subtotal,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mercadopago/crear-orden-pos")
def crear_orden_pos(
    req: CrearOrdenPOSRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Envía una orden de pago al Smart Point de MercadoPago.

    El cliente elige el medio de pago (QR, débito, crédito, NFC) en el dispositivo.
    """
    from app.services import venta_service

    venta = venta_service.obtener_venta(db, req.venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    if venta.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Venta en estado {venta.estado}, no se puede cobrar")

    if not venta.items:
        raise HTTPException(status_code=400, detail="Venta sin productos")

    try:
        result = mercadopago_service.crear_orden_pos(
            db,
            venta_id=venta.id,
            venta_numero=venta.numero,
            monto=venta.subtotal,
            descripcion=req.descripcion or f"Venta {venta.numero}",
        )
        return {
            "success": True,
            "order_id": result["order_id"],
            "status": result.get("status"),
            "point_of_interaction": result.get("point_of_interaction"),
            "venta_id": venta.id,
            "venta_numero": venta.numero,
            "monto": venta.subtotal,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/mercadopago/orden/{order_id}")
def obtener_orden(
    order_id: str,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Consulta el estado de una orden de pago."""
    try:
        orden = mercadopago_service.obtener_estado_orden(db, order_id)
        return {"success": True, "orden": orden}
    except ValueError as e:
        logger.error(f"Error consultando orden {order_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mercadopago/webhook")
async def webhook_mercadopago(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    x_signature: str = Header(None, alias="X-Signature"),
    x_request_id: str = Header(None, alias="X-Request-Id"),
    data_id: str = Query(None, alias="data.id"),
):
    """Endpoint para recibir webhooks de MercadoPago.

    MercadoPago envía notificaciones cuando un pago se completa.
    Valida la firma del webhook si está configurado el secret.
    """
    import hmac
    import hashlib
    from app.services import venta_service
    from app.services import mercadopago_service as mp_svc

    logger.info(f"Webhook MP recibido: {payload}")

    webhook_secret = mp_svc.get_mercadopago_config(db).get("webhook_secret")
    if webhook_secret and x_signature:
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

        data_id_lower = (data_id or "").lower()
        if data_id_lower and payload.data and payload.data.get("id"):
            data_id_lower = payload.data.get("id", "").lower()

        parts = []
        if data_id_lower:
            parts.append(f"id:{data_id_lower}")
        if x_request_id:
            parts.append(f"request-id:{x_request_id}")
        parts.append(f"ts:{ts}")
        manifest = ";".join(parts) + ";"

        computed = hmac.new(
            webhook_secret.encode(),
            manifest.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(computed, hash_value or ""):
            logger.warning(f"Webhook MP firma inválida: computed={computed}, received={hash_value}, manifest={manifest}")
            raise HTTPException(status_code=403, detail="Firma de webhook inválida")

    webhook_data = payload.model_dump()

    try:
        resultado = mercadopago_service.procesar_webhook(db, webhook_data)
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    if not resultado:
        return {"received": True, "processed": False}

    venta_id = resultado["venta_id"]
    order_id = resultado["order_id"]
    payment_id = resultado.get("payment_id")

    background_tasks.add_task(
        confirmar_venta_mp_background,
        db_url=db.bind.url if hasattr(db.bind, "url") else str(db.bind),
        venta_id=venta_id,
        order_id=order_id,
        payment_id=payment_id,
    )

    return {"received": True, "processed": True, "venta_id": venta_id}


def confirmar_venta_mp_background(db_url: str, venta_id: int, order_id: str, payment_id: str | None):
    """Background task para confirmar venta tras pago MP."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            mercadopago_service.confirmar_venta_por_mp(db, venta_id, order_id, payment_id)
            logger.info(f"Venta {venta_id} confirmada por pago MP exitoso")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error confirmando venta {venta_id} en background: {e}")


@router.post("/mercadopago/crear-sucursal")
def crear_sucursal(
    req: CrearSucursalRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Crea una sucursal en MercadoPago."""
    try:
        result = mercadopago_service.crear_sucursal_mp(
            db,
            nombre=req.nombre,
            external_id=req.external_id,
            street_number=req.street_number,
            street_name=req.street_name,
            city_name=req.city_name,
            state_name=req.state_name,
            latitude=req.latitude,
            longitude=req.longitude,
            reference=req.reference,
        )
        return {
            "success": True,
            "store_id": result.get("id"),
            "name": result.get("name"),
            "external_id": result.get("external_id"),
            "message": "Sucursal creada exitosamente"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mercadopago/crear-caja")
def crear_caja(
    req: CrearCajaRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Crea una caja (POS) en MercadoPago y guarda el QR fijo."""
    from app.services import config_service

    config_mp = mercadopago_service.get_mercadopago_config(db)
    if not config_mp.get("user_id"):
        mercadopago_service._get_mp_user_id(db)

    try:
        result = mercadopago_service.crear_caja_mp(
            db,
            nombre=req.nombre,
            store_id=int(config_mp.get("store_id") or 0),
            external_store_id=req.external_store_id,
            external_id=req.external_id,
            fixed_amount=req.fixed_amount,
            category=req.category,
        )

        qr_image_url = None
        if result.get("qr") and result["qr"].get("image"):
            qr_image_url = result["qr"]["image"]

        box_external_id = result.get("external_id")
        box_id = result.get("id")

        config_service.set_config(
            db,
            "mercadopago_external_pos_id",
            box_external_id,
            "External ID de la caja para órdenes QR"
        )

        if box_id:
            config_service.set_config(
                db,
                "mercadopago_pos_id_qr",
                str(box_id),
                "ID numérico de la caja"
            )

        if qr_image_url:
            config_service.set_config(
                db,
                "mercadopago_qr_fijo_url",
                qr_image_url,
                "URL de imagen del QR fijo de MercadoPago"
            )

        return {
            "success": True,
            "pos_id": box_id,
            "external_pos_id": box_external_id,
            "name": result.get("name"),
            "qr_image_url": qr_image_url,
            "external_id": box_external_id,
            "message": "Caja creada exitosamente"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
