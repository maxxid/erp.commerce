"""Fase D — eficientizar: que desconectar salga barato.

El negocio trabaja casi siempre con internet por hotspot (limitado), tiene un
día sin internet, y al dueño le importa que **si se va el negocio siga
andando**. La eficiencia acá no es un fin en sí misma: es lo que hace que
desconectar sea un no-evento en vez de un "modo" aparte con sus bugs.

Se arreglaron cuatro cosas:

1. **Refrescar no cuesta bajar el catálogo entero.** Antes eran tres requests
   y 0,41 MB en cada apertura de la pantalla de cobro. Ahora se pregunta si
   cambió (~100 bytes) y solo se descarga si cambió; sin señal no se intenta
   nada.
2. **El celular sube las ventas al abrir.** Sincronizaba solo con el evento
   `online`, que dispara solo si antes estuvo desconectado: el cajero llegaba a
   su casa con wifi ya encendido y la plata quedaba quieta hasta que alguien
   apretara "Sincronizar ahora". (Ese punto de subida hoy es `useOfflineSync`,
   que además sube las operaciones de caja de la Fase E.)
3. **Se ve cuánto hay en juego.** "3 ventas sin subir" no dice si son $3.000 o
   $300.000.
4. **El poll de caja se pausa cuando la red falló.** Reintentar cada 60 s contra
   un servidor que no responde solo gasta batería.

Además: `POST /api/catalogo/descargar` exige admin o encargado, y CobroMóvil lo
llamaba **en cada apertura** (sin el rate limit que sí tenían App.vue y
POSView), dentro del `await` — o sea, un 403 silencioso para todo cajero, que
encima frenaba el momento en que se ven los productos.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "frontend" / "src"

COBRO = SRC / "views" / "CobroMovilView.vue"
POS = SRC / "views" / "POSView.vue"
CAJA_VIEW = SRC / "views" / "CajaView.vue"
INDICADOR = SRC / "components" / "layout" / "OfflineIndicator.vue"
COLA = SRC / "composables" / "useOfflineSales.js"
SINCRONIZAR = SRC / "composables" / "useOfflineSync.js"
REFRESCO = SRC / "composables" / "useRefrescoPeriodico.js"
STORE_CAJA = SRC / "stores" / "caja.js"
STORE_PRODUCTOS = SRC / "stores" / "productos.js"


def _leer(path):
    return path.read_text(encoding="utf-8")


def _cuerpo(texto, nombre, siguiente):
    """Lo que hay entre una función y la siguiente: da el cuerpo sin adivinar."""
    inicio = texto.index(f"async function {nombre}(")
    fin = texto.index(f"async function {siguiente}(", inicio)
    return texto[inicio:fin]


def _on_mounted(texto):
    """Del onMounted hasta que cierra: es lo que se espera antes de ver la pantalla."""
    inicio = texto.index("onMounted(async () => {")
    fin = texto.index("document.addEventListener('click', handleClickOutside)", inicio)
    return texto[inicio:fin]


class TestElCelularSubeAlAbrir:
    def test_cobro_movil_sincroniza_al_montar(self):
        """El hueco: solo sincronizaba con el evento `online`, que dispara si
        antes estuvo desconectado. Quien llega con wifi ya encendido no sube
        nada aunque haya ventas esperando."""
        cuerpo = _on_mounted(_leer(COBRO))

        assert "sincronizarPendientes()" in cuerpo, (
            "CobroMóvil no sube las ventas encoladas al abrir: la plata se "
            "queda quieta hasta que alguien apriete 'Sincronizar ahora'"
        )

    def test_sincronizar_al_abrir_no_cuesta_si_no_hay_nada(self):
        """Si no hay pendientes no se hace ni un request: es gratis."""
        texto = _leer(SINCRONIZAR)

        assert "eventos.length === 0) return { subidas: 0, fallidas: 0 }" in texto
        assert "if (subiendo ||" in texto


class TestRefrescarBarato:
    def test_el_catalogo_de_r2_no_se_descarga_en_cada_apertura(self):
        texto = _leer(COBRO)

        assert "catalogo_last_sync" in texto, (
            "sin rate limit se volvía a descargar el catálogo central de R2 en "
            "cada apertura de la pantalla de cobro"
        )
        assert "Date.now() - Number(lastSync) < hour" in texto

    def test_no_se_pide_lo_que_el_cajero_no_puede_pedir(self):
        """El endpoint exige admin o encargado: para un cajero siempre fue 403."""
        texto = _leer(COBRO)

        assert "if (!auth.isEncargado) return" in texto

    def test_no_frena_la_pantalla_de_cobro(self):
        """Estaba dentro del `await Promise.all`: el cajero esperaba a que
        termine un request que además le contestaba 403."""
        cuerpo = _on_mounted(_leer(COBRO))

        assert "catalogo/descargar" not in cuerpo, (
            "la descarga del catálogo de R2 sigue frenando la pantalla de cobro"
        )

    def test_baja_el_catalogo_en_un_solo_pedido(self):
        texto = _leer(STORE_PRODUCTOS)

        assert "api.get('/api/catalogo/local')" in texto
        assert "api.get('/api/catalogo/version')" in texto


class TestCuantoHaySinSubir:
    def test_el_indicador_muestra_el_monto(self):
        texto = _leer(INDICADOR)

        assert "montoSinSubir" in texto
        assert "sin subir" in texto
        assert "formatCurrency as fc" in texto

    def test_el_total_se_calcula_de_los_items_de_la_cola(self):
        texto = _leer(COLA)

        assert "export function totalDeVenta(data)" in texto, (
            "sin esta función no había forma de decir cuánto hay en juego: "
            "las vistas encolaban la venta sin su total"
        )

    def test_la_cola_guarda_el_total_al_encolar(self):
        texto = _leer(COLA)

        assert "total: totalDeVenta(saleData)" in texto

    def test_el_indicador_usa_el_total_guardado_y_si_no_lo_tiene_lo_calcula(self):
        texto = _leer(INDICADOR)

        assert "totalDeVenta(s.data)" in texto, (
            "las ventas encoladas antes de esto no tienen `total` guardado"
        )


class TestElPollNoGastaCuandoNoHayRed:
    def test_se_pausa_cuando_la_red_dejo_de_contestar(self):
        texto = _leer(STORE_CAJA)

        assert "import api, { esErrorDeRed } from '@/services/api'" in texto
        assert "if (esErrorDeRed(e)) sinRed.value = true" in texto

    def test_el_guard_solo_esta_en_el_refresco_periodico(self):
        """`fetchEstado` a mano tiene que seguir pidiendo siempre: es lo que
        hace que entrar a una pantalla nunca quede con datos viejos por un
        corte anterior que ya se superó."""
        texto = _leer(STORE_CAJA)
        fetch = _cuerpo(texto, "fetchEstado", "refrescarPeriodicamente")
        periodico = _cuerpo(texto, "refrescarPeriodicamente", "fetchUltimoCierre")

        assert "if (sinRed.value) return" not in fetch, (
            "fetchEstado quedó con el guard: una pantalla que lo pida a mano "
            "no iba a refrescar nunca"
        )
        assert "if (sinRed.value) return" in periodico
        assert texto.count("if (sinRed.value) return") == 1

    def test_un_pedido_a_mano_vuelve_a_habilitar_el_refresco(self):
        """Si no fuera así, un corte viejo dejaría el poll pausado para siempre."""
        texto = _leer(STORE_CAJA)
        fetch = _cuerpo(texto, "fetchEstado", "refrescarPeriodicamente")

        assert "sinRed.value = false" in fetch

    def test_al_volver_la_red_se_reanuda_solo(self):
        texto = _leer(STORE_CAJA)

        assert "window.addEventListener('online', () => { sinRed.value = false })" in texto

    def test_las_tres_pantallas_usan_el_mismo_refresco(self):
        """Antes Caja y POS armaban su timer a mano y **CobroMóvil —la
        pantalla que más mira el cajero— no refrescaba nada**: lo único que se
        actualizaba era lo que se tocaba."""
        for path in (POS, CAJA_VIEW, COBRO):
            texto = _leer(path)
            assert "useRefrescoPeriodico()" in texto, (
                f"{path.name} no refresca sola: hay que refrescar a mano"
            )
            assert "cajaStore.refrescarPeriodicamente()" not in texto, (
                f"{path.name} sigue con su timer propio: el refresco es uno solo"
            )

        assert "cajaStore.refrescarPeriodicamente()" in _leer(REFRESCO)
