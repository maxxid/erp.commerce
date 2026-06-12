"""Router de Proveedores: CRUD."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.models.proveedor import Proveedor
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/proveedores", tags=["Proveedores"])


class ProveedorCreate(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=150)
    cuit: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    nombre_contacto: Optional[str] = None
    notas: Optional[str] = None


class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = None
    cuit: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    nombre_contacto: Optional[str] = None
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
    query = db.query(Proveedor).filter(Proveedor.activo == True)
    if search:
        like = f"%{search}%"
        query = query.filter(Proveedor.nombre.ilike(like) | Proveedor.cuit.ilike(like))
    total = query.count()
    proveedores = query.order_by(Proveedor.nombre).offset((page - 1) * page_size).limit(page_size).all()
    return RespuestaLista(data=[_prov_to_dict(p) for p in proveedores], total=total, page=page, page_size=page_size)


def _prov_to_dict(p):
    return {"id": p.id, "nombre": p.nombre, "cuit": p.cuit, "telefono": p.telefono,
            "email": p.email, "direccion": p.direccion, "nombre_contacto": p.nombre_contacto,
            "notas": p.notas, "activo": p.activo,
            "created_at": p.created_at.isoformat() if p.created_at else None} if p else None


@router.get("/{proveedor_id}", response_model=RespuestaData)
def obtener(proveedor_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p: raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return RespuestaData(data=_prov_to_dict(p))


@router.post("", response_model=RespuestaData)
def crear(data: ProveedorCreate, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    p = Proveedor(**data.model_dump())
    db.add(p); db.commit(); db.refresh(p)
    return RespuestaData(data=_prov_to_dict(p), message="Proveedor creado")


@router.put("/{proveedor_id}", response_model=RespuestaData)
def actualizar(proveedor_id: int, data: ProveedorUpdate, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin", "encargado"))):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p: raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items(): setattr(p, k, v)
    db.commit(); db.refresh(p)
    return RespuestaData(data=_prov_to_dict(p), message="Proveedor actualizado")
