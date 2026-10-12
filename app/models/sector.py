"""Modelo Sector: agrupación física (estante, góndola, mesa) del local.

Sirve para ordenar/filtrar la impresión de etiquetas por dónde van colocadas.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship

from app.database import Base


class Sector(Base):
    __tablename__ = "sectores"

    id = Column(Integer, primary_key=True, index=True)
    # Sin unique a nivel DB: el nombre se valida en el router solo contra los
    # activos, así un sector borrado no bloquea volver a crearlo.
    nombre = Column(String(100), nullable=False, index=True)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    productos = relationship("Producto", back_populates="sector")

    def __repr__(self):
        return f"<Sector(id={self.id}, nombre='{self.nombre}', orden={self.orden})>"
