"""
Configuración del sistema: clave-valor persistente.

Para settings que el usuario puede modificar desde la UI.
"""

from sqlalchemy import Column, Integer, String, Text
from app.database import Base


class Configuracion(Base):
    __tablename__ = "configuraciones"

    id = Column(Integer, primary_key=True, index=True)
    clave = Column(String(100), unique=True, nullable=False, index=True)
    valor = Column(String(500), nullable=False)
    valor_texto = Column(Text, nullable=True)  # Para valores largos (certs, keys)
    descripcion = Column(Text, nullable=True)

    def __repr__(self):
        return f"<Config(clave='{self.clave}', valor='{self.valor[:20]}')>"
