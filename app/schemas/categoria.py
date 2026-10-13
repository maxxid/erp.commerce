"""Schemas para Categoria."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CategoriaBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    padre_id: Optional[int] = None
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoriaCreate(CategoriaBase):
    pass


class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    padre_id: Optional[int] = None
    activo: Optional[bool] = None
    color: Optional[str] = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")


class CategoriaOut(CategoriaBase):
    id: int
    activo: bool
    created_at: datetime
    cantidad_productos: int = 0

    model_config = {"from_attributes": True}
