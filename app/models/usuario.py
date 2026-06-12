"""
Modelos Usuario y Sucursal.

Usuario: operador del sistema con roles (admin, cajero, encargado, repositor).
Sucursal: punto de venta físico, prepara para multi-sucursal.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Sucursal(Base):
    __tablename__ = "sucursales"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(150), nullable=False)
    direccion = Column(String(200), nullable=True)
    telefono = Column(String(30), nullable=True)
    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ventas = relationship("Venta", back_populates="sucursal")
    compras = relationship("Compra", back_populates="sucursal")
    movimientos_caja = relationship("MovimientoCaja", back_populates="sucursal")

    def __repr__(self):
        return f"<Sucursal(id={self.id}, nombre='{self.nombre}')>"


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    nombre = Column(String(150), nullable=False)
    rol = Column(String(20), nullable=False, default="cajero")  # admin | cajero | encargado | repositor
    activo = Column(Boolean, default=True)
    ultimo_login = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    ventas = relationship("Venta", back_populates="usuario")
    compras = relationship("Compra", back_populates="usuario")
    movimientos_stock = relationship("MovimientoStock", back_populates="usuario")
    movimientos_caja = relationship("MovimientoCaja", back_populates="usuario")

    def __repr__(self):
        return f"<Usuario(id={self.id}, username='{self.username}', rol='{self.rol}')>"
