"""Servicio de Productos: CRUD + lógica de negocio."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from app.models.producto import Producto
from app.models.categoria import Categoria
from app.models.lote import Lote


def _suma_lotes_activos(db: Session, producto_id: int) -> float:
    """Suma de cantidad_actual de los lotes activos de un producto."""
    total = (
        db.query(func.coalesce(func.sum(Lote.cantidad_actual), 0.0))
        .filter(Lote.producto_id == producto_id, Lote.activo == True)
        .scalar()
    )
    return float(total or 0)


def listar_productos(
    db: Session,
    search: Optional[str] = None,
    categoria_id: Optional[int] = None,
    solo_activos: bool = True,
    page: int = 1,
    page_size: int = 50,
) -> tuple[List[Producto], int]:
    """Lista productos con filtros y paginación."""
    query = db.query(Producto)

    if solo_activos:
        query = query.filter(Producto.activo == True)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Producto.nombre.ilike(like),
                Producto.codigo_barras.ilike(like),
                Producto.marca.ilike(like),
            )
        )

    if categoria_id:
        query = query.filter(Producto.categoria_id == categoria_id)

    total = query.count()
    productos = (
        query.order_by(Producto.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # El stock siempre es la suma de los lotes activos, nunca un dato editable.
    if productos:
        ids = [p.id for p in productos]
        sumas = dict(
            db.query(Lote.producto_id, func.sum(Lote.cantidad_actual))
            .filter(Lote.producto_id.in_(ids), Lote.activo == True)
            .group_by(Lote.producto_id)
            .all()
        )
        for p in productos:
            p.stock_actual = float(sumas.get(p.id, 0) or 0)

    return productos, total


def obtener_producto(db: Session, producto_id: int) -> Optional[Producto]:
    """Obtiene un producto por ID."""
    return db.query(Producto).filter(Producto.id == producto_id).first()


def obtener_por_barcode(db: Session, codigo_barras: str) -> Optional[Producto]:
    """Obtiene un producto por código de barras."""
    return (
        db.query(Producto)
        .filter(Producto.codigo_barras == codigo_barras)
        .first()
    )


def crear_producto(db: Session, data: dict) -> Producto:
    """Crea un producto nuevo con stock inicial."""
    cantidad_inicial = data.pop("cantidad_inicial", 0) or data.pop("stock_actual", 0) or 0

    if not data.get("codigo_barras"):
        existing = db.query(Producto).filter(
            Producto.codigo_barras.like("MAN-%")
        ).order_by(Producto.id.desc()).first()
        seq = 1
        if existing and existing.codigo_barras:
            try:
                seq = int(existing.codigo_barras.split("-")[1]) + 1
            except:
                pass
        data["codigo_barras"] = f"MAN-{seq:010d}"

    producto = Producto(**data)
    producto.stock_actual = cantidad_inicial
    db.add(producto)
    db.commit()
    db.refresh(producto)
    if cantidad_inicial > 0:
        from app.services import lote_service
        lote_service.crear_lote(
            db,
            producto_id=producto.id,
            codigo_lote="AJUSTE",
            cantidad=cantidad_inicial,
            notas="Stock inicial de alta",
        )
    return producto


def actualizar_producto(db: Session, producto: Producto, data: dict) -> Producto:
    """Actualiza campos de un producto existente.

    El stock NO se edita aquí: es siempre la suma de los lotes activos.
    Se ignora cualquier `stock_actual` enviado y se recalcula desde lotes.
    """
    updatable = [
        "nombre", "marca", "descripcion", "codigo_barras", "precio_referencia", "precio_costo",
        "precio_venta", "precio_etiqueta", "imagen_url", "sku", "propiedades", "fuente",
        "categoria_id", "stock_minimo", "observaciones", "fecha_vencimiento",
        "tipo_venta", "precio_por_kilo", "precio_por_unidad",
    ]
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(producto, field, data[field])

    if "activo" in data:
        producto.activo = data["activo"]

    producto.stock_actual = _suma_lotes_activos(db, producto.id)

    db.commit()
    db.refresh(producto)
    return producto


def guardar_desde_lookup(db: Session, data: dict) -> Producto:
    """Guarda un producto desde los datos del lookup (crea o actualiza).

    Si ya existe un producto con ese código de barras, lo actualiza.
    Si no, lo crea. La cantidad va a un lote AJUSTE; el stock cache
    queda sincronizado con los lotes.
    """
    from app.services import lote_service

    cantidad = float(data.get("cantidad") or 0)

    existente = obtener_por_barcode(db, data["codigo_barras"])
    if existente:
        updatable = [
            "nombre", "marca", "descripcion", "precio_referencia",
            "imagen_url", "sku", "propiedades", "fuente",
        ]
        for field in updatable:
            if field in data and data[field]:
                setattr(existente, field, data[field])
        if data.get("precio_venta") is not None:
            existente.precio_venta = data["precio_venta"]
        if data.get("categoria"):
            cat = _obtener_o_crear_categoria(db, data["categoria"])
            existente.categoria_id = cat.id
        db.commit()
        db.refresh(existente)
        if cantidad > 0:
            lote_service.crear_lote(
                db, producto_id=existente.id, codigo_lote="AJUSTE",
                cantidad=cantidad, notas="Stock desde lookup",
            )
        existente.stock_actual = _suma_lotes_activos(db, existente.id)
        return existente
    else:
        cat_id = None
        if data.get("categoria"):
            cat = _obtener_o_crear_categoria(db, data["categoria"])
            cat_id = cat.id
        producto = Producto(
            codigo_barras=data["codigo_barras"],
            nombre=data.get("nombre", ""),
            marca=data.get("marca"),
            descripcion=data.get("descripcion"),
            precio_referencia=data.get("precio_referencia"),
            precio_venta=data.get("precio_venta"),
            imagen_url=data.get("imagen_url"),
            sku=data.get("sku"),
            propiedades=data.get("propiedades"),
            fuente=data.get("fuente", "manual"),
            categoria_id=cat_id,
            stock_actual=0,
        )
        db.add(producto)
        db.commit()
        db.refresh(producto)
        if cantidad > 0:
            lote_service.crear_lote(
                db, producto_id=producto.id, codigo_lote="AJUSTE",
                cantidad=cantidad, notas="Stock desde lookup",
            )
        producto.stock_actual = _suma_lotes_activos(db, producto.id)
        return producto


def _obtener_o_crear_categoria(db: Session, nombre: str) -> Categoria:
    """Busca una categoría por nombre o la crea si no existe."""
    cat = db.query(Categoria).filter(Categoria.nombre == nombre).first()
    if not cat:
        cat = Categoria(nombre=nombre)
        db.add(cat)
        db.commit()
        db.refresh(cat)
    return cat
