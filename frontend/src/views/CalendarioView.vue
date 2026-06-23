<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Calendario</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Resumen diario de actividad del comercio</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton
          variant="secondary"
          size="md"
          :loading="syncing"
          :disabled="syncing"
          @click="syncCalendario"
        >
          <i class="fa-solid fa-arrows-rotate"></i>
          {{ syncing ? 'Actualizando...' : 'Actualizar' }}
        </BaseButton>
        <BaseButton variant="primary" size="md">
          <i class="fa-solid fa-download text-sm"></i>
          Exportar
        </BaseButton>
      </div>
    </div>

    <BaseCard padding="md">
      <div class="flex flex-col sm:flex-row sm:items-center gap-4">
        <div class="w-full sm:w-44">
          <BaseInput
            v-model="selectedDate"
            label="Fecha"
            type="date"
          />
        </div>
        <div class="bg-slate-100 dark:bg-slate-800 p-1 rounded-xl inline-flex ml-auto">
          <BaseButton
            v-for="tab in tabs"
            :key="tab.key"
            :variant="activeTab === tab.key ? 'primary' : 'ghost'"
            size="sm"
            @click="activeTab = tab.key"
          >
            {{ tab.label }}
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-show="activeTab === 'todo' || activeTab === 'ventas'" padding="md" class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center">
            <i class="fa-solid fa-cart-shopping text-emerald-600 dark:text-emerald-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900 dark:text-white">Ventas del día</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Total</p>
          <p class="text-xl font-mono-data font-bold text-slate-900 dark:text-white">{{ formatCurrency(dailySalesTotal) }}</p>
        </div>
      </div>

      <div class="grid grid-cols-3 gap-4">
        <BaseCard padding="md" class="text-center bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-800">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Tickets</p>
          <p class="text-lg font-mono-data font-bold text-slate-900 dark:text-white">{{ dailySales.length }}</p>
        </BaseCard>
        <BaseCard padding="md" class="text-center bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-800">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Promedio</p>
          <p class="text-lg font-mono-data font-bold text-slate-900 dark:text-white">{{ formatCurrency(dailySalesAvg) }}</p>
        </BaseCard>
        <BaseCard padding="md" class="text-center bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-800">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Productos vendidos</p>
          <p class="text-lg font-mono-data font-bold text-slate-900 dark:text-white">{{ totalItemsSold }}</p>
        </BaseCard>
      </div>

      <div>
        <BaseButton variant="ghost" size="sm" @click="showSalesDetail = !showSalesDetail">
          <i class="fa-solid fa-chevron-down text-xs transition-transform" :class="showSalesDetail ? 'rotate-180' : ''"></i>
          Ver detalle de ventas
        </BaseButton>
        <div v-show="showSalesDetail" class="mt-3">
          <BaseTable
            :columns="salesColumns"
            :rows="dailySales"
            compact
            empty-icon="fa-cart-shopping"
            empty-title="Sin ventas"
            empty-text="No hay ventas registradas para esta fecha."
          >
            <template #id="{ row }">
              <span class="text-slate-700 dark:text-slate-300 font-mono-data">Ticket #{{ String(row.id).padStart(6, '0') }}</span>
            </template>
            <template #total="{ row }">
              <span class="font-mono-data font-medium text-slate-900 dark:text-white">{{ formatCurrency(row.total) }}</span>
            </template>
          </BaseTable>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-show="activeTab === 'todo' || activeTab === 'caja'" padding="md" class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
            <i class="fa-solid fa-cash-register text-amber-600 dark:text-amber-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900 dark:text-white">Movimientos de caja</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Balance</p>
          <p class="text-xl font-mono-data font-bold" :class="cashBalance >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">{{ formatCurrency(cashBalance) }}</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <BaseCard padding="md" class="text-center bg-emerald-50 dark:bg-emerald-900/20 border-emerald-100 dark:border-emerald-900/30">
          <p class="text-[10px] uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-semibold">Ingresos</p>
          <p class="text-lg font-mono-data font-bold text-emerald-700 dark:text-emerald-300">{{ formatCurrency(cashInTotal) }}</p>
        </BaseCard>
        <BaseCard padding="md" class="text-center bg-red-50 dark:bg-red-900/20 border-red-100 dark:border-red-900/30">
          <p class="text-[10px] uppercase tracking-wider text-red-500 dark:text-red-400 font-semibold">Egresos</p>
          <p class="text-lg font-mono-data font-bold text-red-600 dark:text-red-400">{{ formatCurrency(cashOutTotal) }}</p>
        </BaseCard>
      </div>

      <div>
        <BaseButton variant="ghost" size="sm" @click="showCashDetail = !showCashDetail">
          <i class="fa-solid fa-chevron-down text-xs transition-transform" :class="showCashDetail ? 'rotate-180' : ''"></i>
          Ver detalle de movimientos
        </BaseButton>
        <div v-show="showCashDetail" class="mt-3">
          <BaseTable
            :columns="cashColumns"
            :rows="cashMovements"
            compact
            empty-icon="fa-cash-register"
            empty-title="Sin movimientos"
            empty-text="No hay movimientos de caja para esta fecha."
          >
            <template #type="{ row }">
              <BaseBadge :variant="row.type === 'ingreso' ? 'success' : 'danger'" size="xs">
                <i :class="row.type === 'ingreso' ? 'fa-solid fa-circle-arrow-down' : 'fa-solid fa-circle-arrow-up'"></i>
                {{ row.type === 'ingreso' ? 'Ingreso' : 'Egreso' }}
              </BaseBadge>
            </template>
            <template #amount="{ row }">
              <span class="font-mono-data font-medium" :class="row.type === 'ingreso' ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">
                {{ row.type === 'ingreso' ? '+' : '-' }}{{ formatCurrency(row.amount) }}
              </span>
            </template>
          </BaseTable>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-show="activeTab === 'todo' || activeTab === 'compras'" padding="md" class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
            <i class="fa-solid fa-truck-fast text-blue-600 dark:text-blue-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900 dark:text-white">Compras recibidas</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="text-right">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Total compras</p>
          <p class="text-xl font-mono-data font-bold text-slate-900 dark:text-white">{{ formatCurrency(purchasesTotal) }}</p>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <BaseCard padding="md" class="text-center bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-800">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Recepciones</p>
          <p class="text-lg font-mono-data font-bold text-slate-900 dark:text-white">{{ purchases.length }}</p>
        </BaseCard>
        <BaseCard padding="md" class="text-center bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-800">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Ítems recibidos</p>
          <p class="text-lg font-mono-data font-bold text-slate-900 dark:text-white">{{ totalItemsPurchased }}</p>
        </BaseCard>
      </div>

      <div>
        <BaseButton variant="ghost" size="sm" @click="showPurchasesDetail = !showPurchasesDetail">
          <i class="fa-solid fa-chevron-down text-xs transition-transform" :class="showPurchasesDetail ? 'rotate-180' : ''"></i>
          Ver detalle de compras
        </BaseButton>
        <div v-show="showPurchasesDetail" class="mt-3">
          <BaseTable
            :columns="purchaseColumns"
            :rows="purchases"
            compact
            empty-icon="fa-truck-fast"
            empty-title="Sin compras"
            empty-text="No hay compras recibidas para esta fecha."
          >
            <template #total="{ row }">
              <span class="font-mono-data font-medium text-slate-900 dark:text-white">{{ formatCurrency(row.total) }}</span>
            </template>
          </BaseTable>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-show="activeTab === 'todo' || activeTab === 'productos'" padding="md" class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-purple-100 dark:bg-purple-900/30 flex items-center justify-center">
            <i class="fa-solid fa-boxes-stacked text-purple-600 dark:text-purple-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900 dark:text-white">Productos nuevos / modificados</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ selectedDate }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <BaseBadge variant="success" size="sm">{{ newProducts.length }} nuevos</BaseBadge>
          <BaseBadge variant="warning" size="sm">{{ modifiedProducts.length }} modificados</BaseBadge>
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold mb-2">Productos nuevos</p>
          <BaseTable
            :columns="newProductColumns"
            :rows="newProducts"
            compact
            empty-icon="fa-box"
            empty-title="Sin productos nuevos"
            empty-text="No hay productos nuevos para esta fecha."
          >
            <template #code="{ row }">
              <span class="font-mono-data text-slate-600 dark:text-slate-400 text-xs">{{ row.code }}</span>
            </template>
          </BaseTable>
        </div>
        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold mb-2">Productos modificados</p>
          <BaseTable
            :columns="modifiedProductColumns"
            :rows="modifiedProducts"
            compact
            empty-icon="fa-pen-to-square"
            empty-title="Sin modificaciones"
            empty-text="No hay productos modificados para esta fecha."
          >
            <template #change="{ row }">
              <span class="text-slate-500 dark:text-slate-400 text-xs">{{ row.change }}</span>
            </template>
          </BaseTable>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-show="activeTab === 'todo' || activeTab === 'clientes'" padding="md" class="space-y-4">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-cyan-100 dark:bg-cyan-900/30 flex items-center justify-center">
            <i class="fa-solid fa-user-plus text-cyan-600 dark:text-cyan-400"></i>
          </div>
          <div>
            <h3 class="font-semibold text-slate-900 dark:text-white">Nuevos clientes</h3>
            <p class="text-xs text-slate-500 dark:text-slate-400">{{ selectedDate }}</p>
          </div>
        </div>
        <BaseBadge variant="info" size="sm">{{ newClients.length }} registrados</BaseBadge>
      </div>

      <BaseTable
        :columns="clientColumns"
        :rows="newClients"
        compact
        empty-icon="fa-user-plus"
        empty-title="Sin nuevos clientes"
        empty-text="No hay nuevos clientes registrados para esta fecha."
      >
        <template #doc="{ row }">
          <span class="text-slate-500 dark:text-slate-400">{{ row.docType }} {{ row.docNumber }}</span>
        </template>
      </BaseTable>
    </BaseCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { formatCurrency } from '@/composables/useUtils'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const toast = useToastStore()

const syncing = ref(false)
const selectedDate = ref('2026-06-20')
const activeTab = ref('todo')
const showSalesDetail = ref(false)
const showCashDetail = ref(false)
const showPurchasesDetail = ref(false)

const tabs = [
  { key: 'todo', label: 'Todo' },
  { key: 'ventas', label: 'Ventas' },
  { key: 'caja', label: 'Caja' },
  { key: 'compras', label: 'Compras' },
  { key: 'productos', label: 'Productos' },
  { key: 'clientes', label: 'Clientes' },
]

const salesColumns = [
  { key: 'id', label: 'Ticket' },
  { key: 'time', label: 'Hora' },
  { key: 'paymentMethod', label: 'Método' },
  { key: 'total', label: 'Total', align: 'right' },
]

const cashColumns = [
  { key: 'type', label: 'Tipo' },
  { key: 'description', label: 'Descripción' },
  { key: 'time', label: 'Hora' },
  { key: 'amount', label: 'Monto', align: 'right' },
]

const purchaseColumns = [
  { key: 'supplier', label: 'Proveedor' },
  { key: 'time', label: 'Hora' },
  { key: 'items', label: 'Ítems', align: 'center' },
  { key: 'total', label: 'Total', align: 'right' },
]

const newProductColumns = [
  { key: 'name', label: 'Nombre' },
  { key: 'code', label: 'Código', align: 'right' },
]

const modifiedProductColumns = [
  { key: 'name', label: 'Nombre' },
  { key: 'change', label: 'Cambio', align: 'right' },
]

const clientColumns = [
  { key: 'name', label: 'Nombre' },
  { key: 'doc', label: 'Documento' },
  { key: 'time', label: 'Hora', align: 'right' },
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
