"""Servicio de Licencia: generar, activar, validar, verificar expiración."""

import hmac
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.licencia import Licencia
from app.config import settings


def _hmac_sign(message: str) -> str:
    """Firma un mensaje con HMAC-SHA256 usando JWT_SECRET."""
    return hmac.new(
        settings.JWT_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()[:12]


def generar_clave(cliente: str, fecha_expiracion: datetime) -> str:
    """Genera una clave de licencia firmada."""
    msg = f"{cliente}|{int(fecha_expiracion.timestamp())}"
    firma = _hmac_sign(msg)
    return f"APX-{firma[:4]}-{firma[4:8]}-{firma[8:12]}"


def validar_clave(cliente: str, fecha_expiracion: datetime, clave: str) -> bool:
    """Verifica que una clave sea válida para los parámetros dados."""
    esperada = generar_clave(cliente, fecha_expiracion)
    return clave.upper().replace(" ", "") == esperada.upper()


def crear_licencia(db: Session, cliente: str, dias: int = 30) -> dict:
    """Crea una nueva licencia con clave firmada (uso admin)."""
    expiracion = datetime.now(timezone.utc) + timedelta(days=dias)
    clave = generar_clave(cliente, expiracion)
    lic = Licencia(
        clave=clave,
        cliente=cliente,
        fecha_expiracion=expiracion,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return {
        "id": lic.id,
        "clave": lic.clave,
        "cliente": lic.cliente,
        "fecha_inicio": lic.fecha_inicio.isoformat(),
        "fecha_expiracion": lic.fecha_expiracion.isoformat(),
        "activa": lic.activa,
    }


def activar_licencia(db: Session, clave: str) -> Optional[Licencia]:
    """Activa una licencia a partir de la clave."""
    clave = clave.upper().replace(" ", "")
    lic = db.query(Licencia).filter(Licencia.clave == clave, Licencia.activa == False).first()
    if lic:
        lic.activa = True
        if lic.fecha_expiracion < datetime.now(timezone.utc):
            lic.fecha_expiracion = datetime.now(timezone.utc) + timedelta(days=30)
            lic.fecha_inicio = datetime.now(timezone.utc)
        db.commit()
    return lic


def obtener_licencia_activa(db: Session) -> Optional[Licencia]:
    """Retorna la licencia activa actual, si existe y no expiró."""
    lic = db.query(Licencia).filter(Licencia.activa == True).order_by(Licencia.fecha_expiracion.desc()).first()
    return lic


def licencia_valida(db: Session) -> bool:
    """True si hay una licencia activa que no expiró."""
    lic = obtener_licencia_activa(db)
    if not lic:
        return False
    # Verificar también contra la fecha de la última venta (anti-tampering de reloj)
    from app.models.venta import Venta
    ultima_venta = db.query(Venta).order_by(Venta.fecha.desc()).first()
    now = datetime.now(timezone.utc)
    if ultima_venta and ultima_venta.fecha:
        uv = ultima_venta.fecha
        if uv.tzinfo is None:
            uv = uv.replace(tzinfo=timezone.utc)
        if uv > now:
            return False
    if lic.fecha_expiracion.tzinfo is None:
        lic.fecha_expiracion = lic.fecha_expiracion.replace(tzinfo=timezone.utc)
    return lic.fecha_expiracion > now


def historial_licencias(db: Session) -> list:
    """Historial de todas las licencias."""
    return db.query(Licencia).order_by(Licencia.created_at.desc()).all()
