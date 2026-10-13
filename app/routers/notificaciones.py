"""Router de Notificaciones: la campana del header.

`GET /api/notificaciones` genera los avisos vigentes (una sola vez por clave
y día) y devuelve los últimos 100 con su estado de lectura para el usuario
que pide. Marcar como leída respeta el modo elegido en Ajustes
(`avisos_lectura`): usuario o global.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.notificacion import Notificacion
from app.models.usuario import Usuario
from app.auth.dependencies import get_current_user
from app.schemas.common import RespuestaData
from app.services import notificaciones_service

router = APIRouter(prefix="/api/notificaciones", tags=["Notificaciones"])


@router.get("", response_model=RespuestaData)
def listar_notificaciones(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Genera los avisos vigentes y devuelve los últimos con su lectura."""
    notificaciones_service.generar(db)
    return RespuestaData(data=notificaciones_service.listar(db, user))


@router.post("/leer-todas", response_model=RespuestaData)
def marcar_todas(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Marca todas las notificaciones como leídas."""
    total = notificaciones_service.marcar_todas(db, user)
    return RespuestaData(data={"marcadas": total}, message=f"{total} notificación(es) marcadas como leídas")


@router.post("/{notificacion_id}/leer", response_model=RespuestaData)
def marcar_leida(
    notificacion_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Marca una notificación como leída."""
    if not notificaciones_service.marcar_leida(db, notificacion_id, user):
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    return RespuestaData(data={"id": notificacion_id}, message="Notificación marcada como leída")
