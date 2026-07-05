"""Generación de PDF para facturas electrónicas en formato 80mm."""

from io import BytesIO
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm as units
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, white, HexColor
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors


WIDTH_MM = 80
WIDTH_PT = WIDTH_MM * units


def generar_factura_pdf(
    venta: dict,
    factura: dict,
    emisor: dict,
    items: list
) -> bytes:
    """Genera un PDF de factura electrónica en formato 80mm térmico."""

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=(WIDTH_PT, 200 * units))
    c.setFont("Courier", 8)

    y = 280
    left_margin = 3 * units

    def print_line(text, x=0, size=8, bold=False):
        return

    c.setFont("Courier-Bold" if bold else "Courier", 7)
    lines = []

    lines.append(("center", "=" * 40))
    lines.append(("center", emisor.get("nombre", "").upper() or "EMPRESA"))
    lines.append(("center", emisor.get("domicilio", "") or ""))
    lines.append(("center", f"CUIT: {emisor.get('cuit', '')}"))
    cond_iva = emisor.get("condicion_iva", "responsable_inscripto")
    cond_map = {
        "responsable_inscripto": "Responsable Inscripto",
        "monotributista": "Monotributista",
        "exento": "Exento"
    }
    lines.append(("center", cond_map.get(cond_iva, cond_iva)))
    lines.append(("center", f"Ing. Brutos: {emisor.get('ingresos_brutos', 'Exento')}"))
    lines.append(("center", f"Fecha Inicio: {emisor.get('fecha_inicio', '')}"))
    lines.append(("center", "=" * 40))

    tipo_map = {"11": "C", "1": "A", "6": "B"}
    tipo_factura = tipo_map.get(str(factura.get("tipo", "11")), "C")
    lines.append(("center", f"[ {tipo_factura} ]"))
    lines.append(("center", f"Punto de Venta: {str(factura.get('punto_venta', '00001')).zfill(5)}"))
    num_fiscal = str(factura.get("numero_fiscal", "00000000")).zfill(8)
    lines.append(("center", f"Comp. Nro: {factura.get('punto_venta', '00001').zfill(5)} - {num_fiscal}"))
    lines.append(("center", f"Fecha: {venta.get('fecha', '')[:10] if venta.get('fecha') else ''}"))
    lines.append(("center", "-" * 40))
    lines.append(("left", "RECEPTOR:"))
    cliente = venta.get("cliente_nombre", "Consumidor Final")
    if cliente == "Consumidor Final" or not cliente:
        lines.append(("left", "A CONSUMIDOR FINAL"))
    else:
        lines.append(("left", cliente.upper()))
    nro_doc = factura.get("nro_doc_comprador", "0")
    if nro_doc and nro_doc != "0":
        lines.append(("left", f"CUIT: {nro_doc}"))
    lines.append(("left", "-" * 40))

    lines.append(("left", f"{'Producto':<20} {'Cant':>4} {'Precio':>10}"))
    lines.append(("left", "-" * 40))

    for item in items:
        nombre = (item.get("producto_nombre") or item.get("nombre") or "Producto")[:20]
        cantidad = item.get("cantidad", 0)
        precio = item.get("precio_unitario", 0)
        subtotal = item.get("subtotal", 0)
        linea = f"{nombre:<20} {cantidad:>4} ${precio:>8.2f}"
        lines.append(("left", linea))

    lines.append(("left", "-" * 40))

    total = factura.get("total", venta.get("total", 0))
    neto = factura.get("neto", venta.get("total", 0))
    iva = factura.get("iva", 0)
    descuento = venta.get("descuento", 0)

    if descuento > 0:
        lines.append(("left", f"Descuento: -${descuento:.2f}"))
    lines.append(("left", f"Neto: ${neto:.2f}"))
    if iva > 0:
        lines.append(("left", f"IVA: ${iva:.2f}"))
    lines.append(("left", f"TOTAL: ${total:.2f}"))

    lines.append(("center", "-" * 40))
    lines.append(("center", f"CAI: {factura.get('cae', 'N/A')}"))
    if factura.get("vencimiento_cae"):
        lines.append(("center", f"Vencimiento: {str(factura.get('vencimiento_cae'))[:10]}"))
    lines.append(("center", "¡Gracias por su compra!"))

    y_pos = 280 * units
    for align, text in lines:
        if align == "center":
            c.drawCentredString(WIDTH_PT / 2, y_pos, text)
        else:
            c.drawString(left_margin, y_pos, text)
        y_pos -= 10

    c.save()
    buffer.seek(0)
    return buffer.getvalue()
