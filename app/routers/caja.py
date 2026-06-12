"""Router de Caja: apertura, cierre, estado, movimientos."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from app.database import get_db
from app.services import caja_service
from app.schemas.common import RespuestaData, RespuestaLista
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario

router = APIRouter(prefix="/api/caja", tags=["Caja"])


class AperturaRequest(BaseModel):
    monto_inicial: float = Field(..., ge=0)
    sucursal_id: int = 1


class CierreRequest(BaseModel):
    monto_real: float = Field(..., ge=0)
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
    """Estado actual de la caja: abierta/cerrada, saldo."""
    state = caja_service.obtener_estado_caja(db)
    return RespuestaData(data=state)


@router.post("/apertura", response_model=RespuestaData)
def apertura(
    data: AperturaRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Abre la caja con un monto inicial."""
    try:
        mov = caja_service.abrir_caja(db, data.monto_inicial, user.id, data.sucursal_id)
        return RespuestaData(
            data={"id": mov.id, "monto": mov.monto, "tipo": mov.tipo},
            message="Caja abierta",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/cierre", response_model=RespuestaData)
def cierre(
    data: CierreRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Cierra la caja con arqueo del monto real."""
    try:
        mov, esperado, diferencia = caja_service.cerrar_caja(
            db, data.monto_real, user.id, data.sucursal_id
        )
        return RespuestaData(
            data={
                "id": mov.id,
                "monto_real": data.monto_real,
                "saldo_esperado": esperado,
                "diferencia": diferencia,
            },
            message=f"Caja cerrada. Diferencia: ${diferencia:,.2f}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ingreso", response_model=RespuestaData)
def ingreso(
    data: MovimientoRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "cajero")),
):
    """Registra un ingreso extra de dinero."""
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
    """Registra un egreso/retiro de dinero."""
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
    """Historial de movimientos de caja."""
    movs, total = caja_service.listar_movimientos(db, page=page, page_size=page_size)
    return RespuestaLista(
        data=movs, total=total, page=page, page_size=page_size,
        message=f"{total} movimiento(s)"
    )
