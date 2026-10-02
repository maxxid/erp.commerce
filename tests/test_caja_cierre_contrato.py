"""Smoke test del contrato del cierre de caja.

Sin tests de frontend, tres cosas se rompen sin que nadie se entere:

  1. Que las cuentas digitales vuelvan a precargarse con el saldo del cierre
     anterior. Se ve bien, funciona, y abre la caja con plata que nadie vio.
     El campo se ve bien y el arqueo del día nace con una diferencia fantasma.
  2. Que el botón de conteo de una cuenta digital vuelva a abrir el contador de
     billetes: el componente compila igual, solo cambia el emit.
  3. Que la extracción en modo "dejo" mande el monto dejado en vez del extraído.
     El backend valida cualquier número positivo, así que el error se descubre
     cuando el fondo de la caja no cuadra, un día después.

Este archivo toma las URLs y los emits que el front arma de verdad y los cruza
con lo que el backend expone. No reemplaza los tests de cada endpoint.
"""

import re
from pathlib import Path

import pytest

RAIZ_FRONTS = Path(__file__).resolve().parent.parent / "frontend" / "src"

CAJA_VIEW = RAIZ_FRONTS / "views" / "CajaView.vue"
POS_VIEW = RAIZ_FRONTS / "views" / "POSView.vue"
ARQUEO = RAIZ_FRONTS / "components" / "caja" / "ArqueoMedios.vue"
CONTADOR_TRANSFERENCIAS = RAIZ_FRONTS / "components" / "caja" / "ContadorTransferenciasModal.vue"
ROUTER_CAJA = Path(__file__).resolve().parent.parent / "app" / "routers" / "caja.py"

ROTOS_MOJIBAKE = ("Ã", "Â", "â€", "�")


def _texto(path):
    return path.read_text(encoding="utf-8")


def test_archivos_de_caja_existen():
    for path in (CAJA_VIEW, POS_VIEW, ARQUEO, CONTADOR_TRANSFERENCIAS, ROUTER_CAJA):
        assert path.exists(), f"falta {path}"


@pytest.mark.parametrize("path", [CAJA_VIEW, POS_VIEW, ARQUEO, CONTADOR_TRANSFERENCIAS])
def test_archivos_de_caja_sin_mojibake(path):
    """El cierre de caja se edita a mano y una doble codificación se cuela sin
    romper el build: solo queda la palabra corrupta en pantalla."""
    for numero, linea in enumerate(_texto(path).splitlines(), 1):
        for roto in ROTOS_MOJIBAKE:
            assert roto not in linea, f"{path.name}:{numero} mojibake {roto!r}"


# --- Cuentas digitales: abren en 0, el saldo de ayer es solo referencia ---


@pytest.mark.parametrize("vista,funcion", [("caja", CAJA_VIEW), ("pos", POS_VIEW)])
def test_cuentas_digitales_no_se_precargan(vista, funcion):
    """El saldo del último cierre se puede leer, pero nunca escribirse en el
    formulario: si se asigna al valor del input, la caja abre con un saldo
    inventado."""
    texto = _texto(funcion)
    cuerpo = re.search(
        r"async function cargarSaldosCuentasSugeridos\w*\(\)\s*\{(.*?)\n\}",
        texto,
        re.S,
    )
    assert cuerpo, f"{vista}: no se encontro cargarSaldosCuentasSugeridos"
    bloque = cuerpo.group(1)

    precarga = re.findall(r"saldos\[(\w+)\]\s*=\s*Number\(sugeridos", bloque)
    assert not precarga, (
        f"{vista}: las cuentas se siguen precargando con el saldo del cierre "
        f"anterior ({precarga}); deben quedar en 0"
    )

    # El 0 por defecto tiene que estar explícito, no implícito.
    assert re.search(r"MEDIOS_CUENTA\.forEach\(m\s*=>\s*\{\s*saldos\[m\]\s*=\s*0\s*\}\)", bloque), (
        f"{vista}: las cuentas no arrancan en 0"
    )


@pytest.mark.parametrize("vista,funcion", [("caja", CAJA_VIEW), ("pos", POS_VIEW)])
def test_saldo_anterior_solo_como_referencia(vista, funcion):
    """Si el saldo de ayer se guarda, tiene que haber una forma de cargarlo a
    mano. Y si no se guarda, el endpoint no se puede llamar: sobra traffic."""
    texto = _texto(funcion)
    guarda = "saldosUltimosCuentas" in texto
    if guarda:
        assert "ayer" in texto, f"{vista}: se guarda el saldo anterior pero no se muestra"
    else:
        assert "saldos-cuentas" not in texto, (
            f"{vista}: se consulta el saldo del cierre anterior y se descarta"
        )


# --- Conteo de medios: efectivo por denominación, cuentas por transferencia ---


def test_arqueo_emite_ambos_contadores():
    texto = _texto(ARQUEO)
    emits = re.search(r"defineEmits\(\[([^\]]*)\]", texto)
    assert emits, "ArqueoMedios no declara defineEmits"
    declarados = set(re.findall(r"'([^']+)'", emits.group(1)))
    for evento in ("contar", "contar-medio"):
        assert evento in declarados, f"ArqueoMedios no emite {evento}"


def test_contador_de_billetes_es_solo_para_efectivo():
    """El botón de billetes tiene que quedar restringido al efectivo, y las
    cuentas tienen que ir al contador por monto."""
    texto = _texto(ARQUEO)
    assert re.search(
        r'v-if="metodo\.valor === \'efectivo\'"[\s\S]{0,400}?\$emit\(\'contar\', metodo\)', texto
    ), "el conteo por billetes ya no es exclusivo del efectivo"
    assert re.search(r'v-else[\s\S]{0,400}?\$emit\(\'contar-medio\', metodo\)', texto), (
        "las cuentas digitales no tienen contador por monto"
    )


def test_contador_de_transferencias_usa_enter_para_avanzar():
    """El operador tipea un monto y da Enter: si no avanza solo, hay que ir a
    buscar el mouse por cada fila."""
    texto = _texto(CONTADOR_TRANSFERENCIAS)
    assert "Enter" in texto, "el contador de transferencias no maneja Enter"
    assert re.search(r"@keydown(\.enter|\.enter\.[a-z]+)?", texto), "no hay binding de Enter"


def test_contador_de_transferencias_compara_con_el_esperado():
    """El motivo del contador es ver si la cuenta cuadra: sin el esperado a la
    vista solo sirve para cargar un número."""
    texto = _texto(CONTADOR_TRANSFERENCIAS)
    assert "valorEsperado" in texto, "el contador no recibe el esperado de la cuenta"
    assert "sobrante" in texto, "el contador no calcula la diferencia con el esperado"
    # Y la diferencia tiene que verse, no solo calcularse.
    assert re.search(r"v-if=\"sobrante != 0\"", texto), "la diferencia no se avisa en pantalla"


# --- Modo "dejo": se manda lo que sale, no lo que queda ---


def test_extraccion_manda_el_monto_extraido():
    """El backend registra un egreso por el monto que le manden. Si en modo
    "dejo" se mandara el monto dejado, se descontaría al revés la plata que
    quedó en el cajón."""
    texto = _texto(ARQUEO)
    emissions = re.search(r"function extraer\(\)\s*\{(.*?)\n\}", texto, re.S)
    assert emissions, "ArqueoMedios no tiene función extraer"
    bloque = emissions.group(1)
    assert re.search(r"monto:\s*porExtraer\.value", bloque), (
        "el evento de extracción no manda el monto calculado como extraído"
    )
    assert re.search(r"dejo:\s*montoDejoIngresado\.value", bloque), (
        "el evento de extracción no informa cuánto quedó en el cajón"
    )


def test_extraccion_nunca_supera_el_efectivo_esperado():
    """No se puede sacar más plata de la que hay: con el cálculo sin tope, un
    valor tipeado de más genera un egreso que descuadra el día entero."""
    texto = _texto(ARQUEO)
    por_extraer = re.search(r"const porExtraer = computed\(.*?\n\}\)", texto, re.S)
    assert por_extraer, "ArqueoMedios no calcula porExtraer"
    bloque = por_extraer.group(0)
    # Con el modo "dejo" el tope va sobre lo que se deja, y la resta da lo que
    # sale; con el modo normal, el tope va sobre el monto tipeado.
    assert bloque.count("esperadoEfectivo.value") >= 2, (
        "la extracción no se limita al efectivo esperado"
    )
    assert "Math.max" in bloque and "Math.min" in bloque, (
        "la extracción no acota el monto en ambos sentidos"
    )


def test_extraccion_se_deshabilita_sin_monto():
    texto = _texto(ARQUEO)
    puede = re.search(r"const puedeExtraer = computed\(\(\)\s*=>\s*(.*?)\)\n", texto)
    assert puede, "ArqueoMedios no deshabilita el botón de extracción"
    assert "porExtraer.value <= 0" in puede.group(1), (
        "se puede registrar una extracción de 0"
    )


def test_cambiar_de_modo_convierte_el_monto():
    """El mismo número significa dos cosas según el modo. Si al volver a
    "cuánto saco" queda el valor tipeado, el que escribió 50000 para dejar el
    fondo del día siguiente termina extrayendo 50000 y nadie se entera hasta
    que la caja del día siguiente no cuadra."""
    texto = _texto(ARQUEO)
    desactivar = re.search(r"function desactivarPorDejo\(\)\s*\{(.*?)\n\}", texto, re.S)
    assert desactivar, "volver al modo 'cuánto saco' no está manejado"
    bloque = desactivar.group(1)
    assert "porDejo.value = false" in bloque
    assert re.search(r"montoRetiro\.value\s*=\s*round2\(porExtraer\.value\)", bloque), (
        "al cambiar de modo el monto no se convierte: queda el valor del modo anterior"
    )
    # Y el botón tiene que llamar a esa función, no poner el flag a mano.
    assert re.search(r'@click="desactivarPorDejo"', texto), (
        "el toggle sigue poniendo el flag a mano sin convertir el monto"
    )


def test_guardar_devuelve_el_form_al_modo_seguro():
    """En modo "dejo" con el campo en 0, "Me llevo" muestra todo el efectivo del
    cajón. Si el form quedara así después de guardar, el operador que tipea el
    siguiente movimiento sin mirar la etiqueta extrae el monto entero. Después de
    cada alta el modo tiene que volver a "cuánto saco"."""
    texto = _texto(ARQUEO)
    watcher = re.search(r"watch\(\(\)\s*=>\s*props\.retiros\.length.*?\n\}\)", texto, re.S)
    assert watcher, "no se limpia el form después de registrar un egreso"
    bloque = watcher.group(0)
    assert "porDejo.value = false" in bloque, (
        "el form queda en modo 'dejo' después de guardar"
    )
    assert "montoRetiro.value = 0" in bloque, "el monto queda del egreso anterior"
    # Y el pago se limpia solo si lo que se agregó fue un pago.
    assert "esPagoProveedor(props.retiros[0])" in bloque, (
        "el form de pago se limpia siempre, aunque lo agregado haya sido una extracción"
    )


# --- Pago a proveedor: la lista y los dos endpoints ---


def test_arqueo_pide_proveedores():
    texto = _texto(ARQUEO)
    assert "proveedores:" in re.search(r"defineProps\(\{(.*?)\n\}\)", texto, re.S).group(1), (
        "ArqueoMedios no recibe la lista de proveedores"
    )
    assert "pago-proveedor" in re.search(r"defineEmits\(\[([^\]]*)\]", texto).group(1), (
        "ArqueoMedios no emite el pago a proveedor"
    )


def test_caja_view_usa_los_dos_endpoints():
    """La lista de egresos mezcla extracción y pago a proveedor. Si el borrado
    va siempre al endpoint de extracción, anular un pago deja el movimiento
    puesto y el arqueo sigue descuadrado."""
    texto = _texto(CAJA_VIEW)
    assert "/api/caja/pago-proveedor" in texto, "no se registran pagos a proveedor"
    assert "pago-proveedor" in texto and "retiro-cierre" in texto, (
        "el borrado no distingue pago de proveedor de extracción"
    )
    assert re.search(r"pago-proveedor'\s*:\s*'retiro-cierre'", texto), (
        "el borrado no rutea por tipo de movimiento"
    )


def test_pagos_con_mas_de_un_sesion_requieren_cierre_id():
    """El pago a un proveedor es un egreso de caja, pero se anota contra la
    sesión que se está cerrando. Sin mandarle el id de sesión, el pago queda
    colgando de la sesión abierta y el cierre de mañana lo cuenta dos veces."""
    texto = _texto(CAJA_VIEW)
    llamada = re.search(r"async function registrarPagoProveedor\(.*?\n\}", texto, re.S)
    assert llamada, "CajaView no tiene registrarPagoProveedor"
    assert "cierre_id" in llamada.group(0), "el pago no manda el id de sesión"


def test_cargar_proveedores_usa_parametros_planos():
    """api.get no acepta { params: {...} }: se mandaría ?params[page_size]=... y
    el backend vería la lista vacía sin avisar."""
    texto = _texto(CAJA_VIEW)
    llamada = re.search(r"async function cargarProveedores\(\).*?\n\}", texto, re.S)
    assert llamada, "CajaView no carga los proveedores"
    assert "params:" not in llamada.group(0), "los proveedores se piden con params anidado"
    assert re.search(r"api\.get\([^,]+,\s*\{[^}]*\}", llamada.group(0)), (
        "no se mandan los parámetros de la lista"
    )


def test_proveedores_se_cargan_al_abrir_el_cierre():
    """La lista se pide cuando se abre el cierre, no siempre: son cientos de
    filas y no hacen falta para nada más."""
    texto = _texto(CAJA_VIEW)
    apertura = re.search(r"async function initCierreCaja\(\).*?\n\}", texto, re.S)
    assert apertura, "no se encuentra la función que abre el cierre"
    assert "cargarProveedores()" in apertura.group(0), (
        "la lista de proveedores se pide en otro momento o nunca"
    )


def test_contador_de_transferencias_integrado():
    texto = _texto(CAJA_VIEW)
    assert "ContadorTransferenciasModal" in texto, "el modal de transferencias no está en CajaView"
    assert "contar-medio" in texto, "CajaView no escucha el conteo de cuentas digitales"
    assert re.search(r"import ContadorTransferenciasModal", texto), "el modal no está importado"
