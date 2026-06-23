<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'primary' }, // primary, secondary, ghost, danger
  size: { type: String, default: 'md' }, // xs, sm, md, lg
  loading: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  block: { type: Boolean, default: false },
  iconOnly: { type: Boolean, default: false },
  type: { type: String, default: 'button' },
  ariaLabel: { type: String, default: '' }
})

const emit = defineEmits(['click'])

const sizeClasses = computed(() => {
  if (props.iconOnly) {
    return {
      xs: 'w-7 h-7 text-xs',
      sm: 'w-8 h-8 text-sm',
      md: 'w-9 h-9 text-base',
      lg: 'w-10 h-10 text-lg'
    }[props.size]
  }
  return {
    xs: 'px-2.5 py-1 text-xs',
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2 text-sm',
    lg: 'px-5 py-2.5 text-sm'
  }[props.size]
})

const variantClasses = computed(() => {
  const map = {
    primary: 'btn-primary',
    secondary: 'btn-secondary',
    ghost: 'btn-ghost',
    danger: 'btn-danger'
  }
  return map[props.variant] || map.primary
})

const isDisabled = computed(() => props.disabled || props.loading)
</script>

<template>
  <button
    :type="type"
    :disabled="isDisabled"
    :aria-label="ariaLabel || undefined"
    class="btn-base relative overflow-hidden"
    :class="[
      variantClasses,
      sizeClasses,
      { 'w-full': block, '!rounded-full': iconOnly, 'opacity-60 cursor-not-allowed': isDisabled }
    ]"
    @click="emit('click', $event)"
  >
    <span
      v-if="loading"
      class="absolute inset-0 flex items-center justify-center"
    >
      <i class="fa-solid fa-circle-notch fa-spin"></i>
    </span>
    <span :class="{ 'opacity-0': loading, 'flex items-center gap-2': !iconOnly }">
      <slot />
    </span>
  </button>
</template>
