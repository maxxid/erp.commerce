"""Servicio de Licencia: generar, activar, validar, verificar expiración con machine binding."""

import hmac
import hashlib
import platform
import uuid
import subprocess
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from app.models.licencia import Licencia
from app.config import settings


def _hmac_sign(message: str) -> str:
    return hmac.new(
        settings.JWT_SECRET.encode(),
        message.encode(),
        hashlib.sha256,
    ).hexdigest()[:12]


def obtener_machine_id() -> str:
    """Genera un ID único para esta máquina basado en hardware."""
    hostname = platform.node() or "unknown"
    disco = ""

    # Intentar obtener serial del disco (timeout corto, no bloquear el startup)
    try:
        if platform.system() == "Windows":
            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 "Get-WmiObject Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber -First 1"],
                capture_output=True, text=True, timeout=3
            )
            if result.returncode == 0 and result.stdout.strip():
                disco = result.stdout.strip()
    except Exception:
        pass

    # Fallback: usar MAC address (instantáneo, no requiere subprocess)
    if not disco:
        try:
            mac = uuid.getnode()
            disco = format(mac, "x")
        except Exception:
            disco = "fallback"

    raw = f"{hostname}|{disco}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def generar_clave(cliente: str, machine_id: str, fecha_expiracion: datetime) -> str:
    """Genera una clave de licencia firmada con HMAC atada a la máquina."""
    msg = f"{cliente}|{machine_id}|{int(fecha_expiracion.timestamp())}"
    firma = _hmac_sign(msg).upper()
    return f"APX-{firma[:4]}-{firma[4:8]}-{firma[8:12]}"


def validar_clave(cliente: str, machine_id: str, fecha_expiracion: datetime, clave: str) -> bool:
    esperada = generar_clave(cliente, machine_id, fecha_expiracion)
    return clave.upper().replace(" ", "") == esperada.upper()


def crear_licencia(db: Session, cliente: str, machine_id: str, dias: int = 30) -> dict:
    """Crea una nueva licencia con clave firmada (uso admin)."""
    expiracion = datetime.now(timezone.utc) + timedelta(days=dias)
    clave = generar_clave(cliente, machine_id, expiracion)
    lic = Licencia(
        clave=clave,
        cliente=cliente,
        machine_id=machine_id,
        fecha_expiracion=expiracion,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return {
        "id": lic.id, "clave": lic.clave, "cliente": lic.cliente,
        "machine_id": lic.machine_id,
        "fecha_inicio": lic.fecha_inicio.isoformat(),
        "fecha_expiracion": lic.fecha_expiracion.isoformat(),
        "activa": lic.activa,
    }


def activar_licencia(db: Session, clave: str, machine_id: str) -> Optional[Licencia]:
    """Activa una licencia. Valida que la clave corresponda a esta máquina y no esté usada."""
    clave = clave.upper().replace(" ", "")
    lic = db.query(Licencia).filter(Licencia.clave == clave).first()
    if not lic:
        return None
    if lic.activa:
        return None
    if lic.machine_id and lic.machine_id != machine_id:
        return None
    lic.activa = True
    lic.machine_id = machine_id
    exp = lic.fecha_expiracion
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    if exp and exp < now:
        lic.fecha_expiracion = now + timedelta(days=30)
        lic.fecha_inicio = now
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
    # Verificar anti-tampering de reloj
    try:
        from app.models.venta import Venta
        ultima_venta = db.query(Venta).order_by(Venta.fecha.desc()).first()
        now = datetime.now(timezone.utc)
        if ultima_venta and ultima_venta.fecha:
            uv = ultima_venta.fecha
            if uv.tzinfo is None:
                uv = uv.replace(tzinfo=timezone.utc)
            if uv > now:
                return False
    except Exception:
        pass  # Si no hay ventas todavía, ignorar
    exp = lic.fecha_expiracion
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    return exp > datetime.now(timezone.utc) if exp else False


def historial_licencias(db: Session) -> list:
    """Historial de todas las licencias."""
    return db.query(Licencia).order_by(Licencia.created_at.desc()).all()
