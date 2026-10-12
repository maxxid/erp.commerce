"""Abstracción de proveedor de IA/LLM.

Toda llamada a modelos pasa por un ProveedorIA. El objetivo es no atarse a un
proveedor: OpenAI, Groq, DeepSeek, Together u Ollama local se conectan con la
misma clase compatible con la API de OpenAI, cambiando solo la config.

Las features (recategorización, descripciones, etc.) usan `ia.completar()`,
nunca instancian un proveedor a mano: así el gating por plan y los límites de
uso viven en un solo lugar.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


class ErrorIA(Exception):
    """Error base de la capa de IA."""


class IADeshabilitada(ErrorIA):
    """No hay proveedor configurado, o el plan no incluye IA."""


class LimiteAgotado(ErrorIA):
    """Se superó el límite mensual de llamadas."""


class ErrorProveedor(ErrorIA):
    """El proveedor respondió mal, no respondió, o quedó sin reintentos."""


@dataclass(frozen=True)
class IARespuesta:
    texto: str
    tokens_in: int = 0
    tokens_out: int = 0
    modelo: str = ""
    reintentos: int = 0


class ProveedorIA(ABC):
    """Interfaz mínima que implementa cada proveedor."""

    @abstractmethod
    def completar(
        self,
        *,
        sistema: str,
        usuario: str,
        como_json: bool = False,
        max_tokens: int = 1024,
        temperatura: float = 0.0,
    ) -> IARespuesta:
        """Devuelve la respuesta del modelo. Lanza ErrorProveedor si falla."""
        raise NotImplementedError
