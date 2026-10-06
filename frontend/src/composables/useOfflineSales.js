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
        const venta = await api.post('/api/ventas', {
          cliente_id: sale.data.cliente_id || null,
          sucursal_id: sale.data.sucursal_id || 1,
          notas: sale.data.notas || null,
        })
        if (!venta || !venta.id) throw new Error('No se pudo crear la venta')

        const ventaId = venta.id

        for (const item of sale.data.items || []) {
          await api.post(`/api/ventas/${ventaId}/items`, {
            producto_id: item.producto_id,
            cantidad: item.cantidad,
            precio_unitario: item.precio_unitario,
            oferta_tipo: item.oferta_tipo || null,
            oferta_valor: item.oferta_valor || null,
            oferta_info: item.oferta_info || null,
            por_kilo: item.por_kilo || false,
            peso: item.peso || null,
          })
        }

        await api.put(`/api/ventas/${ventaId}/confirmar`, {
          medio_pago: sale.data.medio_pago || 'efectivo',
          efectivo_pagado: sale.data.efectivo_pagado || 0,
          descuento: sale.data.descuento || 0,
        })

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
    pendingSales.value = pendingSales.value.filter((s) => s.id !== id)
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
