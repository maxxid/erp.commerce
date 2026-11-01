"""Servicio para etiquetas de precios."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.sector import Sector
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
    
    # desde/hasta llegan como dates (medianoche). Un producto tocado el día
    # "hasta" (casi siempre "hoy") tiene updated_at con hora y quedaba fuera de
    # between(): se usa el día siguiente como bound superior exclusivo.
    hasta_excl = filtros.hasta + timedelta(days=1)
    
    if filtros.incluir_cambios_precio:
        condiciones.append(
            and_(
                or_(
                    Producto.precio_etiqueta.is_(None),
                    Producto.precio_etiqueta != Producto.precio_venta
                ),
                Producto.updated_at >= filtros.desde,
                Producto.updated_at < hasta_excl
            )
        )
    
    if filtros.incluir_nuevos:
        condiciones.append(
            and_(
                Producto.created_at >= filtros.desde,
                Producto.created_at < hasta_excl
            )
        )
    
    if condiciones:
        query = query.filter(or_(*condiciones))
    
    if filtros.solo_con_stock:
        query = query.filter(Producto.stock_actual > 0)
    
    # Filtro por categoría
    if filtros.categoria_id:
        query = query.filter(Producto.categoria_id == filtros.categoria_id)

    # Filtro por sector (dónde se pega la etiqueta)
    if filtros.sector_id:
        query = query.filter(Producto.sector_id == filtros.sector_id)

    query = query.outerjoin(Categoria, Producto.categoria_id == Categoria.id)
    query = query.outerjoin(Sector, Producto.sector_id == Sector.id)

    # Ordenamiento
    if filtros.orden == 'fecha_desc':
        query = query.order_by(Producto.created_at.desc())
    elif filtros.orden == 'fecha_asc':
        query = query.order_by(Producto.created_at.asc())
    elif filtros.orden == 'nombre':
        query = query.order_by(Producto.nombre.asc())
    elif filtros.orden == 'precio_asc':
        query = query.order_by(Producto.precio_venta.asc().nullslast(), Producto.nombre.asc())
    elif filtros.orden == 'precio_desc':
        query = query.order_by(Producto.precio_venta.desc().nullslast(), Producto.nombre.asc())
    elif filtros.orden == 'sector':
        # Agrupa por dónde va colocada la etiqueta: sector, después nombre.
        query = query.order_by(
            Sector.orden.asc().nullslast(),
            Sector.nombre.asc().nullslast(),
            Producto.nombre.asc(),
        )
    elif filtros.orden == 'categoria':
        query = query.order_by(Categoria.nombre.asc().nullslast(), Producto.nombre.asc())
    else:
        query = query.order_by(Categoria.nombre.asc().nullslast(), Producto.nombre.asc())
    
    # Desempate estable: la pantalla pide por páginas y sin esto un empate de
    # fecha/precio podía repetir o saltear productos entre página y página.
    return query.order_by(Producto.id.asc()).all()


@dataclass
class FilaEtiqueta:
    """Una etiqueta a imprimir: un producto suelto o un grupo de variantes.

    Expone los mismos atributos que usa el PDF de un Producto, así que se puede
    dibujar directamente. En los grupos `id` es el del representante.
    """
    id: int
    codigo_barras: str
    nombre: str
    marca: Optional[str]
    descripcion: Optional[str]
    precio_venta: float
    precio_etiqueta: Optional[float]
    tipo_venta: str
    precio_por_kilo: Optional[float]
    categoria_id: Optional[int]
    categoria_nombre: Optional[str]
    sector_id: Optional[int]
    sector_nombre: Optional[str]
    stock_actual: float
    motivo: str
    es_grupo: bool = False
    grupo: Optional[str] = None
    ids: List[int] = field(default_factory=list)
    variantes: List[dict] = field(default_factory=list)
    precios_distintos: bool = False
    sectores_distintos: bool = False


def _igual(a, b) -> bool:
    return abs(float(a or 0) - float(b or 0)) < 0.005


def _clave_grupo(p: Producto) -> Optional[str]:
    g = (p.grupo_etiqueta or "").strip().lower()
    return g if g and not p.etiqueta_propia else None


def _motivo(p: Producto, filtros) -> str:
    es_nuevo = bool(p.created_at and filtros.desde <= p.created_at.date() <= filtros.hasta)
    es_cambio = bool(
        (p.precio_etiqueta is None or p.precio_etiqueta != p.precio_venta)
        and p.updated_at and filtros.desde <= p.updated_at.date() <= filtros.hasta
    )
    if es_nuevo and es_cambio:
        return 'ambos'
    if es_nuevo:
        return 'nuevo'
    return 'cambio_precio'


def _fila_individual(p: Producto, filtros) -> FilaEtiqueta:
    return FilaEtiqueta(
        id=p.id,
        codigo_barras=p.codigo_barras,
        nombre=p.nombre,
        marca=p.marca,
        descripcion=p.descripcion,
        precio_venta=float(p.precio_venta or 0),
        precio_etiqueta=float(p.precio_etiqueta) if p.precio_etiqueta else None,
        tipo_venta=p.tipo_venta,
        precio_por_kilo=float(p.precio_por_kilo) if p.precio_por_kilo else None,
        categoria_id=p.categoria_id,
        categoria_nombre=p.categoria.nombre if p.categoria else None,
        sector_id=p.sector_id,
        sector_nombre=p.sector.nombre if p.sector else None,
        stock_actual=float(p.stock_actual or 0),
        motivo=_motivo(p, filtros),
        grupo=(p.grupo_etiqueta or '').strip() or None,
        ids=[p.id],
    )


def _cubierto(p: Producto, miembros: List[Producto]) -> bool:
    """True si otra variante del grupo ya tiene impresa una etiqueta con el precio de p."""
    return any(
        q.id != p.id
        and q.precio_etiqueta is not None
        and _igual(q.precio_etiqueta, p.precio_venta)
        and _igual(q.precio_venta, p.precio_venta)
        for q in miembros
    )


def _fila_grupo(restantes: List[Producto], miembros: List[Producto], filtros) -> FilaEtiqueta:
    precio = Counter(round(float(p.precio_venta), 2) for p in restantes).most_common(1)[0][0]
    rep = next(p for p in restantes if _igual(p.precio_venta, precio))
    cubiertos = [m for m in miembros if _igual(m.precio_venta, precio)]
    pendientes_ids = {p.id for p in restantes}
    marcas = {(m.marca or "").strip().lower() for m in miembros}
    motivos = {_motivo(p, filtros) for p in restantes}
    if 'ambos' in motivos or motivos == {'nuevo', 'cambio_precio'}:
        motivo = 'ambos'
    elif motivos == {'nuevo'}:
        motivo = 'nuevo'
    else:
        motivo = 'cambio_precio'
    nombre = (rep.grupo_etiqueta or "").strip()

    return FilaEtiqueta(
        id=rep.id,
        codigo_barras=rep.codigo_barras,
        nombre=nombre,
        marca=rep.marca if len(marcas) == 1 and (rep.marca or "").strip() else None,
        descripcion=nombre,
        precio_venta=float(precio),
        precio_etiqueta=float(rep.precio_etiqueta) if rep.precio_etiqueta else None,
        tipo_venta="unidad",
        precio_por_kilo=None,
        categoria_id=rep.categoria_id,
        categoria_nombre=rep.categoria.nombre if rep.categoria else None,
        sector_id=rep.sector_id,
        sector_nombre=rep.sector.nombre if rep.sector else None,
        stock_actual=float(sum((m.stock_actual or 0) for m in cubiertos)),
        motivo=motivo,
        es_grupo=True,
        grupo=nombre,
        ids=[m.id for m in cubiertos],
        variantes=[
            {
                "id": m.id,
                "nombre": m.nombre,
                "codigo_barras": m.codigo_barras,
                "precio_venta": float(m.precio_venta or 0),
                "precio_etiqueta": float(m.precio_etiqueta) if m.precio_etiqueta else None,
                "stock_actual": float(m.stock_actual or 0),
                "pendiente": m.id in pendientes_ids,
                "distinto": not _igual(m.precio_venta, precio),
            }
            for m in sorted(miembros, key=lambda x: (x.nombre or "").lower())
        ],
        precios_distintos=len({round(float(m.precio_venta), 2) for m in miembros}) > 1,
        sectores_distintos=len({m.sector_id for m in miembros}) > 1,
    )


def construir_filas_etiquetas(db: Session, filtros: "EtiquetasFiltros") -> List[FilaEtiqueta]:
    """Arma las etiquetas a imprimir: variantes de un grupo salen en una sola fila.

    Una variante pendiente no genera etiqueta si otra del mismo grupo ya la tiene
    impresa con ese mismo precio (se agregó un sabor nuevo a un grupo ya etiquetado).
    """
    pendientes = obtener_productos_para_etiquetar(db, filtros)
    if not filtros.agrupar:
        return [_fila_individual(p, filtros) for p in pendientes]

    pend_por_clave: dict = {}
    for p in pendientes:
        clave = _clave_grupo(p)
        if clave:
            pend_por_clave.setdefault(clave, []).append(p)

    miembros_por_clave: dict = {}
    if pend_por_clave:
        activos = db.query(Producto).filter(
            Producto.activo == True,
            Producto.etiqueta_propia == False,
            Producto.grupo_etiqueta.isnot(None),
            Producto.precio_venta.isnot(None),
        ).all()
        for m in activos:
            clave = _clave_grupo(m)
            if clave in pend_por_clave:
                miembros_por_clave.setdefault(clave, []).append(m)

    filas: List[FilaEtiqueta] = []
    vistos = set()
    for p in pendientes:
        clave = _clave_grupo(p)
        if not clave:
            filas.append(_fila_individual(p, filtros))
            continue
        if clave in vistos:
            continue
        vistos.add(clave)
        miembros = miembros_por_clave.get(clave) or pend_por_clave[clave]
        restantes = [x for x in pend_por_clave[clave] if not _cubierto(x, miembros)]
        if restantes:
            filas.append(_fila_grupo(restantes, miembros, filtros))
    return filas


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