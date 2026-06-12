"""
Modelo Cliente.

Puede estar asociado a ventas (opcional). Si tiene saldo_cta_corriente > 0
significa que nos debe dinero. El límite de crédito controla cuánto puede
deber como máximo.
"""

from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    tipo_documento = Column(String(10), nullable=True, default="DNI")
    numero_documento = Column(String(20), unique=True, nullable=True)
    telefono = Column(String(30), nullable=True)
    email = Column(String(100), nullable=True)
    direccion = Column(Text, nullable=True)

    saldo_cta_corriente = Column(Float, default=0.0)
    limite_credito = Column(Float, default=0.0)

    notas = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    ventas = relationship("Venta", back_populates="cliente")

    def __repr__(self):
        return f"<Cliente(id={self.id}, nombre='{self.nombre}')>"
