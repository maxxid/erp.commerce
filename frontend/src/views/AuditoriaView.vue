<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div>
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Auditoría ERP</h1>
          <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Registro de actividad y cambios en el sistema</p>
        </div>
        <BaseBadge
          v-if="suspiciousToday"
          variant="danger"
          size="sm"
        >
          <i class="fa-solid fa-triangle-exclamation text-[10px]"></i>
          {{ suspiciousToday }} sospechoso{{ suspiciousToday !== 1 ? 's' : '' }} hoy
        </BaseBadge>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton
          :variant="autoRefresh ? 'success' : 'secondary'"
          size="sm"
          @click="toggleAutoRefresh"
        >
          <i :class="autoRefresh ? 'fa-solid fa-rotate text-emerald-600 animate-spin' : 'fa-solid fa-rotate text-slate-400'"></i>
          Auto-refrescar
        </BaseButton>
        <BaseButton
          variant="primary"
          size="sm"
          :loading="syncing"
          @click="refreshLogs"
        >
          <i v-if="!syncing" class="fa-solid fa-arrows-rotate"></i>
          {{ syncing ? 'Sincronizando...' : 'Refrescar' }}
        </BaseButton>
      </div>
    </div>

    <BaseCard padding="sm">
      <div class="flex items-center gap-3 flex-wrap">
        <span class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Filtrar por tipo</span>
        <div class="bg-slate-100 dark:bg-slate-800 p-1 rounded-xl inline-flex">
          <BaseButton
            v-for="filter in filters"
            :key="filter.key"
            :variant="activeFilter === filter.key ? 'primary' : 'ghost'"
            size="xs"
            @click="activeFilter = filter.key"
          >
            {{ filter.label }}
          </BaseButton>
        </div>
        <div class="ml-auto flex items-center gap-3">
          <BaseButton
            :variant="sinAuditar ? 'danger' : 'ghost'"
            size="xs"
            @click="sinAuditar = !sinAuditar"
          >
            <i class="fa-solid fa-clipboard-check text-[10px]"></i>
            Sin auditar
          </BaseButton>
          <span class="w-2 h-2 rounded-full bg-rose-500"></span>
          <span class="text-xs text-slate-500 dark:text-slate-400">Sin auditar: {{ suspiciousCount }}</span>
        </div>
      </div>
    </BaseCard>

    <BaseCard padding="none">
      <BaseTable
        :columns="[
          { key: 'timestamp', label: 'Timestamp' },
          { key: 'user', label: 'Usuario' },
          { key: 'event', label: 'Evento' },
          { key: 'action', label: 'Acción' },
          { key: 'detail', label: 'Detalle' },
          { key: 'alert', label: 'Alerta' }
        ]"
        :rows="filteredLogs"
        :row-class="rowBgClass"
        empty-title="Sin registros"
        empty-text="No hay registros que coincidan con los filtros seleccionados."
        empty-icon="fa-inbox"
      >
        <template #timestamp="{ row }">
          <span class="font-mono-data text-xs text-slate-600 dark:text-slate-400">{{ row.timestamp }}</span>
          <div class="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">{{ timeAgo(row.timestamp) }}</div>
        </template>
        <template #user="{ row }">
          <div class="flex items-center gap-2">
            <div class="w-6 h-6 rounded-full bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-[10px] font-semibold text-slate-500 dark:text-slate-400">
              {{ row.user?.charAt(0) || '?' }}
            </div>
            <span class="text-slate-700 dark:text-slate-300">{{ row.user }}</span>
          </div>
        </template>
        <template #event="{ row }">
          <span
            class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-medium"
            :class="eventBadgeClass(row)"
          >
            <span class="text-[10px]">{{ eventEmoji(row.event) }}</span>
            {{ eventLabel(row) }}
          </span>
        </template>
        <template #action="{ row }">
          <span class="text-slate-700 dark:text-slate-300 font-medium">{{ row.action }}</span>
        </template>
        <template #detail="{ row }">
          <div class="text-slate-600 dark:text-slate-400 text-xs max-w-xs">
            <template v-if="row.event === 'carrito_abandonado'">
              <div class="space-y-0.5">
                <div>{{ row.items_count }} items, {{ formatCurrency(row.subtotal) }} subtotal</div>
                <div class="text-slate-400 dark:text-slate-500">Sin confirmar por {{ row.abandoned_min }} min</div>
              </div>
            </template>
            <template v-else-if="row.event === 'venta_anulada'">
              <div class="space-y-0.5">
                <div>Total anulado: <span class="font-mono-data font-semibold text-red-600 dark:text-red-400">{{ formatCurrency(row.total_anulado) }}</span></div>
                <div class="text-slate-400 dark:text-slate-500">{{ row.medio_pago }}</div>
              </div>
            </template>
            <template v-else-if="row.event === 'venta_editada'">
              <div class="space-y-0.5">
                <div>Editada — total original: <span class="font-mono-data font-semibold text-amber-600 dark:text-amber-400">{{ formatCurrency(row.total_anulado) }}</span></div>
                <div class="text-slate-400 dark:text-slate-500">{{ row.medio_pago }} · Vuelta al carrito para edición</div>
              </div>
            </template>
            <template v-else-if="row.event === 'item_quitado'">
              <div class="space-y-0.5">
                <div>{{ row.producto }} &times; {{ row.qty }} <span class="text-amber-600 dark:text-amber-400 font-mono-data">&minus;{{ formatCurrency(row.subtotal_change) }}</span></div>
              </div>
            </template>
            <template v-else-if="row.event === 'venta_confirmada' && row.total">
              <div class="space-y-0.5">
                <div class="font-mono-data font-semibold text-emerald-600 dark:text-emerald-400">{{ formatCurrency(row.total) }}</div>
                <div class="text-slate-400 dark:text-slate-500">{{ row.medio_pago }}</div>
              </div>
            </template>
            <template v-else>
              <span class="truncate block" :title="row.description">{{ row.description }}</span>
            </template>
          </div>
        </template>
        <template #alert="{ row }">
          <div v-if="row.auditado" class="flex flex-col items-center gap-0.5">
            <BaseBadge variant="success" size="xs">
              <i class="fa-solid fa-check text-[10px]"></i>
              Auditado
            </BaseBadge>
            <span class="text-[9px] text-slate-400 dark:text-slate-500">{{ row.auditado_por_nombre }}</span>
          </div>
          <button
            v-else-if="isSuspicious(row) && !String(row.id).startsWith('abandon_')"
            type="button"
            :disabled="auditando === row.id"
            class="px-2 py-1 rounded-md text-[10px] font-bold bg-rose-100 dark:bg-rose-900/40 text-rose-600 dark:text-rose-400 hover:bg-rose-200 dark:hover:bg-rose-800/60 transition disabled:opacity-50"
            @click="auditarEvento(row)"
          >
            <i :class="auditando === row.id ? 'fa-solid fa-spinner fa-spin' : 'fa-solid fa-check'"></i>
            Auditar
          </button>
          <button
            v-else-if="isSuspicious(row) && String(row.id).startsWith('abandon_')"
            type="button"
            class="px-2 py-1 rounded-md text-[10px] font-bold bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600 transition"
            @click="descartarEvento(row)"
          >
            <i class="fa-solid fa-xmark"></i>
            Descartar
          </button>
          <span v-else class="text-slate-300 dark:text-slate-600 text-xs">&mdash;</span>
        </template>
      </BaseTable>
      <div class="px-5 py-3 border-t border-slate-100 dark:border-slate-800 text-sm text-slate-500 dark:text-slate-400 flex items-center justify-between">
        <span>{{ filteredLogs.length }} registros</span>
        <span class="text-xs text-slate-400 dark:text-slate-500">Última actualización: {{ lastRefresh }}</span>
      </div>
    </BaseCard>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted, onMounted } from 'vue'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseTable from '@/components/ui/BaseTable.vue'

const toast = useToastStore()

const logs = ref([
  { id: 1, timestamp: '2026-06-22 18:45:12', user: 'admin.sistema', type: 'Ventas', event: 'venta_anulada', action: 'Anulación de ticket', description: 'Ticket #001045 anulado. Motivo: error de carga.', total_anulado: 8500, medio_pago: 'Efectivo', suspicious: false },
  { id: 2, timestamp: '2026-06-22 17:30:00', user: 'maria.gomez', type: 'Caja', event: 'cierre_caja', action: 'Cierre de caja', description: 'Cierre de caja diario. Balance: $345,200. Diferencia: $0', suspicious: false },
  { id: 3, timestamp: '2026-06-22 16:15:45', user: 'carlos.lopez', type: 'Compras', event: 'registro_compra', action: 'Registro de compra', description: 'Compra registrada a Frigorífico Las Pampas por $156,800', suspicious: false },
  { id: 4, timestamp: '2026-06-22 15:40:00', user: 'cliente.anonimo', type: 'Ventas', event: 'carrito_abandonado', action: 'Carrito abandonado', description: 'Carrito con 5 items por $12,300 abandonado sin confirmar', items_count: 5, subtotal: 12300, abandoned_min: 45, suspicious: false },
  { id: 5, timestamp: '2026-06-22 15:10:22', user: 'cliente.anonimo', type: 'Ventas', event: 'item_quitado', action: 'Item quitado del carrito', description: 'Producto "Aceite girasol 1.5L" quitado del carrito activo', producto: 'Aceite girasol 1.5L', qty: 2, subtotal_change: 3200, suspicious: false },
  { id: 6, timestamp: '2026-06-22 14:22:10', user: 'admin.sistema', type: 'Productos', event: 'modificacion_precio', action: 'Modificación de precio', description: 'Producto "Leche entera 1L": precio actualizado de $1,050 a $1,134 (+8%)', suspicious: false },
  { id: 7, timestamp: '2026-06-22 14:00:00', user: 'cliente.anonimo', type: 'Ventas', event: 'carrito_creado', action: 'Carrito creado', description: 'Nuevo carrito iniciado con 1 item', items_count: 1, subtotal: 1200, suspicious: false },
  { id: 8, timestamp: '2026-06-22 13:30:18', user: 'laura.diaz', type: 'Ventas', event: 'venta_confirmada', action: 'Venta realizada', description: 'Ticket #001098 generado por $23,400. Pago: Efectivo', total: 23400, medio_pago: 'Efectivo', suspicious: false },
  { id: 9, timestamp: '2026-06-22 12:05:33', user: 'cliente.anonimo', type: 'Ventas', event: 'carrito_abandonado', action: 'Carrito abandonado', description: 'Carrito con 8 items por $18,700 abandonado sin confirmar', items_count: 8, subtotal: 18700, abandoned_min: 120, suspicious: false },
  { id: 10, timestamp: '2026-06-22 11:30:18', user: 'maria.gomez', type: 'Clientes', event: 'creacion_cliente', action: 'Creación de cliente', description: 'Nuevo cliente creado: Comercio La Amistad (CUIT 30-11223344-5)', suspicious: false },
  { id: 11, timestamp: '2026-06-22 10:15:00', user: 'admin.sistema', type: 'Caja', event: 'retiro_efectivo', action: 'Retiro de efectivo', description: 'Retiro de caja por $180,000. Concepto: transferencia bancaria', suspicious: false },
  { id: 12, timestamp: '2026-06-22 09:45:22', user: 'pedro.sanchez', type: 'Productos', event: 'ajuste_stock', action: 'Ajuste de stock', description: 'Stock de "Aceite girasol 1.5L" ajustado de 15 a 45 unidades. Diferencia: +30', suspicious: false },
  { id: 13, timestamp: '2026-06-22 09:10:00', user: 'cliente.anonimo', type: 'Ventas', event: 'item_quitado', action: 'Item quitado del carrito', description: 'Producto "Yerba mate 1kg" quitado del carrito activo', producto: 'Yerba mate 1kg', qty: 3, subtotal_change: 5700, suspicious: false },
  { id: 14, timestamp: '2026-06-22 08:05:10', user: 'carlos.lopez', type: 'Caja', event: 'apertura_caja', action: 'Apertura de caja', description: 'Apertura de caja. Monto inicial: $50,000', suspicious: false },
  { id: 15, timestamp: '2026-06-22 03:12:00', user: 'carlos.lopez', type: 'Ventas', event: 'venta_confirmada', action: 'Venta fuera de horario', description: 'WARN: Ticket #001099 generado a las 03:12 AM por $98,500 desde IP 189.45.x.x — fuera de rango horario habitual', total: 98500, medio_pago: 'Transferencia', suspicious: true },
  { id: 16, timestamp: '2026-06-21 23:00:00', user: 'admin.sistema', type: 'Sistema', event: 'backup', action: 'Backup manual', description: 'Backup manual generado. Archivo: backup_20260621_2300.zip (128 MB)', suspicious: false },
  { id: 17, timestamp: '2026-06-21 18:30:00', user: 'laura.diaz', type: 'Ventas', event: 'venta_anulada', action: 'Venta anulada luego ejecutada', description: 'WARN: Ticket #001078 anulado y re-emitido como #001079 con $2,400 menos. Posible manipulación de precio', total_anulado: 2400, medio_pago: 'Tarjeta de débito', suspicious: true },
  { id: 18, timestamp: '2026-06-21 15:45:00', user: 'maria.gomez', type: 'Clientes', event: 'modificacion_limite', action: 'Modificación de límite', description: 'Límite de crédito de "Carnicería Don Pedro" aumentado de $300,000 a $500,000', suspicious: false },
  { id: 19, timestamp: '2026-06-21 12:30:00', user: 'cliente.anonimo', type: 'Ventas', event: 'carrito_abandonado', action: 'Carrito abandonado', description: 'Carrito con 12 items por $34,500 abandonado sin confirmar', items_count: 12, subtotal: 34500, abandoned_min: 180, suspicious: false },
  { id: 20, timestamp: '2026-06-21 10:00:00', user: 'admin.sistema', type: 'Sistema', event: 'actualizacion_licencia', action: 'Actualización de licencia', description: 'Licencia LIC-A7B3-9F2C-4D8E renovada para Supermercado La Esquina', suspicious: false },
])

const activeFilter = ref('todo')
const autoRefresh = ref(false)
const syncing = ref(false)
const soloSospechosos = ref(false)
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

const sinAuditar = ref(false)
const auditando = ref(null)

function isSuspicious(log) {
  if (log.auditado) return false
  if (log.suspicious) return true
  return false
}

const suspiciousCount = computed(() => logs.value.filter(l => isSuspicious(l)).length)

async function auditarEvento(log) {
  if (auditando.value === log.id) return
  auditando.value = log.id
  try {
    await api.patch(`/api/auditoria/${log.id}/auditar`)
    const idx = logs.value.findIndex(l => l.id === log.id)
    if (idx !== -1) {
      logs.value[idx] = { ...logs.value[idx], auditado: true }
    }
    toast.success('Evento auditado')
  } catch (e) {
    toast.error(e.message || 'Error al auditar')
  }
  auditando.value = null
}

function descartarEvento(log) {
  const idx = logs.value.findIndex(l => l.id === log.id)
  if (idx !== -1) {
    logs.value[idx] = { ...logs.value[idx], suspicious: false }
  }
  toast.info('Descartado')
}

const suspiciousToday = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  return logs.value.filter(l => {
    const eventDate = l.timestamp?.slice(0, 10)
    return eventDate === today && isSuspicious(l)
  }).length
})

const filteredLogs = computed(() => {
  let result = logs.value
  if (activeFilter.value !== 'todo') {
    result = result.filter(l => l.type === activeFilter.value)
  }
  if (sinAuditar.value) {
    result = result.filter(l => isSuspicious(l) || (!l.auditado && l.suspicious))
  }
  return result
})

function eventEmoji(event) {
  const map = {
    carrito_abandonado: '\u26A0\uFE0F',
    item_quitado: '\u2715',
    venta_anulada: '\u2298',
    venta_editada: '\u270F\uFE0F',
    venta_confirmada: '\u2713',
  }
  return map[event] || ''
}

function eventLabel(log) {
  const map = {
    carrito_abandonado: 'Carrito abandonado',
    item_quitado: 'Item quitado',
    venta_anulada: 'Venta anulada',
    venta_editada: 'Venta editada',
    carrito_creado: 'Carrito creado',
    venta_confirmada: 'Venta confirmada',
  }
  return map[log.event] || log.type
}

function eventBadgeClass(log) {
  const map = {
    carrito_abandonado: 'bg-rose-100 text-rose-800',
    item_quitado: 'bg-amber-100 text-amber-800',
    venta_anulada: 'bg-rose-100 text-rose-800',
    venta_editada: 'bg-amber-100 text-amber-800',
    carrito_creado: 'bg-slate-100 text-slate-700',
    venta_confirmada: 'bg-emerald-100 text-emerald-800',
  }
  if (map[log.event]) return map[log.event]
  const typeMap = {
    Ventas: 'bg-emerald-50 text-emerald-700',
    Caja: 'bg-amber-50 text-amber-700',
    Compras: 'bg-blue-50 text-blue-700',
    Productos: 'bg-purple-50 text-purple-700',
    Clientes: 'bg-cyan-50 text-cyan-700',
    Sistema: 'bg-slate-100 text-slate-700',
  }
  return typeMap[log.type] || 'bg-slate-50 text-slate-600'
}

function rowBgClass(log) {
  if (log.event === 'carrito_abandonado' || log.event === 'venta_anulada') return 'bg-rose-100/60 hover:bg-rose-100'
  if (log.event === 'venta_editada') return 'bg-amber-100/60 hover:bg-amber-100'
  if (log.event === 'item_quitado') return 'bg-amber-100/60 hover:bg-amber-100'
  if (log.event === 'venta_confirmada') return 'bg-emerald-100/60 hover:bg-emerald-100'
  if (log.suspicious) return 'bg-rose-50/40 hover:bg-rose-50'
  return 'hover:bg-slate-50'
}

function timeAgo(ts) {
  if (!ts) return ''
  const date = new Date(ts.replace(' ', 'T'))
  const diff = Date.now() - date.getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `hace ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `hace ${hours}h`
  const days = Math.floor(hours / 24)
  return `hace ${days}d`
}

async function refreshLogs() {
  syncing.value = true
  try {
    const data = await api.get('/api/auditoria')
    if (data && data.length) {
      logs.value = data.map(e => ({
        id: e.id,
        timestamp: e.created_at ? new Date(e.created_at).toLocaleString('sv') : '',
        user: e.usuario_nombre || e.user || 'Sistema',
        type: e.tipo,
        event: e.tipo,
        action: e.venta_numero ? `Ticket #${e.venta_numero}` : e.tipo,
        description: typeof e.detalle === 'object' ? JSON.stringify(e.detalle) : (e.detalle || ''),
        suspicious: e.sospechoso || false,
        auditado: e.auditado || false,
        auditado_por_nombre: e.auditado_por_nombre || '',
        // carrito abandonado
        items_count: e.detalle?.items || 0,
        subtotal: e.detalle?.subtotal || 0,
        abandoned_min: e.detalle?.abandonado_desde ? Math.floor((Date.now() - new Date(e.detalle.abandonado_desde)) / 60000) : 0,
        // venta
        total: e.detalle?.total || e.detalle?.subtotal || 0,
        medio_pago: e.detalle?.medio_pago || '',
        total_anulado: e.detalle?.total_anulado || 0,
        // item quitado
        producto: e.detalle?.producto || '',
        qty: e.detalle?.qty || 0,
        subtotal_change: e.detalle?.subtotal_change || 0,
      }))
    }
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
