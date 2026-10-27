<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div>
          <p class="text-sm text-slate-500 dark:text-slate-400">Registro de actividad y cambios en el sistema</p>
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
      <div class="space-y-3">
        <div class="flex items-center gap-3 flex-wrap">
          <span class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Estado</span>
          <div class="bg-slate-100 dark:bg-slate-800 p-1 rounded-xl inline-flex gap-1">
            <BaseButton
              v-for="sf in stateFilters"
              :key="sf.key"
              :variant="activeState === sf.key ? 'primary' : 'ghost'"
              size="xs"
              @click="activeState = sf.key"
            >
              {{ sf.label }}
            </BaseButton>
          </div>
          <span class="ml-auto text-xs text-slate-500 dark:text-slate-400">
            <span class="inline-block w-2 h-2 rounded-full bg-rose-500 mr-1"></span>{{ countByEstado.sospechoso }} pendientes ·
            <span class="inline-block w-2 h-2 rounded-full bg-emerald-500 mr-1"></span>{{ countByEstado.normal }} normales ·
            <span class="inline-block w-2 h-2 rounded-full bg-slate-400 mr-1"></span>{{ countByEstado.descartado }} descartados ·
            <span class="inline-block w-2 h-2 rounded-full bg-orange-500 mr-1"></span>{{ countByEstado.fraude }} fraudes
          </span>
        </div>
        <div class="flex items-center gap-3 flex-wrap">
          <span class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Tipo</span>
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
          <div class="text-[10px] text-slate-400 dark:text-slate-500 mt-0.5">{{ timeAgo(row.creada_en || row.timestamp) }}</div>
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
            <template v-else-if="row.event === 'medio_pago_corregido'">
              <div class="space-y-0.5">
                <div>
                  <span class="line-through text-slate-400 dark:text-slate-500">{{ row.medio_pago_antes }}</span>
                  <span class="mx-1 text-slate-400">&rarr;</span>
                  <span class="font-semibold text-amber-700 dark:text-amber-400">{{ row.medio_pago }}</span>
                </div>
                <div class="text-slate-400 dark:text-slate-500 font-mono-data">{{ formatCurrency(row.total) }}</div>
              </div>
            </template>
            <template v-else-if="row.event === 'producto_manual_creado'">
              <div class="space-y-0.5">
                <div>{{ row.producto }} · <span class="font-mono-data font-semibold">{{ formatCurrency(row.total) }}</span></div>
                <div class="text-slate-400 dark:text-slate-500">{{ row.codigo_barras }} · creado por {{ row.rol_creador }}</div>
              </div>
            </template>
            <template v-else>
              <span class="truncate block" :title="row.description">{{ row.description }}</span>
            </template>
          </div>
        </template>
        <template #alert="{ row }">
          <!-- Badge de estado para eventos ya resueltos -->
          <div v-if="row.estado !== 'sospechoso'" class="flex flex-col items-center gap-0.5">
            <BaseBadge :variant="estadoBadgeVariant(row.estado)" size="xs">
              <i :class="estadoBadgeIcon(row.estado)"></i>
              {{ estadoLabel(row.estado) }}
            </BaseBadge>
            <span class="text-[9px] text-slate-400 dark:text-slate-500">{{ row.auditado_por_nombre }}</span>
          </div>
          <!-- Acciones para eventos sospechosos -->
          <div v-else class="flex items-center gap-1">
            <button
              type="button"
              :disabled="auditando === row.id"
              class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-emerald-100 dark:bg-emerald-900/40 text-emerald-600 dark:text-emerald-400 hover:bg-emerald-200 dark:hover:bg-emerald-800/60 transition disabled:opacity-50"
              title="Es normal, no pasó nada"
              @click="setEstado(row, 'normal')"
            >
              OK
            </button>
            <button
              type="button"
              :disabled="auditando === row.id"
              class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-300 dark:hover:bg-slate-600 transition disabled:opacity-50"
              title="Descartar, se verificó por cámaras"
              @click="setEstado(row, 'descartado')"
            >
              <i class="fa-solid fa-eye-slash text-[8px]"></i>
            </button>
            <button
              type="button"
              :disabled="auditando === row.id"
              class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-orange-100 dark:bg-orange-900/40 text-orange-600 dark:text-orange-400 hover:bg-orange-200 dark:hover:bg-orange-800/60 transition disabled:opacity-50"
              title="Confirmar fraude"
              @click="setEstado(row, 'fraude')"
            >
              <i class="fa-solid fa-triangle-exclamation text-[8px]"></i>
            </button>
          </div>
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
import { formatCurrency, formatDateTime, timeAgo, parseFechaUTC, esHoy } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseTable from '@/components/ui/BaseTable.vue'

const toast = useToastStore()

// Sin datos mock: si la API falla o no hay eventos, la tabla queda vacía. Antes
// el fallback mostraba 20 movimientos de demo que no existían en la base.
const logs = ref([])

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
  { key: 'Sistema', label: 'Sistema' },
]

// El backend manda tipos (`venta_confirmada`, `producto_creado`, ...) y el
// filtro de arriba habla de áreas. Sin este mapeo, cualquier filtro daba cero:
// compara `venta_confirmada === 'Ventas'`.
function categoriaDe(tipo) {
  if (!tipo) return 'Sistema'
  if (/^(venta|carrito|item_|descuento|medio_pago|cliente_telefono)/.test(tipo)) return 'Ventas'
  if (/(caja|retiro|egreso|pago_proveedor)/.test(tipo)) return 'Caja'
  if (/^(producto|revision_stock|recategorizacion|etiquetas|lote)/.test(tipo)) return 'Productos'
  if (/^cliente/.test(tipo)) return 'Clientes'
  if (/^(compra|proveedor)/.test(tipo)) return 'Compras'
  return 'Sistema'
}

const stateFilters = [
  { key: 'todo', label: 'Todos' },
  { key: 'sospechoso', label: 'Pendientes' },
  { key: 'normal', label: 'Normales' },
  { key: 'descartado', label: 'Descartados' },
  { key: 'fraude', label: 'Fraudes' },
]

const activeState = ref('todo')
const auditando = ref(null)

const countByEstado = computed(() => ({
  sospechoso: logs.value.filter(l => l.estado === 'sospechoso').length,
  normal: logs.value.filter(l => l.estado === 'normal').length,
  descartado: logs.value.filter(l => l.estado === 'descartado').length,
  fraude: logs.value.filter(l => l.estado === 'fraude').length,
}))

const suspiciousToday = computed(() =>
  logs.value.filter(l => l.estado === 'sospechoso' && l.creada_en && esHoy(l.creada_en)).length
)

const filteredLogs = computed(() => {
  let result = logs.value
  if (activeFilter.value !== 'todo') {
    result = result.filter(l => l.categoria === activeFilter.value)
  }
  if (activeState.value !== 'todo') {
    result = result.filter(l => l.estado === activeState.value)
  }
  return result
})

async function setEstado(log, estado) {
  if (auditando.value === log.id) return
  auditando.value = log.id
  try {
    // Los carritos abandonados también son filas reales ahora: este PATCH es
    // el que hace que el descarte sobreviva al refresco.
    await api.patch(`/api/auditoria/${log.id}/estado`, { estado })
    const idx = logs.value.findIndex(l => l.id === log.id)
    if (idx !== -1) logs.value[idx] = { ...logs.value[idx], estado }
    toast.success('Estado actualizado')
  } catch (e) {
    toast.error(e.message || 'Error al actualizar')
  } finally {
    auditando.value = null
  }
}

function estadoBadgeVariant(estado) {
  const map = { normal: 'success', descartado: 'default', fraude: 'danger' }
  return map[estado] || 'default'
}

function estadoBadgeIcon(estado) {
  const map = { normal: 'fa-solid fa-check', descartado: 'fa-solid fa-eye-slash', fraude: 'fa-solid fa-triangle-exclamation' }
  return map[estado] || 'fa-solid fa-question'
}

function estadoLabel(estado) {
  const map = { normal: 'Normal', descartado: 'Descartado', fraude: 'Fraude' }
  return map[estado] || estado
}

function eventEmoji(event) {
  const map = {
    carrito_abandonado: '\u26A0\uFE0F',
    item_quitado: '\u2715',
    venta_anulada: '\u2298',
    venta_editada: '\u270F\uFE0F',
    venta_confirmada: '\u2713',
    medio_pago_corregido: '\u21C4',
    producto_manual_creado: '\u270E',
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
    medio_pago_corregido: 'Medio de pago corregido',
    producto_manual_creado: 'Producto manual creado',
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
    medio_pago_corregido: 'bg-amber-100 text-amber-800',
    producto_manual_creado: 'bg-purple-100 text-purple-800',
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
  return typeMap[log.categoria] || 'bg-slate-50 text-slate-600'
}

function rowBgClass(log) {
  if (log.estado === 'fraude') return 'bg-orange-50/60 hover:bg-orange-100'
  if (log.estado === 'sospechoso') return 'bg-rose-50/40 hover:bg-rose-50'
  return 'hover:bg-slate-50'
}

async function refreshLogs() {
  syncing.value = true
  try {
    const data = await api.get('/api/auditoria')
    if (Array.isArray(data)) {
      logs.value = data.map(e => ({
        id: e.id,
        timestamp: e.created_at ? formatDateTime(e.created_at) : '',
        creada_en: e.created_at || '',
        user: e.usuario_nombre || e.user || 'Sistema',
        type: e.tipo,
        event: e.tipo,
        categoria: categoriaDe(e.tipo),
        action: e.venta_numero ? `Ticket #${e.venta_numero}` : e.tipo,
        description: typeof e.detalle === 'object' ? JSON.stringify(e.detalle) : (e.detalle || ''),
        estado: e.estado || 'sospechoso',
        auditado_por_nombre: e.auditado_por_nombre || '',
        // carrito abandonado
        items_count: e.detalle?.items || 0,
        subtotal: e.detalle?.subtotal || 0,
        abandoned_min: e.detalle?.abandonado_desde ? Math.floor((Date.now() - parseFechaUTC(e.detalle.abandonado_desde)) / 60000) : 0,
        // venta
        total: e.detalle?.total || e.detalle?.subtotal || e.detalle?.precio_venta || 0,
        medio_pago: e.detalle?.medio_pago || '',
        medio_pago_antes: e.detalle?.medio_pago_antes || '',
        total_anulado: e.detalle?.total_anulado || 0,
        // item quitado / producto manual
        producto: e.detalle?.producto || e.detalle?.nombre || '',
        codigo_barras: e.detalle?.codigo_barras || '',
        rol_creador: e.detalle?.rol || '',
        qty: e.detalle?.qty || 0,
        subtotal_change: e.detalle?.subtotal_change || 0,
      }))
    }
  } catch { /* sin red: se mantiene lo último que se pudo leer */ }
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
