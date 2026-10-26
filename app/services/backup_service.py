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
import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict
from urllib.parse import urlparse
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.services import config_service

BACKUP_DIR = settings.BACKUP_DIR or os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")

# Cada cuánto sube un respaldo a la nube. Lo local sale cada 15 minutos (cuesta
# un archivo rotado, sin red), pero lo que sale por el hotspot sí se dosifica:
# subir cada 15 minutos serían ~33 MB por día, y este negocio tiene internet
# limitado. Con una hora se pierde a lo sumo una hora de datos ante una
# catástrofe de máquina — el día a día no depende de esto, lo que sube las
# ventas del cajero es la cola offline, no los respaldos.
SUBIR_A_R2_CADA_MIN = 60

# Tope de archivos de la nube que se listan (paginados de a 100). Alcanza para
# más de un año de respaldos por hora; sirve de red de seguridad por si algún
# día se cae la rotación de R2 y el bucket crece sin control.
LIMITE_OBJETOS_R2 = 1000

# Réplica en vivo (Litestream — Fase G, ver FASE_G_CONTINUIDAD.md). Va subiendo
# archivos a este prefijo cada pocos segundos mientras la base cambia, y un
# snapshot por hora aunque no cambie nada: con saber cuándo se tocó el último
# alcanza para saber si la replicación sigue viva.
PREFIJO_REPLICA = "replica"

# Tope de archivos de la réplica que se listan (paginados de a 1000). Con
# retención de 24 h y snapshot cada hora el orden de magnitud es ~3.500.
LIMITE_OBJETOS_REPLICA = 5000

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
    """Crea un snapshot consistente de la base, comprimido (.gz)."""
    _ensure_backup_dir()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"erp_comercio_{ts}.db.gz"
    filepath = os.path.join(BACKUP_DIR, filename)
    temporal = filepath + ".part"

    # Snapshot por el backup API de SQLite y no copiando el archivo a mano:
    # con el POS vendiendo en ese instante, copiar a tientas puede agarrar la
    # base en medio de una escritura y dejar una copia que no abre (o peor,
    # que abre y no tiene la última venta).
    origen = sqlite3.connect(_db_path())
    destino = sqlite3.connect(temporal)
    try:
        origen.backup(destino)
    finally:
        destino.close()
        origen.close()

    try:
        with open(temporal, "rb") as src, gzip.open(filepath, "wb") as dst:
            shutil.copyfileobj(src, dst)
    finally:
        if os.path.exists(temporal):
            os.remove(temporal)

    _limpiar_backups_locales()
    return filename


def listar_backups_locales() -> List[dict]:
    _ensure_backup_dir()
    files = sorted(glob.glob(os.path.join(BACKUP_DIR, "*.db.gz")), reverse=True)
    resultados = []
    for f in files:
        nombre = os.path.basename(f)
        size = os.path.getsize(f)
        # UTC aware: sin la zona, la pantalla de respaldos mostraba la hora
        # de la máquina como si fuera UTC (3 h corridas en Argentina).
        mtime = datetime.fromtimestamp(os.path.getmtime(f), timezone.utc)
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
        # S3 devuelve 100 objetos por llamada y, si hay más, hay que volver a
        # pedir con la continuation token. Con una sola llamada se veían los
        # primeros 50, que son los más VIEJOS (los nombres ordenan por fecha),
        # y el chequeo de salud concluía "la nube no tiene respaldos frescos"
        # mientras afuera estaban subiendo los nuevos: alerta falsa.
        objetos = []
        token = None
        while True:
            params = {"Bucket": cfg["bucket"], "Prefix": f"backups/{mid}/", "MaxKeys": 100}
            if token:
                params["ContinuationToken"] = token
            resp = client.list_objects_v2(**params)
            objetos.extend(resp.get("Contents", []))
            if not resp.get("IsTruncated") or len(objetos) >= LIMITE_OBJETOS_R2:
                break
            token = resp.get("NextContinuationToken")
        resultados = []
        for obj in objetos:
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


def listar_replica_r2(db: Session) -> List[dict]:
    """Archivos de la réplica en vivo (Litestream) en la nube.

    Ordenados del más nuevo al más viejo (`fecha` en ISO). La lista viene
    paginada igual que los respaldos: con una sola llamada S3 devuelve 1000
    objetos de una página y no necesariamente los más nuevos, y un chequeo
    de salud que mira sólo la primera página puede dar una alerta falsa.
    """
    cfg = _get_r2_config(db)
    if not cfg:
        return []
    try:
        from app.services.licencia_service import obtener_machine_id
        mid = obtener_machine_id()
        client = _make_r2_client(cfg)
        objetos = []
        token = None
        while True:
            params = {"Bucket": cfg["bucket"], "Prefix": f"{PREFIJO_REPLICA}/{mid}/", "MaxKeys": 1000}
            if token:
                params["ContinuationToken"] = token
            resp = client.list_objects_v2(**params)
            objetos.extend(resp.get("Contents", []))
            if not resp.get("IsTruncated") or len(objetos) >= LIMITE_OBJETOS_REPLICA:
                break
            token = resp.get("NextContinuationToken")
        resultados = [
            {"clave": obj["Key"], "fecha": obj["LastModified"].isoformat()}
            for obj in objetos
        ]
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


def _debe_subirse_a_r2(db: Session) -> bool:
    """¿Pasó una hora desde la última subida buena? (o no se subió nunca)."""
    ultimo = config_service.get_config(db, "backup_ultimo_upload_r2")
    if not ultimo:
        return True
    try:
        cuando = datetime.fromisoformat(ultimo)
    except ValueError:
        return True
    if cuando.tzinfo is None:
        cuando = cuando.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - cuando).total_seconds() >= SUBIR_A_R2_CADA_MIN * 60


def backup_automatico():
    """Respaldo local en cada vuelta; a la nube, una hora por vez.

    Lo local es gratis (archivo rotado, sin red): sirve para "borré algo" o
    "la base se corrompió". Lo que consume el hotspot es la subida, y esa
    queda cada `SUBIR_A_R2_CADA_MIN`; si la subida falla, la marca de hora no
    se anota y el próximo respaldo reintenta a los 15 minutos.
    """
    try:
        nombre = crear_backup_local()
        db = SessionLocal()
        try:
            if _debe_subirse_a_r2(db) and subir_a_r2(nombre, db):
                config_service.set_config(
                    db, "backup_ultimo_upload_r2", datetime.now(timezone.utc).isoformat(),
                    "Última vez que un respaldo subió a la nube (R2)",
                )
        finally:
            db.close()
    except Exception:
        pass
