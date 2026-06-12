"""
Modelo MovimientoCaja.

Registra cada flujo de dinero: apertura, cierre, ingresos por ventas,
egresos por compras, retiros o depósitos extra.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(20), nullable=False)        # apertura | cierre | ingreso | egreso
    monto = Column(Float, nullable=False)
    descripcion = Column(String(200), nullable=True)
    medio_pago = Column(String(30), nullable=True)    # efectivo | debito | credito | transferencia
    referencia_tipo = Column(String(20), nullable=True)  # venta | compra | retiro | deposito
    referencia_id = Column(Integer, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    usuario = relationship("Usuario", back_populates="movimientos_caja")
    sucursal = relationship("Sucursal", back_populates="movimientos_caja")

    def __repr__(self):
        return f"<MovCaja(id={self.id}, tipo='{self.tipo}', monto={self.monto})>"
