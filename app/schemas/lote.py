"""Schemas para Lote y VentaItemLote."""

from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field


class LoteCreate(BaseModel):
    """Crear un lote manualmente (caso edge: ajustes, mermas, etc.)."""
    codigo_lote: Optional[str] = Field(None, max_length=50)
    fecha_fabricacion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    cantidad_inicial: float = Field(..., ge=0)
    cantidad_actual: Optional[float] = None
    costo: Optional[float] = Field(None, ge=0)
    activo: bool = True
    notas: Optional[str] = None


class LoteUpdate(BaseModel):
    codigo_lote: Optional[str] = Field(None, max_length=50)
    fecha_fabricacion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    costo: Optional[float] = Field(None, ge=0)
    activo: Optional[bool] = None
    notas: Optional[str] = None


class LoteOut(BaseModel):
    id: int
    producto_id: int
    codigo_lote: Optional[str] = None
    fecha_fabricacion: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = None
    cantidad_inicial: float
    cantidad_actual: float
    costo: Optional[float] = None
    activo: bool
    notas: Optional[str] = None
    compra_id: Optional[int] = None
    compra_item_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    dias_para_vencer: Optional[int] = None
    vencido: bool = False

    model_config = {"from_attributes": True}


class LoteResumenProducto(BaseModel):
    """Resumen de stock por producto: total en lotes activos."""
    producto_id: int
    stock_actual: float
    total_lotes: int
    lotes_activos: int
    proximo_vencimiento: Optional[datetime] = None
    lotes_por_vencer_30d: int = 0
    lotes_vencidos: int = 0


class StockPorLoteReporte(BaseModel):
    """Reporte de stock desglosado por lote."""
    producto_id: int
    producto_nombre: str
    codigo_barras: str
    lotes: list[LoteOut]
    stock_total: float
    valor_total: float
