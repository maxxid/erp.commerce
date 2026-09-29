"""Router de Recargas: configuración y cálculo del servicio de recargas.

El POS necesita leer la config (cualquier usuario logueado) y Ajustes escribirla
(admin o encargado).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_role
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData
from app.services import auditoria_service, recarga_service

router = APIRouter(prefix="/api/recargas", tags=["Recargas"])


class RecargaConfigUpdate(BaseModel):
    monto_base: Optional[float] = Field(None, gt=0)
    adicional_pct: Optional[float] = Field(None, ge=0, le=100)
    medio_pago_carga: Optional[str] = None
    producto_id: Optional[int] = None


@router.get("/config", response_model=RespuestaData)
def obtener_configuracion(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Configuración de recargas + el precio de venta de una unidad (base + adicional)."""
    cfg = recarga_service.get_config(db)
    producto = recarga_service.producto_recarga(db)
    cfg["medios_pago_disponibles"] = recarga_service.MEDIOS_PAGO_CARGA
    cfg["producto"] = (
        {"id": producto.id, "nombre": producto.nombre, "precio_venta": producto.precio_venta}
        if producto
        else None
    )
    return RespuestaData(data=cfg)


@router.put("/config", response_model=RespuestaData)
def actualizar_configuracion(
    data: RecargaConfigUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Guarda la configuración de recargas."""
    anterior = recarga_service.get_config(db)
    try:
        nueva = recarga_service.set_config(
            db,
            monto_base=data.monto_base,
            adicional_pct=data.adicional_pct,
            medio_pago_carga=data.medio_pago_carga,
            producto_id=data.producto_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    cambios = {
        k: {"anterior": anterior.get(k), "nuevo": nueva.get(k)}
        for k in ("monto_base", "adicional_pct", "medio_pago_carga", "producto_id")
        if anterior.get(k) != nueva.get(k)
    }
    if cambios:
        auditoria_service.registrar(db, user.id, "recargas_config_editada", None, None, cambios)

    nueva["medios_pago_disponibles"] = recarga_service.MEDIOS_PAGO_CARGA
    return RespuestaData(data=nueva, message="Configuración de recargas actualizada")


@router.get("/calculo", response_model=RespuestaData)
def calcular_recarga(
    unidades: float = Query(1, ge=0, description="Cantidad de unidades de recarga"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Desglose de una recarga: monto cargado, adicional y total a cobrar."""
    cfg = recarga_service.get_config(db)
    return RespuestaData(data=recarga_service.calcular(unidades, cfg))
