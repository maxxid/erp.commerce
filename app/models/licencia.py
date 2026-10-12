"""Modelo Licencia: clave de activación con expiración y plan de servicio."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime, timezone
from app.database import Base


class Licencia(Base):
    __tablename__ = "licencias"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, nullable=False)
    cliente = Column(String(200), nullable=False)
    machine_id = Column(String(200), nullable=True)   # ID único de la máquina (hostname + disco)
    # Nivel de servicio: decide qué features están habilitadas (ver
    # app/services/planes_service.py). "trial" no incluye IA.
    plan = Column(String(50), nullable=False, default="trial", index=True)
    # Override por cliente del límite mensual de llamadas de IA.
    # None = usar el límite del plan/configuración.
    limite_ia_mes = Column(Integer, nullable=True)
    fecha_inicio = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    fecha_expiracion = Column(DateTime, nullable=False)
    activa = Column(Boolean, default=False)  # False = key generated but not yet activated
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<Licencia(cliente='{self.cliente}', plan='{self.plan}', exp={self.fecha_expiracion}, activa={self.activa})>"
