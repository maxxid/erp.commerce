"""Router de Permisos: la matriz de qué puede hacer cada rol.

Una sola respuesta, desde una sola tabla (`app/auth/permisos.py`). La pestaña
de Usuarios la muestra en modo lectura para que el dueño vea qué hace cada rol
sin tener que preguntarle a nadie — y sin que existan tres listas distintas
de roles que terminan divergiendo.
"""

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_role
from app.auth import permisos as mapa
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData

router = APIRouter(prefix="/api/permisos", tags=["Permisos"])


@router.get("", response_model=RespuestaData)
def ver_matriz(user: Usuario = Depends(require_role("admin"))):
    """La matriz de permisos: los roles, las áreas del sistema y los permisos
    especiales que se le pueden otorgar a una persona puntual."""
    return RespuestaData(data=mapa.a_dict(), message="Matriz de permisos")
