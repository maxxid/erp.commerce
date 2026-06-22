<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">POS de Ventas</h2>
        <p class="text-sm text-slate-500 mt-1">Punto de Venta</p>
      </div>
      <div class="flex items-center gap-2">
        <span class="text-xs text-slate-400 bg-slate-100 px-3 py-1 rounded-full font-bold">
          <i class="fa-solid fa-user mr-1"></i>{{ auth.currentUser.nombre }}
        </span>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- COLUMN 1: Product Catalog -->
      <div class="lg:col-span-1 space-y-4">
        <!-- Barcode lookup -->
        <div class="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm space-y-3">
          <label class="text-[10px] font-bold text-slate-400 uppercase block">Código de Barras</label>
          <div class="relative">
            <i class="fa-solid fa-barcode absolute left-4 top-3.5 text-slate-400"></i>
            <input
              v-model="posLookupCode"
              @keydown.enter="triggerPOSLookup"
              @input="handlePOSInput"
              placeholder="Escanear o escribir código..."
              class="w-full bg-slate-50 border border-slate-200 rounded-xl pl-11 pr-4 py-3 text-sm font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
            />
          </div>

          <!-- Lookup result card -->
          <div v-if="lookupProduct._loading" class="flex items-center justify-center py-4">
            <i class="fa-solid fa-circle-notch animate-spin text-brand-600 text-lg"></i>
            <span class="ml-2 text-sm text-slate-500">Buscando...</span>
          </div>
          <div v-else-if="lookupProduct.id" class="p-3 bg-brand-50 border border-brand-100 rounded-xl">
            <div class="flex items-start gap-3">
              <div class="w-12 h-12 rounded-xl bg-brand-100 flex items-center justify-center text-brand-600 flex-shrink-0">
                <i class="fa-solid fa-box text-lg"></i>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-sm font-bold text-slate-900 truncate">{{ lookupProduct.nombre }}</p>
                <p class="text-xs text-slate-500">{{ lookupProduct.marca }}</p>
                <div class="flex items-center gap-3 mt-1.5">
                  <span class="text-sm font-bold font-mono-data text-brand-600">{{ fc(lookupProduct.precio_venta) }}</span>
                  <span class="text-[10px] text-slate-400">Stock: {{ lookupProduct.stock_actual }}</span>
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2 mt-3">
              <input
                v-model.number="lookupProduct._qty"
                type="number"
                min="1"
                class="w-16 bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-sm text-center font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600"
              />
              <input
                v-model.number="lookupProduct._price"
                type="number"
                step="0.01"
                class="flex-1 bg-white border border-slate-200 rounded-lg px-2 py-1.5 text-sm text-center font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600"
              />
              <button
                @click="addToCart(lookupProduct, lookupProduct._qty, lookupProduct._price)"
                class="bg-brand-600 hover:bg-brand-700 text-white px-3 py-1.5 rounded-lg text-xs font-semibold transition flex-shrink-0"
              >
                <i class="fa-solid fa-plus mr-1"></i> Agregar
              </button>
            </div>
          </div>
          <div v-else-if="lookupProduct._searched" class="p-3 bg-rose-50 border border-rose-100 rounded-xl text-xs text-rose-600 font-bold text-center">
            Producto no encontrado
          </div>
        </div>

        <!-- Search input -->
        <div class="relative">
          <i class="fa-solid fa-magnifying-glass absolute left-4 top-3.5 text-slate-400"></i>
          <input
            v-model="posTextSearch"
            placeholder="Buscar producto..."
            class="w-full bg-white border border-slate-200 rounded-xl pl-11 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition shadow-sm"
          />
        </div>

        <!-- Category filter buttons -->
        <div class="flex flex-wrap gap-2">
          <button
            @click="selectedPOSCategory = null"
            :class="!selectedPOSCategory ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold transition shadow-sm"
          >
            Todos
          </button>
          <button
            v-for="cat in categories"
            :key="cat.id"
            @click="selectedPOSCategory = cat.id"
            :class="selectedPOSCategory === cat.id ? 'bg-brand-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold transition shadow-sm"
          >
            {{ cat.nombre }}
          </button>
        </div>

        <!-- Product grid -->
        <div class="grid grid-cols-2 gap-3 max-h-[420px] overflow-y-auto pr-1">
          <div
            v-for="p in filteredPOSProducts"
            :key="p.id"
            @click="selectProductForLookup(p)"
            class="bg-white border border-slate-200 p-3 rounded-xl shadow-sm hover:border-brand-300 hover:shadow-md transition cursor-pointer"
          >
            <div class="flex items-center gap-2 mb-1">
              <div class="w-8 h-8 rounded-lg bg-brand-50 flex items-center justify-center text-brand-600 flex-shrink-0">
                <i class="fa-solid fa-box text-xs"></i>
              </div>
              <p class="text-xs font-bold text-slate-900 truncate leading-tight">{{ p.nombre }}</p>
            </div>
            <p class="text-[10px] text-slate-400 truncate">{{ p.marca }}</p>
            <div class="flex items-center justify-between mt-1.5">
              <span class="text-sm font-bold font-mono-data text-brand-600">{{ fc(p.precio_venta) }}</span>
              <span class="text-[10px] text-slate-400">{{ p.stock_actual }} u</span>
            </div>
          </div>
          <p v-if="!filteredPOSProducts.length" class="col-span-2 text-xs text-slate-400 text-center py-8">
            Sin productos
          </p>
        </div>
      </div>

      <!-- COLUMN 2: Cart -->
      <div class="lg:col-span-1 space-y-4">
        <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
          <div class="p-4 border-b border-slate-100 flex items-center gap-2">
            <i class="fa-solid fa-cash-register text-brand-600"></i>
            <span class="text-sm font-bold text-slate-900">Carrito</span>
            <span class="text-[10px] text-slate-400 ml-auto">{{ cart.items.length }} productos</span>
          </div>

          <!-- Cart items -->
          <div class="max-h-[360px] overflow-y-auto divide-y divide-slate-50">
            <div
              v-for="(item, idx) in cart.items"
              :key="idx"
              class="p-3 flex items-center gap-3 hover:bg-slate-50 transition"
            >
              <div class="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-500 flex-shrink-0">
                <i class="fa-solid fa-box text-xs"></i>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-bold text-slate-900 truncate">{{ item.nombre }}</p>
                <p class="text-[10px] text-slate-400">{{ item.codigo_barras }}</p>
                <div class="flex items-center gap-2 mt-0.5">
                  <button
                    @click="updateCartQty(idx, item.cantidad - 1)"
                    class="w-5 h-5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-500 text-xs flex items-center justify-center transition"
                  >&minus;</button>
                  <span class="text-xs font-mono-data font-bold text-slate-700 w-5 text-center">{{ item.cantidad }}</span>
                  <button
                    @click="updateCartQty(idx, item.cantidad + 1)"
                    class="w-5 h-5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-500 text-xs flex items-center justify-center transition"
                  >+</button>
                  <span class="text-xs font-mono-data font-bold text-brand-600 ml-auto">{{ fc(item.precio_unitario * item.cantidad) }}</span>
                </div>
              </div>
              <button
                @click="removeFromCart(idx)"
                class="w-6 h-6 rounded-lg text-rose-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center transition flex-shrink-0"
              >
                <i class="fa-solid fa-trash text-[10px]"></i>
              </button>
            </div>
          </div>

          <!-- Empty cart -->
          <div v-if="!cart.items.length" class="p-8 text-center">
            <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-3">
              <i class="fa-solid fa-basket-shopping text-slate-300 text-2xl"></i>
            </div>
            <p class="text-sm text-slate-400 font-semibold">Carrito vacío</p>
            <p class="text-xs text-slate-300 mt-1">Escaneá o seleccioná productos</p>
          </div>
        </div>

        <!-- Cart summary -->
        <div class="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-slate-500">Subtotal</span>
            <span class="font-mono-data font-bold text-slate-800">{{ fc(cart.subtotal) }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500">Descuento</span>
            <div class="flex items-center gap-2">
              <input
                v-model.number="cart.descuento"
                @input="recalcCart"
                type="number"
                step="0.01"
                min="0"
                placeholder="0"
                class="w-20 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1.5 text-xs text-right font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600"
              />
              <span class="text-[10px] text-slate-400">$</span>
            </div>
          </div>

          <hr class="border-slate-100" />

          <div class="flex justify-between">
            <span class="text-sm font-bold text-slate-900">Total</span>
            <span class="text-lg font-bold font-mono-data text-brand-600">{{ fc(cart.total) }}</span>
          </div>

          <!-- Payment method -->
          <div ref="pagoSection" tabindex="0" @keydown="handlePagoKeydown"
               class="focus:outline-none focus:ring-2 focus:ring-brand-400 rounded-xl p-1 -m-1">
            <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">
              Medio de Pago
              <span class="text-slate-300 ml-2 font-normal">Atajos: 1-5, ←→, Enter</span>
            </label>
            <select
              v-model="cart.medio_pago"
              class="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
            >
              <option value="efectivo">Efectivo</option>
              <option value="transferencia">Transferencia</option>
              <option value="debito">Débito</option>
              <option value="credito">Crédito</option>
              <option value="cta_corriente">Cta. Corriente</option>
            </select>
          </div>

          <!-- Client selector -->
          <div>
            <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Cliente</label>
            <select
              v-model="cart.cliente_id"
              class="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
            >
              <option :value="null">Consumidor Final</option>
              <option v-for="c in clientes" :key="c.id" :value="c.id">{{ c.nombre }}</option>
            </select>
          </div>

          <button
            @click="confirmarVenta"
            :disabled="!cart.items.length || confirmando"
            class="w-full bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white py-3 rounded-xl text-sm font-semibold shadow-lg shadow-emerald-600/20 transition flex items-center justify-center gap-2"
          >
            <i :class="confirmando ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check-circle'"></i>
            {{ confirmando ? 'Procesando...' : 'Confirmar Venta' }}
          </button>

          <button
            @click="vaciarCarrito"
            v-if="cart.items.length"
            class="w-full text-rose-500 hover:text-rose-600 text-xs font-semibold transition text-center"
          >
            <i class="fa-solid fa-trash mr-1"></i> Vaciar carrito
          </button>
        </div>
      </div>

      <!-- COLUMN 3: Quick Stats -->
      <div class="lg:col-span-1 space-y-4">
        <!-- Stats cards -->
        <div class="grid grid-cols-2 gap-3">
          <div class="bg-white border border-slate-200 p-3 rounded-2xl shadow-sm text-center">
            <div class="text-[10px] font-bold text-slate-400 uppercase">Ventas Hoy</div>
            <div class="text-lg font-bold font-mono-data text-emerald-600 mt-0.5">{{ fc(stats.ventas_hoy) }}</div>
            <div class="text-[10px] text-slate-400 mt-0.5">{{ stats.tickets_hoy }} tickets</div>
          </div>
          <div class="bg-white border border-slate-200 p-3 rounded-2xl shadow-sm text-center">
            <div class="text-[10px] font-bold text-slate-400 uppercase">Ticket Prom.</div>
            <div class="text-lg font-bold font-mono-data text-brand-600 mt-0.5">{{ fc(stats.ticket_promedio) }}</div>
          </div>
          <div class="bg-white border border-slate-200 p-3 rounded-2xl shadow-sm text-center">
            <div class="text-[10px] font-bold text-slate-400 uppercase">Efectivo</div>
            <div class="text-base font-bold font-mono-data text-blue-600 mt-0.5">{{ fc(stats.efectivo) }}</div>
          </div>
          <div class="bg-white border border-slate-200 p-3 rounded-2xl shadow-sm text-center">
            <div class="text-[10px] font-bold text-slate-400 uppercase">Caja</div>
            <div class="text-base font-bold font-mono-data text-emerald-600 mt-0.5">{{ fc(stats.saldo_caja) }}</div>
          </div>
        </div>

        <!-- Recent transactions -->
        <div class="bg-white border border-slate-200 rounded-2xl shadow-sm">
          <div class="p-4 border-b border-slate-100">
            <h3 class="text-sm font-bold text-slate-900">Últimas Transacciones</h3>
          </div>
          <div class="divide-y divide-slate-50 max-h-[300px] overflow-y-auto">
            <div
              v-for="t in recentTransactions"
              :key="t.id"
              class="p-3 flex items-center gap-3 hover:bg-slate-50 transition"
            >
              <div :class="t.medio_pago === 'efectivo' ? 'bg-emerald-50 text-emerald-600' : 'bg-blue-50 text-blue-600'"
                   class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0">
                <i :class="t.medio_pago === 'efectivo' ? 'fa-solid fa-money-bill-wave' : 'fa-solid fa-credit-card'" class="text-xs"></i>
              </div>
              <div class="flex-1 min-w-0">
                <p class="text-xs font-bold text-slate-800 truncate">{{ t.cliente || 'Consumidor Final' }}</p>
                <p class="text-[10px] text-slate-400">{{ t.hora }} · {{ t.items }} productos</p>
              </div>
              <span class="text-xs font-bold font-mono-data text-slate-800">{{ fc(t.total) }}</span>
            </div>
            <p v-if="!recentTransactions.length" class="text-xs text-slate-400 text-center py-6">
              Sin transacciones hoy
            </p>
          </div>
        </div>

        <!-- Product lookup badges -->
        <div v-if="lookupBadges.length" class="bg-white border border-slate-200 p-3 rounded-2xl shadow-sm">
          <p class="text-[10px] font-bold text-slate-400 uppercase mb-2">Escaneos Recientes</p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="(b, bi) in lookupBadges"
              :key="bi"
              class="px-2 py-1 bg-slate-50 border border-slate-200 rounded-lg text-[10px] font-mono-data font-bold text-slate-600"
            >{{ b }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
  <TicketModal :show="showTicket" :ticket="ticketData" @close="showTicket = false" />
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'
import TicketModal from '@/components/layout/TicketModal.vue'

const auth = useAuthStore()
const toast = useToastStore()

const posLookupCode = ref('')
const posTextSearch = ref('')
const selectedPOSCategory = ref(null)
const confirmando = ref(false)
const _processingLookup = ref(false)
const showTicket = ref(false)
const ticketData = reactive({ items: [], numero: '', fecha: '', total: 0, descuento: 0, medio_pago: '', cliente: '', sucursal: '' })

const lookupProduct = reactive({
  id: null,
  codigo_barras: '',
  nombre: '',
  marca: '',
  precio_venta: 0,
  precio_costo: 0,
  categoria_id: null,
  stock_actual: 0,
  _loading: false,
  _searched: false,
  _qty: 1,
  _price: 0
})

const lookupBadges = ref([])

const cart = reactive({
  items: [],
  subtotal: 0,
  total: 0,
  descuento: 0,
  medio_pago: 'efectivo',
  cliente_id: null
})

const stats = reactive({
  ventas_hoy: 84500,
  tickets_hoy: 12,
  ticket_promedio: 7041,
  efectivo: 52000,
  saldo_caja: 72000
})

const products = ref([
  { id: 1, codigo_barras: '7791234567890', nombre: 'Coca-Cola 2.25L', marca: 'Coca-Cola', precio_venta: 2800, precio_costo: 2100, categoria_id: 1, stock_actual: 45 },
  { id: 2, codigo_barras: '7799876543210', nombre: 'Arroz Gallo 1kg', marca: 'Gallo', precio_venta: 1500, precio_costo: 1100, categoria_id: 2, stock_actual: 120 },
  { id: 3, codigo_barras: '7794561237890', nombre: 'Agua Mineral 1.5L', marca: 'Villa del Sur', precio_venta: 950, precio_costo: 600, categoria_id: 1, stock_actual: 80 }
])

const categories = ref([
  { id: 1, nombre: 'Bebidas' },
  { id: 2, nombre: 'Almacén' }
])

const clientes = ref([
  { id: 1, nombre: 'Juan Pérez' },
  { id: 2, nombre: 'María García' },
  { id: 3, nombre: 'Carlos López' }
])

const recentTransactions = ref([
  { id: 1, cliente: 'Juan Pérez', total: 8900, items: 4, medio_pago: 'efectivo', hora: '14:22' },
  { id: 2, cliente: null, total: 3200, items: 2, medio_pago: 'transferencia', hora: '13:45' },
  { id: 3, cliente: 'María García', total: 15600, items: 7, medio_pago: 'efectivo', hora: '12:10' },
  { id: 4, cliente: null, total: 4500, items: 3, medio_pago: 'debito', hora: '11:30' },
  { id: 5, cliente: 'Carlos López', total: 12000, items: 5, medio_pago: 'credito', hora: '10:55' }
])

const filteredPOSProducts = computed(() => {
  let list = products.value
  if (selectedPOSCategory.value) {
    list = list.filter(p => p.categoria_id === selectedPOSCategory.value)
  }
  if (posTextSearch.value.trim()) {
    const q = posTextSearch.value.toLowerCase()
    list = list.filter(p =>
      p.nombre.toLowerCase().includes(q) ||
      p.marca.toLowerCase().includes(q) ||
      p.codigo_barras.includes(q)
    )
  }
  return list
})

onMounted(async () => {
  try {
    const [prods, cats, clis] = await Promise.all([
      api.get('/api/productos').catch(() => null),
      api.get('/api/categorias').catch(() => null),
      api.get('/api/clientes').catch(() => null)
    ])
    if (prods && prods.length) products.value = prods
    if (cats && cats.length) categories.value = cats
    if (clis && clis.length) clientes.value = clis
  } catch { /* fallback to mock */ }

  fetchPOSStats()
  fetchRecentTransactions()
})

async function fetchPOSStats() {
  try {
    const [dash, cajaRes, cajaEst] = await Promise.all([
      api.get('/api/dashboard/resumen').catch(() => null),
      api.get('/api/caja/resumen').catch(() => null),
      api.get('/api/caja/estado').catch(() => null)
    ])
    if (dash) {
      stats.ventas_hoy = dash.ventas_hoy || 0
      stats.tickets_hoy = dash.cant_ventas_hoy || 0
      stats.ticket_promedio = dash.ticket_promedio || 0
    }
    if (cajaRes && cajaRes.desglose) {
      stats.efectivo = cajaRes.desglose.efectivo || 0
    }
    if (cajaEst) {
      stats.saldo_caja = cajaEst.saldo_actual || 0
    }
  } catch { /* fallback to mock */ }
}

async function fetchRecentTransactions() {
  try {
    const ventas = await api.get('/api/ventas?page_size=5').catch(() => null)
    if (ventas && ventas.length) {
      recentTransactions.value = ventas.map(v => ({
        id: v.id,
        cliente: v.cliente_nombre || null,
        total: v.total,
        items: v.items ? v.items.length : 0,
        medio_pago: v.medio_pago,
        hora: v.fecha ? new Date(v.fecha).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }) : ''
      }))
    }
  } catch { /* fallback to mock */ }
}

function selectProductForLookup(product) {
  Object.assign(lookupProduct, {
    id: product.id,
    codigo_barras: product.codigo_barras,
    nombre: product.nombre,
    marca: product.marca,
    precio_venta: product.precio_venta,
    precio_costo: product.precio_costo,
    categoria_id: product.categoria_id,
    stock_actual: product.stock_actual,
    _loading: false,
    _searched: true,
    _qty: 1,
    _price: product.precio_venta
  })
}

async function triggerPOSLookup() {
  const raw = posLookupCode.value.trim()
  if (!raw || _processingLookup) return
  _processingLookup = true

  // 1) Carga manual rápida: *Nombre*Precio
  if (raw.startsWith('*')) {
    posLookupCode.value = ''
    const parts = raw.split('*')
    const nombre = (parts[1] || '').trim()
    const precio = parseFloat(parts[2] || '0')
    if (!nombre || precio <= 0) {
      toast.add('warning', 'Formato: *Nombre*Precio. Ej: *COCA 1.5L*1500')
      _processingLookup = false
      return
    }
    try {
      const resp = await api.post('/api/productos', {
        codigo_barras: `*MANUAL*${Date.now()}`,
        nombre, precio_venta: precio, precio_costo: 0,
        fuente: 'manual', cantidad_inicial: 1, categoria_id: categories.value[0]?.id || 1
      }).catch(() => null)
      if (resp && resp.id) {
        toast.add('warning', `${nombre} creado. Stock=1. Luego de la venta quedará en 0. Ajustá stock y costo reales en Productos > Editar.`)
        const p = { ...resp, nombre, precio_venta: precio, stock_actual: 1 }
        products.value.push(p)
        addToCart(p, 1, precio)
      }
    } catch {
      const tempProd = {
        id: Math.max(...products.value.map(p => p.id), 0) + 1,
        codigo_barras: `*MANUAL*${Date.now()}`, nombre, marca: '',
        precio_venta: precio, precio_costo: 0, stock_actual: 1,
        categoria_id: categories.value[0]?.id || 1
      }
      products.value.push(tempProd)
      addToCart(tempProd, 1, precio)
      toast.add('warning', `${nombre} creado. Stock=1. Luego de la venta quedará en 0. Ajustá stock y costo reales en Productos > Editar.`)
    }
    _processingLookup = false
    return
  }

  lookupProduct._loading = true
  lookupProduct._searched = true
  lookupProduct.id = null

  try {
    const resp = await api.post('/api/productos/lookup', { barcode: raw }).catch(() => null)
    if (resp) {
      selectProductForLookup(resp)
      if (resp.comparacion) {
        lookupBadges.value = resp.comparacion.map(c => `${c.fuente}: ${fc(c.precio)}`)
      }
    } else {
      const local = products.value.find(p => p.codigo_barras === raw)
      if (local) selectProductForLookup(local)
    }
  } catch {
    const local = products.value.find(p => p.codigo_barras === raw)
    if (local) selectProductForLookup(local)
  }

  lookupProduct._loading = false

  if (lookupProduct.id && !lookupBadges.value.some(b => b.includes(raw))) {
    lookupBadges.value.unshift(raw)
    if (lookupBadges.value.length > 10) lookupBadges.value.pop()
  }
  _processingLookup = false
}

function handlePOSInput() {
  if (posLookupCode.value.length >= 13 && !posLookupCode.value.startsWith('*')) {
    triggerPOSLookup()
  }
  lookupProduct._searched = false
  lookupProduct.id = null
}

function addToCart(product, qty = 1, price = null) {
  const unitPrice = price || product.precio_venta
  const existing = cart.items.find(i => i.producto_id === product.id && i.precio_unitario === unitPrice)

  if (existing) {
    existing.cantidad += qty
  } else {
    cart.items.push({
      producto_id: product.id,
      nombre: product.nombre,
      codigo_barras: product.codigo_barras,
      precio_unitario: unitPrice,
      cantidad: qty
    })
  }

  posLookupCode.value = ''
  lookupProduct.id = null
  lookupProduct._searched = false
  recalcCart()
}

function handlePagoKeydown(event) {
  const pagos = ['efectivo', 'debito', 'credito', 'transferencia', 'cta_corriente']
  const key = event.key
  if (key >= '1' && key <= '5') {
    event.preventDefault()
    cart.medio_pago = pagos[parseInt(key) - 1]
  } else if (key === 'ArrowLeft') {
    event.preventDefault()
    const idx = pagos.indexOf(cart.medio_pago)
    cart.medio_pago = pagos[Math.max(0, idx - 1)]
  } else if (key === 'ArrowRight') {
    event.preventDefault()
    const idx = pagos.indexOf(cart.medio_pago)
    cart.medio_pago = pagos[Math.min(pagos.length - 1, idx + 1)]
  } else if (key === 'Enter') {
    event.preventDefault()
    confirmarVenta()
  }
}

function vaciarCarrito() {
  cart.items.splice(0, cart.items.length)
  recalcCart()
  cart.descuento = 0
  cart.cliente_id = null
}

function updateCartQty(idx, qty) {
  if (qty <= 0) {
    removeFromCart(idx)
    return
  }
  cart.items[idx].cantidad = qty
  recalcCart()
}

function removeFromCart(idx) {
  cart.items.splice(idx, 1)
  recalcCart()
}

async function confirmarVenta() {
  if (!cart.items.length) return

  confirmando.value = true
  try {
    const payload = {
      items: cart.items.map(i => ({
        producto_id: i.producto_id,
        cantidad: i.cantidad,
        precio_unitario: i.precio_unitario
      })),
      descuento: cart.descuento,
      medio_pago: cart.medio_pago,
      cliente_id: cart.cliente_id
    }

    try {
      const resp = await api.post('/api/ventas', payload)
      if (resp && resp.id) {
        toast.add('success', `Venta #${resp.id} registrada`)
      } else {
        toast.add('success', 'Venta registrada (modo local)')
      }
    } catch {
      toast.add('success', 'Venta registrada (modo local)')
    }

    const ventaTotal = cart.total
    stats.ventas_hoy += ventaTotal
    stats.tickets_hoy += 1
    stats.ticket_promedio = Math.round(stats.ventas_hoy / stats.tickets_hoy)
    if (cart.medio_pago === 'efectivo') {
      stats.efectivo += ventaTotal
    }
    stats.saldo_caja += ventaTotal

    recentTransactions.value.unshift({
      id: Date.now(),
      cliente: clientes.value.find(c => c.id === cart.cliente_id)?.nombre || null,
      total: ventaTotal,
      items: cart.items.reduce((s, i) => s + i.cantidad, 0),
      medio_pago: cart.medio_pago,
      hora: new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    })
    if (recentTransactions.value.length > 20) recentTransactions.value.pop()

    // Ticket para impresión
    ticketData.numero = resp?.id ? `#${resp.id}` : `#${Date.now().toString().slice(-6)}`
    ticketData.fecha = new Date().toLocaleString('es-AR')
    ticketData.items = cart.items.map(i => ({ ...i }))
    ticketData.total = cart.total
    ticketData.descuento = cart.descuento
    ticketData.medio_pago = cart.medio_pago
    ticketData.cliente = clientes.value.find(c => c.id === cart.cliente_id)?.nombre || ''
    showTicket.value = true

    vaciarCarrito()
  } finally {
    confirmando.value = false
  }
}
</script>
