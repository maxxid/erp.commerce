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


class PosConfigRequest(BaseModel):
    showStatsPanel: bool = True
    productViewMode: str = "grilla"
    enabledPaymentMethods: list[str] = []


@router.get("/pos", response_model=RespuestaData)
def get_pos_config(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Obtiene la configuración de preferencias del POS."""
    configs = db.query(Configuracion).filter(
        Configuracion.clave.in_([
            "pos_show_stats_panel",
            "pos_product_view_mode",
            "pos_enabled_payment_methods"
        ])
    ).all()
    data = {}
    for c in configs:
        if c.clave == "pos_enabled_payment_methods":
            import json
            try:
                data[c.clave] = json.loads(c.valor_texto or c.valor or "[]")
            except:
                data[c.clave] = []
        else:
            data[c.clave] = c.valor_texto or c.valor
    # Defaults
    defaults = {
        "pos_show_stats_panel": "true",
        "pos_product_view_mode": "grilla",
        "pos_enabled_payment_methods": [
            "efectivo", "transferencia", "mercadopago_qr",
            "qr_interop", "mercadopago_pos", "smartpoint", "cta_corriente"
        ]
    }
    for k, v in defaults.items():
        if k not in data:
            data[k] = v
    return RespuestaData(data=data)


@router.put("/pos", response_model=RespuestaData)
def set_pos_config(
    data: PosConfigRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Actualiza la configuración de preferencias del POS."""
    import json
    set_config(db, "pos_show_stats_panel", str(data.showStatsPanel).lower(),
               "Mostrar panel lateral derecho (mini dashboard) en POS")
    set_config(db, "pos_product_view_mode", data.productViewMode,
               "Vista de productos por defecto en POS: grilla | lista")
    set_config(db, "pos_enabled_payment_methods", json.dumps(data.enabledPaymentMethods),
               "Medios de pago habilitados en POS (JSON array)")
    return RespuestaData(
        data={
            "showStatsPanel": data.showStatsPanel,
            "productViewMode": data.productViewMode,
            "enabledPaymentMethods": data.enabledPaymentMethods
        },
        message="Configuración POS actualizada"
    )
