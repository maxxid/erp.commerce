"""Schemas del panel de recategorización."""

from typing import Optional

from pydantic import BaseModel, Field


class SugerenciaIA(BaseModel):
    """Resultado de IA para un producto (siempre requiere confirmación humana)."""

    producto_id: int
    categoria_id: Optional[int] = None
    categoria_nombre: Optional[str] = None
    nueva_categoria: Optional[str] = None
    confianza: float = 0.0
    motivo: str = ""


class SugerenciaLocal(BaseModel):
    categoria_id: Optional[int] = None
    categoria_nombre: Optional[str] = None
    confianza: float = 0.0
    motivo: str = ""


class CandidatoOut(BaseModel):
    producto_id: int
    nombre: str
    marca: Optional[str] = None
    codigo_barras: Optional[str] = None
    descripcion: Optional[str] = None
    categoria_actual_id: Optional[int] = None
    categoria_actual: Optional[str] = None
    sugerencia: Optional[SugerenciaLocal] = None
    destino_id: Optional[int] = None


class CandidatosPage(BaseModel):
    """`api.js` desenvuelve el `data` de la respuesta, así que `total` tiene
    que viajar adentro del payload o la paginación del cliente se queda sin
    total."""

    items: list[CandidatoOut] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = 50


class SugerenciasIARequest(BaseModel):
    productos_ids: list[int] = Field(min_length=1)


class SugerenciasIAOut(BaseModel):
    lote: list[SugerenciaIA] = Field(default_factory=list)
    ignorados: int = 0
    tokens_out: int = 0


class CambioRequest(BaseModel):
    producto_id: int
    categoria_id: Optional[int] = None
    nueva_categoria: Optional[str] = None


class AplicarRequest(BaseModel):
    cambios: list[CambioRequest] = Field(min_length=1)


class AplicarResultado(BaseModel):
    aplicados: int
    categorias_creadas: list[dict] = Field(default_factory=list)
    errores: list[dict] = Field(default_factory=list)
