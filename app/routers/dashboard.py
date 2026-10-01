"""Router de Dashboard: KPIs + analíticas (picos, rankings, alertas, margen, semanal)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.models.producto import Producto
from app.models.venta import Venta, VentaItem
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.licencia import Licencia
from app.models.movimiento_caja import MovimientoCaja
from app.schemas.common import RespuestaData
from app.auth.dependencies import get_current_user
from app.models.usuario import Usuario
from app.services import recarga_service

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

HOY = lambda: datetime.now(timezone.utc)

# Zona horaria Argentina (UTC-3): el "dia" de negocio es local, no UTC.
TZ_AR = timezone(timedelta(hours=-3))


def _a_utc(dt):
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TZ_AR)
    return dt.astimezone(timezone.utc)


def _local(d):
    return (d or HOY()).astimezone(TZ_AR)


def _inicio_dia(d=None):
    local = _local(d)
    return _a_utc(local.replace(hour=0, minute=0, second=0, microsecond=0))


def _inicio_mes(d=None):
    local = _local(d)
    return _a_utc(local.replace(day=1, hour=0, minute=0, second=0, microsecond=0))


def _inicio_semana(d=None):
    local = _local(d)
    return _a_utc((local - timedelta(days=local.weekday())).replace(hour=0, minute=0, second=0, microsecond=0))


def _inicio_trimestre(d=None):
    local = _local(d)
    trimestre = ((local.month - 1) // 3) * 3 + 1
    return _a_utc(local.replace(month=trimestre, day=1, hour=0, minute=0, second=0, microsecond=0))


def _fmt_dt(dt):
    return dt.isoformat() if dt else None


def _costo_ventas(db, desde):
    """Suma el costo total de los items vendidos en un período."""
    costo = db.query(func.coalesce(func.sum(VentaItem.cantidad * func.coalesce(VentaItem.precio_costo, 0)), 0)).join(
        Venta, VentaItem.venta_id == Venta.id
    ).filter(Venta.estado == "confirmada", Venta.fecha >= desde).scalar() or 0
    return float(costo)


# Métricas del gráfico de categorías. "margen_pct" responde "¿en qué categoría
# gano más por peso vendido?", que importe/ganancia/cantidad no muestran: una
# categoría puede ser la de mayor venta y ser la de peor margen.
METRICAS_CATEGORIA = ("importe", "ganancia", "cantidad", "margen_pct")
PERIODOS_CATEGORIA = ("hoy", "semana", "mes", "trimestre")
SIN_CATEGORIA = "sin_categoria"


def _add_meses(desde, n):
    """Primer día del mes n meses después de ``desde``."""
    total = desde.month - 1 + n
    return desde.replace(year=desde.year + total // 12, month=total % 12 + 1, day=1)


def _ventana(periodo):
    """Devuelve (desde, hasta) en UTC para el período pedido."""
    if periodo == "hoy":
        desde = _inicio_dia()
        return desde, desde + timedelta(days=1)
    if periodo == "semana":
        desde = _inicio_semana()
        return desde, desde + timedelta(days=7)
    if periodo == "trimestre":
        desde = _inicio_trimestre()
        return desde, _add_meses(desde, 3)
    desde = _inicio_mes()
    return desde, _add_meses(desde, 1)


def _raices_categorias(db):
    """Para cada categoría, su raíz en la jerarquía y el nombre de esa raíz.

    Las categorías son anidadas (Bebidas -> Gaseosas -> Cola). Un gráfico con los
    tres niveles a la vez es ilegible, así que todo se agrupa en la raíz. También
    toleramos ciclos en la base, que si no dejarían el while colgado.
    """
    info = {c.id: {"nombre": c.nombre, "padre": c.padre_id} for c in db.query(Categoria).all()}

    def raiz(cid):
        actual, visto = cid, set()
        while True:
            cat = info.get(actual)
            if not cat or cat["padre"] is None or cat["padre"] not in info or actual in visto:
                return actual
            visto.add(actual)
            actual = cat["padre"]

    mapa = {cid: raiz(cid) for cid in info}
    # El nombre va del de la raíz, no del de la categoría consultada.
    nombres = {cid: info[raiz(cid)]["nombre"] for cid in info}
    return mapa, nombres


@router.get("/resumen", response_model=RespuestaData)
def resumen(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    """Dashboard completo con KPIs, analíticas y alertas."""
    hoy = _inicio_dia()
    inicio_mes = _inicio_mes()
    hace_7_dias = hoy - timedelta(days=7)
    hace_14_dias = hoy - timedelta(days=14)

    # KPIs base
    total_productos = db.query(func.count(Producto.id)).filter(Producto.activo == True).scalar() or 0
    valor_stock = db.query(func.coalesce(func.sum(Producto.precio_venta * Producto.stock_actual), 0)).filter(
        Producto.activo == True, Producto.precio_venta.isnot(None), Producto.stock_actual > 0).scalar() or 0
    total_clientes = db.query(func.count(Cliente.id)).filter(Cliente.activo == True).scalar() or 0
    stock_bajo = db.query(func.count(Producto.id)).filter(
        Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo, Producto.stock_minimo > 0).scalar() or 0

    # Ventas del día
    ventas_hoy_rows = db.query(Venta).filter(Venta.estado == "confirmada", Venta.fecha >= hoy).all()
    ventas_hoy = sum(v.total for v in ventas_hoy_rows)
    cant_ventas_hoy = len(ventas_hoy_rows)

    # Ventas del mes
    ventas_mes = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes).scalar() or 0
    cant_ventas_mes = db.query(func.count(Venta.id)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes).scalar() or 0

    # Margen bruto
    inicio_semana = _inicio_semana()
    inicio_trimestre = _inicio_trimestre()
    costo_hoy = _costo_ventas(db, hoy)
    costo_mes = _costo_ventas(db, inicio_mes)
    costo_semana = _costo_ventas(db, inicio_semana)
    costo_trimestre = _costo_ventas(db, inicio_trimestre)
    margen_hoy = ventas_hoy - costo_hoy
    margen_mes = ventas_mes - costo_mes
    ventas_semana = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_semana).scalar() or 0
    ventas_trimestre = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_trimestre).scalar() or 0
    margen_semana = ventas_semana - costo_semana
    margen_trimestre = ventas_trimestre - costo_trimestre
    margen_pct_hoy = round((margen_hoy / max(ventas_hoy, 1)) * 100, 1)
    margen_pct_mes = round((margen_mes / max(ventas_mes, 1)) * 100, 1)
    margen_pct_semana = round((margen_semana / max(ventas_semana, 1)) * 100, 1)
    margen_pct_trimestre = round((margen_trimestre / max(ventas_trimestre, 1)) * 100, 1)

    # Tendencia semanal
    ventas_semana_actual = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= hace_7_dias).scalar() or 0
    ventas_semana_anterior = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
        Venta.estado == "confirmada", Venta.fecha >= hace_14_dias, Venta.fecha < hace_7_dias).scalar() or 0
    tendencia = round(((ventas_semana_actual - ventas_semana_anterior) / max(ventas_semana_anterior, 1)) * 100, 1)

    # Últimos 7 días
    dias_labels, dias_valores = [], []
    for i in range(6, -1, -1):
        dia = hoy - timedelta(days=i)
        dia_sig = dia + timedelta(days=1)
        total_dia = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= dia, Venta.fecha < dia_sig).scalar() or 0
        dias_labels.append(dia.strftime("%a %d"))
        dias_valores.append(float(total_dia))

    # Picos por hora (hoy)
    horas = [0] * 24
    for v in ventas_hoy_rows:
        if v.fecha:
            h = v.fecha.hour
            horas[h] += v.total
    horas_labels = [f"{h:02d}:00" for h in range(24)]
    horas_valores = [float(round(h, 2)) for h in horas]

    # Top productos del mes
    top_items = db.query(
        VentaItem.producto_id, func.sum(VentaItem.cantidad).label("qty"), func.sum(VentaItem.subtotal).label("total")
    ).join(Venta).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes
    ).group_by(VentaItem.producto_id).order_by(func.sum(VentaItem.cantidad).desc()).limit(5).all()
    top_productos = []
    for t in top_items:
        prod = db.query(Producto).filter(Producto.id == t.producto_id).first()
        top_productos.append({
            "id": t.producto_id, "nombre": prod.nombre if prod else "?",
            "cantidad_vendida": float(t.qty), "total_vendido": float(t.total),
        })

    # Stock crítico detalle
    criticos = db.query(Producto).filter(
        Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo, Producto.stock_minimo > 0
    ).order_by(Producto.stock_actual).limit(10).all()
    criticos_lista = [{"id": p.id, "nombre": p.nombre, "stock_actual": p.stock_actual,
                       "stock_minimo": p.stock_minimo, "codigo_barras": p.codigo_barras} for p in criticos]

    # Sin stock
    sin_stock = db.query(Producto).filter(
        Producto.activo == True, Producto.stock_actual <= 0
    ).order_by(Producto.updated_at.desc()).limit(10).all()
    sin_stock_lista = [{"id": p.id, "nombre": p.nombre, "codigo_barras": p.codigo_barras} for p in sin_stock]

    # Ticket promedio
    ticket_promedio = round(ventas_hoy / max(cant_ventas_hoy, 1), 2)
    medio_fav = db.query(Venta.medio_pago, func.count(Venta.id)).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_mes
    ).group_by(Venta.medio_pago).order_by(func.count(Venta.id).desc()).first()
    medio_favorito = medio_fav[0] if medio_fav else "—"

    # Recargas de dinero digital (SUBE, saldo, etc.)
    recargas_hoy = recarga_service.resumen(db, hoy, hoy + timedelta(days=1))["totales"]
    recargas_mes = recarga_service.resumen(db, inicio_mes, hoy + timedelta(days=1))["totales"]

    return RespuestaData(data={
        "total_productos": total_productos, "valor_stock": valor_stock,
        "total_clientes": total_clientes, "stock_bajo": stock_bajo,
        "ventas_hoy": ventas_hoy, "ventas_mes": ventas_mes,
        "cant_ventas_hoy": cant_ventas_hoy, "cant_ventas_mes": cant_ventas_mes,
        "ticket_promedio": ticket_promedio, "tendencia": tendencia,
        "medio_favorito": medio_favorito,
        "margen_bruto_hoy": margen_hoy, "margen_bruto_mes": margen_mes,
        "margen_pct_hoy": margen_pct_hoy, "margen_pct_mes": margen_pct_mes,
        "margen_bruto_semana": margen_semana, "margen_bruto_trimestre": margen_trimestre,
        "margen_pct_semana": margen_pct_semana, "margen_pct_trimestre": margen_pct_trimestre,
        "recargas_hoy": recargas_hoy, "recargas_mes": recargas_mes,
        "ventas_7_dias": {"labels": dias_labels, "valores": dias_valores},
        "ventas_por_hora": {"labels": horas_labels, "valores": horas_valores},
        "top_productos_mes": top_productos,
        "stock_critico": criticos_lista, "sin_stock": sin_stock_lista,
    })


@router.get("/por-categoria", response_model=RespuestaData)
def por_categoria(
    metrica: str = Query("importe", description=f"Una de: {', '.join(METRICAS_CATEGORIA)}"),
    periodo: str = Query("mes", description=f"Una de: {', '.join(PERIODOS_CATEGORIA)}"),
    limite: int = Query(10, ge=3, le=30, description="Máximo de categorías a devolver"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Ventas agrupadas por categoría, con la métrica y el período a elección.

    Devuelve las tres métricas más el margen por categoría en una sola respuesta,
    para que el front no tenga que pedir de nuevo al cambiar de métrica.
    """
    if metrica not in METRICAS_CATEGORIA:
        raise HTTPException(status_code=400, detail=f"metrica inválida. Opciones: {', '.join(METRICAS_CATEGORIA)}")
    if periodo not in PERIODOS_CATEGORIA:
        raise HTTPException(status_code=400, detail=f"periodo inválido. Opciones: {', '.join(PERIODOS_CATEGORIA)}")

    desde, hasta = _ventana(periodo)
    mapa_raiz, nombres_raiz = _raices_categorias(db)

    filas = db.query(
        Producto.categoria_id,
        func.coalesce(func.sum(VentaItem.subtotal), 0).label("importe"),
        func.coalesce(func.sum(VentaItem.cantidad), 0).label("cantidad"),
        func.coalesce(func.sum(VentaItem.cantidad * func.coalesce(VentaItem.precio_costo, 0)), 0).label("costo"),
        func.count(VentaItem.id).label("items"),
        func.count(VentaItem.precio_costo).label("items_con_costo"),
    ).join(
        VentaItem, VentaItem.producto_id == Producto.id
    ).join(
        Venta, VentaItem.venta_id == Venta.id
    ).filter(
        Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta
    ).group_by(Producto.categoria_id).all()

    # Acumulamos por categoría raíz. Sin categoría propia cae en un grupo aparte,
    # con clave propia (no null) para que el front pueda usarla de :key.
    grupos = {}
    for cat_id, importe, cantidad, costo, items, con_costo in filas:
        raiz = mapa_raiz.get(cat_id) if cat_id is not None else None
        clave = raiz if raiz is not None else SIN_CATEGORIA
        g = grupos.setdefault(
            clave,
            {"importe": 0.0, "cantidad": 0.0, "costo": 0.0, "items": 0, "items_con_costo": 0},
        )
        g["importe"] += float(importe or 0)
        g["cantidad"] += float(cantidad or 0)
        g["costo"] += float(costo or 0)
        g["items"] += items or 0
        g["items_con_costo"] += con_costo or 0

    def _fila(clave, nombre, g):
        ganancia = g["importe"] - g["costo"]
        return {
            "clave": clave,
            "categoria": nombre,
            "importe": round(g["importe"], 2),
            "costo": round(g["costo"], 2),
            "ganancia": round(ganancia, 2),
            "cantidad": round(g["cantidad"], 2),
            "margen_pct": round((ganancia / g["importe"] * 100), 1) if g["importe"] > 0 else 0.0,
            "items": g["items"],
            # Si faltan costos, la ganancia/margen de esa categoría no es confiable.
            "items_sin_costo": g["items"] - g["items_con_costo"],
        }

    lista = [
        _fila(clave, "Sin categoría" if clave == SIN_CATEGORIA else nombres_raiz.get(clave, "?"), g)
        for clave, g in grupos.items()
    ]
    lista.sort(key=lambda r: r[metrica], reverse=True)

    # El resto se agrupa en "Otras" para que el gráfico siga siendo legible.
    # Los porcentajes se recalculan sobre los totales, no se promedian.
    top = lista[:limite]
    resto = lista[limite:]
    if resto:
        agregado = {
            "importe": sum(r["importe"] for r in resto),
            "cantidad": sum(r["cantidad"] for r in resto),
            "costo": sum(r["costo"] for r in resto),
            "items": sum(r["items"] for r in resto),
            "items_con_costo": sum(r["items"] - r["items_sin_costo"] for r in resto),
        }
        top.append(_fila("otras", f"Otras ({len(resto)})", agregado))

    totales = {
        "importe": round(sum(r["importe"] for r in lista), 2),
        "costo": round(sum(r["costo"] for r in lista), 2),
        "ganancia": round(sum(r["ganancia"] for r in lista), 2),
        "cantidad": round(sum(r["cantidad"] for r in lista), 2),
    }
    totales["margen_pct"] = (
        round(totales["ganancia"] / totales["importe"] * 100, 1) if totales["importe"] > 0 else 0.0
    )

    return RespuestaData(data={
        "metrica": metrica,
        "periodo": periodo,
        "categorias": top,
        "totales": totales,
        "cantidad_categorias": len(lista),
    })


@router.get("/semanal", response_model=RespuestaData)
def semanal(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    """Reporte semanal con comparación vs semana anterior."""
    inicio_actual = _inicio_semana()
    inicio_anterior = inicio_actual - timedelta(days=7)

    def _ventas_periodo(desde):
        return db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < desde + timedelta(days=7)
        ).scalar() or 0

    def _costo_periodo(desde):
        return db.query(func.coalesce(func.sum(VentaItem.cantidad * func.coalesce(VentaItem.precio_costo, 0)), 0)).join(
            Venta, VentaItem.venta_id == Venta.id
        ).filter(Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < desde + timedelta(days=7)).scalar() or 0

    def _tickets_periodo(desde):
        return db.query(func.count(Venta.id)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < desde + timedelta(days=7)
        ).scalar() or 0

    ventas_actual = _ventas_periodo(inicio_actual)
    ventas_anterior = _ventas_periodo(inicio_anterior)
    costo_actual = _costo_periodo(inicio_actual)
    costo_anterior = _costo_periodo(inicio_anterior)
    tickets_actual = _tickets_periodo(inicio_actual)
    tickets_anterior = _tickets_periodo(inicio_anterior)

    margen_actual = ventas_actual - costo_actual
    margen_anterior = ventas_anterior - costo_anterior

    # Ventas por día de la semana actual
    dias_nombres = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    dias_data = []
    for i in range(7):
        dia = inicio_actual + timedelta(days=i)
        dia_sig = dia + timedelta(days=1)
        total = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= dia, Venta.fecha < dia_sig).scalar() or 0
        costo = db.query(func.coalesce(func.sum(VentaItem.cantidad * func.coalesce(VentaItem.precio_costo, 0)), 0)).join(
            Venta, VentaItem.venta_id == Venta.id
        ).filter(Venta.estado == "confirmada", Venta.fecha >= dia, Venta.fecha < dia_sig).scalar() or 0
        dias_data.append({
            "dia": dias_nombres[i], "ventas": float(total), "costo": float(costo),
            "margen": float(total - costo),
        })

    # Top 10 productos de la semana
    top = db.query(
        VentaItem.producto_id, func.sum(VentaItem.cantidad).label("qty"), func.sum(VentaItem.subtotal).label("total")
    ).join(Venta).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_actual
    ).group_by(VentaItem.producto_id).order_by(func.sum(VentaItem.cantidad).desc()).limit(10).all()
    top_lista = []
    for t in top:
        prod = db.query(Producto).filter(Producto.id == t.producto_id).first()
        top_lista.append({"id": t.producto_id, "nombre": prod.nombre if prod else "?",
                          "cantidad": float(t.qty), "total": float(t.total)})

    def _pct_diff(actual, anterior):
        return round(((actual - anterior) / max(anterior, 1)) * 100, 1)

    return RespuestaData(data={
        "ventas_actual": float(ventas_actual), "ventas_anterior": float(ventas_anterior),
        "costo_actual": float(costo_actual), "costo_anterior": float(costo_anterior),
        "margen_actual": float(margen_actual), "margen_anterior": float(margen_anterior),
        "tickets_actual": tickets_actual, "tickets_anterior": tickets_anterior,
        "diff_ventas_pct": _pct_diff(ventas_actual, ventas_anterior),
        "diff_margen_pct": _pct_diff(margen_actual, margen_anterior),
        "diff_tickets_pct": _pct_diff(tickets_actual, tickets_anterior),
        "dias": dias_data,
        "top_productos_semana": top_lista,
    })


@router.get("/alertas", response_model=RespuestaData)
def alertas(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    """Alertas del sistema: stock bajo, licencia, caja sin cerrar, anuladas."""
    alertas = []

    # Stock bajo
    criticos = db.query(Producto).filter(
        Producto.activo == True, Producto.stock_actual <= Producto.stock_minimo, Producto.stock_minimo > 0
    ).count()
    if criticos > 0:
        alertas.append({"tipo": "stock_bajo", "mensaje": f"{criticos} producto(s) bajo stock mínimo", "nivel": "warning"})

    # Sin stock
    agotados = db.query(Producto).filter(Producto.activo == True, Producto.stock_actual <= 0).count()
    if agotados > 0:
        alertas.append({"tipo": "sin_stock", "mensaje": f"{agotados} producto(s) agotados", "nivel": "danger"})

    # Licencia próxima a vencer
    lic = db.query(Licencia).filter(Licencia.activa == True).order_by(Licencia.fecha_expiracion.desc()).first()
    if lic and lic.fecha_expiracion:
        exp = lic.fecha_expiracion
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        dias = (exp - HOY()).days
        if dias <= 7:
            alertas.append({"tipo": "licencia", "mensaje": f"Licencia vence en {max(0, dias)} día(s)", "nivel": "danger" if dias <= 3 else "warning"})

    # Caja sin cerrar (apertura sin cierre total hoy)
    hoy = _inicio_dia()
    apertura = db.query(MovimientoCaja).filter(
        MovimientoCaja.tipo == "apertura", MovimientoCaja.created_at >= hoy
    ).first()
    cierre_total = db.query(MovimientoCaja).filter(
        MovimientoCaja.tipo == "cierre_total", MovimientoCaja.created_at >= hoy
    ).first()
    if apertura and not cierre_total:
        alertas.append({"tipo": "caja_abierta", "mensaje": "Caja abierta sin cierre total", "nivel": "warning"})

    # Ventas anuladas hoy
    anuladas = db.query(func.count(Venta.id)).filter(
        Venta.estado == "anulada", Venta.fecha >= hoy
    ).scalar() or 0
    if anuladas > 0:
        nivel = "danger" if anuladas >= 3 else "warning"
        alertas.append({"tipo": "ventas_anuladas", "mensaje": f"{anuladas} venta(s) anulada(s) hoy", "nivel": nivel})

    # Etiquetas pendientes
    pendientes = db.query(Producto).filter(
        Producto.activo == True, Producto.precio_venta.isnot(None),
        (Producto.precio_etiqueta.is_(None)) | (Producto.precio_etiqueta != Producto.precio_venta)
    ).count()
    if pendientes > 0:
        alertas.append({"tipo": "etiquetas", "mensaje": f"{pendientes} producto(s) necesitan re-etiquetado", "nivel": "warning"})

    return RespuestaData(data={"alertas": alertas, "total": len(alertas)})


@router.get("/mensual", response_model=RespuestaData)
def mensual(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    """Reporte mensual con comparación vs mes anterior."""
    inicio_actual = _inicio_mes()
    inicio_anterior = (_inicio_mes() - timedelta(days=1)).replace(day=1)

    def _ventas_mes(desde):
        hasta = (desde.replace(day=28) + timedelta(days=4)).replace(day=1)
        return db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta
        ).scalar() or 0

    def _costo_mes(desde):
        hasta = (desde.replace(day=28) + timedelta(days=4)).replace(day=1)
        return db.query(func.coalesce(func.sum(VentaItem.cantidad * func.coalesce(VentaItem.precio_costo, 0)), 0)).join(
            Venta, VentaItem.venta_id == Venta.id
        ).filter(Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta).scalar() or 0

    def _tickets_mes(desde):
        hasta = (desde.replace(day=28) + timedelta(days=4)).replace(day=1)
        return db.query(func.count(Venta.id)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta
        ).scalar() or 0

    ventas_actual = _ventas_mes(inicio_actual)
    ventas_anterior = _ventas_mes(inicio_anterior)
    costo_actual = _costo_mes(inicio_actual)
    costo_anterior = _costo_mes(inicio_anterior)
    tickets_actual = _tickets_mes(inicio_actual)
    tickets_anterior = _tickets_mes(inicio_anterior)

    # Ventas por semana del mes actual
    semanas = []
    for s in range(5):
        desde = inicio_actual + timedelta(weeks=s)
        hasta = desde + timedelta(weeks=1)
        if desde.month != inicio_actual.month:
            break
        total = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta
        ).scalar() or 0
        semanas.append({"semana": s + 1, "ventas": float(total), "desde": desde.strftime("%d/%m")})

    # Top 10 productos del mes
    top = db.query(
        VentaItem.producto_id, func.sum(VentaItem.cantidad).label("qty"), func.sum(VentaItem.subtotal).label("total")
    ).join(Venta).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_actual
    ).group_by(VentaItem.producto_id).order_by(func.sum(VentaItem.cantidad).desc()).limit(10).all()
    top_lista = [{"id": t.producto_id, "nombre": (db.query(Producto.nombre).filter(Producto.id == t.producto_id).scalar() or "?"),
                  "cantidad": float(t.qty), "total": float(t.total)} for t in top]

    # Ventas por categoría
    cats = db.query(
        Categoria.nombre, func.coalesce(func.sum(VentaItem.subtotal), 0)
    ).join(Producto, Producto.categoria_id == Categoria.id).join(
        VentaItem, VentaItem.producto_id == Producto.id
    ).join(Venta, VentaItem.venta_id == Venta.id).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_actual
    ).group_by(Categoria.nombre).order_by(func.sum(VentaItem.subtotal).desc()).all()
    cats_lista = [{"categoria": c[0], "total": float(c[1])} for c in cats if c[1] > 0]

    def _pct(actual, anterior):
        return round(((actual - anterior) / max(anterior, 1)) * 100, 1)

    return RespuestaData(data={
        "ventas_actual": float(ventas_actual), "ventas_anterior": float(ventas_anterior),
        "costo_actual": float(costo_actual), "costo_anterior": float(costo_anterior),
        "margen_actual": float(ventas_actual - costo_actual),
        "margen_anterior": float(ventas_anterior - costo_anterior),
        "tickets_actual": tickets_actual, "tickets_anterior": tickets_anterior,
        "ticket_promedio": round(ventas_actual / max(tickets_actual, 1), 2),
        "diff_ventas_pct": _pct(ventas_actual, ventas_anterior),
        "diff_margen_pct": _pct(ventas_actual - costo_actual, ventas_anterior - costo_anterior),
        "semanas": semanas,
        "top_productos": top_lista,
        "por_categoria": cats_lista,
    })


@router.get("/trimestral", response_model=RespuestaData)
def trimestral(db: Session = Depends(get_db), user: Usuario = Depends(get_current_user)):
    """Reporte trimestral con comparación vs trimestre anterior."""
    local = _local(None)
    trim_actual = ((local.month - 1) // 3) * 3 + 1
    inicio_actual = _a_utc(local.replace(month=trim_actual, day=1, hour=0, minute=0, second=0, microsecond=0))
    trim_anterior = trim_actual - 3
    if trim_anterior < 1:
        trim_anterior += 12
    anio_anterior = local.year if trim_anterior > trim_actual else local.year - 1
    inicio_anterior = _a_utc(
        datetime(anio_anterior, trim_anterior, 1, tzinfo=TZ_AR)
    )

    def _ventas_trim(desde):
        hasta = (desde.replace(day=28) + timedelta(days=100)).replace(day=1)
        if hasta.month - desde.month < 3:
            hasta = (desde + timedelta(days=92)).replace(day=1)
        return db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta
        ).scalar() or 0

    def _tickets_trim(desde):
        hasta = (desde.replace(day=28) + timedelta(days=100)).replace(day=1)
        if hasta.month - desde.month < 3:
            hasta = (desde + timedelta(days=92)).replace(day=1)
        return db.query(func.count(Venta.id)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta
        ).scalar() or 0

    ventas_actual = _ventas_trim(inicio_actual)
    ventas_anterior = _ventas_trim(inicio_anterior)
    tickets_actual = _tickets_trim(inicio_actual)
    tickets_anterior = _tickets_trim(inicio_anterior)

    # Ventas por mes del trimestre actual
    meses_nombres = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
    meses_data = []
    for m in range(3):
        desde = inicio_actual.replace(month=inicio_actual.month + m if inicio_actual.month + m <= 12 else inicio_actual.month + m - 12)
        hasta = (desde.replace(day=28) + timedelta(days=4)).replace(day=1)
        total = db.query(func.coalesce(func.sum(Venta.total), 0)).filter(
            Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta
        ).scalar() or 0
        costo = db.query(func.coalesce(func.sum(VentaItem.cantidad * func.coalesce(VentaItem.precio_costo, 0)), 0)).join(
            Venta, VentaItem.venta_id == Venta.id
        ).filter(Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta).scalar() or 0
        meses_data.append({
            "mes": meses_nombres[desde.month - 1], "ventas": float(total),
            "costo": float(costo), "margen": float(total - costo),
        })

    # Top 10 productos del trimestre
    top = db.query(
        VentaItem.producto_id, func.sum(VentaItem.cantidad).label("qty"), func.sum(VentaItem.subtotal).label("total")
    ).join(Venta).filter(
        Venta.estado == "confirmada", Venta.fecha >= inicio_actual
    ).group_by(VentaItem.producto_id).order_by(func.sum(VentaItem.cantidad).desc()).limit(10).all()
    top_lista = [{"id": t.producto_id, "nombre": (db.query(Producto.nombre).filter(Producto.id == t.producto_id).scalar() or "?"),
                  "cantidad": float(t.qty), "total": float(t.total)} for t in top]

    def _pct(actual, anterior):
        return round(((actual - anterior) / max(anterior, 1)) * 100, 1)

    return RespuestaData(data={
        "ventas_actual": float(ventas_actual), "ventas_anterior": float(ventas_anterior),
        "tickets_actual": tickets_actual, "tickets_anterior": tickets_anterior,
        "diff_ventas_pct": _pct(ventas_actual, ventas_anterior),
        "diff_tickets_pct": _pct(tickets_actual, tickets_anterior),
        "meses": meses_data,
        "top_productos": top_lista,
    })


@router.get("/alertas-lotes", response_model=RespuestaData)
def alertas_lotes(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Alertas resumidas: lotes por vencer (30/15/7 días) y lotes vencidos."""
    from app.services import lote_service

    por_vencer_30 = lote_service.lotes_por_vencer(db, dias=30)
    por_vencer_15 = [l for l in por_vencer_30 if (l.dias_para_vencer or 999) <= 15]
    por_vencer_7 = [l for l in por_vencer_30 if (l.dias_para_vencer or 999) <= 7]
    vencidos = lote_service.lotes_vencidos(db)

    def _item(l):
        return {
            "id": l.id,
            "producto_id": l.producto_id,
            "producto_nombre": l.producto.nombre if l.producto else "",
            "codigo_lote": l.codigo_lote,
            "fecha_vencimiento": l.fecha_vencimiento.isoformat() if l.fecha_vencimiento else None,
            "dias_para_vencer": l.dias_para_vencer,
            "cantidad_actual": l.cantidad_actual,
        }

    return RespuestaData(data={
        "vencidos": [_item(l) for l in vencidos],
        "por_vencer_7d": [_item(l) for l in por_vencer_7],
        "por_vencer_15d": [_item(l) for l in por_vencer_15],
        "por_vencer_30d": [_item(l) for l in por_vencer_30],
        "totales": {
            "vencidos": len(vencidos),
            "por_vencer_7d": len(por_vencer_7),
            "por_vencer_15d": len(por_vencer_15),
            "por_vencer_30d": len(por_vencer_30),
        },
    })
