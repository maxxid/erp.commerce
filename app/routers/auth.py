"""Router de Autenticación: login, registro, perfil."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.auth.security import verificar_password, hash_password, crear_token
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData
from app.services import licencia_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=4)
    nombre: str = Field(..., min_length=1, max_length=150)
    rol: str = Field(default="cajero")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    rol: str
    nombre: str


@router.post("/login", response_model=RespuestaData[TokenResponse])
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Autentica un usuario y devuelve un token JWT."""
    # Verificar licencia
    if not licencia_service.licencia_valida(db):
        raise HTTPException(status_code=402, detail="Licencia expirada o inválida")

    user = db.query(Usuario).filter(Usuario.username == data.username).first()

    if not user or not verificar_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")

    if not user.activo:
        raise HTTPException(status_code=403, detail="Usuario desactivado")

    from datetime import datetime, timezone
    user.ultimo_login = datetime.now(timezone.utc)
    db.commit()

    token = crear_token({"sub": user.username, "rol": user.rol})
    return RespuestaData(
        data=TokenResponse(
            access_token=token,
            username=user.username,
            rol=user.rol,
            nombre=user.nombre,
        ),
        message="Login exitoso",
    )


@router.post("/register", response_model=RespuestaData)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Registra un nuevo usuario. Solo admin puede."""
    existente = db.query(Usuario).filter(Usuario.username == data.username).first()
    if existente:
        raise HTTPException(status_code=400, detail="El username ya existe")

    nuevo = Usuario(
        username=data.username,
        password_hash=hash_password(data.password),
        nombre=data.nombre,
        rol=data.rol,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return RespuestaData(message=f"Usuario '{nuevo.username}' creado")


@router.get("/me", response_model=RespuestaData)
def me(user: Usuario = Depends(get_current_user)):
    """Devuelve los datos del usuario autenticado."""
    return RespuestaData(data={
        "id": user.id,
        "username": user.username,
        "nombre": user.nombre,
        "rol": user.rol,
        "ultimo_login": user.ultimo_login.isoformat() if user.ultimo_login else None,
    })
