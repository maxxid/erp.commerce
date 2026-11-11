"""Reporte PDF de productos a reponer, agrupados por proveedor.

Misma regla de "bajo stock" que /productos/stock-bajo (stock_service),
así el papel y la pantalla no se contradicen. A4 horizontal para que entren
las columnas de precio y fecha.

reportlab es opcional: si falta, la app arranca igual y el PDF falla con 503
cuando se pide (mismo criterio que analisis_precios_pdf).
"""

from io import BytesIO
from datetime import datetime
import logging

try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (
        SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak,
    )
    REPORTLAB_DISPONIBLE = True
except ImportError:  # pragma: no cover - depende del entorno
    REPORTLAB_DISPONIBLE = False

    logging.getLogger(__name__).warning(
        "reportlab no esta instalado: el PDF de reposicion por proveedor va a "
        "fallar. Se instala con: pip install 'reportlab>=4.0'"
    )


class ReportlabNoDisponible(RuntimeError):
    """Se pidio el PDF sin tener reportlab instalado."""


if REPORTLAB_DISPONIBLE:
    ANCHO_UTIL = landscape(A4)[0] - 24 * mm

    GRIS = colors.HexColor("#6b7280")
    GRIS_LINEA = colors.HexColor("#e5e7eb")
    ROJO_CLARO = colors.HexColor("#fee2e2")
    AMBAR_CLARO = colors.HexColor("#fef3c7")

    C_10 = ParagraphStyle("c10", fontSize=8.5, leading=10.5)
    C_10_D = ParagraphStyle("c10d", parent=C_10, textColor=colors.white)
    C_TIT = ParagraphStyle("tit", fontSize=16, leading=19, textColor=colors.HexColor("#111827"))
    C_SEC = ParagraphStyle("sec", fontSize=11, leading=14, textColor=colors.HexColor("#374151"), spaceBefore=2)
    C_META = ParagraphStyle("meta", fontSize=8.5, leading=11, textColor=GRIS)

    ANCHOS = [30 * mm, 65 * mm, 28 * mm, 16 * mm, 16 * mm, 18 * mm,
              26 * mm, 24 * mm, 25 * mm, 25 * mm]
else:
    ANCHO_UTIL = GRIS = GRIS_LINEA = ROJO_CLARO = AMBAR_CLARO = None
    ANCHOS = None
    C_10 = C_10_D = C_TIT = C_SEC = C_META = None


COLUMNAS = [
    "Código", "Producto", "Marca", "Stock", "Mínimo", "Reponer",
    "Últ. pago", "Últ. compra", "Costo lista", "Venta",
]


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


def _num(valor):
    if valor is None:
        return "-"
    try:
        v = float(valor)
    except (TypeError, ValueError):
        return "-"
    if int(v) == v:
        return str(int(v))
    return f"{v:.2f}".replace(".", ",")


def _fecha(iso):
    if not iso:
        return "-"
    try:
        return datetime.fromisoformat(str(iso)).strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(iso)[:10]


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
    if resaltar:
        for idx, tono in resaltar:
            estilo.append(("BACKGROUND", (0, idx), (-1, idx), tono))
    t.setStyle(TableStyle(estilo))
    return t


def _fila_producto(p):
    return [
        _escapar(p.get("codigo_barras") or "-"),
        _escapar(p.get("nombre") or "-"),
        _escapar(p.get("marca") or "-"),
        _num(p.get("stock_actual")),
        _num(p.get("stock_minimo")),
        _num(p.get("faltante")),
        _fc(p.get("ultimo_precio_pagado")),
        _fecha(p.get("ultima_fecha_pago")),
        _fc(p.get("costo_lista")),
        _fc(p.get("precio_venta")),
    ]


def _seccion(grupo):
    """Elementos de un bloque de proveedor."""
    nombre = grupo.get("nombre") or "Sin proveedor"
    productos = grupo.get("productos") or []

    contacto = [x for x in (grupo.get("telefono"), grupo.get("email")) if x]
    detalle = f" · {_escapar(' · '.join(contacto))}" if contacto else ""
    sin_stock = sum(1 for p in productos if float(p.get("stock_actual") or 0) <= 0)

    elementos = [
        _p(_escapar(nombre), C_SEC),
        _p(
            f"{len(productos)} producto(s) a reponer · {sin_stock} sin stock"
            f"{detalle}",
            C_META,
        ),
        Spacer(1, 5),
    ]

    if not productos:
        elementos.append(_p("Sin productos bajo stock para este proveedor.", C_META))
        return elementos

    filas = []
    resaltar = []
    for i, p in enumerate(productos, start=1):
        filas.append(_fila_producto(p))
        sin_stock_fila = float(p.get("stock_actual") or 0) <= 0
        resaltar.append((i, ROJO_CLARO if sin_stock_fila else AMBAR_CLARO))

    elementos.append(_tabla(COLUMNAS, filas, ANCHOS, resaltar))
    return elementos


def _generar(grupos, incluir_resumen):
    if not REPORTLAB_DISPONIBLE:
        raise ReportlabNoDisponible(
            "No se puede generar el PDF de reposición porque falta la librería "
            "reportlab. Se instala con: pip install 'reportlab>=4.0' y después "
            "sudo systemctl restart erp-comercio"
        )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=10 * mm, bottomMargin=10 * mm,
        title="Reposición por proveedor",
        author="ApexERP",
    )

    elementos = [
        _p("Reposición por proveedor", C_TIT),
        _p(
            f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} · "
            f"{_escapar('Productos en stock bajo o sin stock')}",
            C_META,
        ),
        Spacer(1, 8),
    ]

    con_productos = [g for g in grupos if g.get("productos")]
    if not con_productos:
        elementos.append(_p("No hay productos bajo stock ni sin stock.", C_META))
        doc.build(elementos)
        return buffer.getvalue()

    if incluir_resumen:
        filas = []
        for g in con_productos:
            productos = g.get("productos") or []
            sin_stock = sum(1 for p in productos if float(p.get("stock_actual") or 0) <= 0)
            filas.append([
                _escapar(g.get("nombre") or "Sin proveedor"),
                str(len(productos)),
                str(sin_stock),
            ])
        elementos.append(_p("Resumen", C_SEC))
        elementos.append(Spacer(1, 4))
        elementos.append(_tabla(
            ["Proveedor", "Productos", "Sin stock"],
            filas,
            [ANCHO_UTIL - 60 * mm, 30 * mm, 30 * mm],
        ))
        elementos.append(Spacer(1, 6))

    for i, grupo in enumerate(con_productos):
        if incluir_resumen or i > 0:
            elementos.append(PageBreak())
        elementos.extend(_seccion(grupo))

    elementos.append(Spacer(1, 8))
    elementos.append(_p(
        "Regla de reposición: producto activo que controla stock con stock <= 0 "
        "o con mínimo definido y stock <= mínimo. "
        "El último precio y la fecha salen de las compras recibidas o parciales.",
        C_META,
    ))

    doc.build(elementos)
    return buffer.getvalue()


def generar_stock_proveedores_pdf(grupos) -> bytes:
    """Reporte completo: resumen y una sección por proveedor."""
    return _generar(grupos, incluir_resumen=True)


def generar_stock_proveedor_pdf(grupo: dict) -> bytes:
    """Reporte de un solo proveedor."""
    return _generar([grupo], incluir_resumen=False)
