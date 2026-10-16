import { esErrorDeRed } from '@/services/api'
import { useOfflineSales } from '@/composables/useOfflineSales'
import { useOfflineCaja } from '@/composables/useOfflineCaja'
import { useCajaStore } from '@/stores/caja'

let subiendo = false
let listenerRegistrado = false

function avisar() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new Event('apex-pending-sales-updated'))
  window.dispatchEvent(new Event('apex-pending-caja-updated'))
}

/**
 * El único punto desde el que se sube lo que quedó sin conexión.
 *
 * Las ventas y las operaciones de caja se mezclan y se suben **en el orden en
 * que ocurrieron**, no en dos tandas sueltas: la venta necesita la caja abierta
 * y el cierre necesita las ventas ya registradas. Subirlas por separado dejaba
 * o la venta sin caja, o el cierre sin la venta adentro.
 *
 * Si se corta la red a mitad se deja de subir todo — lo que sigue tampoco
 * podría entrar, y seguir intentando son pantallas de 30 segundos de espera.
 * Si el servidor rechaza una operación en particular (400), esa queda encolada
 * para mirarla y se sigue con la que viene.
 */
export function useOfflineSync() {
  async function sincronizarPendientes() {
    if (subiendo || typeof navigator === 'undefined' || !navigator.onLine) {
      return { subidas: 0, fallidas: 0 }
    }
    subiendo = true
    try {
      const ventas = useOfflineSales()
      const caja = useOfflineCaja()
      ventas.cargarUnaVez()
      caja.cargarCola()

      const eventos = [
        ...ventas.pendingSales.value
          .filter((s) => !s.synced)
          .map((s) => ({ cuando: s.createdAt, tipo: 'venta', id: s.id, venta: s })),
        ...caja.pendientes().map((op) => ({ cuando: op.createdAt, tipo: 'caja', id: op.id, op })),
      ].sort((a, b) => (a.cuando < b.cuando ? -1 : a.cuando > b.cuando ? 1 : 0))

      if (eventos.length === 0) return { subidas: 0, fallidas: 0 }

      // El estado real de la caja sólo se pide si hay operaciones de caja:
      // con ventas nomás no hace falta y salir a preguntar es un pedido más.
      let estado = null
      if (eventos.some((e) => e.tipo === 'caja')) {
        try {
          estado = await caja.traerEstado()
        } catch {
          // Sin eso no se puede saber qué aplicar dos veces: no se sube nada y
          // se reintenta en el próximo intento. Nunca se sube "a ver qué pasa".
          return { subidas: 0, fallidas: 0 }
        }
      }

      let subidas = 0
      let fallidas = 0
      let cortada = false
      let huboOperacionDeCaja = false

      for (const ev of eventos) {
        if (cortada) break
        if (ev.tipo === 'caja') {
          huboOperacionDeCaja = true
          try {
            const aplicada = await caja.subirOperacion(ev.op, estado)
            if (aplicada) {
              caja.marcarSubida(ev.id)
              subidas++
            } else {
              fallidas++
            }
          } catch (e) {
            fallidas++
            if (esErrorDeRed(e)) cortada = true
          }
        } else {
          try {
            await ventas.subirVenta(ev.venta)
            ventas.marcarSubida(ev.id)
            subidas++
          } catch (e) {
            fallidas++
            if (esErrorDeRed(e)) cortada = true
          }
        }
      }

      // Lo que se subió de la caja cambió el estado real: el navegador tiene
      // que dejar de mostrar lo que valía cuando estaba sin conexión.
      if (huboOperacionDeCaja) await useCajaStore().fetchEstado()

      return { subidas, fallidas }
    } finally {
      subiendo = false
      avisar()
    }
  }

  // Se registra al primer uso. OfflineIndicator está siempre montado en el
  // layout, así que las colas se suben solas al reconectar aunque nadie abra
  // el POS ni la pantalla de caja.
  if (typeof window !== 'undefined' && !listenerRegistrado) {
    listenerRegistrado = true
    window.addEventListener('online', () => { sincronizarPendientes() })
  }

  return { sincronizarPendientes }
}
