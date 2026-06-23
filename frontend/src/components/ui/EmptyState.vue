<script setup>
const props = defineProps({
  icon: { type: String, default: 'fa-inbox' },
  title: { type: String, default: 'Sin datos' },
  text: { type: String, default: 'No hay información disponible.' },
  actionText: { type: String, default: '' },
  compact: { type: Boolean, default: false }
})

const emit = defineEmits(['action'])
</script>

<template>
  <div
    class="flex flex-col items-center justify-center text-center"
    :class="compact ? 'py-6 px-4' : 'py-12 px-4'"
  >
    <div
      class="flex items-center justify-center rounded-2xl bg-slate-100 dark:bg-slate-800 text-slate-400 dark:text-slate-500 mb-4"
      :class="compact ? 'w-12 h-12 text-xl' : 'w-16 h-16 text-2xl'"
    >
      <i :class="`fa-solid ${icon}`"></i>
    </div>
    <h3
      class="font-semibold text-slate-900 dark:text-white"
      :class="compact ? 'text-sm' : 'text-base'"
    >
      {{ title }}
    </h3>
    <p
      class="mt-1 text-slate-500 dark:text-slate-400 max-w-xs"
      :class="compact ? 'text-xs' : 'text-sm'"
    >
      {{ text }}
    </p>
    <button
      v-if="actionText"
      type="button"
      class="mt-4 text-sm font-medium text-brand-600 hover:text-brand-700 dark:text-brand-400 dark:hover:text-brand-300 transition-colors"
      @click="emit('action')"
    >
      {{ actionText }}
      <i class="fa-solid fa-arrow-right ml-1 text-xs"></i>
    </button>
  </div>
</template>
