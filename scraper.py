import re
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

FUENTES = ["carrefour", "vea", "masonline"]


def _extract_json_ld(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            return json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _extract_state(html):
    start_marker = "__STATE__"
    idx = html.find(start_marker)
    if idx == -1:
        return None
    idx = html.find("{", idx)
    if idx == -1:
        return None
    depth = 0
    i = idx
    while i < len(html):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[idx:i + 1])
                except json.JSONDecodeError:
                    return None
        i += 1
    return None


def _find_product_link(html):
    state = _extract_state(html)
    if state:
        for key, val in state.items():
            if isinstance(val, dict) and val.get("link") and val["link"].endswith("/p"):
                return val["link"]
    soup = BeautifulSoup(html, "html.parser")
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.endswith("/p") and not href.startswith("#"):
            return href
    return None


def _resolve_value(values):
    if not isinstance(values, dict):
        return str(values) if values else ""
    json_arr = values.get("json", [])
    if isinstance(json_arr, list):
        parsed = []
        for item in json_arr:
            if isinstance(item, str):
                try:
                    parsed.append(json.loads(item))
                except (json.JSONDecodeError, TypeError):
                    parsed.append(item)
            else:
                parsed.append(item)
        return parsed[0] if len(parsed) == 1 else parsed
    return str(json_arr)


def _extract_propiedades(state):
    propiedades = {}
    if not state:
        return propiedades
    for key, val in state.items():
        if not isinstance(val, dict):
            continue

        props = val.get("properties")
        if props and isinstance(props, list):
            for p in props:
                if not isinstance(p, dict):
                    continue
                ref_id = p.get("id")
                if ref_id and ref_id in state:
                    prop = state[ref_id]
                    name = prop.get("name", "")
                    value = _resolve_value(prop.get("values", ""))
                    propiedades[name] = value

        specs = val.get("specificationGroups")
        if specs and isinstance(specs, list):
            for group in specs:
                if not isinstance(group, dict):
                    continue
                ref_id = group.get("id")
                group_data = state.get(ref_id, group) if ref_id else group
                group_name = group_data.get("name", group.get("name", "Especificaciones"))
                group_specs = {}
                for spec in group_data.get("specifications", []):
                    if not isinstance(spec, dict):
                        continue
                    spec_ref_id = spec.get("id")
                    spec_data = state.get(spec_ref_id, spec) if spec_ref_id else spec
                    spec_name = spec_data.get("name", "")
                    spec_value = _resolve_value(spec_data.get("values", []))
                    group_specs[spec_name] = spec_value
                if group_specs:
                    propiedades[group_name] = group_specs
    return propiedades


def _scrape_producto(html, barcode, fuente):
    ld = _extract_json_ld(html)
    state = _extract_state(html)

    propiedades = _extract_propiedades(state)

    if not ld:
        return None

    nombre = ld.get("name", "")
    marca = ld.get("brand", {}).get("name", "") if isinstance(ld.get("brand"), dict) else ld.get("brand", "")
    descripcion = ld.get("description", nombre)
    imagen = ld.get("image", "")
    sku = ld.get("sku", "")

    precio = None
    offers = ld.get("offers", {})
    if isinstance(offers, dict):
        precio = offers.get("lowPrice") or offers.get("price")
        if precio is None and offers.get("offers"):
            first_offer = offers["offers"][0] if offers["offers"] else {}
            precio = first_offer.get("price")

    return {
        "codigo_barras": barcode,
        "nombre": nombre.strip(),
        "marca": marca.strip() if isinstance(marca, str) else str(marca).strip(),
        "descripcion": descripcion.strip(),
        "precio_referencia": float(precio) if precio else None,
        "imagen_url": imagen.strip() if isinstance(imagen, str) else imagen[0] if isinstance(imagen, list) and imagen else "",
        "sku": str(sku).strip(),
        "propiedades": propiedades,
        "fuente": fuente,
    }


def lookup_producto(barcode, fuente=None):
    """Busca un producto por código de barras."""
    fuentes = [fuente] if fuente else FUENTES

    for f in fuentes:
        result = _lookup_fuente(barcode, f)
        if result:
            return result
    return None


def _lookup_fuente(barcode, fuente):
    if fuente == "carrefour":
        return _lookup_carrefour_api(barcode)

    search_url = f"https://www.{fuente}.com.ar/{barcode}?_q={barcode}&map=ft"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=20, allow_redirects=True)
        resp.raise_for_status()
        _fix_encoding(resp)
    except requests.RequestException:
        return None

    final_url = resp.url.rstrip("/")
    if final_url.endswith("/p"):
        return _scrape_producto(resp.text, barcode, fuente)

    product_path = _find_product_link(resp.text)
    if not product_path:
        return None

    product_url = f"https://www.{fuente}.com.ar{product_path}"
    try:
        prod_resp = requests.get(product_url, headers=HEADERS, timeout=20)
        prod_resp.raise_for_status()
        _fix_encoding(prod_resp)
    except requests.RequestException:
        return None

    return _scrape_producto(prod_resp.text, barcode, fuente)


def _lookup_carrefour_api(barcode):
    api_url = f"https://www.carrefour.com.ar/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{barcode}"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        results = resp.json()
    except (requests.RequestException, ValueError):
        return None

    if not results or not isinstance(results, list):
        return None

    p = results[0]
    items = p.get("items", [])
    if not items:
        return None

    item = items[0]
    sellers = item.get("sellers", [])
    price = None
    if sellers:
        offer = sellers[0].get("commertialOffer", {})
        price = offer.get("Price")

    images = item.get("images", [])
    imagen = images[0].get("imageUrl", "") if images else ""

    nombre = p.get("productName", "")
    marca = p.get("brand", "")
    descripcion = p.get("description") or nombre
    sku = str(item.get("itemId", ""))

    return {
        "codigo_barras": barcode,
        "nombre": nombre.strip(),
        "marca": marca.strip() if isinstance(marca, str) else str(marca).strip(),
        "descripcion": descripcion.strip(),
        "precio_referencia": float(price) if price else None,
        "imagen_url": imagen.strip() if isinstance(imagen, str) else "",
        "sku": sku.strip(),
        "propiedades": {},
        "fuente": "carrefour",
    }


def _fix_encoding(resp):
    if resp.encoding and resp.encoding.lower() != 'utf-8':
        resp.encoding = 'utf-8'
