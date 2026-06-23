"""Servicio de Ofertas: CRUD + lógica de auto-desactivación."""

from typing import Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.oferta import Oferta
from app.models.producto import Producto


def listar_ofertas(
    db: Session,
    producto_id: Optional[int] = None,
    solo_activas: bool = False,
    page: int = 1,
    page_size: int = 50,
) -> Tuple[List[Oferta], int]:
    """Lista ofertas con filtros y paginación."""
    query = db.query(Oferta)

    if producto_id:
        query = query.filter(Oferta.producto_id == producto_id)

    if solo_activas:
        ahora = datetime.now(timezone.utc)
        query = query.filter(
            Oferta.activo == True,
            Oferta.fecha_inicio <= ahora,
        ).filter(
            (Oferta.fecha_fin.is_(None)) | (Oferta.fecha_fin > ahora)
        )

    total = query.count()
    ofertas = (
        query.order_by(Oferta.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return ofertas, total


def obtener_oferta(db: Session, oferta_id: int) -> Optional[Oferta]:
    """Obtiene una oferta por ID."""
    return db.query(Oferta).filter(Oferta.id == oferta_id).first()


def obtener_oferta_activa_para_producto(db: Session, producto_id: int) -> Optional[Oferta]:
    """Obtiene la oferta activa de un producto (si existe y está vigente)."""
    ahora = datetime.now(timezone.utc)
    return (
        db.query(Oferta)
        .filter(
            Oferta.producto_id == producto_id,
            Oferta.activo == True,
            Oferta.fecha_inicio <= ahora,
        )
        .filter(
            (Oferta.fecha_fin.is_(None)) | (Oferta.fecha_fin > ahora)
        )
        .first()
    )


def crear_oferta(db: Session, data: dict) -> Oferta:
    """Crea una oferta nueva."""
    if data.get("fecha_inicio") is None:
        data["fecha_inicio"] = datetime.now(timezone.utc)

    oferta = Oferta(**data)
    db.add(oferta)
    db.commit()
    db.refresh(oferta)
    return oferta


def actualizar_oferta(db: Session, oferta: Oferta, data: dict) -> Oferta:
    """Actualiza campos de una oferta existente."""
    updatable = [
        "tipo", "valor", "requiere_cantidad", "fecha_inicio",
        "fecha_fin", "max_unidades", "descripcion", "activo",
    ]
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(oferta, field, data[field])

    db.commit()
    db.refresh(oferta)
    return oferta


def eliminar_oferta(db: Session, oferta: Oferta):
    """Elimina una oferta permanentemente."""
    db.delete(oferta)
    db.commit()


def verificar_y_desactivar(db: Session, oferta: Oferta) -> bool:
    """Verifica si una oferta debe desactivarse (fecha o cantidad).

    Retorna True si se desactivó.
    """
    ahora = datetime.now(timezone.utc)
    desactivar = False

    if oferta.fecha_fin and ahora > oferta.fecha_fin:
        desactivar = True

    if oferta.max_unidades and oferta.unidades_vendidas >= oferta.max_unidades:
        desactivar = True

    if desactivar:
        oferta.activo = False
        db.commit()

    return desactivar


def incrementar_vendidas(db: Session, producto_id: int, cantidad: float):
    """Incrementa unidades_vendidas de la oferta activa de un producto.

    Llamado desde venta_service al confirmar una venta.
    También verifica si debe desactivarse.
    """
    oferta = obtener_oferta_activa_para_producto(db, producto_id)
    if not oferta:
        return

    oferta.unidades_vendidas += int(cantidad)
    verificar_y_desactivar(db, oferta)
