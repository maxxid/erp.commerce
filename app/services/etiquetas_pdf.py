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
    descripciones_editadas: Dict[int, str],
    modelo: str = "completa",
) -> bytes:
    """Genera PDF con etiquetas de precios en A4 horizontal.

    modelo:
      - "completa": marca + precio + fecha + descripción + código de barras
      - "sencilla": solo precio grande + descripción, ocupando todo el espacio
    """
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

        if modelo == "sencilla":
            _dibujar_etiqueta_sencilla(c, x, y, label_w, label_h, prod, descripciones_editadas.get(prod.id))
        else:
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


def _dibujar_etiqueta_sencilla(
    c,
    x: float, y: float, w: float, h: float,
    prod: "Producto",
    descripcion_editada: str | None
):
    """Etiqueta sencilla: marca + precio + descripción sobre marco ornamental.

    Sin código de barras ni fecha. Marco doble azul con florituras de
    espiral en las 4 esquinas (estilo certificado). El contenido va
    centrado y ocupa todo el interior del marco.
    """
    import math

    color = HexColor("#1F3A6E")

    # ── Marco doble ──
    inset1 = 1.5 * mm
    inset2 = 2.3 * mm
    c.setStrokeColor(color)
    c.setLineWidth(1.4)
    c.rect(x + inset1, y + inset1, w - 2 * inset1, h - 2 * inset1)
    c.setLineWidth(0.6)
    c.rect(x + inset2, y + inset2, w - 2 * inset2, h - 2 * inset2)

    # ── Florituras de esquina ──
    c.setFillColor(color)
    s = 4.6 * mm
    esquinas = [
        (x + inset2, y + h - inset2, 1, -1),
        (x + w - inset2, y + h - inset2, -1, -1),
        (x + inset2, y + inset2, 1, 1),
        (x + w - inset2, y + inset2, -1, 1),
    ]
    for cx, cy, sx, sy in esquinas:
        c.saveState()
        c.translate(cx, cy)
        c.scale(sx, sy)
        _floritura_esquina(c, s, math)
        c.restoreState()

    # ── Contenido: centrado dentro del marco ──
    padding = 4.5 * mm
    inner_w = w - 2 * padding
    inner_x = x + padding
    centro = x + w / 2
    top_y = y + h - padding

    cursor = top_y

    # Marca arriba, centrada
    if prod.marca:
        marca_str = prod.marca[:40]
        marca_fs = 10
        while marca_fs > 6.5 and c.stringWidth(marca_str, "Helvetica-Bold", marca_fs) > inner_w:
            marca_fs -= 0.5
        c.setFillColor(HexColor("#111111"))
        c.setFont("Helvetica-Bold", marca_fs)
        c.drawCentredString(centro, cursor - marca_fs, marca_str)
        cursor -= marca_fs + 1.5 * mm

    # Precio grande, centrado; baja de tamaño si no entra
    if prod.tipo_venta == "kilo" and prod.precio_por_kilo:
        precio_str = _formatear_precio(prod.precio_por_kilo) + " /kg"
    else:
        precio_str = _formatear_precio(prod.precio_venta)
    precio_fs = 20
    while precio_fs > 10 and c.stringWidth(precio_str, "Helvetica-Bold", precio_fs) > inner_w:
        precio_fs -= 1
    c.setFont("Helvetica-Bold", precio_fs)
    c.drawCentredString(centro, cursor - precio_fs, precio_str)
    cursor -= precio_fs + 4 * mm

    # Descripción: llena todo el resto, con las líneas que entren (2-3 típico)
    desc = descripcion_editada if descripcion_editada is not None else (prod.descripcion or prod.nombre or "")
    if desc:
        desc_font = 9.5
        line_height = desc_font + 1.5
        desc_top = cursor
        max_lines = max(1, int((desc_top - (y + padding)) / line_height))
        c.setFont("Helvetica", desc_font)
        words = desc.split()
        lines = []
        current = ""
        for word in words:
            test = (current + " " + word).strip()
            if c.stringWidth(test, "Helvetica", desc_font) <= inner_w:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
                if len(lines) >= max_lines:
                    break
        if current and len(lines) < max_lines:
            lines.append(current)
        if len(lines) == max_lines and words:
            last = lines[-1]
            while last and c.stringWidth(last + "...", "Helvetica", desc_font) > inner_w:
                last = last[:-1]
            lines[-1] = last + "..."
        c.setFillColor(HexColor("#111111"))
        for i, line in enumerate(lines):
            c.drawCentredString(centro, desc_top - i * line_height, line)


def _floritura_esquina(c, s: float, math_mod):
    """Floritura de esquina: dos espejos de espiral + tallos ondulados.

    Se asume la transformación ya aplicada: esquina en (0,0) e interior
    de la etiqueta en el cuadrante (+x, +y). s = tamaño aproximado.
    """
    # Espiral principal: ojo en la diagonal, cola cayendo sobre el eje x
    # local (un borde de la etiqueta). Espejo de la diagonal → cola en eje y.
    ojo_x = ojo_y = s * 0.62
    r0 = s * 0.70
    r1 = s * 0.06
    vueltas = 1.35
    # Ángulo inicial: la cola aterriza sobre y=0 (borde)
    sin0 = -ojo_y / r0
    ang0 = math_mod.asin(max(-1.0, sin0))
    n = 40

    def dibujar_espiral(swap):
        p = c.beginPath()
        for i in range(n + 1):
            t = i / n
            ang = ang0 - t * vueltas * 2 * math_mod.pi  # sentido horario
            r = r0 * (r1 / r0) ** t
            px = ojo_x + r * math_mod.cos(ang)
            py = ojo_y + r * math_mod.sin(ang)
            if swap:
                px, py = py, px
            if i == 0:
                p.moveTo(px, py)
            else:
                p.lineTo(px, py)
        c.drawPath(p)

    c.setLineWidth(0.6)
    dibujar_espiral(swap=False)
    dibujar_espiral(swap=True)

    # Tallo ondulado desde cada cola, siguiendo el borde
    cola_x = ojo_x + r0 * math_mod.cos(ang0)
    for swap in (False, True):
        p = c.beginPath()
        x0, y0 = cola_x, 0.01 * s
        if swap:
            x0, y0 = y0, x0
        p.moveTo(x0, y0)
        c1 = (1.10 * s, 0.10 * s)
        c2 = (1.22 * s, -0.04 * s)
        e = (1.38 * s, 0.08 * s)
        if swap:
            c1, c2, e = (c1[1], c1[0]), (c2[1], c2[0]), (e[1], e[0])
        p.curveTo(c1[0], c1[1], c2[0], c2[1], e[0], e[1])
        c.drawPath(p)
        # Rizito al final del tallo
        p2 = c.beginPath()
        rq = s * 0.16
        eye = (e[0] + rq * 0.4, e[1] + rq * 0.9)
        for i in range(14):
            t = i / 13
            ang = -math_mod.pi * 0.55 - t * 0.9 * 2 * math_mod.pi
            r = rq * (0.12) ** t
            px = eye[0] + r * math_mod.cos(ang)
            py = eye[1] + r * math_mod.sin(ang)
            if swap:
                px, py = py, px
            if i == 0:
                p2.moveTo(px, py)
            else:
                p2.lineTo(px, py)
        c.drawPath(p2)

    # Punto pequeño en el vértice
    c.circle(s * 0.14, s * 0.14, s * 0.05, stroke=0, fill=1)