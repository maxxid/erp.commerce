"""
Modelos Compra y CompraItem.

Compra representa una adquisición de mercadería a un proveedor.
CompraItem es cada línea/producto comprado.
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Compra(Base):
    __tablename__ = "compras"

    id = Column(Integer, primary_key=True, index=True)
    numero = Column(String(20), unique=True, nullable=False, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), default=1, nullable=False)

    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    subtotal = Column(Float, nullable=False, default=0.0)
    iva = Column(Float, nullable=False, default=0.0)
    total = Column(Float, nullable=False, default=0.0)

    estado = Column(String(20), nullable=False, default="pendiente")  # pendiente | parcial | recibida | anulada
    notas = Column(Text, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    proveedor = relationship("Proveedor", back_populates="compras")
    usuario = relationship("Usuario", back_populates="compras")
    sucursal = relationship("Sucursal", back_populates="compras")
    items = relationship("CompraItem", back_populates="compra", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Compra(id={self.id}, numero='{self.numero}', total={self.total})>"


class CompraItem(Base):
    __tablename__ = "compra_items"

    id = Column(Integer, primary_key=True, index=True)
    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=False, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False)

    cantidad = Column(Float, nullable=False)             # cantidad ordenada original
    cantidad_recibida = Column(Float, nullable=False, default=0.0)  # cuánto ya se recibió
    precio_unitario = Column(Float, nullable=False)
    subtotal = Column(Float, nullable=False)

    # Relaciones
    compra = relationship("Compra", back_populates="items")
    producto = relationship("Producto", back_populates="compra_items")

    @property
    def pendiente_recibir(self):
        return max(0, self.cantidad - (self.cantidad_recibida or 0))

    def __repr__(self):
        return f"<CompraItem(prod={self.producto_id}, cant={self.cantidad}, recibido={self.cantidad_recibida})>"
