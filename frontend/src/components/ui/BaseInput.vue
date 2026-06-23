<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  loading: { type: Boolean, default: false },
  required: { type: Boolean, default: false },
  autofocus: { type: Boolean, default: false },
  size: { type: String, default: 'md' }, // sm, md, lg
  inputClass: { type: String, default: '' },
  id: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'blur', 'focus', 'keydown', 'enter'])

const inputId = computed(() => props.id || `input-${Math.random().toString(36).slice(2, 9)}`)

const sizeClass = computed(() => {
  return { sm: 'px-3 py-1.5 text-xs', md: 'px-3.5 py-2.5 text-sm', lg: 'px-4 py-3 text-base' }[props.size]
})

function onInput(e) {
  emit('update:modelValue', e.target.value)
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
      <div
        v-if="$slots.prefix"
        class="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
      >
        <slot name="prefix" />
      </div>
      <input
        :id="inputId"
        :type="type"
        :value="modelValue"
        :placeholder="placeholder"
        :disabled="disabled || loading"
        :autofocus="autofocus"
        :required="required"
        :aria-invalid="!!error"
        :aria-describedby="error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined"
        class="w-full rounded-lg border bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500 transition-all duration-200 ease-out-expo"
        :class="[
          sizeClass,
          inputClass,
          $slots.prefix ? 'pl-10' : '',
          $slots.suffix ? 'pr-10' : '',
          error
            ? 'border-red-300 dark:border-red-700 focus:border-red-500 focus:ring-2 focus:ring-red-500/20'
            : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 dark:focus:ring-brand-500/25'
        ]"
        @input="onInput"
        @blur="emit('blur', $event)"
        @focus="emit('focus', $event)"
        @keydown="emit('keydown', $event)"
        @keyup.enter="emit('enter', $event)"
      >
      <div
        v-if="$slots.suffix"
        class="absolute right-3.5 top-1/2 -translate-y-1/2"
      >
        <slot name="suffix" />
      </div>
      <div
        v-else-if="loading"
        class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"
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
