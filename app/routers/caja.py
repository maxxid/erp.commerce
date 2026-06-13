"""Router de Caja: apertura, cierre por método, cierre total."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services import caja_service
from app.services import catalogo_service
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/caja", tags=["Caja"])


class AperturaRequest(BaseModel):
    monto_inicial: float = Field(..., ge=0)
    sucursal_id: int = 1


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


@router.get("/estado", response_model=RespuestaData)
def estado(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    state = caja_service.obtener_estado_caja(db)
    return RespuestaData(data=state)


@router.post("/apertura", response_model=RespuestaData)
def apertura(
    data: AperturaRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    try:
        mov = caja_service.abrir_caja(db, data.monto_inicial, user.id, data.sucursal_id)
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
        sucursal_id=data.sucursal_id,
    )
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
    return RespuestaData(data={"id": mov.id, "monto": mov.monto}, message="Egreso registrado")


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
