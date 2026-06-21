<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Reportes</h1>
        <p class="text-sm text-gray-500 mt-1">Análisis de ventas y rendimiento por período</p>
      </div>
      <button class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-2xl shadow-sm font-medium transition-colors flex items-center gap-2">
        <i class="fa-solid fa-file-pdf text-sm"></i>
        Exportar todo
      </button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
            <i class="fa-solid fa-calendar-week text-indigo-600 text-sm"></i>
          </div>
          <h2 class="font-semibold text-gray-900">Semanal</h2>
        </div>

        <div class="space-y-3">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-gray-900">{{ formatCurrency(weekly.total) }}</p>
          </div>
          <div class="flex items-center gap-3">
            <div>
              <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Tickets</p>
              <p class="text-lg font-mono-data font-semibold text-gray-700">{{ weekly.tickets }}</p>
            </div>
            <div>
              <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Promedio ticket</p>
              <p class="text-lg font-mono-data font-semibold text-gray-700">{{ formatCurrency(weekly.averageTicket) }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">vs semana anterior</span>
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold" :class="weekly.change >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">
              <i :class="weekly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(weekly.change) }}%
            </span>
          </div>
        </div>

        <div class="space-y-1.5">
          <div v-for="(bar, idx) in weeklyBars" :key="idx" class="flex items-center gap-2">
            <span class="w-12 text-[10px] text-gray-500 text-right">{{ bar.day }}</span>
            <div class="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
              <div class="h-full bg-indigo-400 rounded-full transition-all" :style="{ width: bar.percent + '%' }"></div>
            </div>
            <span class="w-16 text-right font-mono-data text-xs text-gray-600">{{ formatCurrency(bar.value) }}</span>
          </div>
        </div>

        <div>
          <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in weekly.topProducts" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-gray-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-gray-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
            <i class="fa-solid fa-calendar-check text-emerald-600 text-sm"></i>
          </div>
          <h2 class="font-semibold text-gray-900">Mensual</h2>
        </div>

        <div class="space-y-3">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-gray-900">{{ formatCurrency(monthly.total) }}</p>
          </div>
          <div class="flex items-center gap-3">
            <div>
              <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Tickets</p>
              <p class="text-lg font-mono-data font-semibold text-gray-700">{{ monthly.tickets }}</p>
            </div>
            <div>
              <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Promedio ticket</p>
              <p class="text-lg font-mono-data font-semibold text-gray-700">{{ formatCurrency(monthly.averageTicket) }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">vs mes anterior</span>
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold" :class="monthly.change >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">
              <i :class="monthly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(monthly.change) }}%
            </span>
          </div>
        </div>

        <div class="space-y-1.5">
          <div v-for="(bar, idx) in monthlyBars" :key="idx" class="flex items-center gap-2">
            <span class="w-12 text-[10px] text-gray-500 text-right">{{ bar.week }}</span>
            <div class="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
              <div class="h-full bg-emerald-400 rounded-full transition-all" :style="{ width: bar.percent + '%' }"></div>
            </div>
            <span class="w-16 text-right font-mono-data text-xs text-gray-600">{{ formatCurrency(bar.value) }}</span>
          </div>
        </div>

        <div>
          <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in monthly.topProducts" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-gray-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-gray-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm p-5 space-y-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
            <i class="fa-solid fa-calendar-alt text-amber-600 text-sm"></i>
          </div>
          <h2 class="font-semibold text-gray-900">Trimestral</h2>
        </div>

        <div class="space-y-3">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-gray-900">{{ formatCurrency(quarterly.total) }}</p>
          </div>
          <div class="flex items-center gap-3">
            <div>
              <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Tickets</p>
              <p class="text-lg font-mono-data font-semibold text-gray-700">{{ quarterly.tickets }}</p>
            </div>
            <div>
              <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Promedio ticket</p>
              <p class="text-lg font-mono-data font-semibold text-gray-700">{{ formatCurrency(quarterly.averageTicket) }}</p>
            </div>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">vs trim. anterior</span>
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-semibold" :class="quarterly.change >= 0 ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'">
              <i :class="quarterly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(quarterly.change) }}%
            </span>
          </div>
        </div>

        <div class="space-y-1.5">
          <div v-for="(bar, idx) in quarterlyBars" :key="idx" class="flex items-center gap-2">
            <span class="w-12 text-[10px] text-gray-500 text-right">{{ bar.month }}</span>
            <div class="flex-1 h-5 bg-gray-100 rounded-full overflow-hidden">
              <div class="h-full bg-amber-400 rounded-full transition-all" :style="{ width: bar.percent + '%' }"></div>
            </div>
            <span class="w-16 text-right font-mono-data text-xs text-gray-600">{{ formatCurrency(bar.value) }}</span>
          </div>
        </div>

        <div>
          <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in quarterly.topProducts" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-gray-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-gray-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatCurrency } from '@/composables/useUtils'

const weekly = {
  total: 2456800,
  tickets: 342,
  averageTicket: 7184,
  change: 4.5,
  topProducts: [
    { name: 'Leche entera 1L', sold: 245 },
    { name: 'Pan francés', sold: 198 },
    { name: 'Yerba mate 500g', sold: 156 },
    { name: 'Queso cremoso 1kg', sold: 134 },
    { name: 'Aceite girasol 1.5L', sold: 112 },
  ],
}

const weeklyBars = [
  { day: 'Lun', value: 412000, percent: 68 },
  { day: 'Mar', value: 389500, percent: 65 },
  { day: 'Mié', value: 456200, percent: 76 },
  { day: 'Jue', value: 512800, percent: 85 },
  { day: 'Vie', value: 528300, percent: 88 },
  { day: 'Sáb', value: 598000, percent: 100 },
  { day: 'Dom', value: 0, percent: 0 },
]

const monthly = {
  total: 9875200,
  tickets: 1456,
  averageTicket: 6783,
  change: -2.3,
  topProducts: [
    { name: 'Leche entera 1L', sold: 980 },
    { name: 'Carne picada común', sold: 845 },
    { name: 'Pan francés', sold: 790 },
    { name: 'Yerba mate 500g', sold: 632 },
    { name: 'Huevos x30', sold: 548 },
  ],
}

const monthlyBars = [
  { week: 'Sem 1', value: 2340000, percent: 74 },
  { week: 'Sem 2', value: 2567800, percent: 81 },
  { week: 'Sem 3', value: 2456800, percent: 78 },
  { week: 'Sem 4', value: 3154600, percent: 100 },
]

const quarterly = {
  total: 29876500,
  tickets: 4320,
  averageTicket: 6916,
  change: 8.2,
  topProducts: [
    { name: 'Leche entera 1L', sold: 2980 },
    { name: 'Carne picada común', sold: 2540 },
    { name: 'Pan francés', sold: 2310 },
    { name: 'Yerba mate 500g', sold: 1890 },
    { name: 'Aceite girasol 1.5L', sold: 1720 },
  ],
}

const quarterlyBars = [
  { month: 'Abr', value: 9875200, percent: 82 },
  { month: 'May', value: 10234500, percent: 85 },
  { month: 'Jun', value: 12046800, percent: 100 },
]
</script>
