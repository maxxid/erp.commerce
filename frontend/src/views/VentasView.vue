<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Ventas</h2>
        <p class="text-sm text-slate-500 mt-1">Historial de tickets de venta</p>
      </div>
      <div class="flex items-center gap-2">
        <div class="relative">
          <i class="fa-solid fa-calendar absolute left-4 top-3 text-slate-400 text-xs"></i>
          <input v-model="filtroFecha" type="date"
                 class="bg-white border border-slate-200 rounded-xl pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600">
        </div>
        <button :disabled="syncing" @click="syncData"
                class="px-3 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition shadow-sm">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </button>
      </div>
    </div>

    <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-slate-50 text-left">
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase w-8"></th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Ticket</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Fecha</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Cliente</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Medio de Pago</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Total</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Estado</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <template v-for="sale in filteredSales" :key="sale.id">
              <tr @click="toggleRow(sale.id)" class="hover:bg-slate-50 transition cursor-pointer">
                <td class="px-5 py-3 text-xs text-slate-400">
                  <i class="fa-solid text-[10px]" :class="expandedRows.includes(sale.id) ? 'fa-chevron-down' : 'fa-chevron-right'"></i>
                </td>
                <td class="px-5 py-3 text-xs font-bold text-slate-700">#{{ sale.id }}</td>
                <td class="px-5 py-3 text-xs text-slate-600">{{ sale.fecha }}</td>
                <td class="px-5 py-3 text-xs text-slate-600">{{ sale.cliente }}</td>
                <td class="px-5 py-3 text-xs text-slate-600">{{ sale.metodo_pago }}</td>
                <td class="px-5 py-3 text-xs font-mono-data font-bold text-slate-800">{{ fc(sale.total) }}</td>
                <td class="px-5 py-3">
                  <span :class="estadoClass(sale.estado)"
                        class="px-2 py-0.5 rounded-lg text-[10px] font-bold">
                    {{ sale.estado }}
                  </span>
                </td>
                <td class="px-5 py-3">
                  <div class="flex items-center gap-1">
                    <button v-if="sale.estado === 'Pendiente'"
                            :disabled="anullingId === sale.id"
                            @click.stop="anularVenta(sale)"
                            class="px-2 py-1 bg-rose-50 hover:bg-rose-100 text-rose-600 rounded-lg text-[10px] font-bold transition">
                      <i :class="[anullingId === sale.id ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-ban', 'mr-1']"></i> {{ anullingId === sale.id ? 'Anulando...' : 'Anular' }}
                    </button>
                    <span v-else class="text-[10px] text-slate-300">—</span>
                  </div>
                </td>
              </tr>
              <tr v-if="expandedRows.includes(sale.id)" class="bg-slate-50/50">
                <td colspan="8" class="px-5 py-4">
                  <div class="space-y-2">
                    <p class="text-[10px] font-bold text-slate-400 uppercase">Detalle de Productos</p>
                    <table class="w-full text-xs">
                      <thead>
                        <tr class="text-left">
                          <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase">Producto</th>
                          <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase text-center">Cant.</th>
                          <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase text-right">Precio</th>
                          <th class="py-1.5 text-[10px] font-bold text-slate-400 uppercase text-right">Subtotal</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="(item, idx) in sale.items" :key="idx" class="border-t border-slate-100">
                          <td class="py-1.5 text-slate-700">{{ item.producto }}</td>
                          <td class="py-1.5 text-slate-600 text-center">{{ item.cantidad }}</td>
                          <td class="py-1.5 text-slate-600 text-right font-mono-data">{{ fc(item.precio) }}</td>
                          <td class="py-1.5 text-slate-800 text-right font-mono-data font-bold">{{ fc(item.subtotal) }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
            <tr v-if="!filteredSales.length">
              <td colspan="8" class="px-5 py-8 text-xs text-slate-400 text-center">Sin ventas que mostrar</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'

const auth = useAuthStore()
const toast = useToastStore()

const filtroFecha = ref('')
const expandedRows = ref([])
const syncing = ref(false)
const anullingId = ref(null)

const sales = ref([
  {
    id: 1024, fecha: '2026-06-20 09:15', cliente: 'Juan Pérez',
    metodo_pago: 'Efectivo', total: 5000, estado: 'Completada',
    items: [
      { producto: 'Coca-Cola 500ml', cantidad: 2, precio: 1200, subtotal: 2400 },
      { producto: 'Papas Fritas', cantidad: 1, precio: 800, subtotal: 800 },
      { producto: 'Alfajor', cantidad: 3, precio: 600, subtotal: 1800 },
    ]
  },
  {
    id: 1025, fecha: '2026-06-20 10:30', cliente: 'María Gómez',
    metodo_pago: 'Transferencia', total: 3200, estado: 'Pendiente',
    items: [
      { producto: 'Agua Mineral', cantidad: 2, precio: 800, subtotal: 1600 },
      { producto: 'Sandwich', cantidad: 1, precio: 1600, subtotal: 1600 },
    ]
  },
  {
    id: 1026, fecha: '2026-06-19 12:00', cliente: 'Consumidor Final',
    metodo_pago: 'Efectivo', total: 8000, estado: 'Completada',
    items: [
      { producto: 'Cerveza 1L', cantidad: 4, precio: 1500, subtotal: 6000 },
      { producto: 'Maní', cantidad: 2, precio: 1000, subtotal: 2000 },
    ]
  },
])

const filteredSales = computed(() => {
  if (!filtroFecha.value) return sales.value
  return sales.value.filter(s => s.fecha.startsWith(filtroFecha.value))
})

onMounted(async () => {
  await fetchVentas()
})

async function fetchVentas() {
  try {
    const data = await api.get('/api/ventas')
    if (data && data.length) sales.value = data
  } catch { /* fallback to mock */ }
}

async function syncData() {
  syncing.value = true
  try {
    await fetchVentas()
    toast.add('success', 'Datos sincronizados')
  } catch {
    toast.add('warning', 'Error al sincronizar')
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

function estadoClass(estado) {
  const map = {
    'Completada': 'bg-emerald-50 text-emerald-700',
    'Pendiente': 'bg-amber-50 text-amber-700',
    'Anulada': 'bg-rose-50 text-rose-700',
  }
  return map[estado] || 'bg-slate-50 text-slate-600'
}

async function anularVenta(sale) {
  anullingId.value = sale.id
  try {
    sale.estado = 'Anulada'
    toast.add('info', `Venta #${sale.id} anulada`)
  } finally {
    anullingId.value = null
  }
}
</script>
