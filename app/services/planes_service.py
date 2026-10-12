"""Planes de servicio y features que habilita cada uno.

Es el lugar único donde se define qué incluye cada plan. Agregar una feature
nueva es agregarla al catálogo y usar `requiere_feature("...")` en el router.

El plan vive en `licencias.plan`. Las licencias creadas por el admin eligen
plan explícitamente; el default del modelo es "trial" (sin IA) para no
regalar features si alguien crea una licencia sin setear plan.
"""

from typing import Optional

from sqlalchemy.orm import Session

from app.services import licencia_service

PLAN_DEFECTO = "trial"

FEATURES = ("ia", "sectores")

PLANES = {
    "trial": {
        "nombre": "Prueba",
        "descripcion": "30 días con features básicas",
        "features": {"ia": False, "sectores": True},
    },
    "basico": {
        "nombre": "Básico",
        "descripcion": "Gestión completa, sin IA",
        "features": {"ia": False, "sectores": True},
    },
    "pro": {
        "nombre": "Pro",
        "descripcion": "Con inteligencia artificial",
        "features": {"ia": True, "sectores": True},
    },
    "enterprise": {
        "nombre": "Enterprise",
        "descripcion": "Sin límites y soporte dedicado",
        "features": {"ia": True, "sectores": True},
    },
}

# Límite mensual de llamadas de IA por defecto cuando el plan no fija uno.
LIMITE_IA_DEFECTO = 1000


def catalogo() -> list:
    """Lista de planes para el selector de Ajustes/Licencias."""
    return [
        {"id": pid, "nombre": p["nombre"], "descripcion": p["descripcion"],
         "features": dict(p["features"])}
        for pid, p in PLANES.items()
    ]


def _plan_de(lic) -> str:
    if lic is None:
        return PLAN_DEFECTO
    plan = (getattr(lic, "plan", None) or "").strip().lower()
    return plan if plan in PLANES else PLAN_DEFECTO


def plan_de(db: Session) -> str:
    """Plan vigente, o el default si no hay licencia."""
    if not licencia_service.licencia_valida(db):
        return PLAN_DEFECTO
    return _plan_de(licencia_service.obtener_licencia_activa(db))


def features_de(db: Session) -> dict:
    """Features habilitadas por el plan vigente."""
    return dict(PLANES[plan_de(db)]["features"])


def tiene_feature(db: Session, feature: str) -> bool:
    return bool(features_de(db).get(feature, False))


def requiere_licencia_valida(db: Session) -> bool:
    return licencia_service.licencia_valida(db)


def limite_ia_de(db: Session) -> Optional[int]:
    """Límite mensual de llamadas de IA.

    Precedencia: licencia (override por cliente) > configuración (operador) >
    default. `None` o `<= 0` significa sin límite.
    """
    if licencia_service.licencia_valida(db):
        lic = licencia_service.obtener_licencia_activa(db)
        if lic is not None and lic.limite_ia_mes is not None:
            return lic.limite_ia_mes

    from app.services import config_service
    from app.services.ia.registro import CLAVE_LIMITE_MES, LIMITE_MES_DEFECTO

    crudo = config_service.get_config(db, CLAVE_LIMITE_MES)
    if crudo is None or str(crudo).strip() == "":
        return LIMITE_MES_DEFECTO
    try:
        return int(crudo)
    except (TypeError, ValueError):
        return LIMITE_MES_DEFECTO
