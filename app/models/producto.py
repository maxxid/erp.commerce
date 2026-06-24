"""
Modelo Producto.

Representa un artículo vendible. El código de barras es único.
El stock se actualiza mediante MovimientoStock (nunca directamente).
Campos de precio: referencia (fuente externa), costo (proveedor), venta (público).
"""

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, JSON, Table,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


# Tabla de asociación muchos-a-muchos entre Producto y Proveedor
producto_proveedor = Table(
    "producto_proveedor",
    Base.metadata,
    Column("producto_id", Integer, ForeignKey("productos.id"), primary_key=True),
    Column("proveedor_id", Integer, ForeignKey("proveedores.id"), primary_key=True),
)


class Producto(Base):
    __tablename__ = "productos"

    id = Column(Integer, primary_key=True, index=True)
    codigo_barras = Column(String(50), unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    marca = Column(String(100), nullable=True)
    descripcion = Column(Text, nullable=True)

    precio_referencia = Column(Float, nullable=True)
    precio_costo = Column(Float, nullable=True)
    precio_venta = Column(Float, nullable=True)
    precio_etiqueta = Column(Float, nullable=True)   # último precio impreso en etiqueta. Si != precio_venta, necesita re-etiquetado.

    imagen_url = Column(String(500), nullable=True)
    sku = Column(String(50), nullable=True)
    propiedades = Column(JSON, nullable=True)

    fuente = Column(String(20), default="manual")
    categoria_id = Column(Integer, ForeignKey("categorias.id"), nullable=True, index=True)

    stock_actual = Column(Float, default=0.0)
    stock_transito = Column(Float, default=0.0)    # Mercadería comprada, aún no recibida
    stock_minimo = Column(Float, default=0.0)

    observaciones = Column(Text, nullable=True)

    activo = Column(Boolean, default=True)
    ia_analizado = Column(Boolean, default=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    categoria = relationship("Categoria", back_populates="productos")
    venta_items = relationship("VentaItem", back_populates="producto")
    compra_items = relationship("CompraItem", back_populates="producto")
    movimientos_stock = relationship("MovimientoStock", back_populates="producto")
    proveedores = relationship("Proveedor", secondary=producto_proveedor, back_populates="productos")

    def __repr__(self):
        return f"<Producto(id={self.id}, nombre='{self.nombre[:30]}', stock={self.stock_actual})>"
