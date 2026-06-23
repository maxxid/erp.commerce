"""
Modelo Oferta.

Representa una promoción aplicada a un producto.
Tipos: 2x1, porcentaje, monto_fijo.
Se desactiva automáticamente al superar fecha_fin o max_unidades.
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Oferta(Base):
    __tablename__ = "ofertas"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)

    tipo = Column(String(20), nullable=False)           # 2x1 | porcentaje | monto_fijo
    valor = Column(Float, nullable=False, default=0)     # porcentaje=20, monto_fijo=500, 2x1=se ignora
    requiere_cantidad = Column(Integer, nullable=False, default=2)  # unidades mínimas para activar

    fecha_inicio = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    fecha_fin = Column(DateTime, nullable=True)          # null = sin límite temporal

    max_unidades = Column(Integer, nullable=True)        # null = sin límite
    unidades_vendidas = Column(Integer, nullable=False, default=0)

    descripcion = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    producto = relationship("Producto", backref="ofertas")

    def __repr__(self):
        return f"<Oferta(id={self.id}, prod={self.producto_id}, tipo='{self.tipo}', activo={self.activo})>"
