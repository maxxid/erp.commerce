"""
Modelo Denominacion.

Denominaciones monetarias habilitadas para el conteo de efectivo en caja
(apertura, cierre por método y arqueo). Se administran desde Ajustes: se pueden
agregar, editar el valor, cambiar el tipo, habilitar o deshabilitar.

Una denominación deshabilitada se conserva en la tabla pero no aparece en el
contador; el `valor` es único para evitar filas duplicadas.
"""

from sqlalchemy import (
    Column, Integer, Float, String, Boolean, DateTime, Index,
)
from datetime import datetime, timezone
from app.database import Base


class Denominacion(Base):
    __tablename__ = "denominaciones"

    id = Column(Integer, primary_key=True, index=True)
    valor = Column(Float, nullable=False, unique=True, index=True)
    tipo = Column(String(10), nullable=False, default="moneda")
    activo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Denominacion(id={self.id}, valor={self.valor}, tipo={self.tipo}, activo={self.activo})>"


Index("ix_denominaciones_tipo_activo", Denominacion.tipo, Denominacion.activo)
