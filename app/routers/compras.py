"""Router de Compras: crear, items, recibir, anular, listar."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services import compra_service
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.compra import Compra

router = APIRouter(prefix="/api/compras", tags=["Compras"])


def _compra_to_dict(c: Compra) -> dict:
    return {
        "id": c.id, "numero": c.numero,
        "proveedor_id": c.proveedor_id,
        "proveedor_nombre": c.proveedor.nombre if c.proveedor else "",
        "usuario_id": c.usuario_id,
        "sucursal_id": c.sucursal_id,
        "fecha": c.fecha.isoformat() if c.fecha else None,
        "subtotal": c.subtotal, "iva": c.iva, "total": c.total,
        "estado": c.estado, "notas": c.notas,
        "items": [
            {
                "id": i.id, "producto_id": i.producto_id,
                "producto_nombre": i.producto.nombre if i.producto else "",
                "cantidad": i.cantidad,
                "cantidad_recibida": i.cantidad_recibida or 0,
                "pendiente_recibir": i.pendiente_recibir if hasattr(i, 'pendiente_recibir') else max(0, i.cantidad - (i.cantidad_recibida or 0)),
                "precio_unitario": i.precio_unitario,
                "subtotal": i.subtotal,
            }
            for i in (c.items or [])
        ],
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


class CompraCreate(BaseModel):
    proveedor_id: int
    sucursal_id: int = 1
    notas: Optional[str] = None


class CompraItemAdd(BaseModel):
    producto_id: int
    cantidad: float = Field(..., gt=0)
    precio_unitario: float = Field(..., gt=0)


@router.get("", response_model=RespuestaLista)
def listar(
    estado: Optional[str] = Query(None),
    proveedor_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    compras, total = compra_service.listar_compras(
        db, estado=estado, proveedor_id=proveedor_id, page=page, page_size=page_size
    )
    return RespuestaLista(
        data=[_compra_to_dict(c) for c in compras],
        total=total, page=page, page_size=page_size,
    )


@router.get("/{compra_id}", response_model=RespuestaData)
def obtener(compra_id: int, db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    c = compra_service.obtener_compra(db, compra_id)
    if not c: raise HTTPException(status_code=404, detail="Compra no encontrada")
    return RespuestaData(data=_compra_to_dict(c))


@router.post("", response_model=RespuestaData)
def crear(
    data: CompraCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    c = compra_service.crear_compra(db, user.id, data.proveedor_id, data.sucursal_id, data.notas)
    return RespuestaData(data=_compra_to_dict(c), message=f"Compra {c.numero} creada")


@router.post("/{compra_id}/items", response_model=RespuestaData)
def agregar_item(
    compra_id: int,
    data: CompraItemAdd,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    c = compra_service.obtener_compra(db, compra_id)
    if not c: raise HTTPException(status_code=404, detail="Compra no encontrada")
    try:
        item = compra_service.agregar_item(db, c, data.producto_id, data.cantidad, data.precio_unitario)
        db.refresh(c)
        return RespuestaData(
            data={"item_id": item.id, "subtotal": item.subtotal, "compra_subtotal": c.subtotal},
            message="Ítem agregado",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{compra_id}/items/{item_id}", response_model=RespuestaData)
def quitar_item(
    compra_id: int, item_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    c = compra_service.obtener_compra(db, compra_id)
    if not c: raise HTTPException(status_code=404, detail="Compra no encontrada")
    try:
        compra_service.quitar_item(db, c, item_id)
        db.refresh(c)
        return RespuestaData(data={"compra_subtotal": c.subtotal}, message="Ítem quitado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{compra_id}/recibir", response_model=RespuestaData)
def recibir(
    compra_id: int,
    data: Optional[dict] = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Recibe la mercadería. Opcional: pasar 'cantidades': {item_id: cantidad_real}."""
    c = compra_service.obtener_compra(db, compra_id)
    if not c: raise HTTPException(status_code=404, detail="Compra no encontrada")
    try:
        cantidades = (data or {}).get("cantidades", None)
        c = compra_service.recibir_compra(db, c, user.id, cantidades=cantidades)
        return RespuestaData(data=_compra_to_dict(c), message=f"Compra {c.numero} recibida.")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{compra_id}/anular", response_model=RespuestaData)
def anular(
    compra_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    c = compra_service.obtener_compra(db, compra_id)
    if not c: raise HTTPException(status_code=404, detail="Compra no encontrada")
    try:
        c = compra_service.anular_compra(db, c)
        return RespuestaData(data=_compra_to_dict(c), message=f"Compra {c.numero} anulada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class ComentarioRequest(BaseModel):
    texto: str = Field(..., min_length=1, max_length=500)


@router.post("/{compra_id}/comentario", response_model=RespuestaData)
def agregar_comentario(
    compra_id: int,
    data: ComentarioRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado", "cajero")),
):
    """Agrega un comentario con fecha/hora a la compra. Se concatena al historial."""
    c = compra_service.obtener_compra(db, compra_id)
    if not c: raise HTTPException(status_code=404, detail="Compra no encontrada")
    from datetime import datetime, timezone
    ahora = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    entrada = f"[{ahora}] {user.nombre}: {data.texto}"
    if c.notas:
        c.notas = c.notas + "\n" + entrada
    else:
        c.notas = entrada
    db.commit()
    db.refresh(c)
    return RespuestaData(data={"notas": c.notas}, message="Comentario agregado")
