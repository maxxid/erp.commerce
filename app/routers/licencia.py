"""Router de Licencia: activar, estado, generar (admin)."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timezone
from app.database import get_db
from app.auth.dependencies import require_role
from app.models.licencia import Licencia
from app.models.usuario import Usuario
from app.schemas.common import RespuestaBase, RespuestaData, RespuestaLista
from app.services import licencia_service

router = APIRouter(prefix="/api/licencia", tags=["Licencia"])


class ActivarRequest(BaseModel):
    clave: str = Field(..., min_length=10)


class GenerarRequest(BaseModel):
    cliente: str = Field(..., min_length=1, max_length=200)
    machine_id: str = Field(..., min_length=1, max_length=200)
    dias: int = Field(default=30, ge=1, le=365)
    plan: str = Field(default="trial", max_length=50)


class ActivaRequest(BaseModel):
    """Estado que el cliente quiere dejar. Sin esto se invierte el actual."""
    activa: Optional[bool] = None


def _licencia_to_dict(l: Licencia) -> dict:
    exp = l.fecha_expiracion
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    dias = max(0, (exp - datetime.now(timezone.utc)).days) if exp else 0
    return {
        "id": l.id, "clave": l.clave, "cliente": l.cliente,
        "machine_id": l.machine_id,
        "plan": getattr(l, "plan", None) or "trial",
        "fecha_inicio": l.fecha_inicio.isoformat() if l.fecha_inicio else None,
        "fecha_expiracion": l.fecha_expiracion.isoformat() if l.fecha_expiracion else None,
        "dias_restantes": dias,
        "activa": l.activa,
    }


@router.get("/machine-id", response_model=RespuestaData)
def machine_id():
    """Devuelve el ID único de esta máquina."""
    mid = licencia_service.obtener_machine_id()
    return RespuestaData(data={"machine_id": mid}, message="ID de máquina")


@router.get("/estado", response_model=RespuestaData)
def estado(db: Session = Depends(get_db)):
    """Estado de la licencia actual. No requiere auth.

    Expone el plan y las features que habilita, más el uso de IA del mes, para
    que el frontend sepa qué mostrar/ocultar sin tener que preguntar por
    separado.
    """
    from app.services import planes_service
    from app.services.ia import registro as ia_registro
    from app.services.ia import limites as ia_limites

    lic = licencia_service.obtener_licencia_activa(db)
    valida = licencia_service.licencia_valida(db)
    plan = planes_service.plan_de(db)
    features = planes_service.features_de(db)
    cfg_ia = ia_registro.configuracion(db)

    base = {
        "plan": plan,
        "planes": planes_service.catalogo(),
        "features": features,
        "ia_disponible": bool(features.get("ia")) and cfg_ia["habilitada"],
        "ia_configurada": cfg_ia["habilitada"],
        "ia_uso": {
            "llamadas": ia_limites.leer(db)["llamadas"],
            "limite": planes_service.limite_ia_de(db),
        },
    }

    if not lic:
        return RespuestaData(
            data={**base, "tiene_licencia": False, "valida": False},
            message="Sin licencia activa"
        )
    exp = lic.fecha_expiracion
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    dias = max(0, (exp - datetime.now(timezone.utc)).days) if exp else 0
    return RespuestaData(
        data={
            **base,
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
    mid = licencia_service.obtener_machine_id()
    lic = licencia_service.activar_licencia(db, data.clave, mid)
    if not lic:
        raise HTTPException(status_code=400, detail="Clave inválida, ya utilizada, o no corresponde a esta máquina")
    exp = lic.fecha_expiracion
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    dias = max(0, (exp - datetime.now(timezone.utc)).days) if exp else 0
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
    resultado = licencia_service.crear_licencia(
        db, data.cliente, data.machine_id, data.dias, plan=data.plan
    )
    return RespuestaData(data=resultado, message=f"Licencia generada: {resultado['clave']}")


@router.get("/historial", response_model=RespuestaLista)
def historial(db: Session = Depends(get_db), user: Usuario = Depends(require_role("admin"))):
    """Historial de licencias generadas."""
    licencias = licencia_service.historial_licencias(db)
    data = [_licencia_to_dict(l) for l in licencias]
    return RespuestaLista(data=data, total=len(data), message=f"{len(data)} licencia(s)")


def _no_desactivar_la_unica(db: Session, lic: Licencia) -> None:
    """No se puede dejar a la app sin licencia.

    El login arranca pidiendo una licencia válida: si se desactiva la única de
    esta máquina, no queda nadie que pueda entrar para volver a activarla. Con
    esto, desactivar es para apagar una licencia vieja, no la que se está usando.

    Una licencia vencida ya no deja entrar a nadie, así que apagarla no empeora
    nada y queda libre.
    """
    exp = lic.fecha_expiracion
    if exp and exp.tzinfo is None:
        exp = exp.replace(tzinfo=timezone.utc)
    if exp and exp <= datetime.now(timezone.utc):
        return
    mid = licencia_service.obtener_machine_id()
    # Es la licencia de otro cliente: a esta máquina no la deja sin nada.
    if lic.machine_id and lic.machine_id != mid:
        return
    otras = (
        db.query(Licencia)
        .filter(
            Licencia.id != lic.id,
            Licencia.activa == True,
            or_(Licencia.machine_id == mid, Licencia.machine_id.is_(None)),
        )
        .count()
    )
    if otras == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "Es la única licencia vigente de esta máquina: desactivarla "
                "dejaría a todos sin poder entrar."
            ),
        )


@router.patch("/{licencia_id}/toggle", response_model=RespuestaData)
def alternar_activa(
    licencia_id: int,
    data: Optional[ActivaRequest] = None,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Activa/desactiva una licencia (solo admin).

    El botón "Desactivar" de la vista llamaba a esta ruta, que no existía: el
    `catch` se tragaba el 404 y la tabla mostraba "Inactiva" mientras en la base
    seguía activa.
    """
    lic = db.query(Licencia).filter(Licencia.id == licencia_id).first()
    if not lic:
        raise HTTPException(status_code=404, detail="Licencia no encontrada")
    activa = data.activa if data and data.activa is not None else not lic.activa
    if not activa:
        _no_desactivar_la_unica(db, lic)
    lic.activa = bool(activa)
    db.commit()
    db.refresh(lic)
    return RespuestaData(
        data=_licencia_to_dict(lic),
        message=f"Licencia {lic.clave} {'activada' if activa else 'desactivada'}",
    )
