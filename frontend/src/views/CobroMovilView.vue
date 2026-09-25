<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useProductosStore } from '@/stores/productos'
import { useCajaStore } from '@/stores/caja'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'
import QRCode from 'qrcode'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()
const productosStore = useProductosStore()
const cajaStore = useCajaStore()

const products = computed(() => productosStore.productos || [])
const categorias = computed(() => productosStore.categorias || [])
const ofertas = computed(() => productosStore.ofertas || [])

const searchText = ref('')
const buscando = ref(false)
const cargando = ref(true)
const confirmando = ref(false)
const showPago = ref(false)
const showCobro = ref(false)
const showTicket = ref(false)
const scannerOpen = ref(false)
const scannerError = ref('')
const lastTicket = ref(null)
const ajustes = ref({})

const cart = reactive({
  items: [],
  subtotal: 0,
  total: 0,
  descuento: 0,
  recibido: '',
  medio_pago: 'efectivo',
})

const mediosPago = [
  { value: 'efectivo', label: 'Efectivo', icon: 'fa-money-bill-wave' },
  { value: 'transferencia', label: 'Transferencia', icon: 'fa-mobile-screen-button' },
  { value: 'mercadopago_qr', label: 'QR MercadoPago', icon: 'fa-qrcode' },
  { value: 'qr_interoperable', label: 'QR BCRA', icon: 'fa-wallet' },
  { value: 'smartpoint', label: 'SmartPoint', icon: 'fa-cash-register' },
  { value: 'cta_corriente', label: 'Cuenta corriente', icon: 'fa-file-invoice-dollar' }
]

const recibidoNum = computed(() => parseFloat(String(cart.recibido).replace(',', '.')) || 0)
const vuelto = computed(() => {
  if (cart.medio_pago !== 'efectivo' || recibidoNum.value <= 0) return 0
  return Math.max(0, recibidoNum.value - cart.total)
})
const falta = computed(() => {
  if (cart.medio_pago !== 'efectivo' || recibidoNum.value <= 0) return 0
  return Math.max(0, cart.total - recibidoNum.value)
})

const filteredProducts = computed(() => {
  const s = searchText.value.trim().toLowerCase()
  let list = products.value
  if (s) {
    list = list.filter(p =>
      (p.nombre || '').toLowerCase().includes(s) ||
      (p.marca || '').toLowerCase().includes(s) ||
      (p.codigo_barras || '').toLowerCase().includes(s)
    )
  }
  return list.slice(0, 48)
})

onMounted(async () => {
  cajaStore.fetchEstado()
  await Promise.all([
    productosStore.fetchAll(),
    api.get('/api/config/ajustes').then(r => { ajustes.value = r || {} }).catch(() => {})
  ])
  cargando.value = false
})

onUnmounted(() => {
  closeCamera()
  clearPolling()
})

function sugerenciasRecibido() {
  if (cart.total <= 0) return []
  const billetes = [100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000]
  const total = Math.ceil(cart.total)
  const sug = []
  for (const b of billetes) {
    if (b >= total && !sug.includes(b)) sug.push(b)
  }
  const exacto = cart.total
  if (!sug.includes(exacto) && exacto > 0) sug.unshift(exacto)
  return sug.slice(0, 5)
}

function autoCompletarRecibido(valor) {
  cart.recibido = String(valor)
}

function addToCart(product, qty = 1, price = null) {
  const isManual = product._pending || (product.codigo_barras && (product.codigo_barras.startsWith('*MANUAL*') || product.codigo_barras.startsWith('GEN-')))
  const oferta = ofertas.value.find(o => o.producto_id === product.id && o.activo)
  const basePrice = price || product.precio_por_kilo || product.precio_venta || 0
  const existing = cart.items.find(i => i.producto_id === product.id)
  const newQty = (existing ? existing.cantidad : 0) + qty
  if (!isManual && product.stock_actual !== undefined && newQty > product.stock_actual) {
    toast.warning(`Stock insuficiente: ${product.stock_actual} disponibles. Se venderá igual y quedará bajo revisión.`)
  }
  if (existing) {
    existing.cantidad += qty
    if (!isManual && product.stock_actual !== undefined && existing.cantidad > product.stock_actual) existing._revision = true
    if (oferta && !isManual) existing.oferta = { ...oferta }
  } else {
    cart.items.push({
      producto_id: product.id,
      nombre: product.nombre,
      codigo_barras: product.codigo_barras,
      precio_unitario: basePrice,
      cantidad: qty,
      oferta: oferta && !isManual ? { ...oferta } : null,
      tipo_venta: product.tipo_venta || 'unidad',
      precio_kilo: product.precio_por_kilo || null,
      precio_unidad: product.precio_por_unidad || null,
      por_kilo: product.tipo_venta === 'kilo' || (product.tipo_venta === 'ambos' && basePrice === product.precio_por_kilo),
      peso: product.tipo_venta === 'kilo' ? (qty > 1 ? qty : 1) : null,
      _pending: product._pending || false,
      _revision: !isManual && product.stock_actual !== undefined && qty > product.stock_actual,
      _nombre: product._nombre,
      _precio: product._precio,
      categoria_id: product.categoria_id
    })
  }
  recalcCart()
  searchText.value = ''
}

function recalcCart() {
  cart.subtotal = cart.items.reduce((sum, i) => {
    const porKilo = i.por_kilo
    const qty = porKilo ? (i.peso || 0) : (i.cantidad || 0)
    const unitPrice = i.precio_unitario || 0
    let lineTotal = unitPrice * qty
    if (i.oferta && !porKilo) {
      const req = i.oferta.requiere_cantidad || 2
      if (qty >= req) {
        if (i.oferta.tipo === 'porcentaje') {
          lineTotal = Math.max(0, lineTotal - lineTotal * (i.oferta.valor / 100))
        } else if (i.oferta.tipo === 'monto_fijo') {
          const mult = Math.floor(qty / req)
          lineTotal = Math.max(0, lineTotal - i.oferta.valor * mult)
        } else if (i.oferta.tipo === '2x1') {
          const mult = Math.floor(qty / req)
          lineTotal = unitPrice * (qty - mult)
        }
      }
    }
    i._precio_neto = qty > 0 ? lineTotal / qty : unitPrice
    return sum + lineTotal
  }, 0)
  cart.total = Math.max(0, cart.subtotal - (cart.descuento || 0))
}

function updateCartQty(idx, qty) {
  if (qty <= 0) {
    cart.items.splice(idx, 1)
    recalcCart()
    return
  }
  const item = cart.items[idx]
  const prod = products.value.find(p => p.id === item.producto_id)
  const isManual = prod?._pending || (prod?.codigo_barras && (prod.codigo_barras.startsWith('*MANUAL*') || prod.codigo_barras.startsWith('GEN-')))
  if (!isManual && prod && prod.stock_actual !== undefined && qty > prod.stock_actual) {
    toast.warning(`Stock insuficiente: ${prod.stock_actual} disponibles. Se venderá igual y quedará bajo revisión.`)
    item._revision = true
  } else {
    item._revision = false
  }
  if (item.por_kilo) {
    item.peso = qty
  } else {
    item.cantidad = qty
  }
  recalcCart()
}

function removeItem(idx) {
  cart.items.splice(idx, 1)
  recalcCart()
}

function vaciarCarrito() {
  cart.items.splice(0, cart.items.length)
  cart.descuento = 0
  cart.recibido = ''
  recalcCart()
}

async function buscarBarcode() {
  const raw = scannerInput.value.trim()
  if (!raw) return
  await lookupAndAdd(raw)
}

async function lookupAndAdd(raw) {
  buscando.value = true
  try {
    const local = products.value.find(p => p.codigo_barras === raw)
    if (local) {
      addToCart(local)
      scannerInput.value = ''
      return
    }
    const resp = await api.post('/api/productos/lookup', { barcode: raw }).catch(() => null)
    if (resp && resp.id) {
      const newP = {
        id: resp.id,
        codigo_barras: resp.codigo_barras,
        nombre: resp.nombre,
        marca: resp.marca || '',
        precio_venta: resp.precio_venta || 0,
        precio_por_kilo: resp.precio_por_kilo || 0,
        precio_por_unidad: resp.precio_por_unidad || 0,
        tipo_venta: resp.tipo_venta || 'unidad',
        stock_actual: resp.stock_actual || 0,
      }
      addToCart(newP)
      productosStore.productos.push(newP)
      scannerInput.value = ''
      return
    }
    if (resp && resp.nombre) {
      showManualEntry.value = true
      manualEntry.codigo = raw
      manualEntry.nombre = resp.nombre
      manualEntry.precio = resp.precio_referencia || resp.precio_venta || 0
      manualEntry.marca = resp.marca || ''
      scannerInput.value = ''
      return
    }
    showManualEntry.value = true
    manualEntry.codigo = raw
    manualEntry.nombre = ''
    manualEntry.precio = 0
    manualEntry.marca = ''
    scannerInput.value = ''
  } catch {
    showManualEntry.value = true
    manualEntry.codigo = raw
    manualEntry.nombre = ''
    manualEntry.precio = 0
    manualEntry.marca = ''
    scannerInput.value = ''
  } finally {
    buscando.value = false
  }
}

const showManualEntry = ref(false)
const manualEntry = reactive({ codigo: '', nombre: '', precio: 0, marca: '', qty: 1 })
const manualGuardando = ref(false)

async function guardarManual() {
  if (!manualEntry.nombre.trim()) {
    toast.error('Ingresá el nombre del producto')
    return
  }
  manualGuardando.value = true
  try {
    const seg = String(manualEntry.codigo || '').trim() || `MANUAL-${Date.now().toString().slice(-6)}`
    const temp = {
      id: Date.now() + Math.random(),
      codigo_barras: seg.startsWith('*') || seg.startsWith('GEN-') ? seg : `*MANUAL*${manualEntry.codigo || ''}`,
      nombre: manualEntry.nombre.trim(),
      marca: manualEntry.marca || '',
      precio_venta: Number(manualEntry.precio) || 0,
      precio_por_kilo: 0,
      precio_por_unidad: Number(manualEntry.precio) || 0,
      tipo_venta: 'unidad',
      stock_actual: manualEntry.qty || 1,
      _pending: true,
      _nombre: manualEntry.nombre.trim(),
      _precio: Number(manualEntry.precio) || 0,
      categoria_id: categorias.value[0]?.id || 1
    }
    addToCart(temp, Number(manualEntry.qty) || 1, Number(manualEntry.precio) || 0)
    productosStore.productos.push(temp)
    showManualEntry.value = false
    manualEntry.codigo = ''
    manualEntry.nombre = ''
    manualEntry.precio = 0
    manualEntry.marca = ''
    manualEntry.qty = 1
    toast.info('Producto temporal. Se dará de alta al confirmar la venta.')
  } finally {
    manualGuardando.value = false
  }
}

// Escáner de cámara
const scannerInput = ref('')
const videoEl = ref(null)
const barcodeDetector = ref(null)
const scanTimer = ref(null)
const cameraStream = ref(null)

function supportsBarcodeDetector() {
  return typeof window !== 'undefined' && 'BarcodeDetector' in window
}

async function abrirScanner() {
  if (!supportsBarcodeDetector()) {
    toast.warning('Tu navegador no soporta escaneo por cámara. Usá el campo manual.')
    return
  }
  scannerError.value = ''
  scannerOpen.value = true
  await nextTick()
  try {
    barcodeDetector.value = new BarcodeDetector({
      formats: ['ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e', 'codabar']
    })
    cameraStream.value = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    if (videoEl.value) {
      videoEl.value.srcObject = cameraStream.value
      await videoEl.value.play().catch(() => {})
    }
    scanTimer.value = setInterval(() => detectFromCamera(), 350)
  } catch {
    scannerError.value = 'No se pudo acceder a la cámara. Permití el acceso e intentá de nuevo.'
    closeCamera()
  }
}

async function detectFromCamera() {
  if (!barcodeDetector.value || !videoEl.value || !cameraStream.value) return
  try {
    const codes = await barcodeDetector.value.detect(videoEl.value)
    if (codes && codes.length && codes[0].rawValue) {
      clearInterval(scanTimer.value)
      scanTimer.value = null
      closeCamera()
      const raw = codes[0].rawValue.trim()
      await lookupAndAdd(raw)
    }
  } catch {
    // ignorar frames sin detección
  }
}

function closeCamera() {
  if (scanTimer.value) {
    clearInterval(scanTimer.value)
    scanTimer.value = null
  }
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(t => t.stop())
    cameraStream.value = null
  }
  barcodeDetector.value = null
  scannerOpen.value = false
}

// MercadoPago QR dinámico (con importe). El QR fijo ya no se usa: no trae monto
// y solo lo paga la app de MercadoPago cuando el vendedor carga el importe.
const mpModalOpen = ref(false)
const mpLoading = ref(false)
const mpError = ref('')
const mpData = ref(null)
const mpPollingTimer = ref(null)
let mpVentaId = null

async function iniciarQr() {
  if (!cart.total) return
  mpLoading.value = true
  mpError.value = ''
  mpModalOpen.value = true
  try {
    const ventaId = await crearVenta()
    if (!ventaId) {
      mpError.value = 'No se pudo crear la venta'
      return
    }
    mpVentaId = ventaId
    const resp = await api.post('/api/pagos/mercadopago/crear-orden', {
      venta_id: ventaId,
      descripcion: `Venta ${ventaId}`
    })
    if (resp && resp.success) {
      const qrDataUrl = resp.qr_data ? await QRCode.toDataURL(resp.qr_data, { width: 480, margin: 2 }) : ''
      mpData.value = {
        tipo: 'dinamico',
        image_url: qrDataUrl,
        order_id: resp.order_id,
        monto: cart.total
      }
      vaciarCarrito()
      startMpPolling(ventaId)
    } else {
      mpError.value = resp?.detail || 'Error al crear la orden de pago'
      mpData.value = null
    }
  } catch (e) {
    mpError.value = e.message || 'Error al crear la orden'
    mpData.value = null
    if (mpVentaId) {
      cancelarVentaPendiente(mpVentaId)
    }
  } finally {
    mpLoading.value = false
  }
}

function startMpPolling(ventaId) {
  if (mpPollingTimer.value) clearInterval(mpPollingTimer.value)
  mpPollingTimer.value = setInterval(async () => {
    try {
      const resp = await api.get(`/api/ventas/${ventaId}`)
      const venta = resp?.data || resp
      if (venta && venta.estado === 'confirmada') {
        clearInterval(mpPollingTimer.value)
        mpPollingTimer.value = null
        mpModalOpen.value = false
        mpData.value = null
        toast.success(`Pago confirmado. Venta ${venta.numero} completada.`)
        showTicket.value = true
        lastTicket.value = { ...venta }
        setTimeout(() => { showTicket.value = false }, 6000)
        productosStore.refreshProductos()
        cajaStore.fetchEstado()
      }
    } catch {
      // polling sigue
    }
  }, 3000)
}

async function cancelarVentaPendiente(ventaId) {
  try {
    await api.put(`/api/ventas/${ventaId}/confirmar`, {
      medio_pago: 'efectivo',
      efectivo_pagado: 0,
      descuento: 0
    })
    toast.warning('Orden MP cancelada. La venta quedó anotada como efectivo.')
  } catch {
    toast.warning('Error conectando. Revisá más tarde en Ventas.')
  }
}

function clearPolling() {
  if (mpPollingTimer.value) {
    clearInterval(mpPollingTimer.value)
    mpPollingTimer.value = null
  }
}

function cerrarModalMp() {
  if (mpData.value?.tipo === 'dinamico' && mpVentaId && mpPollingTimer.value) {
    toast.info('Saliendo del QR. Vendé de nuevo con la modalidad que prefieras.')
  }
  mpModalOpen.value = false
  mpData.value = null
  mpError.value = ''
}

// QR interoperable (EMVCo QRCPS v1.0): lo paga cualquier billetera.
// El dinero llega por transferencia inmediata a la CBU/CVU configurada; la
// venta se confirma manualmente al ver el ingreso acreditado.
const qiModalOpen = ref(false)
const qiLoading = ref(false)
const qiError = ref('')
const qiData = ref(null)
const qiConfirmando = ref(false)
let qiVentaId = null

async function iniciarQrPreferido() {
  const conf = ajustes.value || {}
  if (conf.qr_interop_cuit?.valor && conf.qr_interop_cuenta?.valor) {
    await iniciarQrInteroperable()
  } else {
    await iniciarQr()
  }
}

async function iniciarQrInteroperable() {
  qiLoading.value = true
  qiError.value = ''
  qiModalOpen.value = true
  try {
    const ventaId = await crearVenta()
    if (!ventaId) {
      qiError.value = 'No se pudo crear la venta'
      return
    }
    qiVentaId = ventaId
    const resp = await api.post('/api/pagos/interoperable/crear-orden', {
      venta_id: ventaId
    })
    if (resp && resp.success) {
      const qrDataUrl = resp.qr_data ? await QRCode.toDataURL(resp.qr_data, { width: 480, margin: 2 }) : ''
      qiData.value = {
        image_url: qrDataUrl,
        monto: resp.monto || cart.total,
        venta_numero: resp.venta_numero
      }
      vaciarCarrito()
    } else {
      qiError.value = resp?.detail || 'Error al generar el QR'
      qiData.value = null
    }
  } catch (e) {
    qiError.value = e.data?.detail || e.message || 'Error al generar el QR'
    qiData.value = null
  } finally {
    qiLoading.value = false
  }
}

async function confirmarQrInteroperable() {
  if (!qiVentaId) return
  qiConfirmando.value = true
  try {
    const resp = await api.put(`/api/ventas/${qiVentaId}/confirmar`, {
      medio_pago: 'transferencia',
      efectivo_pagado: 0,
      descuento: 0
    })
    const total = resp?.total || qiData.value?.monto || 0
    qiModalOpen.value = false
    qiData.value = null
    qiError.value = ''
    qiVentaId = null
    toast.success(`Pago por transferencia confirmado. Total: ${fc(total)}`)
    showTicket.value = true
    lastTicket.value = {
      numero: resp?.numero || `#${qiVentaId}`,
      total,
      medio_pago: 'QR Transferencia',
      items: [],
      descuento: 0
    }
    setTimeout(() => { showTicket.value = false }, 8000)
    productosStore.refreshProductos()
    cajaStore.fetchEstado()
  } catch (e) {
    toast.error(e.data?.detail || e.message || 'Error confirmando el pago')
  } finally {
    qiConfirmando.value = false
  }
}

async function cancelarQrInteroperable() {
  qiModalOpen.value = false
  qiData.value = null
  qiError.value = ''
  if (qiVentaId) {
    try {
      await api.put(`/api/ventas/${qiVentaId}/anular`)
      toast.info('Venta pendiente anulada.')
    } catch {
      toast.info('QR cerrado. Quedó una venta pendiente; anulala desde Ventas si no cobrás.')
    }
    qiVentaId = null
  }
}

// apertura de caja
const showApertura = ref(false)
const montoInicial = ref('')
const abriendoCaja = ref(false)

async function confirmarApertura() {
  abriendoCaja.value = true
  try {
    await api.post('/api/caja/apertura', { monto_inicial: parseFloat(montoInicial.value) || 0 })
    await cajaStore.fetchEstado()
    showApertura.value = false
    toast.success('Caja abierta')
  } catch (e) {
    toast.error(e.data?.detail || 'Error al abrir la caja')
  } finally {
    abriendoCaja.value = false
  }
}

async function crearVenta() {
  if (!cart.items.length || cart.total <= 0) return null
  if (!cajaStore.abierta) {
    showApertura.value = true
    return null
  }
  try {
    for (const item of cart.items) {
      const prod = products.value.find(p => p.id === item.producto_id)
      if (prod && prod._pending) {
        try {
          const resp = await api.post('/api/productos', {
            codigo_barras: prod.codigo_barras,
            nombre: prod._nombre || prod.nombre,
            precio_venta: prod._precio || prod.precio_venta,
            precio_costo: 0, fuente: 'manual',
            cantidad_inicial: item.cantidad,
            categoria_id: prod.categoria_id || 1
          })
          if (resp && resp.id) {
            item.producto_id = resp.id
            prod.id = resp.id
            prod.stock_actual = item.cantidad
            prod._pending = false
          }
        } catch {
          // continúa
        }
      }
    }
    const venta = await api.post('/api/ventas', { cliente_id: undefined })
    if (!venta || !venta.id) throw new Error('No se pudo crear la venta')
    for (const item of cart.items) {
      await api.post(`/api/ventas/${venta.id}/items`, {
        producto_id: item.producto_id,
        cantidad: item.cantidad,
        precio_unitario: item._precio_neto || item.precio_unitario,
        oferta_tipo: item.oferta?.tipo || null,
        oferta_valor: item.oferta?.valor || null,
        oferta_info: item.oferta ? `${item.oferta.tipo === 'porcentaje' ? item.oferta.valor + '% OFF' : item.oferta.tipo === 'monto_fijo' ? '$' + item.oferta.valor + ' OFF' : '2x1'}` : null,
        por_kilo: item.por_kilo || false,
        peso: item.peso || null,
      })
    }
    return venta.id
  } catch (e) {
    toast.error(e.message || 'Error creando la venta')
    return null
  }
}

function confirmarVenta() {
  if (!cart.items.length || cart.total <= 0) {
    toast.warning('El carrito está vacío')
    return
  }
  if (!cajaStore.abierta) {
    showApertura.value = true
    return
  }
  cart.recibido = ''
  showCobro.value = true
}

async function ejecutarCobro() {
  if (cart.medio_pago === 'efectivo' && cart.recibido && recibidoNum.value < cart.total) {
    toast.error(`Faltan ${fc(falta.value)}`)
    return
  }
  showCobro.value = false
  if (cart.medio_pago === 'mercadopago_qr') {
    await iniciarQr()
    return
  }
  if (cart.medio_pago === 'qr_interoperable') {
    await iniciarQrInteroperable()
    return
  }
  if (cart.medio_pago === 'smartpoint') {
    const id = await crearVenta()
    if (id) {
      vaciarCarrito()
      toast.success('Venta creada. Registrala en el SmartPoint.')
    }
    return
  }
  if (cart.medio_pago === 'mercadopago_pos') {
    const id = await crearVenta()
    if (id) {
      vaciarCarrito()
      toast.success('Venta creada. Registrala en el SmartPoint físico.')
    }
    return
  }
  confirmando.value = true
  try {
    const ventaId = await crearVenta()
    if (!ventaId) return
    const resp = await api.put(`/api/ventas/${ventaId}/confirmar`, {
      medio_pago: cart.medio_pago,
      efectivo_pagado: 0,
      descuento: cart.descuento || 0
    })
    const total = resp?.total || cart.total
    toast.success(`Venta confirmada. Total: ${fc(total)}`)
    showTicket.value = true
    lastTicket.value = { numero: resp?.numero || `#${ventaId}`, total, medio_pago: cart.medio_pago, items: cart.items.map(i => ({ ...i })), descuento: cart.descuento }
    setTimeout(() => { showTicket.value = false }, 8000)
    vaciarCarrito()
    productosStore.refreshProductos()
    cajaStore.fetchEstado()
  } catch (e) {
    toast.error(e.data?.detail || e.message || 'Error confirmando la venta')
  } finally {
    confirmando.value = false
  }
}

function volverAlPos() {
  router.push('/pos')
}

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div class="h-[100dvh] flex flex-col bg-slate-100 dark:bg-slate-950 overflow-hidden">
    <div class="max-w-md mx-auto w-full h-full flex flex-col">

      <header class="bg-slate-900 text-white px-4 py-3 flex items-center gap-3">
        <button class="p-2 rounded-lg hover:bg-slate-700/50" @click="volverAlPos()" aria-label="Volver al POS">
          <i class="fa-solid fa-arrow-left text-lg"></i>
        </button>
        <div class="flex-1 min-w-0">
          <div class="font-semibold leading-tight truncate">Cobro rápido</div>
          <div class="text-xs text-slate-300 truncate">{{ auth.currentUser?.nombre || auth.currentUser?.username }}</div>
        </div>
        <span v-if="cajaStore.abierta" class="text-xs bg-green-600/80 px-2 py-1 rounded-lg">Caja abierta</span>
        <span v-else class="text-xs bg-amber-500/80 px-2 py-1 rounded-lg">Caja cerrada</span>
        <button class="p-2 rounded-lg hover:bg-slate-700/50 text-xs" @click="logout()" aria-label="Salir">
          <i class="fa-solid fa-right-from-bracket text-base"></i>
        </button>
      </header>

      <div class="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        <div class="flex gap-2">
          <div class="relative flex-1">
            <input
              v-model="scannerInput"
              type="text"
              inputmode="numeric"
              placeholder="Código de barras…"
              class="w-full rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-4 py-3 text-base"
              @keyup.enter="buscarBarcode"
            />
            <i class="fa-solid fa-barcode absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
          </div>
          <button class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-brand-600 text-white active:bg-brand-700" @click="abrirScanner">
            <i class="fa-solid fa-camera"></i>
            <span class="text-sm font-medium">Escanear</span>
          </button>
        </div>

        <div class="flex gap-2 items-center">
          <i class="fa-solid fa-magnifying-glass text-slate-400"></i>
          <input
            v-model="searchText"
            type="text"
            placeholder="Buscar producto…"
            class="flex-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm"
          />
        </div>

        <div v-if="cart.items.length" class="rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-3 flex flex-col gap-2">
          <div class="text-sm font-semibold text-slate-600 dark:text-slate-300 flex items-center justify-between">
            <span>Carrito ({{ cart.items.length }})</span>
            <button class="text-xs text-red-500" @click="vaciarCarrito">Vaciar</button>
          </div>
          <div v-for="(item, idx) in cart.items" :key="item.producto_id" class="flex flex-col gap-1.5 border-b border-slate-200 dark:border-slate-700 last:border-0 pb-2 last:pb-0">
            <div class="flex items-center gap-2">
              <span class="text-red-500 cursor-pointer p-1" @click="removeItem(idx)"><i class="fa-solid fa-xmark"></i></span>
              <div class="flex-1 min-w-0">
                <div class="text-sm truncate flex items-center gap-1.5">
                  <span class="truncate">{{ item.nombre }}</span>
                  <span v-if="item._revision" class="shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-rose-100 text-rose-600 dark:bg-rose-900/40 dark:text-rose-300" title="Se vende por encima del stock registrado en lotes. Revisar.">A revisar</span>
                </div>
                <div class="text-xs text-slate-500">{{ fc(item._precio_neto || item.precio_unitario) }}</div>
              </div>
              <div class="flex items-center gap-1">
                <button class="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-700 text-base" @click="updateCartQty(idx, (item.por_kilo ? item.peso||0 : item.cantidad||0) - 1)">−</button>
                <span v-if="!item.por_kilo" class="w-7 text-center text-sm font-semibold">{{ item.cantidad }}</span>
                <input v-else v-model="item.peso" type="text" inputmode="decimal" class="w-14 text-center text-sm rounded-md bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600" @input="recalcCart" />
                <button class="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-700 text-base" @click="updateCartQty(idx, (item.por_kilo ? item.peso||0 : item.cantidad||0) + 1)">+</button>
              </div>
            </div>
            <div class="text-right text-sm font-semibold">{{ fc((item._precio_neto || item.precio_unitario) * (item.por_kilo ? (item.peso||0) : item.cantidad)) }}</div>
          </div>
        </div>

        <div v-if="filteredProducts.length" class="grid grid-cols-2 gap-2">
          <button
            v-for="p in filteredProducts"
            :key="p.id"
            class="flex flex-col items-start rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3 active:bg-slate-100 dark:active:bg-slate-700 min-w-0"
            @click="addToCart(p)"
          >
            <span class="text-sm font-medium line-clamp-2 text-left">{{ p.nombre }}</span>
            <span v-if="p.marca" class="text-xs text-slate-500 line-clamp-1">{{ p.marca }}</span>
            <span class="mt-1 text-sm font-bold text-brand-600">
              {{ fc(p.precio_por_kilo || p.precio_venta || 0) }}
            </span>
          </button>
        </div>
        <div v-else-if="!cargando" class="text-center text-slate-400 text-sm py-8">
          No hay productos que coincidan
        </div>
      </div>

      <!-- Barra de cobro -->
      <div class="border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 px-4 pt-3 pb-4 flex flex-col gap-2">
        <div class="text-xs text-slate-500">Total a cobrar</div>
        <div class="text-3xl font-bold">{{ fc(cart.total) }}</div>
        <div class="flex gap-2 pt-1">
          <button
            :disabled="!cart.items.length || cart.total <= 0 || mpLoading"
            class="flex-1 rounded-xl border border-slate-300 dark:border-slate-700 py-3 text-sm font-medium active:bg-slate-100 dark:active:bg-slate-800 disabled:opacity-40"
            @click="iniciarQrPreferido"
          >
            <i v-if="mpLoading" class="fa-solid fa-circle-notch animate-spin mr-1"></i>
            <i v-else class="fa-solid fa-qrcode mr-1"></i> QR
          </button>
          <button
            :disabled="!cart.items.length || cart.total <= 0 || confirmando || (buscando && false)"
            class="flex-[2] rounded-xl bg-brand-600 text-white py-3 text-base font-semibold active:bg-brand-700 disabled:opacity-40"
            @click="confirmarVenta"
          >
            <i v-if="confirmando" class="fa-solid fa-circle-notch animate-spin"></i>
            <template v-else>Cobrar ({{ cart.total ? fc(cart.total) : '' }})</template>
          </button>
        </div>
      </div>
    </div>

    <!-- Modal escáner -->
    <BaseModal v-model="scannerOpen" title="Escanear código" :persistent="true">
      <div class="flex flex-col gap-3">
        <div v-if="!scannerError" class="relative rounded-xl overflow-hidden bg-black aspect-video mx-auto max-w-sm w-full">
          <video ref="videoEl" class="w-full h-full object-cover" muted playsinline></video>
        </div>
        <div v-else class="text-amber-600 text-sm">{{ scannerError }}</div>
        <div class="flex gap-2">
          <BaseButton variant="secondary" block @click="closeCamera">Cancelar</BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal QR MercadoPago -->
    <BaseModal v-model="mpModalOpen" title="Pago con QR" :close-on-esc="false">
      <div class="flex flex-col items-center gap-3 py-2">
        <div v-if="mpLoading" class="py-8 text-slate-400"><i class="fa-solid fa-circle-notch animate-spin text-3xl"></i></div>
        <template v-if="mpData">
          <img :src="mpData.image_url" alt="QR" class="w-56 h-56 rounded-xl bg-white p-2 object-contain" />
          <div class="text-center text-sm text-slate-600 dark:text-slate-300">{{ mpData.monto ? `Monto: ${fc(mpData.monto)}` : '' }}</div>
          <div class="text-xs text-slate-500 text-center">El cliente escanea este QR y abona. La venta se cierra sola al confirmar el pago.</div>
        </template>
        <div v-if="mpError" class="text-red-500 text-sm text-center">{{ mpError }}</div>
        <BaseButton v-if="mpError" variant="secondary" block @click="mpModalOpen = false">Cerrar</BaseButton>
      </div>
    </BaseModal>

    <!-- Modal QR interoperable (todas las billeteras) -->
    <BaseModal v-model="qiModalOpen" title="Cobro con QR (transferencia)" :close-on-esc="false">
      <div class="flex flex-col items-center gap-3 py-2">
        <div v-if="qiLoading" class="py-8 text-slate-400"><i class="fa-solid fa-circle-notch animate-spin text-3xl"></i></div>
        <template v-if="qiData">
          <img :src="qiData.image_url" alt="QR" class="w-56 h-56 rounded-xl bg-white p-2 object-contain" />
          <div class="text-center text-sm text-slate-600 dark:text-slate-300">{{ qiData.monto ? `Monto: ${fc(qiData.monto)}` : '' }}</div>
          <div class="text-xs text-slate-500 text-center">El cliente lo paga con cualquier billetera (Brubank, Personal Pay, MODO, MP). La transferencia llega directo a tu CBU/CVU. Confirmá acá el cobro cuando lo veas acreditado.</div>
          <div class="flex gap-2 w-full mt-2">
            <BaseButton variant="secondary" block :disabled="qiConfirmando" @click="cancelarQrInteroperable">Cancelar</BaseButton>
            <BaseButton variant="primary" block :loading="qiConfirmando" @click="confirmarQrInteroperable">
              <i class="fa-solid fa-check mr-1"></i> Ya me pagaron
            </BaseButton>
          </div>
        </template>
        <div v-if="qiError" class="text-red-500 text-sm text-center">{{ qiError }}</div>
        <BaseButton v-if="qiError" variant="secondary" block @click="qiModalOpen = false">Cerrar</BaseButton>
      </div>
    </BaseModal>

    <!-- Modal pago manual simple -->
    <BaseModal v-model="showManualEntry" title="Alta rápida" :persistent="true">
      <div class="flex flex-col gap-3">
        <div class="text-xs text-slate-500">Código: {{ manualEntry.codigo || 'sin código' }}</div>
        <BaseInput v-model="manualEntry.nombre" label="Nombre *" placeholder="Ej: Pan casero" />
        <BaseInput v-model="manualEntry.precio" label="Precio de venta *" type="text" inputmode="decimal" placeholder="0" />
        <BaseInput v-model="manualEntry.qty" label="Cantidad" type="text" inputmode="numeric" />
        <div class="grid grid-cols-1 gap-2 mt-1">
          <BaseButton variant="primary" block :loading="manualGuardando" @click="guardarManual">Agregar al carrito</BaseButton>
          <BaseButton variant="ghost" block @click="showManualEntry = false">Cancelar</BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal cobro -->
    <BaseModal v-model="showCobro" title="Confirmar venta" :close-on-esc="false">
      <div class="flex flex-col gap-4">
        <div class="text-center">
          <div class="text-xs text-slate-500">Total a cobrar</div>
          <div class="text-4xl font-bold text-brand-600">{{ fc(cart.total) }}</div>
        </div>

        <div>
          <div class="text-sm font-semibold mb-2">Medio de pago</div>
          <div class="grid grid-cols-3 gap-2">
            <button
              v-for="m in mediosPago.filter(x => x.value !== 'mercadopago_pos')"
              :key="m.value"
              class="flex flex-col items-center gap-1 py-2 rounded-xl border text-xs transition"
              :class="cart.medio_pago === m.value ? 'border-brand-600 bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300' : 'border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300'"
              @click="cart.medio_pago = m.value"
            >
              <i :class="['fa-solid', m.icon, 'text-lg']"></i>
              <span>{{ m.label }}</span>
            </button>
          </div>
        </div>

        <div v-if="cart.medio_pago === 'efectivo'">
          <BaseInput v-model="cart.recibido" label="¿Con cuánto paga?" type="text" inputmode="decimal" placeholder="0" hint="Opcional. Dejalo vacío para cobrar exacto." />
          <div class="flex gap-2 flex-wrap mt-2" v-if="sugerenciasRecibido().length">
            <button
              v-for="s in sugerenciasRecibido()"
              :key="s"
              class="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 text-sm text-slate-600 dark:text-slate-300"
              @click="autoCompletarRecibido(s)"
            >{{ fc(s) }}</button>
          </div>
          <div v-if="recibidoNum > 0 && cart.total > 0" class="mt-3 space-y-1">
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">TOTAL</span>
              <span>{{ fc(cart.total) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span class="text-slate-500">Paga con</span>
              <span>{{ fc(recibidoNum) }}</span>
            </div>
            <div class="flex justify-between text-base font-semibold" :class="falta > 0 ? 'text-red-500' : 'text-green-600'">
              <span>{{ falta > 0 ? 'FALTA' : 'VUELTO' }}</span>
              <span>{{ fc(falta > 0 ? falta : vuelto) }}</span>
            </div>
          </div>
        </div>

        <div v-else class="text-sm text-slate-500 text-center bg-slate-50 dark:bg-slate-800 rounded-xl py-3">
          Confirmando {{ mediosPago.find(m => m.value === cart.medio_pago)?.label || cart.medio_pago }} por {{ fc(cart.total) }}
        </div>

        <div class="grid grid-cols-2 gap-2">
          <BaseButton variant="secondary" block @click="showCobro = false">Volver</BaseButton>
          <BaseButton variant="primary" block :loading="confirmando" @click="ejecutarCobro">Confirmar compra</BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal apertura de caja -->
    <BaseModal v-model="showApertura" title="Abrir caja" :persistent="true">
      <div class="flex flex-col gap-3">
        <div class="text-sm text-slate-500">La caja está cerrada. Ingresá el dinero inicial para abrirla y poder cobrar.</div>
        <BaseInput v-model="montoInicial" label="Monto inicial" type="text" inputmode="decimal" placeholder="0" />
        <div class="grid grid-cols-1 gap-2 mt-1">
          <BaseButton variant="primary" block :loading="abriendoCaja" @click="confirmarApertura">Abrir caja</BaseButton>
          <BaseButton variant="ghost" block @click="showApertura = false">Cancelar</BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Notificación de ticket -->
    <div v-if="showTicket" class="fixed inset-x-0 bottom-4 flex justify-center pointer-events-none" :style="{ zIndex: 60 }">
      <div class="bg-slate-900 text-white rounded-xl px-5 py-3 shadow-xl flex flex-col gap-1 max-w-sm w-full mx-4">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-circle-check text-green-400"></i>
          <span class="font-semibold">Venta {{ lastTicket?.numero }}</span>
        </div>
        <span class="text-sm text-slate-300">Total: {{ fc(lastTicket?.total) }}</span>
        <span class="text-xs text-slate-400">{{ lastTicket?.items?.length }} producto(s)</span>
      </div>
    </div>
  </div>
</template>