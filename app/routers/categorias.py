"""Router de Categorías."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.categoria import Categoria
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate, CategoriaOut
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.services.texto_service import title_case_es

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
    # El chequeo va contra la forma canónica: el modelo guarda title case, así
    # que comparar contra el input crudo dejaba pasar variante de casing y el
    # INSERT chocaba con el unique.
    payload = data.model_dump()
    payload["nombre"] = title_case_es(payload["nombre"])
    existente = db.query(Categoria).filter(Categoria.nombre == payload["nombre"]).first()
    if existente:
        raise HTTPException(status_code=400, detail="La categoría ya existe")
    cat = Categoria(**payload)
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
    if "nombre" in update:
        # Mismo criterio que en crear, y excluyendo la propia: renombrar a una
        # variante de otra categoría chocaría con el unique y tiraría un 500.
        update["nombre"] = title_case_es(update["nombre"])
        chocan = (
            db.query(Categoria)
            .filter(Categoria.nombre == update["nombre"], Categoria.id != categoria_id)
            .first()
        )
        if chocan:
            raise HTTPException(status_code=400, detail="La categoría ya existe")
    for k, v in update.items():
        setattr(cat, k, v)
    db.commit()
    db.refresh(cat)
    return RespuestaData(data=cat, message="Categoría actualizada")
