"""Normaliza nombre, marca y descripcion de productos a Title Case español.

Se ejecuta una sola vez. Es idempotente: si los datos ya están normalizados, no cambia nada.

Por defecto SOLO MUESTRA qué cambiaría (dry-run). Para escribir hay que pasar --aplicar.

Uso en el server:

    cd /opt/erp-comercio && sudo -u erp bash -c 'source venv/bin/activate && \
        DATABASE_URL=sqlite:////data/erp/erp_comercio.db \
        python scripts/normalizar_productos_titlecase.py --dry-run'

  y después la misma línea con --aplicar.

Ojo con DATABASE_URL: sin la variable toma el default `sqlite:///erp_comercio.db`
(relativo al cwd), que NO es la DB de producción. El script imprime la DB que va a
usar y se niega a escribir si nadie la eligió explícitamente.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# `--db` hay que resolverlo ANTES de importar app.database: ese módulo arma el
# engine con settings.DATABASE_URL en el momento del import, así que un
# settings.DATABASE_URL = ... posterior no cambia nada.
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--db", default=None)
_db_args, _ = _pre.parse_known_args()
if _db_args.db:
    os.environ["DATABASE_URL"] = _db_args.db

from app.config import settings
from app.database import SessionLocal
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.services.texto_service import title_case_es

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("normalizar")

DEFAULT_URL = "sqlite:///erp_comercio.db"
CAMPOS_PRODUCTO = ("nombre", "marca", "descripcion")
MAX_EJEMPLOS = 50


def db_url():
    return settings.DATABASE_URL


def db_path():
    """Archivo real si es sqlite, si no None."""
    url = db_url()
    return url.split("///", 1)[1] if url.startswith("sqlite:///") else None


def recolectar(db, model, campos):
    """Devuelve [(id, campo, antes, despues)] sin tocar nada."""
    cambios = []
    for obj in db.query(model).all():
        for campo in campos:
            valor = getattr(obj, campo, None)
            if isinstance(valor, str) and valor.strip():
                nuevo = title_case_es(valor)
                if nuevo != valor:
                    cambios.append((obj.id, campo, valor, nuevo))
    return cambios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--aplicar",
        action="store_true",
        help="Escribe los cambios. Sin esta flag solo se imprime el dry-run.",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="DATABASE_URL a usar (default: variable de entorno DATABASE_URL).",
    )
    args = parser.parse_args()

    url = db_url()
    path = db_path()
    log.info("DB: %s", url)
    if path:
        if not Path(path).exists():
            log.error("El archivo de DB no existe: %s", path)
            return 1
        log.info("Archivo: %s (%d bytes)", path, Path(path).stat().st_size)

    if not args.aplicar:
        log.info("MODO DRY-RUN: no se escribe nada. Pasá --aplicar para aplicar.")
    elif url == DEFAULT_URL:
        log.error(
            "DATABASE_URL es el default (%s), que no es la DB de producción. "
            "Pasá DATABASE_URL=sqlite:////data/erp/erp_comercio.db o --db.",
            DEFAULT_URL,
        )
        return 1

    db = SessionLocal()
    try:
        prod = recolectar(db, Producto, CAMPOS_PRODUCTO)
        cat = recolectar(db, Categoria, ("nombre",))

        ids_prod = len({c[0] for c in prod})
        ids_cat = len({c[0] for c in cat})
        log.info("")
        log.info("Productos con cambios: %d de %d", ids_prod, db.query(Producto).count())
        log.info("Categorías con cambios: %d de %d", ids_cat, db.query(Categoria).count())
        log.info("Campos a tocar: %d (productos) + %d (categorías)", len(prod), len(cat))

        for titulo, items in (("PRODUCTO", prod), ("CATEGORÍA", cat)):
            if not items:
                continue
            log.info("")
            log.info("--- %s: primeros %d ---", titulo, min(len(items), MAX_EJEMPLOS))
            for _id, campo, antes, despues in items[:MAX_EJEMPLOS]:
                log.info("  [%s] %-20s -> %s", campo, antes, despues)
            if len(items) > MAX_EJEMPLOS:
                log.info("  ... y %d más", len(items) - MAX_EJEMPLOS)

        if not args.aplicar:
            log.info("")
            log.info("Dry-run listo: %d cambios pendientes de aplicar.", len(prod) + len(cat))
            return 0

        pendientes = ((Producto, prod), (Categoria, cat))
        for modelo, items in pendientes:
            for _id, campo, _antes, nuevo in items:
                obj = db.get(modelo, _id)
                if obj is not None:
                    setattr(obj, campo, nuevo)

        db.commit()
        log.info("")
        log.info("Aplicado: %d productos y %d categorías.", ids_prod, ids_cat)
        log.info("Listo.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
