"""Router de Configuración del Sistema (Ajustes AFIP)."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.database import get_db
from app.schemas.common import RespuestaData
from app.auth.dependencies import get_current_user, require_role
from app.models.usuario import Usuario
from app.models.configuracion import Configuracion
from app.services.config_service import set_config, get_config
from app.services import auditoria_service

router = APIRouter(prefix="/api/config", tags=["Configuración"])


class ConfigUpdate(BaseModel):
    clave: str
    valor: str
    descripcion: str = ""


@router.get("/ajustes", response_model=RespuestaData)
def listar_ajustes(
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Lista todas las configuraciones del sistema."""
    configs = db.query(Configuracion).all()
    data = {
        c.clave: {
            "valor": c.valor_texto or c.valor,
            "descripcion": c.descripcion,
        }
        for c in configs
    }
    return RespuestaData(data=data)


@router.put("/ajustes", response_model=RespuestaData)
def actualizar_ajuste(
    data: ConfigUpdate,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Actualiza un valor de configuración."""
    valor_anterior = get_config(db, data.clave)
    set_config(db, data.clave, data.valor, data.descripcion)

    if data.clave == "telefono_dueño" and valor_anterior != data.valor:
        auditoria_service.registrar(db, user.id, "telefono_dueño_editado", None, None, {
            "clave": data.clave,
            "valor_anterior": valor_anterior,
            "valor_nuevo": data.valor,
        })

    return RespuestaData(data={"clave": data.clave, "valor": data.valor}, message=f"Configuración '{data.clave}' actualizada")


class SidebarBlock(BaseModel):
    type: str  # 'link' | 'separator' | 'subtitle'
    to: str | None = None
    text: str | None = None


class SidebarConfigRequest(BaseModel):
    blocks: list[dict]


@router.get("/sidebar", response_model=RespuestaData)
def get_sidebar_config(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Configuración del menú lateral (orden, separadores, subtítulos).

    La lee cualquier usuario autenticado para renderizar el sidebar. Si no hay
    configuración guardada, devuelve `blocks: null` y el frontend usa el orden
    por defecto.
    """
    import json
    val = get_config(db, "sidebar_config")
    blocks = None
    if val:
        try:
            blocks = json.loads(val)
        except (ValueError, TypeError):
            blocks = None
    return RespuestaData(data={"blocks": blocks})


@router.put("/sidebar", response_model=RespuestaData)
def set_sidebar_config(
    data: SidebarConfigRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin")),
):
    """Actualiza la configuración del menú lateral. Solo admin."""
    import json
    # Validar tipos básicos
    clean = []
    for b in data.blocks or []:
        t = b.get("type")
        if t not in ("link", "separator", "subtitle"):
            continue
        if t == "link" and not b.get("to"):
            continue
        if t == "subtitle":
            b = {"type": "subtitle", "text": (b.get("text") or "").strip()[:60]}
        else:
            b = {k: v for k, v in b.items() if k in ("type", "to")}
        clean.append(b)
    set_config(db, "sidebar_config", json.dumps(clean), "Configuración del menú lateral")
    return RespuestaData(data={"blocks": clean}, message="Menú lateral actualizado")


class PosConfigRequest(BaseModel):
    showStatsPanel: bool = True
    productViewMode: str = "grilla"
    enabledPaymentMethods: list[str] = []
    calculadoraAlcance: str = "pos-productos"
    calculadoraHistorial: int = 5


@router.get("/pos", response_model=RespuestaData)
def get_pos_config(
    db: Session = Depends(get_db),
    user: Usuario = Depends(get_current_user),
):
    """Obtiene la configuración de preferencias del POS.

    La lee cualquier usuario autenticado (incluso cajero): es la única forma de
    que el POS muestre los mismos medios de pago que marcó el dueño en Ajustes.
    """
    configs = db.query(Configuracion).filter(
        Configuracion.clave.in_([
            "pos_show_stats_panel",
            "pos_product_view_mode",
            "pos_enabled_payment_methods",
            "pos_calculadora_alcance",
            "pos_calculadora_historial"
        ])
    ).all()
    # Claves en camelCase, las mismas que espera el PUT: antes devolvía
    # snake_case y el frontend (que lee enabledPaymentMethods) nunca veía lo
    # guardado, por eso el toggle "no hacía nada".
    data = {}
    for c in configs:
        valor = c.valor_texto or c.valor
        if c.clave == "pos_enabled_payment_methods":
            import json
            try:
                data["enabledPaymentMethods"] = json.loads(valor or "[]")
            except (ValueError, TypeError):
                data["enabledPaymentMethods"] = []
        elif c.clave == "pos_show_stats_panel":
            data["showStatsPanel"] = str(valor).lower() == "true"
        elif c.clave == "pos_product_view_mode":
            data["productViewMode"] = valor or "grilla"
        elif c.clave == "pos_calculadora_alcance":
            data["calculadoraAlcance"] = valor or "pos-productos"
        elif c.clave == "pos_calculadora_historial":
            try:
                data["calculadoraHistorial"] = int(valor)
            except (TypeError, ValueError):
                data["calculadoraHistorial"] = 5
    # Defaults. El panel lateral arranca **cerrado** (decisión del dueño:
    # un KPI viejo o vacío en el POS se lee como "algo se rompió").
    defaults = {
        "showStatsPanel": False,
        "productViewMode": "grilla",
        "enabledPaymentMethods": [
            "efectivo", "transferencia", "mercadopago_qr",
            "qr_interop", "mercadopago_pos", "smartpoint", "cta_corriente"
        ],
        "calculadoraAlcance": "pos-productos",
        "calculadoraHistorial": 5,
    }
    for k, v in defaults.items():
        data.setdefault(k, v)
    return RespuestaData(data=data)


@router.put("/pos", response_model=RespuestaData)
def set_pos_config(
    data: PosConfigRequest,
    db: Session = Depends(get_db),
    user: Usuario = Depends(require_role("admin", "encargado")),
):
    """Actualiza la configuración de preferencias del POS."""
    import json
    set_config(db, "pos_show_stats_panel", str(data.showStatsPanel).lower(),
               "Mostrar panel lateral derecho (mini dashboard) en POS")
    set_config(db, "pos_product_view_mode", data.productViewMode,
               "Vista de productos por defecto en POS: grilla | lista")
    set_config(db, "pos_enabled_payment_methods", json.dumps(data.enabledPaymentMethods),
               "Medios de pago habilitados en POS (JSON array)")
    set_config(db, "pos_calculadora_alcance", data.calculadoraAlcance,
               "Dónde se muestra la calculadora flotante: global | pos-productos")
    set_config(db, "pos_calculadora_historial", str(data.calculadoraHistorial),
               "Cuántos cálculos guarda el historial de la calculadora flotante")
    return RespuestaData(
        data={
            "showStatsPanel": data.showStatsPanel,
            "productViewMode": data.productViewMode,
            "enabledPaymentMethods": data.enabledPaymentMethods,
            "calculadoraAlcance": data.calculadoraAlcance,
            "calculadoraHistorial": data.calculadoraHistorial
        },
        message="Configuración POS actualizada"
    )
