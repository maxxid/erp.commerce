"""Schemas para Etiquetas de Precios."""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import date, datetime


class EtiquetasFiltros(BaseModel):
    """Filtros para buscar productos a etiquetar."""
    desde: date
    hasta: date
    incluir_cambios_precio: bool = True
    incluir_nuevos: bool = True
    solo_con_stock: bool = False


class EtiquetaProductoOut(BaseModel):
    """Producto para etiquetar."""
    id: int
    codigo_barras: str
    nombre: str
    marca: Optional[str] = None
    descripcion: Optional[str] = None
    precio_venta: float
    precio_etiqueta: Optional[float] = None
    tipo_venta: str
    precio_por_kilo: Optional[float] = None
    categoria_id: Optional[int] = None
    categoria_nombre: Optional[str] = None
    stock_actual: float

    model_config = {"from_attributes": True}


class GenerarPDFRequest(BaseModel):
    """Request para generar PDF de etiquetas."""
    filtros: EtiquetasFiltros
    tamano: Literal["70x35", "60x40"]
    borderless: bool = False
    descripciones_editadas: dict[int, str] = {}


class HistorialImpresionOut(BaseModel):
    """Entrada del historial de impresiones."""
    desde: date
    hasta: date
    fecha_impresion: datetime
    total_etiquetas: int
    tamano: str
    borderless: bool


class MarcarImpresoRequest(BaseModel):
    """Request para marcar productos como impresos."""
    productos_ids: list[int]
    tamano: Literal["70x35", "60x40"]
    borderless: bool = False