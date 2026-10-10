"""Generación de PDF para etiquetas de precios.

Dos tamaños:
- 70x35mm
- 60x40mm

Hoja A4 en horizontal (297x210mm). Columnas y filas se calculan dinámicamente
según el tamaño de etiqueta y los márgenes, para que nunca se desborden ni se
corten en el salto de página.
"""

from io import BytesIO
from typing import List, Dict
import logging

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas
    REPORTLAB_DISPONIBLE = True
except ImportError:  # pragma: no cover - depende del entorno
    REPORTLAB_DISPONIBLE = False
    logging.getLogger(__name__).warning(
        "reportlab no esta instalado: la ficha PDF de etiquetas va a fallar. "
        "Se instala con: pip install 'reportlab>=4.0'"
    )


class ReportlabNoDisponible(RuntimeError):
    """Se pidio la ficha PDF sin tener reportlab instalado."""


LAYOUTS = {
    "70x35": {"label_w": 70, "label_h": 35},
    "60x40": {"label_w": 60, "label_h": 40},
}


def _es_ean13_valido(codigo: str) -> bool:
    """Verifica si el código es un EAN13 válido (13 dígitos numéricos)."""
    return codigo.isdigit() and len(codigo) == 13


def _dibujar_codigo_barras(c, x: float, y: float, w: float, h: float, codigo: str):
    """Dibuja código de barras EAN13 o Code128 fallback, centrado en el ancho dado."""
    if not REPORTLAB_DISPONIBLE:
        return
    from reportlab.graphics.barcode import eanbc
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF

    if _es_ean13_valido(codigo):
        barcode = eanbc.Ean13BarcodeWidget(codigo)
        barcode.barHeight = h
        barcode.barWidth = 0.33 * mm
        bounds = barcode.getBounds()
        bw = bounds[2] - bounds[0]
        bh = bounds[3] - bounds[1]
        d = Drawing(bw, h)
        d.add(barcode)
        # Centrar el barcode dentro del ancho disponible
        offset_x = x + (w - bw) / 2
        renderPDF.draw(d, c, offset_x, y)
    else:
        c.setFont("Courier", 8)
        c.drawCentredString(x + w/2, y + h * 0.15, codigo[:20])


def _formatear_precio(valor: float) -> str:
    """Formatea precio con separador de miles y 2 decimales."""
    return f"$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generar_etiquetas_pdf(
    productos: List["Producto"],
    tamano: str,
    borderless: bool,
    descripciones_editadas: Dict[int, str]
) -> bytes:
    """Genera PDF con etiquetas de precios en A4 horizontal."""
    if not REPORTLAB_DISPONIBLE:
        raise ReportlabNoDisponible(
            "reportlab no esta instalado. Instala con: pip install 'reportlab>=4.0'"
        )

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas

    A4_W, A4_H = A4  # retrato
    page_w, page_h = A4_H, A4_W  # horizontal: 297 x 210 mm

    layout = LAYOUTS[tamano]
    label_w = layout["label_w"] * mm
    label_h = layout["label_h"] * mm

    if borderless:
        margin_x = margin_y = 0
    else:
        margin_x = margin_y = 5 * mm

    available_w = page_w - 2 * margin_x
    available_h = page_h - 2 * margin_y

    cols = max(1, int(available_w // label_w))
    rows = max(1, int(available_h // label_h))

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    etiquetas_por_hoja = cols * rows
    total = len(productos)

    for idx, prod in enumerate(productos):
        pos_en_hoja = idx % etiquetas_por_hoja

        if pos_en_hoja == 0 and idx > 0:
            c.showPage()

        col = pos_en_hoja % cols
        row = pos_en_hoja // cols
        x = margin_x + col * label_w
        y = page_h - margin_y - (row + 1) * label_h

        if not borderless:
            c.setStrokeColor(HexColor("#CCCCCC"))
            c.setLineWidth(0.3)
            c.rect(x, y, label_w, label_h)

        _dibujar_etiqueta(c, x, y, label_w, label_h, prod, descripciones_editadas.get(prod.id))

    c.save()
    return buffer.getvalue()


def _dibujar_etiqueta(
    c,
    x: float, y: float, w: float, h: float,
    prod: "Producto",
    descripcion_editada: str | None
):
    """Dibuja una sola etiqueta.

    Layout (de arriba a abajo):
      [ Marca .................. Precio ]
      ──────────────────────────────────
      Descripción (máx 2 líneas)
      [     código de barras            ]
    """
    from datetime import date
    padding = 3 * mm
    inner_w = w - 2 * padding
    inner_x = x + padding
    right_x = x + w - padding
    top_y = y + h - padding - 2 * mm  # aire extra arriba para que no se escape
    fecha_hoy = date.today().strftime("%d/%m/%Y")
    codigo_num = prod.codigo_barras or ""

    # ── Fila superior: marca (izq) + precio (der) en la misma línea ──
    baseline = top_y

    if prod.tipo_venta == "kilo" and prod.precio_por_kilo:
        precio_str = _formatear_precio(prod.precio_por_kilo) + " /kg"
    else:
        precio_str = _formatear_precio(prod.precio_venta)

    # Precio primero (para medir su ancho)
    c.setFont("Helvetica-Bold", 13)
    precio_w = c.stringWidth(precio_str, "Helvetica-Bold", 13)
    c.drawString(right_x - precio_w, baseline, precio_str)

    # Marca alineada a la izquierda, misma altura que el precio
    if prod.marca:
        c.setFont("Helvetica-Bold", 13)
        marca_text = prod.marca[:35]
        marca_w = c.stringWidth(marca_text, "Helvetica-Bold", 13)
        max_marca_w = inner_w - precio_w - 3 * mm
        if marca_w > max_marca_w:
            while marca_text and c.stringWidth(marca_text + "...", "Helvetica-Bold", 13) > max_marca_w:
                marca_text = marca_text[:-1]
            marca_text += "..."
        c.drawString(inner_x, baseline, marca_text)

    # Fecha debajo del precio, alineada a la derecha
    c.setFont("Helvetica", 6)
    fecha_w = c.stringWidth(fecha_hoy, "Helvetica", 6)
    c.drawString(right_x - fecha_w, baseline - 10, fecha_hoy)

    # ── Línea separadora ──
    sep_y = baseline - 12
    c.setStrokeColor(HexColor("#999999"))
    c.setLineWidth(0.3)
    c.line(inner_x, sep_y, inner_x + inner_w, sep_y)

    # ── Descripción (máx 2 líneas) ──
    desc_y = sep_y - 8
    desc = descripcion_editada if descripcion_editada is not None else (prod.descripcion or prod.nombre or "")
    if desc:
        c.setFont("Helvetica", 9)
        words = desc.split()
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if c.stringWidth(test, "Helvetica", 9) <= inner_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
                if len(lines) >= 2:
                    break
        if current and len(lines) < 2:
            lines.append(current)
        # Ellipsis en la última línea si se cortó
        if len(lines) == 2:
            last = lines[1]
            while last and c.stringWidth(last + "...", "Helvetica", 9) > inner_w:
                last = last[:-1]
            lines[1] = last + "..."
        for i, line in enumerate(lines):
            c.drawString(inner_x, desc_y - i * 10, line)
        desc_bottom = desc_y - (len(lines) - 1) * 10
    else:
        desc_bottom = desc_y

    # ── Código de barras ──
    barcode_h = 8 * mm
    barcode_y = desc_bottom - 3 * mm - barcode_h
    min_barcode_y = y + padding + 2 * mm
    if barcode_y < min_barcode_y:
        barcode_y = min_barcode_y
    _dibujar_codigo_barras(c, inner_x, barcode_y, inner_w, barcode_h, codigo_num)