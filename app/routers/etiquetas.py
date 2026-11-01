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
    construir_filas_etiquetas, verificar_stock_cero,
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
    sector_id: Optional[int] = Query(None),
    orden: str = Query('fecha_desc', pattern='^(fecha_desc|fecha_asc|nombre|categoria|sector|precio_asc|precio_desc)$'),
    agrupar: bool = Query(True),
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
        sector_id=sector_id,
        orden=orden,
        agrupar=agrupar,
    )

    filas = construir_filas_etiquetas(db, filtros)

    total = len(filas)
    start = (page - 1) * page_size
    end = start + page_size

    data = [
        EtiquetaProductoOut(**{k: getattr(f, k) for k in EtiquetaProductoOut.model_fields})
        for f in filas[start:end]
    ]

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
    # data.filtros ya es un EtiquetasFiltros: reconstruirlo campo por campo
    # hacía que cualquier filtro nuevo se perdiera silenciosamente acá.
    filtros = data.filtros

    productos = construir_filas_etiquetas(db, filtros)

    if data.productos_ids is not None:
        elegidos = set(data.productos_ids)
        productos = [f for f in productos if f.id in elegidos]

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
        descripciones_editadas=data.descripciones_editadas,
        modelo=data.modelo,
    )
    
    sufijo_modelo = f"-{data.modelo}" if data.modelo != "completa" else ""
    filename = f"etiquetas-{data.filtros.desde}-a-{data.filtros.hasta}-{data.tamano}{sufijo_modelo}.pdf"
    
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