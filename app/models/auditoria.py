"""Modelo Auditoria: registro de acciones en POS para detección de fraude."""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Auditoria(Base):
    __tablename__ = "auditoria"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    tipo = Column(String(30), nullable=False)  # carrito_creado | item_quitado | venta_confirmada | venta_anulada
    venta_id = Column(Integer, ForeignKey("ventas.id"), nullable=True)
    venta_numero = Column(String(20), nullable=True)
    detalle = Column(Text, nullable=True)  # JSON con info extra (producto, montos, etc.)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    usuario = relationship("Usuario")

    def __repr__(self):
        return f"<Auditoria(id={self.id}, tipo='{self.tipo}', user={self.usuario_id})>"
