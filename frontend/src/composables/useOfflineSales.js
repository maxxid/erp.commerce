import { ref } from 'vue'
import api from '@/services/api'

const OFFLINE_SALES_KEY = 'apex-offline-sales'
const pendingSales = ref([])
let syncing = false
let onlineListenerRegistered = false

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

  function notificar() {
    window.dispatchEvent(new Event('apex-pending-sales-updated'))
  }

  function addPendingSale(saleData) {
    pendingSales.value.push({
      id: (typeof crypto !== 'undefined' && crypto.randomUUID)
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      data: saleData,
      createdAt: new Date().toISOString(),
      synced: false,
      // Reanudación: si el sync anterior creó la venta pero se cortó a mitad
      // de los items, no se vuelve a crear la venta al reintentar.
      ventaId: null,
      itemsEnviados: 0,
    })
    savePendingSales()
    notificar()
  }

  async function syncPendingSales() {
    if (syncing || !navigator.onLine) return { synced: 0, failed: 0 }
    syncing = true
    try {
      loadPendingSales()
      const toSync = pendingSales.value.filter((s) => !s.synced)
      if (toSync.length === 0) return { synced: 0, failed: 0 }

      let synced = 0
      let failed = 0

      for (const sale of toSync) {
        try {
          let ventaId = sale.ventaId
          if (!ventaId) {
            const venta = await api.post('/api/ventas', {
              cliente_id: sale.data.cliente_id || null,
              sucursal_id: sale.data.sucursal_id || 1,
              notas: sale.data.notas || null,
            })
            if (!venta || !venta.id) throw new Error('No se pudo crear la venta')
            ventaId = venta.id
            sale.ventaId = ventaId
            sale.itemsEnviados = 0
            savePendingSales()
          }

          const items = sale.data.items || []
          for (let i = sale.itemsEnviados || 0; i < items.length; i++) {
            const item = items[i]
            await api.post(`/api/ventas/${ventaId}/items`, {
              producto_id: item.producto_id,
              cantidad: item.cantidad,
              precio_unitario: item.precio_unitario,
              oferta_tipo: item.oferta_tipo || null,
              oferta_valor: item.oferta_valor || null,
              oferta_info: item.oferta_info || null,
              por_kilo: item.por_kilo || false,
              peso: item.peso || null,
              importe: item.importe ?? null,
              medio_pago_carga: item.medio_pago_carga || null,
            })
            sale.itemsEnviados = i + 1
            savePendingSales()
          }

          await api.put(`/api/ventas/${ventaId}/confirmar`, {
            medio_pago: sale.data.medio_pago || 'efectivo',
            efectivo_pagado: sale.data.efectivo_pagado || 0,
            descuento: sale.data.descuento || 0,
            cliente_id: sale.data.cliente_id || undefined,
            comprador_cuit: sale.data.comprador_cuit || undefined,
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
    } finally {
      syncing = false
      notificar()
    }
  }

  function removePendingSale(id) {
    pendingSales.value = pendingSales.value.filter((s) => s.id !== id)
    savePendingSales()
    notificar()
  }

  function getPendingCount() {
    return pendingSales.value.filter((s) => !s.synced).length
  }

  // Listener 'online' a nivel de módulo: se registra una sola vez aunque el
  // composable se use en varias vistas, y las ventas se sincronizan aunque el
  // usuario no vuelva a abrir el POS.
  if (typeof window !== 'undefined' && !onlineListenerRegistered) {
    onlineListenerRegistered = true
    loadPendingSales()
    window.addEventListener('online', () => { syncPendingSales() })
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
