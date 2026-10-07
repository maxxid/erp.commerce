"""Generación de PDF para etiquetas de precios.

Dos tamaños:
- 70x35mm: 3 columnas x 10 filas = 30 etiquetas/hoja A4
- 60x40mm: 3 columnas x 8 filas = 24 etiquetas/hoja A4

Opción borderless: usa toda la hoja A4 (210x297mm) sin márgenes.
"""

from io import BytesIO
from typing import List, Dict
import logging

# reportlab es una dependencia solo de este modulo. Se importa de forma perezosa
# para que la app arranque igual sin ella y el PDF falle solo cuando se pide.
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import black, white, HexColor
    from reportlab.pdfgen import canvas
    from reportlab.graphics.barcode import eanbc
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF
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
    "70x35": {
        "cols": 3, "rows": 10,
        "label_w": 70, "label_h": 35,
        "margin_x": 0, "margin_y": 0,
        "gap_x": 0, "gap_y": 0,
    },
    "60x40": {
        "cols": 3, "rows": 8,
        "label_w": 60, "label_h": 40,
        "margin_x": 0, "margin_y": 0,
        "gap_x": 0, "gap_y": 0,
    },
}

BARCODE_HEIGHT_RATIO = 0.35
BARCODE_PADDING_V = 2


def _es_ean13_valido(codigo: str) -> bool:
    """Verifica si el código es un EAN13 válido (13 dígitos numéricos)."""
    return codigo.isdigit() and len(codigo) == 13


def _dibujar_codigo_barras(c, x: float, y: float, w: float, h: float, codigo: str):
    """Dibuja código de barras EAN13 o Code128 fallback."""
    if not REPORTLAB_DISPONIBLE:
        return
    from reportlab.graphics.barcode import eanbc
    from reportlab.graphics.shapes import Drawing
    from reportlab.graphics import renderPDF

    if _es_ean13_valido(codigo):
        barcode = eanbc.Ean13BarcodeWidget(codigo)
        barcode.barHeight = h * BARCODE_HEIGHT_RATIO
        barcode.barWidth = 0.33 * mm
        bounds = barcode.getBounds()
        bw = bounds[2] - bounds[0]
        bh = bounds[3] - bounds[1]
        scale_x = w / bw
        scale_y = (h * BARCODE_HEIGHT_RATIO) / bh
        d = Drawing(w, h * BARCODE_HEIGHT_RATIO + BARCODE_PADDING_V * 2)
        d.add(barcode)
        renderPDF.draw(d, c, x, y + BARCODE_PADDING_V)
    else:
        c.setFont("Courier", 8)
        c.drawCentredString(x + w/2, y + h * 0.15, codigo[:20])


def _wrap_text(c, text: str, x: float, y: float, w: float, max_lines: int, font_size: int) -> float:
    """Dibuja texto con wrap, retorna nueva posición Y."""
    if not text:
        return y
    
    c.setFont("Helvetica", font_size)
    words = text.split()
    lines = []
    current = ""
    
    for word in words:
        test = current + (" " if current else "") + word
        if c.stringWidth(test, "Helvetica", font_size) <= w:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
            if len(lines) >= max_lines:
                break
    if current and len(lines) < max_lines:
        lines.append(current)
    
    line_h = font_size * 1.2
    for i, line in enumerate(lines[:max_lines]):
        c.drawString(x, y - i * line_h, line)
    
    return y - len(lines) * line_h


def _formatear_precio(valor: float) -> str:
    """Formatea precio con separador de miles y 2 decimales."""
    return f"$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def generar_etiquetas_pdf(
    productos: List["Producto"],
    tamano: str,
    borderless: bool,
    descripciones_editadas: Dict[int, str]
) -> bytes:
    """Genera PDF con etiquetas de precios."""
    if not REPORTLAB_DISPONIBLE:
        raise ReportlabNoDisponible(
            "reportlab no esta instalado. Instala con: pip install 'reportlab>=4.0'"
        )

    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor
    from reportlab.pdfgen import canvas

    A4_W, A4_H = A4

    layout = LAYOUTS[tamano]
    label_w = layout["label_w"] * mm
    label_h = layout["label_h"] * mm
    cols = layout["cols"]
    rows = layout["rows"]
    margin_x = layout["margin_x"] * mm
    margin_y = layout["margin_y"] * mm
    gap_x = layout["gap_x"] * mm
    gap_y = layout["gap_y"] * mm
    
    if borderless:
        page_w, page_h = A4_W, A4_H
    else:
        margin_x = 5 * mm
        margin_y = 5 * mm
        page_w, page_h = A4_W, A4_H
    
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))
    
    etiquetas_por_hoja = cols * rows
    total = len(productos)
    
    for idx, prod in enumerate(productos):
        hoja = idx // etiquetas_por_hoja
        pos_en_hoja = idx % etiquetas_por_hoja
        col = pos_en_hoja % cols
        row = pos_en_hoja // cols
        
        if pos_en_hoja == 0 and idx > 0:
            c.showPage()
        
        x = margin_x + col * (label_w + gap_x)
        y = page_h - margin_y - (row + 1) * (label_h + gap_y)
        
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
    """Dibuja una sola etiqueta."""
    padding = 2 * mm
    inner_w = w - 2 * padding
    inner_x = x + padding
    curr_y = y + h - padding
    
    from datetime import date
    fecha_hoy = date.today().strftime("%d/%m/%Y")
    codigo_num = prod.codigo_barras if prod.codigo_barras else ""
    
    if prod.marca:
        c.setFont("Helvetica-Bold", 7)
        c.drawString(inner_x, curr_y, prod.marca[:35])
        curr_y -= 9
    
    c.setStrokeColor(HexColor("#999999"))
    c.setLineWidth(0.3)
    c.line(inner_x, curr_y, inner_x + inner_w, curr_y)
    curr_y -= 4
    
    desc = descripcion_editada if descripcion_editada is not None else (prod.descripcion or "")
    curr_y = _wrap_text(c, desc, inner_x, curr_y, inner_w, max_lines=3, font_size=7)
    curr_y -= 2
    
    barcode_h = h * BARCODE_HEIGHT_RATIO
    barcode_y = curr_y - barcode_h - BARCODE_PADDING_V
    _dibujar_codigo_barras(c, inner_x, barcode_y, inner_w, barcode_h, codigo_num)
    curr_y = barcode_y - 2
    
    if prod.tipo_venta == "kilo" and prod.precio_por_kilo:
        c.setFont("Helvetica-Bold", 11)
        precio_str = _formatear_precio(prod.precio_por_kilo) + " /kg"
    else:
        c.setFont("Helvetica-Bold", 11)
        precio_str = _formatear_precio(prod.precio_venta)
    
    c.drawString(inner_x, curr_y, precio_str)
    
    c.setFont("Helvetica", 6)
    c.drawRightString(x + w - padding, curr_y + 2, fecha_hoy)
    
    curr_y -= 10
    if curr_y > y + padding:
        c.setFont("Courier", 6)
        c.drawCentredString(x + w/2, curr_y, codigo_num)