"""Contador de uso mensual de la IA.

Se guarda en `configuraciones` como JSON (mismo patrón que
`historial_etiquetas`) en vez de sumar una tabla: es una fila por mes y no
aporta nada indexarla.
"""

import json
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.services import config_service
from app.services.ia.proveedor import LimiteAgotado

PREFIJO = "ia_uso_"
_VACIO = {"llamadas": 0, "tokens_in": 0, "tokens_out": 0}


def clave_mes(mes: Optional[datetime] = None) -> str:
    momento = mes or datetime.now()
    return f"{PREFIJO}{momento.year:04d}_{momento.month:02d}"


def leer(db: Session, mes: Optional[datetime] = None) -> dict:
    crudo = config_service.get_config(db, clave_mes(mes))
    if not crudo:
        return dict(_VACIO)
    try:
        data = json.loads(crudo)
    except ValueError:
        return dict(_VACIO)
    if not isinstance(data, dict):
        return dict(_VACIO)
    return {
        "llamadas": _entero(data.get("llamadas")),
        "tokens_in": _entero(data.get("tokens_in")),
        "tokens_out": _entero(data.get("tokens_out")),
    }


def registrar(
    db: Session,
    *,
    llamadas: int = 1,
    tokens_in: int = 0,
    tokens_out: int = 0,
    mes: Optional[datetime] = None,
) -> dict:
    uso = leer(db, mes)
    uso["llamadas"] += llamadas
    uso["tokens_in"] += _entero(tokens_in)
    uso["tokens_out"] += _entero(tokens_out)
    config_service.set_config(
        db, clave_mes(mes), json.dumps(uso), "Uso mensual de IA"
    )
    return uso


def verificar(
    db: Session, limite: Optional[int], *, mes: Optional[datetime] = None
) -> dict:
    """Lanza LimiteAgotado si el mes ya agotó `limite` llamadas.

    `limite` None = sin límite. Se chequea ANTES de llamar, asi el contador
    que queda grabado nunca supera lo que el plan permite.
    """
    uso = leer(db, mes)
    if limite is None or limite <= 0:
        return uso
    if uso["llamadas"] >= limite:
        raise LimiteAgotado(
            f"Límite mensual de IA alcanzado ({uso['llamadas']}/{limite} llamadas)"
        )
    return uso


def _entero(valor) -> int:
    try:
        return max(0, int(valor or 0))
    except (TypeError, ValueError):
        return 0
