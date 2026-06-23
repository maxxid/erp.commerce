<script setup>
import AnimatedNumber from './AnimatedNumber.vue'

const props = defineProps({
  label: { type: String, default: '' },
  value: { type: Number, default: 0 },
  prefix: { type: String, default: '' },
  suffix: { type: String, default: '' },
  decimals: { type: Number, default: 0 },
  sublabel: { type: String, default: '' },
  trend: { type: Number, default: null }, // null, positive, negative
  trendLabel: { type: String, default: '' },
  icon: { type: String, default: '' },
  iconColor: { type: String, default: 'brand' }, // brand, success, warning, danger, info
  loading: { type: Boolean, default: false },
  animate: { type: Boolean, default: true }
})

const iconBg = {
  brand: 'bg-brand-50 text-brand-600 dark:bg-brand-900/30 dark:text-brand-400',
  success: 'bg-emerald-50 text-emerald-600 dark:bg-emerald-900/30 dark:text-emerald-400',
  warning: 'bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400',
  danger: 'bg-red-50 text-red-600 dark:bg-red-900/30 dark:text-red-400',
  info: 'bg-blue-50 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400'
}[props.iconColor]
</script>

<template>
  <div class="card-elevated p-5 group">
    <div class="flex items-start justify-between">
      <div class="min-w-0 flex-1">
        <p class="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400 truncate">
          {{ label }}
        </p>
        <div class="mt-2 text-2xl font-bold text-slate-900 dark:text-white">
          <AnimatedNumber
            v-if="!loading && animate"
            :value="value"
            :prefix="prefix"
            :suffix="suffix"
            :decimals="decimals"
          />
          <span v-else-if="!loading">
            {{ prefix }}{{ value.toLocaleString('es-AR', { minimumFractionDigits: decimals, maximumFractionDigits: decimals }) }}{{ suffix }}
          </span>
          <div v-else class="skeleton w-24 h-8 rounded-md"></div>
        </div>
        <div v-if="trend !== null || sublabel" class="mt-1.5 flex items-center gap-2 text-xs">
          <span
            v-if="trend !== null"
            class="inline-flex items-center gap-1 font-semibold rounded-full px-1.5 py-0.5"
            :class="trend >= 0
              ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300'
              : 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'"
          >
            <i :class="trend >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
            {{ Math.abs(trend) }}%
          </span>
          <span class="text-slate-500 dark:text-slate-400 truncate">{{ trendLabel || sublabel }}</span>
        </div>
      </div>
      <div
        v-if="icon"
        class="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-200 group-hover:scale-105"
        :class="iconBg"
      >
        <i :class="`fa-solid ${icon} text-lg`"></i>
      </div>
    </div>
  </div>
</template>
