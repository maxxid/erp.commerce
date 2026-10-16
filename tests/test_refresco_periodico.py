"""Refresco automático de la pantalla, en un solo lugar.

El dueño lo pidió probando la Fase E: la venta sin conexión andaba, pero
**nada se actualizaba solo**. Revisado, estaba desparejo:

- `CajaView` y `POSView` refrescaban el estado de la caja cada 60 s, cada una
  con su timer armado a mano.
- `CobroMóvilView` —la pantalla que más mira el cajero en el celular— **no
  refrescaba nada**: lo único que se actualizaba era lo que se tocaba.

`useRefrescoPeriodico` es el timer único que comparten las tres y hace tres
cosas por tick: sube lo que quedó sin conexión (gratis si no hay nada),
refresca el estado de la caja y, cada 5 ticks, pregunta si cambió el catálogo.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "frontend" / "src"

REFRESCO = SRC / "composables" / "useRefrescoPeriodico.js"
VISTAS = {
    "POSView": SRC / "views" / "POSView.vue",
    "CajaView": SRC / "views" / "CajaView.vue",
    "CobroMovilView": SRC / "views" / "CobroMovilView.vue",
}


def _leer(path):
    return path.read_text(encoding="utf-8")


def _cuerpo():
    return _leer(REFRESCO)


class TestUnSoloRefresco:
    def test_las_tres_pantallas_lo_usan(self):
        for nombre, path in VISTAS.items():
            assert "useRefrescoPeriodico()" in _leer(path), (
                f"{nombre} no refresca sola: la pantalla queda congelada "
                "hasta que alguien toque algo"
            )

    def test_nadie_se_arma_su_timer_propio(self):
        """Tres timers iguales con tres comportamientos distintos es como no
        tener ninguno: el que falta es el que nadie se acuerda de poner."""
        for nombre, path in VISTAS.items():
            vista = _leer(path)
            assert "cajaStore.refrescarPeriodicamente()" not in vista, (
                f"{nombre} sigue refrescando la caja por su cuenta"
            )

        assert "cajaStore.refrescarPeriodicamente()" in _cuerpo()

    def test_es_un_solo_intervalo_que_se_limpia_al_desmontar(self):
        texto = _cuerpo()

        assert "setInterval(tick, TICK_MS)" in texto
        assert "clearInterval(timer)" in texto
        assert "onMounted(" in texto and "onUnmounted(" in texto


class TestLoQueSeRefresca:
    def test_cada_60_segundos(self):
        assert "TICK_MS = 60000" in _cuerpo()

    def test_las_tres_cosas_en_el_mismo_tick(self):
        texto = _cuerpo()

        # 1. Lo que quedó sin conexión. Sin esto, la cola se subía solo al
        #    montar una pantalla o si el navegador disparaba `online`.
        assert "await sincronizarPendientes()" in texto
        # 2. El estado de la caja: es lo que decide si se puede cobrar.
        assert "await cajaStore.refrescarPeriodicamente()" in texto
        # 3. Si cambió el catálogo se baja; si no, ~100 bytes.
        assert "await productosStore.fetchAll()" in texto

    def test_el_catalogo_no_se_pregunta_cada_60_segundos(self):
        """Si cambió se baja el completo (0,41 MB): con internet por hotspot,
        preguntarlo cada minuto es gastar datos en algo que en 5 minutos no
        cambia de verdad."""
        texto = _cuerpo()

        assert "TICKS_CATALOGO = 5" in texto
        cuerpo = texto[texto.index("async function tick("):]
        assert cuerpo.index("productosStore.fetchAll()") > cuerpo.index("ticks++")


class TestNoGastaCuandoNoHayRed:
    def test_sin_red_no_se_reintenta_nada(self):
        """Cada intento son hasta 30 s de espera contra un servidor que no
        contesta, repetidos cada 60 s: eso solo gasta batería."""
        assert "if (cajaStore.sinRed) return" in _cuerpo()

    def test_un_tick_que_no_termino_no_arranca_otro(self):
        assert "if (corriendo) return" in _cuerpo()

    def test_un_fallo_no_tumba_el_refresco(self):
        texto = _cuerpo()
        cuerpo = texto[texto.index("async function tick("):]

        assert "finally {" in cuerpo, (
            "si un tick se rompe y no libera el flag, el refresco deja de "
            "andar para siempre"
        )
