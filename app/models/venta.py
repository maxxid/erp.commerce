"""
Modelos Venta y VentaItem.

Venta representa una transacción de venta completa.
VentaItem es cada línea/producto dentro de la venta.
Guarda el precio al momento de la venta para integridad histórica.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Venta(Base):
    __tablename__ = "ventas"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(20), unique=True, nullable=False, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), default=1, nullable=False)

    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    subtotal = Column(Float, nullable=False, default=0.0)
    descuento = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)

    medio_pago = Column(String(30), nullable=True, default="efectivo")
    estado = Column(String(20), nullable=False, default="pendiente")  # pendiente | confirmada | anulada
    notas = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    cliente = relationship("Cliente", back_populates="ventas")
    usuario = relationship("Usuario", back_populates="ventas")
    sucursal = relationship("Sucursal", back_populates="ventas")
    items = relationship("VentaItem", back_populates="venta", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Venta(id={self.id}, numero='{self.numero}', total={self.total})>"


class VentaItem(Base):
    __tablename__ = "venta_items"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)

    cantidad = Column(Float, nullable=False)
    precio_unitario = Column(Float, nullable=False)
    precio_costo = Column(Float, nullable=True)     # Costo al momento de la venta
    subtotal = Column(Float, nullable=False)

    # Relaciones
    venta = relationship("Venta", back_populates="items")
    producto = relationship("Producto", back_populates="venta_items")

    def __repr__(self):
        return f"<VentaItem(prod={self.producto_id}, cant={self.cantidad}, subt={self.subtotal})>"
