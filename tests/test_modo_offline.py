"""Modo offline: que un corte no le cierre la puerta al que está trabajando.

La app ya tenía PWA (service worker cacheando el shell), cola de ventas
pendientes y un indicador de "sin conexión". Lo que faltaba —y lo que hacía
que el modo offline no existiera en la práctica— era el arranque:

  1. `checkLicense()` sin red fallaba y la pantalla de login se convertía en
     la de **activación de licencia**, como si el comercio no tuviera licencia.
  2. `checkAutoLogin()` sin red fallaba y hacía `clearToken()`: te borraba la
     sesión. Con eso, cada corte de internet desloguaba a todos.
  3. `api.js` no distinguía "se cortó la red" de "sesión vencida": un TypeError
     de fetch salía crudo, sin status, y las decisiones que dependen de esa
     diferencia no podían tomarse.
  4. `navigator.onLine` solo sabe si hay tarjeta de red. Con el wifi levantado
     y sin internet el indicador no aparecía.

Ojo con lo que **no** se hizo: `/api/licencia/estado` y `/api/auth/me` no se
agregaron al caché del service worker. Cachear respuestas de autenticación
hace que la app muestre "estás adentro" con datos viejos y sin forma de
enterarse de que el servidor ya no lo acepta. La caché vive en localStorage, es
explícita, y solo se usa cuando el fallo es de red.
"""

from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
FRONT = RAIZ / "frontend" / "src"
API_JS = FRONT / "services" / "api.js"
AUTH_JS = FRONT / "stores" / "auth.js"
APP_VUE = FRONT / "App.vue"
LOGIN_VUE = FRONT / "views" / "LoginView.vue"
INDICADOR = FRONT / "components" / "layout" / "OfflineIndicator.vue"
SW = RAIZ / "frontend" / "public" / "sw.js"


def _leer(path):
    return path.read_text(encoding="utf-8")


class TestErroresDeRed:
    def test_api_marca_los_errores_de_red(self):
        """Sin status 0 nadie puede distinguir un corte de un 401."""
        texto = _leer(API_JS)

        assert "function errorDeRed(mensaje)" in texto
        assert "error.status = 0" in texto
        assert "export function esErrorDeRed(error)" in texto

    def test_el_timeout_tambien_es_error_de_red(self):
        texto = _leer(API_JS)

        assert "throw errorDeRed('El servidor no responde (timeout)')" in texto
        assert "throw errorDeRed('Sin conexión con el servidor')" in texto

    def test_el_401_sigue_echando_al_usuario(self):
        """No se puede blanquear el 401: eso sí es sesión vencida de verdad."""
        texto = _leer(API_JS)

        assert "response.status === 401" in texto


class TestArranqueSinRed:
    def test_la_licencia_se_consulta_de_lo_cacheado(self):
        texto = _leer(AUTH_JS)

        assert "const CLAVE_LICENCIA = 'apex-licencia-cache'" in texto
        # Sin tarjeta de red el fetch tarda hasta el timeout en fallar.
        assert "if (!navigator.onLine && cache)" in texto
        assert "usarLicenciaCache(cache)" in texto

    def test_la_sesion_no_se_borra_si_fallo_la_red(self):
        texto = _leer(AUTH_JS)

        assert "const CLAVE_SESION = 'apex-sesion-offline'" in texto
        assert "esErrorDeRed(e) && cache" in texto
        # El clearToken del auto-login solo puede quedar para el error real.
        assert texto.count("api.clearToken()") == 2, (
            "quedó un clearToken sin distinguir el motivo: echaría al usuario "
            "cada vez que se corta el internet"
        )

    def test_se_guarda_la_sesion_al_loguearse(self):
        """Si no se guarda al entrar, al cortarse la red no hay nada que restaurar."""
        texto = _leer(AUTH_JS)

        assert "escribirCache(CLAVE_SESION, currentUser.value)" in texto

    def test_el_logout_borra_la_sesion_cacheada(self):
        """Cerrar sesión es una decisión: no se vuelve a entrar sin red."""
        texto = _leer(AUTH_JS)

        assert "localStorage.removeItem(CLAVE_SESION)" in texto


class TestVolverDeLaRed:
    def test_al_volver_se_revalida_licencia_y_token(self):
        texto = _leer(APP_VUE)

        assert "function onOnline()" in texto
        assert "auth.revalidar()" in texto
        assert "window.addEventListener('online', onOnline)" in texto

    def test_revalidar_quita_el_modo_offline(self):
        texto = _leer(AUTH_JS)

        assert "async function revalidar()" in texto


class TestAvisos:
    def test_el_indicador_no_confia_solo_en_navigator_online(self):
        texto = _leer(INDICADOR)

        assert "auth.offline" in texto, (
            "navigator.onLine solo ve la tarjeta de red: con wifi levantado y "
            "sin internet no aparecía ningún aviso"
        )
        assert "Modo offline" in texto

    def test_el_login_explica_que_sin_red_no_puede_confirmar_la_clave(self):
        texto = _leer(LOGIN_VUE)

        assert "auth.offline" in texto
        assert "Sin conexión con el servidor" in texto


def test_el_service_worker_no_cachea_autenticacion():
    """Lo que decide si alguien puede entrar no se guarda en el caché del SW."""
    texto = _leer(SW)

    assert "/api/auth" not in texto
    assert "/api/licencia" not in texto
