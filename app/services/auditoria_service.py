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
from app.models.venta import Venta


def registrar(
    db: Session,
    usuario_id: int,
    tipo: str,
    venta_id: Optional[int] = None,
    venta_numero: Optional[str] = None,
    detalle: Optional[dict] = None,
    creado_por: Optional[int] = None,
):
    """Registra un evento de auditoría."""
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
) -> tuple:
    """Lista eventos de auditoría con filtros."""
    query = db.query(Auditoria)
    if usuario_id:
        query = query.filter(Auditoria.usuario_id == usuario_id)
    if tipo:
        query = query.filter(Auditoria.tipo == tipo)

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
        "auditado_por_nombre": e.auditado_por.nombre if e.auditado_por else None,
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

    riesgo_sospechoso = [
        "item_quitado", "item_modificado", "descuento_manual", "precio_manual",
        "cliente_telefono_editado", "telefono_dueño_editado",
        "venta_cliente_sin_verificar", "venta_empleado_particular",
        "modo_entrenamiento_produccion", "cajon_abierto_fuera_venta",
        "venta_pausada", "multiples_cancelaciones_turno",
        "venta_modificada_post_tarjeta", "abono_cliente",
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


def listar_con_carritos_abandonados(
    db: Session,
    usuario_id: Optional[int] = None,
    tipo: Optional[str] = None,
    estado: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple:
    """Lista eventos de auditoría + detecta carritos abandonados (ventas pendientes sin items o sin confirmar)."""
    eventos, total = listar(db, usuario_id=usuario_id, tipo=tipo, page=page, page_size=page_size)
    data = [_evento_to_dict(e) for e in eventos]

    # Si hay filtro de estado, filtrar resultados en memoria
    if estado:
        data = [d for d in data if d.get("estado") == estado]

    # Detectar carritos abandonados: ventas en estado "pendiente" hace más de 10 min sin confirmar
    # (solo si no estamos filtrando por tipo específico)
    # Solo se registran si tenían al menos 1 item (carritos vacíos se ignoran)
    if not tipo and not estado:
        limite = datetime.now(timezone.utc) - timedelta(minutes=10)
        abandonadas = (
            db.query(Venta)
            .filter(Venta.estado == "pendiente", Venta.created_at < limite)
            .all()
        )
        for v in abandonadas:
            from app.models.venta import VentaItem
            items_count = db.query(VentaItem).filter(VentaItem.venta_id == v.id).count()
            if items_count == 0:
                continue
            usuario_nombre = v.usuario.nombre if v.usuario else ""
            data.insert(0, {
                "id": f"abandon_{v.id}",
                "usuario_id": v.usuario_id,
                "usuario_nombre": usuario_nombre,
                "tipo": "carrito_abandonado",
                "venta_id": v.id,
                "venta_numero": v.numero,
                "detalle": {
                    "items": items_count,
                    "subtotal": v.subtotal,
                    "abandonado_desde": v.created_at.isoformat() if v.created_at else "",
                },
                "estado": "sospechoso",
                "created_at": v.created_at.isoformat() if v.created_at else None,
            })
            total += 1

    return data, total


def cambiar_estado(db: Session, evento_id: int, auditor_id: int, estado: str, nota: Optional[str] = None) -> Optional[Auditoria]:
    """Cambia el estado de un evento de auditoría."""
    from app.models.auditoria import Auditoria
    evento = db.query(Auditoria).filter(Auditoria.id == evento_id).first()
    if not evento:
        return None
    evento.estado = estado
    evento.auditado_por = auditor_id
    evento.auditado_en = datetime.now(timezone.utc)
    evento.nota = nota
    db.commit()
    db.refresh(evento)
    return evento
