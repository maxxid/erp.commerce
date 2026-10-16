import { onMounted, onUnmounted } from 'vue'
import { useCajaStore } from '@/stores/caja'
import { useProductosStore } from '@/stores/productos'
import { useOfflineSync } from '@/composables/useOfflineSync'

// Cada cuánto se refresca la pantalla sin que nadie toque nada.
const TICK_MS = 60000
// El catálogo se pregunta cada 5 ticks (5 min). Cada pregunta son ~100 bytes,
// pero si cambió se baja el completo (0,41 MB): preguntarlo cada 60 s en un
// hotspot limitado no vale la pena. Además, si cambió, en 5 min alcanza para
// que la pantalla se entere — la que vende en este equipo ya lo descuenta sola.
const TICKS_CATALOGO = 5

/**
 * Refresco automático compartido por POS, CobroMóvil y Caja.
 *
 * Antes cada pantalla armaba su timer a mano y hacía una cosa distinta: Caja y
 * POS refrescaban el estado de la caja cada 60 s, y **CobroMóvil —la pantalla
 * que más mira el cajero— no refrescaba nada**, así que lo único que se
 * actualizaba era lo que se tocaba.
 *
 * En cada tick:
 *
 * 1. **Sube lo que quedó sin conexión.** Si no hay nada pendiente no hace ni
 *    un request, así que el 99 % de los ticks sale gratis. Es el respaldo del
 *    evento `online`, que algunos navegadores no disparan bien con el hotspot.
 * 2. **El estado de la caja** — es lo que decide si se puede cobrar.
 * 3. **¿Cambia el catálogo?** — pregunta la versión y solo baja si cambió.
 *
 * Con la red caída no se reintenta nada: cada intento son hasta 30 s de espera
 * contra un servidor que no contesta, repetidos cada 60 s. Se pausa sola y se
 * reanuda con el evento `online` (lo escucha `stores/caja.js`) o cuando alguien
 * pide el estado a mano.
 */
export function useRefrescoPeriodico() {
  const cajaStore = useCajaStore()
  const productosStore = useProductosStore()
  const { sincronizarPendientes } = useOfflineSync()

  // Un tick que todavía no terminó no arranca otro: si la red está colgada, un
  // tick puede tardar 30 s y sin esto se apilarían pedidos.
  let corriendo = false
  let ticks = 0
  let timer = null

  async function tick() {
    if (corriendo) return
    corriendo = true
    try {
      if (cajaStore.sinRed) return

      await sincronizarPendientes()
      await cajaStore.refrescarPeriodicamente()

      ticks++
      if (ticks >= TICKS_CATALOGO) {
        ticks = 0
        await productosStore.fetchAll()
      }
    } catch {
      // Nada de esto puede frenar la pantalla: si un paso falló, el siguiente
      // tick lo reintenta.
    } finally {
      corriendo = false
    }
  }

  onMounted(() => {
    if (!timer) timer = setInterval(tick, TICK_MS)
  })

  onUnmounted(() => {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  })
}
