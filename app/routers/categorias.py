"""Router de Categorías."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.categoria import Categoria
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate, CategoriaOut
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/categorias", tags=["Categorías"])


@router.get("", response_model=RespuestaLista[CategoriaOut])
def listar(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista todas las categorías activas con conteo de productos."""
    categorias = (
        db.query(Categoria)
        .filter(Categoria.activo == True)
        .order_by(Categoria.nombre)
        .all()
    )
    for cat in categorias:
        cat.cantidad_productos = len(cat.productos)
    return RespuestaLista(
        data=categorias, total=len(categorias),
        message=f"{len(categorias)} categoría(s)"
    )


@router.post("", response_model=RespuestaData[CategoriaOut])
def crear(
    data: CategoriaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Crea una categoría nueva."""
    existente = db.query(Categoria).filter(Categoria.nombre == data.nombre).first()
    if existente:
        raise HTTPException(status_code=400, detail="La categoría ya existe")
    cat = Categoria(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return RespuestaData(data=cat, message="Categoría creada")


@router.put("/{categoria_id}", response_model=RespuestaData[CategoriaOut])
def actualizar(
    categoria_id: int,
    data: CategoriaUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Actualiza una categoría."""
    cat = db.query(Categoria).filter(Categoria.id == categoria_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    update = data.model_dump(exclude_unset=True)
    for k, v in update.items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return RespuestaData(data=cat, message="Categoría actualizada")
