"""Parseo de tickets/facturas de proveedor con IA.

El operador pega el texto de un ticket (cantidad, detalle, precio unitario,
importe) y la IA devuelve la lista de artículos estructurada, más las líneas
que no pudo interpretar (para que el operador las cargue a mano).
"""

import logging
from typing import Any, Dict, List

from app.services.ia.openai_compat import extraer_json

logger = logging.getLogger(__name__)

SISTEMA_IA = """Sos un asistente que extrae artículos de un ticket o factura de proveedor.
El texto puede venir con columnas: Cantidad, Detalle, Precio unitario, Importe.
Las cantidades usan coma como separador decimal (ej. "2,000" = 2 unidades).
Los precios están en ARS y usan coma como separador de miles y punto como
separador decimal (ej. "1.690,00" = 1690.0).

Devolvé SOLO un objeto JSON con esta forma exacta, sin texto adicional ni
bloques de código:
{
  "items": [
    {
      "cantidad": <número>,
      "codigo_barras": <string o null>,
      "nombre": <string, descripción del artículo>,
      "precio_unitario": <número>,
      "importe": <número>
    }
  ],
  "no_reconocidos": [<string con el texto original de cada línea que no se pudo interpretar como artículo>]
}

Reglas:
- Ignorá la línea de encabezado (Cantidad / Detalle / Precio / Importe).
- Ignorá líneas de TOTAL, SUBTOTAL, DESCUENTO, IVA, o cualquier línea que sea un
  resumen/totales, no un artículo.
- Si el detalle empieza con un código de barras (número de 8 a 14 dígitos), ponelo
  en codigo_barras y el resto del detalle en nombre.
- Si no hay código de barras, codigo_barras = null y todo el detalle va en nombre.
- cantidad, precio_unitario e importe son números (no strings). Convertí las comas
  y puntos según las reglas de ARS.
- Si una línea está cortada o es ambigua y no se puede interpretar como un
  artículo, agregá su texto original a no_reconocidos. No la inventes.
- No inventes artículos que no estén en el texto.

Respondé ÚNICAMENTE con el objeto JSON, sin explicaciones, sin markdown, sin
bloques de código.
"""


def prompt_ia(texto: str) -> str:
    return (
        f"Texto del ticket del proveedor:\n{texto}\n\n"
        "Extraé los artículos y devolvé SOLO el objeto JSON pedido, sin texto adicional."
    )


def interpretar_ia(crudo: str) -> dict:
    """Interpreta la respuesta cruda del LLM y devuelve {items, no_reconocidos}."""
    data = extraer_json(crudo)
    if not isinstance(data, dict):
        raise ValueError("la respuesta no es un objeto JSON")

    items_raw = data.get("items")
    if not isinstance(items_raw, list):
        raise ValueError("falta la lista 'items'")

    items: List[Dict[str, Any]] = []
    for it in items_raw:
        if not isinstance(it, dict):
            continue
        nombre = (it.get("nombre") or "").strip()
        try:
            cantidad = float(it.get("cantidad"))
        except (TypeError, ValueError):
            continue
        if not nombre or cantidad <= 0:
            continue
        try:
            precio = float(it.get("precio_unitario")) if it.get("precio_unitario") is not None else 0.0
        except (TypeError, ValueError):
            precio = 0.0
        try:
            importe = float(it.get("importe")) if it.get("importe") is not None else 0.0
        except (TypeError, ValueError):
            importe = 0.0
        codigo = it.get("codigo_barras")
        if codigo is not None:
            codigo = str(codigo).strip() or None
        items.append({
            "cantidad": cantidad,
            "codigo_barras": codigo,
            "nombre": nombre,
            "precio_unitario": precio,
            "importe": importe,
        })

    no_reconocidos_raw = data.get("no_reconocidos") or []
    no_reconocidos = [str(x).strip() for x in no_reconocidos_raw if str(x).strip()]

    return {"items": items, "no_reconocidos": no_reconocidos}