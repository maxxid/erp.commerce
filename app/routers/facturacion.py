"""Router de Facturación Electrónica AFIP."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.factura_electronica import FacturaElectronica
from app.services.venta_service import obtener_venta
from app.services import afip_service

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
        return RespuestaData(data={
            "id": fe.id,
            "cae": fe.cae,
            "numero_fiscal": fe.numero_fiscal,
            "estado": fe.estado,
            "error_message": fe.error_message,
        }, message=f"Factura {fe.estado}: CAE={fe.cae or 'pendiente'}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
