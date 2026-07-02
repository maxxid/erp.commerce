"""Router de Facturación Electrónica AFIP."""

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from io import BytesIO

from app.database import get_db
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.factura_electronica import FacturaElectronica
from app.services.venta_service import obtener_venta
from app.services import afip_service
from app.services import afip_csr_service
from app.services.config_service import get_config

router = APIRouter(prefix="/api/facturacion", tags=["Facturación Electrónica"])


@router.get("/facturas", response_model=RespuestaLista)
def listar_facturas(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Lista todas las facturas electrónicas emitidas."""
    facturas = db.query(FacturaElectronica).order_by(FacturaElectronica.id.desc()).limit(200).all()
    data = [
        {
            "id": f.id,
            "venta_id": f.venta_id,
            "venta_numero": f.venta_numero,
            "tipo": f.tipo,
            "numero_fiscal": f.numero_fiscal,
            "cae": f.cae,
            "resultado": f.resultado,
            "total": f.total,
            "estado": f.estado,
            "error_message": f.error_message,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "emitted_at": f.emitted_at.isoformat() if f.emitted_at else None,
        }
        for f in facturas
    ]
    return RespuestaLista(data=data, total=len(data), message=f"{len(data)} factura(s)")


@router.get("/facturas/{venta_id}", response_model=RespuestaData)
def obtener_factura_por_venta(
    venta_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene la factura asociada a una venta."""
    fe = db.query(FacturaElectronica).filter(FacturaElectronica.venta_id == venta_id).first()
    if not fe:
        raise HTTPException(status_code=404, detail="No hay factura para esta venta")
    return RespuestaData(data={
        "id": fe.id,
        "venta_id": fe.venta_id,
        "venta_numero": fe.venta_numero,
        "tipo": fe.tipo,
        "punto_venta": fe.punto_venta,
        "numero_fiscal": fe.numero_fiscal,
        "cae": fe.cae,
        "vencimiento_cae": fe.vencimiento_cae.isoformat() if fe.vencimiento_cae else None,
        "resultado": fe.resultado,
        "total": fe.total,
        "neto": fe.neto,
        "iva": fe.iva,
        "estado": fe.estado,
        "error_message": fe.error_message,
        "emitted_at": fe.emitted_at.isoformat() if fe.emitted_at else None,
    })


class EmitirFacturaRequest(BaseModel):
    afip_cuit: str = ""


@router.post("/facturas/{venta_id}/emitir", response_model=RespuestaData)
def emitir_factura(
    venta_id: int,
    data: EmitirFacturaRequest = EmitirFacturaRequest(),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Emite una factura electrónica para una venta ya confirmada."""
    venta = obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if venta.estado != "confirmada":
        raise HTTPException(status_code=400, detail="La venta debe estar confirmada para facturar")

    # Verificar si ya existe factura emitida
    existente = db.query(FacturaElectronica).filter(
        FacturaElectronica.venta_id == venta_id,
        FacturaElectronica.estado == "emitida",
    ).first()
    if existente:
        return RespuestaData(data={
            "id": existente.id,
            "cae": existente.cae,
            "numero_fiscal": existente.numero_fiscal,
            "mensaje": "Ya existe una factura emitida para esta venta",
        })

    try:
        fe = afip_service.emitir_factura(db, venta, data.afip_cuit or None)
        if fe.estado == 'rechazada':
            return RespuestaData(data={
                "id": fe.id,
                "cae": fe.cae,
                "numero_fiscal": fe.numero_fiscal,
                "estado": fe.estado,
                "error_message": fe.error_message,
            }, message=f"Factura rechazada: {fe.error_message or 'verificar cert/key AFIP'}")
        return RespuestaData(data={
            "id": fe.id,
            "cae": fe.cae,
            "numero_fiscal": fe.numero_fiscal,
            "estado": fe.estado,
            "error_message": fe.error_message,
        }, message=f"Factura {fe.estado}: CAE={fe.cae or 'pendiente'}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GenerarCsrRequest(BaseModel):
    cuit: str
    pto_vta: int
    razon_social: str = ""


@router.post("/afip/generar-csr", response_model=RespuestaData)
def generar_csr(
    data: GenerarCsrRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Genera una nueva clave privada RSA y un CSR para subir a ARCA."""
    try:
        result = afip_csr_service.generar_csr(
            db,
            cuit=data.cuit,
            pto_vta=data.pto_vta,
            razon_social=data.razon_social,
        )
        return RespuestaData(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/afip/descargar-clave", response_model=RespuestaData)
def descargar_clave(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Descarga la clave privada RSA generada (para guardar enbackup seguro)."""
    try:
        clave = afip_csr_service.descargar_clave_privada(db)
        return RespuestaData(data={"clave_pem": clave})
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/afip/certificado-info", response_model=RespuestaData)
def certificado_info(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Devuelve información del certificado guardado, o None si no hay."""
    cert_pem = get_config(db, "afip_cert")
    if not cert_pem:
        return RespuestaData(data=None)
    info = afip_csr_service.get_cert_info(db)
    return RespuestaData(data=info)


@router.get("/afip/certificado-pem", response_model=RespuestaData)
def certificado_pem(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Devuelve el contenido PEM del certificado guardado, o None si no hay."""
    cert_pem = get_config(db, "afip_cert")
    if not cert_pem:
        return RespuestaData(data=None)
    return RespuestaData(data={"cert_pem": cert_pem})


@router.get("/afip/csr-guardado", response_model=RespuestaData)
def csr_guardado(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Devuelve el CSR guardado en la DB, o None si no hay."""
    csr = afip_csr_service.get_csr_guardado(db)
    if not csr:
        return RespuestaData(data=None)
    return RespuestaData(data={"csr_pem": csr})


class SubirCertificadoRequest(BaseModel):
    cert_pem: str


class SubirKeyRequest(BaseModel):
    key_pem: str


class SubirPemRequest(BaseModel):
    contenido: str


class CargarCsrRequest(BaseModel):
    csr_pem: str


@router.post("/afip/cargar-csr", response_model=RespuestaData)
def cargar_csr(
    data: CargarCsrRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Guarda un CSR cargado desde archivo (para persistencia entre refrescos)."""
    afip_csr_service.guardar_csr(db, data.csr_pem)
    return RespuestaData(message="CSR guardado correctamente")


@router.post("/afip/subir-key", response_model=RespuestaData)
def subir_key(
    data: SubirKeyRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Guarda la clave privada .key en la configuracion."""
    from app.services.config_service import set_config
    set_config(db, "afip_key", data.key_pem, "Clave privada AFIP (PEM)")
    return RespuestaData(message="Clave privada guardada correctamente")


@router.post("/afip/subir-pem", response_model=RespuestaData)
def subir_pem(
    data: SubirPemRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Guarda contenido .pem (certificado o clave) en la configuracion."""
    from app.services.config_service import set_config
    contenido = data.contenido
    if "CERTIFICATE" in contenido:
        set_config(db, "afip_cert", contenido, "Certificado AFIP (PEM)")
        return RespuestaData(message="Certificado PEM guardado correctamente")
    elif "PRIVATE KEY" in contenido or "RSA PRIVATE KEY" in contenido:
        set_config(db, "afip_key", contenido, "Clave privada AFIP (PEM)")
        return RespuestaData(message="Clave privada PEM guardada correctamente")
    else:
        raise HTTPException(status_code=400, detail="El archivo PEM no parece ser un certificado ni una clave privada")


@router.post("/afip/subir-certificado", response_model=RespuestaData)
def subir_certificado(
    data: SubirCertificadoRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Guarda el certificado .crt devuelto por ARCA."""
    try:
        result = afip_csr_service.guardar_certificado(db, data.cert_pem)
        return RespuestaData(data=result, message=result["mensaje"])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
