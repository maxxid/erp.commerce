"""Resuelve y orquesta el proveedor de IA a partir de la configuración.

Punto de entrada único de la capa de IA: `completar()` aplica el
habilitado/deshabilitado, los límites mensuales y el registro de uso, así
ninguna feature se saltea nada.
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.config import settings
from app.services import config_service
from app.services.ia import limites
from app.services.ia.openai_compat import ProveedorOpenAICompat
from app.services.ia.proveedor import (
    IADeshabilitada,
    IARespuesta,
    ProveedorIA,
)

logger = logging.getLogger(__name__)

CLAVE_HABILITADA = "ia_habilitada"
CLAVE_PROVIDER = "ia_provider"
CLAVE_API_KEY = "ia_api_key"
CLAVE_BASE_URL = "ia_base_url"
CLAVE_MODELO = "ia_model"
CLAVE_LIMITE_MES = "ia_limite_mes"

LIMITE_MES_DEFECTO = 1000

# Defaults por proveedor. La capa es compatible con la API de OpenAI, así que
# cualquiera de estos se agrega acá (o se usa "custom") sin tocar código.
PROVEEDORES = {
    "groq": {
        "nombre": "Groq",
        "base_url": "https://api.groq.com/openai/v1",
        "modelo": "llama-3.3-70b-versatile",
    },
    "openai": {
        "nombre": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "modelo": "gpt-4o-mini",
    },
    "deepseek": {
        "nombre": "DeepSeek",
        "base_url": "https://api.deepseek.com/v1",
        "modelo": "deepseek-chat",
    },
    "custom": {"nombre": "Otro (compatible OpenAI)", "base_url": "", "modelo": ""},
}


def configuracion(db: Session) -> dict:
    """Snapshot de la config de IA para la UI y para el gating.

    La key nunca se devuelve cruda: es write-only. Solo se informa si existe,
    de dónde viene y una máscara.
    """
    proveedor = (config_service.get_config(db, CLAVE_PROVIDER) or "groq").lower()
    if proveedor not in PROVEEDORES:
        proveedor = "custom"
    defaults = PROVEEDORES[proveedor]

    base_url = (
        config_service.get_config(db, CLAVE_BASE_URL)
        or settings.IA_DEFAULT_BASE_URL
        or defaults["base_url"]
    )
    modelo = (
        config_service.get_config(db, CLAVE_MODELO)
        or settings.IA_DEFAULT_MODELO
        or defaults["modelo"]
    )

    key_db = config_service.get_config(db, CLAVE_API_KEY) or ""
    key_env = settings.IA_DEFAULT_API_KEY or ""
    # BYOK tiene prioridad: si el cliente puso la suya, manda sobre la interna.
    api_key = key_db or key_env
    origen = "cliente" if key_db else ("interna" if key_env else "ninguna")

    habilitada_raw = config_service.get_config(db, CLAVE_HABILITADA)
    habilitada = habilitada_raw is None or str(habilitada_raw).lower() in ("1", "true")
    if not api_key:
        habilitada = False

    return {
        "habilitada": habilitada,
        "configure_key": not bool(api_key),
        "provider": proveedor,
        "proveedores": [
            {"id": k, "nombre": v["nombre"], "base_url": v["base_url"], "modelo": v["modelo"]}
            for k, v in PROVEEDORES.items()
        ],
        "base_url": base_url,
        "modelo": modelo,
        "api_key_origen": origen,
        "api_key_enmascarada": enmascarar(api_key),
        "limite_mes": limite_mes(db),
        "uso_mes": limites.leer(db),
    }


def enmascarar(key: str) -> str:
    """gsk_abc...xyz1234 -> gsk_••••xyz1234, o vacío si no hay key."""
    if not key:
        return ""
    if len(key) <= 8:
        return "••••••••"
    return f"{key[:4]}••••{key[-4:]}"


def limite_mes(db: Session) -> Optional[int]:
    """Límite mensual efectivo de llamadas.

    Precedencia: licencia (override por cliente) > configuración (operador) >
    default. Se importa `planes_service` adentro de la función para no armar un
    ciclo de imports (él importa este módulo para leer la clave de config).
    """
    from app.services import planes_service

    return planes_service.limite_ia_de(db)


def obtener(db: Session) -> Optional[ProveedorIA]:
    """Devuelve el proveedor listo para usar, o None si está deshabilitado."""
    cfg = configuracion(db)
    if not cfg["habilitada"]:
        return None
    return ProveedorOpenAICompat(
        base_url=cfg["base_url"],
        api_key=_key_real(db),
        modelo=cfg["modelo"],
    )


def _key_real(db: Session) -> str:
    """Key real para la llamada (nunca expuesta en respuestas de API)."""
    key_db = config_service.get_config(db, CLAVE_API_KEY)
    if key_db:
        return key_db
    return settings.IA_DEFAULT_API_KEY


def completar(
    db: Session,
    *,
    sistema: str,
    usuario: str,
    como_json: bool = False,
    max_tokens: int = 1024,
    temperatura: float = 0.0,
) -> IARespuesta:
    """Llamada de alto nivel: gating + límites + registro de uso.

    Es lo único que deben usar las features. Levanta IADeshabilitada o
    LimiteAgotado, que los routers traducen a 402/409.
    """
    cfg = configuracion(db)
    if not cfg["habilitada"]:
        raise IADeshabilitada(
            "La IA está deshabilitada o falta configurar la API key"
        )
    limites.verificar(db, cfg["limite_mes"])
    proveedor = ProveedorOpenAICompat(
        base_url=cfg["base_url"],
        api_key=_key_real(db),
        modelo=cfg["modelo"],
    )
    respuesta = proveedor.completar(
        sistema=sistema,
        usuario=usuario,
        como_json=como_json,
        max_tokens=max_tokens,
        temperatura=temperatura,
    )
    limites.registrar(
        db,
        llamadas=1,
        tokens_in=respuesta.tokens_in,
        tokens_out=respuesta.tokens_out,
    )
    return respuesta


def probar(db: Session) -> dict:
    """Verificación de conexión para el botón de Ajustes."""
    cfg = configuracion(db)
    if not cfg["habilitada"]:
        return {"ok": False, "detalle": "IA deshabilitada o sin API key"}
    try:
        respuesta = completar(
            db,
            sistema="Respondé solo con la palabra OK.",
            usuario="ping",
            max_tokens=8,
        )
    except Exception as err:  # noqa: BLE001 - la UI necesita el motivo exacto
        logger.warning("IA: test de conexión falló: %s", err)
        return {"ok": False, "detalle": str(err)}
    return {
        "ok": True,
        "detalle": f"Conectado con {cfg['modelo']}",
        "modelo": respuesta.modelo,
        "latencia_intentos": respuesta.reintentos,
    }
