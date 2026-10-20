"""Prueba 3 del dueño (20/10/2026): tres bugs del tab POS.

1. **El botón "Abrir caja" del POS no hacía nada y no tiraba error.**
   `POSView.vue` usaba `<AperturaCajaModal>` **sin importarlo** y el proyecto no
   tiene auto-import de componentes, así que Vue lo trataba como una etiqueta
   HTML desconocida: no se renderizaba ningún modal, el click quedaba sin
   destino y lo único que aparecía era un warning en la consola del navegador.
   El tab Caja sí lo importaba, por eso ahí funcionaba.

2. **"Últimas Transacciones" quedaba vacía al recargar la página.** El panel
   pedía `/api/ventas?estado=completada` y `Venta.estado` solo acepta
   `pendiente | confirmada | anulada`: el filtro no devolvía ninguna fila.
   Lo único que se veía era lo que el propio POS agregaba a mano en memoria
   después de cobrar.

3. **Los medios de pago no se adaptaban**: el grid venía con `grid-cols-7`
   fijo y, al deshabilitar la mayoría en Ajustes, los que quedaban se achicaban
   y sobraba la fila entera.
"""

import pathlib
import re

RAIZ = pathlib.Path(__file__).resolve().parents[1]
SRC = RAIZ / "frontend" / "src"
POS = SRC / "views" / "POSView.vue"
MODELO_VENTA = RAIZ / "app" / "models" / "venta.py"

# Los que trae Vue y no hace falta importar.
VUE_BUILTIN = {"Transition", "TransitionGroup", "Teleport", "KeepAlive", "Suspense"}


def _leer(ruta: pathlib.Path) -> str:
    return ruta.read_text(encoding="utf-8")


def test_el_modal_de_apertura_del_pos_esta_importado():
    texto = _leer(POS)

    assert "import AperturaCajaModal" in texto, (
        "sin el import Vue no arma el modal: el botón 'Abrir caja' del POS "
        "quedaba apretando sobre una etiqueta desconocida y no pasaba nada"
    )


def test_los_componentes_del_template_estan_importados():
    """Todos los `<Mayus>` del archivo tienen que estar importados en el mismo.

    Cualquier olvido se comporta igual que el bug 1: no se ve nada, no tira
    error en pantalla, sólo un warning en la consola.
    """
    sin_importar = []

    for archivo in sorted(SRC.rglob("*.vue")):
        texto = _leer(archivo)
        if "<script" not in texto:
            continue
        for componente in sorted(set(re.findall(r"<([A-Z][A-Za-z0-9_]*)", texto))):
            if componente in VUE_BUILTIN:
                continue
            if f"import {componente}" in texto:
                continue
            if re.search(rf"\bas\s+{componente}\b", texto):
                continue
            if re.search(rf"\b{componente}\s*=", texto):
                continue
            sin_importar.append(f"{archivo.relative_to(SRC)}: <{componente}>")

    assert not sin_importar, (
        "componente usado en el template y nunca declarado (no se ve en la "
        "pantalla, sólo en la consola): " + ", ".join(sin_importar)
    )


def test_ultimas_transacciones_pide_los_estados_que_existen():
    texto = _leer(POS)
    modelo = _leer(MODELO_VENTA)

    linea_estado = next(
        l for l in modelo.splitlines() if l.strip().startswith("estado = Column")
    )
    estados_validos = {e.strip() for e in linea_estado.split("#", 1)[1].split("|")}

    pedidos = []
    for url in re.findall(r"/api/ventas\?[^'\"]*", texto):
        m = re.search(r"estado=([a-z_]+)", url)
        if m:
            pedidos.append(m.group(1))

    assert pedidos, "el panel de últimas transacciones dejó de pedir por estado"
    assert "estado=completada" not in texto, (
        "no existe `Venta.estado = completada`: el filtro no devolvía nada y "
        "el panel quedaba en 'Sin transacciones hoy' después de cada recarga"
    )
    for estado in pedidos:
        assert estado in estados_validos, (
            f"el POS pide estado={estado} y la venta solo conoce "
            f"{sorted(estados_validos)}"
        )


def test_el_grid_de_medios_de_pago_se_adapta_a_cuantos_hay():
    texto = _leer(POS)

    assert "columnasMediosPago" in texto, (
        "con las columnas fijas en 7, al deshabilitar la mayoría los medios "
        "que quedaban se achicaban y sobraba la fila entera"
    )
    assert 'class="grid grid-cols-3 sm:grid-cols-7' not in texto
    assert "Atajos: 1-{{ mediosPago.length }}" in texto, (
        "el atajo seguía anunciando 1-7 aunque hubiera 3 medios"
    )
    assert "idxAtajo < pagos.length" in texto, (
        "con menos de 7 habilitados, la tecla que sobraba dejaba "
        "`medio_pago` en undefined"
    )
