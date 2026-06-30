"""Router de Configuración del Sistema (Ajustes AFIP)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.schemas.common import RespuestaData
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.configuracion import Configuracion
from app.services.config_service import set_config, get_config
from app.services import auditoria_service

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
    configs = db.query(Configuracion).all()
    data = {
        c.clave: {
            "valor": c.valor_texto or c.valor,
            "descripcion": c.descripcion,
        }
        for c in configs
    }
    return RespuestaData(data=data)


@router.put("/ajustes", response_model=RespuestaData)
def actualizar_ajuste(
    data: ConfigUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Actualiza un valor de configuración."""
    valor_anterior = get_config(db, data.clave)
    set_config(db, data.clave, data.valor, data.descripcion)

    if data.clave == "telefono_dueño" and valor_anterior != data.valor:
        auditoria_service.registrar(db, user.id, "telefono_dueño_editado", None, None, {
            "clave": data.clave,
            "valor_anterior": valor_anterior,
            "valor_nuevo": data.valor,
        })

    return RespuestaData(data={"clave": data.clave, "valor": data.valor}, message=f"Configuración '{data.clave}' actualizada")
