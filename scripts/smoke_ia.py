"""Smoke test de la capa de IA contra el proveedor real.

Solo lectura: verifica la config, hace un ping y pide sugerencias para un lote.
**NUNCA llama a `aplicar()`** — nada se mueve sin que lo confirme una persona
en el panel.

Uso en el server:

    cd /opt/erp-comercio && sudo -u erp bash -c 'source venv/bin/activate && \
        DATABASE_URL=sqlite:////data/erp/erp_comercio.db \
        python scripts/smoke_ia.py'

Flags: --solo-ping, --lote N, --modo pendientes|sin_categoria|general|todos, --db URL
"""

import argparse
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Igual que normalizar_productos_titlecase: --db hay que resolverlo ANTES de
# importar app.database, que arma el engine con settings.DATABASE_URL en el import.
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--db", default=None)
_pre_args, _ = _pre.parse_known_args()
if _pre_args.db:
    os.environ["DATABASE_URL"] = _pre_args.db

from app.database import SessionLocal
from app.models.usuario import Usuario
from app.routers.recategorizar import sugerir_con_ia
from app.schemas.recategorizar import SugerenciasIARequest
from app.services import categorizacion_service as servicio
from app.services.ia import registro

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("smoke_ia")

MODOS = ("pendientes", "sin_categoria", "general", "todos")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None, help="DATABASE_URL (default: env DATABASE_URL)")
    parser.add_argument("--lote", type=int, default=10, help="Cuántos productos analizar")
    parser.add_argument("--modo", default="pendientes", choices=MODOS)
    parser.add_argument("--solo-ping", action="store_true", help="Solo verificar la conexión")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        cfg = registro.configuracion(db)
        log.info("--- config ---")
        log.info("  habilitada : %s", cfg["habilitada"])
        log.info("  key        : %s %s", cfg["api_key_origen"], cfg["api_key_enmascarada"])
        log.info("  proveedor  : %s / %s", cfg["provider"], cfg["modelo"])
        log.info("  base_url   : %s", cfg["base_url"])
        log.info("  limite/uso : %s / %s llamadas este mes",
                 cfg["limite_mes"], cfg["uso_mes"]["llamadas"])

        if not cfg["habilitada"]:
            log.error("IA no habilitada: falta la API key "
                      "(IA_DEFAULT_API_KEY en el unit, o BYOK en Ajustes > IA).")
            return 1

        log.info("--- ping ---")
        ping = registro.probar(db)
        log.info("  %s", ping)
        if not ping.get("ok"):
            return 1
        if args.solo_ping:
            log.info("SMOKE OK (solo ping)")
            return 0

        filas, total = servicio.candidatos(
            db, modo=args.modo, q="", page=1, page_size=args.lote
        )
        ids = [f["producto_id"] for f in filas]
        if not ids:
            log.info("Sin candidatos en el modo %r; pruebo con 'todos'.", args.modo)
            filas, total = servicio.candidatos(
                db, modo="todos", q="", page=1, page_size=args.lote
            )
            ids = [f["producto_id"] for f in filas]
        if not ids:
            log.error("No hay productos para analizar.")
            return 1

        user = (
            db.query(Usuario)
            .filter(Usuario.rol.in_(["admin", "encargado"]))
            .order_by(Usuario.id)
            .first()
        )
        if not user:
            log.error("No hay usuarios admin/encargado para correr el endpoint.")
            return 1

        log.info("--- lote: %d de %d candidatos (modo %s) ---", len(ids), total, args.modo)
        resp = sugerir_con_ia(
            SugerenciasIARequest(productos_ids=ids), db=db, _user=user, _plan=user
        )
        for s in resp.data.lote:
            destino = s.categoria_nombre or f"nueva: {s.nueva_categoria}"
            log.info("  [%s] -> %s · %s", s.producto_id, destino, s.motivo)
        log.info("  ignorados: %s · tokens_out: %s",
                 resp.data.ignorados, resp.data.tokens_out)
        log.info("SMOKE OK")
        return 0
    except Exception as err:
        log.error("SMOKE FALLÓ: %s", err)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
