"""Router de Clientes: CRUD básico."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.cliente import Cliente
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/clientes", tags=["Clientes"])


def _cli_to_dict(c):
    if not c: return None
    return {
        "id": c.id, "nombre": c.nombre, "tipo_documento": c.tipo_documento,
        "numero_documento": c.numero_documento, "telefono": c.telefono,
        "email": c.email, "direccion": c.direccion,
        "saldo_cta_corriente": c.saldo_cta_corriente or 0,
        "limite_credito": c.limite_credito or 0,
        "notas": c.notas, "activo": c.activo,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    }


class ClienteCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    tipo_documento: str = "DNI"
    numero_documento: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    limite_credito: float = 0.0
    notas: Optional[str] = None


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    tipo_documento: Optional[str] = None
    numero_documento: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    limite_credito: Optional[float] = None
    notas: Optional[str] = None
    activo: Optional[bool] = None


@router.get("", response_model=RespuestaLista)
def listar(
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista clientes con búsqueda y paginación."""
    query = db.query(Cliente).filter(Cliente.activo == True)

    if search:
        like = f"%{search}%"
        query = query.filter(
            Cliente.nombre.ilike(like) | Cliente.numero_documento.ilike(like)
        )

    total = query.count()
    clientes = (
        query.order_by(Cliente.nombre)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return RespuestaLista(
        data=[_cli_to_dict(c) for c in clientes], total=total, page=page, page_size=page_size,
        message=f"{total} cliente(s)"
    )


@router.get("/{cliente_id}", response_model=RespuestaData)
def obtener(
    cliente_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene un cliente por ID."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return RespuestaData(data=_cli_to_dict(cliente))


@router.post("", response_model=RespuestaData)
def crear(
    data: ClienteCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Crea un cliente nuevo."""
    cliente = Cliente(**data.model_dump())
    db.add(cliente)
    db.commit()
    db.refresh(cliente)
    return RespuestaData(data=_cli_to_dict(cliente), message="Cliente creado")


@router.put("/{cliente_id}", response_model=RespuestaData)
def actualizar(
    cliente_id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Actualiza un cliente."""
    cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    update = data.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(cliente, k, v)
    db.commit()
    db.refresh(cliente)
    return RespuestaData(data=_cli_to_dict(cliente), message="Cliente actualizado")
