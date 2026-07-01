"""Schemas compartidos: paginación, respuestas estándar."""

from pydantic import BaseModel
from typing import Generic, TypeVar, Optional

T = TypeVar("T")


class RespuestaBase(BaseModel):
    """Formato estándar de respuesta exitosa."""
    ok: bool = True
    message: str = "Operación exitosa"


class RespuestaData(RespuestaBase, Generic[T]):
    """Respuesta con datos."""
    data: Optional[T] = None


class RespuestaLista(RespuestaBase, Generic[T]):
    """Respuesta para listados con paginación."""
    data: list[T]
    total: int
    page: int = 1
    page_size: int = 50


class RespuestaError(BaseModel):
    """Formato estándar de error."""
    ok: bool = False
    error: str
    detail: Optional[str] = None


class Paginacion(BaseModel):
    """Parámetros de paginación."""
    page: int = 1
    page_size: int = 50
