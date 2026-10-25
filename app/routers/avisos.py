"""Router del aviso proactivo de stock bajo (Telegram)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.common import RespuestaData
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.services import avisos_service, config_service

router = APIRouter(prefix="/api/avisos", tags=["Avisos"])


@router.get("/bot/estado", response_model=RespuestaData)
def estado_bot(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin"))):
    """Diagnóstico del bot interactivo de Telegram (sin exponer el token)."""
    token = config_service.get_config(db, "telegram_bot_token") or ""
    chat_id = config_service.get_config(db, "telegram_chat_id") or ""
    interactivo = (config_service.get_config(db, "telegram_bot_interactivo") or "").lower() == "true"
    offset = config_service.get_config(db, "telegram_bot_offset") or "0"
    habilitado = (config_service.get_config(db, "stock_aviso_enabled") or "").lower() == "true"
    return RespuestaData(data={
        "token_configurado": bool(token),
        "chat_id_configurado": bool(chat_id),
        "chat_id": chat_id,
        "interactivo": interactivo,
        "aviso_habilitado": habilitado,
        "offset": offset,
    }, message="OK")


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
