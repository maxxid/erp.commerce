"""Modelo Sector: agrupación física (estante, góndola, mesa) del local.

Sirve para ordenar/filtrar la impresión de etiquetas por dónde van colocadas.
"""

from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String
from sqlalchemy.orm import relationship, validates

from app.database import Base


class Sector(Base):
    __tablename__ = "sectores"

    id = Column(Integer, primary_key=True, index=True)
    # Sin unique a nivel DB: el nombre se valida en el router solo contra los
    # activos, así un sector borrado no bloquea volver a crearlo.
    nombre = Column(String(100), nullable=False, index=True)
    orden = Column(Integer, nullable=False, default=0)
    activo = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    productos = relationship("Producto", back_populates="sector")

    @validates("nombre")
    def _title_case(self, campo, valor):
        # El protocolo del catálogo vive en el modelo, igual que en Producto y
        # Categoria. Acá el dedup del router ya es case-insensitive, así que esto
        # solo fija la forma en la que se guarda (los selects y la columna de
        # etiquetas lo muestran tal cual).
        # El import va adentro: texto_service cuelga de app.services, cuyo
        # __init__ importa producto_service, que importa estos modelos.
        if not isinstance(valor, str):
            return valor
        from app.services.texto_service import title_case_es
        return title_case_es(valor)

    def __repr__(self):
        return f"<Sector(id={self.id}, nombre='{self.nombre}', orden={self.orden})>"
