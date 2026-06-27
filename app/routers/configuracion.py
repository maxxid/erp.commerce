"""Router de Configuración del Sistema (Ajustes AFIP)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.schemas.common import RespuestaData
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.configuracion import Configuracion
from app.services.config_service import set_config

router = APIRouter(prefix="/api/config", tags=["Configuración"])


class ConfigUpdate(BaseModel):
    clave: str
    valor: str
    descripcion: str = ""


@router.get("/ajustes", response_model=RespuestaData)
def listar_ajustes(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Lista todas las configuraciones del sistema."""
    configs = db.query(Configuracion).filter(
        Configuracion.clave.like("afip_%")
    ).all()
    data = {
        c.clave: {
            "valor": c.valor_texto or c.valor,
            "descripcion": c.descripcion,
        }
        for c in configs
    }
    # Valores por defecto desde env
    import os
    defaults = {
        "afip_mode": os.getenv("AFIP_MODE", "testing"),
        "afip_cuit": os.getenv("AFIP_CUIT", ""),
        "afip_pto_vta": os.getenv("AFIP_PTO_VTA", "1"),
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = {"valor": v, "descripcion": ""}
    return RespuestaData(data=data)


@router.put("/ajustes", response_model=RespuestaData)
def actualizar_ajuste(
    data: ConfigUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Actualiza un valor de configuración."""
    set_config(db, data.clave, data.valor, data.descripcion)
    return RespuestaData(message=f"Configuración '{data.clave}' actualizada")
