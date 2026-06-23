"""Router de Ofertas: CRUD de promociones por producto."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.oferta import OfertaCreate, OfertaUpdate, OfertaOut
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.oferta import Oferta
from app.services import oferta_service

router = APIRouter(prefix="/api/ofertas", tags=["Ofertas"])


def _oferta_to_dict(o: Oferta) -> dict:
    """Convierte una oferta a dict seguro para JSON."""
    return {
        "id": o.id,
        "producto_id": o.producto_id,
        "producto_nombre": o.producto.nombre if o.producto else None,
        "producto_codigo": o.producto.codigo_barras if o.producto else None,
        "tipo": o.tipo,
        "valor": o.valor,
        "requiere_cantidad": o.requiere_cantidad,
        "fecha_inicio": o.fecha_inicio.isoformat() if o.fecha_inicio else None,
        "fecha_fin": o.fecha_fin.isoformat() if o.fecha_fin else None,
        "max_unidades": o.max_unidades,
        "unidades_vendidas": o.unidades_vendidas,
        "descripcion": o.descripcion,
        "activo": o.activo,
        "created_at": o.created_at.isoformat() if o.created_at else None,
        "updated_at": o.updated_at.isoformat() if o.updated_at else None,
    }


@router.get("", response_model=RespuestaLista)
def listar(
    producto_id: Optional[int] = Query(None),
    solo_activas: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista ofertas con filtros."""
    ofertas, total = oferta_service.listar_ofertas(
        db, producto_id=producto_id, solo_activas=solo_activas,
        page=page, page_size=page_size,
    )
    return RespuestaLista(
        data=[_oferta_to_dict(o) for o in ofertas],
        total=total, page=page, page_size=page_size,
        message=f"{total} oferta(s)"
    )


@router.get("/activas", response_model=RespuestaLista)
def listar_activas(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista todas las ofertas activas y vigentes (para el POS)."""
    ofertas, total = oferta_service.listar_ofertas(db, solo_activas=True, page_size=200)
    return RespuestaLista(
        data=[_oferta_to_dict(o) for o in ofertas],
        total=total, message=f"{total} oferta(s) activa(s)"
    )


@router.get("/{oferta_id}", response_model=RespuestaData)
def obtener(
    oferta_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene una oferta por ID."""
    oferta = oferta_service.obtener_oferta(db, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    return RespuestaData(data=_oferta_to_dict(oferta))


@router.post("", response_model=RespuestaData)
def crear(
    data: OfertaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Crea una oferta nueva."""
    from app.models.producto import Producto
    producto = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    oferta = oferta_service.crear_oferta(db, data.model_dump())
    return RespuestaData(data=_oferta_to_dict(oferta), message="Oferta creada")


@router.put("/{oferta_id}", response_model=RespuestaData)
def actualizar(
    oferta_id: int,
    data: OfertaUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Actualiza una oferta existente."""
    oferta = oferta_service.obtener_oferta(db, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    oferta = oferta_service.actualizar_oferta(db, oferta, data.model_dump(exclude_unset=True))
    return RespuestaData(data=_oferta_to_dict(oferta), message="Oferta actualizada")


@router.delete("/{oferta_id}", response_model=RespuestaData)
def eliminar(
    oferta_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Elimina una oferta permanentemente."""
    oferta = oferta_service.obtener_oferta(db, oferta_id)
    if not oferta:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")
    oferta_service.eliminar_oferta(db, oferta)
    return RespuestaData(message="Oferta eliminada")
