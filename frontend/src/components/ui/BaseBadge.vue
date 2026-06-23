<script setup>
const props = defineProps({
  variant: { type: String, default: 'default' }, // default, success, warning, danger, info, brand
  size: { type: String, default: 'sm' }, // xs, sm, md
  dot: { type: Boolean, default: false },
  pulse: { type: Boolean, default: false }
})

const sizeClass = {
  xs: 'px-1.5 py-0.5 text-[10px]',
  sm: 'px-2 py-0.5 text-xs',
  md: 'px-2.5 py-1 text-sm'
}[props.size]

const variantClass = {
  default: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300',
  brand: 'bg-brand-50 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300',
  success: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300',
  warning: 'bg-amber-50 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  danger: 'bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  info: 'bg-blue-50 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
}[props.variant]

const dotClass = {
  default: 'bg-slate-400',
  brand: 'bg-brand-500',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-red-500',
  info: 'bg-blue-500'
}[props.variant]
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 font-medium rounded-full border border-transparent transition-colors"
    :class="[sizeClass, variantClass]"
  >
    <span
      v-if="dot"
      class="w-1.5 h-1.5 rounded-full"
      :class="[dotClass, pulse ? 'animate-pulse' : '']"
    ></span>
    <slot />
  </span>
</template>
