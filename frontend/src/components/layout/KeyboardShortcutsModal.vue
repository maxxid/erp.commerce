<script setup>
import BaseModal from '@/components/ui/BaseModal.vue'
import Kbd from '@/components/ui/Kbd.vue'

defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: 'Atajos de teclado' },
  shortcuts: { type: Array, default: () => [] },
  globalShortcuts: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])
</script>

<template>
  <BaseModal :model-value="modelValue" :title="title" size="md" @update:model-value="emit('update:modelValue', $event)">
    <div class="space-y-6">
      <div v-if="globalShortcuts.length">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold mb-3">Globales</p>
        <div class="space-y-2">
          <div v-for="s in globalShortcuts" :key="s.key" class="flex items-center justify-between py-1.5">
            <span class="text-sm text-slate-700 dark:text-slate-300">{{ s.description }}</span>
            <Kbd>{{ s.key }}</Kbd>
          </div>
        </div>
      </div>
      <div v-if="shortcuts.length">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold mb-3">Esta vista</p>
        <div class="space-y-2">
          <div v-for="s in shortcuts" :key="s.key" class="flex items-center justify-between py-1.5">
            <span class="text-sm text-slate-700 dark:text-slate-300">{{ s.description }}</span>
            <Kbd>{{ s.key }}</Kbd>
          </div>
        </div>
      </div>
      <div v-if="!shortcuts.length && !globalShortcuts.length" class="text-center py-6 text-slate-400 dark:text-slate-500 text-sm">
        No hay atajos configurados para esta vista.
      </div>
    </div>
  </BaseModal>
</template>
