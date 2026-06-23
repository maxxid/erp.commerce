<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number, Boolean], default: '' },
  label: { type: String, default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Seleccionar...' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  required: { type: Boolean, default: false },
  size: { type: String, default: 'md' },
  id: { type: String, default: '' },
  optionValue: { type: String, default: 'value' },
  optionLabel: { type: String, default: 'label' }
})

const emit = defineEmits(['update:modelValue', 'change'])

const inputId = computed(() => props.id || `select-${Math.random().toString(36).slice(2, 9)}`)
const sizeClass = computed(() => {
  return { sm: 'px-3 py-1.5 text-xs', md: 'px-3.5 py-2.5 text-sm', lg: 'px-4 py-3 text-base' }[props.size]
})

function onChange(e) {
  emit('update:modelValue', e.target.value)
  emit('change', e.target.value)
}
</script>

<template>
  <div class="w-full">
    <label
      v-if="label"
      :for="inputId"
      class="block mb-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300"
    >
      {{ label }}
      <span v-if="required" class="text-red-500 ml-0.5">*</span>
    </label>
    <div class="relative">
      <select
        :id="inputId"
        :value="modelValue"
        :disabled="disabled || loading"
        :required="required"
        :aria-invalid="!!error"
        :aria-describedby="error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined"
        class="w-full rounded-lg border bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 appearance-none transition-all duration-200 ease-out-expo cursor-pointer"
        :class="[
          sizeClass,
          error
            ? 'border-red-300 dark:border-red-700 focus:border-red-500 focus:ring-2 focus:ring-red-500/20'
            : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:focus:ring-brand-500/25'
        ]"
        style="background-image: url(&quot;data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e&quot;); background-size: 1.25em 1.25em; background-position: right 0.5rem center; background-repeat: no-repeat; padding-right: 2.5rem;"
        @change="onChange"
      >
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option
          v-for="(opt, idx) in options"
          :key="idx"
          :value="typeof opt === 'object' ? opt[optionValue] : opt"
        >
          {{ typeof opt === 'object' ? opt[optionLabel] : opt }}
        </option>
      </select>
      <div
        v-if="loading"
        class="absolute right-8 top-1/2 -translate-y-1/2 text-slate-400"
      >
        <i class="fa-solid fa-circle-notch fa-spin text-sm"></i>
      </div>
    </div>
    <p
      v-if="error"
      :id="`${inputId}-error`"
      class="mt-1.5 text-xs font-medium text-red-600 dark:text-red-400 animate-fade-in"
    >
      <i class="fa-solid fa-circle-exclamation mr-1"></i>{{ error }}
    </p>
    <p
      v-else-if="hint"
      :id="`${inputId}-hint`"
      class="mt-1.5 text-xs text-slate-500 dark:text-slate-400"
    >
      {{ hint }}
    </p>
  </div>
</template>
