import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useCajaStore = defineStore('caja', () => {
  const abierta = ref(false)
  const saldo_actual = ref(0)
  const metodos_cerrados = ref([])

  async function fetchEstado() {
    try {
      const state = await api.get('/api/caja/estado')
      if (state) {
        abierta.value = state.abierta || false
        saldo_actual.value = state.saldo_actual || 0
        metodos_cerrados.value = state.metodos_cerrados || []
      }
    } catch { /* fallback */ }
  }

  return { abierta, saldo_actual, metodos_cerrados, fetchEstado }
})
