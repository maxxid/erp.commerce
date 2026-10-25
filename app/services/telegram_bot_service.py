"""Bot de Telegram interactivo: el dueño consulta el negocio desde el celular.

Polling con getUpdates (offset persistido). Solo responde al chat_id configurado.
Comandos: /start /help, /stockbajo (menú por categoría), /stock, /ventas [fecha],
/caja, /top, /clientes, /resumen.
"""
from __future__ import annotations

import html as _html
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

import requests
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.producto import Producto
from app.models.venta import Venta, VentaItem
from app.models.movimiento_caja import MovimientoCaja
from app.services import avisos_service, config_service, stock_service
from app.services.notificaciones_service import fila_producto, mensaje_bajo

TZ_AR = timezone(timedelta(hours=-3))
TG_API = "https://api.telegram.org/bot{token}"
MAX_MSG = 4000
_OFERTA_LOTE_SELECCIONADO: dict = {}
_OFERTA_ESTADO: dict = {}
_WEBHOOK_DELETED = False
CHEQUEO_CADA_SEG = 3


# ---------- helpers de config ----------

def _cfg(db: Session) -> dict:
    c = avisos_service.config_aviso(db)
    c["interactivo"] = (config_service.get_config(db, "telegram_bot_interactivo") or "").lower() == "true"
    return c


def _offset(db: Session) -> int:
    v = config_service.get_config(db, "telegram_bot_offset")
    try:
        return int(v) if v else 0
    except (ValueError, TypeError):
        return 0


def _set_offset(db: Session, value: int) -> None:
    config_service.set_config(db, "telegram_bot_offset", str(value), "Último update_id procesado por el bot de Telegram")


# ---------- helpers de envío ----------

def _send(token: str, chat_id: str, texto: str, reply_markup: Optional[dict] = None) -> None:
    """Envía (partiendo si es largo) y soporta reply_markup en el último chunk."""
    chunks = []
    if len(texto) <= MAX_MSG:
        chunks = [texto]
    else:
        # partir por líneas
        acc = ""
        for linea in texto.split("\n"):
            if len(acc) + len(linea) + 1 > MAX_MSG:
                if acc:
                    chunks.append(acc)
                acc = linea
            else:
                acc = (acc + "\n" + linea) if acc else linea
        if acc:
            chunks.append(acc)
    for i, ch in enumerate(chunks):
        payload = {"chat_id": chat_id, "text": ch, "parse_mode": "HTML",
                   "disable_web_page_preview": True}
        if reply_markup is not None and i == len(chunks) - 1:
            payload["reply_markup"] = reply_markup
        try:
            resp = requests.post(f"{TG_API.format(token=token)}/sendMessage", json=payload, timeout=20)
            try:
                rj = resp.json()
                if not (resp.ok and rj.get("ok")):
                    print(f"[TelegramBot] sendMessage FAIL chat={chat_id}: {rj.get('description') or resp.status_code}", flush=True)
            except Exception:
                if not resp.ok:
                    print(f"[TelegramBot] sendMessage FAIL chat={chat_id}: HTTP {resp.status_code}", flush=True)
        except requests.RequestException as e:
            print(f"[TelegramBot] sendMessage EXC chat={chat_id}: {e}", flush=True)


def _answer_callback(token: str, cb_id: str, text: Optional[str] = None) -> None:
    try:
        payload = {"callback_query_id": cb_id}
        if text:
            payload["text"] = text
        requests.post(f"{TG_API.format(token=token)}/answerCallbackQuery", json=payload, timeout=10)
    except requests.RequestException:
        pass


def _edit_message(token: str, chat_id: str, message_id: int, texto: str) -> None:
    try:
        requests.post(f"{TG_API.format(token=token)}/editMessageText",
                      json={"chat_id": chat_id, "message_id": message_id, "text": texto,
                            "parse_mode": "HTML", "disable_web_page_preview": True},
                      timeout=20)
    except requests.RequestException:
        pass


# ---------- helpers de datos ----------

def _fmt_money(v) -> str:
    try:
        return f"${float(v or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "$0,00"


def _inicio_dia_utc(fecha_local_date) -> datetime:
    """Medianoche AR de una fecha → UTC."""
    local = datetime(fecha_local_date.year, fecha_local_date.month, fecha_local_date.day,
                     0, 0, 0, tzinfo=TZ_AR)
    return local.astimezone(timezone.utc)


def _parse_fecha(arg: str) -> Optional[datetime]:
    """Devuelve la fecha local (date) o None si no se pudo parsear."""
    arg = (arg or "").strip()
    if not arg:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m", "%d-%m-%Y"):
        try:
            d = datetime.strptime(arg, fmt)
            if "%Y" not in fmt and "%y" not in fmt:
                d = d.replace(year=datetime.now(TZ_AR).year)
            return d.date()
        except ValueError:
            continue
    return None


# ---------- handlers ----------

def _h_start() -> str:
    return (
        "👋 <b>ApexERP — Bot del negocio</b>\n\n"
        "Comandos disponibles:\n"
        "/stockbajo — productos bajo mínimo (por categoría o proveedor)\n"
        "/stock — resumen de stock\n"
        "/stockproducto <codigo> — stock y lotes de un producto\n"
        "/buscar <texto> — buscar producto\n"
        "/ventas — ventas de hoy (Hoy/Ayer/Semana)\n"
        "/egresos — egresos del día\n"
        "/ingresos — ingresos manuales\n"
        "/movimientos — últimos movimientos de caja\n"
        "/detalle <venta> — detalle de una venta\n"
        "/caja — estado de caja\n"
        "/dashboard — KPIs del día\n"
        "/top — top 5 productos del mes\n"
        "/clientes — clientes con deuda\n"
        "/compraspendientes — OC pendientes de recibir\n"
        "/lotesvencidos — lotes vencidos y por vencer\n"
        "/vencimientos [dias] — vencimientos próximos (default 30)\n"
        "/alertas — resumen de alertas\n"
        "/backup — último respaldo y salud\n"
        "/oferta <producto> — crear oferta (guiado)\n"
        "/anular <venta> — anular una venta (con confirmación)\n"
        "/resumen — resumen del día\n"
        "/help — esta ayuda"
    )


def _h_stock(db: Session) -> str:
    total = db.query(Producto).filter(Producto.activo == True).count()
    bajos = stock_service.productos_stock_bajo(db)
    agotados = stock_service.filtro_agotado(db.query(Producto)).count()
    valor = db.query(Producto).filter(Producto.activo == True).all()
    valor_stock = sum((p.precio_venta or 0) * (p.stock_actual or 0) for p in valor)
    return (
        f"📦 <b>Stock</b>\n"
        f"Productos activos: {total}\n"
        f"Bajo mínimo: {len(bajos)}\n"
        f"Agotados: {agotados}\n"
        f"Valor de stock: {_fmt_money(valor_stock)}"
    )


def _h_stockbajo_menu_principal(token: str, chat_id: str) -> None:
    kb = {"inline_keyboard": [
        [{"text": "📂 Por categoría", "callback_data": "sb:catmenu"},
         {"text": "🏭 Por proveedor", "callback_data": "sb:provmenu"}],
    ]}
    _send(token, chat_id, "📉 <b>Stock bajo</b> — ¿cómo querés verlo?", reply_markup=kb)


def _h_stockbajo_menu_categorias(db: Session, token: str, chat_id: str) -> None:
    cats = db.query(Categoria).filter(Categoria.activo == True).order_by(Categoria.nombre).all()
    filas = []
    fila = [{"text": "📋 Todos", "callback_data": "sb:all"}]
    for c in cats:
        fila.append({"text": c.nombre, "callback_data": f"sb:{c.id}"})
        if len(fila) >= 2:
            filas.append(fila)
            fila = []
    if fila:
        filas.append(fila)
    kb = {"inline_keyboard": filas} if filas else None
    _send(token, chat_id, "📉 <b>Stock bajo por categoría</b> — elegí:", reply_markup=kb)


def _proveedores_con_bajos(db: Session) -> List[tuple]:
    """Lista de (nombre_proveedor, [productos]) con stock bajo, ordenados por nombre."""
    bajos = stock_service.productos_stock_bajo(db)
    if not bajos:
        return []
    detalle = stock_service.detalle_reposicion(db, bajos)
    grupos: Dict[str, List[Producto]] = {}
    for p in bajos:
        fila = (detalle or {}).get(p.id, {})
        prov = (fila.get("proveedor") or "Sin proveedor").strip() or "Sin proveedor"
        grupos.setdefault(prov, []).append(p)
    return sorted(grupos.items(), key=lambda x: x[0].lower())


def _h_stockbajo_menu_proveedores(db: Session, token: str, chat_id: str) -> None:
    grupos = _proveedores_con_bajos(db)
    if not grupos:
        _send(token, chat_id, "✅ No hay productos bajo mínimo.")
        return
    filas = [[{"text": "📋 Todos", "callback_data": "sbp:all"}]]
    for nombre, prods in grupos:
        cb = f"sbp:{nombre}"
        if len(cb.encode("utf-8")) > 64:
            cb = "sbp:all"
        filas.append([{"text": f"{nombre} ({len(prods)})", "callback_data": cb}])
    kb = {"inline_keyboard": filas}
    _send(token, chat_id, "📉 <b>Stock bajo por proveedor</b> — elegí:", reply_markup=kb)


def _fmt_producto_bajo(db: Session, p: Producto, detalle: dict, por_proveedor: bool = False) -> str:
    fila = (detalle or {}).get(p.id, {})
    nombre = _html.escape(str(p.nombre or ""))
    desc = _html.escape(str(p.descripcion or "").strip())
    prov = _html.escape(str(fila.get("proveedor") or "—"))
    marca = _html.escape(str(p.marca or "—"))
    pc = fila.get("precio_compra")
    pv = fila.get("precio_venta", p.precio_venta)
    lineas = [f"📦 <b>{nombre}</b>" + (f"  <i>({marca})</i>" if marca and marca != "—" else "")]
    if desc and desc != nombre:
        lineas.append(f"   {desc}")
    lineas.append(f"   Stock: {p.stock_actual:g} / Mín: {p.stock_minimo:g}")
    if not por_proveedor:
        lineas.append(f"   Proveedor: {prov}")
    lineas.append(f"   Compra: {_fmt_money(pc)} / Venta: {_fmt_money(pv)}")
    return "\n".join(lineas)


def _h_stockbajo_categoria(db: Session, cat_id: Optional[int]) -> str:
    bajos = stock_service.productos_stock_bajo(db)
    if cat_id is not None and cat_id != 0:
        bajos = [p for p in bajos if p.categoria_id == cat_id]
    if not bajos:
        nombre = "Todos" if cat_id in (None, 0) else _nombre_categoria(db, cat_id)
        return f"✅ Sin productos bajo mínimo en: {nombre}."
    detalle = stock_service.detalle_reposicion(db, bajos)
    cat_nombre = "Todos" if cat_id in (None, 0) else _nombre_categoria(db, cat_id)
    lineas = [f"📉 <b>Stock bajo — {cat_nombre}</b> ({len(bajos)})", ""]
    for p in bajos[:25]:
        lineas.append(_fmt_producto_bajo(db, p, detalle))
        lineas.append("")
    if len(bajos) > 25:
        lineas.append(f"… y {len(bajos) - 25} más.")
    return "\n".join(lineas).strip()


def _h_stockbajo_proveedor(db: Session, prov_nombre: str) -> str:
    bajos = stock_service.productos_stock_bajo(db)
    if prov_nombre and prov_nombre.lower() != "all":
        detalle = stock_service.detalle_reposicion(db, bajos)
        filtrados = []
        for p in bajos:
            fila = (detalle or {}).get(p.id, {})
            if (fila.get("proveedor") or "").strip().lower() == prov_nombre.strip().lower():
                filtrados.append(p)
        bajos = filtrados
    if not bajos:
        return "✅ Sin productos bajo mínimo para ese proveedor."
    detalle = stock_service.detalle_reposicion(db, bajos)
    titulo = "Todos los proveedores" if prov_nombre.lower() == "all" else prov_nombre
    lineas = [f"📉 <b>Stock bajo — {titulo}</b> ({len(bajos)})", ""]
    for p in bajos[:25]:
        lineas.append(_fmt_producto_bajo(db, p, detalle, por_proveedor=True))
        lineas.append("")
    if len(bajos) > 25:
        lineas.append(f"… y {len(bajos) - 25} más.")
    return "\n".join(lineas).strip()


def _nombre_categoria(db: Session, cat_id: int) -> str:
    c = db.query(Categoria).filter(Categoria.id == cat_id).first()
    return c.nombre if c else f"#{cat_id}"


def _h_ventas(db: Session, fecha_arg: str = "") -> str:
    arg = (fecha_arg or "").strip().lower()
    if arg in ("ayer",):
        fecha_local = (datetime.now(TZ_AR) - timedelta(days=1)).date()
    elif arg in ("semana", "semanal"):
        # total de la semana actual
        hoy = datetime.now(TZ_AR).date()
        lunes = hoy - timedelta(days=hoy.weekday())
        desde = _inicio_dia_utc(lunes)
        hasta = _inicio_dia_utc(hoy) + timedelta(days=1)
        return _resumen_ventas_rango(db, desde, hasta, "Semana")
    elif arg in ("", "hoy"):
        fecha_local = datetime.now(TZ_AR).date()
    else:
        parsed = _parse_fecha(arg)
        if parsed is None:
            fecha_local = datetime.now(TZ_AR).date()
        else:
            fecha_local = parsed
    desde = _inicio_dia_utc(fecha_local)
    hasta = desde + timedelta(days=1)
    return _resumen_ventas_rango(db, desde, hasta, fecha_local.strftime("%d/%m/%Y"))


def _resumen_ventas_rango(db: Session, desde: datetime, hasta: datetime, titulo: str) -> str:
    ventas = db.query(Venta).filter(
        Venta.estado == "confirmada",
        Venta.fecha >= desde,
        Venta.fecha < hasta,
    ).all()
    total = sum(v.total or 0 for v in ventas)
    tickets = len(ventas)
    promedio = (total / tickets) if tickets else 0
    por_medio: Dict[str, float] = {}
    for v in ventas:
        por_medio[v.medio_pago or "efectivo"] = por_medio.get(v.medio_pago or "efectivo", 0) + (v.total or 0)
    lineas = [
        f"💰 <b>Ventas — {titulo}</b>",
        f"Total: {_fmt_money(total)}",
        f"Tickets: {tickets}",
        f"Ticket promedio: {_fmt_money(promedio)}",
    ]
    if por_medio:
        lineas.append("")
        lineas.append("Por medio:")
        for m, v in sorted(por_medio.items(), key=lambda x: -x[1]):
            lineas.append(f"  • {m}: {_fmt_money(v)}")
    return "\n".join(lineas)


def _h_caja(db: Session) -> str:
    abierta = False
    try:
        from app.services import caja_service
        abierta = caja_service.caja_abierta(db)
    except Exception:
        abierta = False
    if not abierta:
        return "💼 <b>Caja</b>: cerrada."
    try:
        from app.services import caja_service
        resumen = caja_service.obtener_resumen_por_medio_pago(db)
    except Exception:
        resumen = {}
    lineas = ["💼 <b>Caja: abierta</b>"]
    if isinstance(resumen, dict):
        efectivo = resumen.get("saldo_efectivo")
        cuenta_total = resumen.get("saldo_cuenta_total")
        total = resumen.get("saldo_total")
        if efectivo is not None:
            lineas.append(f"Cajón: {_fmt_money(efectivo)}")
        if cuenta_total is not None:
            lineas.append(f"Cuentas digitales: {_fmt_money(cuenta_total)}")
        if total is not None:
            lineas.append(f"Total: {_fmt_money(total)}")
        ingresos = resumen.get("total_ingresos")
        if ingresos is not None:
            lineas.append(f"Ingresos del día: {_fmt_money(ingresos)}")
    return "\n".join(lineas)


def _h_top(db: Session) -> str:
    from sqlalchemy import func
    inicio_mes = _inicio_dia_utc(datetime.now(TZ_AR).replace(day=1).date())
    filas = (
        db.query(VentaItem.producto_id,
                 func.sum(VentaItem.cantidad),
                 func.sum(VentaItem.subtotal))
        .join(Venta, Venta.id == VentaItem.venta_id)
        .filter(Venta.estado == "confirmada", Venta.fecha >= inicio_mes)
        .group_by(VentaItem.producto_id)
        .order_by(func.sum(VentaItem.cantidad).desc())
        .limit(5)
        .all()
    )
    ids = [r[0] for r in filas]
    nombres = {}
    if ids:
        for p in db.query(Producto).filter(Producto.id.in_(ids)).all():
            nombres[p.id] = p.nombre
    lineas = ["🏆 <b>Top 5 del mes</b>"]
    if not filas:
        lineas.append("Sin ventas este mes.")
        return "\n".join(lineas)
    for r in filas:
        clave = r[0]
        nombre = nombres.get(clave, str(clave))
        cant = r[1] or 0
        imp = r[2] or 0
        lineas.append(f"• {_html.escape(str(nombre))}: {cant:g} u. ({_fmt_money(imp)})")
    return "\n".join(lineas)


def _h_clientes(db: Session) -> str:
    clientes = db.query(Cliente).filter(
        Cliente.activo == True,
        Cliente.saldo_cta_corriente > 0,
    ).order_by(Cliente.saldo_cta_corriente.desc()).limit(10).all()
    if not clientes:
        return "👥 Sin clientes con deuda."
    lineas = [f"👥 <b>Clientes con deuda</b> ({len(clientes)})"]
    for c in clientes:
        lineas.append(f"• {_html.escape(c.nombre)}: {_fmt_money(c.saldo_cta_corriente)}")
    total = sum(c.saldo_cta_corriente or 0 for c in clientes)
    lineas.append(f"\nTotal: {_fmt_money(total)}")
    return "\n".join(lineas)


def _h_resumen(db: Session) -> str:
    ventas_txt = _h_ventas(db, "")
    caja_txt = _h_caja(db)
    bajos = stock_service.productos_stock_bajo(db)
    return f"{ventas_txt}\n\n{caja_txt}\n\n📉 Productos bajo mínimo: {len(bajos)}"


# ---------- alertas proactivas ----------

def chequear_alertas_proactivas() -> None:
    """Job del scheduler: avisa proactivamente al dueño si algo requiere atención."""
    db = SessionLocal()
    try:
        cfg = _cfg(db)
        if not cfg["interactivo"] or not cfg["token"] or not cfg["chat_id"]:
            return
        # Alertas proactivas desactivadas por defecto (toggle en Ajustes).
        if (config_service.get_config(db, "telegram_alertas_proactivas") or "").lower() != "true":
            return
        ahora = datetime.now(TZ_AR)
        hoy = ahora.strftime("%Y-%m-%d")
        # 1) Caja abierta pasadas las 21:00
        if ahora.hour >= 21:
            try:
                from app.services import caja_service
                if caja_service.caja_abierta(db):
                    key = "alerta_caja_abierta_ultimo"
                    if config_service.get_config(db, key) != hoy:
                        _send(cfg["token"], cfg["chat_id"],
                              "⚠️ <b>Caja sigue abierta</b> a las " + ahora.strftime("%H:%M") +
                              ". Recordá cerrarla antes de irte.")
                        config_service.set_config(db, key, hoy, "Último día en que se alertó caja abierta")
            except Exception:
                pass
        # 2) Lotes vencidos (una vez por día)
        try:
            from app.services import lote_service
            vencidos = lote_service.lotes_vencidos(db)
            if vencidos:
                key = "alerta_lotes_vencidos_ultimo"
                if config_service.get_config(db, key) != hoy:
                    _send(cfg["token"], cfg["chat_id"],
                          f"⛔ <b>{len(vencidos)} lote(s) vencido(s)</b> con stock. Revisá /lotesvencidos")
                    config_service.set_config(db, key, hoy, "Último día en que se alertó lotes vencidos")
        except Exception:
            pass
    finally:
        db.close()


# ---------- oferta desde Telegram ----------

def _buscar_producto_oferta(db: Session, arg: str):
    arg = (arg or "").strip()
    if not arg:
        return None
    p = db.query(Producto).filter(Producto.activo == True, Producto.codigo_barras == arg).first()
    if not p:
        p = db.query(Producto).filter(Producto.activo == True, Producto.nombre.ilike(f"%{arg}%")).first()
    return p


def _h_oferta_inicio(db: Session, token: str, chat_id: str, arg: str) -> None:
    arg = (arg or "").strip()
    if not arg:
        from app.services import lote_service
        por_vencer = lote_service.lotes_por_vencer(db, 30)
        vencidos = lote_service.lotes_vencidos(db)
        lotes = vencidos + por_vencer
        if not lotes:
            _send(token, chat_id, "✅ No hay lotes con vencimiento próximo.\nUsá /oferta <nombre> para buscar un producto.")
            return
        seen = set()
        filas = []
        for l in lotes[:12]:
            if l.producto_id in seen:
                continue
            seen.add(l.producto_id)
            p = db.query(Producto).filter(Producto.id == l.producto_id).first()
            if not p:
                continue
            dias = 0
            if l.fecha_vencimiento:
                dias = (l.fecha_vencimiento - datetime.now(timezone.utc).replace(tzinfo=None)).days
            etiqueta = f"{p.nombre[:20]} ({dias}d, {l.cantidad_actual:g}u)"
            filas.append([{"text": etiqueta, "callback_data": f"oferta_sel:{p.id}:{l.id}"}])
        kb = {"inline_keyboard": filas}
        _send(token, chat_id, "🏷️ <b>Crear oferta</b> — elegí un producto con vencimiento próximo:", reply_markup=kb)
        return
    p = _buscar_producto_oferta(db, arg)
    if not p:
        _send(token, chat_id, "Uso: /oferta <producto>\nEj: /oferta coca\nO /oferta sin argumentos para ver vencimientos próximos.")
        return
    _h_oferta_sel(db, token, chat_id, p.id, None)


def _h_oferta_sel(db: Session, token: str, chat_id: str, prod_id: int, lot_id: Optional[int] = None) -> None:
    p = db.query(Producto).filter(Producto.id == prod_id).first()
    if not p:
        _send(token, chat_id, "❌ Producto no encontrado.")
        return
    if lot_id:
        _OFERTA_LOTE_SELECCIONADO[str(chat_id)] = lot_id
    else:
        _OFERTA_LOTE_SELECCIONADO.pop(str(chat_id), None)
    _OFERTA_ESTADO[str(chat_id)] = {"step": "tipo", "prod_id": prod_id, "lot_id": lot_id}
    extra = ""
    lid = _OFERTA_LOTE_SELECCIONADO.get(str(chat_id))
    if lid:
        from app.models.lote import Lote
        lote = db.query(Lote).filter(Lote.id == lid).first()
        if lote and lote.fecha_vencimiento:
            extra = f"\nLote: {lote.codigo or 'lote'} — vence {lote.fecha_vencimiento.strftime('%d/%m/%Y')} ({lote.cantidad_actual:g} u.)"
    kb = {"inline_keyboard": [
        [{"text": "% Porcentaje", "callback_data": "oferta_tipo:pct"},
         {"text": "$ Importe fijo", "callback_data": "oferta_tipo:imp"}],
        [{"text": "2x1", "callback_data": "oferta_tipo:2x1"}],
        [{"text": "❌ Cancelar", "callback_data": "oferta_cancel"}],
    ]}
    _send(token, chat_id, f"🏷️ <b>Oferta para:</b> {_html.escape(p.nombre)}\nPrecio actual: {_fmt_money(p.precio_venta)}{extra}\n\n¿Tipo de oferta?", reply_markup=kb)


def _h_oferta_tipo(db: Session, token: str, chat_id: str, tipo: str) -> None:
    st = _OFERTA_ESTADO.get(str(chat_id))
    if not st:
        _send(token, chat_id, "Sesión expirada. Usá /oferta de nuevo.")
        return
    prod_id = st["prod_id"]
    p = db.query(Producto).filter(Producto.id == prod_id).first()
    if not p:
        _send(token, chat_id, "❌ Producto no encontrado.")
        _OFERTA_ESTADO.pop(str(chat_id), None)
        return
    if tipo == "pct":
        st["tipo"] = "porcentaje"
        st["step"] = "pct"
        kb = {"inline_keyboard": [
            [{"text": "10%", "callback_data": "oferta_pct:10"},
             {"text": "20%", "callback_data": "oferta_pct:20"},
             {"text": "30%", "callback_data": "oferta_pct:30"},
             {"text": "50%", "callback_data": "oferta_pct:50"}],
            [{"text": "❌ Cancelar", "callback_data": "oferta_cancel"}],
        ]}
        _send(token, chat_id, f"🏷️ {_html.escape(p.nombre)} — ¿Qué descuento?", reply_markup=kb)
    elif tipo == "imp":
        st["tipo"] = "monto_fijo"
        st["step"] = "monto"
        _send(token, chat_id, f"🏷️ {_html.escape(p.nombre)} — escribí el monto fijo de descuento (en $):")
    elif tipo == "2x1":
        st["tipo"] = "2x1"
        st["valor"] = 0
        st["step"] = "dias"
        kb = {"inline_keyboard": [
            [{"text": "7 días", "callback_data": "oferta_dias:7"},
             {"text": "14 días", "callback_data": "oferta_dias:14"},
             {"text": "30 días", "callback_data": "oferta_dias:30"}],
            [{"text": "❌ Cancelar", "callback_data": "oferta_cancel"}],
        ]}
        _send(token, chat_id, f"🏷️ {_html.escape(p.nombre)} — 2x1\n¿Por cuántos días?", reply_markup=kb)


def _h_oferta_pct(db: Session, token: str, chat_id: str, pct: int) -> None:
    st = _OFERTA_ESTADO.get(str(chat_id))
    if not st:
        _send(token, chat_id, "Sesión expirada. Usá /oferta de nuevo.")
        return
    st["valor"] = float(pct)
    st["step"] = "dias"
    prod_id = st["prod_id"]
    p = db.query(Producto).filter(Producto.id == prod_id).first()
    kb = {"inline_keyboard": [
        [{"text": "7 días", "callback_data": "oferta_dias:7"},
         {"text": "14 días", "callback_data": "oferta_dias:14"},
         {"text": "30 días", "callback_data": "oferta_dias:30"}],
        [{"text": "❌ Cancelar", "callback_data": "oferta_cancel"}],
    ]}
    _send(token, chat_id, f"🏷️ {_html.escape(p.nombre if p else '')} — {pct}% OFF\n\n¿Por cuántos días?", reply_markup=kb)


def _h_oferta_dias(db: Session, token: str, chat_id: str, dias: int) -> None:
    st = _OFERTA_ESTADO.get(str(chat_id))
    if not st:
        _send(token, chat_id, "Sesión expirada. Usá /oferta de nuevo.")
        return
    st["dias"] = dias
    st["step"] = "cantidad"
    prod_id = st["prod_id"]
    p = db.query(Producto).filter(Producto.id == prod_id).first()
    lid = st.get("lot_id")
    cant_lote = 0
    if lid:
        from app.models.lote import Lote
        lote = db.query(Lote).filter(Lote.id == lid).first()
        if lote:
            cant_lote = int(lote.cantidad_actual or 0)
    kb = {"inline_keyboard": []}
    fila = []
    if cant_lote > 0:
        fila.append({"text": f"Cantidad del lote ({cant_lote})", "callback_data": "oferta_cant:lote"})
    fila.append({"text": "Otra cantidad", "callback_data": "oferta_cant:otra"})
    kb["inline_keyboard"].append(fila)
    kb["inline_keyboard"].append([{"text": "❌ Cancelar", "callback_data": "oferta_cancel"}])
    _send(token, chat_id, f"🏷️ {_html.escape(p.nombre if p else '')}\n\n¿Cantidad de unidades para la oferta?", reply_markup=kb)


def _h_oferta_cantidad_lote(db: Session, token: str, chat_id: str) -> None:
    st = _OFERTA_ESTADO.get(str(chat_id))
    if not st:
        _send(token, chat_id, "Sesión expirada. Usá /oferta de nuevo.")
        return
    lid = st.get("lot_id")
    cant = 0
    if lid:
        from app.models.lote import Lote
        lote = db.query(Lote).filter(Lote.id == lid).first()
        if lote:
            cant = int(lote.cantidad_actual or 0)
    st["cantidad"] = cant if cant > 0 else None
    st["step"] = "preview"
    _mostrar_preview_oferta(db, token, chat_id, st)


def _mostrar_preview_oferta(db: Session, token: str, chat_id: str, st: dict) -> None:
    prod_id = st["prod_id"]
    p = db.query(Producto).filter(Producto.id == prod_id).first()
    if not p:
        _send(token, chat_id, "❌ Producto no encontrado.")
        _OFERTA_ESTADO.pop(str(chat_id), None)
        return
    tipo = st.get("tipo", "porcentaje")
    valor = st.get("valor", 0)
    dias = st.get("dias", 7)
    cantidad = st.get("cantidad")
    if tipo == "porcentaje":
        precio_oferta = (p.precio_venta or 0) * (1 - valor / 100.0)
        descuento_txt = f"{valor:g}%"
    elif tipo == "monto_fijo":
        precio_oferta = (p.precio_venta or 0) - valor
        descuento_txt = f"${valor:g}"
    else:
        precio_oferta = (p.precio_venta or 0) / 2
        descuento_txt = "2x1"
    fin = datetime.now(TZ_AR) + timedelta(days=dias)
    lid = st.get("lot_id")
    extra = ""
    if lid:
        from app.models.lote import Lote
        lote = db.query(Lote).filter(Lote.id == lid).first()
        if lote and lote.fecha_vencimiento:
            extra = f"\nLote: {lote.codigo or 'lote'} — vence {lote.fecha_vencimiento.strftime('%d/%m/%Y')} ({lote.cantidad_actual:g} u.)"
    cant_txt = f"\nCantidad (max_unidades): {cantidad}" if cantidad else ""
    kb = {"inline_keyboard": [[
        {"text": "✅ Crear oferta", "callback_data": "oferta_ok"},
        {"text": "❌ Cancelar", "callback_data": "oferta_cancel"},
    ]]}
    _send(token, chat_id,
          f"🏷️ <b>Vista previa</b>\n"
          f"Producto: {_html.escape(p.nombre)}\n"
          f"Tipo: {tipo} — {descuento_txt}\n"
          f"Precio oferta: {_fmt_money(precio_oferta)} (era {_fmt_money(p.precio_venta)})\n"
          f"Vigencia: {dias} días (hasta {fin.strftime('%d/%m/%Y')}){extra}{cant_txt}\n\n¿Confirmar?",
          reply_markup=kb)
    st["step"] = "preview"


def _h_oferta_crear_estado(db: Session, token: str, chat_id: str) -> None:
    st = _OFERTA_ESTADO.get(str(chat_id))
    if not st:
        _send(token, chat_id, "Sesión expirada. Usá /oferta de nuevo.")
        return
    prod_id = st["prod_id"]
    p = db.query(Producto).filter(Producto.id == prod_id).first()
    if not p:
        _send(token, chat_id, "❌ Producto no encontrado.")
        _OFERTA_ESTADO.pop(str(chat_id), None)
        return
    from app.services import oferta_service
    ahora = datetime.now(timezone.utc)
    dias = st.get("dias", 7)
    fin = ahora + timedelta(days=dias)
    tipo = st.get("tipo", "porcentaje")
    valor = st.get("valor", 0)
    cantidad = st.get("cantidad")
    lid = st.get("lot_id")
    desc_extra = ""
    if lid:
        from app.models.lote import Lote
        lote = db.query(Lote).filter(Lote.id == lid).first()
        if lote:
            desc_extra = f" (lote {lote.codigo or lid}, vence {lote.fecha_vencimiento.strftime('%d/%m/%Y') if lote.fecha_vencimiento else 's/venc'})"
    data = {
        "producto_id": p.id,
        "tipo": tipo,
        "valor": float(valor),
        "requiere_cantidad": 2 if tipo == "2x1" else 1,
        "fecha_inicio": ahora,
        "fecha_fin": fin,
        "max_unidades": cantidad,
        "descripcion": f"Oferta creada desde Telegram{desc_extra}",
    }
    try:
        oferta = oferta_service.crear_oferta(db, data)
        _send(token, chat_id, f"✅ Oferta creada (id {oferta.id}) en {_html.escape(p.nombre)}.")
    except Exception as e:
        _send(token, chat_id, f"❌ Error al crear oferta: {e}")
    finally:
        _OFERTA_ESTADO.pop(str(chat_id), None)
        _OFERTA_LOTE_SELECCIONADO.pop(str(chat_id), None)

# ---------- nuevos comandos (fase 2) ----------

def _admin_user_id(db: Session) -> Optional[int]:
    from app.models.usuario import Usuario
    u = db.query(Usuario).filter(Usuario.rol == "admin", Usuario.activo == True).first()
    return u.id if u else None


def _h_egresos(db: Session, fecha_arg: str = "") -> str:
    arg = (fecha_arg or "").strip().lower()
    if arg in ("semana", "semanal"):
        hoy = datetime.now(TZ_AR).date()
        lunes = hoy - timedelta(days=hoy.weekday())
        desde = _inicio_dia_utc(lunes)
        hasta = _inicio_dia_utc(hoy) + timedelta(days=1)
        titulo = "Semana"
    elif arg in ("ayer",):
        fecha_local = (datetime.now(TZ_AR) - timedelta(days=1)).date()
        desde = _inicio_dia_utc(fecha_local)
        hasta = desde + timedelta(days=1)
        titulo = fecha_local.strftime("%d/%m/%Y")
    elif arg in ("", "hoy"):
        fecha_local = datetime.now(TZ_AR).date()
        desde = _inicio_dia_utc(fecha_local)
        hasta = desde + timedelta(days=1)
        titulo = fecha_local.strftime("%d/%m/%Y")
    elif arg not in ("semana", "semanal"):
        parsed = _parse_fecha(arg)
        if parsed is None:
            fecha_local = datetime.now(TZ_AR).date()
            desde = _inicio_dia_utc(fecha_local)
            hasta = desde + timedelta(days=1)
            titulo = fecha_local.strftime("%d/%m/%Y")
        else:
            desde = _inicio_dia_utc(parsed)
            hasta = desde + timedelta(days=1)
            titulo = parsed.strftime("%d/%m/%Y")

    movs_q = db.query(MovimientoCaja).filter(MovimientoCaja.tipo == "egreso")
    if arg not in ("semana", "semanal"):
        movs_q = movs_q.filter(
            MovimientoCaja.created_at >= desde,
            MovimientoCaja.created_at < hasta,
        )
    movs = movs_q.order_by(MovimientoCaja.id.desc()).limit(50).all()
    total = sum(m.monto or 0 for m in movs)
    lineas = [f"💸 <b>Egresos — {titulo}</b>", f"Total: {_fmt_money(total)} ({len(movs)} mov.)", ""]
    for m in movs[:20]:
        hora = ""
        if getattr(m, "created_at", None):
            try:
                hora = m.created_at.strftime("%H:%M")
            except Exception:
                hora = ""
        desc = _html.escape(str(m.descripcion or m.referencia_tipo or "egreso"))
        lineas.append(f"• {_fmt_money(m.monto)} — {desc} ({m.medio_pago or 'efectivo'}) {hora}")
    if len(movs) > 20:
        lineas.append(f"… y {len(movs) - 20} más.")
    if not movs:
        lineas.append("Sin egresos.")
    return "\n".join(lineas)


def _h_ingresos(db: Session) -> str:
    movs = db.query(MovimientoCaja).filter(
        MovimientoCaja.tipo == "ingreso",
    ).order_by(MovimientoCaja.id.desc()).limit(20).all()
    total = sum(m.monto or 0 for m in movs)
    lineas = [f"💵 <b>Ingresos manuales</b> — {_fmt_money(total)}", ""]
    for m in movs:
        hora = m.created_at.strftime("%H:%M") if getattr(m, "created_at", None) else ""
        lineas.append(f"• {_fmt_money(m.monto)} — {_html.escape(str(m.descripcion or 'ingreso'))} {hora}")
    if not movs:
        lineas.append("Sin ingresos manuales.")
    return "\n".join(lineas)


def _h_movimientos(db: Session) -> str:
    movs = db.query(MovimientoCaja).order_by(MovimientoCaja.id.desc()).limit(15).all()
    lineas = ["📜 <b>Últimos movimientos</b>", ""]
    for m in movs:
        hora = m.created_at.strftime("%H:%M") if getattr(m, "created_at", None) else ""
        tipo = (m.tipo or "").upper()
        lineas.append(f"• {hora} {tipo} {_fmt_money(m.monto)} — {_html.escape(str(m.descripcion or '')[:40])}")
    if not movs:
        lineas.append("Sin movimientos.")
    return "\n".join(lineas)


def _h_detalle_venta(db: Session, arg: str) -> str:
    arg = (arg or "").strip()
    if not arg:
        return "Uso: /detalle V-000123  (o /detalle 123)"
    venta = None
    if arg.isdigit():
        venta = db.query(Venta).filter(Venta.id == int(arg)).first()
    else:
        venta = db.query(Venta).filter(Venta.numero == arg).first()
    if not venta:
        # try by numero partial
        venta = db.query(Venta).filter(Venta.numero.ilike(f"%{arg}%")).first()
    if not venta:
        return f"❌ Venta no encontrada: {arg}"
    cliente = None
    if venta.cliente_id:
        cliente = db.query(Cliente).filter(Cliente.id == venta.cliente_id).first()
    lineas = [
        f"🧾 <b>{venta.numero}</b> — {venta.estado}",
        f"Fecha: {venta.fecha.strftime('%d/%m/%Y %H:%M') if venta.fecha else '—'}",
        f"Cliente: {_html.escape(cliente.nombre if cliente else 'Consumidor Final')}",
        f"Medio: {venta.medio_pago}",
        f"Subtotal: {_fmt_money(venta.subtotal)}  Desc: {_fmt_money(venta.descuento)}",
        f"Total: {_fmt_money(venta.total)}",
        "",
        "Items:",
    ]
    for it in (venta.items or []):
        lineas.append(f"  • {_html.escape(str(it.producto_nombre or it.producto_id))} x{it.cantidad:g} @ {_fmt_money(it.precio_unitario)} = {_fmt_money(it.subtotal)}")
    return "\n".join(lineas)


def _h_buscar(db: Session, arg: str) -> str:
    arg = (arg or "").strip()
    if not arg:
        return "Uso: /buscar <nombre o codigo>"
    from sqlalchemy import or_
    q = db.query(Producto).filter(Producto.activo == True).filter(
        or_(Producto.nombre.ilike(f"%{arg}%"),
            Producto.codigo_barras.ilike(f"%{arg}%"),
            Producto.marca.ilike(f"%{arg}%"))
    ).limit(8).all()
    if not q:
        return f"❌ Sin resultados para: {arg}"
    lineas = [f"🔍 <b>Búsqueda: {arg}</b> ({len(q)})", ""]
    for p in q:
        cat = ""
        if p.categoria_id:
            from app.models.categoria import Categoria
            c = db.query(Categoria).filter(Categoria.id == p.categoria_id).first()
            if c:
                cat = c.nombre
        lineas.append(f"📦 <b>{_html.escape(p.nombre)}</b>" + (f" ({_html.escape(p.marca)})" if p.marca else ""))
        lineas.append(f"   Stock: {p.stock_actual:g} / Mín: {p.stock_minimo:g}  |  Venta: {_fmt_money(p.precio_venta)}")
        if cat:
            lineas.append(f"   Categoría: {cat}")
        lineas.append("")
    return "\n".join(lineas).strip()


def _h_stockproducto(db: Session, arg: str) -> str:
    arg = (arg or "").strip()
    if not arg:
        return "Uso: /stockproducto <codigo de barras>"
    p = db.query(Producto).filter(Producto.codigo_barras == arg).first()
    if not p:
        p = db.query(Producto).filter(Producto.codigo_barras.ilike(f"%{arg}%")).first()
    if not p:
        return f"❌ Producto no encontrado: {arg}"
    from app.services import lote_service
    try:
        lotes, _ = lote_service.listar_lotes(db, producto_id=p.id, solo_con_stock=True)
    except Exception:
        lotes = []
    lineas = [
        f"📦 <b>{_html.escape(p.nombre)}</b>" + (f" ({_html.escape(p.marca)})" if p.marca else ""),
        f"Stock actual: {p.stock_actual:g}  (mín: {p.stock_minimo:g})",
        f"Precio venta: {_fmt_money(p.precio_venta)}  |  costo: {_fmt_money(p.precio_costo)}",
    ]
    if lotes:
        lineas.append("")
        lineas.append("Lotes:")
        for l in lotes[:10]:
            venc = l.fecha_vencimiento.strftime("%d/%m/%Y") if getattr(l, "fecha_vencimiento", None) else "s/venc"
            lineas.append(f"  • {l.codigo or 'lote'}: {l.cantidad_actual:g} — vence {venc}")
    return "\n".join(lineas)


def _h_compras_pendientes(db: Session) -> str:
    from app.models.compra import Compra
    compras = db.query(Compra).filter(Compra.estado.in_(["pendiente", "parcial"])).order_by(Compra.id.desc()).limit(15).all()
    if not compras:
        return "✅ No hay compras pendientes de recibir."
    lineas = [f"🛒 <b>Compras pendientes</b> ({len(compras)})", ""]
    for c in compras:
        prov = c.proveedor.nombre if getattr(c, "proveedor", None) else f"#{c.proveedor_id}"
        lineas.append(f"• {c.numero} — {_html.escape(str(prov))}")
        lineas.append(f"   Estado: {c.estado}  |  Total: {_fmt_money(c.total)}")
    return "\n".join(lineas)


def _h_lotes_vencidos(db: Session) -> str:
    from app.services import lote_service
    vencidos = lote_service.lotes_vencidos(db)
    por_vencer = lote_service.lotes_por_vencer(db, 7)
    lineas = []
    if vencidos:
        lineas.append(f"⛔ <b>Lotes vencidos</b> ({len(vencidos)})")
        for l in vencidos[:15]:
            prod = db.query(Producto).filter(Producto.id == l.producto_id).first()
            nombre = prod.nombre if prod else f"#{l.producto_id}"
            lineas.append(f"  • {_html.escape(nombre)} — {l.cantidad_actual:g} (venció {l.fecha_vencimiento.strftime('%d/%m/%Y')})")
        lineas.append("")
    if por_vencer:
        lineas.append(f"⚠️ <b>Por vencer (7 días)</b> ({len(por_vencer)})")
        for l in por_vencer[:15]:
            prod = db.query(Producto).filter(Producto.id == l.producto_id).first()
            nombre = prod.nombre if prod else f"#{l.producto_id}"
            lineas.append(f"  • {_html.escape(nombre)} — {l.cantidad_actual:g} (vence {l.fecha_vencimiento.strftime('%d/%m/%Y')})")
    if not lineas:
        lineas.append("✅ Sin lotes vencidos ni por vencer.")
    return "\n".join(lineas)


def _h_vencimientos(db: Session, arg: str = "") -> str:
    arg = (arg or "").strip()
    max_dias = 21
    if arg.isdigit():
        max_dias = max(1, min(90, int(arg)))
    from app.services import lote_service
    por_vencer = lote_service.lotes_por_vencer(db, max_dias)
    vencidos = lote_service.lotes_vencidos(db)

    # Agrupar por tier
    tier1, tier2, tier3 = [], [], []
    ahora = datetime.now(timezone.utc).replace(tzinfo=None)
    for l in por_vencer:
        if l.fecha_vencimiento is None:
            continue
        dias = (l.fecha_vencimiento - ahora).days
        if dias <= 7:
            tier1.append((l, dias))
        elif dias <= 14:
            tier2.append((l, dias))
        else:
            tier3.append((l, dias))

    lineas = []
    if vencidos:
        lineas.append(f"⛔ <b>VENCIDOS</b> ({len(vencidos)})")
        for l in vencidos[:15]:
            prod = db.query(Producto).filter(Producto.id == l.producto_id).first()
            nombre = prod.nombre if prod else f"#{l.producto_id}"
            marca = f" ({prod.marca})" if prod and prod.marca else ""
            lineas.append(f"  • {_html.escape(nombre)}{marca}")
            lineas.append(f"    Cant: {l.cantidad_actual:g} | Costo: {_fmt_money(prod.precio_costo if prod else 0)} | Venta: {_fmt_money(prod.precio_venta if prod else 0)}")
        lineas.append("")

    def _tier(titulo, items, emoji):
        if not items:
            return
        lineas.append(f"{emoji} <b>{titulo}</b> ({len(items)})")
        for l, dias in items[:15]:
            prod = db.query(Producto).filter(Producto.id == l.producto_id).first()
            nombre = prod.nombre if prod else f"#{l.producto_id}"
            marca = f" ({prod.marca})" if prod and prod.marca else ""
            lineas.append(f"  • {_html.escape(nombre)}{marca}")
            lineas.append(f"    Cant: {l.cantidad_actual:g} | Costo: {_fmt_money(prod.precio_costo if prod else 0)} | Venta: {_fmt_money(prod.precio_venta if prod else 0)} | vence en {dias}d")
        if len(items) > 15:
            lineas.append(f"  … y {len(items) - 15} más.")
        lineas.append("")

    _tier("URGENTE (≤7 días)", tier1, "🔴")
    _tier("Próximos 8-14 días", tier2, "🟠")
    _tier("15-21 días", tier3, "🟡")

    if not (vencidos or tier1 or tier2 or tier3):
        lineas.append("✅ Sin vencimientos próximos.")
    return "\n".join(lineas).strip()


def _h_alertas(db: Session) -> str:
    bajos = stock_service.productos_stock_bajo(db)
    from app.services import lote_service
    vencidos = lote_service.lotes_vencidos(db)
    por_vencer = lote_service.lotes_por_vencer(db, 7)
    # licencia
    from app.models.licencia import Licencia
    lic = db.query(Licencia).filter(Licencia.activo == True).order_by(Licencia.fecha_vencimiento.asc()).first()
    lic_txt = ""
    if lic and lic.fecha_vencimiento:
        dias = (lic.fecha_vencimiento - datetime.now(timezone.utc)).days
        if dias <= 30:
            lic_txt = f"\n🔐 Licencia vence en {dias} días"
    # caja
    try:
        from app.services import caja_service
        caja_abierta = caja_service.caja_abierta(db)
    except Exception:
        caja_abierta = False
    lineas = ["🔔 <b>Alertas</b>", ""]
    lineas.append(f"📉 Stock bajo: {len(bajos)}")
    lineas.append(f"⛔ Lotes vencidos: {len(vencidos)}")
    lineas.append(f"⚠️ Lotes por vencer (7d): {len(por_vencer)}")
    lineas.append(f"💼 Caja: {'abierta' if caja_abierta else 'cerrada'}")
    if lic_txt:
        lineas.append(lic_txt.strip())
    if not (bajos or vencidos or por_vencer or lic_txt):
        lineas.append("\n✅ Todo en orden.")
    return "\n".join(lineas)


def _h_dashboard(db: Session) -> str:
    from app.models.venta import Venta
    hoy = datetime.now(TZ_AR).date()
    desde = _inicio_dia_utc(hoy)
    hasta = desde + timedelta(days=1)
    ventas = db.query(Venta).filter(Venta.estado == "confirmada", Venta.fecha >= desde, Venta.fecha < hasta).all()
    total = sum(v.total or 0 for v in ventas)
    tickets = len(ventas)
    promedio = (total / tickets) if tickets else 0
    efectivo = sum(v.total or 0 for v in ventas if v.medio_pago == "efectivo")
    bajos = stock_service.productos_stock_bajo(db)
    try:
        from app.services import caja_service
        caja_abierta = caja_service.caja_abierta(db)
    except Exception:
        caja_abierta = False
    lineas = [
        f"📊 <b>Dashboard — {hoy.strftime('%d/%m/%Y')}</b>",
        f"Ventas: {_fmt_money(total)} ({tickets} tickets)",
        f"Ticket promedio: {_fmt_money(promedio)}",
        f"Efectivo: {_fmt_money(efectivo)}",
        f"Caja: {'abierta' if caja_abierta else 'cerrada'}",
        f"Stock crítico: {len(bajos)}",
    ]
    return "\n".join(lineas)


def _h_backup(db: Session) -> str:
    from app.services import backup_service, salud_service
    locales = backup_service.listar_backups_locales()
    ultimo = locales[0] if locales else None
    lineas = ["💾 <b>Backups</b>"]
    if ultimo:
        lineas.append(f"Último local: {ultimo.get('nombre')} ({_fmt_money(ultimo.get('size', 0)/1024)} KB)")
        lineas.append(f"Fecha: {ultimo.get('fecha')}")
    else:
        lineas.append("Sin backups locales.")
    try:
        problemas = salud_service.problemas_de_replica(db)
        if problemas:
            lineas.append("")
            lineas.append("⚠️ Problemas de réplica:")
            for p in problemas:
                lineas.append(f"  • {p}")
        else:
            lineas.append("Réplica: OK")
    except Exception:
        pass
    return "\n".join(lineas)


def _h_anular(db: Session, token: str, chat_id: str, arg: str) -> None:
    arg = (arg or "").strip()
    if not arg:
        _send(token, chat_id, "Uso: /anular V-000123  (o /anular 123)\nSe pedirá confirmación.")
        return
    venta = None
    if arg.isdigit():
        venta = db.query(Venta).filter(Venta.id == int(arg)).first()
    else:
        venta = db.query(Venta).filter(Venta.numero == arg).first()
    if not venta:
        venta = db.query(Venta).filter(Venta.numero.ilike(f"%{arg}%")).first()
    if not venta:
        _send(token, chat_id, f"❌ Venta no encontrada: {arg}")
        return
    if venta.estado != "confirmada":
        _send(token, chat_id, f"❌ Solo se anulan ventas confirmadas (estado: {venta.estado}).")
        return
    kb = {"inline_keyboard": [[
        {"text": "✅ Confirmar anulación", "callback_data": f"anular:{venta.id}"},
        {"text": "❌ Cancelar", "callback_data": f"anularcancel:{venta.id}"},
    ]]}
    _send(token, chat_id, f"⚠️ ¿Anular {venta.numero} por {_fmt_money(venta.total)}?", reply_markup=kb)


def _do_anular(db: Session, venta_id: int) -> str:
    from app.services import venta_service
    venta = db.query(Venta).filter(Venta.id == venta_id).first()
    if not venta:
        return "❌ Venta no encontrada."
    if venta.estado != "confirmada":
        return f"❌ Estado actual: {venta.estado}."
    uid = _admin_user_id(db)
    try:
        venta_service.anular_venta(db, venta, uid)
    except Exception as e:
        return f"❌ Error: {e}"
    return f"✅ Venta {venta.numero} anulada. Stock y caja revertidos."

def _es_autorizado(chat_id: str, cfg: dict) -> bool:
    return str(chat_id) == str(cfg.get("chat_id", "")).strip()


def procesar_update(db: Session, token: str, update: dict) -> None:
    """Procesa un update (message o callback_query)."""
    # callback_query
    cb = update.get("callback_query")
    if cb:
        cb_id = cb.get("id")
        msg = cb.get("message") or {}
        chat = (msg.get("chat") or {})
        chat_id = str(chat.get("id"))
        cfg = _cfg(db)
        if not _es_autorizado(chat_id, cfg):
            _answer_callback(token, cb_id, "No autorizado")
            return
        data = cb.get("data") or ""
        msg_id = msg.get("message_id")
        if data == "sb:catmenu":
            _h_stockbajo_menu_categorias(db, token, chat_id)
        elif data == "sb:provmenu":
            _h_stockbajo_menu_proveedores(db, token, chat_id)
        elif data.startswith("sb:"):
            sufijo = data[3:]
            cat_id = None if sufijo == "all" else int(sufijo) if sufijo.isdigit() else None
            texto = _h_stockbajo_categoria(db, cat_id)
            if msg_id:
                _edit_message(token, chat_id, msg_id, texto)
            else:
                _send(token, chat_id, texto)
        elif data.startswith("sbp:"):
            sufijo = data[4:]
            prov = "all" if sufijo == "all" else sufijo
            texto = _h_stockbajo_proveedor(db, prov)
            if msg_id:
                _edit_message(token, chat_id, msg_id, texto)
            else:
                _send(token, chat_id, texto)
        elif data.startswith("ventas:"):
            suf = data[7:]
            _send(token, chat_id, _h_ventas(db, suf))
        elif data.startswith("anular:"):
            vid = int(data[7:]) if data[7:].isdigit() else None
            if vid:
                res = _do_anular(db, vid)
                _send(token, chat_id, res)
        elif data.startswith("anularcancel:"):
            _send(token, chat_id, "Cancelado.")
        elif data == "oferta:venc":
            _h_oferta_inicio(db, token, chat_id, "")
        elif data.startswith("oferta_sel:"):
            parts = data.split(":")
            pid = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None
            lid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
            if pid:
                _h_oferta_sel(db, token, chat_id, pid, lid)
        elif data.startswith("oferta_tipo:"):
            _h_oferta_tipo(db, token, chat_id, data.split(":", 1)[1])
        elif data.startswith("oferta_pct:"):
            pct = int(data.split(":", 1)[1]) if data.split(":", 1)[1].isdigit() else 0
            _h_oferta_pct(db, token, chat_id, pct)
        elif data.startswith("oferta_dias:"):
            dias = int(data.split(":", 1)[1]) if data.split(":", 1)[1].isdigit() else 7
            _h_oferta_dias(db, token, chat_id, dias)
        elif data == "oferta_cant:lote":
            _h_oferta_cantidad_lote(db, token, chat_id)
        elif data == "oferta_cant:otra":
            st = _OFERTA_ESTADO.get(str(chat_id))
            if st:
                st["step"] = "cantidad_texto"
                _send(token, chat_id, "Escribí la cantidad de unidades:")
        elif data == "oferta_ok":
            _h_oferta_crear_estado(db, token, chat_id)
        elif data == "oferta_cancel":
            _OFERTA_ESTADO.pop(str(chat_id), None)
            _OFERTA_LOTE_SELECCIONADO.pop(str(chat_id), None)
            _send(token, chat_id, "Cancelado.")
        else:
            _send(token, chat_id, _h_start())
        _answer_callback(token, cb_id)
        return

    message = update.get("message") or update.get("edited_message")
    if not message:
        return
    chat = message.get("chat") or {}
    chat_id = str(chat.get("id"))
    texto = (message.get("text") or "").strip()
    cfg = _cfg(db)
    if not _es_autorizado(chat_id, cfg):
        if texto:
            _send(token, chat_id, "⛔ No autorizado para consultar este negocio.")
        return
    if not texto:
        return

    # normalizar comando
    cmd = texto.split()[0].lower() if texto else ""
    print(f"[TelegramBot] chat={chat_id} texto={texto!r} cmd={cmd!r}", flush=True)
    # Manejo de entrada de texto pendiente (monto / cantidad)
    st = _OFERTA_ESTADO.get(str(chat_id))
    if st and st.get("step") in ("monto", "cantidad_texto") and not texto.startswith("/"):
        if st["step"] == "monto":
            try:
                val = float(texto.replace(",", "."))
            except ValueError:
                _send(token, chat_id, "❌ Número inválido. Escribí el monto (ej: 500):")
                return
            st["valor"] = val
            st["step"] = "dias"
            p = db.query(Producto).filter(Producto.id == st["prod_id"]).first()
            kb = {"inline_keyboard": [
                [{"text": "7 días", "callback_data": "oferta_dias:7"},
                 {"text": "14 días", "callback_data": "oferta_dias:14"},
                 {"text": "30 días", "callback_data": "oferta_dias:30"}],
                [{"text": "❌ Cancelar", "callback_data": "oferta_cancel"}],
            ]}
            _send(token, chat_id, f"🏷️ {_html.escape(p.nombre if p else '')}\n\n¿Por cuántos días?", reply_markup=kb)
            return
        elif st["step"] == "cantidad_texto":
            try:
                val = int(float(texto.replace(",", ".")))
            except ValueError:
                _send(token, chat_id, "❌ Número inválido. Escribí la cantidad (ej: 10):")
                return
            st["cantidad"] = val
            st["step"] = "preview"
            _mostrar_preview_oferta(db, token, chat_id, st)
            return
    # quitar @botname
    if "@" in cmd:
        cmd = cmd.split("@")[0]
    args = texto[len(texto.split()[0]):].strip() if " " in texto else ""

    if cmd in ("/start", "/help", "help", "ayuda", "hola"):
        _send(token, chat_id, _h_start())
    elif cmd in ("/stockbajo", "stockbajo", "stock bajo"):
        _h_stockbajo_menu_principal(token, chat_id)
    elif cmd in ("/stock", "stock"):
        _send(token, chat_id, _h_stock(db))
    elif cmd in ("/ventas", "ventas"):
        _send(token, chat_id, _h_ventas(db, args))
        kb = {"inline_keyboard": [[
            {"text": "Hoy", "callback_data": "ventas:hoy"},
            {"text": "Ayer", "callback_data": "ventas:ayer"},
            {"text": "Semana", "callback_data": "ventas:semana"},
        ]]}
        _send(token, chat_id, "Filtrar por:", reply_markup=kb)
    elif cmd in ("/egresos", "egresos"):
        _send(token, chat_id, _h_egresos(db, args))
    elif cmd in ("/ingresos", "ingresos"):
        _send(token, chat_id, _h_ingresos(db))
    elif cmd in ("/movimientos", "movimientos"):
        _send(token, chat_id, _h_movimientos(db))
    elif cmd in ("/detalle", "detalle"):
        _send(token, chat_id, _h_detalle_venta(db, args))
    elif cmd in ("/buscar", "buscar"):
        _send(token, chat_id, _h_buscar(db, args))
    elif cmd in ("/stockproducto", "stockproducto"):
        _send(token, chat_id, _h_stockproducto(db, args))
    elif cmd in ("/compraspendientes", "compraspendientes"):
        _send(token, chat_id, _h_compras_pendientes(db))
    elif cmd in ("/lotesvencidos", "lotesvencidos"):
        _send(token, chat_id, _h_lotes_vencidos(db))
    elif cmd in ("/vencimientos", "vencimientos"):
        texto = _h_vencimientos(db, args)
        kb = {"inline_keyboard": [[
            {"text": "🏷️ Crear oferta", "callback_data": "oferta:venc"},
            {"text": "❌ Cerrar", "callback_data": "oferta_cancel"},
        ]]}
        _send(token, chat_id, texto, reply_markup=kb)
    elif cmd in ("/alertas", "alertas"):
        _send(token, chat_id, _h_alertas(db))
    elif cmd in ("/dashboard", "dashboard"):
        _send(token, chat_id, _h_dashboard(db))
    elif cmd in ("/backup", "backup"):
        _send(token, chat_id, _h_backup(db))
    elif cmd in ("/anular", "anular"):
        _h_anular(db, token, chat_id, args)
    elif cmd in ("/caja", "caja"):
        _send(token, chat_id, _h_caja(db))
    elif cmd in ("/top", "top"):
        _send(token, chat_id, _h_top(db))
    elif cmd in ("/clientes", "clientes"):
        _send(token, chat_id, _h_clientes(db))
    elif cmd in ("/oferta", "oferta"):
        _h_oferta_inicio(db, token, chat_id, args)
    else:
        _send(token, chat_id, "❓ Comando no reconocido.\n" + _h_start())


def chequear_mensajes() -> None:
    """Job del scheduler: trae updates nuevos y los procesa."""
    db = SessionLocal()
    try:
        cfg = _cfg(db)
        if not cfg["interactivo"] or not cfg["token"] or not cfg["chat_id"]:
            return
        global _WEBHOOK_DELETED
        if not _WEBHOOK_DELETED:
            try:
                requests.post(f"{TG_API.format(token=cfg['token'])}/deleteWebhook", json={"drop_pending_updates": False}, timeout=10)
            except Exception:
                pass
            _WEBHOOK_DELETED = True
        offset = _offset(db)
        try:
            r = requests.get(
                f"{TG_API.format(token=cfg['token'])}/getUpdates",
                params={"offset": offset, "timeout": 2, "allowed_updates": ["message", "callback_query", "edited_message"]},
                timeout=10,
            )
        except requests.RequestException:
            return
        try:
            data = r.json()
        except ValueError:
            return
        # Conflicto por webhook activo: lo borramos y reintentamos una vez.
        if not r.ok and "webhook" in (data.get("description") or "").lower():
            try:
                requests.post(f"{TG_API.format(token=cfg['token'])}/deleteWebhook", json={"drop_pending_updates": False}, timeout=10)
            except requests.RequestException:
                pass
            try:
                r = requests.get(
                    f"{TG_API.format(token=cfg['token'])}/getUpdates",
                    params={"offset": offset, "timeout": 2, "allowed_updates": ["message", "callback_query", "edited_message"]},
                    timeout=10,
                )
                data = r.json()
            except (requests.RequestException, ValueError):
                return
        if not r.ok or not data.get("ok"):
            return
        updates = data.get("result") or []
        nuevo_offset = offset
        for u in updates:
            uid = u.get("update_id", 0)
            if uid >= nuevo_offset:
                nuevo_offset = uid + 1
            try:
                procesar_update(db, cfg["token"], u)
            except Exception as e:
                print(f"[TelegramBot] error procesando update {uid}: {e}")
        if nuevo_offset != offset:
            _set_offset(db, nuevo_offset)
    finally:
        db.close()
