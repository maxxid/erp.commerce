"""Router de Reportes: análisis de ventas."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.models.venta import Venta, VentaItem
from app.schemas.common import RespuestaData

router = APIRouter(prefix="/api/reportes", tags=["Reportes"])


def _parse_fecha(valor: str, nombre: str) -> datetime:
    try:
        return datetime.strptime(valor, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"{nombre} inválido. Usá formato YYYY-MM-DD")


@router.get("/vendido-por-peso", response_model=RespuestaData)
def vendido_por_peso(
    desde: str = Query(..., description="Fecha inicial YYYY-MM-DD"),
    hasta: str = Query(..., description="Fecha final YYYY-MM-DD (inclusive)"),
    producto_id: Optional[int] = Query(None, description="Filtra un producto puntual"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Vendido por peso: kg e importe por producto en un rango de fechas.

    Solo cuenta ventas confirmadas (las anuladas quedan excluidas).
    El peso y el importe salen de los ítems marcados como venta por kilo.
    """
    try:
        f_desde = _parse_fecha(desde, "desde")
        f_hasta = _parse_fecha(hasta, "hasta") + timedelta(days=1)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if f_desde >= f_hasta:
        raise HTTPException(status_code=400, detail="'desde' debe ser anterior a 'hasta'")

    query = (
        db.query(
            VentaItem.producto_id,
            func.sum(VentaItem.peso).label("peso_total"),
            func.sum(VentaItem.subtotal).label("importe_total"),
            func.count(VentaItem.id).label("ventas"),
            func.min(VentaItem.peso).label("peso_min"),
            func.max(VentaItem.peso).label("peso_max"),
        )
        .join(Venta, Venta.id == VentaItem.venta_id)
        .filter(
            Venta.estado == "confirmada",
            VentaItem.por_kilo == True,
            Venta.fecha >= f_desde,
            Venta.fecha < f_hasta,
        )
    )
    if producto_id:
        query = query.filter(VentaItem.producto_id == producto_id)

    filas = query.group_by(VentaItem.producto_id).all()

    ids = [f.producto_id for f in filas]
    nombres = {}
    if ids:
        for pid, nombre in db.query(Producto.id, Producto.nombre).filter(Producto.id.in_(ids)).all():
            nombres[pid] = nombre

    items = sorted(
        [
            {
                "producto_id": f.producto_id,
                "producto_nombre": nombres.get(f.producto_id, f"Producto {f.producto_id}"),
                "peso_total": round(f.peso_total or 0, 3),
                "importe_total": round(f.importe_total or 0, 2),
                "ventas": f.ventas,
                "peso_promedio": round((f.peso_total or 0) / f.ventas, 3) if f.ventas else 0,
                "peso_min": round(f.peso_min or 0, 3),
                "peso_max": round(f.peso_max or 0, 3),
            }
            for f in filas
        ],
        key=lambda x: x["importe_total"],
        reverse=True,
    )

    return RespuestaData(
        data={
            "desde": desde,
            "hasta": hasta,
            "items": items,
            "totales": {
                "peso_total": round(sum(i["peso_total"] for i in items), 3),
                "importe_total": round(sum(i["importe_total"] for i in items), 2),
                "ventas": sum(i["ventas"] for i in items),
                "productos": len(items),
            },
        },
        message="Reporte de ventas por peso",
    )
