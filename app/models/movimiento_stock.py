"""
Modelo MovimientoStock.

Bitácora inmutable de cada cambio de stock. Se genera automáticamente al:
- Confirmar una venta (tipo="salida")
- Recibir una compra (tipo="entrada")
- Hacer un ajuste manual (tipo="ajuste")

Nunca se edita ni elimina. Es el registro de auditoría del inventario.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class MovimientoStock(Base):
    __tablename__ = "movimientos_stock"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False)       # entrada | salida | ajuste
    cantidad = Column(Float, nullable=False)
    stock_anterior = Column(Float, nullable=False)
    stock_resultante = Column(Float, nullable=False)
    referencia_tipo = Column(String(20), nullable=True)   # venta | compra | ajuste_manual
    referencia_id = Column(Integer, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    notas = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    producto = relationship("Producto", back_populates="movimientos_stock")
    usuario = relationship("Usuario", back_populates="movimientos_stock")

    def __repr__(self):
        return f"<MovStock(id={self.id}, tipo='{self.tipo}', cant={self.cantidad})>"
