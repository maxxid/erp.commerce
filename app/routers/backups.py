"""Router de Respaldos: backup local, subir/bajar de R2, listar, configurar R2."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
import os
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaBase, RespuestaData, RespuestaLista
from app.services import backup_service
from app.config import settings

router = APIRouter(prefix="/api/backups", tags=["Respaldos"])


class RestaurarRequest(BaseModel):
    filename: str
    origen: str = "local"


class R2ConfigRequest(BaseModel):
    endpoint: str = ""
    access_key: str = ""
    secret_key: str = ""
    bucket: str = "erp-backups"


def _r2_ok(db: Session) -> bool:
    return backup_service._get_r2_config(db) is not None


@router.get("/local", response_model=RespuestaLista)
def listar_locales(user: Usuario = Depends(require_role("admin", "encargado"))):
    backups = backup_service.listar_backups_locales()
    return RespuestaLista(data=backups, total=len(backups), message=f"{len(backups)} backup(s) local(es)")


@router.get("/r2", response_model=RespuestaLista)
def listar_r2(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    if not _r2_ok(db):
        raise HTTPException(status_code=400, detail="R2 no está configurado")
    backups = backup_service.listar_backups_r2(db)
    return RespuestaLista(data=backups, total=len(backups), message=f"{len(backups)} backup(s) en R2")


@router.post("/crear", response_model=RespuestaData)
def crear_backup(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    try:
        nombre = backup_service.crear_backup_local()
        if _r2_ok(db):
            backup_service.subir_a_r2(nombre, db)
        return RespuestaData(data={"filename": nombre}, message=f"Backup creado: {nombre}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/subir")
def subir_backup(filename: str, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    if not _r2_ok(db):
        raise HTTPException(status_code=400, detail="R2 no está configurado")
    ok = backup_service.subir_a_r2(filename, db)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")
    return RespuestaData(data={"filename": filename}, message="Backup subido a R2")


@router.post("/descargar")
def descargar_backup(filename: str, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    if not _r2_ok(db):
        raise HTTPException(status_code=400, detail="R2 no está configurado")
    filepath = backup_service.descargar_de_r2(filename, db)
    if not filepath:
        raise HTTPException(status_code=404, detail=f"No se pudo descargar: {filename}")
    return RespuestaData(data={"filename": filename, "path": filepath}, message="Backup descargado de R2")


@router.get("/descargar/{filename}")
def obtener_archivo_backup(filename: str, user: Usuario = Depends(require_role("admin", "encargado"))):
    filepath = os.path.join(backup_service.BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")
    return FileResponse(filepath, media_type="application/gzip", filename=filename)


@router.delete("/local/{filename}", response_model=RespuestaBase)
def eliminar_backup(filename: str, user: Usuario = Depends(require_role("admin", "encargado"))):
    ok = backup_service.eliminar_backup_local(filename)
    if not ok:
        raise HTTPException(status_code=404, detail=f"Backup no encontrado: {filename}")
    return RespuestaBase(message=f"Backup eliminado: {filename}")


@router.delete("/r2/{filename}", response_model=RespuestaBase)
def eliminar_backup_r2(filename: str, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    if not _r2_ok(db):
        raise HTTPException(status_code=400, detail="R2 no está configurado")
    ok = backup_service.eliminar_backup_r2(filename, db)
    if not ok:
        raise HTTPException(status_code=404, detail=f"No se pudo eliminar de R2: {filename}")
    return RespuestaBase(message=f"Backup eliminado de R2: {filename}")


@router.get("/estado", response_model=RespuestaData)
def estado_backup(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    locales = backup_service.listar_backups_locales()
    r2_cfg = backup_service._get_r2_config(db)
    return RespuestaData(
        data={
            "r2_habilitado": r2_cfg is not None,
            "r2_endpoint": r2_cfg.get("endpoint", "")[:40] + "..." if r2_cfg else "",
            "r2_bucket": r2_cfg.get("bucket", "") if r2_cfg else "",
            "backup_automatico_min": settings.BACKUP_INTERVAL_MIN,
            "backups_locales": len(locales),
            "ultimo_backup": locales[0] if locales else None,
        },
        message="Estado del sistema de respaldos",
    )


@router.post("/test-r2", response_model=RespuestaBase)
def test_r2(data: R2ConfigRequest, user: Usuario = Depends(require_role("admin", "encargado"))):
    cfg = {"endpoint": data.endpoint, "access_key": data.access_key, "secret_key": data.secret_key, "bucket": data.bucket}
    try:
        client = backup_service._make_r2_client(cfg)
        client.list_objects_v2(Bucket=data.bucket, MaxKeys=1)
        return RespuestaBase(message="Conexión exitosa a R2")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error de conexión: {str(e)[:200]}")


@router.put("/config-r2", response_model=RespuestaBase)
def configurar_r2(data: R2ConfigRequest, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    claves = {
        "r2_endpoint": data.endpoint,
        "r2_access_key": data.access_key,
        "r2_secret_key": data.secret_key,
        "r2_bucket": data.bucket,
    }
    backup_service._guardar_r2_config(db, claves)
    return RespuestaBase(message="Configuración R2 guardada")


@router.post("/upload-db", response_model=RespuestaData)
async def subir_db(
    file: UploadFile = File(...),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Sube un archivo .db o .db.gz desde la PC local a la carpeta de backups."""
    filename = file.filename or "uploaded.db"
    if not (filename.endswith(".db") or filename.endswith(".db.gz") or filename.endswith(".gz")):
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .db o .db.gz")

    save_path = os.path.join(backup_service.BACKUP_DIR, filename)
    os.makedirs(backup_service.BACKUP_DIR, exist_ok=True)

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    instrucciones = (
        "Para restaurar en Oracle, ejecutá en la terminal del servidor:\n"
        f"  sudo systemctl stop erp-comercio\n"
        f"  cp '{save_path}' /data/erp/erp_comercio.db\n"
        f"  sudo chown erp:erp /data/erp/erp_comercio.db\n"
        f"  sudo systemctl start erp-comercio"
    )

    return RespuestaData(
        data={
            "filename": filename,
            "size": len(content),
            "path": save_path,
            "instrucciones": instrucciones,
        },
        message=f"Archivo subido: {filename} ({len(content)} bytes)",
    )
