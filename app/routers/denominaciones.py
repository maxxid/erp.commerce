"""Router de denominaciones: configuración del contador de efectivo de caja."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaData, RespuestaLista
from app.schemas.denominacion import DenominacionCreate, DenominacionOut, DenominacionUpdate
from app.services import denominacion_service as service


router = APIRouter(prefix="/api/denominaciones", tags=["Denominaciones"])


@router.get("", response_model=RespuestaLista)
def listar(
    incluir_inactivas: bool = Query(False, description="Incluye las denominaciones deshabilitadas"),
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Denominaciones de efectivo. Lectura libre para cualquier usuario autenticado
    porque el contador de caja lo usan también los cajeros."""
    denoms = service.listar(db, incluir_inactivas=incluir_inactivas)
    return RespuestaLista(
        data=[DenominacionOut.model_validate(d).model_dump() for d in denoms],
        total=len(denoms), page=1, page_size=max(len(denoms), 1),
    )


@router.post("", response_model=RespuestaData)
def crear(
    data: DenominacionCreate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    try:
        den = service.crear(db, valor=data.valor, tipo=data.tipo, activo=data.activo)
        return RespuestaData(data=DenominacionOut.model_validate(den).model_dump(), message="Denominación creada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{den_id}", response_model=RespuestaData)
def editar(
    den_id: int,
    data: DenominacionUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    try:
        den = service.actualizar(db, den_id, data.model_dump(exclude_unset=True))
        return RespuestaData(data=DenominacionOut.model_validate(den).model_dump(), message="Denominación actualizada")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{den_id}", response_model=RespuestaData)
def eliminar(
    den_id: int,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    try:
        den = service.eliminar(db, den_id)
        return RespuestaData(
            data={"id": den.id, "valor": den.valor},
            message="Denominación eliminada",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/restaurar-defaults", response_model=RespuestaData)
def restaurar_defaults(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    total = service.restaurar_defaults(db)
    return RespuestaData(
        data={"total": total},
        message="Denominaciones restauradas a los valores por defecto",
    )
