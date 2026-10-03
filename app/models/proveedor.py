"""
Modelo Proveedor.

Empresa o persona que abastece de productos al comercio.
Se relaciona con las compras realizadas.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    cuit = Column(String(20), unique=True, nullable=True)
    telefono = Column(String(30), nullable=True)
    email = Column(String(100), nullable=True)
    direccion = Column(Text, nullable=True)
    nombre_contacto = Column(String(100), nullable=True)
    notas = Column(Text, nullable=True)
    activo = Column(Boolean, default=True)

    # Saldo de la cuenta corriente: lo que le debemos al proveedor.
    # Es una caché; la verdad son las filas de DeudaProveedor y PagoProveedor.
    # recalcular_saldo() en proveedor_pago_service.py es el único que escribe.
    saldo_cta_corriente = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    compras = relationship("Compra", back_populates="proveedor")
    productos = relationship("Producto", secondary="producto_proveedor", back_populates="proveedores")
    deudas = relationship("DeudaProveedor", back_populates="proveedor", cascade="all, delete-orphan")
    pagos = relationship("PagoProveedor", back_populates="proveedor")

    def __repr__(self):
        return f"<Proveedor(id={self.id}, nombre='{self.nombre}')>"
