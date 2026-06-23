<script setup>
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  label: { type: String, default: '' },
  description: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  size: { type: String, default: 'md' } // sm, md
})

const emit = defineEmits(['update:modelValue'])

const sizeClass = {
  sm: { track: 'w-9 h-5', knob: 'w-3.5 h-3.5', translate: 'translate-x-4.5' },
  md: { track: 'w-11 h-6', knob: 'w-5 h-5', translate: 'translate-x-5' }
}[props.size]

function toggle() {
  if (props.disabled) return
  emit('update:modelValue', !props.modelValue)
}
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :disabled="disabled"
    class="group inline-flex items-center gap-3 w-full text-left disabled:opacity-50 disabled:cursor-not-allowed"
    @click="toggle"
  >
    <span
      class="relative inline-flex shrink-0 rounded-full transition-colors duration-200 ease-out-expo focus-within:outline-none"
      :class="[
        sizeClass.track,
        modelValue
          ? 'bg-brand-600 shadow-sm shadow-brand-500/30'
          : 'bg-slate-200 dark:bg-slate-700'
      ]"
      tabindex="-1"
    >
      <span
        class="absolute top-1/2 -translate-y-1/2 left-0.5 bg-white rounded-full shadow-sm transition-transform duration-200 ease-out-expo"
        :class="[
          sizeClass.knob,
          modelValue ? sizeClass.translate : 'translate-x-0'
        ]"
      ></span>
    </span>
    <span v-if="label || description" class="flex flex-col">
      <span v-if="label" class="text-sm font-medium text-slate-900 dark:text-slate-100">{{ label }}</span>
      <span v-if="description" class="text-xs text-slate-500 dark:text-slate-400">{{ description }}</span>
    </span>
  </button>
</template>
