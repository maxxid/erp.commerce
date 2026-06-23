<script setup>
const props = defineProps({
  padding: { type: String, default: 'md' }, // none, sm, md, lg
  hover: { type: Boolean, default: false },
  interactive: { type: Boolean, default: false },
  active: { type: Boolean, default: false },
  loading: { type: Boolean, default: false }
})

const paddingClass = {
  none: '',
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-6'
}[props.padding]
</script>

<template>
  <div
    class="relative bg-white dark:bg-slate-900 rounded-xl border transition-all duration-200 ease-out-expo overflow-hidden"
    :class="[
      paddingClass,
      active
        ? 'border-brand-400 dark:border-brand-500 shadow-glow ring-1 ring-brand-500/20'
        : 'border-slate-200/70 dark:border-slate-700/70 shadow-sm',
      hover || interactive ? 'hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600' : '',
      interactive ? 'cursor-pointer active:scale-[0.995]' : '',
      loading ? 'pointer-events-none' : ''
    ]"
  >
    <div
      v-if="loading"
      class="absolute inset-0 z-10 bg-white/60 dark:bg-slate-900/60 backdrop-blur-[1px] flex items-center justify-center"
    >
      <i class="fa-solid fa-circle-notch fa-spin text-brand-500 text-xl"></i>
    </div>
    <slot />
  </div>
</template>
