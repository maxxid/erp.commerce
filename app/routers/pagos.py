"""Router de Pagos: MercadoPago QR."""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
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
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/mercadopago/webhook")
async def webhook_mercadopago(
    payload: WebhookPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """Endpoint para recibir webhooks de MercadoPago.

    MercadoPago envía notificaciones cuando un pago se completa.
    """
    import requests
    from app.services import venta_service

    logger.info(f"Webhook MP recibido: {payload}")

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
