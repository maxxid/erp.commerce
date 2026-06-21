<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Auditoría</h1>
        <p class="text-sm text-slate-500 mt-1">Registro de actividad y cambios en el sistema</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="toggleAutoRefresh"
          class="px-4 py-2.5 rounded-xl shadow-sm text-sm font-medium transition-colors flex items-center gap-2"
          :class="autoRefresh ? 'bg-green-100 text-emerald-700' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
        >
          <i :class="autoRefresh ? 'fa-solid fa-rotate text-emerald-600 animate-spin' : 'fa-solid fa-rotate text-slate-400'"></i>
          Auto-refrescar
        </button>
        <button
          @click="refreshLogs"
          :disabled="syncing"
          class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-2xl shadow-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Refrescar' }}
        </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm p-5">
      <div class="flex items-center gap-3 flex-wrap">
        <span class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Filtrar por tipo</span>
        <button
          v-for="filter in filters"
          :key="filter.key"
          @click="activeFilter = filter.key"
          class="px-3.5 py-1.5 rounded-lg text-xs font-medium transition-colors"
          :class="activeFilter === filter.key ? 'bg-brand-600 text-white shadow-sm' : 'text-slate-500 hover:bg-slate-100'"
        >
          {{ filter.label }}
        </button>
        <div class="ml-auto flex items-center gap-2">
          <span class="w-2 h-2 rounded-full bg-rose-500"></span>
          <span class="text-xs text-slate-500">Actividad sospechosa: {{ suspiciousCount }}</span>
        </div>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Timestamp</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Usuario</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Tipo</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Acción</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Descripción</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Alerta</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr
              v-for="log in filteredLogs"
              :key="log.id"
              class="hover:bg-slate-50 transition-colors"
              :class="log.suspicious ? 'bg-rose-50/40' : ''"
            >
              <td class="px-5 py-3 font-mono-data text-xs text-slate-600">{{ log.timestamp }}</td>
              <td class="px-5 py-3">
                <div class="flex items-center gap-2">
                  <div class="w-6 h-6 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-semibold text-slate-500">
                    {{ log.user.charAt(0) }}
                  </div>
                  <span class="text-slate-700">{{ log.user }}</span>
                </div>
              </td>
              <td class="px-5 py-3">
                <span
                  class="inline-flex px-2 py-0.5 rounded-md text-xs font-medium"
                  :class="typeClass(log.type)"
                >
                  {{ log.type }}
                </span>
              </td>
              <td class="px-5 py-3 text-slate-700 font-medium">{{ log.action }}</td>
              <td class="px-5 py-3 text-slate-600 text-xs max-w-xs truncate" :title="log.description">{{ log.description }}</td>
              <td class="px-5 py-3">
                <span v-if="log.suspicious" class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium bg-red-100 text-rose-700">
                  <i class="fa-solid fa-triangle-exclamation text-[10px]"></i>
                  Sospechoso
                </span>
                <span v-else class="text-slate-300 text-xs">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="px-5 py-3 border-t border-slate-100 text-sm text-slate-500 flex items-center justify-between">
        <span>{{ filteredLogs.length }} registros</span>
        <span class="text-xs text-slate-400">Última actualización: {{ lastRefresh }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, onMounted, watch } from 'vue'
import api from '@/services/api'
import { formatCurrency } from '@/composables/useUtils'

const logs = ref([
  { id: 1, timestamp: '2026-06-20 18:45:12', user: 'admin.sistema', type: 'Ventas', action: 'Anulación de ticket', description: 'Ticket #001045 anulado. Motivo: error de carga. Monto revertido: $8,500', suspicious: false },
  { id: 2, timestamp: '2026-06-20 17:30:00', user: 'maria.gomez', type: 'Caja', action: 'Cierre de caja', description: 'Cierre de caja diario. Balance: $345,200. Diferencia: $0', suspicious: false },
  { id: 3, timestamp: '2026-06-20 16:15:45', user: 'carlos.lopez', type: 'Compras', action: 'Registro de compra', description: 'Compra registrada a Frigorífico Las Pampas por $156,800', suspicious: false },
  { id: 4, timestamp: '2026-06-20 14:22:10', user: 'admin.sistema', type: 'Productos', action: 'Modificación de precio', description: 'Producto "Leche entera 1L": precio actualizado de $1,050 a $1,134 (+8%)', suspicious: false },
  { id: 5, timestamp: '2026-06-20 12:05:33', user: 'laura.diaz', type: 'Ventas', action: 'Venta realizada', description: 'Ticket #001098 generado por $23,400. Pago: Efectivo', suspicious: false },
  { id: 6, timestamp: '2026-06-20 11:30:18', user: 'maria.gomez', type: 'Clientes', action: 'Creación de cliente', description: 'Nuevo cliente creado: Comercio La Amistad (CUIT 30-11223344-5)', suspicious: false },
  { id: 7, timestamp: '2026-06-20 10:15:00', user: 'admin.sistema', type: 'Caja', action: 'Retiro de efectivo', description: 'Retiro de caja por $180,000. Concepto: transferencia bancaria', suspicious: false },
  { id: 8, timestamp: '2026-06-20 09:45:22', user: 'pedro.sanchez', type: 'Productos', action: 'Ajuste de stock', description: 'Stock de "Aceite girasol 1.5L" ajustado de 15 a 45 unidades. Diferencia: +30', suspicious: false },
  { id: 9, timestamp: '2026-06-20 08:05:10', user: 'carlos.lopez', type: 'Caja', action: 'Apertura de caja', description: 'Apertura de caja. Monto inicial: $50,000', suspicious: false },
  { id: 10, timestamp: '2026-06-20 03:12:00', user: 'carlos.lopez', type: 'Ventas', action: 'Venta fuera de horario', description: 'WARN: Ticket #001099 generado a las 03:12 AM por $98,500 desde IP 189.45.x.x — fuera de rango horario habitual', suspicious: true },
  { id: 11, timestamp: '2026-06-19 23:00:00', user: 'admin.sistema', type: 'Sistema', action: 'Backup manual', description: 'Backup manual generado. Archivo: backup_20260619_2300.zip (128 MB)', suspicious: false },
  { id: 12, timestamp: '2026-06-19 18:30:00', user: 'laura.diaz', type: 'Ventas', action: 'Venta anulada luego ejecutada', description: 'WARN: Ticket #001078 anulado y re-emitido como #001079 con $2,400 menos. Posible manipulación de precio', suspicious: true },
  { id: 13, timestamp: '2026-06-19 15:45:00', user: 'maria.gomez', type: 'Clientes', action: 'Modificación de límite', description: 'Límite de crédito de "Carnicería Don Pedro" aumentado de $300,000 a $500,000', suspicious: false },
  { id: 14, timestamp: '2026-06-19 10:00:00', user: 'admin.sistema', type: 'Sistema', action: 'Actualización de licencia', description: 'Licencia LIC-A7B3-9F2C-4D8E renovada para Supermercado La Esquina', suspicious: false },
])

const activeFilter = ref('todo')
const autoRefresh = ref(false)
const syncing = ref(false)
const lastRefresh = ref(new Date().toLocaleTimeString())
let refreshInterval = null

const filters = [
  { key: 'todo', label: 'Todo' },
  { key: 'Ventas', label: 'Ventas' },
  { key: 'Caja', label: 'Caja' },
  { key: 'Compras', label: 'Compras' },
  { key: 'Productos', label: 'Productos' },
  { key: 'Clientes', label: 'Clientes' },
]

const suspiciousCount = computed(() => logs.value.filter(l => l.suspicious).length)

const filteredLogs = computed(() => {
  if (activeFilter.value === 'todo') return logs.value
  return logs.value.filter(l => l.type === activeFilter.value)
})

function typeClass(type) {
  const map = {
    Ventas: 'bg-emerald-50 text-emerald-700',
    Caja: 'bg-amber-50 text-amber-700',
    Compras: 'bg-blue-50 text-blue-700',
    Productos: 'bg-purple-50 text-purple-700',
    Clientes: 'bg-cyan-50 text-cyan-700',
    Sistema: 'bg-slate-100 text-slate-700',
  }
  return map[type] || 'bg-slate-50 text-slate-600'
}

async function refreshLogs() {
  syncing.value = true
  try {
    const data = await api.get('/api/auditoria')
    if (data && data.length) logs.value = data
  } catch { /* fallback to mock */ }
  lastRefresh.value = new Date().toLocaleTimeString()
  syncing.value = false
}

function toggleAutoRefresh() {
  autoRefresh.value = !autoRefresh.value
  if (autoRefresh.value) {
    refreshInterval = setInterval(refreshLogs, 30000)
  } else if (refreshInterval) {
    clearInterval(refreshInterval)
  }
}

onMounted(() => { refreshLogs() })

onUnmounted(() => {
  if (refreshInterval) clearInterval(refreshInterval)
})
</script>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1.5s linear infinite;
}
</style>
