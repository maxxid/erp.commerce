"""Normaliza nombre, marca y descripcion de productos a Title Case español.

Uso (en el server):
    cd /opt/erp-comercio && sudo -u erp bash -c 'source venv/bin/activate && python scripts/normalizar_productos_titlecase.py'

Se ejecuta una sola vez. Es idempotente: si los datos ya están normalizados, no cambia nada.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.services.texto_service import title_case_es

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("normalizar")


def normalizar_query(db, model, campos):
    """Normaliza campos de texto en un modelo. Retorna cantidad de cambios."""
    cambios = 0
    for obj in db.query(model).all():
        modificado = False
        for campo in campos:
            valor = getattr(obj, campo, None)
            if isinstance(valor, str) and valor.strip():
                nuevo = title_case_es(valor)
                if nuevo != valor:
                    setattr(obj, campo, nuevo)
                    modificado = True
        if modificado:
            cambios += 1
    return cambios


def main():
    db = SessionLocal()
    try:
        prod_cambios = normalizar_query(db, Producto, ["nombre", "marca", "descripcion"])
        cat_cambios = normalizar_query(db, Categoria, ["nombre"])

        db.commit()

        log.info("Productos normalizados: %d", prod_cambios)
        log.info("Categorías normalizadas: %d", cat_cambios)
        log.info("Listo.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
