"""Parseo de las 4 fuentes online, con fixtures y sin red.

Cada scraper se parte en dos (_lookup_* hace fetch, _parse_* hace parse) para
poder testear el parseo contra HTML guardado. Si una fuente cambia su markup,
estos tests fallan con un nombre claro en vez de devolver [] en silencio.
"""

import pytest

from app.services import lookup_service as ls

from conftest import BARCODE


class TestVea:
    """Vea y MasOnline comparten el scraper VTEX."""

    def test_extrae_nombre_marca_precio_e_imagen(self, leer_fixture):
        p = ls._parse_vea(leer_fixture("vea_producto.html"), BARCODE, "vea")

        assert p is not None
        # _clean_name separa con " - " el prefijo que coincide con la categoria
        assert p["nombre"] == "Café Molido - Premium 1 kg"
        assert p["marca"] == "Nescafé"
        assert p["precio_referencia"] == 18500.0
        assert p["imagen_url"] == "https://www.vea.com.ar/medias/cafe-molido-1kg.jpg"
        assert p["fuente"] == "vea"
        assert p["codigo_barras"] == BARCODE

    def test_ignora_precios_ausentes(self, leer_fixture):
        p = ls._parse_vea(leer_fixture("vea_producto.html"), BARCODE, "vea")
        assert p["precio_referencia"] is not None

    def test_detecta_oferta_con_precio_de_lista(self, leer_fixture):
        p = ls._parse_vea(leer_fixture("vea_producto.html"), BARCODE, "vea")

        assert p["descuento"] is not None
        assert p["descuento"]["activo"] is True
        assert p["descuento"]["precio_original"] == 21900.0
        assert p["descuento"]["precio_oferta"] == 18500.0

    def test_extrae_propiedades_del_state(self, leer_fixture):
        p = ls._parse_vea(leer_fixture("vea_producto.html"), BARCODE, "vea")

        assert p["propiedades"].get("Peso") == "1 kg"
        assert p["propiedades"].get("Origen") == "Argentina}"

    def test_categoria_usa_el_ultimo_segmento(self, leer_fixture):
        # El ultimo segmento de /Almacén/Almacén/Bebidas/Café/Café molido es
        # "Café molido", que NO esta en el mapa de _map_categoria, asi que cae
        # al .capitalize() y devuelve el texto crudo. Documentado a proposito:
        # la tabla de mapeo es ad-hoc y esto queda como categoria propia.
        p = ls._parse_vea(leer_fixture("vea_producto.html"), BARCODE, "vea")
        assert p["categoria"] == "Café molido"

    def test_categoria_conocida_se_mapea(self):
        assert ls._map_categoria(["/Almacén/Almacén/Bebidas/Gaseosas"]) == "Bebidas"
        assert ls._map_categoria(["/Bebidas/Cervezas"]) == "Bebidas"
        assert ls._map_categoria(["/Hogar/Platos"]) == "Platos"
        assert ls._map_categoria([]) == ""

    def test_html_sin_jsonld_devuelve_none(self):
        assert ls._parse_vea("<html><body>nada</body></html>", BARCODE, "vea") is None


class TestBusquedaProducto:
    """_find_product_link: primero __STATE__, despues el HTML."""

    def test_encuentra_link_desde_state(self, leer_fixture):
        link = ls._find_product_link(leer_fixture("masonline_busqueda.html"))
        assert link == "/gaseosa-cola-2l/p"

    def test_fallback_a_href_del_html(self):
        html = '<html><body><a href="/algo/p">x</a></body></html>'
        assert ls._find_product_link(html) == "/algo/p"

    def test_ignora_anclas_y_hrefs_no_producto(self):
        html = '<html><body><a href="#ancla">a</a><a href="/ayuda">b</a></body></html>'
        assert ls._find_product_link(html) is None


class TestCarrefour:
    def test_parsea_payload_de_la_api(self, leer_json):
        p = ls._parse_carrefour(leer_json("carrefour_producto.json"), BARCODE)

        assert p["nombre"] == "Gaseosa - Cola 2,25 L"
        assert p["marca"] == "Coca-Cola"
        assert p["precio_referencia"] == 2400.0
        assert p["imagen_url"] == "https://www.carrefour.com.ar/medias/gaseosa-cola.jpg"
        assert p["sku"] == "99003"
        assert p["url"] == "https://www.carrefour.com.ar/gaseosa-cola-225-l/p"

    def test_detecta_oferta(self, leer_json):
        p = ls._parse_carrefour(leer_json("carrefour_producto.json"), BARCODE)

        assert p["descuento"]["activo"] is True
        assert p["descuento"]["precio_original"] == 3100.0
        assert p["descuento"]["precio_oferta"] == 2400.0
        assert p["descuento"]["promocion"] == "Oferta 20% off"

    def test_mapea_categoria_a_bebidas(self, leer_json):
        p = ls._parse_carrefour(leer_json("carrefour_producto.json"), BARCODE)
        assert p["categoria"] == "Bebidas"

    @pytest.mark.parametrize("payload", [None, [], {}, [{"items": []}]])
    def test_payloads_vacios_devuelven_none(self, payload):
        assert ls._parse_carrefour(payload, BARCODE) is None

    def test_sin_offer_no_hay_descuento(self):
        payload = [{
            "productName": "X",
            "brand": "Y",
            "link": "/x/p",
            "items": [{"itemId": "1", "images": [], "sellers": []}],
        }]
        p = ls._parse_carrefour(payload, BARCODE)
        assert p["descuento"] is None


class TestSuperCoco:
    def test_parsea_resultado_de_busqueda(self, leer_fixture):
        p = ls._parse_supercoco(leer_fixture("supercoco_busqueda.html"), BARCODE)

        assert p["nombre"] == "Alfajor Blanco 125g"
        assert p["marca"] == "Tostadas"
        assert p["precio_referencia"] == 2400.0
        assert p["imagen_url"] == "https://supercoco.com.ar/medias/alfajor-blanco.jpg"
        assert p["sku"] == "7790009999999"

    def test_url_apunta_al_producto_no_a_la_busqueda(self, leer_fixture):
        p = ls._parse_supercoco(leer_fixture("supercoco_busqueda.html"), BARCODE)
        assert p["url"] == "https://supercoco.com.ar/alfajor-blanco-125g"

    def test_detecta_descuento_por_precio_rebajado(self, leer_fixture):
        p = ls._parse_supercoco(leer_fixture("supercoco_busqueda.html"), BARCODE)

        assert p["descuento"]["activo"] is True
        assert p["descuento"]["precio_original"] == 3200.0
        assert p["descuento"]["precio_oferta"] == 2400.0

    def test_html_sin_datos_devuelve_none(self):
        assert ls._parse_supercoco("<html><body>sin datos</body></html>", BARCODE) is None
