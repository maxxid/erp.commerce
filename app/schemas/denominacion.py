"""Schemas para Denominacion (contador de efectivo de caja)."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


TipoDenominacion = Literal["billete", "moneda"]


class DenominacionCreate(BaseModel):
    valor: float = Field(..., gt=0, le=1_000_000_000, description="Valor nominal de la denominación.")
    tipo: TipoDenominacion = "moneda"
    activo: bool = True


class DenominacionUpdate(BaseModel):
    valor: Optional[float] = Field(None, gt=0, le=1_000_000_000)
    tipo: Optional[TipoDenominacion] = None
    activo: Optional[bool] = None


class DenominacionOut(BaseModel):
    id: int
    valor: float
    tipo: str
    activo: bool

    model_config = {"from_attributes": True}
