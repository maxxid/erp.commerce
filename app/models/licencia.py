"""Modelo Licencia: clave de activación con expiración."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone
from app.database import Base


class Licencia(Base):
    __tablename__ = "licencias"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, nullable=False)
    cliente = Column(String(200), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    fecha_expiracion = Column(DateTime, nullable=False)
    activa = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Licencia(cliente='{self.cliente}', exp={self.fecha_expiracion}, activa={self.activa})>"
