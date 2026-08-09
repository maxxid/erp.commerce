"""Schemas para la relación Producto ↔ Proveedor (tabla puente producto_proveedor)."""

from typing import Optional
from pydantic import BaseModel, Field


class ProductoProveedorAsignar(BaseModel):
    """Body para POST /api/productos/{id}/proveedores."""
    proveedor_id: int = Field(..., gt=0)


class ProductoProveedorUpdate(BaseModel):
    """Body para PUT /api/productos/{id}/proveedores/{pid}."""
    codigo_proveedor: Optional[str] = Field(None, max_length=100)
    costo: Optional[float] = Field(None, ge=0)
    plazo_entrega_dias: Optional[int] = Field(None, ge=0)
    es_principal: Optional[bool] = None
    activo: Optional[bool] = None
    notas: Optional[str] = None


class ProductoProveedorOut(BaseModel):
    """Out para GET /api/productos/{id}/proveedores."""
    id: int
    nombre: str
    cuit: Optional[str] = None
    codigo_proveedor: Optional[str] = None
    costo: Optional[float] = None
    plazo_entrega_dias: Optional[int] = None
    es_principal: int = 0
    activo: int = 1
    notas: Optional[str] = None
