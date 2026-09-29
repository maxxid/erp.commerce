"""Tests de las promos por cantidad de MasOnline.

Estas promos no estan en el HTML ni en el estado de VTEX: el precio de la
pagina se arma por JS y el offer llega con teasers:[] y
discountHighlights:[] vacios, con price == priceWithoutDiscount. El unico lugar
donde aparecen es la simulacion de carrito, que devuelve el precio por unidad
con la promo ya aplicada segun la cantidad.

La fixture es la pagina real de la Coca Cola Zero 2,25 L con los bloques
ld+json y el estado. El precio de lista sale del priceToken (item 195).

Lo que no se debe perder de vista: el precio efectivo de un 3x2 no es el de una
unidad, es el que se paga comprando 3. Por eso va cantidad_minima.
"""

import json
import os

import pytest

from app.services import lookup_service as lk

BASE = 5899.0
OFERTA = 3932.86  # lo que devuelve la simulacion en cantidad 3


def fixture_html():
    ruta = os.path.join(os.path.dirname(__file__), "fixtures", "masonline_promo_real.html")
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def estado_de_fixture():
    h = fixture_html()
    crudo = h.split("window.__STATE__=", 1)[1].rsplit(";</script>", 1)[0]
    return json.loads(crudo)


def html_con_cluster(nombre, token_valido=True):
    """Arma un estado minimo con un cluster y un priceToken."""
    import base64
    payload = base64.urlsafe_b64encode(json.dumps({
        "data": {"id": "195", "seller": "1", "priceWithoutDiscount": 589900}
    }).encode()).decode().rstrip("=")
    token = f"header.{payload}.firma" if token_valido else "basura"
    st = {
        "Product:algo.productClusters.0": {"id": "1", "name": nombre,
                                            "__typename": "ProductClusters"},
        "$Product:algo.items.0.sellers.0.commertialOffer": {
            "Price": 5899, "priceToken": token},
    }
    return json.dumps(st)


class TestFiltroDeClusters:
    def test_el_producto_real_pasa_el_filtro(self):
        assert lk._tiene_cluster_multicompra(estado_de_fixture()) is True

    def test_3x2_y_2x1_pasan(self):
        assert lk._tiene_cluster_multicompra({"a.productClusters.0": {"name": "3x2- Bebidas"}}) is True
        assert lk._tiene_cluster_multicompra({"a.productClusters.0": {"name": "Hasta 2x1 Bebidas - OP"}}) is True

    def test_acepta_espacios_y_asterisco(self):
        for nombre in ("3 x 2 Bebidas", "3X2", "2*1", "4x3"):
            assert lk._tiene_cluster_multicompra({"a.productClusters.0": {"name": nombre}}) is True

    def test_nombres_genericos_no_pasan(self):
        """Estos son los que llenan casi todos los productos, no filtran nada."""
        for nombre in ("Bebidas y snacks- OP", "Derrumbe- Bebidas y Snacks",
                       "Ofertazos - Bebidas", "Coca Cola", "Los mas vendidos"):
            assert lk._tiene_cluster_multicompra({"a.productClusters.0": {"name": nombre}}) is False

    def test_no_lee_1x1_como_multi_compra(self):
        assert lk._tiene_cluster_multicompra({"a.productClusters.0": {"name": "1x1"}}) is False

    def test_estado_vacio_o_basura(self):
        assert lk._tiene_cluster_multicompra(None) is False
        assert lk._tiene_cluster_multicompra({}) is False
        assert lk._tiene_cluster_multicompra({"a.productClusters.0": "no soy dict"}) is False
        assert lk._tiene_cluster_multicompra({"a.productClusters.0": {"name": 123}}) is False


class TestTokenDePrecio:
    def test_saca_id_seller_y_lista_del_token_real(self):
        t = lk._token_de_precio(estado_de_fixture())
        assert t == {"id": "195", "seller": "1", "precio_lista": 5899.0}

    def test_convierte_centavos_a_pesos(self):
        t = lk._token_de_precio({"x": {"priceToken": token_de(10000)}})
        assert t["precio_lista"] == 100.0

    def test_token_que_no_es_jwt(self):
        assert lk._token_de_precio({"x": {"priceToken": "basura"}}) is None
        assert lk._token_de_precio({"x": {"priceToken": "solo.una"}}) is None

    def test_payload_base64_invalido(self):
        assert lk._token_de_precio({"x": {"priceToken": "a.@@@@.c"}}) is None

    def test_payload_sin_data(self):
        import base64
        p = base64.urlsafe_b64encode(b'{"otra":1}').decode().rstrip("=")
        assert lk._token_de_precio({"x": {"priceToken": f"h.{p}.s"}}) is None

    def test_falta_id_o_seller_o_precio(self):
        import base64
        for data in ({"seller": "1", "priceWithoutDiscount": 100},
                     {"id": "1", "priceWithoutDiscount": 100},
                     {"id": "1", "seller": "1"}):
            p = base64.urlsafe_b64encode(json.dumps({"data": data}).encode()).decode().rstrip("=")
            assert lk._token_de_precio({"x": {"priceToken": f"h.{p}.s"}}) is None

    def test_sin_token(self):
        assert lk._token_de_precio({"x": {"Price": 100}}) is None
        assert lk._token_de_precio(None) is None


def token_de(centavos):
    import base64
    p = base64.urlsafe_b64encode(json.dumps(
        {"data": {"id": "195", "seller": "1", "priceWithoutDiscount": centavos}}).encode()
    ).decode().rstrip("=")
    return f"header.{p}.firma"


class TestLogicaPura:
    """_detectar_promo_cantidad no toca red: se le pasan las simulaciones."""

    def test_3x2_del_caso_real(self):
        d = lk._detectar_promo_cantidad([(2, BASE), (3, OFERTA)], BASE)
        assert d["activo"] is True
        assert d["precio_original"] == 5899.0
        assert d["precio_oferta"] == 3932.86
        assert d["promocion"] == "3x2"
        assert d["cantidad_minima"] == 3
        assert d["vigencia"] is None

    def test_2x1_gana_a_3_si_ya_baja_en_2(self):
        d = lk._detectar_promo_cantidad([(2, 50.0), (3, 40.0)], 100.0)
        assert d["cantidad_minima"] == 2
        assert d["promocion"] == "2x1"

    def test_toma_la_menor_cantidad_que_baja(self):
        d = lk._detectar_promo_cantidad([(2, 50.0), (3, 66.0), (4, 25.0)], 100.0)
        assert d["cantidad_minima"] == 2

    def test_sin_descuento_devuelve_none(self):
        assert lk._detectar_promo_cantidad([(2, BASE), (3, BASE)], BASE) is None
        assert lk._detectar_promo_cantidad([], BASE) is None

    def test_usa_el_precio_de_vtex_no_la_cuenta(self):
        """3932.86 viene de la simulacion; lista*2/3 daria 3932.67."""
        d = lk._detectar_promo_cantidad([(3, OFERTA)], BASE)
        assert d["precio_oferta"] == 3932.86
        assert round(BASE * 2 / 3, 2) == 3932.67

    def test_descuento_que_no_es_multi_compra_queda_sin_etiqueta(self):
        d = lk._detectar_promo_cantidad([(2, 85.0), (3, 85.0)], 100.0)
        assert d["cantidad_minima"] == 2
        assert d["promocion"] == ""

    def test_precios_basura_se_ignoran(self):
        d = lk._detectar_promo_cantidad([("x", None), (None, 50.0), (2, 50.0)], 100.0)
        assert d["cantidad_minima"] == 2

    def test_precio_cero_o_negativo_no_es_promo(self):
        assert lk._detectar_promo_cantidad([(2, 0), (3, -5)], BASE) is None

    def test_entradas_invalidas(self):
        assert lk._detectar_promo_cantidad([(2, 50.0)], 0) is None
        assert lk._detectar_promo_cantidad([(2, 50.0)], None) is None
        assert lk._detectar_promo_cantidad("no soy lista", BASE) is None
        assert lk._detectar_promo_cantidad(None, BASE) is None


class TestPromoCantidadConRed:
    def _mockear(self, monkeypatch, precios):
        """Mockea la simulacion de carrito. Devuelve las cantidades pedidas."""
        pedidas = []

        def fake(fuente, token, cantidad):
            pedidas.append(cantidad)
            return precios.get(cantidad)

        monkeypatch.setattr(lk, "_simular_carrito", fake)
        return pedidas

    def test_detecta_la_promo_real(self, monkeypatch):
        self._mockear(monkeypatch, {2: BASE, 3: OFERTA})
        d = lk._promo_cantidad(estado_de_fixture(), "masonline")
        assert d["promocion"] == "3x2"
        assert d["cantidad_minima"] == 3
        assert d["precio_oferta"] == 3932.86

    def test_corta_si_ya_baja_en_2(self, monkeypatch):
        """Si la 2x1 esta, no hay que preguntar por la 3."""
        pedidas = self._mockear(monkeypatch, {2: 50.0, 3: 50.0})
        lk._promo_cantidad({"x": {"priceToken": token_de(10000)}}, "masonline")
        assert pedidas == [2]

    def test_simula_las_dos_cantidades_cuando_no_alcanza(self, monkeypatch):
        pedidas = self._mockear(monkeypatch, {})
        lk._promo_cantidad({"x": {"priceToken": token_de(10000)}}, "masonline")
        assert pedidas == [2, 3]

    def test_sin_token_no_toca_la_red(self, monkeypatch):
        pedidas = self._mockear(monkeypatch, {2: 1.0, 3: 1.0})
        assert lk._promo_cantidad({}, "masonline") is None
        assert pedidas == []

    def test_error_de_red_no_revienta(self, monkeypatch):
        def explota(*a, **k):
            raise requests_error()
        monkeypatch.setattr(lk, "_simular_carrito", explota)
        assert lk._promo_cantidad({"x": {"priceToken": token_de(10000)}}, "masonline") is None


def requests_error():
    import requests
    return requests.RequestException("boom")


class TestSimularCarrito:
    def _resp(self, monkeypatch, body, status=200):
        import requests

        class R:
            def __init__(self):
                self.status = status

            def raise_for_status(self):
                if self.status >= 400:
                    raise requests.HTTPError("http " + str(self.status))

            def json(self):
                if isinstance(body, Exception):
                    raise body
                return body

        monkeypatch.setattr(lk.requests, "get", lambda *a, **k: R())

    def test_devuelve_el_precio_en_pesos(self, monkeypatch):
        self._resp(monkeypatch, {"items": [{"sellingPrice": 393286}]})
        assert lk._simular_carrito("masonline", {"id": "1", "seller": "1"}, 3) == 3932.86

    def test_arma_los_parametros_correctos(self, monkeypatch):
        import requests
        vistos = {}

        class R:
            def raise_for_status(self):
                pass

            def json(self):
                return {"items": [{"sellingPrice": 1000}]}

        def get(url, params=None, headers=None, timeout=None):
            vistos.update(url=url, params=params)
            return R()

        monkeypatch.setattr(lk.requests, "get", get)
        lk._simular_carrito("masonline", {"id": "195", "seller": "1"}, 3)
        assert vistos["params"] == {
            "request.items[0].id": "195",
            "request.items[0].quantity": "3",
            "request.items[0].seller": "1",
        }
        assert "masonline.com.ar" in vistos["url"]

    def test_sin_items(self, monkeypatch):
        self._resp(monkeypatch, {"items": []})
        assert lk._simular_carrito("masonline", {"id": "1", "seller": "1"}, 3) is None

    def test_json_invalido(self, monkeypatch):
        self._resp(monkeypatch, ValueError("no json"))
        assert lk._simular_carrito("masonline", {"id": "1", "seller": "1"}, 3) is None

    def test_http_error(self, monkeypatch):
        self._resp(monkeypatch, {}, status=500)
        assert lk._simular_carrito("masonline", {"id": "1", "seller": "1"}, 3) is None

    def test_selling_price_que_no_es_numero(self, monkeypatch):
        self._resp(monkeypatch, {"items": [{"sellingPrice": "n/d"}]})
        assert lk._simular_carrito("masonline", {"id": "1", "seller": "1"}, 3) is None


class TestIntegracionConScrape:
    def test_el_precio_de_referencia_pasa_a_ser_el_efectivo(self, monkeypatch):
        monkeypatch.setattr(lk, "_simular_carrito",
                            lambda f, t, c: {2: BASE, 3: OFERTA}.get(c))
        r = lk._parse_vea(fixture_html(), "7790895067570", "masonline", url="")
        assert r["precio_referencia"] == 3932.86
        assert r["descuento"]["cantidad_minima"] == 3
        assert r["descuento"]["precio_original"] == 5899.0

    def test_sin_promo_el_precio_queda_el_de_lista(self, monkeypatch):
        monkeypatch.setattr(lk, "_simular_carrito", lambda f, t, c: BASE)
        r = lk._parse_vea(fixture_html(), "7790895067570", "masonline", url="")
        assert r["precio_referencia"] == 5899.0

    def test_vea_no_consulta_el_carrito(self, monkeypatch):
        """La promo de Vea sale del JSON-LD, no hay que gastar un request."""
        def explota(*a, **k):
            raise AssertionError("Vea no deberia pegarle al checkout")

        monkeypatch.setattr(lk, "_simular_carrito", explota)
        r = lk._parse_vea(fixture_html(), "7790895067570", "vea", url="")
        assert r["precio_referencia"] is not None

    def test_carrefour_no_consulta_el_carrito(self, monkeypatch):
        def explota(*a, **k):
            raise AssertionError("Carrefour no deberia pegarle al checkout")

        monkeypatch.setattr(lk, "_simular_carrito", explota)
        lk._scrape_producto(fixture_html(), "7790895067570", "carrefour", url="")

    def test_sin_cluster_no_consulta_el_carrito(self, monkeypatch):
        """El filtro tiene que evitar el request, no solo descartar el resultado."""
        def explota(*a, **k):
            raise AssertionError("sin cluster NxM no deberia consultar")

        monkeypatch.setattr(lk, "_simular_carrito", explota)
        h = '<script type="application/ld+json">{"@type":"Product","name":"P",' \
            '"offers":{"price":100,"priceSpecification":{"price":100}}}</script>' \
            '<script>window.__STATE__={};</script>'
        r = lk._parse_vea(h, "7790000000000", "masonline", url="")
        assert r["descuento"] is None

    def test_si_ya_hay_descuento_no_se_repregunta(self, monkeypatch):
        def explota(*a, **k):
            raise AssertionError("ya hay descuento del JSON-LD")

        monkeypatch.setattr(lk, "_simular_carrito", explota)
        h = '<script id="structured-data-schema" type="application/ld+json">' \
            '{"@type":"Product","name":"P","offers":{"price":3926.67,' \
            '"priceSpecification":{"price":5890}}}</script>' \
            '<script>window.__STATE__=' + html_con_cluster("3x2 Bebidas") + ';</script>'
        r = lk._parse_vea(h, "7790000000000", "masonline", url="")
        assert r["descuento"]["precio_oferta"] == 3926.67
        assert r["descuento"]["cantidad_minima"] is None


class TestNormalizarDescuento:
    def test_todo_descuento_tiene_las_mismas_claves(self):
        for d in (
            {"activo": True, "precio_original": 100, "precio_oferta": 50, "promocion": "2x1"},
            {"activo": False, "precio_original": None, "precio_oferta": None, "promocion": "3x2"},
            {"activo": True, "precio_original": 100, "precio_oferta": 50,
             "promocion": "", "vigencia": "2026-10-01", "cantidad_minima": 3},
        ):
            out = lk._normalizar_descuento(d)
            assert set(out) == {"activo", "precio_original", "precio_oferta",
                                "promocion", "vigencia", "cantidad_minima"}

    def test_promocion_vacia_no_es_none(self):
        assert lk._normalizar_descuento({"activo": False, "promocion": None})["promocion"] == ""

    def test_activo_siempre_booleano(self):
        assert lk._normalizar_descuento({"activo": 1})["activo"] is True
        assert lk._normalizar_descuento({})["activo"] is False

    def test_none_sigue_siendo_none(self):
        assert lk._normalizar_descuento(None) is None
        assert lk._normalizar_descuento("texto") is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
