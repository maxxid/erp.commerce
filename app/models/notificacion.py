"""
Modelos Notificacion y NotificacionLeida.

La campana del header necesita dos cosas: qué avisos hay hoy y quién ya los
vio. `notificaciones` guarda el aviso en sí (se genera desde el estado real
del sistema, no desde una acción del usuario) y `notificaciones_leidas` guarda
la lectura.

`notificaciones_leidas.usuario_id` puede ser NULL y ahí la lectura vale para
todos: es el modo "global" que se elige en Ajustes. En modo "usuario" cada
fila es de un usuario y no le borra el aviso al resto.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base


class Notificacion(Base):
    __tablename__ = "notificaciones"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String(40), nullable=False, index=True)
    nivel = Column(String(10), nullable=False, default="warning")  # warning | danger
    titulo = Column(String(200), nullable=False)
    mensaje = Column(Text, nullable=False)
    data = Column(Text, nullable=True)   # JSON: detalle del aviso (productos, etc.)
    clave = Column(String(120), nullable=False, index=True)  # evita duplicar el mismo aviso
    creada_en = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    leidas = relationship("NotificacionLeida", back_populates="notificacion",
                          cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Notificacion(id={self.id}, tipo='{self.tipo}', nivel='{self.nivel}')>"


class NotificacionLeida(Base):
    __tablename__ = "notificaciones_leidas"

    id = Column(Integer, primary_key=True, index=True)
    notificacion_id = Column(Integer, ForeignKey("notificaciones.id"), nullable=False, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=True, index=True)
    leida_en = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    notificacion = relationship("Notificacion", back_populates="leidas")
    usuario = relationship("Usuario")

    def __repr__(self):
        return f"<NotificacionLeida(notif={self.notificacion_id}, user={self.usuario_id})>"
