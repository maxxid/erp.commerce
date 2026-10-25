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
            requests.post(f"{TG_API.format(token=token)}/sendMessage", json=payload, timeout=20)
        except requests.RequestException:
            pass


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
        "/stockbajo — productos bajo mínimo (elige categoría)\n"
        "/stock — resumen de stock\n"
        "/ventas — ventas de hoy\n"
        "/ventas YYYY-MM-DD — ventas de un día\n"
        "/caja — estado de caja\n"
        "/top — top 5 productos del mes\n"
        "/clientes — clientes con deuda\n"
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
    lineas = [f"📦 <b>{nombre}</b>"]
    if desc and desc != nombre:
        lineas.append(f"   {desc}")
    lineas.append(f"   Stock: {p.stock_actual:g} / Mín: {p.stock_minimo:g}")
    if por_proveedor:
        lineas.append(f"   Marca: {marca}")
    else:
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
    fecha_local = _parse_fecha(fecha_arg)
    if fecha_local is None:
        fecha_local = datetime.now(TZ_AR).date()
    desde = _inicio_dia_utc(fecha_local)
    hasta = desde + timedelta(days=1)
    ventas = db.query(Venta).filter(
        Venta.estado == "confirmada",
        Venta.fecha >= desde,
        Venta.fecha < hasta,
    ).all()
    total = sum(v.total or 0 for v in ventas)
    tickets = len(ventas)
    promedio = (total / tickets) if tickets else 0
    # desglose por medio
    por_medio: Dict[str, float] = {}
    for v in ventas:
        por_medio[v.medio_pago or "efectivo"] = por_medio.get(v.medio_pago or "efectivo", 0) + (v.total or 0)
    lineas = [
        f"💰 <b>Ventas — {fecha_local.strftime('%d/%m/%Y')}</b>",
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


# ---------- procesamiento ----------

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
    cmd = texto.split()[0].lower()
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
    elif cmd in ("/caja", "caja"):
        _send(token, chat_id, _h_caja(db))
    elif cmd in ("/top", "top"):
        _send(token, chat_id, _h_top(db))
    elif cmd in ("/clientes", "clientes"):
        _send(token, chat_id, _h_clientes(db))
    elif cmd in ("/resumen", "resumen"):
        _send(token, chat_id, _h_resumen(db))
    else:
        _send(token, chat_id, "❓ Comando no reconocido.\n" + _h_start())


def chequear_mensajes() -> None:
    """Job del scheduler: trae updates nuevos y los procesa."""
    db = SessionLocal()
    try:
        cfg = _cfg(db)
        if not cfg["interactivo"] or not cfg["token"] or not cfg["chat_id"]:
            return
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
