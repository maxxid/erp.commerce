"""Router de configuración de IA (Ajustes > Inteligencia Artificial).

La key es write-only: se puede guardar o borrar, nunca se lee. El snapshot que
devuelve GET solo trae la máscara y el origen. El plan de la licencia decide si
la IA está disponible (`plan_incluye_ia`); guardar la config no requiere el
plan, pero probarla sí, para que el upsell salga del backend y no de una
condición replicada en el frontend.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.dependencies import requiere_feature, require_role
from app.database import get_db
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData
from app.services import auditoria_service, config_service, planes_service
from app.services.ia import registro
from app.services import ticket_proveedor_service as ticket_servicio

router = APIRouter(prefix="/api/ia", tags=["IA"])


class IAConfigUpdate(BaseModel):
    habilitada: bool | None = None
    provider: str | None = None
    api_key: str | None = None  # write-only: ausente = no tocar, "" = borrar
    base_url: str | None = None
    modelo: str | None = None
    limite_mes: int | None = None


class ParsearTicketRequest(BaseModel):
    texto: str


def _snapshot(db: Session) -> dict:
    cfg = registro.configuracion(db)
    return {
        **cfg,
        "limite_configurado": config_service.get_config(db, registro.CLAVE_LIMITE_MES),
        "plan": planes_service.plan_de(db),
        "plan_incluye_ia": planes_service.tiene_feature(db, "ia"),
        "disponible": bool(cfg["habilitada"]) and planes_service.tiene_feature(db, "ia"),
    }


@router.get("/config", response_model=RespuestaData)
def obtener_config(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Configuración de IA para la UI. Nunca incluye la key cruda."""
    return RespuestaData(data=_snapshot(db))


@router.put("/config", response_model=RespuestaData)
def actualizar_config(
    data: IAConfigUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    cambios = {campo: getattr(data, campo) for campo in data.model_fields_set}
    try:
        registro.guardar(db, cambios)
    except ValueError as err:
        return RespuestaData(data=_snapshot(db), message=str(err))

    if "api_key" in cambios:
        accion = "ia_api_key_borrada" if not (cambios["api_key"] or "").strip() else "ia_api_key_guardada"
        auditoria_service.registrar(db, user.id, accion, None, None, {
            "origen": "ajustes",
        })
    return RespuestaData(data=_snapshot(db), message="Configuración de IA actualizada")


@router.post("/probar", response_model=RespuestaData)
def probar_conexion(
    db: Session = Depends(get_db),
    _plan: Usuario = Depends(requiere_feature("ia")),
):
    """Ping real contra el proveedor. 402 si el plan no incluye IA."""
    resultado = registro.probar(db)
    return RespuestaData(data=resultado, message=resultado["detalle"])


@router.post("/parsear-ticket", response_model=RespuestaData)
def parsear_ticket(
    data: ParsearTicketRequest,
    db: Session = Depends(get_db),
    _user: Usuario = Depends(require_role("admin", "encargado", "repositor")),
    _plan: Usuario = Depends(requiere_feature("ia")),
):
    """Parsea un ticket de proveedor con IA y devuelve los artículos detectados."""
    from app.services.ia.proveedor import ErrorProveedor, IADeshabilitada, LimiteAgotado

    texto = (data.texto or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El texto del ticket está vacío")

    try:
        respuesta = registro.completar(
            db,
            sistema=ticket_servicio.SISTEMA_IA,
            usuario=ticket_servicio.prompt_ia(texto),
            como_json=True,
            max_tokens=2048,
            temperatura=0.0,
        )
    except IADeshabilitada as err:
        raise HTTPException(status_code=402, detail=str(err))
    except LimiteAgotado as err:
        raise HTTPException(status_code=409, detail=str(err))
    except ErrorProveedor as err:
        raise HTTPException(status_code=502, detail=f"El proveedor de IA falló: {err}")

    try:
        resultado = ticket_servicio.interpretar_ia(respuesta.texto)
    except ValueError as err:
        raise HTTPException(status_code=502, detail=f"Respuesta ilegible de la IA: {err}")

    return RespuestaData(
        data={
            "items": resultado["items"],
            "no_reconocidos": resultado["no_reconocidos"],
            "tokens_out": respuesta.tokens_out or 0,
        },
        message=f"{len(resultado['items'])} artículo(s) detectado(s)",
    )
