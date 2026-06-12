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
from app.services import producto_service
from app.services import lookup_service as lk
from app.services import stock_service

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

    Primero busca en la base local. Si no existe, busca en:
    Carrefour → Vea → Masonline.
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
