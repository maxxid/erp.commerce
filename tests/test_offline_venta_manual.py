"""Venta offline con un producto que no estaba en la base: no puede quedar en 422.

El reporte (26/10/2026): se cobró con internet, se cortó la red, el cajero siguió
vendiendo y al volver la conexión la venta quedó "sin subir". Al tocar
"Sincronizar ahora" no pasaba nada visible y la consola se llenaba de
`POST /api/ventas/859/items 422`.

**Causa**: los productos que no están en el catálogo (alta manual
`*Nombre*Precio` o traídos de una fuente externa) se agregan al carrito con un
id temporal `Date.now() + Math.random()`. Ese número tiene decimales y
`VentaItemAdd.producto_id: int` lo rechaza con 422. Como no es un error de red,
el sync lo contaba como fallido y lo reintentaba cada 60 s **sin mostrarlo**:
la venta no avanzaba nunca y el motivo no llegaba a nadie.

Lo que se arregló:

1. La cola guarda el producto completo (`producto_nuevo`) cuando el id es
   temporal, y el sync lo crea antes de mandar el ítem (reusando el existente
   si un intento anterior ya lo había creado).
2. El body se normaliza (números, `importe` > 0, peso/cantidad).
3. Un rechazo del servidor queda marcado con el motivo, se ve en el aviso y
   "Sincronizar ahora" lo muestra; el refresco automático deja de martillarlo.
4. Los 422 se leen: la lista de FastAPI se convierte en un mensaje con el campo.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.routers.ventas import VentaItemAdd

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "frontend" / "src"

COLA = SRC / "composables" / "useOfflineSales.js"
SYNC = SRC / "composables" / "useOfflineSync.js"
INDICADOR = SRC / "components" / "layout" / "OfflineIndicator.vue"
API_JS = SRC / "services" / "api.js"
POS = SRC / "views" / "POSView.vue"
COBRO = SRC / "views" / "CobroMovilView.vue"


def _leer(path):
    return path.read_text(encoding="utf-8")


class TestPorQueEra422:
    def test_un_id_temporal_no_pasa_la_validacion(self):
        """El id del producto manual es `Date.now() + Math.random()`: decimal.

        El test documenta el 422 real; si algún día el schema aceptara floats,
        esto dejaría de ser el motivo y habría que revisar el diagnóstico.
        """
        with pytest.raises(ValidationError) as exc:
            VentaItemAdd(producto_id=1761234567890.1234, cantidad=1, precio_unitario=100)

        assert "valid integer" in str(exc.value)

    def test_un_id_real_si_pasa(self):
        item = VentaItemAdd(producto_id=12, cantidad=1, precio_unitario=100)

        assert item.producto_id == 12


class TestLaColaGuardaElProducto:
    def test_el_pos_guarda_los_datos_del_producto_temporal(self):
        texto = _leer(POS)

        assert "producto_nuevo: esIdTemporal(item.producto_id) ? {" in texto
        assert "nombre: item.nombre || prod?.nombre || ''" in texto
        assert "codigo_barras: item.codigo_barras || prod?.codigo_barras || null" in texto
        assert "precio_venta:" in texto

    def test_cobro_movil_guarda_los_datos_del_producto_temporal(self):
        texto = _leer(COBRO)

        assert "producto_nuevo: esIdTemporal(item.producto_id) ? {" in texto
        assert "nombre: item.nombre || prod?.nombre || ''" in texto

    def test_las_dos_vistas_usan_la_misma_regla(self):
        """Si cada vista decide por su cuenta, una queda con el bug."""
        for path in (POS, COBRO):
            texto = _leer(path)
            assert "import { useOfflineSales, esIdTemporal }" in texto, (
                f"{path.name} no distingue un id temporal de uno real"
            )
            assert "esIdTemporal(item.producto_id)" in texto

    def test_el_carrito_persistido_tambien_se_puede_recuperar(self):
        """Tras un refresco el producto temporal ya no está en `products`: los
        datos tienen que salir del ítem, que sí quedó en el carrito."""
        for path in (POS, COBRO):
            texto = _leer(path)
            assert "prod?._nombre || item.nombre || prod?.nombre" in texto, (
                f"{path.name} depende de tener el producto en memoria"
            )


class TestElSyncCreaElProducto:
    def test_crea_el_producto_antes_del_item(self):
        texto = _leer(COLA)
        cuerpo = texto[texto.index("async function subirVenta("):]

        assert "await asegurarProducto(item)" in cuerpo
        assert cuerpo.index("asegurarProducto(item)") < cuerpo.index("/items`")

    def test_solo_lo_hace_con_ids_temporales(self):
        texto = _leer(COLA)
        cuerpo = texto[texto.index("async function asegurarProducto("):]

        assert "if (!esIdTemporal(item.producto_id)) return" in cuerpo
        assert "api.post('/api/productos/pos', datos)" in cuerpo

    def test_si_el_intento_anterior_ya_lo_creo_lo_reusa(self):
        """El sync es reanudable: sin esto, el reintento choca con "ya existe"
        y la venta se traba igual, ahora con 400."""
        texto = _leer(COLA)
        cuerpo = texto[texto.index("async function asegurarProducto("):]

        assert "e?.status === 400 || e?.status === 409" in cuerpo
        assert "/api/productos/lookup" in cuerpo
        assert "item.producto_id = existente.id" in cuerpo

    def test_el_payload_normaliza_los_tipos(self):
        texto = _leer(COLA)
        cuerpo = texto[texto.index("function itemParaElServidor("):]

        assert "cantidad = numero(item.cantidad)" in cuerpo
        assert "importe != null && importe > 0 ? importe : null" in cuerpo
        assert "peso: porKilo ? numero(item.peso) : null" in cuerpo

    def test_si_falta_el_nombre_lo_dice_en_vez_de_mandar_un_id_temporal(self):
        texto = _leer(COLA)

        assert "no se puede recrear en el servidor" in texto


class TestElRechazoSeVe:
    def test_el_sync_marca_la_venta_con_el_motivo(self):
        texto = _leer(SYNC)

        assert "ventas.marcarRechazada(ev.id, mensaje)" in texto
        assert "errores.push({ tipo: 'venta', mensaje })" in texto

    def test_el_refresco_automatico_no_reintenta_lo_rechazado(self):
        texto = _leer(SYNC)

        assert ".filter((s) => !s.synced && (forzar || !s.ultimoError))" in texto

    def test_el_boton_fuerza_el_reintento(self):
        texto = _leer(INDICADOR)

        assert "sincronizarPendientes({ forzar: true })" in texto
        assert "toast.error(" in texto

    def test_el_aviso_muestra_el_motivo(self):
        texto = _leer(INDICADOR)

        assert "errorSinSubir" in texto
        assert "ultimoError" in texto
        assert "El servidor rechazó una" in texto

    def test_la_cola_guarda_el_ultimo_error(self):
        texto = _leer(COLA)
        cuerpo = texto[texto.index("function marcarRechazada("):]

        assert "venta.ultimoError = mensaje" in cuerpo
        assert "savePendingSales()" in cuerpo

    def test_una_venta_irrecuperable_se_puede_descartar(self):
        """Una cola vieja no guardó el nombre del producto: sin una salida, el
        aviso quedaría para siempre."""
        texto = _leer(INDICADOR)

        assert "confirmandoDescarte" in texto
        assert "Sí, descartar" in texto
        assert "pedirDescarte" in texto
        assert "confirm('" not in texto, "el proyecto pide confirmación inline"
        assert "function descartar(id)" in _leer(COLA)


class TestLos422SeLeen:
    def test_el_detalle_de_fastapi_se_convierte_en_texto(self):
        texto = _leer(API_JS)

        assert "function detalleDeError(data, status)" in texto
        assert "Array.isArray(detalle)" in texto
        assert "campo ? `${campo}: ${d?.msg}` : d?.msg" in texto
        assert "new Error(detalleDeError(data, response.status))" in texto

    def test_no_queda_el_object_object(self):
        texto = _leer(API_JS)

        assert "new Error(data.detail || data.error" not in texto
