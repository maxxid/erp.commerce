"""
Modelo Categoria.

Jerarquía: una categoría puede tener una categoría padre (subcategorías).
Ejemplo: Bebidas → Gaseosas → Cola.
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship, validates
from datetime import datetime, timezone
from app.database import Base


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), unique=True, nullable=False, index=True)
    padre_id = Column(Integer, ForeignKey("categorias.id"), nullable=True)
    # #RRGGBB o NULL. Si es NULL la pantalla usa el color por defecto del rubro:
    # así una categoría nueva ya se ve con color sin que nadie la edite.
    color = Column(String(7), nullable=True)

    activo = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    padre = relationship("Categoria", remote_side=[id], backref="subcategorias")
    productos = relationship("Producto", back_populates="categoria")

    @validates("nombre")
    def _title_case(self, campo, valor):
        # El protocolo del catálogo vive en el modelo, igual que en Producto.
        # La columna es unique: así solo se llega a guardar la forma canónica y
        # dos altas del mismo concepto con distinto casing no terminan en dos
        # filas distintas.
        # El import va adentro: texto_service cuelga de app.services, cuyo
        # __init__ importa producto_service, que importa estos modelos.
        if not isinstance(valor, str):
            return valor
        from app.services.texto_service import title_case_es
        return title_case_es(valor)

    def __repr__(self):
        return f"<Categoria(id={self.id}, nombre='{self.nombre}')>"
