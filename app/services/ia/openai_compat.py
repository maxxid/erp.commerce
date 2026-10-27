"""Cliente sobre la API de chat/completions compatible con OpenAI.

La mayoría de los proveedores (OpenAI, Groq, DeepSeek, Together, Ollama)
expone el mismo endpoint con el mismo shape de request/response, asi que una
clase cubre todos cambiando `base_url`, `api_key` y `model`.

Reintentos: el resto del repo no tiene ninguno y los errores de red se tragan
devolviendo None. Acá hace falta reintentar porque un 429 de rate limit no es
un error del usuario y una llamada de IA barata no deberia romper el flujo.
"""

import json as _json
import logging
import re
import time

import requests

from app.config import settings
from app.services.ia.proveedor import ErrorProveedor, IARespuesta, ProveedorIA

logger = logging.getLogger(__name__)

# 408/409/425 son retryables por timeout/conflicto transitorio; 429 por rate
# limit; 5xx porque el servidor fallo del lado de ellos.
_STATUS_REINTENTABLE = {408, 409, 425, 429, 500, 502, 503, 504}

# Corta la espera en tests y evita colgar un request de minutos.
_ESPERA_MAX = 30.0


def dormir(segundos: float) -> None:
    """Punto único de espera para poder mockearlo en tests."""
    time.sleep(segundos)


def espera_reintento(status: int, headers, intento: int) -> float:
    """Respeta Retry-After si viene, si no backoff exponencial acotado."""
    retry_after = None
    if headers is not None:
        retry_after = headers.get("Retry-After")
    if retry_after:
        try:
            return min(float(retry_after), _ESPERA_MAX)
        except (TypeError, ValueError):
            pass
    if status == 429:
        return min(1.0 * (2 ** intento), _ESPERA_MAX)
    return min(0.5 * (2 ** intento), _ESPERA_MAX)


class ProveedorOpenAICompat(ProveedorIA):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        modelo: str,
        timeout: int | None = None,
        max_reintentos: int | None = None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key or ""
        self.modelo = modelo or ""
        self.timeout = settings.IA_TIMEOUT if timeout is None else timeout
        self.max_reintentos = (
            settings.IA_MAX_REINTENTOS if max_reintentos is None else max_reintentos
        )

    def completar(
        self,
        *,
        sistema: str,
        usuario: str,
        como_json: bool = False,
        max_tokens: int = 1024,
        temperatura: float = 0.0,
    ) -> IARespuesta:
        if not self.base_url or not self.api_key:
            raise ErrorProveedor("proveedor sin base_url o api_key")
        if not self.modelo:
            raise ErrorProveedor("proveedor sin modelo")

        mensajes = []
        if sistema:
            mensajes.append({"role": "system", "content": sistema})
        mensajes.append({"role": "user", "content": usuario})

        payload = {
            "model": self.modelo,
            "messages": mensajes,
            "max_tokens": max_tokens,
            "temperature": temperatura,
        }
        if como_json:
            payload["response_format"] = {"type": "json_object"}

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/chat/completions"

        ultimo_error = "sin intentos"
        for intento in range(self.max_reintentos + 1):
            respuesta = self._post(url, payload, headers, intento)
            if respuesta is None:
                continue

            status = respuesta.status_code
            if status in _STATUS_REINTENTABLE:
                ultimo_error = f"HTTP {status}"
                if intento < self.max_reintentos:
                    dormir(espera_reintento(status, getattr(respuesta, "headers", None), intento))
                    continue
                raise ErrorProveedor(f"{ultimo_error} tras {intento + 1} intentos")

            if status >= 400:
                raise ErrorProveedor(f"HTTP {status}: {_detalle(respuesta)}")

            try:
                data = respuesta.json()
            except ValueError as err:
                raise ErrorProveedor("el proveedor no devolvio JSON") from err
            return _parsear(data, self.modelo, intento)

        raise ErrorProveedor(ultimo_error)

    def _post(self, url, payload, headers, intento):
        """Un intento de red. Devuelve la respuesta o None para reintentar."""
        try:
            return requests.post(
                url, json=payload, headers=headers, timeout=self.timeout
            )
        except requests.RequestException as err:
            if intento < self.max_reintentos:
                logger.warning("IA: fallo de red (intento %s): %s", intento + 1, err)
                dormir(espera_reintento(0, None, intento))
                return None
            raise ErrorProveedor(
                f"sin conexion tras {intento + 1} intentos: {type(err).__name__}"
            ) from err


def _parsear(data, modelo: str, reintentos: int) -> IARespuesta:
    try:
        mensaje = data["choices"][0]["message"]
        # Algunos modelos de razonamiento (gpt-oss, o1, ...) devuelven el
        # razonamiento en un campo aparte y dejan `content` vacío si se
        # quedaron sin tokens. Caemos a esos campos como fallback.
        texto = (
            mensaje.get("content")
            or mensaje.get("reasoning_content")
            or mensaje.get("reasoning")
            or ""
        )
    except (KeyError, IndexError, TypeError) as err:
        raise ErrorProveedor("estructura de respuesta inesperada") from err
    uso = data.get("usage") or {}
    return IARespuesta(
        texto=texto,
        tokens_in=_entero(uso.get("prompt_tokens")),
        tokens_out=_entero(uso.get("completion_tokens")),
        modelo=data.get("model") or modelo,
        reintentos=reintentos,
    )


def _entero(valor) -> int:
    try:
        return int(valor or 0)
    except (TypeError, ValueError):
        return 0


def _detalle(respuesta) -> str:
    try:
        cuerpo = respuesta.text or ""
    except Exception:  # noqa: BLE001 - un proveedor raro no deberia tumbar todo
        return "sin detalle"
    cuerpo = cuerpo.strip()
    return cuerpo[:300] if cuerpo else "sin detalle"


def extraer_json(texto: str):
    """Toma el primer JSON balanceado de la respuesta, tolerando code fences.

    Pedir JSON no garantiza que el modelo no agregue prose alrededor, y
    `response_format` no esta soportado igual en todos los proveedores.
    """
    if not texto or not texto.strip():
        raise ValueError("respuesta vacia")
    limpio = texto.strip()
    limpio = re.sub(r"^```[a-zA-Z]*\s*", "", limpio)
    limpio = re.sub(r"\s*```$", "", limpio).strip()
    try:
        return _json.loads(limpio)
    except ValueError:
        pass
    substring = _primer_json(limpio)
    if substring is None:
        raise ValueError("sin JSON en la respuesta")
    return _json.loads(substring)


def _primer_json(texto: str) -> str | None:
    """Escaneo balanceado que respeta strings, escapes y anidamiento."""
    abre = {"{": "}", "[": "]"}
    cierra = {"}": "{", "]": "["}
    pila = []
    inicio = None
    dentro_de_string = False
    escapado = False
    for i, ch in enumerate(texto):
        if inicio is None:
            if ch in abre:
                inicio = i
                pila.append(ch)
            continue
        if dentro_de_string:
            if escapado:
                escapado = False
            elif ch == "\\":
                escapado = True
            elif ch == '"':
                dentro_de_string = False
            continue
        if ch == '"':
            dentro_de_string = True
        elif ch in abre:
            pila.append(ch)
        elif ch in cierra:
            if not pila or pila[-1] != cierra[ch]:
                return None
            pila.pop()
            if not pila:
                return texto[inicio : i + 1]
    return None
