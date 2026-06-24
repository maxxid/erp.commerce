"""Servicio de Productos: CRUD + lógica de negocio."""

from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.models.producto import Producto
from app.models.categoria import Categoria


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

    producto = Producto(**data)
    producto.stock_actual = cantidad_inicial
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return producto


def actualizar_producto(db: Session, producto: Producto, data: dict) -> Producto:
    """Actualiza campos de un producto existente.

    Si viene stock_actual, lo maneja via stock_service.ajustar_stock()
    para generar MovimientoStock. Requiere usuario_id en data.
    """
    from app.services import stock_service

    updatable = [
        "nombre", "marca", "descripcion", "precio_referencia", "precio_costo",
        "precio_venta", "imagen_url", "sku", "propiedades", "fuente",
        "categoria_id", "stock_minimo", "observaciones", "fecha_vencimiento",
    ]
    for field in updatable:
        if field in data and data[field] is not None:
            setattr(producto, field, data[field])

    if "stock_actual" in data and data["stock_actual"] is not None:
        nuevo_stock = data["stock_actual"]
        usuario_id = data.get("usuario_id")
        diff = nuevo_stock - producto.stock_actual
        if diff != 0 and usuario_id:
            tipo = "entrada" if diff > 0 else "salida"
            notas = data.get("notas")
            stock_service.ajustar_stock(
                db, producto.id, diff, tipo, usuario_id,
                referencia_tipo="ajuste_manual",
                notas=notas,
            )

    if "activo" in data:
        producto.activo = data["activo"]

    db.commit()
    db.refresh(producto)
    return producto


def guardar_desde_lookup(db: Session, data: dict) -> Producto:
    """Guarda un producto desde los datos del lookup (crea o actualiza).

    Si ya existe un producto con ese código de barras, lo actualiza.
    Si no, lo crea.
    """
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
        existente.stock_actual = data.get("cantidad", existente.stock_actual)
        db.commit()
        db.refresh(existente)
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
            stock_actual=data.get("cantidad", 0),
        )
        db.add(producto)
        db.commit()
        db.refresh(producto)
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
