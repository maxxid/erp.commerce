import { ref } from 'vue'
import api from '@/services/api'

const OFFLINE_SALES_KEY = 'apex-offline-sales'
const pendingSales = ref([])

export function useOfflineSales() {
  function loadPendingSales() {
    try {
      const stored = localStorage.getItem(OFFLINE_SALES_KEY)
      pendingSales.value = stored ? JSON.parse(stored) : []
    } catch {
      pendingSales.value = []
    }
  }

  function savePendingSales() {
    localStorage.setItem(OFFLINE_SALES_KEY, JSON.stringify(pendingSales.value))
  }

  function addPendingSale(saleData) {
    pendingSales.value.push({
      id: Date.now(),
      data: saleData,
      createdAt: new Date().toISOString(),
      synced: false,
    })
    savePendingSales()
  }

  async function syncPendingSales() {
    if (!navigator.onLine) return { synced: 0, failed: 0 }

    loadPendingSales()
    const toSync = pendingSales.value.filter((s) => !s.synced)
    if (toSync.length === 0) return { synced: 0, failed: 0 }

    let synced = 0
    let failed = 0

    for (const sale of toSync) {
      try {
        await api.post('/api/ventas', sale.data)
        sale.synced = true
        synced++
      } catch {
        failed++
      }
    }

    pendingSales.value = pendingSales.value.filter((s) => !s.synced)
    savePendingSales()

    return { synced, failed }
  }

  function removePendingSale(id) {
    pendingSales.value = pendingPendingSales().filter((s) => s.id !== id)
    savePendingSales()
  }

  function getPendingCount() {
    return pendingSales.value.filter((s) => !s.synced).length
  }

  if (typeof window !== 'undefined') {
    loadPendingSales()
    window.addEventListener('online', () => syncPendingSales())
  }

  return {
    pendingSales,
    addPendingSale,
    syncPendingSales,
    removePendingSale,
    getPendingCount,
    loadPendingSales,
  }
}
