import { ref } from 'vue'
import api from '@/services/api'

const OFFLINE_SALES_KEY = 'apex-offline-sales'
const pendingSales = ref([])
let cargado = false

/**
 * Total de una venta guardada para sincronizar después.
 *
 * Si la cola no registró el importe (las ventas encoladas antes de esto), se
 * recalcula de los items. Es un aviso para el cajero y para el dueño, no un
 * asiento contable: un monto aproximado vale más que no mostrar nada y que
 * nadie se entere de que hay plata sin subir.
 */
export function totalDeVenta(data) {
  if (!data) return 0
  let total = 0
  for (const item of data.items || []) {
    const importe = item.importe ?? (
      Number(item.precio_unitario || 0) * Number(item.peso ?? item.cantidad ?? 0)
    )
    total += Number(importe) || 0
  }
  return Math.max(0, total - (Number(data.descuento) || 0))
}

export function useOfflineSales() {
  function loadPendingSales() {
    try {
      const stored = localStorage.getItem(OFFLINE_SALES_KEY)
      pendingSales.value = stored ? JSON.parse(stored) : []
    } catch {
      pendingSales.value = []
    }
    cargado = true
  }

  // Se carga antes de tocar la cola: sin esto, la primera venta encolada de una
  // sesión pisaría con una lista vacía lo que había quedado guardado.
  function cargarUnaVez() {
    if (!cargado) loadPendingSales()
  }

  function savePendingSales() {
    localStorage.setItem(OFFLINE_SALES_KEY, JSON.stringify(pendingSales.value))
  }

  function notificar() {
    window.dispatchEvent(new Event('apex-pending-sales-updated'))
  }

  function addPendingSale(saleData) {
    cargarUnaVez()
    pendingSales.value.push({
      id: (typeof crypto !== 'undefined' && crypto.randomUUID)
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      data: saleData,
      total: totalDeVenta(saleData),
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

  /**
   * Sube una venta a la server: crear, meter los items de a uno, confirmar.
   *
   * Se llama desde `useOfflineSync`, que ordena las ventas con la caja — la
   * venta necesita la caja abierta y el cierre necesita las ventas ya
   * registradas, así que el orden en que se suben no es un detalle.
   *
   * Lanza lo que le pase: quien llama decide si corta o si sigue. Si se cortó a
   * mitad, `ventaId` y `itemsEnviados` hacen que el siguiente intento continúe
   * donde quedó en vez de crear una venta nueva.
   */
  async function subirVenta(sale) {
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
  }

  // No avisa: quien sincroniza avisa una sola vez al terminar, para que la
  // pantalla no repinte por cada venta subida.
  function marcarSubida(id) {
    const venta = pendingSales.value.find((s) => s.id === id)
    if (venta) venta.synced = true
    pendingSales.value = pendingSales.value.filter((s) => !s.synced)
    savePendingSales()
  }

  return {
    pendingSales,
    addPendingSale,
    subirVenta,
    marcarSubida,
    cargarUnaVez,
  }
}
