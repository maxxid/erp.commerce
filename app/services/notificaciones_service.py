"""Servicio de Notificaciones: genera los avisos y maneja su lectura.

La campana del header no inventa avisos: se calculan desde el estado real
del sistema (stock bajo, caja abierta, lotes por vencer, licencia por vencer).
Cada aviso se guarda una sola vez por `clave` (tipo + fecha), así que abrir
la app diez veces no llena la campana de duplicados.

Dos comportamientos se eligen en Ajustes y se guardan en `configuraciones`:

- `avisos_lectura`: "usuario" (default) o "global". En modo global la lectura
  se guarda con usuario_id NULL y le sirve a todos; en modo usuario cada uno
  tiene la suya y no le borra el aviso al resto.
- `avisos_granularidad`: "tipo" (default, un aviso por tipo por día) o
  "producto" (una fila por producto para stock bajo, que es cuando conviene
  marcarlos de a uno).
"""

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.licencia import Licencia
from app.models.notificacion import Notificacion, NotificacionLeida
from app.models.producto import Producto
from app.models.venta import Venta
from app.services import caja_service, config_service, licencia_service, lote_service, stock_service

MODO_LECTURA_DEFAULT = "usuario"
MODO_GRANULARIDAD_DEFAULT = "tipo"
DIAS_PARA_BORRAR = 30
DIAS_LICENCIA_AVISO = 7


def modo_lectura(db: Session) -> str:
    valor = config_service.get_config(db, "avisos_lectura")
    return valor if valor in ("usuario", "global") else MODO_LECTURA_DEFAULT


def modo_granularidad(db: Session) -> str:
    valor = config_service.get_config(db, "avisos_granularidad")
    return valor if valor in ("tipo", "producto") else MODO_GRANULARIDAD_DEFAULT


def _hoy_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _fila_producto(p: Producto, detalle: dict) -> dict:
    d = detalle.get(p.id, {})
    return {
        "id": p.id,
        "nombre": p.nombre,
        "codigo_barras": p.codigo_barras,
        "stock_actual": float(p.stock_actual or 0),
        "stock_minimo": float(p.stock_minimo or 0),
        "proveedor": d.get("proveedor"),
        "precio_compra": d.get("precio_compra", 0.0),
        "precio_venta": d.get("precio_venta", 0.0),
    }


def _mensaje_bajo(fila: dict) -> str:
    """"Stock 2 / mínimo 8 — Proveedor: Carrefour — compra $150 — venta $250"."""
    partes = [
        f"Stock {fila['stock_actual']:g} / mínimo {fila['stock_minimo']:g}",
    ]
    if fila.get("proveedor"):
        partes.append(f"Proveedor: {fila['proveedor']}")
    if fila.get("precio_compra", 0) > 0:
        partes.append(f"compra ${fila['precio_compra']:,.2f}")
    if fila.get("precio_venta", 0) > 0:
        partes.append(f"venta ${fila['precio_venta']:,.2f}")
    return " — ".join(partes)


def _avisos_actuales(db: Session) -> List[dict]:
    """Avisos vigentes hoy, calculados del estado real del sistema."""
    hoy = _hoy_utc()
    avisos: List[dict] = []

    # Stock bajo: el aviso más importante, con de dónde se repone.
    bajos = stock_service.productos_stock_bajo(db)
    if bajos:
        detalle = stock_service.detalle_reposicion(db, bajos)
        filas = [_fila_producto(p, detalle) for p in bajos]
        if modo_granularidad(db) == "producto":
            for fila in filas:
                avisos.append({
                    "tipo": "stock_bajo",
                    "nivel": "warning",
                    "titulo": fila["nombre"],
                    "mensaje": _mensaje_bajo(fila),
                    "data": fila,
                    "clave": f"stock_bajo:{fila['id']}:{hoy}",
                })
        else:
            avisos.append({
                "tipo": "stock_bajo",
                "nivel": "warning",
                "titulo": "Stock bajo",
                "mensaje": f"{len(filas)} producto(s) bajo stock mínimo",
                "data": {"productos": filas},
                "clave": f"stock_bajo:{hoy}",
            })

    # Sin stock: controlan stock y quedaron en cero.
    agotados = stock_service.filtro_agotado(db.query(Producto)).count()
    if agotados > 0:
        avisos.append({
            "tipo": "sin_stock",
            "nivel": "danger",
            "titulo": "Sin stock",
            "mensaje": f"{agotados} producto(s) agotados",
            "data": {"total": agotados},
            "clave": f"sin_stock:{hoy}",
        })

    # Caja abierta desde ayer o de hoy sin cierre total.
    if caja_service.caja_abierta(db):
        avisos.append({
            "tipo": "caja_abierta",
            "nivel": "warning",
            "titulo": "Caja abierta",
            "mensaje": "Hay una caja abierta sin cierre total",
            "data": {},
            "clave": f"caja_abierta:{hoy}",
        })

    # Licencia por vencer.
    lic = licencia_service.obtener_licencia_activa(db)
    if lic and lic.fecha_expiracion:
        exp = lic.fecha_expiracion
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        dias = (exp - datetime.now(timezone.utc)).days
        if dias <= DIAS_LICENCIA_AVISO:
            avisos.append({
                "tipo": "licencia",
                "nivel": "danger" if dias <= 3 else "warning",
                "titulo": "Licencia por vencer",
                "mensaje": f"La licencia vence en {max(0, dias)} día(s)",
                "data": {"dias": dias},
                "clave": f"licencia:{hoy}",
            })

    # Lotes: primero lo vencido, después lo que vence en la semana.
    vencidos = lote_service.lotes_vencidos(db)
    if vencidos:
        avisos.append({
            "tipo": "lotes_vencidos",
            "nivel": "danger",
            "titulo": "Lotes vencidos",
            "mensaje": f"{len(vencidos)} lote(s) vencido(s) con stock",
            "data": {"total": len(vencidos)},
            "clave": f"lotes_vencidos:{hoy}",
        })
    por_vencer = [l for l in lote_service.lotes_por_vencer(db, dias=7) if (l.dias_para_vencer or 999) <= 7]
    if por_vencer:
        avisos.append({
            "tipo": "lotes_por_vencer",
            "nivel": "warning",
            "titulo": "Lotes por vencer",
            "mensaje": f"{len(por_vencer)} lote(s) vence(n) en los próximos 7 días",
            "data": {"total": len(por_vencer)},
            "clave": f"lotes_por_vencer:{hoy}",
        })

    return avisos


def generar(db: Session) -> int:
    """Guarda los avisos vigentes que todavía no existan. Devuelve los nuevos."""
    hoy = _hoy_utc()
    existentes = {
        n.clave for n in db.query(Notificacion).filter(Notificacion.clave.like(f"%:{hoy}")).all()
    }
    creadas = 0
    for aviso in _avisos_actuales(db):
        if aviso["clave"] in existentes:
            continue
        db.add(Notificacion(
            tipo=aviso["tipo"],
            nivel=aviso["nivel"],
            titulo=aviso["titulo"],
            mensaje=aviso["mensaje"],
            data=json.dumps(aviso["data"], ensure_ascii=False, default=str),
            clave=aviso["clave"],
        ))
        creadas += 1
    if creadas:
        db.commit()

    # Dejar la campana manejable: fuera lo de más de un mes.
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS_PARA_BORRAR)
    db.query(Notificacion).filter(Notificacion.creada_en < limite).delete(synchronize_session=False)
    db.commit()
    return creadas


def _ids_leidas(db: Session, usuario_id: int) -> set:
    """Notificaciones leídas por este usuario (las globales cuentan para todos)."""
    filas = db.query(NotificacionLeida).filter(
        or_(NotificacionLeida.usuario_id == usuario_id, NotificacionLeida.usuario_id.is_(None))
    ).all()
    return {f.notificacion_id for f in filas}


def listar(db: Session, usuario) -> dict:
    """Últimas notificaciones con su estado de lectura para este usuario."""
    leidas = _ids_leidas(db, usuario.id)
    filas = db.query(Notificacion).order_by(Notificacion.creada_en.desc()).limit(100).all()
    items = [{
        "id": n.id,
        "tipo": n.tipo,
        "nivel": n.nivel,
        "titulo": n.titulo,
        "mensaje": n.mensaje,
        "data": json.loads(n.data) if n.data else None,
        "creada_en": n.creada_en.isoformat() if n.creada_en else None,
        "leida": n.id in leidas,
    } for n in filas]
    return {
        "avisos": items,
        "no_leidas": sum(1 for i in items if not i["leida"]),
        "modo_lectura": modo_lectura(db),
    }


def marcar_leida(db: Session, notificacion_id: int, usuario) -> bool:
    """Marca una notificación como leída según el modo configurado."""
    notificacion = db.query(Notificacion).filter(Notificacion.id == notificacion_id).first()
    if not notificacion:
        return False

    # En modo global la fila va con usuario_id NULL: sirve para todos.
    user_id = None if modo_lectura(db) == "global" else usuario.id
    consulta = db.query(NotificacionLeida).filter(NotificacionLeida.notificacion_id == notificacion_id)
    consulta = consulta.filter(NotificacionLeida.usuario_id.is_(None) if user_id is None
                               else NotificacionLeida.usuario_id == user_id)
    if consulta.first():
        return True

    db.add(NotificacionLeida(notificacion_id=notificacion_id, usuario_id=user_id))
    db.commit()
    return True


def marcar_todas(db: Session, usuario) -> int:
    """Marca como leídas todas las que todavía no lo estaban. Devuelve cuántas."""
    leidas = _ids_leidas(db, usuario.id)
    pendientes = db.query(Notificacion).filter(~Notificacion.id.in_(leidas)).all() if leidas else \
        db.query(Notificacion).all()
    user_id = None if modo_lectura(db) == "global" else usuario.id
    ahora = datetime.now(timezone.utc)
    for n in pendientes:
        db.add(NotificacionLeida(notificacion_id=n.id, usuario_id=user_id, leida_en=ahora))
    db.commit()
    return len(pendientes)
