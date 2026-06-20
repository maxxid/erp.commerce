"""Router de Productos: CRUD, lookup por código de barras."""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.producto import (
    ProductoCreate, ProductoUpdate, ProductoOut,
    ProductoLookupRequest, ProductoLookupResponse,
)
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.services import producto_service
from app.services import lookup_service as lk
from app.services import stock_service
from app.services import catalogo_service

router = APIRouter(prefix="/api/productos", tags=["Productos"])


@router.get("", response_model=RespuestaLista[ProductoOut])
def listar(
    search: Optional[str] = Query(None),
    categoria_id: Optional[int] = Query(None),
    solo_activos: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista productos con filtros y paginación."""
    productos, total = producto_service.listar_productos(
        db, search=search, categoria_id=categoria_id,
        solo_activos=solo_activos, page=page, page_size=page_size,
    )
    return RespuestaLista(
        data=productos, total=total, page=page, page_size=page_size,
        message=f"{total} producto(s)"
    )


@router.get("/pendientes-etiquetar", response_model=RespuestaLista)
def pendientes_etiquetar(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Productos cuyo precio_venta cambió y necesitan re-etiquetado."""
    productos = (
        db.query(Producto)
        .filter(
            Producto.activo == True,
            Producto.precio_venta.isnot(None),
            (Producto.precio_etiqueta.is_(None)) | (Producto.precio_etiqueta != Producto.precio_venta),
        )
        .all()
    )
    data = [
        {
            "id": p.id, "nombre": p.nombre, "codigo_barras": p.codigo_barras,
            "precio_venta": p.precio_venta, "precio_etiqueta": p.precio_etiqueta,
        }
        for p in productos
    ]
    return RespuestaLista(data=data, total=len(data), message=f"{len(data)} producto(s) necesitan etiquetado")


class MarcarEtiquetadoRequest(BaseModel):
    productos_ids: list[int]


@router.post("/marcar-etiquetado", response_model=RespuestaData)
def marcar_etiquetado(
    data: MarcarEtiquetadoRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Marca productos como etiquetados (precio_etiqueta = precio_venta)."""
    count = 0
    for pid in data.productos_ids:
        p = db.query(Producto).filter(Producto.id == pid).first()
        if p:
            p.precio_etiqueta = p.precio_venta
            count += 1
    db.commit()
    return RespuestaData(data={"marcados": count}, message=f"{count} producto(s) marcados como etiquetados")


@router.get("/{producto_id}", response_model=RespuestaData[ProductoOut])
def obtener(
    producto_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene un producto por ID."""
    producto = producto_service.obtener_producto(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return RespuestaData(data=producto)


@router.post("", response_model=RespuestaData[ProductoOut])
def crear(
    data: ProductoCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Crea un producto manualmente."""
    existente = producto_service.obtener_por_barcode(db, data.codigo_barras)
    if existente:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe un producto con código {data.codigo_barras}"
        )
    producto = producto_service.crear_producto(db, data.model_dump())
    return RespuestaData(data=producto, message="Producto creado")


@router.put("/{producto_id}", response_model=RespuestaData[ProductoOut])
def actualizar(
    producto_id: int,
    data: ProductoUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Actualiza un producto existente."""
    producto = producto_service.obtener_producto(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto = producto_service.actualizar_producto(
        db, producto, data.model_dump(exclude_unset=True)
    )
    return RespuestaData(data=producto, message="Producto actualizado")


@router.delete("/{producto_id}", response_model=RespuestaData)
def desactivar(
    producto_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Desactiva un producto (soft delete)."""
    producto = producto_service.obtener_producto(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto_service.actualizar_producto(db, producto, {"activo": False})
    return RespuestaData(message="Producto desactivado")


@router.post("/lookup", response_model=RespuestaData[ProductoLookupResponse])
def lookup(
    data: ProductoLookupRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Busca un producto por código de barras en fuentes externas.

    Primero busca en la base local, luego en el catálogo central
    (catalogo_completo.json), y finalmente en fuentes externas.
    """
    barcode = data.barcode.strip()

    local = producto_service.obtener_por_barcode(db, barcode)
    if local:
        result = ProductoLookupResponse(
            codigo_barras=local.codigo_barras,
            nombre=local.nombre,
            marca=local.marca,
            descripcion=local.descripcion,
            precio_referencia=local.precio_referencia,
            imagen_url=local.imagen_url,
            sku=local.sku,
            propiedades=local.propiedades,
            fuente=local.fuente,
            categoria=local.categoria.nombre if local.categoria else None,
            _cached=True,
            ia_mode=data.ia_mode,
        )
        return RespuestaData(data=result, message="Encontrado en base local")

    # Buscar en catálogo central (catalogo_completo.json)
    cat = catalogo_service.buscar_en_catalogo(barcode)
    if cat:
        result = ProductoLookupResponse(
            codigo_barras=barcode,
            nombre=cat.get("nombre", ""),
            marca=cat.get("marca", ""),
            descripcion=cat.get("descripcion", ""),
            precio_referencia=cat.get("precio_referencia"),
            imagen_url=cat.get("imagen_url", ""),
            sku=cat.get("sku", ""),
            propiedades=cat.get("propiedades"),
            fuente="catalogo_central",
            categoria=cat.get("categoria_nombre", ""),
            ia_mode=data.ia_mode,
        )
        return RespuestaData(data=result, message="Encontrado en catálogo central")

    producto = lk.lookup_producto(barcode, fuente=data.fuente)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")

    precios = lk.comparar_precios(barcode)
    result = ProductoLookupResponse(
        codigo_barras=producto["codigo_barras"],
        nombre=producto["nombre"],
        marca=producto.get("marca"),
        descripcion=producto.get("descripcion"),
        precio_referencia=producto.get("precio_referencia"),
        imagen_url=producto.get("imagen_url"),
        sku=producto.get("sku"),
        propiedades=producto.get("propiedades"),
        fuente=producto.get("fuente"),
        url=producto.get("url"),
        descuento=producto.get("descuento"),
        categoria=producto.get("categoria"),
        comparacion=precios,
        ia_mode=data.ia_mode,
    )
    return RespuestaData(data=result, message="Producto encontrado")


class AjustarStockRequest(BaseModel):
    cantidad: float = Field(...)
    notas: Optional[str] = None


@router.put("/{producto_id}/ajustar-stock", response_model=RespuestaData)
def ajustar_stock(
    producto_id: int,
    data: AjustarStockRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Ajusta el stock de un producto (entrada o salida manual)."""
    producto = producto_service.obtener_producto(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    tipo = "entrada" if data.cantidad > 0 else "salida"
    try:
        mov = stock_service.ajustar_stock(
            db, producto_id, data.cantidad, tipo, user.id,
            referencia_tipo="ajuste_manual",
            notas=data.notas,
        )
        return RespuestaData(
            data={"stock_anterior": mov.stock_anterior, "stock_resultante": mov.stock_resultante},
            message=f"Stock ajustado: {mov.stock_anterior} → {mov.stock_resultante}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{producto_id}/proveedores", response_model=RespuestaData)
def listar_proveedores_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista los proveedores asignados a un producto."""
    producto = producto_service.obtener_producto(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    provs = [{"id": p.id, "nombre": p.nombre, "cuit": p.cuit} for p in producto.proveedores]
    return RespuestaData(data=provs)


@router.post("/{producto_id}/proveedores", response_model=RespuestaData)
def asignar_proveedor(
    producto_id: int,
    data: dict,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Asigna un proveedor al producto."""
    producto = producto_service.obtener_producto(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    from app.models.proveedor import Proveedor
    proveedor_id = data.get("proveedor_id")
    prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if prov not in producto.proveedores:
        producto.proveedores.append(prov)
        db.commit()
    return RespuestaData(message=f"Proveedor '{prov.nombre}' asignado")


@router.delete("/{producto_id}/proveedores/{proveedor_id}", response_model=RespuestaData)
def quitar_proveedor(
    producto_id: int,
    proveedor_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Quita un proveedor del producto."""
    producto = producto_service.obtener_producto(db, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    from app.models.proveedor import Proveedor
    prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if prov and prov in producto.proveedores:
        producto.proveedores.remove(prov)
        db.commit()
    return RespuestaData(message="Proveedor quitado")


@router.get("/costos", response_model=RespuestaLista)
def costos(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista productos con su último precio de compra y margen actual."""
    from app.models.compra import Compra, CompraItem
    from app.models.proveedor import Proveedor
    from sqlalchemy import desc

    query = db.query(
        Producto.id, Producto.nombre, Producto.precio_venta, Producto.precio_costo,
        Producto.codigo_barras,
        func.coalesce(
            db.query(CompraItem.precio_unitario)
            .join(Compra, CompraItem.compra_id == Compra.id)
            .filter(CompraItem.producto_id == Producto.id, Compra.estado == "recibida")
            .order_by(desc(Compra.fecha))
            .limit(1).correlate(Producto).scalar_subquery(), 0
        ).label("ultimo_costo"),
        db.query(Compra.fecha)
            .join(CompraItem, CompraItem.compra_id == Compra.id)
            .filter(CompraItem.producto_id == Producto.id, Compra.estado == "recibida")
            .order_by(desc(Compra.fecha))
            .limit(1).correlate(Producto).scalar_subquery().label("ultima_compra"),
        db.query(Proveedor.nombre)
            .join(Compra, Compra.proveedor_id == Proveedor.id)
            .join(CompraItem, CompraItem.compra_id == Compra.id)
            .filter(CompraItem.producto_id == Producto.id, Compra.estado == "recibida")
            .order_by(desc(Compra.fecha))
            .limit(1).correlate(Producto).scalar_subquery().label("proveedor"),
    ).filter(Producto.activo == True)

    if search:
        query = query.filter(Producto.nombre.ilike(f"%{search}%"))

    rows = query.order_by(Producto.nombre).limit(200).all()

    data = []
    for r in rows:
        costo = float(r.ultimo_costo or 0)
        venta = float(r.precio_venta or 0)
        margen = venta - costo
        pct = round((margen / venta * 100), 1) if venta > 0 else 0
        data.append({
            "id": r.id, "nombre": r.nombre, "codigo_barras": r.codigo_barras,
            "precio_venta": venta, "ultimo_costo": costo,
            "margen": margen, "margen_pct": pct,
            "ultima_compra": r.ultima_compra.isoformat() if r.ultima_compra else None,
            "proveedor": r.proveedor or "",
        })

    return RespuestaLista(data=data, total=len(data), message=f"{len(data)} producto(s)")
