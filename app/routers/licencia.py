"""Router de Licencia: activar, estado, generar (admin)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.usuario import Usuario
from app.schemas.common import RespuestaBase, RespuestaData, RespuestaLista
from app.services import licencia_service

router = APIRouter(prefix="/api/licencia", tags=["Licencia"])


class ActivarRequest(BaseModel):
    clave: str = Field(..., min_length=10)


class GenerarRequest(BaseModel):
    cliente: str = Field(..., min_length=1, max_length=200)
    dias: int = Field(default=30, ge=1, le=365)


@router.get("/estado", response_model=RespuestaData)
def estado(db: Session = Depends(get_db)):
    """Estado de la licencia actual. No requiere auth."""
    lic = licencia_service.obtener_licencia_activa(db)
    valida = licencia_service.licencia_valida(db)
    if not lic:
        return RespuestaData(
            data={"tiene_licencia": False, "valida": False},
            message="Sin licencia activa"
        )
    exp = lic.fecha_expiracion
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    dias = max(0, (exp - datetime.now(timezone.utc)).days) if exp else 0
    return RespuestaData(
        data={
            "tiene_licencia": True,
            "valida": valida,
            "cliente": lic.cliente,
            "fecha_expiracion": lic.fecha_expiracion.isoformat() if lic.fecha_expiracion else None,
            "dias_restantes": dias,
        },
        message="Licencia válida" if valida else "Licencia expirada"
    )


@router.post("/activar", response_model=RespuestaData)
def activar(data: ActivarRequest, db: Session = Depends(get_db)):
    """Activa una licencia con la clave proporcionada. No requiere auth."""
    lic = licencia_service.activar_licencia(db, data.clave)
    if not lic:
        raise HTTPException(status_code=400, detail="Clave inválida o ya utilizada")
    dias = max(0, (lic.fecha_expiracion - datetime.now(timezone.utc)).days)
    return RespuestaData(
        data={
            "cliente": lic.cliente,
            "fecha_expiracion": lic.fecha_expiracion.isoformat(),
            "dias_restantes": dias,
        },
        message=f"Licencia activada para {lic.cliente}"
    )


@router.post("/generar", response_model=RespuestaData)
def generar(data: GenerarRequest, db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin"))):
    """Genera una nueva clave de licencia (solo admin)."""
    resultado = licencia_service.crear_licencia(db, data.cliente, data.dias)
    return RespuestaData(data=resultado, message=f"Licencia generada: {resultado['clave']}")


@router.get("/historial", response_model=RespuestaLista)
def historial(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin"))):
    """Historial de licencias generadas."""
    licencias = licencia_service.historial_licencias(db)
    data = [
        {
            "id": l.id, "clave": l.clave, "cliente": l.cliente,
            "fecha_inicio": l.fecha_inicio.isoformat() if l.fecha_inicio else None,
            "fecha_expiracion": l.fecha_expiracion.isoformat() if l.fecha_expiracion else None,
            "activa": l.activa,
        }
        for l in licencias
    ]
    return RespuestaLista(data=data, total=len(data), message=f"{len(data)} licencia(s)")
