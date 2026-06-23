"""Schemas para Oferta."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class OfertaBase(BaseModel):
    """Campos compartidos por create y update."""
    producto_id: int
    tipo: str = Field(..., pattern=r"^(2x1|porcentaje|monto_fijo)$")
    valor: float = Field(0, ge=0)
    requiere_cantidad: int = Field(2, ge=1)
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    max_unidades: Optional[int] = Field(None, ge=1)
    descripcion: Optional[str] = None


class OfertaCreate(OfertaBase):
    """Schema para crear una oferta."""
    pass


class OfertaUpdate(BaseModel):
    """Schema para actualizar. Todos los campos opcionales."""
    tipo: Optional[str] = Field(None, pattern=r"^(2x1|porcentaje|monto_fijo)$")
    valor: Optional[float] = Field(None, ge=0)
    requiere_cantidad: Optional[int] = Field(None, ge=1)
    fecha_inicio: Optional[datetime] = None
    fecha_fin: Optional[datetime] = None
    max_unidades: Optional[int] = Field(None, ge=1)
    descripcion: Optional[str] = None
    activo: Optional[bool] = None


class OfertaOut(BaseModel):
    """Schema de respuesta con todos los campos."""
    id: int
    producto_id: int
    producto_nombre: Optional[str] = None
    producto_codigo: Optional[str] = None
    tipo: str
    valor: float
    requiere_cantidad: int
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    max_unidades: Optional[int] = None
    unidades_vendidas: int
    descripcion: Optional[str] = None
    activo: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}
