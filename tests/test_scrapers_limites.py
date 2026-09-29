"""Casos limite que rompian el scraping en silencio.

Cada test de este archivo cubre un fallo que devolvia None o un precio
equivocado sin levantar excepcion: la pantalla terminaba diciendo "no lo
encontramos" cuando el producto si estaba.
"""

import json

import pytest

from app.services import lookup_service as ls

from conftest import BARCODE


class TestLlavesDentroDeStrings:
    """El conteo de llaves original no ignoraba strings JSON."""

    def test_state_con_llave_suelta_en_un_string(self, leer_fixture):
        state = ls._extract_state(leer_fixture("vea_producto.html"))
        assert state is not None
        assert state["$Prop:origen"]["values"]["json"] == ['"Argentina}"']

    def test_state_con_llave_abierta_en_un_string(self):
        html = 'window.__STATE__ = {"desc": "envase {1kg}", "price": 100};'
        state = ls._extract_state(html)
        assert state == {"desc": "envase {1kg}", "price": 100}

    def test_state_con_escapes(self):
        html = 'window.__STATE__ = {"desc": "cinta \\"adhesiva\\" {x}", "n": 1};'
        state = ls._extract_state(html)
        assert state["desc"] == 'cinta "adhesiva" {x}'

    def test_state_incompleto_devuelve_none(self):
        assert ls._extract_state('window.__STATE__ = {"a": 1, ') is None

    def test_state_ausente_devuelve_none(self):
        assert ls._extract_state("<html>sin state</html>") is None

    def test_state_con_json_invalido_devuelve_none(self):
        assert ls._extract_state('window.__STATE__ = {"a": 1,,}') is None


class TestScannerSupercoco:
    """El regex no-greedy cortaba en la primera '}...)'."""

    def test_payload_con_parentesis_dentro_de_un_string(self, leer_fixture):
        data = ls._extract_supercoco_data(leer_fixture("supercoco_busqueda.html"))
        assert data is not None
        assert data["name"] == "Alfajor Blanco 125g"
        assert "})" in data["descriptionPlainText"]

    def test_salta_el_fallback_vacio(self):
        # 'window.data.products = window.data.products || {}' antes del assign real
        html = (
            '<script>window.data.products = window.data.products || {};'
            'window.data.products = Object.assign(window.data.products, '
            '{"1": {"name": "Real", "price": 100}});</script>'
        )
        data = ls._extract_supercoco_data(html)
        assert data["name"] == "Real"

    def test_sin_productos_devuelve_none(self):
        html = '<script>window.data.products = Object.assign(window.data.products, {});</script>'
        assert ls._extract_supercoco_data(html) is None

    def test_json_lista_no_es_un_dict(self):
        html = '<script>window.data.products = Object.assign(x, [1, 2]);</script>'
        assert ls._extract_supercoco_data(html) is None


class TestUrlSupercoco:
    """La URL apuntaba a la pagina de busqueda, no al producto."""

    def test_usa_el_slug(self):
        html = '<script>window.data.products = Object.assign(x, {"1": {"name": "A", "slug": "/a-b"}});</script>'
        assert ls._supercoco_product_url({"slug": "/a-b"}) == "https://supercoco.com.ar/a-b"

    def test_respeta_url_absoluta(self):
        assert ls._supercoco_product_url({"slug": "https://otro.com/x"}) == "https://otro.com/x"

    def test_sin_slug_cae_al_fallback(self):
        assert ls._supercoco_product_url({}, "https://supercoco.com.ar/s/?q=1") == "https://supercoco.com.ar/s/?q=1"

    def test_slug_no_string_cae_al_fallback(self):
        assert ls._supercoco_product_url({"slug": 123}, "fb") == "fb"


class TestCategoriasRobustas:
    """_clean_name y _map_categoria reventaban con AttributeError si VTEX
    cambiaba categories de lista de strings a lista de dicts."""

    def test_clean_name_con_dicts_no_revienta(self):
        # antes: AttributeError -> 'dict' object has no attribute 'strip'
        assert ls._clean_name("Gaseosa Cola 2L", [{"name": "Gaseosa"}]) == "Gaseosa - Cola 2L"

    def test_clean_name_ignora_tipos_raros(self):
        # antes: AttributeError en None / int
        assert ls._clean_name("Gaseosa Cola", [None, 42, {"name": "Gaseosa"}]) == "Gaseosa - Cola"

    def test_clean_name_sin_prefijo_devuelve_el_nombre(self):
        assert ls._clean_name("Gaseosa Cola", [{"name": "Bebidas"}]) == "Gaseosa Cola"

    def test_map_categoria_con_dicts(self):
        assert ls._map_categoria([{"name": "/Bebidas/Gaseosas"}]) == "Bebidas"

    def test_map_categoria_ignora_tipos_raros(self):
        assert ls._map_categoria([None, 7, {"name": "/Bebidas/Cervezas"}]) == "Bebidas"


class TestPreciosDefensivos:
    def test_acepta_aggregate_offer_simple(self):
        ld = json.dumps({"@type": "Product", "name": "X", "offers": {"price": "1999.90"}})
        p = ls._scrape_producto(
            f'<script type="application/ld+json">{ld}</script>', BARCODE, "vea"
        )
        assert p["precio_referencia"] == 1999.90

    def test_acepta_lista_de_ofertas(self):
        ld = json.dumps({
            "@type": "Product", "name": "X", "offers": {"offers": [{"price": 500.0}]},
        })
        p = ls._scrape_producto(
            f'<script type="application/ld+json">{ld}</script>', BARCODE, "vea"
        )
        assert p["precio_referencia"] == 500.0

    def test_acepta_imagen_como_lista(self):
        ld = json.dumps({"@type": "Product", "name": "X", "image": ["a.jpg", "b.jpg"]})
        p = ls._scrape_producto(
            f'<script type="application/ld+json">{ld}</script>', BARCODE, "vea"
        )
        assert p["imagen_url"] == "a.jpg"

    def test_acepta_marca_como_string(self):
        ld = json.dumps({"@type": "Product", "name": "X", "brand": "Marca S.A."})
        p = ls._scrape_producto(
            f'<script type="application/ld+json">{ld}</script>', BARCODE, "vea"
        )
        assert p["marca"] == "Marca S.A."

    def test_jsonld_invalido_no_revienta(self):
        assert ls._scrape_producto(
            '<script type="application/ld+json">{roto</script>', BARCODE, "vea"
        ) is None


class TestDescuentos:
    def test_descuento_descartado_si_es_menor_que_la_sextima_parte(self):
        # 100 -> 10000 es ruido de scraping, no una oferta real
        assert ls._supercoco_descuento({"discountedPrice": 100.0, "price": 10000.0}) is None

    def test_descuento_aceptado_si_es_coherente(self):
        d = ls._supercoco_descuento({"discountedPrice": 2400.0, "price": 3200.0})
        assert d["activo"] is True
        assert d["precio_original"] == 3200.0

    def test_precios_no_numericos_no_revientan(self):
        assert ls._supercoco_descuento({"discountedPrice": "N/A", "price": "N/A"}) is None

    def test_carrefour_sin_teasers_no_falla(self, leer_json):
        payload = leer_json("carrefour_producto.json")
        payload[0]["items"][0]["sellers"][0]["commertialOffer"].pop("Teasers")
        p = ls._parse_carrefour(payload, BARCODE)
        assert p["precio_referencia"] == 2400.0
        assert p["descuento"]["activo"] is True
        assert p["descuento"]["promocion"] == ""

    def test_promocion_sin_precios_no_crea_descuento_fantasma(self):
        payload = [{
            "productName": "X", "brand": "Y", "link": "/x/p", "categories": [],
            "items": [{
                "itemId": "1", "images": [],
                "sellers": [{
                    "commertialOffer": {
                        "Teasers": [{"Name": "2x1"}],
                    }
                }],
            }],
        }]
        p = ls._parse_carrefour(payload, BARCODE)
        assert p["descuento"]["activo"] is True
        assert p["descuento"]["precio_oferta"] is None
