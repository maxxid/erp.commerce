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


class CrearOrdenInteroperableRequest(BaseModel):
    venta_id: int
    monto: Optional[float] = None


class QrPruebaRequest(BaseModel):
    """Laboratorio de QR: genera payloads para probar contra una billetera real.

    Todo es opcional: si viene vacío se toma lo configurado en Ajustes, así se
    puede probar sin tocar la configuración de producción.
    """

    cuit: Optional[str] = None
    cuenta: Optional[str] = None
    nombre: Optional[str] = None
    ciudad: Optional[str] = None
    mcc: Optional[str] = None
    monto: float = 100.0
    dinamico: bool = True


class QrAnalizarRequest(BaseModel):
    payload: str


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


@router.post("/interoperable/crear-orden")
def crear_orden_interoperable(
    req: CrearOrdenInteroperableRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Genera el payload del QR interoperable (EMVCo QRCPS v1.0) para una venta.

    El QR lo puede pagar cualquier billetera interoperable (Brubank, Personal
    Pay, MODO, MercadoPago, etc.) porque el importe viaja como transferencia
    inmediata (PCT) a la CBU/CVU codificada en el campo 51.

    Requiere configurarlo en Ajustes: qr_interop_cuit, qr_interop_cuenta,
    qr_interop_nombre y opcionalmente qr_interop_ciudad y qr_interop_mcc.
    """
    from app.services import config_service, venta_service
    from app.services import qr_interop_service

    venta = venta_service.obtener_venta(db, req.venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")

    if venta.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Venta en estado {venta.estado}, no se puede cobrar")

    monto = req.monto if req.monto is not None else venta.subtotal

    cuit = config_service.get_config(db, "qr_interop_cuit") or ""
    cuenta = config_service.get_config(db, "qr_interop_cuenta") or ""
    nombre = config_service.get_config(db, "qr_interop_nombre") or ""
    ciudad = config_service.get_config(db, "qr_interop_ciudad") or ""
    mcc = config_service.get_config(db, "qr_interop_mcc") or "9700"

    if not cuit or not cuenta or not nombre:
        raise HTTPException(
            status_code=400,
            detail="Falta configurar el QR interoperable en Ajustes (CUIT, CBU/CVU/alias y nombre del comercio)",
        )

    try:
        qr_data = qr_interop_service.generar_qr_interoperable(
            cuit=cuit,
            cuenta=cuenta,
            monto=monto,
            nombre_comercio=nombre,
            ciudad=ciudad,
            dinamico=True,
            mcc=mcc,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "success": True,
        "qr_data": qr_data,
        "venta_id": venta.id,
        "venta_numero": venta.numero,
        "monto": monto,
    }


def _describir_payload(payload: str) -> list:
    """Desarma el TLV del payload para poder mostrarlo en el laboratorio."""
    campos = []
    i = 0
    while i + 4 <= len(payload):
        tag = payload[i : i + 2]
        if not tag.isdigit():
            break
        largo = int(payload[i + 2 : i + 4])
        valor = payload[i + 4 : i + 4 + largo]
        if len(valor) != largo:
            break
        campos.append({"tag": tag, "largo": largo, "valor": valor})
        i += 4 + largo
    return campos


@router.post("/qr-interop/analizar")
def analizar_qr_interop(
    req: QrAnalizarRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Desarma un payload de QR ajeno y lo compara contra el estándar local.

    Sirve para ver cómo arma el QR el banco, un PSP u otro ERP, y decidir si la
    diferencia está en el estándar o en algún campo que el nuestro no manda.
    """
    from app.services import qr_interop_service

    payload = (req.payload or "").strip()
    if not payload:
        raise HTTPException(status_code=400, detail="Pegá un payload de QR")

    campos = _describir_payload(payload)
    if not campos:
        raise HTTPException(
            status_code=400,
            detail="No se pudo leer como TLV. Revisá que no tenga espacios ni saltos de línea.",
        )

    cubierto = sum(4 + c["largo"] for c in campos)

    # El CRC se calcula sobre todo lo anterior al campo 63, así que primero hay
    # que ubicar dónde arranca ese campo.
    desplazamiento = 0
    inicio_crc = None
    largo_crc = 0
    for c in campos:
        if c["tag"] == "63":
            inicio_crc = desplazamiento
            largo_crc = c["largo"]
            break
        desplazamiento += 4 + c["largo"]

    if inicio_crc is None:
        cuerpo = payload
        crc_declarado = ""
    else:
        # El CRC cubre el payload entero, incluido el identificador y el largo
        # del propio campo 63. Por eso el cuerpo llega hasta el final del 6304.
        cuerpo = payload[: inicio_crc + 4]
        crc_declarado = payload[inicio_crc + 4 : inicio_crc + 4 + largo_crc]

    crc_ok = bool(crc_declarado) and qr_interop_service.crc16_ccitt(cuerpo) == crc_declarado

    por_tag = {c["tag"]: c["valor"] for c in campos}
    comentarios = []

    if not crc_ok:
        comentarios.append(
            "El CRC no cierra: el payload cambió de largo o se copió con caracteres de más."
        )
    if cubierto != len(payload):
        comentarios.append(
            f"Hay {len(payload) - cubierto} caracteres después del último campo."
        )
    if "00" in por_tag and por_tag["00"] != "01":
        comentarios.append(f"Indicador de formato inesperado: {por_tag['00']!r} (esperado '01').")
    if "01" in por_tag and por_tag["01"] not in ("11", "12"):
        comentarios.append(
            f"Punto de iniciación inesperado: {por_tag['01']!r} (esperado '11' estático o '12' dinámico)."
        )
    if "50" not in por_tag:
        comentarios.append("No trae la CUIT del comercio en el campo 50 (obligatorio por la Com. A 6425).")
    if "54" in por_tag:
        comentarios.append(f"Lleva importe en el campo 54: {por_tag['54']}.")
    else:
        comentarios.append("No lleva importe: la billetera le pregunta el monto al cliente.")
    if "51" in por_tag:
        cuenta = por_tag["51"]
        if cuenta.startswith("00"):
            cuenta = cuenta[2 + 2 :]
        if cuenta.isdigit() and len(cuenta) == 22:
            if qr_interop_service.cbu_es_valida(cuenta):
                comentarios.append("El campo 51 trae una CBU con dígitos verificadores correctos.")
            else:
                comentarios.append("El campo 51 trae una CBU de 22 dígitos que no cierra sus verificadores.")
        else:
            comentarios.append(
                "El campo 51 no parece una CBU de 22 dígitos (puede ser un alias)."
            )

    return {
        "success": True,
        "payload": payload,
        "campos": campos,
        "crc": crc_declarado,
        "crc_ok": crc_ok,
        "completo": cubierto == len(payload),
        "comentarios": comentarios,
    }


@router.post("/qr-interop/laboratorio")
def laboratorio_qr_interop(
    req: QrPruebaRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Genera un QR de prueba y devuelve su payload desarmado.

    Sirve para comparar contra el QR que emite el banco o un PSP, sin tener que
    deployar: se puede probar cualquier combinación de CBU, MCC, nombre, etc.
    """
    from app.services import config_service
    from app.services import qr_interop_service

    def cfg(campo):
        """Usa lo que venga en el request y, si falta, lo de Ajustes."""
        valor = getattr(req, campo)
        if valor is not None:
            return valor
        return config_service.get_config(db, f"qr_interop_{campo}") or ""

    try:
        payload = qr_interop_service.generar_qr_interoperable(
            cuit=cfg("cuit"),
            cuenta=cfg("cuenta"),
            monto=req.monto,
            nombre_comercio=cfg("nombre"),
            ciudad=cfg("ciudad"),
            dinamico=req.dinamico,
            mcc=cfg("mcc") or "9700",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    campos = _describir_payload(payload)
    cuenta = cfg("cuenta").strip()

    avisos = []
    if cuenta.isdigit() and len(cuenta) == 22:
        if not qr_interop_service.cbu_es_valida(cuenta):
            avisos.append("La CBU no cierra sus dígitos verificadores.")
    elif cuenta:
        avisos.append(
            "La cuenta configurada no es una CBU de 22 dígitos (parece un alias). "
            "Algunas billeteras no resuelven alias desde el QR."
        )

    return {
        "success": True,
        "qr_data": payload,
        "campos": campos,
        "crc_ok": qr_interop_service.crc16_ccitt(payload[:-4]) == payload[-4:],
        "crc": payload[-4:],
        "dinamico": req.dynamico,
        "monto": req.monto,
        "avisos": avisos,
    }


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
    data_external_reference: str = Query(None, alias="data.external_reference"),
):
    """Endpoint para recibir webhooks de MercadoPago.

    Si mercadopago_webhook_secret esta configurado en la DB, se valida la firma
    HMAC-SHA256 del webhook. Si no esta configurado, se acepta sin validar.
    """
    from app.services import venta_service
    from app.services import mercadopago_service as mp_svc

    if not mercadopago_service.validar_firma_webhook(
        x_signature=x_signature,
        x_request_id=x_request_id,
        data_id=data_id,
        db=db,
    ):
        logger.warning(f"Webhook MP: firma invalida, rechazando request")
        raise HTTPException(status_code=401, detail="Firma de webhook invalida")

    logger.info(f"Webhook MP recibido: payload={payload}, data_id={data_id}, data_external_reference={data_external_reference}")

    webhook_data = payload.model_dump()
    webhook_data["data_external_reference"] = data_external_reference

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
