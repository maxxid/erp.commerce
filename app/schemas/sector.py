"""Schemas para Sectores (agrupaciones físicas del local)."""

from typing import Optional

from pydantic import BaseModel, Field


class SectorCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    orden: int = 0


class SectorUpdate(BaseModel):
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=100)
    orden: Optional[int] = None


class SectorOut(BaseModel):
    id: int
    nombre: str
    orden: int
    activo: bool
    cantidad_productos: int = 0
