"""Fase E — el ciclo completo sin red: abrir, cobrar y cerrar.

El dueño tiene un día sin internet y quiere que **si se va, el negocio siga
andando**. Con el nivel 1 y la Fase D ya se podía entrar y vender; lo que faltaba
era que la jornada se pudiera **abrir** y **cerrar** igual, y que al volver la
red todo subiera **una sola vez**.

Lo que se hizo:

1. **La caja recuerda su estado.** Si no, refrescar la página sin internet
   mostraba "CAJA CERRADA" y el POS no dejaba cobrar aunque la caja estuviera
   abierta en el negocio.
2. **Una sola cola para abrir y cerrar** (`useOfflineCaja.postear`): si la red
   no contesta, la operación queda anotada y se aplica en el navegador al
   momento (la caja queda abierta/cerrada como quedó en el negocio).
3. **Un solo punto de subida** (`useOfflineSync`): ventas y caja se mezclan y
   suben **en el orden en que pasaron**. La venta necesita la caja abierta y el
   cierre necesita las ventas adentro: subirlas en dos tandas sueltas dejaba o
   la venta sin caja, o el cierre sin la venta.
4. **Nunca dos veces.** Antes de reintentar se le pregunta al servidor en qué
   estado está la caja; si la operación ya estaba hecha, no se vuelve a hacer.
   Esa reconciliación existe porque el servidor **no** es idempotente: `abrir_caja`
   y `cerrar_todo` tiran error si se los llama dos veces (y un error no es lo
   mismo que "ya estaba hecho").
"""

from pathlib import Path
import re

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Usuario, Sucursal
import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.services import caja_service as cs

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "frontend" / "src"

STORE_CAJA = SRC / "stores" / "caja.js"
COLA_CAJA = SRC / "composables" / "useOfflineCaja.js"
SYNC = SRC / "composables" / "useOfflineSync.js"
COLA_VENTAS = SRC / "composables" / "useOfflineSales.js"
INDICADOR = SRC / "components" / "layout" / "OfflineIndicator.vue"
SW = RAIZ / "frontend" / "public" / "sw.js"
VISTAS = {
    "CajaView": SRC / "views" / "CajaView.vue",
    "POSView": SRC / "views" / "POSView.vue",
    "CobroMovilView": SRC / "views" / "CobroMovilView.vue",
}


def _leer(path):
    return path.read_text(encoding="utf-8")


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add(Sucursal(id=1, nombre="Principal"))
        session.flush()
        session.add(Usuario(
            username="caja_fase_e", nombre="Cajero", password_hash="x",
            rol="admin", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _user_id(db):
    return db.query(Usuario).first().id


class TestElServidorNoEsIdempotente:
    """Por qué la subida tiene que reconciliar contra el estado y no mandar
    "la misma operación otra vez" a ver qué pasa."""

    def test_abrir_dos_veces_tira_error(self, db):
        cs.abrir_caja(db, 20000.0, _user_id(db))

        with pytest.raises(ValueError, match="Ya hay una caja abierta"):
            cs.abrir_caja(db, 20000.0, _user_id(db))

    def test_cerrar_dos_veces_tira_error(self, db):
        cs.abrir_caja(db, 20000.0, _user_id(db))
        cs.cerrar_todo(db, _user_id(db), "")

        with pytest.raises(ValueError, match="No hay caja abierta"):
            cs.cerrar_todo(db, _user_id(db), "")


class TestLoQueLaColaNecesitaSaber:
    """La cola sólo puede decidir "esto ya estaba hecho" si el servidor le dice
    en qué está la caja y qué arqueos ya cargó."""

    def test_el_estado_dice_si_esta_abierta(self, db):
        assert cs.obtener_estado_caja(db)["abierta"] is False

        cs.abrir_caja(db, 20000.0, _user_id(db))

        assert cs.obtener_estado_caja(db)["abierta"] is True

    def test_el_estado_lista_los_medios_ya_arqueados(self, db):
        """Si no, un arqueo reintentado se volvería a cargar y el monto
        arqueado del día saldría contado dos veces."""
        cs.abrir_caja(db, 20000.0, _user_id(db))
        assert "efectivo" not in cs.obtener_estado_caja(db)["metodos_cerrados"]

        cs.cerrar_metodo(db, "efectivo", 20000.0, _user_id(db), "")

        estado = cs.obtener_estado_caja(db)
        assert estado["abierta"] is True
        assert "efectivo" in estado["metodos_cerrados"]

    def test_al_cerrar_todo_el_estado_dice_que_no_hay_caja(self, db):
        cs.abrir_caja(db, 20000.0, _user_id(db))

        cs.cerrar_todo(db, _user_id(db), "")

        assert cs.obtener_estado_caja(db)["abierta"] is False


class TestLaCajaSeRecuerdaSinRed:
    def test_se_guarda_el_estado_en_el_navegador(self):
        texto = _leer(STORE_CAJA)

        assert "apex-caja-estado" in texto, (
            "sin estado persistido, un refresco sin internet mostraba "
            "'CAJA CERRADA' y el POS no dejaba cobrar"
        )
        assert "persistir()" in texto

    def test_se_restaura_al_arma_el_store(self):
        texto = _leer(STORE_CAJA)

        assert "const guardado = leerEstado()" in texto
        assert "aplicarEstado(guardado" in texto

    def test_no_restaura_la_caja_de_otro_dia(self):
        """El servidor da por cerrada una apertura de ayer (cambio de día):
        restaurarla abierta dejaba el POS cobrando contra una sesión inexistente."""
        texto = _leer(STORE_CAJA)

        assert "function esDeHoy(" in texto
        assert "esDeHoy(guardado.sesion_inicio)" in texto
        assert "esDeHoy(guardado.guardadoEn)" in texto, (
            "con un solo || sobre sesion_inicio, si la hora del servidor no se "
            "podia leer no se restauraba nada y la pantalla decia 'CAJA CERRADA' "
            "con la caja abierta en el negocio"
        )

    def test_hay_un_camino_local_para_abrir_y_para_cerrar(self):
        texto = _leer(STORE_CAJA)

        assert "function aplicarAperturaLocal(" in texto
        assert "function aplicarCierreLocal(" in texto
        assert texto.count("persistir()") >= 3, "cada cambio de estado hay que guardarlo"


class TestLaColaDeCaja:
    def test_solo_se_encolan_las_tres_operaciones_reconciliables(self):
        """Ingresos, egresos y extracciones no se pueden reconciliar: duplicar
        plata es peor que mostrar el error, así que siguen avisando en rojo."""
        texto = _leer(COLA_CAJA)

        assert "'/api/caja/apertura'" in texto
        assert "'/api/caja/cierre-metodo'" in texto
        assert "'/api/caja/cierre-total'" in texto
        assert "'/api/caja/ingreso'" not in texto
        assert "'/api/caja/egreso'" not in texto
        assert "no encolable" in texto

    def test_postear_encola_solo_si_fue_la_red(self):
        texto = _leer(COLA_CAJA)

        assert "if (!esErrorDeRed(e)) throw e" in texto, (
            "un 400 del servidor no es 'sin conexión': si se encolara, el "
            "problema quedaba escondido hasta el día siguiente"
        )
        assert "encolar(endpoint, data, etiqueta)" in texto

    def test_encolar_aplica_el_estado_en_el_navegador(self):
        """El negocio siguió andando: mientras no conteste el servidor, la
        pantalla tiene que mostrar la caja como quedó."""
        texto = _leer(COLA_CAJA)

        assert "caja.aplicarAperturaLocal(data)" in texto
        assert "caja.aplicarCierreLocal()" in texto

    def test_la_reconciliacion_mira_el_estado_que_va_evolucionando(self):
        """Si se mirara siempre el estado inicial, una cola con apertura y
        cierre saltaría el cierre ("la caja ya está cerrada") y la jornada
        quedaría abierta para siempre en el servidor."""
        texto = _leer(COLA_CAJA)
        cuerpo = texto[texto.index("async function subirOperacion("):]

        assert "if (yaHecha) return true" in cuerpo
        assert "estado.abierta = true" in cuerpo
        assert "estado.abierta = false" in cuerpo
        assert "estado.metodos_cerrados = [" in cuerpo

    def test_si_se_corta_la_red_los_que_siguen_no_suben(self):
        texto = _leer(COLA_CAJA)
        cuerpo = texto[texto.index("async function subirOperacion("):]

        assert "if (esErrorDeRed(e)) throw e" in cuerpo


class TestUnSoloPuntoDeSubida:
    def test_las_dos_colas_se_mezclan_por_orden_de_ocurrencia(self):
        texto = _leer(SYNC)

        assert "tipo: 'venta'" in texto
        assert "tipo: 'caja'" in texto
        assert ".sort(" in texto, "sin orden, la venta subía sin caja abierta o el cierre sin la venta"
        assert "cuando: s.createdAt" in texto and "cuando: op.createdAt" in texto

    def test_el_estado_de_la_caja_se_pide_solo_si_hay_que_subir_caja(self):
        texto = _leer(SYNC)

        assert "if (eventos.some((e) => e.tipo === 'caja'))" in texto
        assert "eventos.length === 0) return { subidas: 0, fallidas: 0, errores: [] }" in texto

    def test_un_corte_de_red_detiene_todo_la_subida(self):
        texto = _leer(SYNC)
        cuerpo = texto[texto.index("async function sincronizarPendientes("):]

        assert "if (cortada) break" in cuerpo
        assert "if (esErrorDeRed(e)) {" in cuerpo
        assert "cortada = true" in cuerpo
        assert "return { subidas: 0, fallidas: 0, errores: [] }" in cuerpo, (
            "si ni siquiera se pudo preguntar el estado de la caja, no se sube "
            "nada: nunca se sube 'a ver qué pasa'"
        )

    def test_al_terminar_refresca_la_caja_que_se_acaba_de_subir(self):
        texto = _leer(SYNC)

        assert "await useCajaStore().fetchEstado()" in texto

    def test_se_escucha_la_reconexion(self):
        texto = _leer(SYNC)

        assert "window.addEventListener('online'" in texto

    def test_no_quedo_una_segunda_forma_de_sincronizar(self):
        """Si quedaran dos puntos de subida, uno de ellos no iba a respetar el
        orden y en algún caso subía mal."""
        assert "syncPendingSales" not in _leer(COLA_VENTAS)
        for nombre, path in VISTAS.items():
            texto = _leer(path)
            assert "syncPendingSales" not in texto, f"{nombre} sigue usando la subida vieja"


class TestLasVistasUsanElMismoCamino:
    def test_todas_abren_caja_por_la_cola(self):
        for nombre, path in VISTAS.items():
            texto = _leer(path)
            assert not re.search(r"api\.post\(\s*'/api/caja/apertura'", texto), (
                f"{nombre} sigue abriendo caja directo: sin conexión se pierde"
            )
            assert re.search(r"postearCaja\(\s*'/api/caja/apertura'", texto), (
                f"{nombre} no abre caja por la cola"
            )

    def test_el_cierre_de_la_jornada_pasa_por_la_cola(self):
        texto = _leer(VISTAS["CajaView"])
        assert re.search(r"postearCaja\(\s*'/api/caja/cierre-metodo'", texto)
        assert re.search(r"postearCaja\(\s*'/api/caja/cierre-total'", texto)
        assert "api.post('/api/caja/cierre-" not in texto

        movil = _leer(VISTAS["CobroMovilView"])
        assert re.search(r"postearCaja\(\s*'/api/caja/cierre-total'", movil)
        assert "api.post('/api/caja/cierre-total'" not in movil

    def test_cobro_movil_y_pos_suben_lo_pendiente_al_abrir(self):
        for nombre in ("POSView", "CobroMovilView"):
            texto = _leer(VISTAS[nombre])
            assert "sincronizarPendientes()" in texto, f"{nombre} no sube lo que quedó sin red"

    def test_caja_view_sube_antes_de_pedir_el_historial(self):
        """Si no, la pantalla mostraría el historial sin las aperturas y
        cierres que estaban encolados."""
        texto = _leer(VISTAS["CajaView"])
        inicio = texto.index("onMounted(async () => {")
        bloque = texto[inicio:inicio + 400]

        assert "await sincronizarPendientes()" in bloque
        assert bloque.index("sincronizarPendientes()") < bloque.index("fetchMovimientos()")


class TestElAviso:
    def test_el_indicador_tambien_muestra_lo_de_caja(self):
        texto = _leer(INDICADOR)

        assert "pendingCajaCount" in texto
        assert "movimiento(s) de caja sin subir" in texto
        assert "apex-pending-caja-updated" in texto

    def test_el_aviso_se_muestra_aunque_no_haya_ventas(self):
        texto = _leer(INDICADOR)

        assert "pendingSalesCount > 0 || pendingCajaCount > 0" in texto


class TestRefrescarSinInternetDeciaCajaCerrada:
    """Prueba 2 del dueño (19/10/2026): con la caja abierta y sin internet,
    refrescar la página mostraba "CAJA CERRADA".

    Causa: el service worker tenía cacheado el estado de la caja. Sin red
    devolvía la última respuesta —la de antes de abrir—, `fetchEstado` la tomaba
    como verdad, la pisaba por encima del estado local (que sí sabía que la caja
    se abrió sin conexión) y la volvía a guardar. La pantalla salía cerrada y
    además quedaba anotada así para la próxima.
    """

    def test_el_service_worker_no_cachea_el_estado_de_la_caja(self):
        sw = _leer(SW)
        inicio = sw.index("CACHEABLE_API_PATTERNS")
        lista = sw[inicio:sw.index("]", inicio)]

        assert "/api/caja/estado" not in lista, (
            "sin red el SW le devuelve al store un estado viejo y lo pisa: "
            "con la caja abierta la pantalla decia 'CAJA CERRADA'"
        )

    def test_el_estado_local_sigue_siendo_el_que_manda(self):
        texto = _leer(STORE_CAJA)

        # Sin red el pedido tiene que fallar (no devolver una respuesta vieja),
        # para que el store guarde lo que sabe y pause el refresco.
        assert "if (esErrorDeRed(e)) sinRed.value = true" in texto
        assert "apex-caja-estado" in texto


class TestCerrarLaCajaDesdeElCelular:
    """Prueba 2 del dueño (19/10/2026): "desde el celular me permite cerrar y
    abrir caja casi sin confirmar nada" — era un confirm() de un toque, sin
    ningún dato, en un chip del header que se toca por error."""

    def test_cerrar_pide_confirmar_con_los_numeros_a_la_vista(self):
        texto = _leer(VISTAS["CobroMovilView"])

        assert "confirm('¿Querés cerrar la caja ahora?')" not in texto
        assert "showCierre" in texto
        assert "Sí, cerrar la caja" in texto
        assert "{{ fc(cajaStore.saldo_actual) }}" in texto, (
            "cerrar sin mostrar cuánta plata hay es cerrar a ciegas"
        )
        assert "cajaStore.desdeTexto" in texto, (
            "hacía falta ver desde cuándo estaba abierta: la caja de otro día "
            "se veía igual que la de hoy"
        )

    def test_abrir_sigue_pidiendo_el_monto_inicial(self):
        texto = _leer(VISTAS["CobroMovilView"])

        assert "confirm('¿Querés abrir la caja?')" not in texto
        assert 'title="Abrir caja"' in texto
        assert 'label="Monto inicial"' in texto


class TestLaCajaQueSeVeEsLaDeHoy:
    """Prueba 2 del dueño (20/10/2026): "en la PC tenía la caja abierta,
    entré sin internet y me salía la cerrada".

    Tres cosas podían dejar la pantalla diciendo "CAJA CERRADA" con la caja
    abierta: la caché del service worker (arreglada el 19/10), una apertura
    con red que no llegaba a guardarse porque **el pedido que seguía** no
    salía, y una caja dejada abierta de otro día — que se cierra sola con el
    cambio de fecha y ahora lo dice en pantalla en vez de cambiar sola."""

    def test_abrir_con_red_tambien_lo_deja_anotado_en_el_navegador(self):
        texto = _leer(COLA_CAJA)
        cuerpo = texto[texto.index("async function postear("):]

        assert "aplicarLocal(endpoint, data)" in cuerpo, (
            "con red la apertura solo quedaba guardada si salia el fetchEstado "
            "que seguia: si ese fallaba, la pantalla seguia abierta y al "
            "refrescar salia 'CAJA CERRADA'"
        )
        # Los tres usos son: la declaracion, el camino sin red (encolar) y el
        # camino con red (postear). Un cuarto significaria dos aplicaciones.
        assert texto.count("aplicarLocal(endpoint, data)") == 3

    def test_el_store_deja_constancia_de_la_caja_de_otro_dia(self):
        texto = _leer(STORE_CAJA)

        assert "cerroDeOtroDia" in texto, (
            "que la caja de otro dia no se restaure esta bien, pero en silencio "
            "se lea como un bug"
        )
        assert "desdeTexto" in texto

    def test_el_pos_avisa_por_que_esta_cerrada(self):
        texto = _leer(VISTAS["POSView"])

        assert "chipCaja" in texto
        assert "la de otro día" in texto
        assert "CAJA ABIERTA · desde " in texto
