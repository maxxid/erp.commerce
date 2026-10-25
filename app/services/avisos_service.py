"""Aviso proactivo por Telegram de los productos bajo mínimo.

Una vez por día, a la hora que se configure en Ajustes, el ERP manda al canal
de Telegram el mismo listado que muestra la campana del header: producto,
stock contra mínimo, proveedor de la última compra y precios de compra y
venta. Si no hay nada bajo mínimo no se manda nada, y se vuelve a mirar en
el próximo chequeo (cada 10 minutos), así un producto que se queda sin stock
a la tarde igual avisa ese mismo día.

La configuración se lee en cada chequeo y no al arrancar el servicio: así se
puede cambiar la hora o el token en Ajustes sin reiniciar nada.
"""

from datetime import datetime, timedelta, timezone
from html import escape

import requests

from app.database import SessionLocal
from app.models.usuario import Usuario
from app.services import config_service, auditoria_service
from app.services.notificaciones_service import fila_producto, mensaje_bajo
from app.services.stock_service import productos_stock_bajo, detalle_reposicion

TZ_AR = timezone(timedelta(hours=-3))
TELEGRAM_SEND_URL = "https://api.telegram.org/bot{token}/sendMessage"
CHEQUEO_CADA_MIN = 10


def config_aviso(db) -> dict:
    """Config del aviso, leída ahora mismo (no cacheada al arrancar)."""
    return {
        "habilitado": (config_service.get_config(db, "stock_aviso_enabled") or "").lower() == "true",
        "hora": (config_service.get_config(db, "stock_aviso_hora") or "09:00").strip(),
        "token": (config_service.get_config(db, "telegram_bot_token") or "").strip(),
        "chat_id": (config_service.get_config(db, "telegram_chat_id") or "").strip(),
    }


def mensaje_stock_bajo(db) -> str:
    """Texto del aviso, con las mismas palabras que la campana.

    Devuelve vacío si no hay ningún producto bajo mínimo: mejor no joder
    que mandar un "todo bien" todos los días.
    """
    bajos = productos_stock_bajo(db)
    if not bajos:
        return ""
    detalle = detalle_reposicion(db, bajos)
    hoy = datetime.now(TZ_AR).strftime("%d/%m/%Y")
    lineas = [f"🔔 <b>Stock bajo — {hoy}</b> ({len(bajos)} producto(s))", ""]
    for p in bajos:
        fila = fila_producto(p, detalle)
        lineas.append(f"• <b>{escape(str(fila['nombre']))}</b>")
        lineas.append(f"  {escape(mensaje_bajo(fila))}")
    lineas.append("")
    lineas.append("Abrí ApexERP → Productos → Stock bajo para reponer.")
    return "\n".join(lineas)


def enviar_a_telegram(token: str, chat_id: str, texto: str) -> tuple:
    """Manda el mensaje. Devuelve (ok, detalle) para poder mostrarlo en Ajustes."""
    try:
        r = requests.post(
            TELEGRAM_SEND_URL.format(token=token),
            json={
                "chat_id": chat_id,
                "text": texto,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=20,
        )
    except requests.RequestException as e:
        return False, f"Sin conexión con Telegram: {e}"
    try:
        datos = r.json()
    except ValueError:
        datos = {}
    if r.ok and datos.get("ok"):
        return True, "Mensaje enviado"
    return False, datos.get("description") or f"HTTP {r.status_code}"


def _hora_objetivo(ahora: datetime, hora_cfg: str):
    """Hora de hoy a la que hay que avisar, o None si la config está rota."""
    partes = hora_cfg.split(":")
    try:
        h, m = int(partes[0]), int(partes[1]) if len(partes) > 1 else 0
        return ahora.replace(hour=h, minute=m, second=0, microsecond=0)
    except (ValueError, IndexError):
        return None


def chequear_aviso_diario():
    """El job del scheduler: envía el resumen diario si la caja ya está cerrada."""
    db = SessionLocal()
    try:
        cfg = config_aviso(db)
        if not cfg["habilitado"] or not cfg["token"] or not cfg["chat_id"]:
            # igual intentar si el bot interactivo está activo
            bot_on = (config_service.get_config(db, "telegram_bot_interactivo") or "").lower() == "true"
            if not bot_on:
                return
        ahora = datetime.now(TZ_AR)
        objetivo = _hora_objetivo(ahora, cfg.get("hora", "21:00") or "21:00")
        if objetivo is None or ahora < objetivo:
            return
        # Solo si la caja está cerrada (sesión terminada)
        try:
            from app.services import caja_service
            if caja_service.caja_abierta(db):
                return
        except Exception:
            pass
        # Delegar en generar_resumen_diario (idempotente por fecha)
        try:
            from app.services import caja_service
            caja_service.generar_resumen_diario(db)
        except Exception as e:
            print(f"[Avisos] Error generando resumen diario: {e}")
    finally:
        db.close()


def probar_envio(db, user_id=None) -> tuple:
    """Manda un mensaje de prueba ahora, sin esperar la hora ni el switch."""
    cfg = config_aviso(db)
    if not cfg["token"] or not cfg["chat_id"]:
        return False, "Falta el token del bot o el chat ID en Ajustes → Avisos"
    texto = "✅ <b>ApexERP</b>: el aviso de stock bajo está conectado."
    ok, detalle = enviar_a_telegram(cfg["token"], cfg["chat_id"], texto)
    auditoria_service.registrar(
        db, user_id, "aviso_stock_telegram_prueba", None, None,
        {"resultado": "enviado" if ok else "error", "detalle": detalle},
    )
    return ok, detalle
