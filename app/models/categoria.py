"""
Modelo Categoria.

Jerarquía: una categoría puede tener una categoría padre (subcategorías).
Ejemplo: Bebidas → Gaseosas → Cola.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    padre_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)

    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    padre = relationship("Categoria", remote_side=[id], backref="subcategorias")
    productos = relationship("Producto", back_populates="categoria")

    def __repr__(self):
        return f"<Categoria(id={self.id}, nombre='{self.nombre}')>"
