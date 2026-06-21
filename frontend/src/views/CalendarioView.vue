<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Calendario</h1>
        <p class="text-sm text-slate-500 mt-1">Resumen diario de actividad del comercio</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          :disabled="syncing"
          @click="syncCalendario"
          class="bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm disabled:opacity-60"
          title="Actualizar datos"
        >
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-sync'"></i>
          {{ syncing ? 'Actualizando...' : 'Actualizar' }}
        </button>
        <button class="bg-white border border-slate-300 rounded-xl px-4 py-2.5 text-sm hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm">
          <i class="fa-solid fa-download text-slate-500"></i>
          Exportar
        </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm p-5">
      <div class="flex items-center gap-4">
        <label class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Fecha</label>
        <input
          v-model="selectedDate"
          type="date"
          class="border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all"
        />
        <div class="flex items-center gap-1.5 ml-auto">
          <button
            v-for="tab in tabs"
            :key="tab.key"
            @click="activeTab = tab.key"
            class="px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
            :class="activeTab === tab.key ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'"
          >
            {{ tab.label }}
          </button>
        </div>
      </div>
    </div>

    <div v-show="activeTab === 'todo' || activeTab === 'ventas'" class="bg-white rounded-2xl shadow-sm p-5">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-emerald-100 flex items-center justify-center">
            <i class="fa-solid fa-cart-shopping text-emerald-600"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900">Ventas del día</h3>
            <p class="text-xs text-slate-500">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Total</p>
          <p class="text-xl font-mono-data font-bold text-slate-900">{{ formatCurrency(dailySalesTotal) }}</p>
        </div>
      </div>
      <div class="grid grid-cols-3 gap-4 mb-4">
        <div class="bg-slate-50 rounded-xl p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Tickets</p>
          <p class="text-lg font-mono-data font-bold text-slate-900">{{ dailySales.length }}</p>
        </div>
        <div class="bg-slate-50 rounded-xl p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Promedio</p>
          <p class="text-lg font-mono-data font-bold text-slate-900">{{ formatCurrency(dailySalesAvg) }}</p>
        </div>
        <div class="bg-slate-50 rounded-xl p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Productos vendidos</p>
          <p class="text-lg font-mono-data font-bold text-slate-900">{{ totalItemsSold }}</p>
        </div>
      </div>
      <details class="group">
        <summary class="cursor-pointer text-sm font-medium text-brand-600 hover:text-brand-700 transition-colors flex items-center gap-1.5">
          <i class="fa-solid fa-chevron-down text-xs group-open:rotate-180 transition-transform"></i>
          Ver detalle de ventas
        </summary>
        <div class="mt-3 space-y-2">
          <div v-for="sale in dailySales" :key="sale.id" class="flex items-center justify-between px-4 py-2.5 bg-slate-50 rounded-xl text-sm">
            <span class="text-slate-700 font-mono-data">Ticket #{{ String(sale.id).padStart(6, '0') }}</span>
            <span class="text-slate-500">{{ sale.time }}</span>
            <span class="text-slate-500">{{ sale.paymentMethod }}</span>
            <span class="font-mono-data font-medium text-slate-900">{{ formatCurrency(sale.total) }}</span>
          </div>
        </div>
      </details>
    </div>

    <div v-show="activeTab === 'todo' || activeTab === 'caja'" class="bg-white rounded-2xl shadow-sm p-5">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-amber-100 flex items-center justify-center">
            <i class="fa-solid fa-cash-register text-amber-600"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900">Movimientos de caja</h3>
            <p class="text-xs text-slate-500">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Balance</p>
          <p class="text-xl font-mono-data font-bold" :class="cashBalance >= 0 ? 'text-emerald-600' : 'text-red-600'">{{ formatCurrency(cashBalance) }}</p>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 mb-4">
        <div class="bg-emerald-50 rounded-xl p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-emerald-600 font-semibold">Ingresos</p>
          <p class="text-lg font-mono-data font-bold text-emerald-700">{{ formatCurrency(cashInTotal) }}</p>
        </div>
        <div class="bg-rose-50 rounded-xl p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-red-500 font-semibold">Egresos</p>
          <p class="text-lg font-mono-data font-bold text-red-600">{{ formatCurrency(cashOutTotal) }}</p>
        </div>
      </div>
      <details class="group">
        <summary class="cursor-pointer text-sm font-medium text-brand-600 hover:text-brand-700 transition-colors flex items-center gap-1.5">
          <i class="fa-solid fa-chevron-down text-xs group-open:rotate-180 transition-transform"></i>
          Ver detalle de movimientos
        </summary>
        <div class="mt-3 space-y-2">
          <div v-for="mov in cashMovements" :key="mov.id" class="flex items-center justify-between px-4 py-2.5 bg-slate-50 rounded-xl text-sm">
            <div class="flex items-center gap-2">
              <span :class="mov.type === 'ingreso' ? 'text-emerald-600' : 'text-red-600'">
                <i :class="mov.type === 'ingreso' ? 'fa-solid fa-circle-arrow-down' : 'fa-solid fa-circle-arrow-up'"></i>
              </span>
              <span class="text-slate-700">{{ mov.description }}</span>
            </div>
            <span class="text-slate-500 text-xs">{{ mov.time }}</span>
            <span class="font-mono-data font-medium" :class="mov.type === 'ingreso' ? 'text-emerald-600' : 'text-red-600'">{{ mov.type === 'ingreso' ? '+' : '-' }}{{ formatCurrency(mov.amount) }}</span>
          </div>
        </div>
      </details>
    </div>

    <div v-show="activeTab === 'todo' || activeTab === 'compras'" class="bg-white rounded-2xl shadow-sm p-5">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-blue-100 flex items-center justify-center">
            <i class="fa-solid fa-truck-fast text-blue-600"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900">Compras recibidas</h3>
            <p class="text-xs text-slate-500">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Total compras</p>
          <p class="text-xl font-mono-data font-bold text-slate-900">{{ formatCurrency(purchasesTotal) }}</p>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4 mb-4">
        <div class="bg-slate-50 rounded-xl p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Recepciones</p>
          <p class="text-lg font-mono-data font-bold text-slate-900">{{ purchases.length }}</p>
        </div>
        <div class="bg-slate-50 rounded-xl p-4 text-center">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ítems recibidos</p>
          <p class="text-lg font-mono-data font-bold text-slate-900">{{ totalItemsPurchased }}</p>
        </div>
      </div>
      <details class="group">
        <summary class="cursor-pointer text-sm font-medium text-brand-600 hover:text-brand-700 transition-colors flex items-center gap-1.5">
          <i class="fa-solid fa-chevron-down text-xs group-open:rotate-180 transition-transform"></i>
          Ver detalle de compras
        </summary>
        <div class="mt-3 space-y-2">
          <div v-for="purchase in purchases" :key="purchase.id" class="flex items-center justify-between px-4 py-2.5 bg-slate-50 rounded-xl text-sm">
            <span class="text-slate-700">{{ purchase.supplier }}</span>
            <span class="text-slate-500 text-xs">{{ purchase.time }}</span>
            <span class="text-slate-500">{{ purchase.items }} items</span>
            <span class="font-mono-data font-medium text-slate-900">{{ formatCurrency(purchase.total) }}</span>
          </div>
        </div>
      </details>
    </div>

    <div v-show="activeTab === 'todo' || activeTab === 'productos'" class="bg-white rounded-2xl shadow-sm p-5">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-purple-100 flex items-center justify-center">
            <i class="fa-solid fa-boxes-stacked text-purple-600"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900">Productos nuevos / modificados</h3>
            <p class="text-xs text-slate-500">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="flex items-center gap-3">
          <span class="px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-emerald-700">{{ newProducts.length }} nuevos</span>
          <span class="px-3 py-1 rounded-full text-xs font-medium bg-amber-100 text-amber-700">{{ modifiedProducts.length }} modificados</span>
        </div>
      </div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Productos nuevos</p>
          <div class="space-y-1.5">
            <div v-for="prod in newProducts" :key="prod.id" class="flex items-center justify-between px-3 py-2 bg-emerald-50 rounded-lg text-sm">
              <span class="text-slate-800">{{ prod.name }}</span>
              <span class="font-mono-data text-slate-600 text-xs">{{ prod.code }}</span>
            </div>
          </div>
        </div>
        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Productos modificados</p>
          <div class="space-y-1.5">
            <div v-for="prod in modifiedProducts" :key="prod.id" class="flex items-center justify-between px-3 py-2 bg-amber-50 rounded-lg text-sm">
              <span class="text-slate-800">{{ prod.name }}</span>
              <span class="text-slate-500 text-xs">{{ prod.change }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-show="activeTab === 'todo' || activeTab === 'clientes'" class="bg-white rounded-2xl shadow-sm p-5">
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-cyan-100 flex items-center justify-center">
            <i class="fa-solid fa-user-plus text-cyan-600"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900">Nuevos clientes</h3>
            <p class="text-xs text-slate-500">{{ selectedDate }}</p>
          </div>
        </div>
        <span class="px-3 py-1 rounded-full text-xs font-medium bg-cyan-100 text-cyan-700">{{ newClients.length }} registrados</span>
      </div>
      <div class="space-y-1.5" v-if="newClients.length > 0">
        <div v-for="client in newClients" :key="client.id" class="flex items-center justify-between px-4 py-2.5 bg-cyan-50 rounded-xl text-sm">
          <span class="text-slate-800 font-medium">{{ client.name }}</span>
          <span class="text-slate-500">{{ client.docType }} {{ client.docNumber }}</span>
          <span class="text-slate-400 text-xs">{{ client.time }}</span>
        </div>
      </div>
      <div v-else class="text-center py-6 text-slate-400 text-sm">
        Sin nuevos clientes en esta fecha
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { formatCurrency } from '@/composables/useUtils'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'

const toast = useToastStore()

const syncing = ref(false)
const selectedDate = ref('2026-06-20')
const activeTab = ref('todo')

const tabs = [
  { key: 'todo', label: 'Todo' },
  { key: 'ventas', label: 'Ventas' },
  { key: 'caja', label: 'Caja' },
  { key: 'compras', label: 'Compras' },
  { key: 'productos', label: 'Productos' },
  { key: 'clientes', label: 'Clientes' },
]

onMounted(async () => {
  try {
    const data = await api.get(`/api/calendario/dia?fecha=${selectedDate.value}`)
    if (data) {
      if (data.dailySales) dailySales.value = data.dailySales
      if (data.cashMovements) cashMovements.value = data.cashMovements
      if (data.purchases) purchases.value = data.purchases
      if (data.newProducts) newProducts.value = data.newProducts
      if (data.modifiedProducts) modifiedProducts.value = data.modifiedProducts
      if (data.newClients) newClients.value = data.newClients
    }
  } catch { /* fallback to mock */ }
})

async function syncCalendario() {
  syncing.value = true
  try {
    const data = await api.get(`/api/calendario/dia?fecha=${selectedDate.value}`)
    if (data) {
      if (data.dailySales) dailySales.value = data.dailySales
      if (data.cashMovements) cashMovements.value = data.cashMovements
      if (data.purchases) purchases.value = data.purchases
      if (data.newProducts) newProducts.value = data.newProducts
      if (data.modifiedProducts) modifiedProducts.value = data.modifiedProducts
      if (data.newClients) newClients.value = data.newClients
    }
  } catch { /* fallback to mock */ }
  syncing.value = false
}

const dailySales = ref([
  { id: 1102, time: '08:15', paymentMethod: 'Efectivo', total: 12500 },
  { id: 1103, time: '09:30', paymentMethod: 'Transferencia', total: 34200 },
  { id: 1104, time: '10:45', paymentMethod: 'Efectivo', total: 8750 },
  { id: 1105, time: '12:00', paymentMethod: 'Crédito', total: 56300 },
  { id: 1106, time: '14:20', paymentMethod: 'Efectivo', total: 19200 },
  { id: 1107, time: '16:10', paymentMethod: 'Débito', total: 41000 },
  { id: 1108, time: '18:45', paymentMethod: 'Transferencia', total: 28900 },
])

const dailySalesTotal = computed(() => dailySales.value.reduce((sum, s) => sum + s.total, 0))
const dailySalesAvg = computed(() => dailySales.value.length ? Math.round(dailySalesTotal.value / dailySales.value.length) : 0)
const totalItemsSold = computed(() => dailySales.value.length * 8)

const cashMovements = ref([
  { id: 1, type: 'ingreso', description: 'Apertura de caja', time: '08:00', amount: 50000 },
  { id: 2, type: 'egreso', description: 'Pago a proveedor', time: '09:15', amount: 32000 },
  { id: 3, type: 'ingreso', description: 'Ventas efectivo mañana', time: '12:00', amount: 48750 },
  { id: 4, type: 'egreso', description: 'Servicio de limpieza', time: '14:00', amount: 8500 },
  { id: 5, type: 'ingreso', description: 'Ventas efectivo tarde', time: '18:00', amount: 61200 },
  { id: 6, type: 'ingreso', description: 'Recarga sube', time: '19:30', amount: 3000 },
])

const cashInTotal = computed(() => cashMovements.value.filter(m => m.type === 'ingreso').reduce((s, m) => s + m.amount, 0))
const cashOutTotal = computed(() => cashMovements.value.filter(m => m.type === 'egreso').reduce((s, m) => s + m.amount, 0))
const cashBalance = computed(() => cashInTotal.value - cashOutTotal.value)

const purchases = ref([
  { id: 1, supplier: 'Frigorífico Las Pampas', time: '07:30', items: 34, total: 156800 },
  { id: 2, supplier: 'Lácteos Santa Rosa', time: '10:00', items: 18, total: 43200 },
  { id: 3, supplier: 'Panificadora El Trigo', time: '15:00', items: 45, total: 28750 },
])

const purchasesTotal = computed(() => purchases.value.reduce((s, p) => s + p.total, 0))
const totalItemsPurchased = computed(() => purchases.value.reduce((s, p) => s + p.items, 0))

const newProducts = ref([
  { id: 1, name: 'Queso crema light 200g', code: 'PROD-8921', price: 2450 },
  { id: 2, name: 'Yerba mate orgánica 1kg', code: 'PROD-8922', price: 3890 },
  { id: 3, name: 'Galletitas integrales sésamo', code: 'PROD-8923', price: 1680 },
])

const modifiedProducts = ref([
  { id: 4, name: 'Leche entera 1L', change: 'Precio +8%' },
  { id: 5, name: 'Pan lactal 500g', change: 'Stock ajustado' },
])

const newClients = ref([
  { id: 1, name: 'Comercio La Amistad', docType: 'CUIT', docNumber: '30-11223344-5', time: '11:30' },
  { id: 2, name: 'Juan Carlos Ríos', docType: 'DNI', docNumber: '31.223.445', time: '16:45' },
])
</script>
