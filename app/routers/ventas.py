"""Router de Ventas: crear, items, confirmar, anular, listar."""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services import venta_service
from app.services import auditoria_service
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.venta import Venta

router = APIRouter(prefix="/api/ventas", tags=["Ventas"])

# Los filtros de fecha llegan como día argentino (YYYY-MM-DD) y la base guarda
# UTC: el día argentino corre de 00:00 a 03:00 UTC, así que un mismo día local
# cae en dos días UTC distintos. Sin este corrimiento, pedir "hoy" dejaba afuera
# la madrugada de hoy (00-03 AR = 03-06 UTC de hoy) y metía la noche anterior.
_OFFSET_LOCAL = timedelta(hours=3)


def _rango_de_dias(
    fecha_desde: Optional[str], fecha_hasta: Optional[str]
) -> tuple[Optional[datetime], Optional[datetime]]:
    """Día argentino (YYYY-MM-DD) → rango [desde, hasta) en UTC naive.

    `fecha_hasta` es el último día **incluido**, así que el límite superior se
    corre al día siguiente.
    """
    def _inicio(dia: str) -> datetime:
        try:
            d = datetime.strptime(dia, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Fecha inválida: '{dia}'. Usar el formato YYYY-MM-DD",
            )
        return d.replace(hour=0, minute=0, second=0, microsecond=0) + _OFFSET_LOCAL

    desde = _inicio(fecha_desde) if fecha_desde else None
    hasta = _inicio(fecha_hasta) + timedelta(days=1) if fecha_hasta else None
    return desde, hasta


def _venta_to_dict(v: Venta) -> dict:
    """Convierte una venta a dict seguro para JSON, evitando lazy loads."""
    return {
        "id": v.id,
        "numero": v.numero,
        "cliente_id": v.cliente_id,
        "cliente_nombre": v.cliente.nombre if v.cliente else None,
        "comprador_cuit": v.comprador_cuit,
        "usuario_id": v.usuario_id,
        "sucursal_id": v.sucursal_id,
        "fecha": v.fecha.isoformat() if v.fecha else None,
        "subtotal": v.subtotal,
        "descuento": v.descuento,
        "total": v.total,
        "medio_pago": v.medio_pago,
        "estado": v.estado,
        "modificada_en": v.modificada_en.isoformat() if v.modificada_en else None,
        "notas": v.notas,
        "items": [
            {
                "id": i.id,
                "producto_id": i.producto_id,
                "producto_nombre": i.producto.nombre if i.producto else "",
                "cantidad": i.cantidad,
                "precio_unitario": i.precio_unitario,
                "precio_costo": i.precio_costo,
                "subtotal": i.subtotal,
                "oferta_tipo": i.oferta_tipo,
                "oferta_valor": i.oferta_valor,
                "oferta_info": i.oferta_info,
                "por_kilo": i.por_kilo,
                "peso": i.peso,
            }
            for i in (v.items or [])
        ],
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


class VentaCreate(BaseModel):
    cliente_id: Optional[int] = None
    sucursal_id: int = 1
    notas: Optional[str] = None


class VentaItemAdd(BaseModel):
    producto_id: int
    cantidad: float = Field(..., gt=0)
    precio_unitario: Optional[float] = None
    oferta_tipo: Optional[str] = None
    oferta_valor: Optional[float] = None
    oferta_info: Optional[str] = None
    por_kilo: Optional[bool] = False
    peso: Optional[float] = None
    importe: Optional[float] = Field(None, gt=0, description="Importe a cobrar por peso. Si viene, define el subtotal exacto y el peso se recalcula como importe / precio_unitario.")
    medio_pago_carga: Optional[str] = Field(None, description="Cuenta de donde sale el dinero para recargas (smartpoint, mercadopago_qr, etc.). Si es 'manual' o null, no genera egreso en caja.")


class VentaConfirmar(BaseModel):
    medio_pago: str = "efectivo"
    efectivo_pagado: float = 0.0
    descuento: float = 0.0
    descuento_tipo: Optional[str] = Field(None, description="Tipo de descuento: 'manual' o 'automatico'")
    cliente_id: Optional[int] = None
    comprador_cuit: Optional[str] = None


class CambiarMedioPago(BaseModel):
    medio_pago: str = Field(
        ...,
        description=(
            "Medio de pago nuevo: efectivo, debito, credito, transferencia, "
            "mercadopago_qr, qr_interop, mercadopago_pos, smartpoint o cta_corriente"
        ),
    )


@router.get("", response_model=RespuestaLista)
def listar(
    estado: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    fecha_desde: Optional[str] = Query(
        None, description="Primer día a listar (YYYY-MM-DD, hora Argentina)"
    ),
    fecha_hasta: Optional[str] = Query(
        None, description="Último día a listar, incluido (YYYY-MM-DD, hora Argentina)"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Lista ventas con filtros.

    `fecha_desde`/`fecha_hasta` son días en hora Argentina (el negocio): el POS
    los usa para mostrar "Últimas transacciones" sólo del día de hoy.
    """
    desde, hasta = _rango_de_dias(fecha_desde, fecha_hasta)
    ventas, total = venta_service.listar_ventas(
        db, estado=estado, cliente_id=cliente_id,
        desde=desde, hasta=hasta, page=page, page_size=page_size,
    )
    return RespuestaLista(
        data=[_venta_to_dict(v) for v in ventas],
        total=total, page=page, page_size=page_size,
        message=f"{total} venta(s)"
    )


@router.get("/exportar")
def exportar_ventas(
    estado: Optional[str] = Query(None),
    cliente_id: Optional[int] = Query(None),
    fecha_desde: Optional[str] = Query(None),
    fecha_hasta: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Exporta las ventas del rango a un archivo Excel (.xlsx)."""
    import io
    from fastapi.responses import StreamingResponse
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.utils import get_column_letter

    desde, hasta = _rango_de_dias(fecha_desde, fecha_hasta)
    ventas, total = venta_service.listar_ventas(
        db, estado=estado, cliente_id=cliente_id,
        desde=desde, hasta=hasta, page=1, page_size=100000,
    )

    wb = Workbook()
    ws = wb.active
    ws.title = "Ventas"

    headers = [
        "Número", "Fecha", "Cliente", "CUIT comprador", "Medio de pago",
        "Estado", "Subtotal", "Descuento", "Total", "Items",
    ]
    header_fill = PatternFill("solid", fgColor="4F46E5")
    header_font = Font(bold=True, color="FFFFFF")
    for col, h in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row_idx, v in enumerate(ventas, start=2):
        items_txt = " | ".join(
            f"{it.producto_nombre} x{it.cantidad} @ {it.precio_unitario}"
            for it in (v.items or [])
        )
        ws.cell(row=row_idx, column=1, value=v.numero)
        ws.cell(row=row_idx, column=2, value=v.fecha.isoformat() if v.fecha else None)
        ws.cell(row=row_idx, column=3, value=v.cliente.nombre if v.cliente else "Consumidor Final")
        ws.cell(row=row_idx, column=4, value=v.comprador_cuit)
        ws.cell(row=row_idx, column=5, value=v.medio_pago)
        ws.cell(row=row_idx, column=6, value=v.estado)
        ws.cell(row=row_idx, column=7, value=v.subtotal)
        ws.cell(row=row_idx, column=8, value=v.descuento)
        ws.cell(row=row_idx, column=9, value=v.total)
        ws.cell(row=row_idx, column=10, value=items_txt)

    # Anchos
    widths = [14, 20, 24, 14, 16, 12, 12, 12, 12, 60]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = "ventas.xlsx"
    if fecha_desde or fecha_hasta:
        filename = f"ventas_{fecha_desde or ''}_{fecha_hasta or ''}.xlsx".replace("__", "_")

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{venta_id}", response_model=RespuestaData)
def obtener(
    venta_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene una venta con sus items."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    return RespuestaData(data=_venta_to_dict(venta))


@router.post("", response_model=RespuestaData)
def crear(
    data: VentaCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Crea una venta nueva (vacía, estado pendiente)."""
    venta = venta_service.crear_venta(
        db,
        usuario_id=user.id,
        cliente_id=data.cliente_id,
        sucursal_id=data.sucursal_id,
        notas=data.notas,
    )
    auditoria_service.registrar(db, user.id, "carrito_creado", venta.id, venta.numero)
    return RespuestaData(data=_venta_to_dict(venta), message=f"Venta {venta.numero} creada")


@router.post("/{venta_id}/items", response_model=RespuestaData)
def agregar_item(
    venta_id: int,
    data: VentaItemAdd,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Agrega un producto a la venta."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        item = venta_service.agregar_item(
            db, venta, data.producto_id, data.cantidad, data.precio_unitario,
            data.oferta_tipo, data.oferta_valor, data.oferta_info,
            data.por_kilo, data.peso, data.importe, data.medio_pago_carga
        )
        db.refresh(venta)
        auditoria_service.registrar(db, user.id, "item_agregado", venta.id, venta.numero, {
            "producto_id": data.producto_id,
            "producto_nombre": item.producto.nombre if item.producto else "?",
            "cantidad": data.cantidad,
            "por_kilo": data.por_kilo,
            "peso": data.peso,
            "precio_unitario": data.precio_unitario,
            "subtotal": item.subtotal,
        })
        return RespuestaData(
            data={"item_id": item.id, "subtotal": item.subtotal, "venta_subtotal": venta.subtotal},
            message="Ítem agregado",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{venta_id}/items/{item_id}", response_model=RespuestaData)
def quitar_item(
    venta_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Quita un ítem de la venta."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        # Obtener info del item antes de quitarlo para el log
        item_obj = next((i for i in venta.items if i.id == item_id), None)
        detalle = None
        if item_obj:
            detalle = {
                "producto": item_obj.producto.nombre if item_obj.producto else "?",
                "cantidad": item_obj.cantidad,
                "precio": item_obj.precio_unitario,
                "subtotal_anterior": item_obj.subtotal,
                "venta_subtotal_antes": venta.subtotal,
                "venta_total_antes": venta.total,
            }
        items_antes = len(venta.items)
        venta_service.quitar_item(db, venta, item_id)
        db.refresh(venta)
        if detalle:
            detalle["venta_subtotal_despues"] = venta.subtotal
        auditoria_service.registrar(db, user.id, "item_quitado", venta.id, venta.numero, detalle)
        if items_antes == 1:
            auditoria_service.registrar(db, user.id, "carrito_vaciado", venta.id, venta.numero, {
                "ultimo_item": detalle,
                "subtotal_final": 0,
            })
        return RespuestaData(data={"venta_subtotal": venta.subtotal}, message="Ítem quitado")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{venta_id}/confirmar", response_model=RespuestaData)
def confirmar(
    venta_id: int,
    data: VentaConfirmar,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Confirma la venta: descuenta stock, registra en caja."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    # Si se especificó cliente_id, asignarlo antes de confirmar
    if data.cliente_id and not venta.cliente_id:
        venta.cliente_id = data.cliente_id
        db.commit()
    if data.comprador_cuit:
        venta.comprador_cuit = data.comprador_cuit
        db.commit()
    try:
        venta = venta_service.confirmar_venta(
            db, venta, data.medio_pago, data.efectivo_pagado, data.descuento, user.id
        )
        auditoria_service.registrar(db, user.id, "venta_confirmada", venta.id, venta.numero,
                                     {"medio_pago": data.medio_pago, "total": venta.total, "items": len(venta.items), "descuento": data.descuento, "hora": datetime.now().strftime("%H:%M")})
        if data.descuento and data.descuento > 0:
            tipo_desc = data.descuento_tipo or "manual"
            if venta.subtotal > 0 and data.descuento >= venta.subtotal:
                evento_desc = "descuento_100pct"
            else:
                evento_desc = f"descuento_{tipo_desc}"
            auditoria_service.registrar(db, user.id, evento_desc, venta.id, venta.numero,
                                         {"monto_descuento": data.descuento, "total_original": venta.subtotal,
                                          "total_final": venta.total, "tipo": tipo_desc})

        whatsapp_url = None
        if venta.cliente_id and venta.cliente and venta.cliente.telefono:
            telefono = venta.cliente.telefono.replace('+','').replace(' ','').replace('-','')
            items_detalle = ", ".join([f"{i.cantidad}x {i.producto.nombre if i.producto else '?'}" for i in venta.items][:5])
            mensaje = f"*Ticket #{venta.numero}*%0A%0A*Total:* ${venta.total:,.2f}%0A*Medio:* {data.medio_pago}%0A*Items:* {items_detalle}%0A*Fecha:* {datetime.now().strftime('%d/%m/%Y %H:%M')}"
            whatsapp_url = f"https://wa.me/{telefono}?text={mensaje}"

        respuesta_data = _venta_to_dict(venta)
        if whatsapp_url:
            respuesta_data["whatsapp_url"] = whatsapp_url
        return RespuestaData(
            data=respuesta_data,
            message=f"Venta {venta.numero} confirmada. Total: ${venta.total:,.2f}" + (" Enviando WhatsApp..." if whatsapp_url else ""),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{venta_id}/anular", response_model=RespuestaData)
def anular(
    venta_id: int,
    edit: bool = Query(False, description="Si es true, se registra como edición en auditoría"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado", "cajero", permiso="anular_ventas")),
):
    """Anula una venta confirmada, revirtiendo stock y caja."""
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        venta = venta_service.anular_venta(db, venta, user.id)
        evento = "venta_editada" if edit else "venta_anulada"
        auditoria_service.registrar(db, user.id, evento, venta.id, venta.numero,
                                     {"total_anulado": venta.total, "medio_pago": venta.medio_pago, "edit": edit})
        return RespuestaData(data=_venta_to_dict(venta), message=f"Venta {venta.numero} anulada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{venta_id}/medio-pago", response_model=RespuestaData)
def cambiar_medio_pago(
    venta_id: int,
    data: CambiarMedioPago,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado", "cajero", permiso="anular_ventas")),
):
    """Corrige el medio de pago de una venta ya cobrada.

    No anula ni rehace nada: cambia el medio y los ingresos que esa venta dejó
    en caja, marca la venta con `modificada_en` y deja un evento de auditoría
    en "pendientes" para que el administrador lo revise. Existe porque ya pasó
    dos veces: el cliente terminó pagando de otra forma y la venta ya estaba
    registrada para no hacer esperar a la cola.
    """
    venta = venta_service.obtener_venta(db, venta_id)
    if not venta:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    try:
        anterior = venta.medio_pago
        venta = venta_service.cambiar_medio_pago(db, venta, data.medio_pago, user.id)
        auditoria_service.registrar(
            db, user.id, "medio_pago_corregido", venta.id, venta.numero,
            {"medio_pago_antes": anterior, "medio_pago": data.medio_pago,
             "total": venta.total, "hora": datetime.now().strftime("%H:%M")},
        )
        return RespuestaData(
            data=_venta_to_dict(venta),
            message=f"Venta {venta.numero}: {anterior} → {data.medio_pago}. Quedó marcada para revisión.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
