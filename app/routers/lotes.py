"""Router de Lotes: gestión de stock por lote y FEFO."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel, Field
from datetime import datetime

from app.database import get_db
from app.services import lote_service
from app.schemas.lote import LoteOut, LoteUpdate, LoteCreate
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.lote import Lote
from app.models.producto import Producto
from app.models.venta import VentaItemLote


router = APIRouter(prefix="/api/lotes", tags=["Lotes"])


def _lote_to_dict(l: Lote) -> dict:
    return {
        "id": l.id,
        "producto_id": l.producto_id,
        "producto_nombre": l.producto.nombre if l.producto else None,
        "codigo_barras": l.producto.codigo_barras if l.producto else None,
        "codigo_lote": l.codigo_lote,
        "fecha_fabricacion": l.fecha_fabricacion.isoformat() if l.fecha_fabricacion else None,
        "fecha_vencimiento": l.fecha_vencimiento.isoformat() if l.fecha_vencimiento else None,
        "cantidad_inicial": l.cantidad_inicial,
        "cantidad_actual": l.cantidad_actual,
        "costo": l.costo,
        "activo": l.activo,
        "notas": l.notas,
        "compra_id": l.compra_id,
        "compra_item_id": l.compra_item_id,
        "created_at": l.created_at.isoformat() if l.created_at else None,
        "updated_at": l.updated_at.isoformat() if l.updated_at else None,
        "vencido": l.vencido,
        "dias_para_vencer": l.dias_para_vencer,
    }


@router.get("", response_model=RespuestaLista)
def listar(
    producto_id: Optional[int] = Query(None),
    solo_activos: bool = Query(True),
    solo_con_stock: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    lotes, total = lote_service.listar_lotes(
        db, producto_id=producto_id, solo_activos=solo_activos,
        solo_con_stock=solo_con_stock, page=page, page_size=page_size,
    )
    return RespuestaLista(
        data=[_lote_to_dict(l) for l in lotes],
        total=total, page=page, page_size=page_size,
    )


@router.get("/alertas", response_model=RespuestaData)
def alertas(
    dias: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lotes activos con stock > 0 próximos a vencer o ya vencidos."""
    por_vencer = lote_service.lotes_por_vencer(db, dias=dias)
    vencidos = lote_service.lotes_vencidos(db)
    return RespuestaData(data={
        "por_vencer": [_lote_to_dict(l) for l in por_vencer],
        "vencidos": [_lote_to_dict(l) for l in vencidos],
        "dias_consultados": dias,
    })


@router.get("/{lote_id}", response_model=RespuestaData)
def obtener(
    lote_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    lote = lote_service.obtener_lote(db, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    return RespuestaData(data=_lote_to_dict(lote))


@router.post("", response_model=RespuestaData)
def crear(
    data: LoteCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Crea un lote manualmente (caso edge: mermas, ajustes, productos sin compra)."""
    producto = db.query(Producto).filter(Producto.id == data.producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    try:
        cantidad = data.cantidad_actual if data.cantidad_actual is not None else data.cantidad_inicial
        lote = lote_service.crear_lote(
            db,
            producto_id=data.producto_id,
            codigo_lote=data.codigo_lote,
            fecha_vencimiento=data.fecha_vencimiento,
            fecha_fabricacion=data.fecha_fabricacion,
            cantidad=cantidad,
            costo=data.costo,
            notas=data.notas,
        )
        return RespuestaData(data=_lote_to_dict(lote), message="Lote creado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{lote_id}", response_model=RespuestaData)
def editar(
    lote_id: int,
    data: LoteUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Edita los metadatos del lote (no se puede cambiar cantidad_actual)."""
    try:
        lote = lote_service.actualizar_lote(db, lote_id, data.model_dump(exclude_unset=True))
        return RespuestaData(data=_lote_to_dict(lote), message="Lote actualizado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{lote_id}/desactivar", response_model=RespuestaData)
def desactivar(
    lote_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Soft delete: el lote queda inactivo y excluido del FEFO."""
    try:
        lote = lote_service.desactivar_lote(db, lote_id)
        return RespuestaData(data=_lote_to_dict(lote), message="Lote desactivado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/producto/{producto_id}/resumen", response_model=RespuestaData)
def resumen_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    return RespuestaData(data=lote_service.resumen_producto(db, producto_id))


@router.get("/reporte/stock-por-lote", response_model=RespuestaData)
def reporte_stock_por_lote(
    search: Optional[str] = Query(None, description="Filtra por nombre o código de barras"),
    solo_con_stock: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Reporte: stock desglosado por lote, valorizado al costo de cada lote."""
    from sqlalchemy import or_

    q_productos = db.query(Producto).filter(Producto.activo == True)
    if search:
        like = f"%{search}%"
        q_productos = q_productos.filter(or_(
            Producto.nombre.ilike(like),
            Producto.codigo_barras.ilike(like),
        ))

    total_productos = q_productos.count()
    productos = q_productos.order_by(Producto.nombre).offset((page - 1) * page_size).limit(page_size).all()

    data = []
    valor_total_general = 0.0
    for prod in productos:
        q_lotes = db.query(Lote).filter(Lote.producto_id == prod.id, Lote.activo == True)
        if solo_con_stock:
            q_lotes = q_lotes.filter(Lote.cantidad_actual > 0)
        lotes = q_lotes.order_by(Lote.fecha_vencimiento.asc().nulls_last()).all()
        if not lotes:
            continue
        stock_total = sum(l.cantidad_actual for l in lotes)
        if stock_total <= 0 and solo_con_stock:
            continue
        valor_total = sum((l.costo or 0) * l.cantidad_actual for l in lotes)
        valor_total_general += valor_total
        data.append({
            "producto_id": prod.id,
            "producto_nombre": prod.nombre,
            "codigo_barras": prod.codigo_barras,
            "stock_total": stock_total,
            "valor_total": round(valor_total, 2),
            "lotes": [_lote_to_dict(l) for l in lotes],
        })

    return RespuestaData(data={
        "productos": data,
        "total_productos": total_productos,
        "valor_total_general": round(valor_total_general, 2),
        "page": page,
        "page_size": page_size,
    })
