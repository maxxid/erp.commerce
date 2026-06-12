"""Router de Dashboard: KPIs + analíticas (picos, rankings, alertas)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models.producto import Producto
from app.models.venta import Venta, VentaItem
from app.models.cliente import Cliente
from app.schemas.common import RespuestaData
from app.auth.dependencies import get_current_user
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

HOY = lambda: datetime.now(timezone.utc)


def _inicio_dia(d=None):
    d = d or HOY()
    return d.replace(hour=0, minute=0, second=0, microsecond=0)

def _inicio_mes(d=None):
    d = d or HOY()
    return d.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def _fmt_dt(dt):
    return dt.isoformat() if dt else None


@router.get("/resumen", response_model=RespuestaData)
def resumen(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Dashboard completo con KPIs, analíticas y alertas."""
    hoy = _inicio_dia()
    inicio_mes = _inicio_mes()
    hace_7_dias = hoy - timedelta(days=7)
    hace_14_dias = hoy - timedelta(days=14)

    # ── KPIs base ──
    total_productos = db.query(func.count(Producto.id)).filter(Producto.activo == True).scalar() or 0
    valor_stock = db.query(func.coalesce(func.sum(Producto.precio_venta * Producto.stock_actual), 0)).filter(
        Producto.activo == True, Producto.precio_venta.isnot(None), Producto.stock_actual > 0).scalar() or 0
    total_clientes = db.query(func.count(Cliente.id)).filter(Cliente.activo == True).scalar() or 0
    stock_bajo = db.query(func.count(Producto.id)).filter(
        Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo, Producto.stock_minimo > 0).scalar() or 0

    # ── Ventas del día ──
    ventas_hoy_rows = db.query(Venta).filter(Venta.estado == "confirmada", Venta.fecha >= hoy).all()
    ventas_hoy = sum(v.total for v in ventas_hoy_rows)
    cant_ventas_hoy = len(ventas_hoy_rows)

    # Ventas del mes
    ventas_mes = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes).scalar() or 0
    cant_ventas_mes = db.query(func.count(Venta.id)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes).scalar() or 0

    # ── Tendencia semanal ──
    ventas_semana_actual = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= hace_7_dias).scalar() or 0
    ventas_semana_anterior = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= hace_14_dias, Venta.fecha < hace_7_dias).scalar() or 0
    tendencia = round(((ventas_semana_actual - ventas_semana_anterior) / max(ventas_semana_anterior, 1)) * 100, 1)

    # ── Últimos 7 días ──
    dias_labels = []
    dias_valores = []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        dia_sig = dia + timedelta(days=1)
        total_dia = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= dia, Venta.fecha < dia_sig).scalar() or 0
        dias_labels.append(dia.strftime("%a %d"))
        dias_valores.append(float(total_dia))

    # ── Picos por hora (hoy) ──
    horas = [0] * 24
    for v in ventas_hoy_rows:
        if v.fecha:
            h = v.fecha.hour
            horas[h] += v.total
    horas_labels = [f"{h:02d}:00" for h in range(24)]
    horas_valores = [float(round(h, 2)) for h in horas]

    # ── Top productos del mes ──
    top_items = db.query(
        VentaItem.producto_id, func.sum(VentaItem.cantidad).label("qty"), func.sum(VentaItem.subtotal).label("total")
    ).join(Venta).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes
    ).group_by(VentaItem.producto_id).order_by(func.sum(VentaItem.cantidad).desc()).limit(5).all()
    top_productos = []
    for t in top_items:
        prod = db.query(Producto).filter(Producto.id == t.producto_id).first()
        top_productos.append({
            "id": t.producto_id,
            "nombre": prod.nombre if prod else "?",
            "cantidad_vendida": float(t.qty),
            "total_vendido": float(t.total),
        })

    # ── Stock crítico detalle ──
    criticos = db.query(Producto).filter(
        Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo, Producto.stock_minimo > 0
    ).order_by(Producto.stock_actual).limit(10).all()
    criticos_lista = [{
        "id": p.id, "nombre": p.nombre, "stock_actual": p.stock_actual,
        "stock_minimo": p.stock_minimo, "codigo_barras": p.codigo_barras,
    } for p in criticos]

    # ── Sin stock ──
    sin_stock = db.query(Producto).filter(
        Producto.activo == True, Producto.stock_actual <= 0
    ).order_by(Producto.updated_at.desc()).limit(10).all()
    sin_stock_lista = [{
        "id": p.id, "nombre": p.nombre, "codigo_barras": p.codigo_barras,
    } for p in sin_stock]

    # ── Ticket promedio ──
    ticket_promedio = round(ventas_hoy / max(cant_ventas_hoy, 1), 2)

    # ── Medio de pago más usado ──
    medio_fav = db.query(Venta.medio_pago, func.count(Venta.id)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes
    ).group_by(Venta.medio_pago).order_by(func.count(Venta.id).desc()).first()
    medio_favorito = medio_fav[0] if medio_fav else "—"

    return RespuestaData(data={
        # KPIs
        "total_productos": total_productos,
        "valor_stock": valor_stock,
        "total_clientes": total_clientes,
        "stock_bajo": stock_bajo,
        "ventas_hoy": ventas_hoy,
        "ventas_mes": ventas_mes,
        "cant_ventas_hoy": cant_ventas_hoy,
        "cant_ventas_mes": cant_ventas_mes,
        "ticket_promedio": ticket_promedio,
        "tendencia": tendencia,
        "medio_favorito": medio_favorito,

        # Charts
        "ventas_7_dias": {"labels": dias_labels, "valores": dias_valores},
        "ventas_por_hora": {"labels": horas_labels, "valores": horas_valores},

        # Rankings
        "top_productos_mes": top_productos,

        # Alertas
        "stock_critico": criticos_lista,
        "sin_stock": sin_stock_lista,
    })
