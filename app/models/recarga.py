"""
Modelo Recarga: detalle de una recarga de dinero digital (SUBE, saldo, etc.).

Cada recarga es una VENTA (el cliente paga el monto cargado + adicional), pero
el dinero cargado sale de una cuenta digital del negocio (MercadoPago,
SmartPoint, etc.), no del cajón. Por eso la recarga necesita su propio registro:

- venta.total       = monto que pagó el cliente (base + adicional)
- venta.precio_costo= monto que realmente se cargó (base)  -> el adicional es margen
- caja egreso       = monto que salió de la cuenta digital

Sin esto, el Dashboard mostraría como ganancia el total cobrado en vez del
adicional, y el egreso real de la cuenta digital quedaría fuera de la caja.
"""

from sqlalchemy import (
    Column, Integer, Float, DateTime, ForeignKey, String, Boolean, true,
)
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Recarga(Base):
    __tablename__ = "recargas"

    id = Column(Integer, primary_key=True, index=True)
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=False, index=True)
    venta_item_id = Column(Integer, ForeignKey("venta_items.id"), nullable=True)
    producto_id = Column(Integer, ForeignKey("productos.id"), nullable=True)

    unidades = Column(Float, nullable=False, default=1)        #Ej: 3 recargas de $1.000
    monto_base = Column(Float, nullable=False, default=0.0)    # monto de 1 unidad de recarga
    monto_cargado = Column(Float, nullable=False, default=0.0) # total cargado al cliente
    adicional_pct = Column(Float, nullable=False, default=0.0) # % aplicado (10)
    adicional_monto = Column(Float, nullable=False, default=0.0)
    total_cobrado = Column(Float, nullable=False, default=0.0) # lo que pagó el cliente

    medio_pago_cobro = Column(String(30), nullable=True)   # efectivo | transferencia | ...
    medio_pago_carga = Column(String(30), nullable=True)   # de dónde salió el dinero cargado

    # True = la recarga generó un egreso real en caja. Se guarda por recarga para
    # que la anulación sepa si debe revertir el egreso o no.
    genera_egreso = Column(Boolean, nullable=False, default=True, server_default=true())

    estado = Column(String(20), nullable=False, default="confirmada")  # confirmada | anulada
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), default=1, nullable=False, index=True)
    fecha = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    venta = relationship("Venta")
    producto = relationship("Producto")

    @property
    def ganancia(self) -> float:
        return round((self.total_cobrado or 0) - (self.monto_cargado or 0), 2)

    def __repr__(self) -> str:
        return f"<Recarga(id={self.id}, venta={self.venta_id}, cargado={self.monto_cargado}, total={self.total_cobrado})>"
