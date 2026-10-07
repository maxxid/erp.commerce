"""Servicio para etiquetas de precios."""

from datetime import date, datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.configuracion import Configuracion
import json


HISTORIAL_KEY = "historial_etiquetas"
MAX_HISTORIAL = 5


def obtener_productos_para_etiquetar(
    db: Session,
    filtros: "EtiquetasFiltros"
) -> List[Producto]:
    """Obtiene productos que necesitan etiquetado según filtros."""
    from app.schemas.etiquetas import EtiquetasFiltros
    
    query = db.query(Producto).filter(
        Producto.activo == True,
        Producto.precio_venta.isnot(None)
    )
    
    condiciones = []
    
    if filtros.incluir_cambios_precio:
        condiciones.append(
            and_(
                or_(
                    Producto.precio_etiqueta.is_(None),
                    Producto.precio_etiqueta != Producto.precio_venta
                ),
                Producto.updated_at.between(filtros.desde, filtros.hasta)
            )
        )
    
    if filtros.incluir_nuevos:
        condiciones.append(
            Producto.created_at.between(filtros.desde, filtros.hasta)
        )
    
    if condiciones:
        query = query.filter(or_(*condiciones))
    
    if filtros.solo_con_stock:
        query = query.filter(Producto.stock_actual > 0)
    
    # Filtro por categoría
    if filtros.categoria_id:
        query = query.filter(Producto.categoria_id == filtros.categoria_id)
    
    query = query.outerjoin(Categoria, Producto.categoria_id == Categoria.id)
    
    # Ordenamiento
    if filtros.orden == 'fecha_desc':
        query = query.order_by(Producto.created_at.desc())
    elif filtros.orden == 'fecha_asc':
        query = query.order_by(Producto.created_at.asc())
    elif filtros.orden == 'nombre':
        query = query.order_by(Producto.nombre.asc())
    elif filtros.orden == 'categoria':
        query = query.order_by(Categoria.nombre.asc().nullslast(), Producto.nombre.asc())
    else:
        query = query.order_by(Categoria.nombre.asc().nullslast(), Producto.nombre.asc())
    
    return query.all()


def verificar_stock_cero(productos: List[Producto]) -> List[Producto]:
    """Devuelve productos con stock cero o negativo."""
    return [p for p in productos if (p.stock_actual or 0) <= 0]


def obtener_historial(db: Session) -> List[dict]:
    """Obtiene el historial de impresiones (últimas 5)."""
    config = db.query(Configuracion).filter(Configuracion.clave == HISTORIAL_KEY).first()
    if not config or not config.valor_texto:
        return []
    try:
        return json.loads(config.valor_texto)
    except json.JSONDecodeError:
        return []


def guardar_historial(
    db: Session,
    user_id: int,
    desde: date,
    hasta: date,
    total: int,
    tamano: str,
    borderless: bool
) -> None:
    """Guarda una nueva entrada en el historial (máx 5)."""
    historial = obtener_historial(db)
    
    nueva_entrada = {
        "desde": desde.isoformat(),
        "hasta": hasta.isoformat(),
        "fecha_impresion": datetime.now(timezone.utc).isoformat(),
        "total_etiquetas": total,
        "tamano": tamano,
        "borderless": borderless,
        "usuario_id": user_id,
    }
    
    historial.insert(0, nueva_entrada)
    historial = historial[:MAX_HISTORIAL]
    
    config = db.query(Configuracion).filter(Configuracion.clave == HISTORIAL_KEY).first()
    if not config:
        config = Configuracion(clave=HISTORIAL_KEY, valor="[]", valor_texto="[]")
        db.add(config)
    
    config.valor = str(total)
    config.valor_texto = json.dumps(historial, ensure_ascii=False)
    db.commit()


def marcar_como_impreso(db: Session, productos_ids: List[int]) -> int:
    """Actualiza precio_etiqueta = precio_venta para los productos dados."""
    count = 0
    for pid in productos_ids:
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p and p.precio_venta is not None:
            p.precio_etiqueta = p.precio_venta
            count += 1
    db.commit()
    return count