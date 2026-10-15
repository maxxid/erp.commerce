"""
Dependencias de FastAPI para autenticación y autorización.

Proporciona:
- get_current_user: extrae el usuario del token JWT
- require_role: deja pasar a los roles dados o a quien tenga el permiso
  especial que corresponda
"""

from typing import List, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.security import decodificar_token
from app.auth.permisos import tiene_permiso
from app.models.usuario import Usuario

security_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    """Dependency: obtiene el usuario autenticado desde el token JWT.

    Lanza 401 si el token es inválido o el usuario no existe/está inactivo.
    """
    token = credentials.credentials
    payload = decodificar_token(token)

    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
        )

    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token sin subject",
        )

    user = db.query(Usuario).filter(Usuario.username == username).first()
    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado o inactivo",
        )

    return user


def require_role(*roles: str, permiso: Optional[str] = None):
    """Factory de dependency: deja pasar a los roles dados y a quien tenga el
    permiso especial `permiso`.

    El permiso es un "pase suelto" que el dueño le otorga a una persona
    puntual desde la pestaña de Usuarios, sin tener que cambiarle el rol:
    que un cajero vea los reportes, que un repositor pueda anular una venta.
    El dueño (admin) entra siempre, así que no hay riesgo de que se quede
    afuera de su propio sistema.

    Uso:
        @router.get("/reportes")
        def reportes(_ = Depends(require_role("admin", "encargado", permiso="ver_reportes"))):
            ...
    """
    def role_checker(user: Usuario = Depends(get_current_user)) -> Usuario:
        if user.rol in roles:
            return user
        if permiso and tiene_permiso(user, permiso):
            return user
        detalle = f"Se requiere rol: {', '.join(roles)}"
        if permiso:
            detalle += f" o el permiso '{permiso}'"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detalle,
        )

    return role_checker


def requiere_feature(feature: str):
    """Factory de dependency: verifica que el plan de la licencia incluya la feature.

    Devuelve 402 (Payment Required) para que el frontend pueda distinguir
    "no incluido en tu plan" de un error genérico y ofrecer la mejora.

    Uso:
        @router.post("/sugerencias/ia")
        def sugerir(_ = Depends(requiere_feature("ia")), db=Depends(get_db)):
            ...
    """
    def feature_checker(
        db: Session = Depends(get_db),
        user: Usuario = Depends(get_current_user),
    ) -> Usuario:
        from app.services import planes_service

        if not planes_service.tiene_feature(db, feature):
            raise HTTPException(
                status_code=402,
                detail=f"La función '{feature}' no está incluida en tu plan",
            )
        return user

    return feature_checker
