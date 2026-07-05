"""
Generación de PDF para facturas electrónicas 80mm
Rediseño completo - Versión 3.0
"""

import base64
import json
from io import BytesIO
from datetime import datetime
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import black, white, HexColor
from reportlab.graphics.barcode import qr

WIDTH_MM = 80
WIDTH = WIDTH_MM * mm

FONT = "Helvetica"
FONT_BOLD = "Helvetica-Bold"

COLOR_TEXT = black
COLOR_GRAY = HexColor("#666666")
COLOR_LIGHT = HexColor("#DDDDDD")
COLOR_DARK = HexColor("#333333")
COLOR_BG_HEADER = HexColor("#F5F5F5")
COLOR_TOTAL_BG = black

LEFT = 5 * mm
RIGHT = WIDTH - LEFT
CONTENT_WIDTH = RIGHT - LEFT


def money_arg(value):
    """Formatea número como peso argentino: $1.234,56"""
    return "${:,.2f}".format(float(value)).replace(",", "X").replace(".", ",").replace("X", ".")


class Ticket80:
    def __init__(self, canvas_obj, page_height):
        self.c = canvas_obj
        self.y = page_height - 8 * mm

    def space(self, mm_space=2):
        self.y -= mm_space * mm

    def hr(self, margin=0, color=None):
        if color is None:
            color = COLOR_LIGHT
        self.c.setStrokeColor(color)
        self.c.line(LEFT + margin, self.y, RIGHT - margin, self.y)
        self.y -= 3 * mm

    def double_hr(self):
        self.c.setStrokeColor(COLOR_LIGHT)
        self.c.line(LEFT, self.y, RIGHT, self.y)
        self.y -= 1.5 * mm
        self.c.line(LEFT, self.y, RIGHT, self.y)
        self.y -= 3 * mm

    def text(self, text, size=8, bold=False, align="left", color=COLOR_TEXT):
        self.c.setFillColor(color)
        self.c.setFont(FONT_BOLD if bold else FONT, size)
        if align == "left":
            self.c.drawString(LEFT, self.y, str(text))
        elif align == "right":
            self.c.drawRightString(RIGHT, self.y, str(text))
        else:
            self.c.drawCentredString(WIDTH / 2, self.y, str(text))
        self.y -= size * 0.6 * mm

    def section(self, title):
        self.space(2)
        self.c.setFillColor(COLOR_BG_HEADER)
        self.c.rect(LEFT, self.y - 5 * mm, CONTENT_WIDTH, 6 * mm, fill=1, stroke=0)
        self.c.setFillColor(COLOR_TEXT)
        self.c.setFont(FONT_BOLD, 9)
        self.c.drawString(LEFT + 2 * mm, self.y + 1, title.upper())
        self.y -= 7 * mm

    def key_value(self, key, value):
        self.c.setFont(FONT, 8)
        self.c.drawString(LEFT, self.y, str(key))
        self.c.drawRightString(RIGHT, self.y, str(value))
        self.y -= 4.5 * mm

    def logo_placeholder(self):
        w = 32 * mm
        h = 14 * mm
        x = (WIDTH - w) / 2
        self.c.setDash(3, 2)
        self.c.rect(x, self.y - h, w, h, stroke=1, fill=0)
        self.c.setDash()
        self.c.setFont(FONT, 8)
        self.c.drawCentredString(WIDTH / 2, self.y - 8, "LOGO")
        self.y -= h + 2 * mm

    def factura_letter(self, letra):
        box_size = 8 * mm
        x = WIDTH - LEFT - box_size - 2 * mm
        y = self.y - box_size
        self.c.setStrokeColor(COLOR_DARK)
        self.c.rect(x, y, box_size, box_size, stroke=1, fill=0)
        self.c.setFont(FONT_BOLD, 14)
        self.c.drawCentredString(x + box_size / 2, y + box_size / 2 - 2, letra)
        self.y -= box_size + 2 * mm

    def product(self, nombre, cantidad, precio, subtotal):
        nombre = nombre.upper()
        max_chars = 38
        while len(nombre) > max_chars:
            self.c.setFont(FONT_BOLD, 8)
            self.c.drawString(LEFT, self.y, nombre[:max_chars])
            nombre = nombre[max_chars:]
            self.y -= 4 * mm
        self.c.setFont(FONT_BOLD, 8)
        self.c.drawString(LEFT, self.y, nombre)
        self.y -= 4 * mm
        self.c.setFont(FONT, 8)
        cantidad_str = str(int(cantidad)) if cantidad == int(cantidad) else str(cantidad)
        self.c.drawString(LEFT + 2 * mm, self.y, f"{cantidad_str} x {money_arg(precio)}")
        self.c.drawRightString(RIGHT, self.y, money_arg(subtotal))
        self.y -= 6 * mm
        self.c.setStrokeColor(HexColor("#ECECEC"))
        self.c.line(LEFT, self.y, RIGHT, self.y)
        self.y -= 2 * mm

    def total_box(self, total_str):
        h = 9 * mm
        self.c.setFillColor(COLOR_TOTAL_BG)
        self.c.rect(LEFT, self.y - h, CONTENT_WIDTH, h, fill=1, stroke=0)
        self.c.setFillColor(white)
        self.c.setFont(FONT_BOLD, 11)
        self.c.drawString(LEFT + 2 * mm, self.y - 6 * mm, "TOTAL")
        self.c.drawRightString(RIGHT - 2 * mm, self.y - 6 * mm, total_str)
        self.c.setFillColor(COLOR_TEXT)
        self.y -= h + 2 * mm

    def qr_code(self, qr_data: dict):
        size = 24 * mm
        x = (WIDTH - size) / 2
        qr_url = self._build_arca_qr_url(qr_data)
        try:
            qr_code_widget = qr.QrCode(qr_url, barWidth=4, barHeight=4)
            qr_code_widget.drawAt((x + 2 * mm), self.y - size - 2 * mm, self.c)
        except Exception as e:
            self.c.setStrokeColor(COLOR_LIGHT)
            self.c.setDash(2, 2)
            self.c.rect(x, self.y - size, size, size, stroke=1, fill=0)
            self.c.setDash()
            self.c.setFillColor(COLOR_TEXT)
            self.c.setFont(FONT, 8)
            self.c.drawCentredString(WIDTH / 2, self.y - size / 2 - 3, "QR")
        self.c.setFillColor(COLOR_TEXT)
        self.c.setFont(FONT, 7)
        self.c.drawCentredString(WIDTH / 2, self.y - size - 4, "ARCA")
        self.y -= size + 6 * mm

    def _build_arca_qr_url(self, data: dict) -> str:
        tipo_doc_map = {96: "DNI", 80: "CUIL", 86: "CUIT", 99: "Consumidor Final"}
        tipo_doc = data.get("tipo_doc_comprador", 99)
        doc_receptor = data.get("nro_doc_comprador", "0")
        if tipo_doc == 99 or not doc_receptor or doc_receptor == "0":
            tipo_doc = 99
            doc_receptor = "0"

        fecha_str = data.get("fecha", "")
        if isinstance(data.get("fecha"), datetime):
            fecha_str = data["fecha"].strftime("%Y-%m-%d")
        elif fecha_str and "T" in fecha_str:
            fecha_str = fecha_str[:10]

        payload = {
            "ver": 1,
            "fecha": fecha_str or datetime.now().strftime("%Y-%m-%d"),
            "cuit": int(data.get("cuit_emisor", 0)),
            "ptoVta": int(data.get("punto_venta", 1)),
            "tipoCmp": int(data.get("tipo", 11)),
            "nroCmp": int(data.get("numero_fiscal", 0)),
            "importe": float(data.get("total", 0)),
            "moneda": "PES",
            "ctz": 1.0,
            "tipoDocRec": tipo_doc,
            "nroDocRec": str(doc_receptor),
            "tipoAut": "E",
            "codAut": int(data.get("cae", 0)),
        }

        json_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        b64 = base64.b64encode(json_bytes).decode("ascii")
        return f"https://www.afip.gob.ar/fe/qr/?p={b64}"

    def boxed_section(self, height):
        self.c.setStrokeColor(COLOR_LIGHT)
        self.c.roundRect(LEFT, self.y - height, CONTENT_WIDTH, height, 2 * mm, stroke=1, fill=0)
        self.y -= height


def generar_factura_pdf(venta, factura, emisor, items) -> bytes:
    descuento = float(venta.get("descuento", 0))
    neto = float(factura.get("neto", venta.get("total", 0)))
    iva = float(factura.get("iva", 0))
    total = float(factura.get("total", venta.get("total", 0)))

    has_iva = iva > 0
    has_discount = descuento > 0

    altura_mm = 60
    altura_mm += len(items) * 12
    if has_discount:
        altura_mm += 6
    if has_iva:
        altura_mm += 6
    altura_mm += 50

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(WIDTH, altura_mm * mm))
    t = Ticket80(c, altura_mm * mm)

    # LOGO
    t.logo_placeholder()

    # EMPRESA
    t.text(emisor.get("nombre", "EMPRESA"), 10, True, "center")
    t.text(emisor.get("domicilio", ""), 7, False, "center", COLOR_GRAY)
    t.text(f"CUIT {emisor.get('cuit', '')}", 7, False, "center")
    cond_map = {
        "responsable_inscripto": "Responsable Inscripto",
        "monotributista": "Monotributista",
        "exento": "Exento"
    }
    t.text(cond_map.get(emisor.get("condicion_iva"), ""), 7, False, "center", COLOR_GRAY)
    if emisor.get("ingresos_brutos"):
        t.text(f"IIBB {emisor['ingresos_brutos']}", 7, False, "center", COLOR_GRAY)
    if emisor.get("fecha_inicio"):
        t.text(f"Inicio {emisor['fecha_inicio']}", 7, False, "center", COLOR_GRAY)
    t.space(2)
    t.double_hr()

    # FACTURA
    tipo_map = {"1": "A", "6": "B", "11": "C"}
    letra = tipo_map.get(str(factura.get("tipo", "11")), "C")
    t.text(f"FACTURA {letra}", 12, True, "center")
    t.factura_letter(letra)

    pv = str(factura.get("punto_venta", 1)).zfill(5)
    numero = str(factura.get("numero_fiscal", 0)).zfill(8)
    fecha = venta.get("fecha", "")[:10] if venta.get("fecha") else ""

    t.key_value("Punto de Venta", pv)
    t.key_value("Comprobante", f"{pv}-{numero}")
    t.key_value("Fecha", fecha)
    t.space(2)
    t.boxed_section(12 * mm)
    yy = t.y + 8 * mm
    venc = str(factura.get("vencimiento_cae", ""))[:10] if factura.get("vencimiento_cae") else "-"
    c.setFont(FONT, 8)
    c.drawString(LEFT + 2 * mm, yy, f"CAE {factura.get('cae', 'N/A')}  |  Venc: {venc}")
    t.y -= 16 * mm

    t.hr()

    # CLIENTE
    t.section("Cliente")
    cliente = venta.get("cliente_nombre", "Consumidor Final")
    if not cliente:
        cliente = "Consumidor Final"
    cliente = cliente.upper()
    t.c.setFont(FONT_BOLD, 9)
    t.c.drawString(LEFT + 2 * mm, t.y, cliente)
    t.y -= 5 * mm
    doc = factura.get("nro_doc_comprador")
    if doc and doc != "0":
        t.text(f"CUIT {doc}", 8, False, "left", COLOR_GRAY)
    else:
        t.text("Consumidor Final", 8, False, "left", COLOR_GRAY)
    t.y -= 4 * mm

    t.hr()

    # PRODUCTOS
    t.section("Detalle")
    c.setFillColor(COLOR_BG_HEADER)
    c.rect(LEFT, t.y - 5 * mm, CONTENT_WIDTH, 5 * mm, fill=1, stroke=0)
    c.setFillColor(COLOR_TEXT)
    c.setFont(FONT_BOLD, 8)
    c.drawString(LEFT + 2 * mm, t.y + 1, "Descripción")
    c.drawRightString(RIGHT - 2 * mm, t.y + 1, "Importe")
    t.y -= 7 * mm

    for item in items:
        nombre = item.get("producto_nombre") or item.get("nombre", "Producto")
        cantidad = item.get("cantidad", 1)
        precio = float(item.get("precio_unitario", 0))
        subtotal = float(item.get("subtotal", 0))
        t.product(nombre, cantidad, precio, subtotal)

    t.space(2)

    # TOTALES
    t.boxed_section(32 * mm)
    yy = t.y + 26 * mm
    c.setFont(FONT, 8)
    c.drawString(LEFT + 2 * mm, yy, "Subtotal")
    c.drawRightString(RIGHT - 2 * mm, yy, money_arg(neto))
    yy -= 5 * mm
    if has_discount:
        c.drawString(LEFT + 2 * mm, yy, "Descuento")
        c.drawRightString(RIGHT - 2 * mm, yy, "-" + money_arg(descuento))
        yy -= 5 * mm
    if has_iva:
        c.drawString(LEFT + 2 * mm, yy, "IVA")
        c.drawRightString(RIGHT - 2 * mm, yy, money_arg(iva))
        yy -= 5 * mm
    t.total_box(money_arg(total))
    t.y -= 2 * mm

    # QR
    qr_payload = {
        "fecha": venta.get("fecha"),
        "cuit_emisor": emisor.get("cuit", "").replace("-", "").replace(" ", ""),
        "punto_venta": factura.get("punto_venta"),
        "tipo": factura.get("tipo"),
        "numero_fiscal": factura.get("numero_fiscal"),
        "total": factura.get("total"),
        "tipo_doc_comprador": factura.get("tipo_doc_comprador"),
        "nro_doc_comprador": factura.get("nro_doc_comprador"),
        "cae": factura.get("cae"),
    }
    t.qr_code(qr_payload)

    # PIE
    t.double_hr()
    t.text("¡GRACIAS POR SU COMPRA!", 10, True, "center")
    t.text("Comprobante electrónico", 7, False, "center", COLOR_GRAY)
    t.text("Autorizado por ARCA", 7, False, "center", COLOR_GRAY)

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
