"""Servicio de respaldo: backup local + sincronización con Cloudflare R2.

- Backup local: copia la DB a la carpeta backups/ con timestamp.
- Config R2: persistida en tabla Configuracion (claves r2_endpoint, r2_access_key, etc.)
  con fallback a variables de entorno.
- Subir/bajar de R2 (S3-compatible).
- Listar backups locales y remotos.
"""

import os
import shutil
import gzip
import glob
from datetime import datetime, timezone
from typing import Optional, List, Dict
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.config import settings

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")

def _db_path() -> str:
    """Extrae la ruta del archivo SQLite desde settings.DATABASE_URL."""
    raw = settings.DATABASE_URL
    if not raw.startswith("sqlite:///"):
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "erp_comercio.db")
    path = raw[len("sqlite:///"):]
    # Si es relativo, resolver contra current working directory (como hace SQLAlchemy)
    if not os.path.isabs(path):
        path = os.path.join(os.getcwd(), path)
    return os.path.normpath(path)


def _ensure_backup_dir():
    os.makedirs(BACKUP_DIR, exist_ok=True)


def _make_r2_client(cfg: dict):
    """Crea un cliente S3 boto3 con la configuración dada."""
    import boto3
    return boto3.client(
        "s3",
        endpoint_url=cfg["endpoint"],
        aws_access_key_id=cfg["access_key"],
        aws_secret_access_key=cfg["secret_key"],
    )


def _get_r2_config(db: Session) -> Optional[dict]:
    """Obtiene la configuración R2: primero DB, luego env vars."""
    from app.models.configuracion import Configuracion

    if db:
        rows = db.query(Configuracion).filter(Configuracion.clave.in_([
            "r2_endpoint", "r2_access_key", "r2_secret_key", "r2_bucket"
        ])).all()
        cfg_db = {r.clave: r.valor for r in rows}
        if cfg_db.get("r2_endpoint") and cfg_db.get("r2_access_key") and cfg_db.get("r2_secret_key"):
            return {
                "endpoint": cfg_db["r2_endpoint"],
                "access_key": cfg_db["r2_access_key"],
                "secret_key": cfg_db["r2_secret_key"],
                "bucket": cfg_db.get("r2_bucket", "erp-backups"),
            }

    # Fallback a env vars
    if settings.R2_ENDPOINT and settings.R2_ACCESS_KEY and settings.R2_SECRET_KEY:
        return {
            "endpoint": settings.R2_ENDPOINT,
            "access_key": settings.R2_ACCESS_KEY,
            "secret_key": settings.R2_SECRET_KEY,
            "bucket": settings.R2_BUCKET,
        }
    return None


def _guardar_r2_config(db: Session, claves: dict):
    """Guarda la configuración R2 en la tabla Configuracion."""
    from app.models.configuracion import Configuracion
    for clave, valor in claves.items():
        row = db.query(Configuracion).filter(Configuracion.clave == clave).first()
        if row:
            row.valor = valor
        else:
            db.add(Configuracion(clave=clave, valor=valor, descripcion=f"R2: {clave}"))
    db.commit()


def crear_backup_local() -> str:
    """Crea un backup comprimido (.gz). Retorna el nombre del archivo."""
    _ensure_backup_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"erp_comercio_{ts}.db.gz"
    filepath = os.path.join(BACKUP_DIR, filename)

    with open(_db_path(), "rb") as src, gzip.open(filepath, "wb") as dst:
        shutil.copyfileobj(src, dst)

    _limpiar_backups_locales()
    return filename


def listar_backups_locales() -> List[dict]:
    _ensure_backup_dir()
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.db.gz")), reverse=True)
    resultados = []
    for f in files:
        nombre = os.path.basename(f)
        size = os.path.getsize(f)
        mtime = datetime.fromtimestamp(os.path.getmtime(f))
        resultados.append({"nombre": nombre, "size": size, "fecha": mtime.isoformat(), "ubicacion": "local"})
    return resultados


def subir_a_r2(filename: str, db: Session) -> bool:
    cfg = _get_r2_config(db)
    if not cfg:
        return False
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        return False
    try:
        from app.services.licencia_service import obtener_machine_id
        mid = obtener_machine_id()
        client = _make_r2_client(cfg)
        key = f"backups/{mid}/{filename}"
        client.upload_file(filepath, cfg["bucket"], key)
        return True
    except Exception:
        return False


def listar_backups_r2(db: Session) -> List[dict]:
    cfg = _get_r2_config(db)
    if not cfg:
        return []
    try:
        from app.services.licencia_service import obtener_machine_id
        mid = obtener_machine_id()
        client = _make_r2_client(cfg)
        resp = client.list_objects_v2(Bucket=cfg["bucket"], Prefix=f"backups/{mid}/", MaxKeys=50)
        resultados = []
        for obj in resp.get("Contents", []):
            resultados.append({
                "nombre": obj["Key"].split("/")[-1],
                "key": obj["Key"],
                "size": obj["Size"],
                "fecha": obj["LastModified"].isoformat(),
                "ubicacion": "r2",
            })
        resultados.sort(key=lambda x: x["fecha"], reverse=True)
        return resultados
    except Exception:
        return []


def descargar_de_r2(filename: str, db: Session) -> Optional[str]:
    cfg = _get_r2_config(db)
    if not cfg:
        return None
    _ensure_backup_dir()
    from app.services.licencia_service import obtener_machine_id
    mid = obtener_machine_id()
    filepath = os.path.join(BACKUP_DIR, filename)
    try:
        client = _make_r2_client(cfg)
        key = f"backups/{mid}/{filename}"
        client.download_file(cfg["bucket"], key, filepath)
        return filepath
    except Exception:
        return None


def eliminar_backup_r2(filename: str, db: Session) -> bool:
    cfg = _get_r2_config(db)
    if not cfg:
        return False
    try:
        from app.services.licencia_service import obtener_machine_id
        mid = obtener_machine_id()
        client = _make_r2_client(cfg)
        key = f"backups/{mid}/{filename}"
        client.delete_object(Bucket=cfg["bucket"], Key=key)
        return True
    except Exception:
        return False


def eliminar_backup_local(filename: str) -> bool:
    filepath = os.path.join(BACKUP_DIR, filename)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False


def _limpiar_backups_locales():
    if settings.BACKUP_KEEP_LOCAL <= 0:
        return
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.db.gz")))
    while len(files) > settings.BACKUP_KEEP_LOCAL:
        os.remove(files.pop(0))


def backup_automatico():
    """Crea backup local y sube a R2 si está configurado."""
    from app.database import SessionLocal
    try:
        nombre = crear_backup_local()
        db = SessionLocal()
        try:
            subir_a_r2(nombre, db)
        finally:
            db.close()
    except Exception:
        pass
