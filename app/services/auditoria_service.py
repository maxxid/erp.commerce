"""Servicio de Auditoría POS: registro de acciones para detección de fraude.

Registra automáticamente:
- Creación de carrito (venta pendiente)
- Eliminación de ítems del carrito
- Confirmación de venta
- Anulación de venta

El endpoint GET detecta automáticamente carritos abandonados (creados pero nunca confirmados).
"""

import json
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.auditoria import Auditoria
from app.models.venta import Venta, VentaItem

# Un carrito es "abandonado" a los 10 minutos sin confirmar. Pasada una semana
# ya no es una alerta para mirar: es ruido de pruebas o de carritos que
# quedaron colgados. Antes se listaban TODOS los pendientes históricos en cada
# carga del tab y no se podían descartar (eran virtuales, sin fila en la base).
ABANDONO_MINUTOS = 10
ABANDONO_VENTANA_DIAS = 7


def registrar(
    db: Session,
    usuario_id: int,
    tipo: str,
    venta_id: Optional[int] = None,
    venta_numero: Optional[str] = None,
    detalle: Optional[dict] = None,
    creado_por: Optional[int] = None,
):
    """Registra un evento de auditoría.

    `venta_id` es una clave foránea hacia `ventas.id`: **solo puede llevar el id
    de una venta**. Si se le pasa el id de un movimiento de caja (borrar una
    extracción, arquear un medio, pagar a un proveedor), SQLite tira
    "FOREIGN KEY constraint failed" y el endpoint responde 500 **después de que
    la operación ya se había hecho** — producción, 20/10/2026, al borrar una
    extracción. Esos ids van en `detalle` en su lugar; `venta_id` se usa solo
    en `routers/ventas.py`.
    """
    riesgo = _evaluar_riesgo(tipo, detalle)
    entry = Auditoria(
        usuario_id=usuario_id,
        tipo=tipo,
        venta_id=venta_id,
        venta_numero=venta_numero,
        detalle=json.dumps(detalle, ensure_ascii=False, default=str) if detalle else None,
        creado_por=creado_por or usuario_id,
        estado=riesgo,
    )
    db.add(entry)
    db.commit()


def listar(
    db: Session,
    usuario_id: Optional[int] = None,
    tipo: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    estado: Optional[str] = None,
) -> tuple:
    """Lista eventos de auditoría con filtros."""
    query = db.query(Auditoria)
    if usuario_id:
        query = query.filter(Auditoria.usuario_id == usuario_id)
    if tipo:
        query = query.filter(Auditoria.tipo == tipo)
    if estado:
        query = query.filter(Auditoria.estado == estado)

    total = query.count()
    eventos = (
        query.order_by(Auditoria.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return eventos, total


def _evento_to_dict(e: Auditoria) -> dict:
    detalle = None
    if e.detalle:
        try:
            detalle = json.loads(e.detalle)
        except (json.JSONDecodeError, TypeError):
            detalle = e.detalle

    return {
        "id": e.id,
        "usuario_id": e.usuario_id,
        "usuario_nombre": e.usuario.nombre if e.usuario else "",
        "tipo": e.tipo,
        "venta_id": e.venta_id,
        "venta_numero": e.venta_numero,
        "detalle": detalle,
        "estado": e.estado,
        "auditado_por": e.auditado_por,
        "auditado_por_nombre": e.auditor_por.nombre if e.auditor_por else None,
        "auditado_en": e.auditado_en.isoformat() if e.auditado_en else None,
        "nota": e.nota or "",
        "created_at": e.created_at.isoformat() if e.created_at else None,
    }


def _evaluar_riesgo(tipo: str, detalle: Optional[dict] = None, medio_pago: str = None) -> str:
    """Evalúa el nivel de riesgo de un evento según el manual de auditoría.

    Returns:
        "normal" - No requiere atención
        "sospechoso" - Requiere revisión
        "muy_sospechoso" - Requiere atención inmediata
    """
    riesgo_alto = ["multiples_cancelaciones", "secuencia_venta_pequena", "fecha_hora_alterada",
                    "venta_modificada_post_efectivo", "venta_anulada_post_efectivo",
                    "carrito_vaciado", "descuento_100pct"]

    # El alta manual desde el POS depende de quién la hizo: la del cajero se
    # revisa, la del dueño o encargado es una carga normal.
    if tipo == "producto_manual_creado":
        rol = (detalle or {}).get("rol")
        return "sospechoso" if rol == "cajero" else "normal"

    riesgo_sospechoso = [
        # Un carrito abandonado es una alerta por definición.
        "carrito_abandonado",
        "item_quitado", "item_modificado", "descuento_manual", "precio_manual",
        "cliente_telefono_editado", "telefono_dueño_editado",
        "venta_cliente_sin_verificar", "venta_empleado_particular",
        "modo_entrenamiento_produccion", "cajon_abierto_fuera_venta",
        "venta_pausada", "multiples_cancelaciones_turno",
        "venta_modificada_post_tarjeta", "abono_cliente",
        # Corregir el medio de pago de una venta ya cobrada: puede ser la
        # cola apurada de siempre, o puede ser alguien tapando un faltante.
        # Por eso queda en pendientes en Auditoría.
        "medio_pago_corregido",
    ]

    if tipo in riesgo_alto:
        return "sospechoso"

    if tipo in riesgo_sospechoso:
        return "sospechoso"

    if tipo == "descuento_aplicado" and detalle:
        monto_desc = detalle.get("monto_descuento", 0)
        total_orig = detalle.get("total_original", 0)
        tipo_desc = detalle.get("tipo", "manual")
        if tipo_desc == "automatico":
            return "normal"
        if total_orig > 0 and monto_desc / total_orig >= 0.99:
            return "sospechoso"
        return "sospechoso"

    if tipo == "venta_confirmada" and detalle:
        h = detalle.get("hora")
        if h:
            try:
                hora = int(h.split(":")[0])
                if hora < 7 or hora > 22:
                    return "sospechoso"
            except:
                pass

    if tipo == "cierre_caja":
        return "sospechoso"

    return "normal"


def _es_sospechoso(e: Auditoria, detalle: dict) -> bool:
    if e.estado != "sospechoso":
        return False
    return True


def _registrar_carritos_abandonados(db: Session) -> int:
    """Convierte los carritos abandonados en eventos reales de auditoría.

    Antes se generaban al vuelo en cada GET con un id `abandon_<venta>`, así
    que se repetían en cada carga, no respetaban la paginación y el botón de
    descartar solo cambiaba la fila en memoria: al refrescar volvían. Como no
    existían en la tabla, tampoco se podía saber quién los había revisado.

    Ahora se registran una sola vez. Sólo se miran los últimos
    `ABANDONO_VENTANA_DIAS` días: un carrito de hace un mes no es una alerta.
    """
    ahora = datetime.now(timezone.utc)
    limite = ahora - timedelta(minutes=ABANDONO_MINUTOS)
    ventana = ahora - timedelta(days=ABANDONO_VENTANA_DIAS)

    candidatas = (
        db.query(Venta)
        .filter(
            Venta.estado == "pendiente",
            Venta.created_at < limite,
            Venta.created_at >= ventana,
        )
        .all()
    )

    creados = 0
    for venta in candidatas:
        items_count = (
            db.query(VentaItem).filter(VentaItem.venta_id == venta.id).count()
        )
        # Un carrito vacío no es una alerta: no hay nada que revisar.
        if items_count == 0:
            continue
        ya_registrado = (
            db.query(Auditoria.id)
            .filter(
                Auditoria.tipo == "carrito_abandonado",
                Auditoria.venta_id == venta.id,
            )
            .first()
        )
        if ya_registrado:
            continue
        registrar(
            db,
            usuario_id=venta.usuario_id,
            tipo="carrito_abandonado",
            venta_id=venta.id,
            venta_numero=venta.numero,
            detalle={
                "items": items_count,
                "subtotal": venta.subtotal,
                "abandonado_desde": venta.created_at.isoformat() if venta.created_at else "",
            },
        )
        creados += 1
    return creados


def listar_con_carritos_abandonados(
    db: Session,
    usuario_id: Optional[int] = None,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple:
    """Lista los eventos de auditoría, registrando antes los carritos abandonados."""
    _registrar_carritos_abandonados(db)
    eventos, total = listar(
        db,
        usuario_id=usuario_id,
        tipo=tipo,
        page=page,
        page_size=page_size,
        estado=estado,
    )
    return [_evento_to_dict(e) for e in eventos], total


def cambiar_estado(db: Session, evento_id: int, auditor_id: int, estado: str, nota: Optional[str] = None) -> dict:
    """Cambia el estado de un evento de auditoría. Retorna dict simple."""
    from app.models.auditoria import Auditoria
    resultado = db.query(Auditoria).filter(Auditoria.id == evento_id).update({
        "estado": estado,
        "auditado_por": auditor_id,
        "auditado_en": datetime.now(timezone.utc),
        "nota": nota,
    })
    db.commit()
    return {"id": evento_id, "actualizado": resultado > 0}
