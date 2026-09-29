"""Cache de scraping y comparacion de precios.

La cache se probo con scripts temporales durante el desarrollo de la pantalla
de Precios Online; aca queda fija para que no se rompa en silencio.
"""

import pytest

from app.services import lookup_service as ls

from conftest import BARCODE


@pytest.fixture
def contador(monkeypatch):
    """Cuenta cuantas veces se scrapea de verdad, sin tocar la red."""
    llamadas = []

    def fake(barcode, fuente):
        llamadas.append(fuente)
        if fuente == "vea":
            return {"precio_referencia": 100.0, "nombre": "V", "marca": "M", "imagen_url": "", "url": "u"}
        return None

    monkeypatch.setattr(ls, "_scrape_fuente", fake)
    return llamadas


class TestCache:
    def test_segunda_llamada_no_vuelve_a_scrapear(self, sin_cache, contador):
        ls._lookup_fuente(BARCODE, "vea")
        ls._lookup_fuente(BARCODE, "vea")
        ls._lookup_fuente(BARCODE, "vea")
        assert contador == ["vea"]

    def test_fuente_distinta_se_cachea_por_separado(self, sin_cache, contador):
        ls._lookup_fuente(BARCODE, "vea")
        ls._lookup_fuente(BARCODE, "carrefour")
        assert contador == ["vea", "carrefour"]

    def test_barcode_distinto_no_usa_el_cache_de_otro(self, sin_cache, contador):
        ls._lookup_fuente(BARCODE, "vea")
        ls._lookup_fuente("7799999999999", "vea")
        assert contador == ["vea", "vea"]

    def test_cachea_tambien_los_fracasos(self, sin_cache, contador):
        assert ls._lookup_fuente(BARCODE, "masonline") is None
        assert ls._lookup_fuente(BARCODE, "masonline") is None
        assert contador == ["masonline"]

    def test_fallo_usa_ttl_corto(self, sin_cache):
        ls._cache_set("k", None)
        assert sin_cache._cache["k"][1] - ls.time.time() <= ls.CACHE_TTL_NEGATIVO

    def test_acierto_usa_ttl_largo(self, sin_cache):
        ls._cache_set("k", {"precio_referencia": 1.0})
        restante = sin_cache._cache["k"][1] - ls.time.time()
        assert restante > ls.CACHE_TTL_NEGATIVO
        assert restante <= ls.CACHE_TTL

    def test_entrada_vencida_se_purge(self, sin_cache):
        sin_cache._cache["k"] = ({"precio_referencia": 1.0}, ls.time.time() - 1)
        assert sin_cache._cache_get("k") == (None, False)
        assert "k" not in sin_cache._cache

    def test_no_crece_sin_limite(self, sin_cache):
        for i in range(600):
            sin_cache._cache[f"vencida{i}"] = (None, ls.time.time() - 1)
        sin_cache._cache_set("nueva", {"precio_referencia": 1.0})
        assert "nueva" in sin_cache._cache
        assert len(sin_cache._cache) < 600


class TestCompararPrecios:
    def test_ordena_de_menor_a_mayor(self, sin_cache, monkeypatch):
        precios = {
            "carrefour": 300.0, "vea": 100.0, "masonline": 500.0, "supercoco": 200.0,
        }
        monkeypatch.setattr(
            ls, "_scrape_fuente",
            lambda b, f: {"precio_referencia": precios.get(f), "nombre": f, "marca": "M", "imagen_url": "i", "url": "u"},
        )
        resultado = ls.comparar_precios(BARCODE)
        assert [r["precio"] for r in resultado] == [100.0, 200.0, 300.0, 500.0]

    def test_descarta_sin_precio(self, sin_cache, monkeypatch):
        monkeypatch.setattr(
            ls, "_scrape_fuente",
            lambda b, f: {"precio_referencia": None, "nombre": "X"} if f == "vea"
            else {"precio_referencia": 150.0, "nombre": f, "marca": "M", "imagen_url": "i", "url": "u"},
        )
        resultado = ls.comparar_precios(BARCODE)
        assert [r["fuente"] for r in resultado] == ["carrefour", "masonline", "supercoco"]

    def test_expone_marca_e_imagen(self, sin_cache, monkeypatch):
        monkeypatch.setattr(
            ls, "_scrape_fuente",
            lambda b, f: {"precio_referencia": 10.0, "nombre": "N", "marca": "Marca", "imagen_url": "http://i", "url": "u"},
        )
        r = ls.comparar_precios(BARCODE)[0]
        assert r["marca"] == "Marca"
        assert r["imagen_url"] == "http://i"

    def test_acepta_marca_vacia(self, sin_cache, monkeypatch):
        monkeypatch.setattr(
            ls, "_scrape_fuente",
            lambda b, f: {"precio_referencia": 10.0, "nombre": "N"},
        )
        r = ls.comparar_precios(BARCODE)[0]
        assert r["marca"] == ""
        assert r["imagen_url"] == ""

    def test_sin_resultados_devuelve_lista_vacia(self, sin_cache, monkeypatch):
        monkeypatch.setattr(ls, "_scrape_fuente", lambda b, f: None)
        assert ls.comparar_precios(BARCODE) == []


class TestConcurrencia:
    """El semaforo acota el scraping saliente y colapsa el stampede.

    Sin el re-check dentro del semaforo, N requests del mismo barcode que
    llegan juntos fallan la cache a la vez y los N salen a scrapear.
    """

    def test_requests_simultaneos_del_mismo_codigo_scraper_una_vez(self, sin_cache, monkeypatch):
        import threading
        import time

        llamadas = []
        barrera = threading.Barrier(6)

        def lento(barcode, fuente):
            llamadas.append(barcode)
            time.sleep(0.05)
            return {"precio_referencia": 10.0, "nombre": "X"}

        monkeypatch.setattr(ls, "_scrape_fuente", lento)

        resultados = []

        def worker():
            barrera.wait()
            resultados.append(ls._lookup_fuente(BARCODE, "vea"))

        hilos = [threading.Thread(target=worker) for _ in range(6)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        assert len(llamadas) == 1
        assert len(resultados) == 6
        assert all(r["precio_referencia"] == 10.0 for r in resultados)

    def test_no_supera_el_tope_de_scrapings_simultaneos(self, sin_cache, monkeypatch):
        import threading
        import time

        activa = {"n": 0, "max": 0}
        candado = threading.Lock()

        def lento(barcode, fuente):
            with candado:
                activa["n"] += 1
                activa["max"] = max(activa["max"], activa["n"])
            time.sleep(0.05)
            with candado:
                activa["n"] -= 1
            return {"precio_referencia": 1.0, "nombre": "X"}

        monkeypatch.setattr(ls, "_scrape_fuente", lento)

        barcodes = [f"77900000000{i}" for i in range(20)]
        hilos = [
            threading.Thread(target=ls._lookup_fuente, args=(b, "vea"))
            for b in barcodes
        ]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        assert activa["max"] <= ls.settings.SCRAPER_MAX_CONCURRENT

    def test_el_tope_es_configurable(self):
        assert ls.settings.SCRAPER_MAX_CONCURRENT >= 1

    def test_los_locks_no_se_acumulan(self, sin_cache, monkeypatch):
        # El dict de locks por clave crece si no se limpia al soltar.
        monkeypatch.setattr(
            ls, "_scrape_fuente",
            lambda b, f: {"precio_referencia": 1.0, "nombre": "X"},
        )
        for i in range(50):
            ls._lookup_fuente(f"77900000000{i}", "vea")
        assert ls._locks_por_clave == {}

    def test_locks_se_liberan_aunque_el_scrape_falle(self, sin_cache, monkeypatch):
        def revienta(barcode, fuente):
            raise ValueError("boom")
        monkeypatch.setattr(ls, "_scrape_fuente", revienta)

        with pytest.raises(ValueError):
            ls._lookup_fuente(BARCODE, "vea")
        assert ls._locks_por_clave == {}

    def test_un_lock_por_clave_no_bloquea_a_otro_codigo(self, sin_cache, monkeypatch):
        import threading
        import time

        arranca = threading.Event()

        def lento(barcode, fuente):
            if barcode == BARCODE:
                arranca.wait(timeout=2)
            return {"precio_referencia": 1.0, "nombre": "X"}

        monkeypatch.setattr(ls, "_scrape_fuente", lento)

        t1 = threading.Thread(target=ls._lookup_fuente, args=(BARCODE, "vea"))
        t1.start()
        arranca.set()
        time.sleep(0.02)

        # otro barcode debe poder scrapear sin esperar al primero
        assert ls._lookup_fuente("7790000000099", "vea") is not None
        t1.join(timeout=2)


class TestLookupProducto:
    def test_devuelve_el_primer_encontrado(self, sin_cache, monkeypatch):
        monkeypatch.setattr(
            ls, "_scrape_fuente",
            lambda b, f: {"precio_referencia": 99.0, "nombre": f} if f == "masonline" else None,
        )
        assert ls.lookup_producto(BARCODE)["nombre"] == "masonline"

    def test_una_sola_fuente_no_pisa_las_demas(self, sin_cache, monkeypatch):
        llamadas = []
        monkeypatch.setattr(
            ls, "_scrape_fuente",
            lambda b, f: llamadas.append(f) or {"precio_referencia": 1.0, "nombre": "X"},
        )
        ls.lookup_producto(BARCODE, fuente="vea")
        assert llamadas == ["vea"]

    def test_sin_match_devuelve_none(self, sin_cache, monkeypatch):
        monkeypatch.setattr(ls, "_scrape_fuente", lambda b, f: None)
        assert ls.lookup_producto(BARCODE) is None
