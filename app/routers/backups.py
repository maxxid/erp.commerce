"""Router de Respaldos: backup local, subir/bajar de R2, listar."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import os
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData, RespuestaLista
from app.services import backup_service
from app.config import settings

router = APIRouter(prefix="/api/backups", tags=["Respaldos"])


class RestaurarRequest(BaseModel):
    filename: str
    origen: str = "local"  # "local" o "r2"


@router.get("/local", response_model=RespuestaLista)
def listar_locales(
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Lista backups locales disponibles."""
    backups = backup_service.listar_backups_locales()
    return RespuestaLista(data=backups, total=len(backups), message=f"{len(backups)} backup(s) local(es)")


@router.get("/r2", response_model=RespuestaLista)
def listar_r2(
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Lista backups en Cloudflare R2."""
    if not settings.R2_ENABLED:
        raise HTTPException(status_code=400, detail="R2 no está configurado (R2_ACCESS_KEY no definida)")
    backups = backup_service.listar_backups_r2()
    return RespuestaLista(data=backups, total=len(backups), message=f"{len(backups)} backup(s) en R2")


@router.post("/crear", response_model=RespuestaData)
def crear_backup(
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Crea un backup local de la base de datos."""
    try:
        nombre = backup_service.crear_backup_local()
        return RespuestaData(data={"filename": nombre}, message=f"Backup creado: {nombre}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subir", response_model=RespuestaData)
def subir_backup(
    filename: str,
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Sube un backup local a Cloudflare R2."""
    if not settings.R2_ENABLED:
        raise HTTPException(status_code=400, detail="R2 no está configurado")
    ok = backup_service.subir_a_r2(filename)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Backup local no encontrado: {filename}")
    return RespuestaData(data={"filename": filename}, message="Backup subido a R2")


@router.post("/descargar", response_model=RespuestaData)
def descargar_backup(
    filename: str,
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Descarga un backup desde R2 a la carpeta local."""
    if not settings.R2_ENABLED:
        raise HTTPException(status_code=400, detail="R2 no está configurado")
    filepath = backup_service.descargar_de_r2(filename)
    if not filepath:
        raise HTTPException(status_code=404, detail=f"No se pudo descargar: {filename}")
    return RespuestaData(data={"filename": filename, "path": filepath}, message="Backup descargado de R2")


@router.get("/descargar/{filename}")
def obtener_archivo_backup(
    filename: str,
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Descarga un archivo de backup local."""
    filepath = os.path.join(backup_service.BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")
    return FileResponse(filepath, media_type="application/gzip", filename=filename)


@router.post("/restaurar", response_model=RespuestaData)
def restaurar_backup(
    data: RestaurarRequest,
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Prepara un backup para restauración (descarga si es de R2, deja en carpeta local)."""
    filename = data.filename
    if data.origen == "r2":
        if not settings.R2_ENABLED:
            raise HTTPException(status_code=400, detail="R2 no está configurado")
        filepath = backup_service.descargar_de_r2(filename)
        if not filepath:
            raise HTTPException(status_code=404, detail=f"No se pudo descargar: {filename}")

    local_path = os.path.join(backup_service.BACKUP_DIR, filename)
    if not os.path.exists(local_path):
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")

    return RespuestaData(
        data={
            "filename": filename,
            "instrucciones": (
                "Para restaurar: 1) Detener el servidor. "
                "2) Descomprimir el archivo .gz. "
                "3) Reemplazar erp_comercio.db con el archivo descomprimido. "
                "4) Reiniciar el servidor."
            ),
        },
        message="Backup listo para restaurar. Seguí las instrucciones.",
    )


@router.delete("/local/{filename}", response_model=RespuestaData)
def eliminar_backup(
    filename: str,
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Elimina un backup local."""
    ok = backup_service.eliminar_backup_local(filename)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")
    return RespuestaData(message=f"Backup eliminado: {filename}")


@router.get("/estado", response_model=RespuestaData)
def estado_backup(
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Estado del sistema de respaldos."""
    return RespuestaData(
        data={
            "r2_habilitado": settings.R2_ENABLED,
            "backup_automatico_min": settings.BACKUP_INTERVAL_MIN,
            "backups_locales": len(backup_service.listar_backups_locales()),
            "ultimo_backup": backup_service.listar_backups_locales()[0] if backup_service.listar_backups_locales() else None,
        },
        message="Estado del sistema de respaldos",
    )
