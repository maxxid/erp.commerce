"""Schemas para Producto."""

from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime


class ProductoBase(BaseModel):
    """Campos compartidos por create y update."""
    codigo_barras: Optional[str] = Field(None, max_length=50)
    nombre: str = Field(..., min_length=1, max_length=200)
    marca: Optional[str] = None
    descripcion: Optional[str] = None
    precio_referencia: Optional[float] = None
    precio_costo: Optional[float] = None
    precio_venta: Optional[float] = None
    precio_etiqueta: Optional[float] = None
    imagen_url: Optional[str] = None
    sku: Optional[str] = None
    propiedades: Optional[dict] = None
    fuente: Optional[str] = "manual"
    categoria_id: Optional[int] = None
    stock_minimo: Optional[float] = 0.0
    stock_actual: Optional[float] = 0.0
    fecha_vencimiento: Optional[datetime] = None
    tipo_venta: Optional[str] = "unidad"
    precio_por_kilo: Optional[float] = None
    precio_por_unidad: Optional[float] = None


class ProductoCreate(ProductoBase):
    """Schema para crear un producto."""
    cantidad_inicial: Optional[float] = 0.0


class ProductoUpdate(BaseModel):
    """Schema para actualizar. Todos los campos opcionales."""
    nombre: Optional[str] = None
    marca: Optional[str] = None
    descripcion: Optional[str] = None
    codigo_barras: Optional[str] = None
    precio_referencia: Optional[float] = None
    precio_costo: Optional[float] = None
    precio_venta: Optional[float] = None
    precio_etiqueta: Optional[float] = None
    imagen_url: Optional[str] = None
    sku: Optional[str] = None
    propiedades: Optional[dict] = None
    fuente: Optional[str] = None
    categoria_id: Optional[int] = None
    stock_minimo: Optional[float] = None
    stock_actual: Optional[float] = None
    observaciones: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    activo: Optional[bool] = None
    tipo_venta: Optional[str] = None
    precio_por_kilo: Optional[float] = None
    precio_por_unidad: Optional[float] = None


class ProductoOut(ProductoBase):
    """Schema de respuesta con todos los campos."""
    id: int
    stock_actual: float
    stock_transito: Optional[float] = 0.0
    precio_etiqueta: Optional[float] = None
    activo: bool
    ia_analizado: bool
    observaciones: Optional[str] = None
    fecha_vencimiento: Optional[datetime] = None
    categoria_nombre: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProductoLookupRequest(BaseModel):
    """Request para buscar producto por código de barras."""
    barcode: str = Field(..., min_length=1)
    fuente: Optional[str] = None
    ia_mode: bool = False


class ProductoLookupResponse(BaseModel):
    """Respuesta del lookup, incluye comparación de precios."""
    codigo_barras: str
    nombre: str
    marca: Optional[str] = None
    descripcion: Optional[str] = None
    precio_referencia: Optional[float] = None
    imagen_url: Optional[str] = None
    sku: Optional[str] = None
    propiedades: Optional[dict] = None
    fuente: Optional[str] = None
    url: Optional[str] = None
    descuento: Optional[dict] = None
    categoria: Optional[str] = None
    ia_mode: bool = False
    _cached: bool = False
    comparacion: Optional[list] = None
