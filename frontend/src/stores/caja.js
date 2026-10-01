import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'
import { useCarritoStore } from '@/stores/carrito'

export const useCajaStore = defineStore('caja', () => {
  const abierta = ref(false)
  const saldo_actual = ref(0)
  const saldos_cuentas = ref({})
  const saldo_cuenta_total = ref(0)
  const saldo_total = ref(0)
  const metodos_cerrados = ref([])
  const ultimoCierre = ref(null)
  const sesion_id = ref(null)
  const sesion_inicio = ref(null)

  async function fetchEstado() {
    try {
      const state = await api.get('/api/caja/estado')
      if (state) {
        abierta.value = state.abierta || false
        // saldo_actual = solo el cajón; las cuentas digitales van aparte para
        // que el efectivo y el saldo de la app se cuadren por separado.
        saldo_actual.value = state.saldo_efectivo ?? state.saldo_actual ?? 0
        saldos_cuentas.value = state.saldos_cuentas || {}
        saldo_cuenta_total.value = state.saldo_cuenta_total || 0
        saldo_total.value = state.saldo_total ?? (saldo_actual.value + saldo_cuenta_total.value)
        metodos_cerrados.value = state.metodos_cerrados || []
        sesion_id.value = state.sesion_id ?? null
        sesion_inicio.value = state.sesion_inicio ?? null
        // Los carritos abiertos son de esta sesion: si la caja arranco de nuevo,
        // su reloj arranca de cero tambien.
        useCarritoStore().sincronizarSesion(state.sesion_id, state.sesion_inicio)
      }
    } catch { /* fallback */ }
  }

  async function fetchUltimoCierre() {
    try {
      const resp = await api.get('/api/caja/ultimo-cierre')
      if (resp) {
        ultimoCierre.value = resp
      }
    } catch { /* fallback */ }
  }

  return { abierta, saldo_actual, saldos_cuentas, saldo_cuenta_total, saldo_total, metodos_cerrados, ultimoCierre, sesion_id, sesion_inicio, fetchEstado, fetchUltimoCierre }
})
