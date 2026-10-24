"""El mini dashboard del POS arranca minimizado (dueño, 24/10/2026).

**El pedido**: "un cajero ni cuenta se daría del cambio, salvo que tenga el
mini dashboard del pos de ventas desplegado, podemos dejarlo por defecto
minimizado?" — el panel de la derecha tiene los KPIs del día (ventas, efectivo,
cajón) y las últimas transacciones. Si el servidor se cae o se pasa a otra
máquina, esa pantalla es la única que delata el cambio: números viejos o
vacíos en plena jornada.

Se cuida que el default esté cerrado en los cuatro lados (preferencias del
navegador, POS, Ajustes y el default del endpoint) y sobre todo que el default
de Ajustes **no** le pise la elección al cajero. Para eso hay que distinguir
"nunca lo toqué" de "lo abrí yo": las preferencias del navegador se guardan
enteras cada vez que se sincronizan los medios de pago, así que la simple
presencia del valor en el almacenamiento no alcanza — por eso existe
`showStatsPanelTocado`, que sólo se prende cuando el usuario lo cambia.
"""

import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POS = os.path.join(RAIZ, "frontend", "src", "views", "POSView.vue")
AJUSTES = os.path.join(RAIZ, "frontend", "src", "views", "AjustesView.vue")
PREFS = os.path.join(RAIZ, "frontend", "src", "stores", "posPreferences.js")
BACKEND = os.path.join(RAIZ, "app", "routers", "configuracion.py")


def _leer(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read()


def test_las_preferencias_del_navegador_arrancan_cerradas():
    src = _leer(PREFS)

    assert re.search(r"showStatsPanel:\s*false", src), "El default del navegador tendría que ser cerrado"
    assert re.search(r"showStatsPanelTocado:\s*false", src)
    # Sólo el usuario prende la marca de "lo toqué".
    tocar = re.search(r"function setShowStatsPanel\(value\) \{(?P<cuerpo>[^}]+)\}", src, re.S)
    assert tocar and "showStatsPanelTocado = true" in tocar.group("cuerpo")
    # El default de Ajustes se rinde ante esa marca.
    assert "if (typeof valor !== 'boolean' || prefs.value.showStatsPanelTocado) return" in src
    assert "aplicarDefaultPanel" in src


def test_el_pos_arranca_sin_panel_y_usa_el_default_de_ajustes():
    src = _leer(POS)

    assert re.search(r"const showStatsPanel = ref\(false\)", src), "El POS tendría que abrir con el panel cerrado"
    assert "posPrefs.aplicarDefaultPanel(posCfg.showStatsPanel)" in src
    # Tiene que aplicar el default ANTES de leerlo: si se lee primero, el
    # panel queda como estaba y el ajuste no hace nada.
    assert src.index("aplicarDefaultPanel") < src.index("posPrefs.prefs.showStatsPanel")
    # Y tiene que poder abrirse: no es un panel escondido para siempre.
    assert "Mostrar panel lateral" in src


def test_ajustes_y_el_endpoint_tambien_arrancan_cerrados():
    ajustes = _leer(AJUSTES)
    assert re.search(r"showStatsPanel:\s*false", ajustes)
    assert "data.showStatsPanel ?? false" in ajustes

    backend = _leer(BACKEND)
    assert '"showStatsPanel": False' in backend, "El default del endpoint tendría que venir cerrado"
