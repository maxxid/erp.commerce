"""Ficha PDF de analisis de precios de un producto.

A4 horizontal para que la tabla de historial entre comoda. Resalta la fila del
menor precio: el online mas bajo y el menor costo historico.
"""

from io import BytesIO
from datetime import datetime

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer,
)

from app.services.lookup_service import nombre_fuente, esta_experimental

ANCHO_UTIL = landscape(A4)[0] - 24 * mm

VERDE = colors.HexColor("#047857")
VERDE_CLARO = colors.HexColor("#d1fae5")
AMBAR = colors.HexColor("#b45309")
AMBAR_CLARO = colors.HexColor("#fef3c7")
GRIS = colors.HexColor("#6b7280")
GRIS_LINEA = colors.HexColor("#e5e7eb")
ROJO = colors.HexColor("#b91c1c")

C_10 = ParagraphStyle("c10", fontSize=9, leading=11)
C_10_D = ParagraphStyle("c10d", parent=C_10, textColor=colors.white)
C_TIT = ParagraphStyle("tit", fontSize=16, leading=19, textColor=colors.HexColor("#111827"))
C_SEC = ParagraphStyle("sec", fontSize=11, leading=14, textColor=colors.HexColor("#374151"), spaceBefore=2)


def _texto_oferta(desc):
    """Columna de oferta: precio tachado y, si hay, el minimo de compra.

    Sin el minimo, un 3x2 se lee como si el precio de una sola unidad hubiera
    bajado, y no es el caso: el precio efectivo sale comprando N.
    """
    if not desc or not desc.get("activo") or not desc.get("precio_oferta"):
        return ""
    texto = f"antes {_fc(desc.get('precio_original'))}"
    minimo = desc.get("cantidad_minima")
    if minimo:
        promo = desc.get("promocion") or "por cantidad"
        texto += f" ({promo}, min. {minimo} u.)"
    return texto


def _fc(valor):
    if valor is None:
        return "-"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "-"
    entero = int(v) == v
    miles = f"{int(v):,}".replace(",", ".")
    return f"$ {miles}" if entero else f"$ {miles},{int(round((v - int(v)) * 100)):02d}"


def _fecha(iso):
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(iso)[:10]


def _p(texto, style=C_10):
    return Paragraph(texto, style)


def _tabla(encabezados, filas, anchos, resaltar=None):
    datos = [[_p(h, C_10_D) for h in encabezados]]
    for f in filas:
        datos.append([_p(str(c)) for c in f])

    t = Table(datos, colWidths=anchos, repeatRows=1)
    estilo = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#374151")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("GRID", (0, 0), (-1, -1), 0.4, GRIS_LINEA),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if resaltar is not None:
        for idx, tono in resaltar:
            estilo.append(("BACKGROUND", (0, idx), (-1, idx), tono))
    t.setStyle(TableStyle(estilo))
    return t


def _kpis(analisis):
    """Fila de KPIs: lo que importa mirar de un vistazo."""
    online = analisis.get("online")
    ultimo = analisis.get("ultimo_costo")
    mejor = analisis.get("mejor_historico")
    proveedor = analisis.get("mejor_oferta_proveedor")
    venta = (analisis.get("producto") or {}).get("precio_venta")

    celdas = [
        ("Precio de venta", _fc(venta), GRIS),
        ("Último costo pagado", _fc(ultimo["precio_unitario"] if ultimo else None),
         AMBAR if ultimo else GRIS),
        ("Mejor costo histórico", _fc(mejor["precio_unitario"] if mejor else None),
         VERDE if mejor else GRIS),
        ("Mejor oferta proveedor", _fc(proveedor), VERDE if proveedor else GRIS),
        ("Mejor precio online hoy", _fc(online["precio"] if online else None),
         VERDE if online else GRIS),
    ]

    titulo_style = ParagraphStyle("kt", fontSize=7.5, leading=9, textColor=GRIS)
    valor_style = ParagraphStyle("kv", fontSize=12, leading=14)

    fila_tit = [_p(t, titulo_style) for t, _, _ in celdas]
    fila_val = []
    for _, v, color in celdas:
        st = ParagraphStyle("kvx", parent=valor_style, textColor=color)
        fila_val.append(_p(v, st))

    ancho = ANCHO_UTIL / len(celdas)
    t = Table([fila_tit, fila_val], colWidths=[ancho] * len(celdas))
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f9fafb")),
        ("BOX", (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_LINEA),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _bloque_recomendacion(analisis):
    """Frase que dice que hacer. Es lo primero que la gente lee."""
    online = analisis.get("online")
    ultimo = analisis.get("ultimo_costo")
    proveedor = analisis.get("mejor_oferta_proveedor")
    historial = analisis.get("historial") or []

    if not online:
        return None

    partes = []
    fuente = nombre_fuente(online.get("fuente"))
    precio = _fc(online["precio"])

    if proveedor is not None and proveedor < online["precio"]:
        partes.append(
            f"Conviene comprar a un proveedor: el mejor costo de lista ({_fc(proveedor)}) "
            f"está por debajo de {fuente} ({precio})."
        )
    elif ultimo and ultimo["precio_unitario"] < online["precio"]:
        partes.append(
            f"Tu proveedor habitual sigue mejor: la última compra fue {_fc(ultimo['precio_unitario'])} "
            f"en {ultimo['proveedor_nombre']}."
        )
    elif proveedor is not None and abs(proveedor - online["precio"]) < 0.01:
        partes.append(f"Tu proveedor y {fuente} están al mismo precio ({precio}).")
    else:
        partes.append(
            f"{fuente} está más barato hoy ({precio}). "
            f"Revisá si te conviene el traslado antes de cambiar."
        )

    if historial:
        mejor = min(historial, key=lambda h: h["precio_unitario"])
        partes.append(
            f"El precio más bajo que pagaste fue {_fc(mejor['precio_unitario'])} "
            f"a {mejor['proveedor_nombre']}, el {_fecha(mejor['fecha'])}."
        )

    estilo = ParagraphStyle("rec", fontSize=10, leading=14, textColor=colors.HexColor("#1f2937"))
    return _p(" ".join(partes), estilo)


def generar_analisis_precios_pdf(analisis: dict) -> bytes:
    """Genera la ficha PDF. Devuelve los bytes del archivo."""
    producto = analisis.get("producto") or {}
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title=f"Analisis de precios - {producto.get('nombre', '')}",
        author="ApexERP",
    )

    elementos = []

    nombre = _p(_escapar(producto.get("nombre") or "Producto"), C_TIT)
    meta = ParagraphStyle(
        "meta", fontSize=8.5, leading=11, textColor=GRIS,
    )
    marca = producto.get("marca") or "-"
    codigo = producto.get("codigo_barras") or "-"
    generado = datetime.now().strftime("%d/%m/%Y %H:%M")
    subtitulo = _p(
        f"{_escapar(marca)} &nbsp;|&nbsp; Código: {_escapar(str(codigo))} "
        f"&nbsp;|&nbsp; Generado: {generado}",
        meta,
    )
    elementos.append(nombre)
    elementos.append(subtitulo)
    elementos.append(Spacer(1, 7))

    elementos.append(_kpis(analisis))
    elementos.append(Spacer(1, 8))

    recomendacion = _bloque_recomendacion(analisis)
    if recomendacion:
        elementos.append(recomendacion)
        elementos.append(Spacer(1, 10))

    precios = analisis.get("precios_online") or []
    elementos.append(_p("Precios online de hoy", C_SEC))
    if precios:
        filas = []
        resaltar = []
        for i, r in enumerate(precios, start=1):
            desc = r.get("descuento")
            oferta = _texto_oferta(desc)
            etiqueta = nombre_fuente(r.get("fuente"))
            if esta_experimental(r.get("fuente")):
                etiqueta += " (puede no ser el mismo producto)"
            filas.append([
                _escapar(etiqueta),
                _fc(r.get("precio")),
                oferta,
                _escapar(str(r.get("nombre", ""))[:70]),
            ])
            if analisis.get("online") and r.get("fuente") == analisis["online"].get("fuente"):
                resaltar.append((i, VERDE_CLARO))
        elementos.append(_tabla(
            ["Fuente", "Precio", "Oferta", "Producto"],
            filas,
            [28 * mm, 28 * mm, 32 * mm, ANCHO_UTIL - 88 * mm],
            resaltar,
        ))
    else:
        elementos.append(_p("Sin resultados online para este código.", meta))
    elementos.append(Spacer(1, 10))

    proveedores = analisis.get("proveedores") or []
    elementos.append(_p("Costo por proveedor", C_SEC))
    if proveedores:
        filas = []
        resaltar = []
        mejor_prov = analisis.get("mejor_oferta_proveedor")
        for i, p in enumerate(proveedores, start=1):
            marca_p = "Principal" if p.get("es_principal") else ""
            filas.append([
                _escapar(p.get("nombre", "")),
                marca_p,
                _fc(p.get("costo_actual")),
                _fc(p.get("ultimo_precio_pagado")),
                _fecha(p.get("ultima_fecha_pago")),
                f"{p['plazo_entrega_dias']} días" if p.get("plazo_entrega_dias") is not None else "-",
            ])
            if mejor_prov is not None and p.get("costo_actual") == mejor_prov:
                resaltar.append((i, VERDE_CLARO))
        elementos.append(_tabla(
            ["Proveedor", "", "Costo actual", "Último pagado", "Fecha", "Plazo"],
            filas,
            [ANCHO_UTIL - 145 * mm, 24 * mm, 30 * mm, 30 * mm, 26 * mm, 35 * mm],
            resaltar,
        ))
    else:
        elementos.append(_p("Este producto no tiene proveedores cargados.", meta))
    elementos.append(Spacer(1, 10))

    historial = analisis.get("historial") or []
    elementos.append(_p("Historial de compras", C_SEC))
    if historial:
        filas = []
        resaltar = []
        mejor_id = (analisis.get("mejor_historico") or {}).get("compra_id")
        for i, h in enumerate(historial, start=1):
            filas.append([
                _fecha(h.get("fecha")),
                _escapar(str(h.get("numero", ""))),
                _escapar(h.get("proveedor_nombre", "")),
                f"{h.get('cantidad_recibida', 0):g}",
                _fc(h.get("precio_unitario")),
                _fc(h.get("subtotal")),
                _escapar(str(h.get("estado", ""))),
            ])
            if mejor_id is not None and h.get("compra_id") == mejor_id:
                resaltar.append((i, AMBAR_CLARO))
        elementos.append(_tabla(
            ["Fecha", "Orden", "Proveedor", "Cant.", "Precio unit.", "Subtotal", "Estado"],
            filas,
            [24 * mm, 30 * mm, ANCHO_UTIL - 155 * mm, 20 * mm, 28 * mm, 28 * mm, 25 * mm],
            resaltar,
        ))
        elementos.append(Spacer(1, 4))
        elementos.append(_p(
            "En amarillo, la compra con el menor precio unitario pagado. "
            "Las compras anuladas no se incluyen.",
            meta,
        ))
    else:
        elementos.append(_p("Este producto todavía no tiene compras registradas.", meta))

    doc.build(elementos)
    return buffer.getvalue()


def _escapar(texto):
    """Escapa los caracteres que reportlab interpreta como marcado."""
    if texto is None:
        return ""
    return (
        str(texto)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
