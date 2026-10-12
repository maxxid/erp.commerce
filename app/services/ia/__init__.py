"""Capa de IA/LLM de ApexERP.

Uso típico desde una feature:

    from app.services import ia

    resp = ia.completar(db, sistema=..., usuario=..., como_json=True)
    datos = ia.extraer_json(resp.texto)

`completar()` aplica habilitado/deshabilitado, límite mensual y registro de
uso. Las features no instancian proveedores a mano.
"""

from app.services.ia.proveedor import (
    ErrorIA,
    ErrorProveedor,
    IADeshabilitada,
    IARespuesta,
    LimiteAgotado,
    ProveedorIA,
)
from app.services.ia.openai_compat import extraer_json
from app.services.ia.registro import (
    PROVEEDORES,
    completar,
    configuracion,
    obtener,
    probar,
)

__all__ = [
    "ErrorIA",
    "ErrorProveedor",
    "IADeshabilitada",
    "IARespuesta",
    "LimiteAgotado",
    "ProveedorIA",
    "PROVEEDORES",
    "completar",
    "configuracion",
    "extraer_json",
    "obtener",
    "probar",
]
