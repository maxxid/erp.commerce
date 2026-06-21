<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Resumen del Comercio</h2>
        <p class="text-sm text-slate-500 mt-1">KPIs en tiempo real</p>
      </div>
      <div class="flex items-center gap-3">
        <button v-if="auth.isAdmin || auth.isEncargado" @click="simple = !simple; load()"
                class="text-[10px] font-bold text-slate-400 hover:text-brand-600 transition flex items-center gap-1">
          <i :class="simple ? 'fa-toggle-off' : 'fa-toggle-on'" class="fa-solid"></i>
          {{ simple ? 'Vista simple' : 'Vista completa' }}
        </button>
        <button @click="load()" class="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl flex items-center gap-2 shadow-sm transition">
          <i class="fa-solid fa-arrows-rotate text-brand-500"></i> Sincronizar
        </button>
      </div>
    </div>

    <!-- Alertas banner -->
    <div v-if="alertas.length" class="space-y-1.5">
      <div v-for="a in alertas" :key="a.tipo"
           :class="a.nivel === 'danger' ? 'bg-rose-50 border-rose-200 text-rose-700' : 'bg-amber-50 border-amber-200 text-amber-700'"
           class="px-4 py-2 rounded-xl border text-xs font-bold flex items-center gap-2">
        <span v-if="a.nivel === 'danger'">🔴</span>
        <span v-if="a.nivel === 'warning'">🟡</span>
        <span>{{ a.mensaje }}</span>
      </div>
    </div>

    <!-- Vista Simple -->
    <div v-if="simple" class="space-y-6">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Ventas Hoy" :value="fc(data.ventas_hoy)" color="emerald" :sub="(data.cant_ventas_hoy || 0) + ' tickets'" />
        <StatCard label="Efectivo Hoy" :value="fc(resumen.desglose?.efectivo || 0)" color="emerald" />
        <StatCard label="Transferencia" :value="fc(resumen.desglose?.transferencia || 0)" color="blue" />
        <StatCard label="Stock Crítico" :value="data.stock_bajo" color="rose" sub="bajo mínimo" />
      </div>
    </div>

    <!-- Vista Completa -->
    <div v-if="!simple" class="space-y-6">
      <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
        <StatCard label="Ventas Hoy" :value="fc(data.ventas_hoy)" color="emerald" :sub="(data.cant_ventas_hoy || 0) + ' tickets'" />
        <StatCard label="Ventas Mes" :value="fc(data.ventas_mes)" color="indigo" :sub="(data.cant_ventas_mes || 0) + ' tickets'" />
        <StatCard label="Ticket Prom." :value="fc(data.ticket_promedio)" color="indigo" :sub="'Medio: ' + (data.medio_favorito || '\u2014')" />
        <StatCard label="Stock" :value="fc(data.valor_stock)" color="amber" :sub="(data.total_productos || 0) + ' productos'" />
        <StatCard label="Stock Crítico" :value="data.stock_bajo" color="rose" sub="bajo mínimo" />
        <StatCard label="Tendencia" :value="(data.tendencia >= 0 ? '+' : '') + (data.tendencia || 0) + '%'" :colorClass="data.tendencia >= 0 ? 'text-emerald-600' : 'text-rose-600'" sub="vs semana anterior" />
        <StatCard label="Margen Bruto" :value="fc(data.margen_bruto_mes || 0)" :colorClass="data.margen_pct_mes >= 0 ? 'text-emerald-600' : 'text-rose-600'" :sub="(data.margen_pct_mes || 0) + '%'" />
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartCard title="Ventas — Últimos 7 Días" :items="data.ventas_7_dias" type="bars" color="bg-brand-500" />
        <ChartCard title="Picos por Hora (Hoy)" :items="data.ventas_por_hora" type="thin" color="bg-accent-success" />
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
          <h3 class="font-bold text-slate-900 text-sm mb-3">🏆 Top Productos del Mes</h3>
          <div class="space-y-2">
            <div v-for="(p, idx) in (data.top_productos_mes || [])" :key="p.id" class="flex items-center gap-3 p-2 bg-slate-50 rounded-lg text-xs">
              <span class="font-bold text-slate-400 w-5">#{{ idx + 1 }}</span>
              <span class="flex-1 font-bold text-slate-800 truncate">{{ p.nombre }}</span>
              <span class="text-slate-500">{{ p.cantidad_vendida }} u</span>
              <span class="font-mono-data font-bold text-emerald-600">{{ fc(p.total_vendido) }}</span>
            </div>
            <p v-if="!(data.top_productos_mes || []).length" class="text-xs text-slate-400 text-center py-4">Sin ventas este mes</p>
          </div>
        </div>
        <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm space-y-4">
          <h3 class="font-bold text-slate-900 text-sm">⚠️ Alertas de Stock</h3>
          <div v-if="(data.stock_critico || []).length">
            <p class="text-[10px] font-bold text-rose-500 uppercase mb-2">Críticos (bajo mínimo)</p>
            <div v-for="p in data.stock_critico" :key="'c'+p.id" class="flex justify-between text-xs p-2 bg-rose-50 rounded-lg mb-1">
              <span class="font-bold truncate flex-1">{{ p.nombre }}</span>
              <span class="font-mono-data font-bold text-rose-600">{{ p.stock_actual }} / {{ p.stock_minimo }}</span>
            </div>
          </div>
          <div v-if="(data.sin_stock || []).length">
            <p class="text-[10px] font-bold text-slate-500 uppercase mb-2 mt-3">Sin stock</p>
            <div v-for="p in data.sin_stock" :key="'s'+p.id" class="flex justify-between text-xs p-2 bg-slate-100 rounded-lg mb-1">
              <span class="font-bold truncate flex-1">{{ p.nombre }}</span>
              <span class="font-mono-data text-slate-400">{{ p.codigo_barras }}</span>
            </div>
          </div>
          <p v-if="!(data.stock_critico || []).length && !(data.sin_stock || []).length" class="text-xs text-slate-400 text-center py-4">Todo en orden</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { formatCurrency as fc } from '@/composables/useUtils'
import StatCard from '@/components/ui/StatCard.vue'
import ChartCard from '@/components/ui/ChartCard.vue'

const auth = useAuthStore()
const simple = ref(false)
const alertas = ref([])
const resumen = reactive({ desglose: {} })
const data = reactive({})

onMounted(() => load())

async function load() {
  try {
    const resp = await fetch('/api/dashboard').then(r => r.json())
    Object.assign(data, resp)
  } catch { /* mock data */ }
  if (!data.total_productos) Object.assign(data, mockData)
}
</script>
