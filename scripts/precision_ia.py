"""Mide qué tan seguida está la IA sobre productos que ya están categorizados.

Clasifica a ciegas (el prompt se arma con `incluir_actual=False`, así que el
modelo no puede copiarse de la respuesta) una muestra al azar de productos con
categoría cargada y compara el veredicto contra lo que dice la base.

Las métricas que interesan:

  * precisión sobre lo que propone  = aciertos / propuestas
  * precisión sobre lo que la UI preselecciona sola = aciertos / propuestas con
    confianza >= 0.8 (umbral `UMBRAL_CONFIANZA` del panel)
  * cobertura = propuestas / analizados, es decir cuántas veces la IA se anima

Solo lectura: no escribe nada, no toca `ia_analizado`, no deja auditoría.

Uso en el server:

    cd /opt/erp-comercio && sudo -u erp bash -c 'source venv/bin/activate && \
        DATABASE_URL=sqlite:////data/erp/erp_comercio.db \
        python scripts/precision_ia.py --env-file /etc/erp-comercio/ia.env'

`--env-file` es obligatorio corriéndolo a mano: el script no hereda el entorno
que systemd arma para el servicio. `--db` también, porque el default es otra
DB. Con `--seed` la muestra se repite, que es lo que sirve para comparar dos
versiones del prompt.
"""

import argparse
import json
import logging
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# --db y --env-file se resuelven ANTES de importar app.database / app.config,
# que congelan DATABASE_URL e IA_DEFAULT_API_KEY en el import (igual que
# scripts/smoke_ia.py).
_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--db", default=None)
_pre.add_argument("--env-file", default=None)
_pre_args, _ = _pre.parse_known_args()
if _pre_args.db:
    os.environ["DATABASE_URL"] = _pre_args.db


def _leer_env_file(ruta: str) -> None:
    """Carga un EnvironmentFile de systemd (key=value, # comentarios)."""
    for linea in Path(ruta).read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip().strip("\"'"))


if _pre_args.env_file:
    _leer_env_file(_pre_args.env_file)

from app.database import SessionLocal  # noqa: E402
from app.models.producto import Producto  # noqa: E402
from app.services import categorizacion_service as servicio  # noqa: E402
from app.services.ia import registro  # noqa: E402
from app.services.ia.proveedor import ErrorProveedor, IADeshabilitada, LimiteAgotado  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("precision_ia")

# El mismo umbral que usa RecategorizarView.vue para preseleccionar filas.
UMBRAL_CONFIANZA = 0.8


def _id(it: dict) -> int | None:
    try:
        return int(it.get("categoria_id"))
    except (TypeError, ValueError):
        return None


def _confianza(it: dict) -> float:
    try:
        return round(min(1.0, max(0.0, float(it.get("confianza")))), 2)
    except (TypeError, ValueError):
        return 0.5


def _porcentaje(parte: int, todo: int) -> str:
    return f"{(100.0 * parte / todo):.1f}%" if todo else "n/a"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=None, help="DATABASE_URL (default: env DATABASE_URL)")
    parser.add_argument("--env-file", default=None,
                        help="EnvironmentFile de systemd, ej. /etc/erp-comercio/ia.env")
    parser.add_argument("--muestra", type=int, default=40,
                        help="Cuántos productos categorizados clasificar a ciegas")
    parser.add_argument("--seed", type=int, default=42,
                        help="Semilla del muestreo: igual seed = misma muestra")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        cfg = registro.configuracion(db)
        log.info("--- config ---")
        log.info("  key        : %s %s", cfg["api_key_origen"], cfg["api_key_enmascarada"])
        log.info("  proveedor  : %s / %s", cfg["provider"], cfg["modelo"])
        log.info("  limite/uso : %s / %s llamadas este mes",
                 cfg["limite_mes"], cfg["uso_mes"]["llamadas"])
        if not cfg["habilitada"]:
            log.error("IA no habilitada: probá con --env-file /etc/erp-comercio/ia.env")
            return 1

        con_categoria = [
            pid for (pid,) in (
                db.query(Producto.id)
                .filter(Producto.categoria_id.isnot(None), Producto.activo.is_(True))
                .order_by(Producto.id)
                .all()
            )
        ]
        if not con_categoria:
            log.error("No hay productos con categoría cargada.")
            return 1
        muestra = min(args.muestra, len(con_categoria))
        elegidos = sorted(random.Random(args.seed).sample(con_categoria, muestra))
        log.info("--- muestra: %d de %d productos con categoría (seed %d) ---",
                 muestra, len(con_categoria), args.seed)

        # El truco del muestreo: prompt sin la categoría actual, para que el
        # modelo no pueda adivinar leyendo lo que dice la base.
        original_prompt = servicio.prompt_ia
        servicio.prompt_ia = lambda filas, cat: original_prompt(
            filas, cat, incluir_actual=False
        )

        lote_tam = servicio.TAMANO_LOTE_IA
        lotes = [elegidos[i:i + lote_tam] for i in range(0, len(elegidos), lote_tam)]
        aciertos: list[dict] = []
        discrepancias: list[dict] = []
        sin_propuesta: list[dict] = []
        tokens = 0
        ilegibles = 0

        for ids_lote in lotes:
            filas, _ = servicio.detalle(db, ids_lote)
            cat = servicio.catalogo(db)
            try:
                respuesta = registro.completar(
                    db,
                    sistema=servicio.SISTEMA_IA,
                    usuario=servicio.prompt_ia(filas, cat),
                    como_json=True,
                    max_tokens=2048,
                    temperatura=0.0,
                )
            except IADeshabilitada as err:
                log.error("IA deshabilitada: %s", err)
                return 1
            except LimiteAgotado as err:
                log.error("Límite de llamadas agotado: %s", err)
                break
            except ErrorProveedor as err:
                log.error("El proveedor falló a mitad de la muestra: %s", err)
                break
            tokens += respuesta.tokens_out or 0

            try:
                crudo = json.loads(respuesta.texto)
                bruto = {
                    int(it["producto_id"]): it
                    for it in crudo.get("sugerencias", [])
                    if isinstance(it, dict) and str(it.get("producto_id", "")).isdigit()
                }
            except (ValueError, AttributeError, TypeError):
                ilegibles += len(filas)
                continue

            for fila in filas:
                pid = fila["producto_id"]
                actual = fila["categoria_actual"]
                it = bruto.get(pid)
                if it is None or (_id(it) is None and not it.get("nueva_categoria")):
                    # O no llegó, o el modelo prefirió no adivinar.
                    sin_propuesta.append({"producto_id": pid, "actual": actual})
                    continue
                propuesta = _id(it)
                fila_res = {
                    "producto_id": pid,
                    "actual": actual,
                    "propuesta": it.get("nueva_categoria") or propuesta,
                    "confianza": _confianza(it),
                    "motivo": str(it.get("motivo") or "").strip()[:80],
                }
                if propuesta is not None and propuesta == fila["categoria_actual_id"]:
                    aciertos.append(fila_res)
                else:
                    discrepancias.append(fila_res)

        analizados = len(aciertos) + len(discrepancias) + len(sin_propuesta)
        propuestas = len(aciertos) + len(discrepancias)
        altas_ok = [a for a in aciertos if a["confianza"] >= UMBRAL_CONFIANZA]
        altas_mal = [d for d in discrepancias if d["confianza"] >= UMBRAL_CONFIANZA]

        log.info("--- resultado ---")
        log.info("  analizados        : %d", analizados)
        log.info("  sin propuesta     : %d  (la IA prefirió no adivinar)",
                 len(sin_propuesta))
        log.info("  propuestas        : %d  (cobertura %s)",
                 propuestas, _porcentaje(propuestas, analizados))
        log.info("  aciertos          : %d/%d = %s",
                 len(aciertos), propuestas, _porcentaje(len(aciertos), propuestas))
        log.info("  confianza >= %.1f : %d propuestas, aciertos %d = %s  (lo que preselecciona la UI)",
                 UMBRAL_CONFIANZA, len(altas_ok) + len(altas_mal), len(altas_ok),
                 _porcentaje(len(altas_ok), len(altas_ok) + len(altas_mal)))
        log.info("  confianza <  %.1f : %d propuestas, aciertos %d = %s",
                 UMBRAL_CONFIANZA, propuestas - len(altas_ok) - len(altas_mal),
                 len(aciertos) - len(altas_ok),
                 _porcentaje(len(aciertos) - len(altas_ok),
                             propuestas - len(altas_ok) - len(altas_mal)))
        log.info("  tokens_out        : %d · respuestas ilegibles: %d", tokens, ilegibles)

        if discrepancias:
            log.info("--- discrepancias (%d) ---", len(discrepancias))
            for d in sorted(discrepancias, key=lambda x: -x["confianza"]):
                log.info("  [%s] %s -> %s · conf %.2f · %s",
                         d["producto_id"], d["actual"], d["propuesta"],
                         d["confianza"], d["motivo"])

        log.info("PRECISION OK (solo lectura, nada aplicado)")
        return 0
    except Exception as err:  # noqa: BLE001
        log.error("PRECISION FALLÓ: %s", err)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
