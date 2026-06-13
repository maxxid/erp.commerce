"""Router de Ventas: crear, items, confirmar, anular, listar."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services import venta_service
from app.services import auditoria_service
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.venta import Venta

router = APIRouter(prefix="/api/ventas", tags=["Ventas"])


def _venta_to_dict(v: Venta) -> dict:
    """Convierte una venta a dict seguro para JSON, evitando lazy loads."""
    return {
        "id": v.id,
        "numero": v.numero,
        "cliente_id": v.cliente_id,
        "usuario_id": v.usuario_id,
        "sucursal_id": v.sucursal_id,
        "fecha": v.fecha.isoformat() if v.fecha else None,
        "subtotal": v.subtotal,
        "descuento": v.descuento,
        "total": v.total,
        "medio_pago": v.medio_pago,
        "estado": v.estado,
        "notas": v.notas,
        "items": [
            {
                "id": i.id,
                "producto_id": i.producto_id,
                "producto_nombre": i.producto.nombre if i.producto else "",
                "cantidad": i.cantidad,
                "precio_unitario": i.precio_unitario,
                "precio_costo": i.precio_costo,
                "subtotal": i.subtotal,
            }
            for i in (v.items or [])
        ],
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


class VentaCreate(BaseModel):
    cliente_id: Optional[int] = None
    sucursal_id: int = 1
    notas: Optional[str] = None


class VentaItemAdd(BaseModel):
    producto_id: int
    cantidad: float = Field(..., gt=0)
    precio_unitario: Optional[float] = None


class VentaConfirmar(BaseModel):
    medio_pago: str = "efectivo"
    descuento: float = 0.0
    cliente_id: Optional[int] = None


@router.get("", response_model=RespuestaLista)
def listar(
    estado: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista ventas con filtros."""
    ventas, total = venta_service.listar_ventas(
        db, estado=estado, cliente_id=cliente_id, page=page, page_size=page_size
    )
    return RespuestaLista(
        data=[_venta_to_dict(v) for v in ventas],
        total=total, page=page, page_size=page_size,
        message=f"{total} venta(s)"
    )


@router.get("/{venta_id}", response_model=RespuestaData)
def obtener(
    venta_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene una venta con sus items."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return RespuestaData(data=_venta_to_dict(venta))


@router.post("", response_model=RespuestaData)
def crear(
    data: VentaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Crea una venta nueva (vacía, estado pendiente)."""
    venta = venta_service.crear_venta(
        db,
        usuario_id=user.id,
        cliente_id=data.cliente_id,
        sucursal_id=data.sucursal_id,
        notas=data.notas,
    )
    auditoria_service.registrar(db, user.id, "carrito_creado", venta.id, venta.numero)
    return RespuestaData(data=_venta_to_dict(venta), message=f"Venta {venta.numero} creada")


@router.post("/{venta_id}/items", response_model=RespuestaData)
def agregar_item(
    venta_id: int,
    data: VentaItemAdd,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Agrega un producto a la venta."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        item = venta_service.agregar_item(
            db, venta, data.producto_id, data.cantidad, data.precio_unitario
        )
        db.refresh(venta)
        return RespuestaData(
            data={"item_id": item.id, "subtotal": item.subtotal, "venta_subtotal": venta.subtotal},
            message="Ítem agregado",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{venta_id}/items/{item_id}", response_model=RespuestaData)
def quitar_item(
    venta_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Quita un ítem de la venta."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        # Obtener info del item antes de quitarlo para el log
        item_obj = next((i for i in venta.items if i.id == item_id), None)
        detalle = None
        if item_obj:
            detalle = {
                "producto": item_obj.producto.nombre if item_obj.producto else "?",
                "cantidad": item_obj.cantidad,
                "precio": item_obj.precio_unitario,
                "subtotal_anterior": item_obj.subtotal,
                "venta_subtotal_antes": venta.subtotal,
                "venta_total_antes": venta.total,
            }
        venta_service.quitar_item(db, venta, item_id)
        db.refresh(venta)
        if detalle:
            detalle["venta_subtotal_despues"] = venta.subtotal
        auditoria_service.registrar(db, user.id, "item_quitado", venta.id, venta.numero, detalle)
        return RespuestaData(data={"venta_subtotal": venta.subtotal}, message="Ítem quitado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{venta_id}/confirmar", response_model=RespuestaData)
def confirmar(
    venta_id: int,
    data: VentaConfirmar,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Confirma la venta: descuenta stock, registra en caja."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    # Si se especificó cliente_id, asignarlo antes de confirmar
    if data.cliente_id and not venta.cliente_id:
        venta.cliente_id = data.cliente_id
        db.commit()
    try:
        venta = venta_service.confirmar_venta(
            db, venta, data.medio_pago, data.descuento, user.id
        )
        auditoria_service.registrar(db, user.id, "venta_confirmada", venta.id, venta.numero,
                                     {"medio_pago": data.medio_pago, "total": venta.total, "items": len(venta.items)})
        return RespuestaData(
            data=_venta_to_dict(venta),
            message=f"Venta {venta.numero} confirmada. Total: ${venta.total:,.2f}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{venta_id}/anular", response_model=RespuestaData)
def anular(
    venta_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Anula una venta confirmada, revirtiendo stock y caja."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        venta = venta_service.anular_venta(db, venta, user.id)
        auditoria_service.registrar(db, user.id, "venta_anulada", venta.id, venta.numero,
                                     {"total_anulado": venta.total, "medio_pago": venta.medio_pago})
        return RespuestaData(data=_venta_to_dict(venta), message=f"Venta {venta.numero} anulada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
