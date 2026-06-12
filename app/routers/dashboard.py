"""Router de Dashboard: KPIs para el panel principal."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models.producto import Producto
from app.models.venta import Venta
from app.models.cliente import Cliente
from app.schemas.common import RespuestaData
from app.auth.dependencies import get_current_user
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/resumen", response_model=RespuestaData)
def resumen(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """KPIs generales del negocio."""
    total_productos = db.query(func.count(Producto.id)).filter(
        Producto.activo == True
    ).scalar() or 0

    valor_stock = db.query(
        func.coalesce(func.sum(Producto.precio_venta * Producto.stock_actual), 0)
    ).filter(
        Producto.activo == True,
        Producto.precio_venta.isnot(None),
        Producto.stock_actual > 0,
    ).scalar() or 0

    total_clientes = db.query(func.count(Cliente.id)).filter(
        Cliente.activo == True
    ).scalar() or 0

    stock_bajo = db.query(func.count(Producto.id)).filter(
        Producto.activo == True,
        Producto.stock_actual <= Producto.stock_minimo,
        Producto.stock_minimo > 0,
    ).scalar() or 0

    hoy = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    ventas_hoy = db.query(
        func.coalesce(func.sum(Venta.total), 0)
    ).filter(
        Venta.estado == "confirmada",
        Venta.fecha >= hoy,
    ).scalar() or 0

    ventas_mes = db.query(
        func.coalesce(func.sum(Venta.total), 0)
    ).filter(
        Venta.estado == "confirmada",
        Venta.fecha >= hoy.replace(day=1),
    ).scalar() or 0

    ultimo = db.query(Producto).filter(Producto.activo == True).order_by(
        Producto.updated_at.desc()
    ).first()

    return RespuestaData(data={
        "total_productos": total_productos,
        "valor_stock": valor_stock,
        "total_clientes": total_clientes,
        "stock_bajo": stock_bajo,
        "ventas_hoy": ventas_hoy,
        "ventas_mes": ventas_mes,
        "ultimo_producto": {
            "nombre": ultimo.nombre,
            "codigo_barras": ultimo.codigo_barras,
            "fecha": ultimo.updated_at.isoformat() if ultimo and ultimo.updated_at else None,
        } if ultimo else None,
    })
