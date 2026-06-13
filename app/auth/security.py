"""
Seguridad: hashing de contraseñas (SHA256) y creación/verificación de JWT.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")

# Soporte para contraseñas viejas (bcrypt) si existen en DB
try:
    pwd_context = CryptContext(schemes=["sha256_crypt", "bcrypt"], deprecated="auto")
except Exception:
    pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def verificar_password(plain: str, hashed: str) -> bool:
    """Compara una contraseña en texto plano con su hash."""
    return pwd_context.verify(plain, hashed)


def hash_password(password: str) -> str:
    """Genera el hash bcrypt de una contraseña."""
    return pwd_context.hash(password)


def crear_token(data: dict, expires_minutes: Optional[int] = None) -> str:
    """Crea un token JWT con los datos proporcionados.

    Args:
        data: Diccionario con los claims (ej: {"sub": username, "rol": "admin"}).
        expires_minutes: Duración del token en minutos. Usa settings por defecto.

    Returns:
        Token JWT codificado.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.JWT_EXPIRE_MINUTES
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decodificar_token(token: str) -> Optional[dict]:
    """Decodifica y valida un token JWT.

    Returns:
        Diccionario con los claims si el token es válido, None si no.
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return None
