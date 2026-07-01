"""Router de Auditoría POS."""

from typing import Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaLista, RespuestaData
from app.services import auditoria_service

router = APIRouter(prefix="/api/auditoria", tags=["Auditoría"])

ESTADOS_VALIDOS = {"sospechoso", "normal", "descartado", "fraude"}


@router.get("", response_model=RespuestaLista)
def listar(
    usuario_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    estado: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Lista eventos de auditoría con detección de carritos abandonados."""
    data, total = auditoria_service.listar_con_carritos_abandonados(
        db, usuario_id=usuario_id, tipo=tipo, estado=estado, page=page, page_size=page_size
    )
    return RespuestaLista(data=data, total=total, page=page, page_size=page_size, message=f"{total} evento(s)")


@router.patch("/{evento_id}/estado", response_model=RespuestaData)
def cambiar_estado(
    evento_id: int,
    estado: Literal["normal", "descartado", "fraude"] = Body(...),
    nota: Optional[str] = Body(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Cambia el estado de un evento: normal | descartado | fraude."""
    resultado = auditoria_service.cambiar_estado(db, evento_id, user.id, estado, nota)
    if not resultado or not resultado.get("actualizado"):
        raise HTTPException(status_code=404, detail="Evento no encontrado")
    return RespuestaData(message=f"Estado cambiado a {estado}")
