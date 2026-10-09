"""Router para Etiquetas de Precios."""

from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.usuario import Usuario
from app.models.producto import Producto
from app.schemas.etiquetas import (
    EtiquetasFiltros, EtiquetaProductoOut, GenerarPDFRequest,
    HistorialImpresionOut, MarcarImpresoRequest
)
from app.schemas.common import RespuestaLista, RespuestaData
from app.services.etiquetas_service import (
    obtener_productos_para_etiquetar, verificar_stock_cero,
    obtener_historial, guardar_historial, marcar_como_impreso
)
from app.services.etiquetas_pdf import generar_etiquetas_pdf
from app.services import auditoria_service


router = APIRouter(prefix="/api/etiquetas", tags=["Etiquetas"])


@router.get("/precios", response_model=RespuestaLista[EtiquetaProductoOut])
def listar_para_etiquetar(
    desde: date = Query(...),
    hasta: date = Query(...),
    incluir_cambios_precio: bool = Query(True),
    incluir_nuevos: bool = Query(True),
    solo_con_stock: bool = Query(False),
    categoria_id: Optional[int] = Query(None),
    orden: str = Query('fecha_desc', pattern='^(fecha_desc|fecha_asc|nombre|categoria)$'),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista productos que necesitan etiquetado según filtros de fecha."""
    filtros = EtiquetasFiltros(
        desde=desde,
        hasta=hasta,
        incluir_cambios_precio=incluir_cambios_precio,
        incluir_nuevos=incluir_nuevos,
        solo_con_stock=solo_con_stock,
        categoria_id=categoria_id,
        orden=orden,
    )
    
    productos = obtener_productos_para_etiquetar(db, filtros)
    
    total = len(productos)
    start = (page - 1) * page_size
    end = start + page_size
    productos_paginados = productos[start:end]
    
    data = []
    for p in productos_paginados:
        data.append(EtiquetaProductoOut(
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
            stock_actual=float(p.stock_actual or 0),
        ))
    
    return RespuestaLista(
        data=data, total=total, page=page, page_size=page_size,
        message=f"{total} producto(s) para etiquetar"
    )


@router.post("/precios/generar-pdf")
def generar_pdf_etiquetas(
    data: GenerarPDFRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Genera PDF con etiquetas de precios."""
    from app.schemas.etiquetas import EtiquetasFiltros
    
    # Crear filtros con todos los parámetros incluyendo categoria_id y orden
    filtros = EtiquetasFiltros(
        desde=data.filtros.desde,
        hasta=data.filtros.hasta,
        incluir_cambios_precio=data.filtros.incluir_cambios_precio,
        incluir_nuevos=data.filtros.incluir_nuevos,
        solo_con_stock=data.filtros.solo_con_stock,
        categoria_id=data.filtros.categoria_id,
        orden=data.filtros.orden,
    )
    
    productos = obtener_productos_para_etiquetar(db, filtros)
    
    if not productos:
        raise HTTPException(status_code=404, detail="No hay productos para etiquetar en ese período")
    
    sin_stock = verificar_stock_cero(productos)
    if sin_stock and not data.filtros.solo_con_stock and not data.forzar:
        raise HTTPException(
            status_code=409,
            detail={
                "mensaje": f"{len(sin_stock)} producto(s) tienen stock 0 o negativo",
                "productos": [{"id": p.id, "nombre": p.nombre, "stock": p.stock_actual} for p in sin_stock],
                "codigo": "STOCK_CERO"
            }
        )
    
    pdf_bytes = generar_etiquetas_pdf(
        productos=productos,
        tamano=data.tamano,
        borderless=data.borderless,
        descripciones_editadas=data.descripciones_editadas
    )
    
    filename = f"etiquetas-{data.filtros.desde}-a-{data.filtros.hasta}-{data.tamano}.pdf"
    
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/historial", response_model=RespuestaLista[HistorialImpresionOut])
def obtener_historial_impresiones(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene las últimas 5 impresiones de etiquetas."""
    historial = obtener_historial(db)
    
    data = []
    for h in historial:
        data.append(HistorialImpresionOut(
            desde=date.fromisoformat(h["desde"]),
            hasta=date.fromisoformat(h["hasta"]),
            fecha_impresion=__import__("datetime").datetime.fromisoformat(h["fecha_impresion"]),
            total_etiquetas=h["total_etiquetas"],
            tamano=h["tamano"],
            borderless=h["borderless"],
        ))
    
    return RespuestaLista(data=data, total=len(data), message=f"{len(data)} impresión(es) en historial")


class MarcarImpresoResponse(BaseModel):
    marcados: int


@router.post("/marcar-impreso", response_model=RespuestaData[MarcarImpresoResponse])
def marcar_etiquetado(
    data: MarcarImpresoRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Marca productos como etiquetados (precio_etiqueta = precio_venta) y guarda en historial."""
    if not data.productos_ids:
        raise HTTPException(status_code=400, detail="No hay productos para marcar")
    
    marcados = marcar_como_impreso(db, data.productos_ids)
    
    if marcados > 0:
        desde = min(
            db.query(Producto.created_at)
            .filter(Producto.id.in_(data.productos_ids))
            .all()
        )[0].date()
        hasta = max(
            db.query(Producto.updated_at)
            .filter(Producto.id.in_(data.productos_ids))
            .all()
        )[0].date()
        
        guardar_historial(
            db, user.id, desde, hasta, marcados,
            data.tamano, data.borderless
        )
        
        auditoria_service.registrar(
            db, user.id, "etiquetas_impresas", None, None,
            {"productos_ids": data.productos_ids, "total": marcados, "tamano": data.tamano}
        )
    
    return RespuestaData(
        data=MarcarImpresoResponse(marcados=marcados),
        message=f"{marcados} producto(s) marcados como etiquetados"
    )