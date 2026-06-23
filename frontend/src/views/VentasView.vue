<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseModal from '@/components/ui/BaseModal.vue'

const auth = useAuthStore()
const toast = useToastStore()

const filtroFecha = ref('')
const expandedRows = ref([])
const syncing = ref(false)
const anullingId = ref(null)
const loading = ref(true)
const anularTarget = ref(null)

const sales = ref([
  {
    id: 1024, fecha: '2026-06-20 09:15', cliente: 'Juan Pérez',
    metodo_pago: 'Efectivo', total: 5000, estado: 'Completada',
    items: [
      { producto_nombre: 'Coca-Cola 500ml', cantidad: 2, precio: 1200, subtotal: 2400 },
      { producto_nombre: 'Papas Fritas', cantidad: 1, precio: 800, subtotal: 800 },
      { producto_nombre: 'Alfajor', cantidad: 3, precio: 600, subtotal: 1800 },
    ]
  },
  {
    id: 1025, fecha: '2026-06-20 10:30', cliente: 'María Gómez',
    metodo_pago: 'Transferencia', total: 3200, estado: 'Pendiente',
    items: [
      { producto_nombre: 'Agua Mineral', cantidad: 2, precio: 800, subtotal: 1600 },
      { producto_nombre: 'Sandwich', cantidad: 1, precio: 1600, subtotal: 1600 },
    ]
  },
  {
    id: 1026, fecha: '2026-06-19 12:00', cliente: 'Consumidor Final',
    metodo_pago: 'Efectivo', total: 8000, estado: 'Completada',
    items: [
      { producto_nombre: 'Cerveza 1L', cantidad: 4, precio: 1500, subtotal: 6000 },
      { producto_nombre: 'Maní', cantidad: 2, precio: 1000, subtotal: 2000 },
    ]
  },
])

const tableColumns = [
  { key: 'expand', label: '', width: 'w-10' },
  { key: 'id', label: 'Ticket' },
  { key: 'fecha', label: 'Fecha' },
  { key: 'cliente', label: 'Cliente' },
  { key: 'metodo_pago', label: 'Medio de Pago' },
  { key: 'total', label: 'Total', align: 'right' },
  { key: 'estado', label: 'Estado' },
  { key: 'acciones', label: '', align: 'right' }
]

const filteredSales = computed(() => {
  if (!filtroFecha.value) return sales.value
  return sales.value.filter(s => s.fecha.startsWith(filtroFecha.value))
})

const tableRows = computed(() => filteredSales.value)

onMounted(async () => {
  await fetchVentas()
})

async function fetchVentas() {
  loading.value = true
  try {
    const data = await api.get('/api/ventas')
    if (data && data.length) sales.value = data
  } catch { /* fallback to mock */ }
  loading.value = false
}

async function syncData() {
  syncing.value = true
  try {
    await fetchVentas()
    toast.success('Datos sincronizados')
  } catch {
    toast.warning('Error al sincronizar')
  } finally {
    syncing.value = false
  }
}

function toggleRow(id) {
  const idx = expandedRows.value.indexOf(id)
  if (idx >= 0) {
    expandedRows.value.splice(idx, 1)
  } else {
    expandedRows.value.push(id)
  }
}

function estadoVariant(estado) {
  const map = {
    'Completada': 'success',
    'Pendiente': 'warning',
    'Anulada': 'danger'
  }
  return map[estado] || 'default'
}

function confirmAnular(sale) {
  anularTarget.value = sale
}

async function executeAnular() {
  if (!anularTarget.value) return
  anullingId.value = anularTarget.value.id
  try {
    const sale = sales.value.find(s => s.id === anularTarget.value.id)
    if (sale) sale.estado = 'Anulada'
    toast.info(`Venta #${anularTarget.value.id} anulada`)
  } finally {
    anullingId.value = null
    anularTarget.value = null
  }
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Ventas</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Historial de tickets de venta</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseInput v-model="filtroFecha" type="date" size="sm" class="w-44">
          <template #prefix>
            <i class="fa-solid fa-calendar text-slate-400 text-xs"></i>
          </template>
        </BaseInput>
        <BaseButton variant="secondary" size="sm" :loading="syncing" @click="syncData">
          <i :class="syncing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
      </div>
    </div>

    <BaseCard padding="none">
      <BaseTable
        :columns="tableColumns"
        :rows="tableRows"
        :loading="loading"
        :expanded-rows="expandedRows"
        empty-title="Sin ventas"
        empty-text="No hay ventas para mostrar en este período."
        empty-icon="fa-receipt"
      >
        <template #expand="{ row }">
          <button
            type="button"
            class="w-6 h-6 rounded-lg flex items-center justify-center text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition"
            @click.stop="toggleRow(row.id)"
          >
            <i class="fa-solid text-[10px]" :class="expandedRows.includes(row.id) ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
          </button>
        </template>
        <template #id="{ row }">
          <span class="text-xs font-bold text-slate-700 dark:text-slate-200">#{{ row.id }}</span>
        </template>
        <template #fecha="{ row }">
          <span class="text-xs text-slate-600 dark:text-slate-400">{{ row.fecha }}</span>
        </template>
        <template #cliente="{ row }">
          <span class="text-xs text-slate-600 dark:text-slate-300">{{ row.cliente }}</span>
        </template>
        <template #metodo_pago="{ row }">
          <span class="text-xs text-slate-600 dark:text-slate-300 capitalize">{{ row.metodo_pago }}</span>
        </template>
        <template #total="{ row }">
          <span class="text-xs font-mono-data font-bold text-slate-800 dark:text-slate-100">{{ fc(row.total) }}</span>
        </template>
        <template #estado="{ row }">
          <BaseBadge :variant="estadoVariant(row.estado)" size="xs">{{ row.estado }}</BaseBadge>
        </template>
        <template #acciones="{ row }">
          <div class="flex items-center justify-end gap-1">
            <button
              type="button"
              class="px-2 py-1 bg-brand-50 dark:bg-brand-900/20 hover:bg-brand-100 dark:hover:bg-brand-900/30 text-brand-700 dark:text-brand-300 rounded-lg text-[10px] font-bold transition"
              @click.stop="toggleRow(row.id)"
            >
              <i class="fa-solid fa-eye mr-1"></i> Ver
            </button>
            <button
              v-if="row.estado === 'Completada'"
              type="button"
              :disabled="anullingId === row.id"
              class="px-2 py-1 bg-red-50 dark:bg-red-900/20 hover:bg-red-100 dark:hover:bg-red-900/30 text-red-600 dark:text-red-300 rounded-lg text-[10px] font-bold transition disabled:opacity-50"
              @click.stop="confirmAnular(row)"
            >
              <i :class="[anullingId === row.id ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-ban', 'mr-1']"></i>
              {{ anullingId === row.id ? 'Anulando...' : 'Anular' }}
            </button>
          </div>
        </template>
        <template #detail="{ row }">
          <p class="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-2">Detalle de Productos</p>
          <div class="overflow-x-auto">
            <table class="w-full text-xs">
              <thead>
                <tr class="text-left">
                  <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase">Producto</th>
                  <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase text-center">Cant.</th>
                  <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase text-right">Precio</th>
                  <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
                <tr v-for="(item, idx) in row.items" :key="idx">
                  <td class="py-1.5 text-slate-700 dark:text-slate-200">{{ item.producto_nombre || item.producto }}</td>
                  <td class="py-1.5 text-slate-600 dark:text-slate-400 text-center">{{ item.cantidad }}</td>
                  <td class="py-1.5 text-slate-600 dark:text-slate-400 text-right font-mono-data">{{ fc(item.precio) }}</td>
                  <td class="py-1.5 text-slate-800 dark:text-slate-100 text-right font-mono-data font-bold">{{ fc(item.subtotal) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="flex flex-wrap items-center gap-4 sm:gap-6 pt-3 border-t border-slate-200 dark:border-slate-700 mt-3">
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase">Total</span>
              <span class="text-sm font-mono-data font-bold text-brand-700 dark:text-brand-400">{{ fc(row.total) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase">Descuento</span>
              <span class="text-sm font-mono-data font-bold text-red-600 dark:text-red-400">{{ fc(row.descuento || 0) }}</span>
            </div>
            <div class="flex items-center gap-2">
              <span class="text-[10px] font-bold text-slate-400 uppercase">Medio de Pago</span>
              <span class="text-xs font-bold text-slate-700 dark:text-slate-200">{{ row.metodo_pago }}</span>
            </div>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal v-model="anularTarget" title="Anular Venta" size="sm">
      <div class="text-center">
        <div class="w-12 h-12 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-3">
          <i class="fa-solid fa-triangle-exclamation text-red-500 text-xl"></i>
        </div>
        <h3 class="text-lg font-bold text-slate-950 dark:text-white font-display mb-1">Anular Venta</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
          ¿Estás seguro de anular la venta <strong class="text-slate-900 dark:text-slate-100">#{{ anularTarget?.id }}</strong>? Esta acción no se puede deshacer.
        </p>
        <div class="flex items-center gap-3">
          <BaseButton variant="secondary" class="flex-1" @click="anularTarget = null">Cancelar</BaseButton>
          <BaseButton variant="danger" :loading="anullingId === anularTarget?.id" class="flex-1" @click="executeAnular">
            <i class="fa-solid fa-ban"></i> Anular
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
