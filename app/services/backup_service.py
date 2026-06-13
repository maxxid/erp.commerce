"""Servicio de respaldo: backup local + sincronización con Cloudflare R2.

- Backup local: copia la DB a la carpeta backups/ con timestamp.
- Subir/bajar de R2 (S3-compatible).
- Listar backups locales y remotos.
- Restauración: descarga y deja listo para reemplazo manual.
"""

import os
import shutil
import gzip
import glob
from datetime import datetime, timezone
from typing import List, Optional
from app.config import settings


BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "erp_comercio.db")


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _r2_client():
    """Crea un cliente S3 para Cloudflare R2."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY,
        aws_secret_access_key=settings.R2_SECRET_KEY,
    )


def crear_backup_local() -> str:
    """Crea un backup comprimido (.gz) en la carpeta backups/. Retorna el nombre del archivo."""
    _ensure_backup_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"erp_comercio_{ts}.db.gz"
    filepath = os.path.join(BACKUP_DIR, filename)

    with open(DB_PATH, "rb") as src, gzip.open(filepath, "wb") as dst:
        shutil.copyfileobj(src, dst)

    _limpiar_backups_locales()
    return filename


def listar_backups_locales() -> List[dict]:
    """Lista los backups locales disponibles."""
    _ensure_backup_dir()
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.db.gz")), reverse=True)
    resultados = []
    for f in files:
        nombre = os.path.basename(f)
        size = os.path.getsize(f)
        mtime = datetime.fromtimestamp(os.path.getmtime(f))
        resultados.append({"nombre": nombre, "size": size, "fecha": mtime.isoformat(), "ubicacion": "local"})
    return resultados


def subir_a_r2(filename: str) -> bool:
    """Sube un backup local a Cloudflare R2."""
    if not settings.R2_ENABLED:
        return False
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return False
    try:
        client = _r2_client()
        client.upload_file(filepath, settings.R2_BUCKET, filename)
        return True
    except Exception:
        return False


def listar_backups_r2() -> List[dict]:
    """Lista backups en Cloudflare R2."""
    if not settings.R2_ENABLED:
        return []
    try:
        client = _r2_client()
        resp = client.list_objects_v2(Bucket=settings.R2_BUCKET, MaxKeys=50)
        resultados = []
        for obj in resp.get("Contents", []):
            resultados.append({
                "nombre": obj["Key"],
                "size": obj["Size"],
                "fecha": obj["LastModified"].isoformat(),
                "ubicacion": "r2",
            })
        resultados.sort(key=lambda x: x["fecha"], reverse=True)
        return resultados
    except Exception:
        return []


def descargar_de_r2(filename: str) -> Optional[str]:
    """Descarga un backup de R2 a la carpeta local. Retorna la ruta local."""
    if not settings.R2_ENABLED:
        return None
    _ensure_backup_dir()
    filepath = os.path.join(BACKUP_DIR, filename)
    try:
        client = _r2_client()
        client.download_file(settings.R2_BUCKET, filename, filepath)
        return filepath
    except Exception:
        return None


def eliminar_backup_local(filename: str) -> bool:
    """Elimina un backup local."""
    filepath = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def _limpiar_backups_locales():
    """Conserva solo los últimos N backups locales."""
    if settings.BACKUP_KEEP_LOCAL <= 0:
        return
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.db.gz")))
    while len(files) > settings.BACKUP_KEEP_LOCAL:
        os.remove(files.pop(0))


def backup_automatico():
    """Crea backup local y sube a R2 si está habilitado."""
    try:
        nombre = crear_backup_local()
        if settings.R2_ENABLED:
            subir_a_r2(nombre)
    except Exception:
        pass
