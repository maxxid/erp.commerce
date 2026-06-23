<script setup>
import { ref, onMounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'
import KpiCard from '@/components/ui/KpiCard.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const auth = useAuthStore()
const simple = ref(false)
const loading = ref(true)
const alertas = ref([])
const data = ref({})

const mockData = {
  total_productos: 3, valor_stock: 450000, stock_bajo: 1,
  ventas_hoy: 22000, cant_ventas_hoy: 5,
  ventas_mes: 22000, cant_ventas_mes: 5,
  ticket_promedio: 4400, medio_favorito: 'efectivo',
  tendencia: 12, margen_bruto_hoy: 8000, margen_bruto_mes: 8000,
  margen_pct_hoy: 36, margen_pct_mes: 36,
  ventas_7_dias: { valores: [5000, 8000, 3000, 12000, 6000, 9000, 7000], labels: ['Lun','Mar','Mie','Jue','Vie','Sab','Dom'] },
  ventas_por_hora: { valores: [0,0,0,2,1,0,3,5,8,6,4,2,0,0,1,3,5,4,2,1,0,0,0,0], labels: Array.from({ length: 24 }, (_, i) => i + 'h') },
  top_productos_mes: [
    { id: 1, nombre: 'Coca Cola 2.25L', cantidad_vendida: 24, total_vendido: 60000 },
    { id: 2, nombre: 'Yerba Mate Playadito 1kg', cantidad_vendida: 15, total_vendido: 48000 },
  ],
  stock_critico: [{ id: 3, nombre: 'Aceite de Girasol Natura 1.5L', stock_actual: 2, stock_minimo: 8 }],
  sin_stock: [],
  efectivo_hoy: 12000, transferencia_hoy: 5500
}

const maxBar = computed(() => {
  const vals = data.value.ventas_7_dias?.valores || []
  return Math.max(...vals, 1)
})

const maxHour = computed(() => {
  const vals = data.value.ventas_por_hora?.valores || []
  return Math.max(...vals, 1)
})

onMounted(() => load())

async function load() {
  loading.value = true
  try {
    const resp = await api.get('/api/dashboard/resumen')
    if (resp && resp.total_productos) data.value = resp
    else Object.assign(data.value, mockData)
  } catch {
    Object.assign(data.value, mockData)
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Resumen del Comercio</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">KPIs en tiempo real</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          v-if="auth.isAdmin || auth.isEncargado"
          type="button"
          class="text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          @click="simple = !simple"
        >
          <i :class="simple ? 'fa-toggle-off' : 'fa-toggle-on'" class="fa-solid text-base"></i>
          {{ simple ? 'Vista simple' : 'Vista completa' }}
        </button>
        <BaseButton variant="secondary" size="sm" :loading="loading" @click="load">
          <i class="fa-solid fa-arrows-rotate" :class="loading ? 'animate-spin' : ''"></i>
          Sincronizar
        </BaseButton>
      </div>
    </div>

    <!-- Alertas -->
    <TransitionGroup
      v-if="alertas.length"
      tag="div"
      class="space-y-2"
      enter-active-class="transition duration-300 ease-out-expo"
      enter-from-class="opacity-0 -translate-x-2"
      enter-to-class="opacity-100 translate-x-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-x-0"
      leave-to-class="opacity-0 translate-x-2"
    >
      <div
        v-for="a in alertas"
        :key="a.tipo"
        class="px-4 py-3 rounded-xl border text-xs font-semibold flex items-center gap-2.5"
        :class="a.nivel === 'danger'
          ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/50 text-red-700 dark:text-red-300'
          : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/50 text-amber-700 dark:text-amber-300'"
      >
        <i :class="a.nivel === 'danger' ? 'fa-solid fa-circle-exclamation text-red-500' : 'fa-solid fa-triangle-exclamation text-amber-500'"></i>
        <span>{{ a.mensaje }}</span>
      </div>
    </TransitionGroup>

    <!-- KPIs -->
    <div v-if="simple" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <KpiCard label="Ventas Hoy" :value="data.ventas_hoy || 0" prefix="$" :loading="loading" icon="fa-sack-dollar" icon-color="success" :sublabel="(data.cant_ventas_hoy || 0) + ' tickets'" />
      <KpiCard label="Efectivo Hoy" :value="data.efectivo_hoy || 0" prefix="$" :loading="loading" icon="fa-money-bill-wave" icon-color="brand" />
      <KpiCard label="Transferencia" :value="data.transferencia_hoy || 0" prefix="$" :loading="loading" icon="fa-mobile-screen-button" icon-color="info" />
      <KpiCard label="Stock Crítico" :value="data.stock_bajo || 0" :loading="loading" icon="fa-triangle-exclamation" icon-color="danger" sublabel="bajo mínimo" />
    </div>

    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <KpiCard label="Ventas Hoy" :value="data.ventas_hoy || 0" prefix="$" :loading="loading" icon="fa-sack-dollar" icon-color="success" :sublabel="(data.cant_ventas_hoy || 0) + ' tickets'" />
      <KpiCard label="Ventas Mes" :value="data.ventas_mes || 0" prefix="$" :loading="loading" icon="fa-chart-line" icon-color="brand" :sublabel="(data.cant_ventas_mes || 0) + ' tickets'" />
      <KpiCard label="Ticket Prom." :value="data.ticket_promedio || 0" prefix="$" :loading="loading" icon="fa-receipt" icon-color="info" :sublabel="'Medio: ' + (data.medio_favorito || '—')" />
      <KpiCard label="Stock" :value="data.valor_stock || 0" prefix="$" :loading="loading" icon="fa-boxes-stacked" icon-color="warning" :sublabel="(data.total_productos || 0) + ' productos'" />
      <KpiCard label="Stock Crítico" :value="data.stock_bajo || 0" :loading="loading" icon="fa-triangle-exclamation" icon-color="danger" sublabel="bajo mínimo" />
      <KpiCard label="Tendencia" :value="data.tendencia || 0" suffix="%" :trend="data.tendencia || 0" trend-label="vs semana anterior" :loading="loading" icon="fa-arrow-trend-up" icon-color="success" />
    </div>

    <!-- Charts -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <BaseCard padding="lg">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-bold text-slate-900 dark:text-white text-sm">Ventas — Últimos 7 Días</h3>
          <BaseBadge variant="brand" size="xs">{{ Math.floor((data.ventas_7_dias?.valores || []).reduce((a, b) => a + b, 0)) }} total</BaseBadge>
        </div>
        <div v-if="loading" class="h-40 flex items-end gap-2">
          <BaseSkeleton v-for="n in 7" :key="n" class="flex-1 rounded-t-lg" :style="{ height: `${20 + Math.random() * 60}%` }" />
        </div>
        <div v-else class="h-40 flex items-end gap-3">
          <div
            v-for="(v, i) in (data.ventas_7_dias?.valores || [])"
            :key="i"
            class="flex-1 flex flex-col items-center gap-2 group"
          >
            <div class="w-full bg-slate-100 dark:bg-slate-800 rounded-t-lg relative overflow-hidden h-full">
              <div
                class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-brand-600 to-brand-400 rounded-t-lg transition-all duration-500 ease-out-expo group-hover:from-brand-500 group-hover:to-brand-300"
                :style="{ height: `${(v / maxBar) * 100}%` }"
              ></div>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap bg-white dark:bg-slate-800 px-2 py-1 rounded-md shadow-sm border border-slate-100 dark:border-slate-700 pointer-events-none">
                {{ fc(v) }}
              </div>
            </div>
            <span class="text-[10px] font-medium text-slate-500 dark:text-slate-400">{{ data.ventas_7_dias?.labels?.[i] }}</span>
          </div>
        </div>
      </BaseCard>

      <BaseCard padding="lg">
        <div class="flex items-center justify-between mb-5">
          <h3 class="font-bold text-slate-900 dark:text-white text-sm">Picos por Hora (Hoy)</h3>
          <BaseBadge variant="success" size="xs">24hs</BaseBadge>
        </div>
        <div v-if="loading" class="h-40 flex items-end gap-1">
          <BaseSkeleton v-for="n in 12" :key="n" class="flex-1 rounded-t-sm" :style="{ height: `${15 + Math.random() * 50}%` }" />
        </div>
        <div v-else class="h-40 flex items-end gap-1">
          <div
            v-for="(v, i) in (data.ventas_por_hora?.valores || []).slice(8, 20)"
            :key="i"
            class="flex-1 flex flex-col items-center gap-1 group"
          >
            <div class="w-full bg-slate-100 dark:bg-slate-800 rounded-t-sm relative overflow-hidden h-full">
              <div
                class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-emerald-500 to-emerald-300 rounded-t-sm transition-all duration-500 ease-out-expo group-hover:from-emerald-400 group-hover:to-emerald-200"
                :style="{ height: `${(v / maxHour) * 100}%` }"
              ></div>
            </div>
            <span class="text-[9px] font-medium text-slate-500 dark:text-slate-400">{{ data.ventas_por_hora?.labels?.[i + 8] }}</span>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- Lists -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <BaseCard padding="lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
            <i class="fa-solid fa-trophy text-amber-500"></i>
            Top Productos del Mes
          </h3>
        </div>
        <div v-if="loading" class="space-y-3">
          <BaseSkeleton v-for="n in 3" :key="n" class="h-10 rounded-lg" />
        </div>
        <div v-else-if="(data.top_productos_mes || []).length" class="space-y-2">
          <div
            v-for="(p, idx) in (data.top_productos_mes || [])"
            :key="p.id"
            class="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl text-sm transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <span class="w-6 h-6 flex items-center justify-center rounded-lg bg-white dark:bg-slate-700 text-xs font-bold text-slate-500 dark:text-slate-300 shadow-sm">{{ idx + 1 }}</span>
            <span class="flex-1 font-medium text-slate-800 dark:text-slate-100 truncate">{{ p.nombre }}</span>
            <span class="text-xs text-slate-500 dark:text-slate-400">{{ p.cantidad_vendida }} u</span>
            <span class="font-mono-data font-semibold text-emerald-600 dark:text-emerald-400">{{ fc(p.total_vendido) }}</span>
          </div>
        </div>
        <EmptyState v-else icon="fa-cart-arrow-down" title="Sin ventas este mes" text="Aún no hay productos destacados." compact />
      </BaseCard>

      <BaseCard padding="lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
            <i class="fa-solid fa-triangle-exclamation text-red-500"></i>
            Alertas de Stock
          </h3>
        </div>
        <div v-if="loading" class="space-y-3">
          <BaseSkeleton v-for="n in 3" :key="n" class="h-10 rounded-lg" />
        </div>
        <div v-else-if="(data.stock_critico || []).length || (data.sin_stock || []).length" class="space-y-4">
          <div v-if="(data.stock_critico || []).length">
            <p class="text-[10px] font-bold text-red-500 uppercase tracking-wider mb-2">Críticos (bajo mínimo)</p>
            <div v-for="p in data.stock_critico" :key="'c'+p.id" class="flex justify-between text-sm p-3 bg-red-50 dark:bg-red-900/20 rounded-xl mb-2">
              <span class="font-medium truncate flex-1 text-slate-800 dark:text-slate-100">{{ p.nombre }}</span>
              <span class="font-mono-data font-semibold text-red-600 dark:text-red-300">{{ p.stock_actual }} / {{ p.stock_minimo }}</span>
            </div>
          </div>
          <div v-if="(data.sin_stock || []).length">
            <p class="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Sin stock</p>
            <div v-for="p in data.sin_stock" :key="'s'+p.id" class="flex justify-between text-sm p-3 bg-slate-100 dark:bg-slate-800 rounded-xl mb-2">
              <span class="font-medium truncate flex-1 text-slate-800 dark:text-slate-100">{{ p.nombre }}</span>
              <span class="font-mono-data text-slate-500 dark:text-slate-400">{{ p.codigo_barras }}</span>
            </div>
          </div>
        </div>
        <EmptyState v-else icon="fa-check-circle" title="Todo en orden" text="No hay alertas de stock activas." compact />
      </BaseCard>
    </div>
  </div>
</template>
