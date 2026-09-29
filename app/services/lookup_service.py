import json
import time
import threading
import requests
from bs4 import BeautifulSoup
from app.config import settings

HEADERS = {
    "User-Agent": settings.SCRAPER_USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
}

FUENTES = ["carrefour", "vea", "masonline", "supercoco"]

TIMEOUT = settings.SCRAPER_TIMEOUT
CACHE_TTL = settings.SCRAPER_CACHE_TTL
CACHE_TTL_NEGATIVO = 120

_cache = {}
_cache_lock = threading.Lock()

_scrape_slots = threading.Semaphore(settings.SCRAPER_MAX_CONCURRENT)

_locks_por_clave = {}
_locks_guard = threading.Lock()


class _KeyLock:
    """Lock por (fuente, barcode) para no scrapear el mismo codigo N veces."""

    __slots__ = ("lock", "refs")

    def __init__(self):
        self.lock = threading.Lock()
        self.refs = 0


def _adquirir_lock(clave):
    with _locks_guard:
        kl = _locks_por_clave.get(clave)
        if kl is None:
            kl = _locks_por_clave[clave] = _KeyLock()
        kl.refs += 1
    kl.lock.acquire()
    return kl


def _liberar_lock(clave, kl):
    kl.lock.release()
    with _locks_guard:
        kl.refs -= 1
        if kl.refs == 0:
            _locks_por_clave.pop(clave, None)


def _cache_get(clave):
    with _cache_lock:
        entrada = _cache.get(clave)
        if entrada is None:
            return None, False
        valor, expira = entrada
        if expira < time.time():
            _cache.pop(clave, None)
            return None, False
        return valor, True


def _cache_set(clave, valor):
    ttl = CACHE_TTL if valor else CACHE_TTL_NEGATIVO
    with _cache_lock:
        if len(_cache) > 500:
            ahora = time.time()
            for k in [k for k, (_, exp) in _cache.items() if exp < ahora]:
                _cache.pop(k, None)
        _cache[clave] = (valor, time.time() + ttl)


def _extract_json_ld(html):
    soup = BeautifulSoup(html, "html.parser")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            return json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


def _parse_balanced_object(html, start):
    """Parsea el objeto JSON que empieza en `start` (un '{'), respetando strings."""
    if start == -1:
        return None
    depth = 0
    in_string = False
    escaped = False
    i = start
    while i < len(html):
        c = html[i]
        if in_string:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_string = False
        elif c == '"':
            in_string = True
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start:i + 1])
                except json.JSONDecodeError:
                    return None
        i += 1
    return None


def _scan_json_object(html, start_marker, skip_empty=False):
    """Extrae el objeto JSON balanceado que sigue a un marcador.

    Cuenta llaves ignorando las que estan dentro de strings JSON. Sin eso, una
    descripcion del tipo 'envase de 1 kg {sellado}' desbalancea el conteo y el
    scrape entero devuelve None en silencio.

    skip_empty sigue buscando si la primera aparicion del marcador no tiene un
    objeto real detras, que es el caso de 'window.data.products = window.data
    .products || {}' seguido del Object.assign de verdad.
    """
    from_idx = 0
    while True:
        idx = html.find(start_marker, from_idx)
        if idx == -1:
            return None
        parsed = _parse_balanced_object(html, html.find("{", idx))
        if parsed is not None and (parsed or not skip_empty):
            return parsed
        from_idx = idx + len(start_marker)


def _extract_state(html):
    return _scan_json_object(html, "__STATE__")


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


def _scrape_producto(html, barcode, fuente, url=""):
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
        low = offers.get("lowPrice")
        high = offers.get("highPrice")
        if low is not None and high is not None and low != high:
            precio = float(low)
        else:
            precio = low or offers.get("price")
            if precio is None and offers.get("offers"):
                first_offer = offers["offers"][0] if offers["offers"] else {}
                precio = first_offer.get("price")

    descuento = _detectar_descuento(state)

    categorias_raw = _extract_categorias(state)

    return {
        "codigo_barras": barcode,
        "nombre": _clean_name(nombre, categorias_raw),
        "marca": marca.strip() if isinstance(marca, str) else str(marca).strip(),
        "descripcion": descripcion.strip(),
        "precio_referencia": float(precio) if precio else None,
        "imagen_url": imagen.strip() if isinstance(imagen, str) else imagen[0] if isinstance(imagen, list) and imagen else "",
        "sku": str(sku).strip(),
        "propiedades": propiedades,
        "fuente": fuente,
        "url": url,
        "descuento": descuento,
        "categoria": _map_categoria(categorias_raw),
    }


def _extract_categorias(state):
    if not state:
        return []
    for key, val in state.items():
        if isinstance(val, dict) and "categories" in val:
            cats = val["categories"]
            if isinstance(cats, list):
                return cats
            if isinstance(cats, dict) and "json" in cats:
                if isinstance(cats["json"], list):
                    return cats["json"]
            continue
        if isinstance(val, dict) and "categoryId" in val:
            cats = val.get("categories", [])
            if isinstance(cats, list):
                return cats
    return []


def _map_categoria(categorias):
    if not categorias:
        return ""
    general = ""
    for cat in categorias:
        if isinstance(cat, dict):
            cat = cat.get("name", "")
        if not isinstance(cat, str):
            continue
        parts = [p for p in cat.strip("/").split("/") if p]
        if not general or len(parts) < len(general.split("/")):
            general = "/".join(parts)
    if not general:
        return ""
    last = general.split("/")[-1].strip().lower()
    mapping = {
        "bebidas": "Bebidas", "gaseosas": "Bebidas", "aguas": "Bebidas",
        "cervezas": "Bebidas", "vinos": "Bebidas", "licores": "Bebidas",
        "jugos": "Bebidas", "aperitivos": "Bebidas", "isotonicos": "Bebidas",
        "almacen": "Almacén", "almacén": "Almacén", "panaderia": "Almacén",
        "panadería": "Almacén", "golosinas": "Golosinas", "galletitas": "Almacén",
        "snacks": "Almacén", "conservas": "Almacén", "enlatados": "Almacén",
        "arroz": "Almacén", "pastas": "Almacén", "harinas": "Almacén",
        "aceites": "Almacén", "aderezos": "Almacén", "especias": "Almacén",
        "infusiones": "Almacén", "cafe": "Almacén", "café": "Almacén",
        "yerba": "Almacén", "azucar": "Almacén", "azúcar": "Almacén",
        "lacteos": "Frescos", "lácteos": "Frescos", "quesos": "Frescos",
        "fiambres": "Frescos", "yogures": "Frescos", "huevos": "Frescos",
        "frescos": "Frescos", "congelados": "Frescos", "carnes": "Frescos",
        "limpieza": "Limpieza", "perfumeria": "Perfumería", "perfumería": "Perfumería",
        "cuidado personal": "Perfumería", "belleza": "Perfumería",
        "mascotas": "Almacén", "electro": "Otros", "hogar": "Otros",
        "libreria": "Otros", "librería": "Otros", "jardineria": "Otros",
        "jardinería": "Otros", "bazar": "Otros", "automotor": "Otros",
    }
    return mapping.get(last, last.capitalize())


def _clean_name(nombre, categorias):
    if not categorias or not nombre:
        return nombre
    parts = set()
    for cat in categorias:
        if isinstance(cat, dict):
            cat = cat.get("name", "")
        if not isinstance(cat, str):
            continue
        cat_clean = cat.strip("/")
        if cat_clean:
            parts.add(cat_clean)
        for part in cat.strip("/").split("/"):
            if part:
                parts.add(part)
    nombre_lower = nombre.lower()
    best_match = ""
    best_len = 0
    for part in parts:
        variants = {part.lower()}
        words = part.lower().split(" ")
        singular = " ".join(w[:-1] if w.endswith("s") else w for w in words)
        if singular != part.lower():
            variants.add(singular)
        for variant in variants:
            if nombre_lower.startswith(variant + " ") and len(variant) > best_len:
                best_match = variant
                best_len = len(variant)
    if best_match:
        return nombre[:best_len] + " -" + nombre[best_len:]
    return nombre


def _detectar_descuento(state):
    if not state:
        return None

    promocion = _find_promotion_code(state)

    for key in state.keys():
        if not key.startswith("$Product:") or not key.endswith(".priceRange"):
            continue
        pr = state.get(key, {})
        if not isinstance(pr, dict):
            continue
        selling_id = pr.get("sellingPrice", {}).get("id", "") if isinstance(pr.get("sellingPrice"), dict) else ""
        list_id = pr.get("listPrice", {}).get("id", "") if isinstance(pr.get("listPrice"), dict) else ""
        selling = state.get(selling_id, {}) if selling_id else {}
        list_p = state.get(list_id, {}) if list_id else {}
        if not isinstance(selling, dict) or not isinstance(list_p, dict):
            continue
        sp = selling.get("highPrice") or selling.get("value")
        lp = list_p.get("highPrice") or list_p.get("value")
        if sp is None or lp is None:
            continue
        try:
            sp, lp = float(sp), float(lp)
        except (ValueError, TypeError):
            continue
        if sp <= 0 or lp <= 0 or sp >= lp or lp > sp * 6:
            continue
        return {"activo": True, "precio_original": lp, "precio_oferta": sp, "promocion": promocion}

    for key in state.keys():
        if "commertialOffer" not in key or "Installments" in key:
            continue
        offer = state.get(key, {})
        if not isinstance(offer, dict):
            continue
        price = offer.get("Price")
        list_price = offer.get("ListPrice")
        teasers = offer.get("teasers", [])
        if teasers:
            t = teasers[0]
            if isinstance(t, dict):
                promocion = promocion or t.get("name", "") or t.get("<Name>k__BackingField", "")
        if price is not None and list_price is not None:
            try:
                sp, lp = float(price), float(list_price)
            except (ValueError, TypeError):
                continue
            if sp > 0 and lp > 0 and sp < lp and lp <= sp * 6:
                return {"activo": True, "precio_original": lp, "precio_oferta": sp, "promocion": promocion}

    if promocion:
        return {"activo": True, "precio_original": None, "precio_oferta": None, "promocion": promocion}
    return None


def _find_promotion_code(state):
    for key in state.keys():
        if "enrichPromotions" not in key:
            continue
        if ".promotions." not in key and not key.endswith(".promotions.0"):
            continue
        promo = state.get(key, {})
        if isinstance(promo, dict):
            code = promo.get("code") or promo.get("name") or promo.get("promotionName", "")
            if code:
                return code
    return ""


def lookup_producto(barcode, fuente=None):
    """Busca un producto por código de barras."""
    fuentes = [fuente] if fuente else FUENTES

    for f in fuentes:
        result = _lookup_fuente(barcode, f)
        if result:
            return result
    return None


def comparar_precios(barcode):
    """Obtiene el precio de cada fuente disponible, ordenado de menor a mayor."""
    precios = []
    for f in FUENTES:
        result = _lookup_fuente(barcode, f)
        if result and result.get("precio_referencia"):
            precios.append({
                "fuente": f,
                "precio": result["precio_referencia"],
                "nombre": result["nombre"],
                "marca": result.get("marca") or "",
                "imagen_url": result.get("imagen_url") or "",
                "url": result.get("url", ""),
                "descuento": result.get("descuento"),
            })
    precios.sort(key=lambda p: p["precio"])
    return precios


def _lookup_fuente(barcode, fuente):
    clave = f"{fuente}:{barcode}"
    valor, hit = _cache_get(clave)
    if hit:
        return valor

    kl = _adquirir_lock(clave)
    try:
        valor, hit = _cache_get(clave)
        if hit:
            return valor
        with _scrape_slots:
            resultado = _scrape_fuente(barcode, fuente)
        _cache_set(clave, resultado)
        return resultado
    finally:
        _liberar_lock(clave, kl)


def _scrape_fuente(barcode, fuente):
    if fuente == "carrefour":
        return _lookup_carrefour_api(barcode)
    if fuente == "supercoco":
        return _lookup_supercoco(barcode)

    search_url = f"https://www.{fuente}.com.ar/{barcode}?_q={barcode}&map=ft"
    try:
        resp = requests.get(search_url, headers=HEADERS, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
        _fix_encoding(resp)
    except requests.RequestException:
        return None

    final_url = resp.url.rstrip("/")
    if final_url.endswith("/p"):
        return _parse_vea(resp.text, barcode, fuente, url=final_url)

    product_path = _find_product_link(resp.text)
    if not product_path:
        return None

    product_url = f"https://www.{fuente}.com.ar{product_path}"
    try:
        prod_resp = requests.get(product_url, headers=HEADERS, timeout=TIMEOUT)
        prod_resp.raise_for_status()
        _fix_encoding(prod_resp)
    except requests.RequestException:
        return None

    return _parse_vea(prod_resp.text, barcode, fuente, url=product_url)


def _parse_vea(html, barcode, fuente, url=""):
    """Parsea la pagina de producto de Vea / Mas Online (VTEX). Sin red."""
    return _scrape_producto(html, barcode, fuente, url=url)


def _lookup_carrefour_api(barcode):
    api_url = f"https://www.carrefour.com.ar/api/catalog_system/pub/products/search?fq=alternateIds_Ean:{barcode}"
    try:
        resp = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        results = resp.json()
    except (requests.RequestException, ValueError):
        return None

    return _parse_carrefour(results, barcode)


def _parse_carrefour(results, barcode):
    """Parsea la respuesta de la API VTEX de Carrefour. Sin red: es testeable."""
    if not results or not isinstance(results, list):
        return None

    p = results[0]
    items = p.get("items", [])
    if not items:
        return None

    item = items[0]
    sellers = item.get("sellers", [])
    price = None
    list_price = None
    promocion = ""
    if sellers:
        offer = sellers[0].get("commertialOffer", {})
        price = offer.get("Price")
        list_price = offer.get("ListPrice")
        teasers = offer.get("Teasers", []) or offer.get("PromotionTeasers", [])
        if teasers:
            t = teasers[0]
            if isinstance(t, dict):
                promocion = t.get("Name", "") or t.get("<Name>k__BackingField", "")

    images = item.get("images", [])
    imagen = images[0].get("imageUrl", "") if images else ""

    nombre = p.get("productName", "")
    marca = p.get("brand", "")
    descripcion = p.get("description") or nombre
    sku = str(item.get("itemId", ""))

    product_url = p.get("link", "")
    if product_url and not product_url.startswith("http"):
        product_url = "https://www.carrefour.com.ar" + product_url

    descuento = None
    if price is not None and list_price is not None and float(price) < float(list_price):
        descuento = {
            "activo": True,
            "precio_original": float(list_price),
            "precio_oferta": float(price),
            "promocion": promocion,
        }
    elif promocion:
        descuento = {"activo": True, "precio_original": None, "precio_oferta": None, "promocion": promocion}

    categorias = p.get("categories", [])

    return {
        "codigo_barras": barcode,
        "nombre": _clean_name(nombre, categorias),
        "marca": marca.strip() if isinstance(marca, str) else str(marca).strip(),
        "descripcion": descripcion.strip(),
        "precio_referencia": float(price) if price else None,
        "imagen_url": imagen.strip() if isinstance(imagen, str) else "",
        "sku": sku.strip(),
        "propiedades": {},
        "fuente": "carrefour",
        "url": product_url,
        "descuento": descuento,
        "categoria": _map_categoria(categorias),
    }


def _lookup_supercoco(barcode):
    """Busca en Super Coco (https://supercoco.com.ar) usando su búsqueda."""
    search_url = f"https://supercoco.com.ar/s/?q={barcode}"
    sc_headers = {"User-Agent": settings.SCRAPER_USER_AGENT}
    try:
        resp = requests.get(search_url, headers=sc_headers, timeout=TIMEOUT, allow_redirects=True)
        resp.raise_for_status()
    except requests.RequestException:
        return None

    return _parse_supercoco(resp.text, barcode, search_url)


def _parse_supercoco(html, barcode, search_url=""):
    """Parsea el HTML de resultados de Super Coco. Sin red: es testeable."""
    data = _extract_supercoco_data(html)
    if not data:
        return None

    nombre = data.get("name", "")
    marca = data.get("brand", {}).get("name", "") if isinstance(data.get("brand"), dict) else ""
    sku = data.get("sku", "")
    precio = data.get("sellingPrice") or data.get("price")
    images = data.get("urls", {}).get("images", []) if isinstance(data.get("urls"), dict) else []
    imagen = images[0] if images else ""
    if imagen and not imagen.startswith("http"):
        imagen = "https://supercoco.com.ar" + imagen

    categorias = []
    cat_path = data.get("categoryPath", []) or data.get("categoriesPath", [[]])
    if cat_path:
        cats = cat_path[0] if isinstance(cat_path[0], list) else cat_path
        categorias = ["/".join(c.get("name", "") for c in cats)]

    return {
        "codigo_barras": barcode,
        "nombre": _clean_name(nombre, categorias),
        "marca": marca.strip() if isinstance(marca, str) else "",
        "descripcion": data.get("descriptionPlainText", nombre).strip(),
        "precio_referencia": float(precio) if precio else None,
        "imagen_url": imagen.strip() if isinstance(imagen, str) else "",
        "sku": sku.strip(),
        "propiedades": {},
        "fuente": "supercoco",
        "url": _supercoco_product_url(data, search_url),
        "descuento": _supercoco_descuento(data),
        "categoria": _map_categoria_supercoco(data.get("categoryPath", [])),
    }


def _supercoco_product_url(data, fallback=""):
    """URL del producto, no de la pagina de busqueda."""
    slug = data.get("slug") or data.get("url") or data.get("friendlyURL") or ""
    if not isinstance(slug, str) or not slug:
        return fallback
    if slug.startswith("http"):
        return slug
    return "https://supercoco.com.ar/" + slug.lstrip("/")


def _extract_supercoco_data(html):
    """Extrae el primer producto de window.data.products del HTML de Super Coco.

    Usa conteo de llaves balanceado en vez de un regex no-greedy: el patron
    anterior cortaba en la primera '}...)' y fallaba si un string del payload
    contenia esa secuencia.
    """
    products = _scan_json_object(html, "window.data.products", skip_empty=True)
    if not products or not isinstance(products, dict):
        return None
    return next(iter(products.values()), None)


def _supercoco_descuento(data):
    """Detecta descuento en datos de Super Coco."""
    discounted = data.get("discountedPrice")
    price = data.get("price") or data.get("sellingPrice")
    if discounted is not None and price is not None:
        try:
            dp, p = float(discounted), float(price)
            if dp < p and dp > 0 and p <= dp * 6:
                return {"activo": True, "precio_original": p, "precio_oferta": dp, "promocion": ""}
        except (ValueError, TypeError):
            pass
    return None


def _map_categoria_supercoco(category_path):
    """Mapea categorías de Super Coco a las del sistema."""
    if not category_path:
        return ""
    names = [c.get("name", "") for c in category_path if isinstance(c, dict)]
    general = "/".join(names)
    return _map_categoria([general])


def _fix_encoding(resp):
    if resp.encoding and resp.encoding.lower() != 'utf-8':
        resp.encoding = 'utf-8'
