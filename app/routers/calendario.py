"""Router de Calendario: vista diaria de toda la actividad."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
from app.database import get_db
from app.schemas.common import RespuestaData
from app.auth.dependencies import get_current_user
from app.models.usuario import Usuario
from app.models.venta import Venta, VentaItem
from app.models.compra import Compra, CompraItem
from app.models.producto import Producto
from app.models.cliente import Cliente
from app.models.movimiento_caja import MovimientoCaja

router = APIRouter(prefix="/api/calendario", tags=["Calendario"])


@router.get("/dia", response_model=RespuestaData)
def actividad_dia(
    fecha: str = Query(None),
    fecha_desde: str = Query(None, description="Fecha inicio para rango (YYYY-MM-DD)"),
    fecha_hasta: str = Query(None, description="Fecha fin para rango (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Devuelve toda la actividad de un día específico (formato YYYY-MM-DD).
    Si se pasa fecha_desde y fecha_hasta, devuelve la actividad en ese rango.
    """
    if fecha_desde and fecha_hasta:
        try:
            desde = datetime.strptime(fecha_desde, "%Y-%m-%d")
            hasta = datetime.strptime(fecha_hasta, "%Y-%m-%d")
        except ValueError:
            desde = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            hasta = desde + timedelta(days=1)
        inicio = desde.replace(hour=0, minute=0, second=0, microsecond=0)
        fin = (hasta.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1))
        return _actividad_rango(inicio, fin, f"{fecha_desde} a {fecha_hasta}", db)

    try:
        dia = datetime.strptime(fecha, "%Y-%m-%d") if fecha else datetime.now(timezone.utc)
    except ValueError:
        dia = datetime.now(timezone.utc)

    inicio = dia.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = inicio + timedelta(days=1)

    return _actividad_rango(inicio, fin, fecha or inicio.strftime("%Y-%m-%d"), db)


def _actividad_rango(inicio: datetime, fin: datetime, label: str, db: Session) -> RespuestaData:
    """Helper que devuelve toda la actividad en un rango de fechas."""

    # Ventas del día
    ventas = (
        db.query(Venta)
        .filter(Venta.fecha >= inicio, Venta.fecha < fin)
        .order_by(Venta.fecha.desc())
        .all()
    )
    ventas_data = []
    for v in ventas:
        ventas_data.append({
            "id": v.id, "numero": v.numero, "fecha": v.fecha.isoformat() if v.fecha else None,
            "subtotal": v.subtotal, "descuento": v.descuento, "total": v.total,
            "medio_pago": v.medio_pago, "estado": v.estado, "notas": v.notas,
            "items": [
                {"producto_nombre": i.producto.nombre if i.producto else "",
                 "cantidad": i.cantidad, "precio_unitario": i.precio_unitario, "subtotal": i.subtotal}
                for i in v.items
            ]
        })

    # Caja
    movs_caja = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.created_at >= inicio, MovimientoCaja.created_at < fin)
        .order_by(MovimientoCaja.id)
        .all()
    )
    caja_data = []
    for m in movs_caja:
        caja_data.append({
            "id": m.id, "tipo": m.tipo, "monto": m.monto,
            "descripcion": m.descripcion, "medio_pago": m.medio_pago,
            "referencia_tipo": m.referencia_tipo,
            "usuario_nombre": m.usuario.nombre if m.usuario else "",
            "created_at": m.created_at.isoformat() if m.created_at else None,
        })

    # Compras recibidas
    compras = (
        db.query(Compra)
        .filter(
            Compra.estado == "recibida",
            Compra.created_at >= inicio, Compra.created_at < fin,
        )
        .order_by(Compra.created_at.desc())
        .all()
    )
    compras_data = []
    for c in compras:
        compras_data.append({
            "id": c.id, "numero": c.numero,
            "proveedor_nombre": c.proveedor.nombre if c.proveedor else "",
            "subtotal": c.subtotal, "total": c.total,
            "fecha": c.created_at.isoformat() if c.created_at else None,
            "items": [
                {"producto_nombre": i.producto.nombre if i.producto else "",
                 "cantidad": i.cantidad, "precio_unitario": i.precio_unitario, "subtotal": i.subtotal}
                for i in c.items
            ]
        })

    # Productos creados/modificados
    prod_nuevos = (
        db.query(Producto)
        .filter(Producto.created_at >= inicio, Producto.created_at < fin)
        .order_by(Producto.created_at.desc())
        .all()
    )
    prod_modif = (
        db.query(Producto)
        .filter(
            Producto.updated_at >= inicio, Producto.updated_at < fin,
            Producto.created_at < inicio,
        )
        .order_by(Producto.updated_at.desc())
        .all()
    )

    # Clientes nuevos
    cli_nuevos = (
        db.query(Cliente)
        .filter(Cliente.created_at >= inicio, Cliente.created_at < fin)
        .order_by(Cliente.created_at.desc())
        .all()
    )

    return RespuestaData(data={
        "fecha": label,
        "fecha_desde": inicio.strftime("%Y-%m-%d"),
        "fecha_hasta": (fin - timedelta(days=1)).strftime("%Y-%m-%d"),
        "ventas": {
            "total_dia": sum(v.total for v in ventas if v.estado == "confirmada"),
            "cantidad": len([v for v in ventas if v.estado == "confirmada"]),
            "items": ventas_data,
        },
        "caja": {
            "movimientos": caja_data,
            "ingresos_totales": sum(m.monto for m in movs_caja if m.tipo == "ingreso"),
            "egresos_totales": sum(m.monto for m in movs_caja if m.tipo == "egreso"),
        },
        "compras": {
            "recibidas": len(compras),
            "items": compras_data,
        },
        "productos": {
            "nuevos": len(prod_nuevos),
            "modificados": len(prod_modif),
            "nuevos_lista": [{"id": p.id, "nombre": p.nombre, "codigo_barras": p.codigo_barras,
                              "created_at": p.created_at.isoformat() if p.created_at else None}
                             for p in prod_nuevos],
            "modificados_lista": [{"id": p.id, "nombre": p.nombre, "codigo_barras": p.codigo_barras,
                                    "updated_at": p.updated_at.isoformat() if p.updated_at else None}
                                   for p in prod_modif],
        },
        "clientes": {
            "nuevos": len(cli_nuevos),
            "lista": [{"id": c.id, "nombre": c.nombre, "telefono": c.telefono}
                      for c in cli_nuevos]
        },
    })
