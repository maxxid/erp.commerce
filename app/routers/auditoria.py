"""Router de Auditoría POS."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaLista
from app.services import auditoria_service

router = APIRouter(prefix="/api/auditoria", tags=["Auditoría"])


@router.get("", response_model=RespuestaLista)
def listar(
    usuario_id: Optional[int] = Query(None),
    tipo: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Lista eventos de auditoría con detección de carritos abandonados."""
    data, total = auditoria_service.listar_con_carritos_abandonados(
        db, usuario_id=usuario_id, tipo=tipo, page=page, page_size=page_size
    )
    return RespuestaLista(data=data, total=total, page=page, page_size=page_size, message=f"{total} evento(s)")
