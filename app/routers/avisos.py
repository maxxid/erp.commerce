"""Router del aviso proactivo de stock bajo (Telegram)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import RespuestaData
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.services import avisos_service

router = APIRouter(prefix="/api/avisos", tags=["Avisos"])


@router.post("/probar", response_model=RespuestaData)
def probar_aviso(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Manda un mensaje de prueba al canal de Telegram, ahora mismo."""
    ok, detalle = avisos_service.probar_envio(db, user.id)
    if not ok:
        return RespuestaData(ok=False, data={"ok": False, "detalle": detalle}, message=detalle)
    return RespuestaData(data={"ok": True, "detalle": detalle}, message="Mensaje de prueba enviado")
