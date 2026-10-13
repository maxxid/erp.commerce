"""Backfill: marca los productos existentes como ya analizados por la IA.

Dry-run por defecto: sólo cuenta. Con `--aplicar` escribe `ia_analizado = 1`
en todo lo que todavía esté en NULL o en 0.

Es el paso único que hace que el modo "nuevos" del panel sea incremental: lo
que ya existe queda registrado como visto, y a partir de ahí sólo aparecen en
ese modo los productos que se carguen después.

Uso en el server:

    cd /opt/erp-comercio && sudo -u erp bash -c 'source venv/bin/activate && \
        DATABASE_URL=sqlite:////data/erp/erp_comercio.db \
        python scripts/marcar_analizados.py --aplicar'

`--db` hace falta corriéndolo a mano: el default es otra base.
"""

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --db se resuelve ANTES de importar app.database, que arma el engine con
# settings.DATABASE_URL en el import.
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--db", default=None)
_pre_args, _ = _pre.parse_known_args()
if _pre_args.db:
    os.environ["DATABASE_URL"] = _pre_args.db

from app.database import SessionLocal  # noqa: E402
from app.models.producto import Producto  # noqa: E402
from app.services import categorizacion_service as servicio  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("marcar_analizados")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None, help="DATABASE_URL (default: env DATABASE_URL)")
    parser.add_argument("--aplicar", action="store_true",
                        help="Escribe; sin este flag sólo se cuentan")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        pendientes = [
            pid
            for (pid,) in (
                db.query(Producto.id)
                .filter(Producto.ia_analizado.isnot(True))
                .order_by(Producto.id)
                .all()
            )
        ]
        total = db.query(Producto.id).count()
        log.info("Productos totales: %s · sin analizar por la IA: %s", total, len(pendientes))
        if not pendientes:
            log.info("Nada por hacer: todo ya estaba marcado.")
            return 0
        if not args.aplicar:
            log.info("DRY-RUN (nada escrito). Pasá --aplicar para marcarlos.")
            return 0

        marcados = servicio.marcar_analizados(db, pendientes)
        log.info("Marcados como analizados: %s", marcados)
        log.info("MARCADOS OK")
        return 0
    except Exception as err:  # noqa: BLE001
        log.error("MARCAR FALLÓ: %s", err)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
