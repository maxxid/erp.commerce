"""Reposición agrupada por proveedor: qué falta y a quién comprárselo.

El universo de productos sale de la misma regla que /productos/stock-bajo
(stock_service.filtro_reposicion). Para cada producto se toman los proveedores
con vínculo activo y los que figuren en compras recibidas/parciales: un
producto comprado a dos proveedores aparece en los dos grupos, con el último
precio pagado a cada uno.
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.compra import Compra, CompraItem
from app.models.producto import Producto, producto_proveedor
from app.models.proveedor import Proveedor
from app.services import stock_service

ESTADOS_VALIDOS = ("recibida", "parcial")


def _faltante(stock, minimo) -> float:
    """Cuánto reponer: lo que falta para el mínimo; al menos 1 si está en cero."""
    stock = float(stock or 0)
    minimo = float(minimo or 0)
    cantidad = max(minimo - stock, 0)
    if stock <= 0 and cantidad < 1:
        cantidad = 1
    return round(cantidad, 2)


def grupos_reposicion(db: Session, proveedor_id: Optional[int] = None) -> list:
    """Agrupa los productos a reponer por proveedor.

    Cada grupo: {id, nombre, telefono, email, productos: [...]}. Los productos
    sin ningún proveedor conocido van al grupo con id=None ("Sin proveedor").
    """
    productos = (
        stock_service.filtro_reposicion(db.query(Producto))
        .order_by(Producto.nombre)
        .all()
    )
    if not productos:
        return []
    ids = [p.id for p in productos]

    proveedores_info = {}
    vinculos = {}
    filas_vinculo = db.execute(
        select(
            producto_proveedor.c.producto_id,
            producto_proveedor.c.proveedor_id,
            producto_proveedor.c.costo,
            producto_proveedor.c.es_principal,
            Proveedor.nombre,
            Proveedor.telefono,
            Proveedor.email,
        )
        .select_from(
            producto_proveedor.join(
                Proveedor, producto_proveedor.c.proveedor_id == Proveedor.id
            )
        )
        .where(
            producto_proveedor.c.producto_id.in_(ids),
            producto_proveedor.c.activo == 1,
        )
    ).all()
    for pid, prov_id, costo, principal, nombre, telefono, email in filas_vinculo:
        vinculos.setdefault(pid, {})[prov_id] = {
            "costo_lista": float(costo) if costo is not None else None,
            "es_principal": bool(principal),
        }
        proveedores_info[prov_id] = {
            "id": prov_id, "nombre": nombre, "telefono": telefono, "email": email,
        }

    ultimo = {}
    filas_historial = db.execute(
        select(
            CompraItem.producto_id,
            Compra.proveedor_id,
            Proveedor.nombre,
            Proveedor.telefono,
            Proveedor.email,
            CompraItem.precio_unitario,
            Compra.fecha,
        )
        .join(Compra, Compra.id == CompraItem.compra_id)
        .join(Proveedor, Proveedor.id == Compra.proveedor_id)
        .where(
            CompraItem.producto_id.in_(ids),
            Compra.estado.in_(ESTADOS_VALIDOS),
        )
        .order_by(Compra.fecha.desc(), Compra.id.desc())
    ).all()
    for pid, prov_id, nombre, telefono, email, precio, fecha in filas_historial:
        proveedores_info[prov_id] = {
            "id": prov_id, "nombre": nombre, "telefono": telefono, "email": email,
        }
        ultimo.setdefault((pid, prov_id), {
            "ultimo_precio_pagado": float(precio) if precio is not None else None,
            "ultima_fecha_pago": fecha.isoformat() if fecha else None,
        })

    historial_por_producto = {}
    for pid, prov_id in ultimo:
        historial_por_producto.setdefault(pid, set()).add(prov_id)

    grupos = {}
    for p in productos:
        prov_ids = set(vinculos.get(p.id, {})) | historial_por_producto.get(p.id, set())
        if not prov_ids:
            prov_ids = {None}
        for prov_id in prov_ids:
            info = proveedores_info.get(prov_id) or {
                "id": None, "nombre": "Sin proveedor", "telefono": None, "email": None,
            }
            grupo = grupos.setdefault(prov_id, {**info, "productos": []})
            vinculo = vinculos.get(p.id, {}).get(prov_id, {})
            pago = ultimo.get((p.id, prov_id), {})
            grupo["productos"].append({
                "producto_id": p.id,
                "nombre": p.nombre,
                "codigo_barras": p.codigo_barras,
                "marca": p.marca,
                "stock_actual": float(p.stock_actual or 0),
                "stock_minimo": float(p.stock_minimo or 0),
                "faltante": _faltante(p.stock_actual, p.stock_minimo),
                "precio_venta": float(p.precio_venta) if p.precio_venta is not None else None,
                "costo_lista": vinculo.get("costo_lista"),
                "es_principal": vinculo.get("es_principal", False),
                "ultimo_precio_pagado": pago.get("ultimo_precio_pagado"),
                "ultima_fecha_pago": pago.get("ultima_fecha_pago"),
            })

    listado = sorted(
        grupos.values(),
        key=lambda g: (g["id"] is None, (g["nombre"] or "").lower()),
    )
    if proveedor_id is not None:
        listado = [g for g in listado if g["id"] == proveedor_id]
    return listado
