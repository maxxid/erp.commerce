"""Router de Caja: apertura, cierre por método, cierre total."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services import caja_service
from app.services import catalogo_service
from app.services import auditoria_service
from app.services import config_service
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/caja", tags=["Caja"])


class AperturaRequest(BaseModel):
    monto_inicial: float = Field(..., ge=0)
    sucursal_id: int = 1
    monto_retiro: float = Field(0.0, ge=0, description="Monto que se retira al abrir caja")
    motivo_retiro: str = Field("", description="Motivo del retiro (ej: 'Fondo para cambio')")


class CierreMetodoRequest(BaseModel):
    medio_pago: str = Field(...)
    monto_real: float = Field(..., ge=0)
    comentario: str = ""
    sucursal_id: int = 1


class CierreTotalRequest(BaseModel):
    comentario: str = ""
    sucursal_id: int = 1


class MovimientoRequest(BaseModel):
    monto: float = Field(..., gt=0)
    descripcion: str = ""
    sucursal_id: int = 1
    medio_pago: Optional[str] = None


class EgresoEspecialRequest(BaseModel):
    monto: float = Field(..., gt=0)
    descripcion: str = ""
    egreso_tipo: str = Field(..., description="Tipo: 'proveedor' o 'dueño'")
    proveedor_id: Optional[int] = Field(None, description="ID del proveedor si egreso_tipo='proveedor'")
    proveedor_nombre: Optional[str] = Field(None, description="Nombre del proveedor o beneficiario")
    sucursal_id: int = 1


@router.get("/estado", response_model=RespuestaData)
def estado(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    state = caja_service.obtener_estado_caja(db)
    return RespuestaData(data=state)


@router.get("/ultimo-cierre", response_model=RespuestaData)
def ultimo_cierre(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene información del último cierre de caja.
    
    Devuelve el monto del último cierre (manual o automático), fecha, y si fue automático.
    Se usa para sugerir el monto inicial al abrir caja.
    """
    info = caja_service.obtener_ultimo_cierre(db)
    return RespuestaData(data=info)


class ConfirmarCierreRequest(BaseModel):
    monto_confirmado: float = Field(..., ge=0)
    comentario: str = ""
    sucursal_id: int = 1


@router.put("/cierre/{cierre_id}/confirmar", response_model=RespuestaData)
def confirmar_cierre(
    cierre_id: int,
    data: ConfirmarCierreRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Confirma o ajusta un cierre (auto o manual) con el monto real contado."""
    try:
        mov = caja_service.confirmar_cierre(
            db, cierre_id, data.monto_confirmado, user.id,
            data.comentario, data.sucursal_id,
        )
        diferencia = (mov.monto_confirmado or 0) - (mov.monto_esperado or mov.monto)
        auditoria_service.registrar(
            db, user.id, "confirmar_cierre_caja", mov.id, None, {
                "monto_confirmado": data.monto_confirmado,
                "monto_esperado": mov.monto_esperado,
                "diferencia": diferencia,
                "comentario": data.comentario,
                "sucursal_id": data.sucursal_id,
            },
        )
        return RespuestaData(
            data={
                "id": mov.id,
                "monto_confirmado": mov.monto_confirmado,
                "monto_esperado": mov.monto_esperado,
                "diferencia": diferencia,
                "confirmado_por_id": mov.confirmado_por_id,
                "confirmado_at": mov.confirmado_at.isoformat() if mov.confirmado_at else None,
            },
            message=f"Cierre confirmado. Diferencia: ${diferencia:,.2f}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/apertura", response_model=RespuestaData)
def apertura(
    data: AperturaRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    try:
        mov = caja_service.abrir_caja(
            db, data.monto_inicial, user.id, data.sucursal_id,
            monto_retiro=data.monto_retiro,
            motivo_retiro=data.motivo_retiro,
        )
        auditoria_service.registrar(db, user.id, "apertura_caja", None, None,
                                   {"monto_inicial": data.monto_inicial, 
                                    "monto_retiro": data.monto_retiro,
                                    "motivo_retiro": data.motivo_retiro,
                                    "sucursal_id": data.sucursal_id})
        return RespuestaData(
            data={"id": mov.id, "monto": mov.monto, "tipo": mov.tipo},
            message="Caja abierta",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cierre-metodo", response_model=RespuestaData)
def cierre_metodo(
    data: CierreMetodoRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Cierra un medio de pago específico con su propio arqueo."""
    try:
        mov, esperado, diferencia = caja_service.cerrar_metodo(
            db, data.medio_pago, data.monto_real, user.id,
            data.comentario, data.sucursal_id
        )
        auditoria_service.registrar(db, user.id, "cierre_caja", None, None,
                                   {"medio_pago": data.medio_pago, "monto_real": data.monto_real,
                                    "esperado": esperado, "diferencia": diferencia, "sucursal_id": data.sucursal_id})
        return RespuestaData(
            data={
                "id": mov.id, "medio_pago": data.medio_pago,
                "monto_real": data.monto_real, "saldo_esperado": esperado,
                "diferencia": diferencia,
            },
            message=f"{data.medio_pago} cerrado. Diferencia: ${diferencia:,.2f}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cierre-total", response_model=RespuestaData)
def cierre_total(
    data: CierreTotalRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Cierra la caja completamente. Fin de la sesión."""
    try:
        mov, desglose = caja_service.cerrar_todo(
            db, user.id, data.comentario, data.sucursal_id
        )
        auditoria_service.registrar(db, user.id, "cierre_total_caja", None, None,
                                   {"total_ingresos": desglose["total_ingresos"], "comentario": data.comentario, "sucursal_id": data.sucursal_id})
        # Auto-exportar catálogo al cerrar caja
        try:
            catalogo_service.subir_catalogo_a_r2(db)
        except Exception:
            pass
        return RespuestaData(
            data={
                "id": mov.id,
                "total_ingresos": desglose["total_ingresos"],
                "desglose": desglose["desglose"],
            },
            message="Caja cerrada totalmente.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingreso", response_model=RespuestaData)
def ingreso(
    data: MovimientoRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    if not caja_service.caja_abierta(db):
        raise HTTPException(status_code=400, detail="La caja no está abierta")
    mov = caja_service.registrar_ingreso(
        db, data.monto, data.descripcion or "Ingreso manual", user.id,
        medio_pago=data.medio_pago or "efectivo",
        sucursal_id=data.sucursal_id,
    )
    auditoria_service.registrar(db, user.id, "ingreso_caja", None, None,
                               {"monto": data.monto, "descripcion": data.descripcion, "sucursal_id": data.sucursal_id})
    return RespuestaData(data={"id": mov.id, "monto": mov.monto}, message="Ingreso registrado")


@router.post("/egreso", response_model=RespuestaData)
def egreso(
    data: MovimientoRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    if not caja_service.caja_abierta(db):
        raise HTTPException(status_code=400, detail="La caja no está abierta")
    mov = caja_service.registrar_egreso(
        db, data.monto, data.descripcion or "Egreso manual", user.id,
        sucursal_id=data.sucursal_id,
    )
    auditoria_service.registrar(db, user.id, "egreso_caja", None, None,
                               {"monto": data.monto, "descripcion": data.descripcion, "sucursal_id": data.sucursal_id})
    return RespuestaData(data={"id": mov.id, "monto": mov.monto}, message="Egreso registrado")


@router.post("/egreso-especial", response_model=RespuestaData)
def egreso_especial(
    data: EgresoEspecialRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Registra un egreso especial (pago a proveedor o extracción del dueño) con notificación WhatsApp."""
    if not caja_service.caja_abierta(db):
        raise HTTPException(status_code=400, detail="La caja no está abierta")
    if data.egreso_tipo not in ("proveedor", "dueño"):
        raise HTTPException(status_code=400, detail="egreso_tipo debe ser 'proveedor' o 'dueño'")

    descripcion_completa = f"[{data.egreso_tipo.upper()}] {data.descripcion}"
    if data.proveedor_nombre:
        descripcion_completa = f"[{data.egreso_tipo.upper()}] {data.proveedor_nombre}: {data.descripcion}"

    mov = caja_service.registrar_egreso(
        db, data.monto, descripcion_completa, user.id,
        referencia_tipo=f"egreso_{data.egreso_tipo}",
        referencia_id=data.proveedor_id,
        sucursal_id=data.sucursal_id,
    )
    auditoria_service.registrar(db, user.id, "egreso_especial", None, None, {
        "monto": data.monto,
        "descripcion": descripcion_completa,
        "egreso_tipo": data.egreso_tipo,
        "proveedor_id": data.proveedor_id,
        "proveedor_nombre": data.proveedor_nombre,
        "sucursal_id": data.sucursal_id,
    })

    telefono_dueño = config_service.get_config(db, "telefono_dueño")
    whatsapp_url = None
    if telefono_dueño:
        mensaje = f"Pago registrado:%0A%0A*Tipo:* {data.egreso_tipo.upper()}%0A*Monto:* ${data.monto:,.2f}%0A*Descripción:* {data.descripcion}%0A*Cajero:* {user.nombre}%0A*Hora:* {datetime.now().strftime('%H:%M')}"
        whatsapp_url = f"https://wa.me/{telefono_dueño.replace('+','').replace(' ','').replace('-','')}?text={mensaje}"

    return RespuestaData(
        data={
            "id": mov.id,
            "monto": mov.monto,
            "whatsapp_url": whatsapp_url,
        },
        message=f"Egreso especial registrado. {'Notificación WhatsApp lista.' if whatsapp_url else 'Sin número de dueño configurado.'}",
    )


@router.get("/calendario", response_model=RespuestaData)
def calendario_caja(
    mes: Optional[str] = Query(None, description="Mes en formato YYYY-MM. Si viene vacío usa el mes actual"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Resumen por día del mes (semáforo): verde ok, amarillo corrección, rojo sin conciliar."""
    import calendar as _cal
    from datetime import datetime, timedelta
    from app.models.movimiento_caja import MovimientoCaja
    from app.models.venta import Venta
    from app.services.caja_service import _a_local

    ahora = datetime.now()
    try:
        aaaa, mm = mes.split("-")
        if len(aaaa) != 4 or len(mm) != 2:
            raise ValueError
        aaaa, mm = int(aaaa), int(mm)
    except Exception:
        aaaa, mm = ahora.year, ahora.month

    dias_del_mes = _cal.monthrange(aaaa, mm)[1]
    # Límites en UTC de un día local argentino (00:00 AR = 03:00 UTC del mismo día)
    inicio_ar = datetime(aaaa, mm, 1)
    fin_ar = inicio_ar.replace(day=dias_del_mes, hour=23, minute=59, second=59)
    inicio_utc = inicio_ar - timedelta(hours=3)
    fin_utc = fin_ar - timedelta(hours=3)

    movs = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == 1,
            MovimientoCaja.created_at >= inicio_utc,
            MovimientoCaja.created_at <= fin_utc,
        )
        .order_by(MovimientoCaja.id.asc())
        .all()
    )
    ventas = (
        db.query(Venta)
        .filter(
            Venta.sucursal_id == 1,
            Venta.estado == "confirmada",
            Venta.created_at >= inicio_utc,
            Venta.created_at <= fin_utc,
        )
        .all()
    )

    resumen_dia = {}
    for m in movs:
        dia = _a_local(m.created_at).strftime("%Y-%m-%d") if m.created_at else None
        if not dia:
            continue
        r = resumen_dia.setdefault(dia, {
            "fecha": dia, "estado": "sin_operacion", "apertura": 0.0,
            "cierre": None, "ingresos": 0.0, "egresos": 0.0,
            "desglose": {}, "n_cierres": 0, "n_automaticos": 0,
            "pendientes_conciliacion": 0, "correcciones": 0,
        })
        if m.tipo == "apertura":
            r["apertura"] += m.monto or 0
        elif m.tipo == "ingreso":
            mp = m.medio_pago or "efectivo"
            r["desglose"][mp] = r["desglose"].get(mp, 0) + (m.monto or 0)
            r["ingresos"] += m.monto or 0
        elif m.tipo == "egreso":
            r["egresos"] += m.monto or 0
        elif m.tipo == "cierre" and not m.medio_pago:
            r["n_cierres"] += 1
            r["cierre"] = m.monto
            if m.fue_automatico:
                r["n_automaticos"] += 1
            if not m.monto_confirmado:
                r["pendientes_conciliacion"] += 1
            elif m.monto_confirmado is not None:
                esperado = m.monto_esperado or m.monto
                if abs(m.monto_confirmado - esperado) > 0.01:
                    r["correcciones"] += 1

    for dia, r in resumen_dia.items():
        if r["estado"] == "sin_operacion" and (r["apertura"] or r["ingresos"] or r["egresos"] or r["n_cierres"]):
            r["estado"] = "abierta"
        if r["pendientes_conciliacion"] > 0:
            r["estado"] = "rojo"
        elif r["correcciones"] > 0:
            r["estado"] = "amarillo"
        elif r["n_cierres"] > 0:
            r["estado"] = "verde"

    # Completar días sin operaciones del mes
    for d in range(1, dias_del_mes + 1):
        fecha = f"{aaaa:04d}-{mm:02d}-{d:02d}"
        if fecha not in resumen_dia:
            resumen_dia[fecha] = {
                "fecha": fecha, "estado": "sin_operacion", "apertura": 0.0,
                "cierre": None, "ingresos": 0.0, "egresos": 0.0,
                "desglose": {}, "n_cierres": 0, "n_automaticos": 0,
                "pendientes_conciliacion": 0, "correcciones": 0,
            }

    dias = []
    for d in range(1, dias_del_mes + 1):
        fecha = f"{aaaa:04d}-{mm:02d}-{d:02d}"
        r = resumen_dia[fecha]
        r["ventas"] = sum(1 for v in ventas if _a_local(v.created_at).strftime("%Y-%m-%d") == fecha)
        r["ventas_total"] = round(sum(v.total for v in ventas if _a_local(v.created_at).strftime("%Y-%m-%d") == fecha), 2)
        dias.append(r)

    return RespuestaData(data={"mes": f"{aaaa:04d}-{mm:02d}", "dias": dias})


@router.get("/dia", response_model=RespuestaData)
def dia_caja(
    fecha: str = Query(..., description="Fecha en formato YYYY-MM-DD"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Detalle de un día: sesiones, desglose por medio y ventas (tickets)."""
    from datetime import datetime, timedelta
    from app.models.movimiento_caja import MovimientoCaja
    from app.models.venta import Venta
    from app.services.caja_service import _a_local

    try:
        fecha_dt = datetime.strptime(fecha, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Fecha inválida. Formato: YYYY-MM-DD")

    inicio_utc = fecha_dt - timedelta(hours=3)
    fin_utc = fecha_dt.replace(hour=23, minute=59, second=59) - timedelta(hours=3)

    movs = (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.sucursal_id == 1,
            MovimientoCaja.created_at >= inicio_utc,
            MovimientoCaja.created_at <= fin_utc,
        )
        .order_by(MovimientoCaja.id.asc())
        .all()
    )
    ventas = (
        db.query(Venta)
        .filter(
            Venta.sucursal_id == 1,
            Venta.estado == "confirmada",
            Venta.created_at >= inicio_utc,
            Venta.created_at <= fin_utc,
        )
        .order_by(Venta.id.asc())
        .all()
    )

    desglose = {}
    total_ingresos = 0.0
    total_egresos = 0.0
    apertura = 0.0
    cierres = []
    movimientos = []
    for m in movs:
        item = {
            "id": m.id, "tipo": m.tipo, "monto": m.monto,
            "monto_esperado": m.monto_esperado,
            "monto_confirmado": m.monto_confirmado,
            "fue_automatico": bool(m.fue_automatico),
            "confirmado_por_id": m.confirmado_por_id,
            "confirmado_por": (m.confirmado_por.nombre if m.confirmado_por else ""),
            "confirmado_at": m.confirmado_at.isoformat() if m.confirmado_at else None,
            "comentario_concil": m.comentario_concil,
            "descripcion": m.descripcion, "medio_pago": m.medio_pago,
            "referencia_tipo": m.referencia_tipo, "referencia_id": m.referencia_id,
            "usuario_id": m.usuario_id,
            "usuario_nombre": m.usuario.nombre if m.usuario else "",
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        movimientos.append(item)
        if m.tipo == "apertura":
            apertura = m.monto or 0
        elif m.tipo == "ingreso":
            mp = m.medio_pago or "efectivo"
            desglose[mp] = desglose.get(mp, 0) + (m.monto or 0)
            total_ingresos += m.monto or 0
        elif m.tipo == "egreso":
            total_egresos += m.monto or 0
        elif m.tipo == "cierre" and not m.medio_pago:
            esperado = m.monto_esperado or m.monto
            confirmado = m.monto_confirmado
            cierres.append({
                "id": m.id, "monto": m.monto, "monto_esperado": esperado,
                "monto_confirmado": confirmado,
                "diferencia": round((confirmado - esperado), 2) if confirmado is not None else None,
                "fue_automatico": bool(m.fue_automatico),
                "confirmado_por": (m.confirmado_por.nombre if m.confirmado_por else ""),
                "confirmado_at": m.confirmado_at.isoformat() if m.confirmado_at else None,
                "comentario_concil": m.comentario_concil,
                "usuario_nombre": m.usuario.nombre if m.usuario else "",
                "descripcion": m.descripcion,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            })

    tickets = [{
        "id": v.id, "numero": v.numero, "fecha": v.created_at.isoformat() if v.created_at else None,
        "medio_pago": v.medio_pago, "total": v.total, "estado": v.estado,
        "cliente": v.cliente.nombre if v.cliente else "",
        "vendedor": v.usuario.nombre if v.usuario else "",
    } for v in ventas]

    return RespuestaData(data={
        "fecha": fecha, "apertura": apertura,
        "total_ingresos": round(total_ingresos, 2),
        "total_egresos": round(total_egresos, 2),
        "desglose": desglose,
        "saldo_final": round(apertura + total_ingresos - total_egresos, 2),
        "cierres": cierres,
        "movimientos": movimientos,
        "tickets": tickets,
        "n_ventas": len(tickets),
    })


@router.get("/movimientos", response_model=RespuestaLista)
def movimientos(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    movs, total = caja_service.listar_movimientos(db, page=page, page_size=page_size)
    data = [{
        "id": m.id, "tipo": m.tipo, "monto": m.monto,
        "descripcion": m.descripcion, "medio_pago": m.medio_pago,
        "referencia_tipo": m.referencia_tipo, "referencia_id": m.referencia_id,
        "usuario_id": m.usuario_id,
        "usuario_nombre": m.usuario.nombre if m.usuario else "",
        "sucursal_id": m.sucursal_id,
        "monto_esperado": m.monto_esperado,
        "monto_confirmado": m.monto_confirmado,
        "fue_automatico": bool(m.fue_automatico),
        "confirmado_por": m.confirmado_por.nombre if m.confirmado_por else "",
        "confirmado_at": m.confirmado_at.isoformat() if m.confirmado_at else None,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    } for m in movs]
    return RespuestaLista(
        data=data, total=total, page=page, page_size=page_size,
        message=f"{total} movimiento(s)"
    )


@router.get("/resumen", response_model=RespuestaData)
def resumen_por_medio(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    data = caja_service.obtener_resumen_por_medio_pago(db)
    data["metodos_cerrados"] = caja_service._metodos_ya_cerrados(db)
    return RespuestaData(data=data)


@router.get("/reportes", response_model=RespuestaData)
def reportes_caja(
    fecha_inicio: Optional[str] = Query(None, description="Fecha inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[str] = Query(None, description="Fecha fin (YYYY-MM-DD)"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Reporte de sesiones de caja con aperturas, cierres y discrepancias."""
    from datetime import datetime
    from app.models.movimiento_caja import MovimientoCaja
    
    # Parsear fechas
    fecha_ini = None
    fecha_fi = None
    if fecha_inicio:
        try:
            fecha_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
        except:
            pass
    if fecha_fin:
        try:
            fecha_fi = datetime.strptime(fecha_fin, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        except:
            pass
    
    # Obtener todos los movimientos en el rango
    query = db.query(MovimientoCaja).filter(
        MovimientoCaja.sucursal_id == 1
    )
    
    if fecha_ini:
        query = query.filter(MovimientoCaja.created_at >= fecha_ini)
    if fecha_fi:
        query = query.filter(MovimientoCaja.created_at <= fecha_fi)
    
    movimientos = query.order_by(MovimientoCaja.created_at.desc()).all()
    
    # Agrupar por sesiones (apertura -> cierre)
    sesiones = []
    sesion_actual = None
    
    for mov in movimientos:
        if mov.tipo == "apertura":
            # Nueva sesión
            sesion_actual = {
                "id": mov.id,
                "apertura_id": mov.id,
                "apertura_fecha": mov.created_at.isoformat() if mov.created_at else None,
                "apertura_monto": mov.monto,
                "apertura_usuario": mov.usuario.nombre if mov.usuario else "Desconocido",
                "apertura_descripcion": mov.descripcion,
                "cierres": [],
                "ingresos": [],
                "egresos": [],
                "total_ingresos": 0,
                "total_egresos": 0,
                "saldo_final": 0,
                "estado": "abierta"
            }
            sesiones.append(sesion_actual)
        elif mov.tipo == "cierre" and sesion_actual:
            # Cierre de sesión
            sesion_actual["cierre_id"] = mov.id
            sesion_actual["cierre_fecha"] = mov.created_at.isoformat() if mov.created_at else None
            sesion_actual["cierre_monto"] = mov.monto
            sesion_actual["cierre_monto_esperado"] = mov.monto_esperado or mov.monto
            sesion_actual["cierre_monto_confirmado"] = mov.monto_confirmado
            sesion_actual["cierre_usuario"] = mov.usuario.nombre if mov.usuario else "Desconocido"
            sesion_actual["cierre_descripcion"] = mov.descripcion
            sesion_actual["cierre_confirmado_por"] = mov.confirmado_por.nombre if mov.confirmado_por else ""
            sesion_actual["cierre_confirmado_at"] = mov.confirmado_at.isoformat() if mov.confirmado_at else None
            sesion_actual["cierre_comentario"] = mov.comentario_concil
            sesion_actual["estado"] = "cerrada"
            
            # Calcular saldo final
            total_ingresos = sum(i["monto"] for i in sesion_actual["ingresos"])
            total_egresos = sum(e["monto"] for e in sesion_actual["egresos"])
            sesion_actual["total_ingresos"] = total_ingresos
            sesion_actual["total_egresos"] = total_egresos
            sesion_actual["saldo_final"] = sesion_actual["apertura_monto"] + total_ingresos - total_egresos
            
            # Detectar si fue automático
            sesion_actual["fue_automatico"] = bool(mov.fue_automatico) or (mov.descripcion and "automático" in mov.descripcion.lower())
            
            sesion_actual = None
        elif mov.tipo == "ingreso" and sesion_actual:
            sesion_actual["ingresos"].append({
                "id": mov.id,
                "monto": mov.monto,
                "medio_pago": mov.medio_pago,
                "descripcion": mov.descripcion,
                "fecha": mov.created_at.isoformat() if mov.created_at else None
            })
        elif mov.tipo == "egreso" and sesion_actual:
            sesion_actual["egresos"].append({
                "id": mov.id,
                "monto": mov.monto,
                "descripcion": mov.descripcion,
                "fecha": mov.created_at.isoformat() if mov.created_at else None
            })
    
    # Obtener cierres parciales (arqueos por método)
    cierres_parciales = db.query(MovimientoCaja).filter(
        MovimientoCaja.sucursal_id == 1,
        MovimientoCaja.tipo == "cierre_parcial"
    )
    
    if fecha_ini:
        cierres_parciales = cierres_parciales.filter(MovimientoCaja.created_at >= fecha_ini)
    if fecha_fi:
        cierres_parciales = cierres_parciales.filter(MovimientoCaja.created_at <= fecha_fi)
    
    cierres_parciales = cierres_parciales.order_by(MovimientoCaja.created_at.desc()).all()
    
    # Enriquecer sesiones con información de cierres parciales
    for sesion in sesiones:
        if sesion.get("apertura_id") and sesion.get("cierre_id"):
            cierres_metodo = [
                c for c in cierres_parciales
                if sesion["apertura_id"] < c.id < sesion["cierre_id"]
            ]
            
            discrepancias = []
            for c in cierres_metodo:
                # Parsear descripción para extraer esperado y diferencia
                esperado = 0
                diferencia = 0
                if c.descripcion:
                    try:
                        parts = c.descripcion.split("Esperado: $")[1].split(". Diferencia: $")
                        if len(parts) >= 2:
                            esperado = float(parts[0].replace(",", ""))
                            diferencia_str = parts[1].split(" — ")[0].replace(",", "")
                            diferencia = float(diferencia_str)
                    except:
                        pass
                
                discrepancias.append({
                    "medio_pago": c.medio_pago,
                    "monto_real": c.monto,
                    "esperado": esperado,
                    "diferencia": diferencia,
                    "descripcion": c.descripcion,
                    "fecha": c.created_at.isoformat() if c.created_at else None,
                    "usuario": c.usuario.nombre if c.usuario else "Desconocido"
                })
            
            sesion["cierres_metodo"] = discrepancias
            sesion["tiene_discrepancias"] = any(abs(d["diferencia"]) > 0.01 for d in discrepancias)
    
    return RespuestaData(data={
        "sesiones": sesiones,
        "total_sesiones": len(sesiones)
    })
