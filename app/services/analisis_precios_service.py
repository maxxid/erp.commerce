"""Análisis de precios de un producto: historial de compras y costos por proveedor.

Todo sale de datos que el sistema ya tiene:
- compras + compra_items: que se pago, cuando y a quien.
- producto_proveedor.costo: el costo de lista actual de cada proveedor.

No hay tabla nueva. Las compras anuladas se excluyen: si no, una compra
cancelada figuraria como "el precio mas bajo que jamais conseguiste".
"""

from typing import List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.compra import Compra, CompraItem
from app.models.producto import Producto, producto_proveedor
from app.models.proveedor import Proveedor

ESTADOS_VALIDOS = ("recibida", "parcial")


def _consultar_historial(db: Session, producto_id: int) -> List[dict]:
    """Historial de compras del producto, de la mas reciente a la mas antigua."""
    filas = (
        db.query(CompraItem, Compra, Proveedor)
        .join(Compra, CompraItem.compra_id == Compra.id)
        .join(Proveedor, Compra.proveedor_id == Proveedor.id)
        .filter(
            CompraItem.producto_id == producto_id,
            Compra.estado.in_(ESTADOS_VALIDOS),
        )
        .order_by(Compra.fecha.desc(), Compra.id.desc())
        .all()
    )

    historial = []
    for item, compra, proveedor in filas:
        historial.append({
            "compra_id": compra.id,
            "numero": compra.numero,
            "fecha": compra.fecha.isoformat() if compra.fecha else None,
            "estado": compra.estado,
            "proveedor_id": proveedor.id,
            "proveedor_nombre": proveedor.nombre,
            "precio_unitario": float(item.precio_unitario or 0.0),
            "cantidad": float(item.cantidad or 0.0),
            "cantidad_recibida": float(item.cantidad_recibida or 0.0),
            "subtotal": float(item.subtotal or 0.0),
        })
    return historial


def _ultimo_por_proveedor(historial: List[dict]) -> dict:
    """Ultimo precio pagado a cada proveedor. El historial viene ordenado desc."""
    ultimo = {}
    for h in historial:
        ultimo.setdefault(h["proveedor_id"], h)
    return ultimo


def _consultar_proveedores(db: Session, producto_id: int) -> List[dict]:
    """Costo de lista actual por proveedor, con el ultimo precio pagado."""
    # select() con columnas explicitas: db.query(Entidad, tabla_core) aplana la
    # tabla Core a sus columnas y la fila deja de desempaquetarse en 2.
    filas = db.execute(
        select(
            Proveedor.id,
            Proveedor.nombre,
            producto_proveedor.c.costo,
            producto_proveedor.c.plazo_entrega_dias,
            producto_proveedor.c.es_principal,
        )
        .select_from(
            producto_proveedor.join(Proveedor, producto_proveedor.c.proveedor_id == Proveedor.id)
        )
        .where(
            producto_proveedor.c.producto_id == producto_id,
            producto_proveedor.c.activo == 1,
        )
        .order_by(producto_proveedor.c.es_principal.desc(), Proveedor.nombre)
    ).all()

    historial = _consultar_historial(db, producto_id)
    ultimo = _ultimo_por_proveedor(historial)

    proveedores = []
    for proveedor_id, nombre, costo, plazo, es_principal in filas:
        anterior = ultimo.get(proveedor_id)
        proveedores.append({
            "proveedor_id": proveedor_id,
            "nombre": nombre,
            "costo_actual": float(costo) if costo is not None else None,
            "plazo_entrega_dias": plazo,
            "es_principal": bool(es_principal),
            "ultimo_precio_pagado": anterior["precio_unitario"] if anterior else None,
            "ultima_fecha_pago": anterior["fecha"] if anterior else None,
        })
    return proveedores


def analizar_precios(db: Session, producto: Producto, precios_online: Optional[list] = None) -> dict:
    """Arma el analisis completo de un producto.

    precios_online es la salida de lookup_service.comparar_precios(). Se pasa
    desde el router para no acoplar este servicio al scraping.
    """
    historial = _consultar_historial(db, producto.id)
    proveedores = _consultar_proveedores(db, producto.id)

    precios = [p for p in (precios_online or []) if p.get("precio")]

    online = min(precios, key=lambda p: p["precio"]) if precios else None

    ultimo = historial[0] if historial else None
    mejor = min(historial, key=lambda h: h["precio_unitario"]) if historial else None

    # Costo mas bajo entre la lista de cada proveedor.
    costos = [p["costo_actual"] for p in proveedores if p["costo_actual"] is not None]
    mejor_oferta_proveedor = min(costos) if costos else None

    ahorro_vs_ultimo = _ahorro(online["precio"] if online else None, ultimo["precio_unitario"] if ultimo else None)
    ahorro_vs_historico = _ahorro(online["precio"] if online else None, mejor["precio_unitario"] if mejor else None)

    return {
        "producto": {
            "id": producto.id,
            "codigo_barras": producto.codigo_barras,
            "nombre": producto.nombre,
            "marca": producto.marca,
            "precio_venta": float(producto.precio_venta) if producto.precio_venta else None,
        },
        "precios_online": precios,
        "online": online,
        "historial": historial,
        "proveedores": proveedores,
        "ultimo_costo": ultimo,
        "mejor_historico": mejor,
        "mejor_oferta_proveedor": mejor_oferta_proveedor,
        "ahorro_vs_ultimo_costo": ahorro_vs_ultimo,
        "ahorro_vs_mejor_historico": ahorro_vs_historico,
        "margen_actual": _margen(producto.precio_venta, online["precio"] if online else None),
        "tiene_historico": bool(historial),
    }


def _ahorro(precio_online: Optional[float], referencia: Optional[float]) -> Optional[dict]:
    """Cuanto sale mas barato (o mas caro) comprar online hoy contra una referencia."""
    if precio_online is None or referencia is None:
        return None
    diferencia = float(referencia) - float(precio_online)
    if diferencia == 0:
        return None
    return {
        "referencia": float(referencia),
        "precio_online": float(precio_online),
        "diferencia": diferencia,
        "porcentaje": round(diferencia / float(referencia) * 100, 1) if referencia else None,
        "conviene_online": diferencia > 0,
    }


def _margen(precio_venta: Optional[float], precio_online: Optional[float]) -> Optional[dict]:
    """Margen de venta si se compra al precio online mas bajo."""
    if not precio_venta or precio_online is None:
        return None
    precio_venta = float(precio_venta)
    precio_online = float(precio_online)
    if precio_venta <= 0:
        return None
    utilidad = precio_venta - precio_online
    return {
        "precio_venta": precio_venta,
        "precio_costo": precio_online,
        "utilidad": round(utilidad, 2),
        "porcentaje": round(utilidad / precio_venta * 100, 1),
        "positivo": utilidad > 0,
    }
