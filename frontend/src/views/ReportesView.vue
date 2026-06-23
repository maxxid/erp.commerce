<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Reportes</h1>
        <p class="text-sm text-slate-500 mt-1">Análisis de ventas y rendimiento por período</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton
          variant="secondary"
          size="md"
          :loading="syncing"
          :disabled="syncing"
          @click="syncAll"
        >
          <i class="fa-solid fa-arrows-rotate"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar todo' }}
        </BaseButton>
        <BaseButton variant="primary" size="md">
          <i class="fa-solid fa-file-pdf text-sm"></i>
          Exportar todo
        </BaseButton>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- ==================== SEMANAL ==================== -->
      <BaseCard class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
              <i class="fa-solid fa-calendar-week text-indigo-600 text-sm"></i>
            </div>
            <h2 class="font-semibold text-slate-900">Semanal</h2>
          </div>
          <BaseButton
            variant="ghost"
            size="xs"
            icon-only
            title="Sincronizar semanal"
            aria-label="Sincronizar semanal"
            :loading="syncingWeekly"
            :disabled="syncingWeekly"
            @click="syncWeekly"
          >
            <i class="fa-solid fa-arrows-rotate text-xs"></i>
          </BaseButton>
        </div>

        <div class="space-y-2">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-slate-900">{{ formatCurrency(weekly.total) }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">vs semana anterior</span>
            <BaseBadge :variant="weekly.change >= 0 ? 'success' : 'danger'" size="sm">
              <i :class="weekly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(weekly.change) }}%
            </BaseBadge>
          </div>
        </div>

        <div v-if="weeklyBars.length" class="flex items-end gap-1" style="height: 130px;">
          <div
            v-for="(item, idx) in weeklyBars" :key="idx"
            class="flex-1 flex flex-col items-center gap-1 min-w-0"
          >
            <span class="text-[10px] font-mono-data text-slate-500 font-medium leading-none text-center">
              {{ item.ventas > 0 ? formatCurrency(item.ventas) : '' }}
            </span>
            <div
              class="w-full bg-brand-500 rounded-t-md transition-all duration-500 ease-out hover:bg-brand-600 cursor-default"
              :style="{ height: weeklyMax > 0 ? Math.max((item.ventas / weeklyMax) * 96, item.ventas > 0 ? 4 : 0) + 'px' : '0px' }"
            ></div>
            <span class="text-[10px] text-slate-500 font-medium">{{ item.dia }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          icon="fa-chart-bar"
          title="Sin datos para esta semana"
          text=""
          compact
        />

        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in weekly.topProducts.slice(0, 5)" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-slate-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-slate-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
          <p v-if="!weekly.topProducts.length" class="text-xs text-slate-400">Sin datos</p>
        </div>
      </BaseCard>

      <!-- ==================== MENSUAL ==================== -->
      <BaseCard class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
              <i class="fa-solid fa-calendar-check text-emerald-600 text-sm"></i>
            </div>
            <h2 class="font-semibold text-slate-900">Mensual</h2>
          </div>
          <BaseButton
            variant="ghost"
            size="xs"
            icon-only
            title="Sincronizar mensual"
            aria-label="Sincronizar mensual"
            :loading="syncingMonthly"
            :disabled="syncingMonthly"
            @click="syncMonthly"
          >
            <i class="fa-solid fa-arrows-rotate text-xs"></i>
          </BaseButton>
        </div>

        <div class="space-y-2">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-slate-900">{{ formatCurrency(monthly.total) }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">vs mes anterior</span>
            <BaseBadge :variant="monthly.change >= 0 ? 'success' : 'danger'" size="sm">
              <i :class="monthly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(monthly.change) }}%
            </BaseBadge>
          </div>
        </div>

        <div v-if="monthlyBars.length" class="flex items-end gap-1" style="height: 130px;">
          <div
            v-for="(item, idx) in monthlyBars" :key="idx"
            class="flex-1 flex flex-col items-center gap-1 min-w-0"
          >
            <span class="text-[10px] font-mono-data text-slate-500 font-medium leading-none text-center">
              {{ item.ventas > 0 ? formatCurrency(item.ventas) : '' }}
            </span>
            <div
              class="w-full bg-brand-500 rounded-t-md transition-all duration-500 ease-out hover:bg-brand-600 cursor-default"
              :style="{ height: monthlyMax > 0 ? Math.max((item.ventas / monthlyMax) * 96, item.ventas > 0 ? 4 : 0) + 'px' : '0px' }"
            ></div>
            <span class="text-[10px] text-slate-500 font-medium">{{ item.semana }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          icon="fa-chart-bar"
          title="Sin datos para este mes"
          text=""
          compact
        />

        <div v-if="monthlyCategories.length">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Por categoría</p>
          <div class="flex flex-wrap gap-1.5">
            <BaseBadge
              v-for="(cat, idx) in monthlyCategories" :key="idx"
              :variant="['brand', 'success', 'warning', 'danger', 'info', 'default'][idx % 6]"
              size="sm"
            >
              {{ cat.categoria }}: {{ formatCurrency(cat.total) }}
            </BaseBadge>
          </div>
        </div>

        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in monthly.topProducts.slice(0, 5)" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-slate-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-slate-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
          <p v-if="!monthly.topProducts.length" class="text-xs text-slate-400">Sin datos</p>
        </div>
      </BaseCard>

      <!-- ==================== TRIMESTRAL ==================== -->
      <BaseCard class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
              <i class="fa-solid fa-calendar-alt text-amber-600 text-sm"></i>
            </div>
            <h2 class="font-semibold text-slate-900">Trimestral</h2>
          </div>
          <BaseButton
            variant="ghost"
            size="xs"
            icon-only
            title="Sincronizar trimestral"
            aria-label="Sincronizar trimestral"
            :loading="syncingQuarterly"
            :disabled="syncingQuarterly"
            @click="syncQuarterly"
          >
            <i class="fa-solid fa-arrows-rotate text-xs"></i>
          </BaseButton>
        </div>

        <div class="space-y-2">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-slate-900">{{ formatCurrency(quarterly.total) }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">vs trim. anterior</span>
            <BaseBadge :variant="quarterly.change >= 0 ? 'success' : 'danger'" size="sm">
              <i :class="quarterly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(quarterly.change) }}%
            </BaseBadge>
          </div>
        </div>

        <div v-if="quarterlyBars.length" class="flex items-end gap-2" style="height: 130px;">
          <div
            v-for="(item, idx) in quarterlyBars" :key="idx"
            class="flex-1 flex flex-col items-center gap-1 min-w-0"
          >
            <span class="text-[10px] font-mono-data text-slate-500 font-medium leading-none text-center">
              {{ item.ventas > 0 ? formatCurrency(item.ventas) : '' }}
            </span>
            <div
              class="w-full bg-brand-500 rounded-t-md transition-all duration-500 ease-out hover:bg-brand-600 cursor-default"
              :style="{ height: quarterlyMax > 0 ? Math.max((item.ventas / quarterlyMax) * 96, item.ventas > 0 ? 4 : 0) + 'px' : '0px' }"
            ></div>
            <span class="text-[10px] text-slate-500 font-medium">{{ item.mes }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          icon="fa-chart-bar"
          title="Sin datos para este trimestre"
          text=""
          compact
        />

        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in quarterly.topProducts.slice(0, 5)" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-slate-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-slate-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
          <p v-if="!quarterly.topProducts.length" class="text-xs text-slate-400">Sin datos</p>
        </div>
      </BaseCard>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import { formatCurrency } from '@/composables/useUtils'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const toast = useToastStore()

const syncing = ref(false)
const syncingWeekly = ref(false)
const syncingMonthly = ref(false)
const syncingQuarterly = ref(false)

// ── Mock / fallback data ──────────────────────────────────────────────

const weekly = ref({
  total: 2456800,
  change: 4.5,
  topProducts: [
    { name: 'Leche entera 1L', sold: 245 },
    { name: 'Pan francés', sold: 198 },
    { name: 'Yerba mate 500g', sold: 156 },
    { name: 'Queso cremoso 1kg', sold: 134 },
    { name: 'Aceite girasol 1.5L', sold: 112 },
  ],
})

const weeklyBars = ref([
  { dia: 'Lun', ventas: 412000 },
  { dia: 'Mar', ventas: 389500 },
  { dia: 'Mié', ventas: 456200 },
  { dia: 'Jue', ventas: 512800 },
  { dia: 'Vie', ventas: 528300 },
  { dia: 'Sáb', ventas: 598000 },
  { dia: 'Dom', ventas: 0 },
])

const monthly = ref({
  total: 9875200,
  change: -2.3,
  topProducts: [
    { name: 'Leche entera 1L', sold: 980 },
    { name: 'Carne picada común', sold: 845 },
    { name: 'Pan francés', sold: 790 },
    { name: 'Yerba mate 500g', sold: 632 },
    { name: 'Huevos x30', sold: 548 },
  ],
})

const monthlyBars = ref([
  { semana: 'Sem 1', ventas: 2340000 },
  { semana: 'Sem 2', ventas: 2567800 },
  { semana: 'Sem 3', ventas: 2456800 },
  { semana: 'Sem 4', ventas: 3154600 },
])

const monthlyCategories = ref([
  { categoria: 'Lácteos', total: 2340000 },
  { categoria: 'Panadería', total: 1890000 },
  { categoria: 'Carnes', total: 3120000 },
  { categoria: 'Almacén', total: 1560000 },
  { categoria: 'Bebidas', total: 965200 },
])

const quarterly = ref({
  total: 29876500,
  change: 8.2,
  topProducts: [
    { name: 'Leche entera 1L', sold: 2980 },
    { name: 'Carne picada común', sold: 2540 },
    { name: 'Pan francés', sold: 2310 },
    { name: 'Yerba mate 500g', sold: 1890 },
    { name: 'Aceite girasol 1.5L', sold: 1720 },
  ],
})

const quarterlyBars = ref([
  { mes: 'Abr', ventas: 9875200 },
  { mes: 'May', ventas: 10234500 },
  { mes: 'Jun', ventas: 12046800 },
])

// ── Computed: max value per dataset for bar scaling ───────────────────

const weeklyMax = computed(() => {
  const vals = weeklyBars.value.map(b => b.ventas || 0)
  return vals.length ? Math.max(...vals) : 0
})

const monthlyMax = computed(() => {
  const vals = monthlyBars.value.map(b => b.ventas || 0)
  return vals.length ? Math.max(...vals) : 0
})

const quarterlyMax = computed(() => {
  const vals = quarterlyBars.value.map(b => b.ventas || 0)
  return vals.length ? Math.max(...vals) : 0
})

// ── Category badge colors ─────────────────────────────────────────────

const catColors = [
  'bg-blue-50 text-blue-700',
  'bg-emerald-50 text-emerald-700',
  'bg-amber-50 text-amber-700',
  'bg-purple-50 text-purple-700',
  'bg-rose-50 text-rose-700',
  'bg-cyan-50 text-cyan-700',
  'bg-indigo-50 text-indigo-700',
  'bg-teal-50 text-teal-700',
]

function catBadgeColor(idx) {
  return catColors[idx % catColors.length]
}

// ── API mapping helpers ───────────────────────────────────────────────

function mapTopProducts(list) {
  return (list || []).map(p => ({
    name: p.nombre,
    sold: p.cantidad,
  }))
}

// ── Sync all ──────────────────────────────────────────────────────────

async function syncAll() {
  syncing.value = true
  try {
    await Promise.all([syncWeekly(true), syncMonthly(true), syncQuarterly(true)])
    toast.success('Datos sincronizados')
  } catch {
    toast.error('No se pudieron sincronizar los datos')
  }
  syncing.value = false
}

// ── Per-period sync ───────────────────────────────────────────────────

async function syncWeekly(silent = false) {
  syncingWeekly.value = true
  try {
    const w = await api.get('/api/dashboard/semanal')
    if (w) {
      weekly.value = {
        total: w.ventas_actual ?? weekly.value.total,
        change: w.diff_ventas_pct ?? weekly.value.change,
        topProducts: mapTopProducts(w.top_productos_semana || w.top_productos).length
          ? mapTopProducts(w.top_productos_semana || w.top_productos)
          : weekly.value.topProducts,
      }
      if (w.dias && w.dias.length) {
        weeklyBars.value = w.dias.map(d => ({ dia: d.dia, ventas: d.ventas }))
      }
    }
    if (!silent) toast.success('Reporte semanal actualizado')
  } catch {
    if (!silent) toast.error('Error al cargar reporte semanal')
  }
  syncingWeekly.value = false
}

async function syncMonthly(silent = false) {
  syncingMonthly.value = true
  try {
    const m = await api.get('/api/dashboard/mensual')
    if (m) {
      monthly.value = {
        total: m.ventas_actual ?? monthly.value.total,
        change: m.diff_ventas_pct ?? monthly.value.change,
        topProducts: mapTopProducts(m.top_productos).length
          ? mapTopProducts(m.top_productos)
          : monthly.value.topProducts,
      }
      if (m.semanas && m.semanas.length) {
        monthlyBars.value = m.semanas.map(s => ({ semana: s.semana, ventas: s.ventas }))
      }
      if (m.por_categoria && m.por_categoria.length) {
        monthlyCategories.value = m.por_categoria
      }
    }
    if (!silent) toast.success('Reporte mensual actualizado')
  } catch {
    if (!silent) toast.error('Error al cargar reporte mensual')
  }
  syncingMonthly.value = false
}

async function syncQuarterly(silent = false) {
  syncingQuarterly.value = true
  try {
    const q = await api.get('/api/dashboard/trimestral')
    if (q) {
      quarterly.value = {
        total: q.ventas_actual ?? quarterly.value.total,
        change: q.diff_ventas_pct ?? quarterly.value.change,
        topProducts: mapTopProducts(q.top_productos).length
          ? mapTopProducts(q.top_productos)
          : quarterly.value.topProducts,
      }
      if (q.meses && q.meses.length) {
        quarterlyBars.value = q.meses.map(m => ({ mes: m.mes, ventas: m.ventas }))
      }
    }
    if (!silent) toast.success('Reporte trimestral actualizado')
  } catch {
    if (!silent) toast.error('Error al cargar reporte trimestral')
  }
  syncingQuarterly.value = false
}

onMounted(() => { syncAll() })
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
