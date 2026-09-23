"""
Modelo MovimientoCaja.

Registra cada flujo de dinero: apertura, cierre, ingresos por ventas,
egresos por compras, retiros o depósitos extra.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class MovimientoCaja(Base):
    __tablename__ = "movimientos_caja"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(20), nullable=False)        # apertura | cierre | cierre_parcial | ingreso | egreso
    monto = Column(Float, nullable=False)
    descripcion = Column(String(200), nullable=True)
    medio_pago = Column(String(30), nullable=True)    # efectivo | debito | credito | transferencia
    referencia_tipo = Column(String(20), nullable=True)  # venta | compra | retiro | deposito
    referencia_id = Column(Integer, nullable=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    sucursal_id = Column(Integer, ForeignKey("sucursales.id"), default=1, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Conciliación de cierres (especialmente automáticos por cambio de día)
    monto_esperado = Column(Float, nullable=True)      # cálculo del sistema (ingresos por ventas)
    monto_confirmado = Column(Float, nullable=True)    # monto real confirmado por el usuario
    confirmado_por_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True)
    confirmado_at = Column(DateTime, nullable=True)
    fue_automatico = Column(Boolean, default=False)    # True = cierre automático por cambio de día
    comentario_concil = Column(Text, nullable=True)    # nota al confirmar/ajustar

    usuario = relationship("Usuario", foreign_keys=[usuario_id], back_populates="movimientos_caja")
    confirmado_por = relationship("Usuario", foreign_keys=[confirmado_por_id])
    sucursal = relationship("Sucursal", back_populates="movimientos_caja")

    def __repr__(self):
        return f"<MovCaja(id={self.id}, tipo='{self.tipo}', monto={self.monto})>"
