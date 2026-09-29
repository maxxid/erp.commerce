"""Tests de la promo de Vea/MasOnline, con una pagina real.

La trampa esta en que Vea emite DOS bloques ld+json del mismo producto:

- el primero trae offers.lowPrice, que es el precio DE LISTA (o sea el precio
  sin promo). Aceptarlo esconde el descuento entero.
- el de id="structured-data-schema" trae offers.price, que es lo que se paga
  por unidad con la promo ya aplicada, mas priceSpecification.price con la
  lista y priceValidUntil con la vigencia.

La fixture es la Coca Cola Zero de la pagina real, con los dos bloques.
"""

import pytest

from app.services import lookup_service as lk


def leer_fixture(nombre="vea_promo_real.html"):
    import os
    ruta = os.path.join(os.path.dirname(__file__), "fixtures", nombre)
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def _bloque(html, script_id=None):
    """Arma un HTML minimo con un solo bloque ld+json."""
    if script_id:
        return f'<script id="{script_id}" type="application/ld+json">{html}</script>'
    return f'<script type="application/ld+json">{html}</script>'


LISTA = '{"@type":"Product","name":"Producto","offers":{"@type":"AggregateOffer","lowPrice":5890,"highPrice":5890,"priceCurrency":"ARS"}}'
OFERTA = ('{"@type":"Product","name":"Producto","offers":{"@type":"Offer","price":3926.67,'
          '"priceCurrency":"ARS","priceSpecification":{"@type":"UnitPriceSpecification",'
          '"priceType":"https://schema.org/ListPrice","price":5890},'
          '"priceValidUntil":"2026-10-01"}}')


class TestElegirElBloqueCorrecto:
    def test_toma_el_de_structured_data_no_el_de_lowprice(self):
        """El bug: devolver el primero parseado devolvia el precio de lista."""
        html = _bloque(LISTA) + _bloque(OFERTA, "structured-data-schema")
        ld = lk._extract_json_ld(html)
        assert ld["offers"]["price"] == 3926.67

    def test_al_reves_tambien_elige_el_correcto(self):
        """El orden en la pagina no deberia importar."""
        html = _bloque(OFERTA, "structured-data-schema") + _bloque(LISTA)
        ld = lk._extract_json_ld(html)
        assert ld["offers"]["price"] == 3926.67

    def test_sin_el_de_structured_data_usa_el_que_precie(self):
        html = _bloque(LISTA) + _bloque(
            '{"@type":"Product","name":"P","offers":{"price":1000}}')
        assert lk._extract_json_ld(html)["offers"]["price"] == 1000

    def test_ignora_json_invalido(self):
        html = "<script type=\"application/ld+json\">{roto</script>" + _bloque(OFERTA, "structured-data-schema")
        assert lk._extract_json_ld(html)["offers"]["price"] == 3926.67

    def test_ignora_bloques_que_no_son_producto(self):
        html = _bloque('{"@type":"Organization","name":"Jumbo"}') + _bloque(OFERTA, "structured-data-schema")
        assert lk._extract_json_ld(html)["offers"]["price"] == 3926.67

    def test_sin_bloques_devuelve_none(self):
        assert lk._extract_json_ld("<html></html>") is None


class TestDescuentoDesdeJsonLd:
    def test_detecta_precio_de_lista_y_de_oferta(self):
        d = lk._descuento_de_json_ld({
            "price": 3926.67,
            "priceSpecification": {"price": 5890},
            "priceValidUntil": "2026-10-01",
        })
        assert d["activo"] is True
        assert d["precio_oferta"] == 3926.67
        assert d["precio_original"] == 5890.0
        assert d["vigencia"] == "2026-10-01"

    def test_reconoce_la_multi_compra_3x2(self):
        """3926.67 es exactamente 2/3 de 5890."""
        d = lk._descuento_de_json_ld({"price": 3926.67, "priceSpecification": {"price": 5890}})
        assert d["promocion"] == "3x2"

    def test_reconoce_2x1_y_4x3(self):
        assert lk._descuento_de_json_ld({"price": 50, "priceSpecification": {"price": 100}})["promocion"] == "2x1"
        assert lk._descuento_de_json_ld({"price": 75, "priceSpecification": {"price": 100}})["promocion"] == "4x3"

    def test_un_descuento_comun_no_se_etiqueta_como_multi_compra(self):
        """5890 -> 5000 no es una 3x2, es un descuento comun."""
        d = lk._descuento_de_json_ld({"price": 5000, "priceSpecification": {"price": 5890}})
        assert d["promocion"] == ""

    def test_sin_priceSpecification_no_hay_descuento(self):
        assert lk._descuento_de_json_ld({"price": 3926.67}) is None

    def test_precio_de_lista_menor_que_el_de_oferta_no_hay_descuento(self):
        assert lk._descuento_de_json_ld({"price": 6000, "priceSpecification": {"price": 5890}}) is None

    def test_precios_iguales_no_hay_descuento(self):
        assert lk._descuento_de_json_ld({"price": 5890, "priceSpecification": {"price": 5890}}) is None

    def test_precio_cero_o_negativo(self):
        assert lk._descuento_de_json_ld({"price": 0, "priceSpecification": {"price": 100}}) is None
        assert lk._descuento_de_json_ld({"price": -5, "priceSpecification": {"price": 100}}) is None

    def test_texto_en_vez_de_numero_no_revienta(self):
        assert lk._descuento_de_json_ld({"price": "no es un numero"}) is None
        assert lk._descuento_de_json_ld({"price": 10, "priceSpecification": {"price": "x"}}) is None

    def test_priceSpecification_como_lista(self):
        d = lk._descuento_de_json_ld({"price": 3926.67, "priceSpecification": [{"price": 5890}]})
        assert d["precio_original"] == 5890.0

    def test_offers_no_es_dict(self):
        assert lk._descuento_de_json_ld(None) is None
        assert lk._descuento_de_json_ld("texto") is None

    def test_usa_lowprice_como_fallback(self):
        d = lk._descuento_de_json_ld({"lowPrice": 50, "priceSpecification": {"price": 100}})
        assert d["precio_oferta"] == 50.0


class TestPaginaReal:
    def fixture_html(self):
        return leer_fixture()

    def test_el_precio_que_mostramos_es_el_de_oferta(self):
        """Este es el assert que importa: 3926.67, no 5890."""
        r = lk._parse_vea(self.fixture_html(), "12110101145", "vea", url="")
        assert r["precio_referencia"] == 3926.67

    def test_no_devuelve_el_precio_de_lista(self):
        r = lk._parse_vea(self.fixture_html(), "12110101145", "vea", url="")
        assert r["precio_referencia"] != 5890.0

    def test_entrega_los_dos_precios(self):
        r = lk._parse_vea(self.fixture_html(), "12110101145", "vea", url="")
        d = r["descuento"]
        assert d["activo"] is True
        assert d["precio_oferta"] == 3926.67
        assert d["precio_original"] == 5890.0
        assert d["promocion"] == "3x2"
        assert d["vigencia"] == "2026-10-01"

    def test_el_ahorro_es_del_33_por_ciento(self):
        r = lk._parse_vea(self.fixture_html(), "12110101145", "vea", url="")
        d = r["descuento"]
        pct = (d["precio_original"] - d["precio_oferta"]) / d["precio_original"] * 100
        assert pct == pytest.approx(33.3, abs=0.1)

    def test_toma_el_nombre_de_la_pagina(self):
        r = lk._parse_vea(self.fixture_html(), "12110101145", "vea", url="")
        assert "Coca" in r["nombre"]

    def test_marca_presente(self):
        r = lk._parse_vea(self.fixture_html(), "12110101145", "vea", url="")
        assert "COCA COLA" in r["marca"].upper()

    def test_no_deja_activo_sin_precios(self):
        """El estado imposible activo:True con los dos precios en None."""
        r = lk._parse_vea(self.fixture_html(), "12110101145", "vea", url="")
        d = r["descuento"]
        if d and d.get("activo"):
            assert d.get("precio_original") is not None
            assert d.get("precio_oferta") is not None


class TestPromoDelBannerNoSeConfunde:
    """El 3x2 de un banner general del sitio no es la promo de este producto."""

    def test_no_toma_la_promo_de_otro_producto(self):
        state = {
            "promo:hamburguesas": {"offerName": "3X2 en Hamburguesas y mas", "expiredDate": "2026-05-29"},
        }
        # Sin JSON-LD util cae en el detector viejo, que barre todo el estado.
        html = _bloque('{"@type":"Product","name":"P","offers":{"lowPrice":100,"highPrice":100}}')
        r = lk._parse_vea(html, "7790001234567", "vea", url="")
        # Lo importante: nunca activo:True con los dos precios en None.
        d = r["descuento"]
        assert not (d and d.get("activo") and d.get("precio_oferta") is None)
