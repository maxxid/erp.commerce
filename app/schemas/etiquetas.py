"""Schemas para Etiquetas de Precios."""

from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import date, datetime


class EtiquetasFiltros(BaseModel):
    """Filtros para buscar productos a etiquetar."""
    desde: date
    hasta: date
    incluir_cambios_precio: bool = True
    incluir_nuevos: bool = True
    solo_con_stock: bool = False
    categoria_id: Optional[int] = None
    sector_id: Optional[int] = None
    orden: Literal['fecha_desc', 'fecha_asc', 'nombre', 'categoria', 'sector', 'precio_asc', 'precio_desc'] = 'fecha_desc'
    agrupar: bool = True   # Variantes de un mismo grupo salen en una sola etiqueta


class VarianteEtiquetaOut(BaseModel):
    """Producto que forma parte de una etiqueta de grupo."""
    id: int
    nombre: str
    codigo_barras: str
    precio_venta: float
    precio_etiqueta: Optional[float] = None
    stock_actual: float
    pendiente: bool = False
    distinto: bool = False   # Su precio no coincide con el de la etiqueta del grupo


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
    sector_id: Optional[int] = None
    sector_nombre: Optional[str] = None
    stock_actual: float
    motivo: Literal['nuevo', 'cambio_precio', 'ambos'] = 'cambio_precio'
    es_grupo: bool = False
    grupo: Optional[str] = None
    ids: List[int] = []   # Productos que cubre esta etiqueta (al marcar impreso se actualizan todos)
    variantes: List[VarianteEtiquetaOut] = []
    precios_distintos: bool = False
    sectores_distintos: bool = False

    model_config = {"from_attributes": True}


class GenerarPDFRequest(BaseModel):
    """Request para generar PDF de etiquetas."""
    filtros: EtiquetasFiltros
    tamano: Literal["70x35", "60x40"]
    borderless: bool = False
    descripciones_editadas: dict[int, str] = {}
    productos_ids: Optional[list[int]] = None   # ids de fila (el representante en los grupos); None = todo lo filtrado
    forzar: bool = False   # Generar igual con productos de stock cero (omite el 409)
    modelo: Literal["completa", "sencilla"] = "completa"  # sencilla: solo precio + descripción, sin código de barras


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