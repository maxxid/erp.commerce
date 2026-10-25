"""Salud de los respaldos: que existan, que abran y que alguien se entere.

Un respaldo automático que nadie chequea es un espejismo: si el scheduler se
apaga, si R2 rechaza las credenciales o si la base se corrompe, se descubre
justo el día que menos sobra. Este servicio mira eso cada 30 minutos y avisa
por Telegram (el mismo bot del aviso de stock bajo de Ajustes):

- ¿hay respaldo local de menos de 24 h? ¿y el último abre?
- ¿R2 (si está configurado) tiene los respaldos frescos?
- ¿la réplica en vivo de la Fase G (Litestream) sigue avanzando? Si se frena,
  el día que se caiga la principal la secundaria restauraría datos viejos
- y todos los días manda un "todo bien" con el último respaldo: es la única
  manera de saber que el canal de avisos anda, no sólo cuando algo falla.

Los avisos llevan una guarda de 12 h por tipo para no repetir el mismo
reclamo cada vuelta. Si no hay token de Telegram no se manda nada, pero el
chequeo corre igual y lo deja impreso en el log.
"""

import gzip
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone
from html import escape
from typing import List, Optional

from app.config import settings
from app.database import SessionLocal
from app.services import avisos_service, backup_service, config_service

TZ_AR = timezone(timedelta(hours=-3))
MAX_H_SIN_BACKUP = 24
CHEQUEO_CADA_MIN = 30
HORA_RESUMEN = 21        # hora Argentina del resumen diario "todo bien"
COOLDOWN_AVISO_H = 12

# Cuánto puede estar quieta la réplica en vivo antes de considerarla rota
# (Fase G). Litestream sube archivos cada pocos segundos mientras la base
# cambia y un snapshot cada 15 minutos aunque no cambie nada: 45 minutos de
# silencio ya no es "está tranquila la noche", es "se cayó el servicio".
MAX_MIN_SIN_REPLICA = 45


def _a_utc(texto: str) -> datetime:
    """Un ISO guardado a UTC aware.

    Los respaldos locales guardan hora **naive** del servidor (que es UTC en
    producción) y R2 devuelve hora con zona: mezclar los dos tipos tira
    TypeError, así que todo pasa por acá.
    """
    d = datetime.fromisoformat(texto)
    if d.tzinfo is None:
        d = d.replace(tzinfo=timezone.utc)
    return d.astimezone(timezone.utc)


def respaldo_sano(nombre: str) -> bool:
    """¿El .gz se descomprime y la base que tiene adentro pasa integrity_check?

    No sirve contar archivos: un respaldo que no se puede abrir no es un
    respaldo, y la única forma de saberlo es abrirlo.
    """
    ruta = os.path.join(backup_service.BACKUP_DIR, nombre)
    temporal = None
    try:
        with gzip.open(ruta, "rb") as src, \
                tempfile.NamedTemporaryFile(delete=False, suffix=".db") as dst:
            temporal = dst.name
            shutil.copyfileobj(src, dst)
        conn = sqlite3.connect(temporal)
        try:
            fila = conn.execute("PRAGMA integrity_check").fetchone()
        finally:
            conn.close()
        return bool(fila) and fila[0] == "ok"
    except Exception:
        return False
    finally:
        if temporal and os.path.exists(temporal):
            os.remove(temporal)


def problemas_de_respaldo(db, ahora: Optional[datetime] = None) -> List[str]:
    """Lo que está mal con los respaldos. Lista vacía = todo bien."""
    ahora = ahora or datetime.now(timezone.utc)
    fallos: List[str] = []

    locales = backup_service.listar_backups_locales()
    if not locales:
        fallos.append("No hay ningún respaldo local.")
    else:
        ultimo = locales[0]
        edad_h = (ahora - _a_utc(ultimo["fecha"])).total_seconds() / 3600
        if edad_h > MAX_H_SIN_BACKUP:
            fallos.append(
                f"El último respaldo local tiene {edad_h:.0f} h "
                f"(debería ser menos de {MAX_H_SIN_BACKUP} h)."
            )
        if not respaldo_sano(ultimo["nombre"]):
            fallos.append("El último respaldo local no abre: la copia está dañada.")

    if backup_service._get_r2_config(db):
        remotos = backup_service.listar_backups_r2(db)
        if not remotos:
            fallos.append("La nube (R2) está configurada pero no tiene ningún respaldo.")
        else:
            edad_r2 = (ahora - _a_utc(remotos[0]["fecha"])).total_seconds() / 3600
            if edad_r2 > MAX_H_SIN_BACKUP:
                fallos.append(f"El último respaldo en la nube tiene {edad_r2:.0f} h.")

    return fallos


def problemas_de_replica(db, ahora: Optional[datetime] = None) -> List[str]:
    """Chequea la réplica en vivo de la Fase G (Litestream → R2).

    Si dejó de avanzar, el día que se caiga la principal la secundaria va a
    restaurar una foto vieja: es mucho mejor enterarse ahora, con un aviso,
    que en el momento del salto. Sólo se chequea si el servidor tiene la
    réplica prendida (`LITESTREAM_HABILITADO`).
    """
    if not settings.LITESTREAM_HABILITADO:
        return []
    if not backup_service._get_r2_config(db):
        return ["La réplica en vivo no puede andar: la nube (R2) no está configurada."]
    objetos = backup_service.listar_replica_r2(db)
    if not objetos:
        return ["La réplica en vivo (Litestream) no tiene ningún archivo en la nube."]
    ahora = ahora or datetime.now(timezone.utc)
    edad_min = (ahora - _a_utc(objetos[0]["fecha"])).total_seconds() / 60
    if edad_min > MAX_MIN_SIN_REPLICA:
        return [
            f"La réplica en vivo lleva {edad_min:.0f} min sin avanzar "
            f"(debería moverse cada pocos segundos)."
        ]
    return []


def minutos_de_replica(db, ahora: Optional[datetime] = None) -> Optional[float]:
    """Minutos desde el último movimiento de la réplica en vivo.

    `None` = no corresponde chequear (este servidor no tiene la réplica
    prendida o no hay R2); para el resumen diario simplemente no se menciona.
    """
    if not settings.LITESTREAM_HABILITADO or not backup_service._get_r2_config(db):
        return None
    objetos = backup_service.listar_replica_r2(db)
    if not objetos:
        return None
    ahora = ahora or datetime.now(timezone.utc)
    return (ahora - _a_utc(objetos[0]["fecha"])).total_seconds() / 60


def _etiqueta(dt_utc: datetime) -> str:
    """'hoy 20:45' / 'ayer 04:10' / '22/10 04:10' en hora del negocio."""
    d = dt_utc.astimezone(TZ_AR)
    hoy = datetime.now(TZ_AR).date()
    if d.date() == hoy:
        return f"hoy {d.strftime('%H:%M')}"
    if d.date() == hoy - timedelta(days=1):
        return f"ayer {d.strftime('%H:%M')}"
    return d.strftime("%d/%m %H:%M")


def mensaje_de_alerta(fallos: List[str], ahora: datetime) -> str:
    fecha = ahora.astimezone(TZ_AR).strftime("%d/%m %H:%M")
    lineas = [f"⚠️ <b>ApexERP: hay que revisar los respaldos</b> ({fecha})", ""]
    for f in fallos:
        lineas.append(f"• {escape(f)}")
    lineas.append("")
    lineas.append(
        "Si no se arregla hoy, es posible que una caída grande cueste "
        "recuperar los datos. Entrá a ApexERP → Ajustes → Avisos."
    )
    return "\n".join(lineas)


def mensaje_resumen(db, ahora: datetime) -> str:
    """El 'todo bien' del día, con el estado real de los respaldos."""
    fecha = ahora.astimezone(TZ_AR).strftime("%d/%m %H:%M")
    lineas = [f"✅ <b>ApexERP — todo bien</b> ({fecha})"]

    locales = backup_service.listar_backups_locales()
    if locales:
        ultimo = locales[0]
        peso = f"{ultimo['size'] / 1024:.0f} KB"
        lineas.append(f"• Último respaldo: {_etiqueta(_a_utc(ultimo['fecha']))} ({peso})")
    else:
        lineas.append("• Último respaldo: no hay ninguno")

    if backup_service._get_r2_config(db):
        remotos = backup_service.listar_backups_r2(db)
        if remotos:
            lineas.append(f"• En la nube (R2): sí, último de {_etiqueta(_a_utc(remotos[0]['fecha']))}")
        else:
            lineas.append("• En la nube (R2): no hay ningún respaldo")
    else:
        lineas.append("• En la nube (R2): sin configurar (el respaldo vive sólo en este servidor)")

    minutos = minutos_de_replica(db, ahora)
    if minutos is not None:
        lineas.append(f"• Réplica en vivo (continuidad): al día, hace {minutos:.0f} min")

    sano = bool(locales) and respaldo_sano(locales[0]["nombre"])
    lineas.append(f"• Base de datos legible: {'sí' if sano else 'no la pude abrir'}")
    return "\n".join(lineas)


def _avisar_si_hace_falta(db, tipo: str, texto: str, ahora: datetime) -> bool:
    """Manda el aviso si hay Telegram configurado y no se mandó recién."""
    cfg = avisos_service.config_aviso(db)
    if not cfg["token"] or not cfg["chat_id"]:
        return False
    clave = f"alerta_salud_ultimo_{tipo}"
    ultimo = config_service.get_config(db, clave)
    if ultimo:
        try:
            if (ahora - _a_utc(ultimo)).total_seconds() < COOLDOWN_AVISO_H * 3600:
                return False
        except ValueError:
            pass  # un valor viejo o roto no frena un aviso nuevo
    ok, detalle = avisos_service.enviar_a_telegram(cfg["token"], cfg["chat_id"], texto)
    if ok:
        config_service.set_config(
            db, clave, ahora.isoformat(),
            "Último aviso de salud de respaldos mandado por Telegram",
        )
    else:
        print(f"[Salud] Telegram rechazó el aviso: {detalle}")
    return ok


def _resumen_pendiente(db, ahora_ar: datetime) -> bool:
    if (config_service.get_config(db, "alerta_resumen_diario") or "true").lower() == "false":
        return False
    if ahora_ar.hour < HORA_RESUMEN:
        return False
    return config_service.get_config(db, "alerta_salud_resumen_dia") != ahora_ar.strftime("%Y-%m-%d")


def chequear_salud(ahora: Optional[datetime] = None):
    """El job del scheduler: mira los respaldos y avisa si algo falla.

    Con `ahora` se puede simular el reloj desde los tests.
    """
    db = SessionLocal()
    try:
        ahora = ahora or datetime.now(timezone.utc)
        fallos = problemas_de_respaldo(db, ahora) + problemas_de_replica(db, ahora)
        if fallos:
            _avisar_si_hace_falta(db, "respaldo", mensaje_de_alerta(fallos, ahora), ahora)
            return
        ahora_ar = ahora.astimezone(TZ_AR)
        if _resumen_pendiente(db, ahora_ar) and \
                _avisar_si_hace_falta(db, "resumen", mensaje_resumen(db, ahora), ahora):
            config_service.set_config(
                db, "alerta_salud_resumen_dia", ahora_ar.strftime("%Y-%m-%d"),
                "Último día en que se mandó el resumen diario de salud",
            )
    finally:
        db.close()
