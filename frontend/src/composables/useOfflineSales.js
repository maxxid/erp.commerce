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

// Los productos que no estaban en el catálogo (alta manual o traídos de una
// fuente externa) se agregan al carrito con `Date.now() + Math.random()` como
// id porque el servidor todavía no los conoce. Ese número tiene decimales, así
// que el backend lo rechaza con 422 ("Input should be a valid integer") y la
// venta quedaba reintentándose para siempre. Los ids reales son enteros.
export function esIdTemporal(productoId) {
  if (productoId === null || productoId === undefined || productoId === '') return true
  return !Number.isInteger(Number(productoId))
}

function numero(valor) {
  if (valor === null || valor === undefined || valor === '') return null
  const n = Number(valor)
  return Number.isFinite(n) ? n : null
}

function datosParaCrearProducto(item) {
  const datos = item.producto_nuevo
  if (!datos || !datos.nombre) {
    throw new Error(
      'La venta incluye un producto cargado sin conexión y no quedó guardado ' +
      'su nombre: no se puede recrear en el servidor.'
    )
  }
  return {
    codigo_barras: datos.codigo_barras || null,
    nombre: datos.nombre,
    precio_venta: numero(datos.precio_venta) ?? 0,
    precio_costo: numero(datos.precio_costo) ?? 0,
    fuente: datos.fuente || 'manual',
    cantidad_inicial: numero(datos.cantidad_inicial) ?? 0,
    categoria_id: datos.categoria_id || 1,
  }
}

// Arma el body con los tipos que espera el backend. Los 422 no son "sin
// conexión": si el payload va mal, reintentarlo cada 60 s no lo arregla.
function itemParaElServidor(item) {
  const porKilo = Boolean(item.por_kilo)
  let cantidad = numero(item.cantidad)
  // En los productos por kilo lo que manda es el peso; `cantidad` puede venir
  // vacío si el cajero tocó el campo. Con 1 alcanza para que el backend use el
  // peso y el importe, que son los datos reales de la venta.
  if (!(cantidad > 0) && porKilo) cantidad = 1
  if (!(cantidad > 0)) throw new Error('El ítem no tiene una cantidad válida.')

  const importe = numero(item.importe)
  return {
    producto_id: Number(item.producto_id),
    cantidad,
    precio_unitario: numero(item.precio_unitario),
    oferta_tipo: item.oferta_tipo || null,
    oferta_valor: numero(item.oferta_valor),
    oferta_info: item.oferta_info || null,
    por_kilo: porKilo,
    peso: porKilo ? numero(item.peso) : null,
    importe: importe != null && importe > 0 ? importe : null,
    medio_pago_carga: item.medio_pago_carga || null,
  }
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

  // Un producto temporal (manual o de una fuente externa) no existe en la base.
  // Antes de meter el ítem hay que crearlo, igual que hace el POS con red. Si
  // un intento anterior lo alcanzó a crear, el código ya existe: se busca y se
  // reusa para no trabar la venta para siempre.
  async function asegurarProducto(item) {
    if (!esIdTemporal(item.producto_id)) return
    const datos = datosParaCrearProducto(item)
    try {
      const producto = await api.post('/api/productos', datos)
      if (!producto || !producto.id) {
        throw new Error('No se pudo crear el producto del ítem.')
      }
      item.producto_id = producto.id
    } catch (e) {
      const sePuedeReusar = e?.status === 400 || e?.status === 409
      const existente = sePuedeReusar && datos.codigo_barras
        ? await api.post('/api/productos/lookup', { barcode: datos.codigo_barras }).catch(() => null)
        : null
      if (!existente || !existente.id) throw e
      item.producto_id = existente.id
    }
    savePendingSales()
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
      await asegurarProducto(item)
      await api.post(`/api/ventas/${ventaId}/items`, itemParaElServidor(item))
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

  // El servidor rechazó la venta (400/403/422): reintentarla cada minuto no la
  // arregla y llena la consola. Queda marcada con el motivo para que el aviso
  // lo muestre y el cajero decida cuándo reintentar.
  function marcarRechazada(id, mensaje) {
    const venta = pendingSales.value.find((s) => s.id === id)
    if (!venta) return
    venta.ultimoError = mensaje
    venta.ultimoIntento = new Date().toISOString()
    savePendingSales()
  }

  // Una venta que el servidor rechaza y que no se puede reparar (por ejemplo,
  // un producto manual de una cola vieja que no guardó el nombre) no puede
  // quedar en el aviso para siempre. Se descarta a mano y con confirmación.
  function descartar(id) {
    pendingSales.value = pendingSales.value.filter((s) => s.id !== id)
    savePendingSales()
    notificar()
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
    marcarRechazada,
    descartar,
    cargarUnaVez,
  }
}
