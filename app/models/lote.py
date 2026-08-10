"""
Modelo Lote.

Cada unidad de stock pertenece a un lote. El lote agrupa mercadería con la misma
fecha de vencimiento y costo. Habilita trazabilidad y despacho FEFO (First Expired,
First Out).

Un producto tiene N lotes. La suma de `cantidad_actual` de los lotes activos es
el stock_actual del producto (cache, recalculado en cada cambio).
"""

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Lote(Base):
    __tablename__ = "lotes"

    id = Column(Integer, primary_key=True, index=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=False, index=True)

    codigo_lote = Column(String(50), nullable=True)
    fecha_fabricacion = Column(DateTime, nullable=True)
    fecha_vencimiento = Column(DateTime, nullable=True, index=True)

    cantidad_inicial = Column(Float, nullable=False, default=0.0)
    cantidad_actual = Column(Float, nullable=False, default=0.0)

    costo = Column(Float, nullable=True)

    activo = Column(Boolean, default=True, nullable=False)
    notas = Column(Text, nullable=True)

    compra_id = Column(Integer, ForeignKey("compras.id"), nullable=True)
    compra_item_id = Column(Integer, ForeignKey("compra_items.id"), nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    producto = relationship("Producto", back_populates="lotes")
    compra = relationship("Compra", back_populates="lotes")
    compra_item = relationship("CompraItem", back_populates="lotes")
    venta_item_lotes = relationship("VentaItemLote", back_populates="lote", cascade="all, delete-orphan")

    @property
    def vencido(self) -> bool:
        if not self.fecha_vencimiento:
            return False
        return self.fecha_vencimiento < datetime.now(timezone.utc)

    @property
    def dias_para_vencer(self):
        if not self.fecha_vencimiento:
            return None
        delta = self.fecha_vencimiento - datetime.now(timezone.utc)
        return int(delta.total_seconds() // 86400)

    def __repr__(self):
        return f"<Lote(id={self.id}, prod={self.producto_id}, cant={self.cantidad_actual}, vto={self.fecha_vencimiento})>"


Index("ix_lotes_producto_vto", Lote.producto_id, Lote.fecha_vencimiento)
Index("ix_lotes_activo", Lote.activo)
