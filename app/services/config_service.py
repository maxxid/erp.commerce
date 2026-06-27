"""Servicio de configuración del sistema.

Lee y escribe settings en la tabla `configuraciones`.
Las variables de entorno tienen prioridad sobre la DB.
"""

import os
from typing import Optional
from sqlalchemy.orm import Session
from app.models.configuracion import Configuracion


def get_config(db: Session, clave: str) -> Optional[str]:
    """Lee un valor de configuración de la DB."""
    cfg = db.query(Configuracion).filter(Configuracion.clave == clave).first()
    if not cfg:
        return None
    return cfg.valor_texto or cfg.valor


def get_config_int(db: Session, clave: str, default: int = 0) -> int:
    v = get_config(db, clave)
    if v is None:
        return default
    try:
        return int(v)
    except (ValueError, TypeError):
        return default


def set_config(db: Session, clave: str, valor: str, descripcion: str = ""):
    """Escribe o actualiza un valor de configuración."""
    cfg = db.query(Configuracion).filter(Configuracion.clave == clave).first()
    if cfg:
        if len(valor) > 450:
            cfg.valor_texto = valor
            cfg.valor = "[texto largo]"
        else:
            cfg.valor = valor
            cfg.valor_texto = None
        if descripcion:
            cfg.descripcion = descripcion
    else:
        if len(valor) > 450:
            cfg = Configuracion(clave=clave, valor="[texto largo]", valor_texto=valor, descripcion=descripcion)
        else:
            cfg = Configuracion(clave=clave, valor=valor, descripcion=descripcion)
        db.add(cfg)
    db.commit()


def get_afip_config(db: Session) -> dict:
    """Lee toda la configuración de AFIP desde la DB + entorno."""
    return {
        "mode": os.getenv("AFIP_MODE") or get_config(db, "afip_mode") or "testing",
        "cuit": os.getenv("AFIP_CUIT") or get_config(db, "afip_cuit") or "",
        "pto_vta": int(os.getenv("AFIP_PTO_VTA") or get_config(db, "afip_pto_vta") or "1"),
        "cert": get_config(db, "afip_cert") or "",
        "key": get_config(db, "afip_key") or "",
    }
