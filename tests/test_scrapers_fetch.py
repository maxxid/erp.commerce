"""Capa de red: verifica el cableado entre fetch y parse.

Los tests de parseo usan fixtures directas, asi que no cubren que
_lookup_* le pase bien los argumentos al parser. Estos tests simulan requests.get
para comprobar esa union, sin tocar la red (sin_red lo bloquea a nivel de socket).
"""

import pytest
import requests

from app.services import lookup_service as ls

from conftest import BARCODE


class RespuestaFalsa:
    def __init__(self, text="", url="", json_data=None, status=200):
        self.text = text
        self.url = url
        self.encoding = "utf-8"
        self._json = json_data
        self._status = status

    def raise_for_status(self):
        if self._status >= 400:
            raise requests.HTTPError(f"HTTP {self._status}")

    def json(self):
        if self._json is None:
            raise ValueError("sin json")
        return self._json


def instalar(monkeypatch, *respuestas):
    """Devuelve el registro de URLs pedidas."""
    pedidas = []
    cola = list(respuestas)

    def fake_get(url, **kwargs):
        pedidas.append((url, kwargs))
        if not cola:
            raise AssertionError(f"request inesperada a {url}")
        r = cola.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(ls.requests, "get", fake_get)
    return pedidas


class TestSuperCocoFetch:
    def test_wirea_html_y_url_de_busqueda(self, monkeypatch, leer_fixture, sin_cache):
        instalar(monkeypatch, RespuestaFalsa(leer_fixture("supercoco_busqueda.html")))
        p = ls._lookup_supercoco(BARCODE)

        assert p["nombre"] == "Alfajor Blanco 125g"
        assert p["precio_referencia"] == 2400.0
        assert p["url"] == "https://supercoco.com.ar/alfajor-blanco-125g"

    def test_error_de_red_devuelve_none(self, monkeypatch):
        instalar(monkeypatch, requests.ConnectionError("sin red"))
        assert ls._lookup_supercoco(BARCODE) is None

    def test_http_error_devuelve_none(self, monkeypatch):
        instalar(monkeypatch, RespuestaFalsa("", status=503))
        assert ls._lookup_supercoco(BARCODE) is None

    def test_usa_el_timeout_configurado(self, monkeypatch):
        pedidas = instalar(monkeypatch, RespuestaFalsa("<html></html>"))
        ls._lookup_supercoco(BARCODE)
        assert pedidas[0][1]["timeout"] == ls.TIMEOUT


class TestCarrefourFetch:
    def test_wirea_el_json_de_la_api(self, monkeypatch, leer_json, sin_cache):
        instalar(monkeypatch, RespuestaFalsa(json_data=leer_json("carrefour_producto.json")))
        p = ls._lookup_carrefour_api(BARCODE)

        assert p["nombre"] == "Gaseosa - Cola 2,25 L"
        assert p["precio_referencia"] == 2400.0
        assert p["descuento"]["precio_original"] == 3100.0

    def test_json_invalido_devuelve_none(self, monkeypatch):
        instalar(monkeypatch, RespuestaFalsa())
        assert ls._lookup_carrefour_api(BARCODE) is None

    def test_usa_el_timeout_configurado(self, monkeypatch):
        pedidas = instalar(monkeypatch, RespuestaFalsa(json_data=[]))
        ls._lookup_carrefour_api(BARCODE)
        assert pedidas[0][1]["timeout"] == ls.TIMEOUT


class TestVeaFetch:
    def test_busqueda_que_redirige_directo_al_producto(self, monkeypatch, leer_fixture, sin_cache):
        html = leer_fixture("vea_producto.html")
        instalar(monkeypatch, RespuestaFalsa(html, url=f"https://www.vea.com.ar/x/p"))
        p = ls._scrape_fuente(BARCODE, "vea")

        assert p["precio_referencia"] == 18500.0
        assert p["url"] == "https://www.vea.com.ar/x/p"

    def test_busqueda_con_dos_pasos(self, monkeypatch, leer_fixture, sin_cache):
        html = leer_fixture("vea_producto.html")
        busqueda = leer_fixture("masonline_busqueda.html")
        pedidas = instalar(
            monkeypatch,
            RespuestaFalsa(busqueda, url="https://www.vea.com.ar/buscar"),
            RespuestaFalsa(html, url="https://www.vea.com.ar/x/p"),
        )
        p = ls._scrape_fuente(BARCODE, "vea")

        assert p["precio_referencia"] == 18500.0
        assert len(pedidas) == 2
        assert pedidas[1][0] == "https://www.vea.com.ar/gaseosa-cola-2l/p"

    def test_sin_link_devuelve_none(self, monkeypatch, sin_cache):
        instalar(monkeypatch, RespuestaFalsa("<html>sin resultados</html>", url="https://www.vea.com.ar/buscar"))
        assert ls._scrape_fuente(BARCODE, "vea") is None

    def test_error_en_el_primer_request(self, monkeypatch):
        instalar(monkeypatch, requests.Timeout("timeout"))
        assert ls._scrape_fuente(BARCODE, "vea") is None

    def test_error_en_el_segundo_request(self, monkeypatch, sin_cache):
        instalar(
            monkeypatch,
            RespuestaFalsa("<html>res</html>", url="https://www.vea.com.ar/buscar"),
            requests.Timeout("timeout"),
        )
        assert ls._scrape_fuente(BARCODE, "vea") is None

    def test_timeout_en_ambos_requests(self, monkeypatch, leer_fixture, sin_cache):
        html = leer_fixture("vea_producto.html")
        pedidas = instalar(
            monkeypatch,
            RespuestaFalsa("<html>res</html>", url="https://www.vea.com.ar/buscar"),
            RespuestaFalsa(html),
        )
        ls._scrape_fuente(BARCODE, "vea")
        assert all(kwargs["timeout"] == ls.TIMEOUT for _, kwargs in pedidas)

    def test_masonline_usa_su_dominio(self, monkeypatch, sin_cache):
        pedidas = instalar(monkeypatch, requests.Timeout("timeout"))
        ls._scrape_fuente(BARCODE, "masonline")
        assert "www.masonline.com.ar" in pedidas[0][0]
