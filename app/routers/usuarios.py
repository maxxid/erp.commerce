"""Router de Usuarios: listar, crear, editar, desactivar. Solo admin."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from app.database import get_db
from app.auth.security import hash_password
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaBase, RespuestaData, RespuestaLista

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios"])


class UsuarioCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)
    nombre: str = Field(..., min_length=1, max_length=150)
    rol: str = Field(default="cajero")  # admin | cajero | encargado | repositor


class UsuarioUpdate(BaseModel):
    nombre: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=4)

    @field_validator("password", mode="before")
    @classmethod
    def _clave_vacia_es_none(cls, v):
        """El form manda "" cuando no se quiere tocar la clave.

        `min_length=4` rechazaba eso con un 422, así que editar un usuario sin
        escribir una clave nueva parecía "no se pudo guardar" sin decir por qué.
        """
        if v is None:
            return None
        v = v.strip() if isinstance(v, str) else v
        return v or None


def _usuario_to_dict(u: Usuario) -> dict:
    return {
        "id": u.id,
        "username": u.username,
        "nombre": u.nombre,
        "rol": u.rol,
        "activo": u.activo,
        "ultimo_login": u.ultimo_login.isoformat() if u.ultimo_login else None,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


@router.get("", response_model=RespuestaLista)
def listar(
    search: Optional[str] = Query(None),
    solo_activos: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    query = db.query(Usuario)
    if search:
        q = f"%{search}%"
        query = query.filter(Usuario.username.ilike(q) | Usuario.nombre.ilike(q))
    if solo_activos:
        query = query.filter(Usuario.activo == True)
    total = query.count()
    usuarios = query.order_by(Usuario.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return RespuestaLista(
        data=[_usuario_to_dict(u) for u in usuarios],
        total=total, page=page, page_size=page_size,
        message=f"{total} usuario(s)",
    )


@router.post("", response_model=RespuestaData)
def crear(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    existente = db.query(Usuario).filter(Usuario.username == data.username).first()
    if existente:
        raise HTTPException(status_code=400, detail="El username ya existe")
    if data.rol not in ("admin", "cajero", "encargado", "repositor"):
        raise HTTPException(status_code=400, detail="Rol inválido")
    nuevo = Usuario(
        username=data.username,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        rol=data.rol,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return RespuestaData(data=_usuario_to_dict(nuevo), message=f"Usuario {nuevo.username} creado")


@router.put("/{usuario_id}", response_model=RespuestaData)
def actualizar(
    usuario_id: int,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if data.nombre is not None:
        u.nombre = data.nombre
    if data.rol is not None:
        if data.rol not in ("admin", "cajero", "encargado", "repositor"):
            raise HTTPException(status_code=400, detail="Rol inválido")
        u.rol = data.rol
    if data.activo is not None:
        if not data.activo:
            _validar_desactivacion(u, current_user)
        u.activo = data.activo
    if data.password is not None:
        u.password_hash = hash_password(data.password)

    db.commit()
    db.refresh(u)
    return RespuestaData(data=_usuario_to_dict(u), message=f"Usuario {u.username} actualizado")


def _validar_desactivacion(u: Usuario, current_user: Usuario) -> None:
    """El administrador jamás se desactiva (ni a sí mismo ni a otro admin).

    Sin esta guarda, un admin que se desactiva solo queda con la única cuenta
    capaz de reactivarlo bloqueada.
    """
    if u.rol == "admin":
        raise HTTPException(status_code=400, detail="No se puede desactivar un usuario Administrador")
    if u.id == current_user.id:
        raise HTTPException(status_code=400, detail="No podés desactivar tu propio usuario")


class ActivoRequest(BaseModel):
    """Estado que el cliente quiere dejar. Sin esto se invierte el actual."""
    activo: Optional[bool] = None


@router.patch("/{usuario_id}/toggle", response_model=RespuestaData)
def alternar_activo(
    usuario_id: int,
    data: Optional[ActivoRequest] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    """Activa/desactiva un usuario. El admin no puede desactivarse.

    El cliente manda el estado que quiere en vez de que el servidor niegue el
    actual: con dos clicks rápidos sobre la misma fila, el "niega" terminaba
    volviendo a activar a quien recién se había desactivado.
    """
    u = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    nuevo = data.activo if data and data.activo is not None else not u.activo
    if not nuevo:
        _validar_desactivacion(u, current_user)
    u.activo = bool(nuevo)
    db.commit()
    db.refresh(u)
    return RespuestaData(
        data=_usuario_to_dict(u),
        message=f"Usuario {u.username} {'activado' if nuevo else 'desactivado'}",
    )


@router.delete("/{usuario_id}", response_model=RespuestaBase)
def desactivar(
    usuario_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_role("admin")),
):
    u = db.query(Usuario).filter(Usuario.id == usuario_id, Usuario.activo == True).first()
    if not u:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o ya inactivo")
    _validar_desactivacion(u, current_user)
    u.activo = False
    db.commit()
    return RespuestaBase(message=f"Usuario {u.username} desactivado")
