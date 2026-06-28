"""Servicio de Catálogo Central: exportar productos reales a JSON, subir/bajar de R2.

- Exporta solo productos con código de barras real (empiezan con dígito).
- No exporta *MANUAL*, *TEMP ni productos sin código real.
- Sube a R2 en catalogo/{machine_id}/productos.json (se pisa).
- Permite descargar/importar un catálogo mergeado (catalogo_completo.json).
- El catálogo importado se mantiene en memoria para lookup rápido.
"""

import json
import os
import hashlib
from datetime import datetime, timezone
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from app.models.producto import Producto
from app.services.backup_service import _get_r2_config, _make_r2_client
from app.services.licencia_service import obtener_machine_id

CATALOGO_LOCAL_FILE = "catalogo_completo.json"

# Catálogo en memoria: dict[barcode] = {nombre, marca, categoria, precio_referencia, imagen_url}
_catalogo_memoria: Dict[str, dict] = {}
_catalogo_cargado = False


def cargar_catalogo_memoria(force=False) -> int:
    """Carga el catálogo local (catalogo_completo.json) en memoria.
    Retorna cuántos productos se cargaron. Si ya está cargado y force=False, no hace nada."""
    global _catalogo_memoria, _catalogo_cargado
    if _catalogo_cargado and not force:
        return len(_catalogo_memoria)

    path = _catalogo_path()
    if not os.path.exists(path):
        return 0

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _catalogo_memoria = {p["codigo_barras"]: p for p in data}
        _catalogo_cargado = True
        return len(_catalogo_memoria)
    except Exception:
        return 0


def buscar_en_catalogo(barcode: str) -> Optional[dict]:
    """Busca un código de barras en el catálogo en memoria."""
    cargar_catalogo_memoria()
    return _catalogo_memoria.get(barcode)


def _catalogo_path() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, CATALOGO_LOCAL_FILE)


def _es_barcode_real(codigo: str) -> bool:
    """True si es un código de barras real (empieza con dígito)."""
    return bool(codigo) and codigo[0].isdigit()


def exportar_productos(db: Session) -> dict:
    """Exporta productos con barcode real a un dict listo para JSON."""
    productos = (
        db.query(Producto)
        .filter(Producto.activo == True, Producto.codigo_barras.isnot(None))
        .all()
    )
    data = []
    for p in productos:
        if not _es_barcode_real(p.codigo_barras):
            continue
        data.append({
            "codigo_barras": p.codigo_barras,
            "nombre": p.nombre or "",
            "marca": p.marca or "",
            "descripcion": p.descripcion or "",
            "precio_referencia": p.precio_referencia,
            "precio_venta": p.precio_venta,
            "imagen_url": p.imagen_url or "",
            "sku": p.sku or "",
            "propiedades": p.propiedades,
            "fuente": p.fuente or "",
            "categoria_nombre": p.categoria.nombre if p.categoria else "",
        })
    return {
        "machine_id": obtener_machine_id(),
        "fecha": datetime.now(timezone.utc).isoformat(),
        "total_productos": len(data),
        "productos": data,
    }


def exportar_a_json(db: Session) -> str:
    """Exporta productos a un archivo JSON local. Retorna la ruta."""
    data = exportar_productos(db)
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "catalogo_export.json",
    )
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def subir_catalogo_a_r2(db: Session) -> bool:
    """Exporta productos y los sube a R2. Retorna True si se subió."""
    cfg = _get_r2_config(db)
    if not cfg:
        return False
    try:
        data = exportar_productos(db)
        mid = data["machine_id"]
        key = f"catalogo/{mid}/productos.json"
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        client = _make_r2_client(cfg)
        client.put_object(Bucket=cfg["bucket"], Key=key, Body=body, ContentType="application/json")
        return True
    except Exception:
        return False


def listar_catalogos_r2(db: Session) -> List[dict]:
    """Lista archivos en la carpeta catalogo/ de R2."""
    cfg = _get_r2_config(db)
    if not cfg:
        return []
    try:
        client = _make_r2_client(cfg)
        resp = client.list_objects_v2(Bucket=cfg["bucket"], Prefix="catalogo/", MaxKeys=100)
        resultados = []
        for obj in resp.get("Contents", []):
            resultados.append({
                "key": obj["Key"],
                "size": obj["Size"],
                "fecha": obj["LastModified"].isoformat(),
            })
        resultados.sort(key=lambda x: x["fecha"], reverse=True)
        return resultados
    except Exception:
        return []


def descargar_de_r2(filename: str, db: Session) -> Optional[str]:
    """Descarga un archivo del catálogo desde R2 a la carpeta local. Retorna ruta local."""
    cfg = _get_r2_config(db)
    if not cfg:
        return None
    try:
        local_path = _catalogo_path()
        client = _make_r2_client(cfg)
        client.download_file(cfg["bucket"], filename, local_path)
        return local_path
    except Exception:
        return None


def descargar_catalogo_central(db: Session) -> Optional[str]:
    """Descarga catalogo/{machine_id}/productos.json de R2 a catalogo_completo.json y recarga en memoria."""
    cfg = _get_r2_config(db)
    if not cfg:
        return None
    try:
        mid = obtener_machine_id()
        key = f"catalogo/{mid}/productos.json"
        local_path = _catalogo_path()
        client = _make_r2_client(cfg)
        client.download_file(cfg["bucket"], key, local_path)
        total = cargar_catalogo_memoria(force=True)
        return local_path
    except Exception:
        return None


def importar_catalogo(data: List[dict]) -> int:
    """Importa un catálogo mergeado: guarda en catalogo_completo.json y carga en memoria.
    Retorna cuántos productos se importaron."""
    global _catalogo_memoria, _catalogo_cargado

    # Si data es un dict con clave 'productos', extraer la lista
    if isinstance(data, dict) and "productos" in data:
        data = data["productos"]

    path = _catalogo_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _catalogo_memoria = {p["codigo_barras"]: p for p in data}
    _catalogo_cargado = True
    return len(_catalogo_memoria)


def estado_catalogo(db: Session) -> dict:
    """Estado actual del sistema de catálogo."""
    r2_ok = _get_r2_config(db) is not None
    total_local = len(_catalogo_memoria) if _catalogo_cargado else 0
    if not _catalogo_cargado and os.path.exists(_catalogo_path()):
        total_local = cargar_catalogo_memoria()

    # Contar exportables
    exportables = (
        db.query(Producto)
        .filter(Producto.activo == True, Producto.codigo_barras.isnot(None))
        .count()
    )
    reales = 0
    for p in db.query(Producto).filter(Producto.activo == True, Producto.codigo_barras.isnot(None)).all():
        if _es_barcode_real(p.codigo_barras):
            reales += 1

    ultimo = None
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
        "catalogo_export.json",
    )
    if os.path.exists(path):
        ultimo = datetime.fromtimestamp(os.path.getmtime(path)).isoformat()

    return {
        "r2_habilitado": r2_ok,
        "exportables": reales,
        "total_productos": total_local or 0,  # local = 0 means not loaded
        "catalogo_cargado": _catalogo_cargado,
        "ultimo_export": ultimo,
        "machine_id": obtener_machine_id(),
    }
