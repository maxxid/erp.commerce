import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

// Campana del header. Los avisos no se inventan acá: los genera el backend
// desde el estado real del sistema (stock bajo, caja abierta, lotes, licencia)
// y los guarda una vez por día. Acá sólo se piden, se marcan como leídos y se
// lleva la cuenta de los que faltan ver.
export const useNotificacionesStore = defineStore('notificaciones', () => {
  const avisos = ref([])
  const noLeidas = ref(0)
  const modoLectura = ref('usuario')
  const cargando = ref(false)
  const panelAbierto = ref(false)

  async function fetch() {
    cargando.value = true
    try {
      const resp = await api.get('/api/notificaciones')
      if (resp) {
        avisos.value = Array.isArray(resp.avisos) ? resp.avisos : []
        noLeidas.value = resp.no_leidas || 0
        modoLectura.value = resp.modo_lectura || 'usuario'
      }
    } catch { /* sin red no hay campana: se reintenta en la próxima carga */ }
    cargando.value = false
  }

  async function marcarLeida(id) {
    const aviso = avisos.value.find(a => a.id === id)
    if (!aviso || aviso.leida) return
    aviso.leida = true
    noLeidas.value = Math.max(0, noLeidas.value - 1)
    try {
      await api.post(`/api/notificaciones/${id}/leer`)
    } catch {
      // Si no se guardó, el próximo fetch vuelve a contarla.
      aviso.leida = false
      noLeidas.value += 1
    }
  }

  async function marcarTodas() {
    const pendientes = avisos.value.filter(a => !a.leida).length
    avisos.value.forEach(a => { a.leida = true })
    noLeidas.value = 0
    try {
      await api.post('/api/notificaciones/leer-todas')
    } catch {
      await fetch()
    }
    return pendientes
  }

  return { avisos, noLeidas, modoLectura, cargando, panelAbierto, fetch, marcarLeida, marcarTodas }
})
