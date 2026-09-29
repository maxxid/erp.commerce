"""Tests del registro de fuentes de scraping.

Cubre el renombre a "Supercoco (experimental)" y el flag SCRAPER_FUENTES_OFF,
que es lo que permite apagar una fuente que rompio sin tocar el codigo.
"""

import pytest

from app.services import lookup_service as lk


class TestNombreCanonico:
    def test_supercoco_marca_experimental(self):
        assert lk.nombre_fuente("supercoco") == "Supercoco (experimental)"

    def test_las_otras_no_cambian(self):
        assert lk.nombre_fuente("carrefour") == "Carrefour"
        assert lk.nombre_fuente("vea") == "Vea"
        assert lk.nombre_fuente("masonline") == "MasOnline"

    def test_solo_supercoco_es_experimental(self):
        experimentales = [f for f in lk.FUENTES if lk.esta_experimental(f)]
        assert experimentales == ["supercoco"]

    def test_fuente_desconocida_devuelve_la_clave(self):
        assert lk.nombre_fuente("desconocida") == "desconocida"

    def test_no_le_importa_la_causa(self):
        assert lk.nombre_fuente("SuperCoco") == "Supercoco (experimental)"
        assert lk.esta_experimental("SUPERcoco") is True

    def test_clave_vacia_no_revienta(self):
        assert lk.nombre_fuente(None) == ""
        assert lk.nombre_fuente("") == ""
        assert lk.esta_experimental(None) is False


class TestApagadoPorConfig:
    def test_sin_config_todas_activas(self):
        assert lk.fuentes_activas() == list(lk.FUENTES)

    def test_apaga_una_fuente(self, monkeypatch):
        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", "supercoco")
        activas = lk.fuentes_activas()
        assert "supercoco" not in activas
        assert len(activas) == len(lk.FUENTES) - 1

    def test_apaga_varias(self, monkeypatch):
        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", "supercoco, vea")
        assert lk.fuentes_activas() == ["carrefour", "masonline"]

    def test_tolera_espacios_y_causa(self, monkeypatch):
        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", " SuperCoco , ")
        assert "supercoco" not in lk.fuentes_activas()

    def test_ignora_nombres_que_no_existen(self, monkeypatch):
        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", "noexiste,supercoco")
        assert lk.fuentes_activas() == ["carrefour", "vea", "masonline"]

    def test_guion_bajo(self, monkeypatch):
        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", "")
        assert len(lk.fuentes_activas()) == 4


class TestNoConsultaApagadas:
    def test_comparar_precios_no_toca_la_fuente_apagada(self, monkeypatch):
        """Una fuente apagada no puede generar ni un request."""
        llamadas = []

        def fake(barcode, fuente):
            llamadas.append(fuente)
            if fuente == "vea":
                return {
                    "precio_referencia": 1000.0,
                    "nombre": "Test",
                    "url": "u",
                    "descuento": None,
                }
            return None

        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", "supercoco")
        monkeypatch.setattr(lk, "_lookup_fuente", fake)

        precios = lk.comparar_precios("7790001234567")

        assert "supercoco" not in llamadas
        assert [p["fuente"] for p in precios] == ["vea"]

    def test_lookup_producto_tampoco(self, monkeypatch):
        llamadas = []
        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", "supercoco")
        monkeypatch.setattr(lk, "_lookup_fuente", lambda b, f: llamadas.append(f))

        lk.lookup_producto("7790001234567")
        assert "supercoco" not in llamadas

    def test_una_fuente_explisitamente_pedida_sigue_funcionando(self, monkeypatch):
        """lookup_producto(fuente=...) es un pedido directo, no un barrido."""
        llamadas = []
        monkeypatch.setattr(lk.settings, "SCRAPER_FUENTES_OFF", "supercoco")
        monkeypatch.setattr(
            lk,
            "_lookup_fuente",
            lambda b, f: llamadas.append(f) or {"precio_referencia": 1.0, "nombre": "X"},
        )

        lk.lookup_producto("7790001234567", fuente="supercoco")
        assert llamadas == ["supercoco"]


class TestPayload:
    def test_comparar_precios_manda_el_nombre_y_el_flag(self, monkeypatch):
        monkeypatch.setattr(
            lk,
            "_lookup_fuente",
            lambda b, f: {
                "precio_referencia": 1000.0,
                "nombre": "Test",
                "url": "u",
                "descuento": None,
            },
        )

        precios = lk.comparar_precios("7790001234567")
        por_fuente = {p["fuente"]: p for p in precios}

        assert por_fuente["supercoco"]["nombre_fuente"] == "Supercoco (experimental)"
        assert por_fuente["supercoco"]["experimental"] is True
        assert por_fuente["vea"]["nombre_fuente"] == "Vea"
        assert por_fuente["vea"]["experimental"] is False
