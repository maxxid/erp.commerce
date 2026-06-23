<script setup>
import { ref, watch, onMounted } from 'vue'

const props = defineProps({
  value: { type: Number, default: 0 },
  duration: { type: Number, default: 700 },
  prefix: { type: String, default: '' },
  suffix: { type: String, default: '' },
  decimals: { type: Number, default: 0 },
  format: { type: Boolean, default: true }
})

const display = ref(0)
let rafId = null

function formatNumber(n) {
  const fixed = n.toFixed(props.decimals)
  if (!props.format) return fixed
  const [intPart, decPart] = fixed.split('.')
  const formatted = Number(intPart).toLocaleString('es-AR')
  return decPart ? `${formatted},${decPart}` : formatted
}

function animate(from, to) {
  if (rafId) cancelAnimationFrame(rafId)
  const start = performance.now()
  const diff = to - from

  function step(now) {
    const elapsed = now - start
    const progress = Math.min(elapsed / props.duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    display.value = from + diff * eased
    if (progress < 1) {
      rafId = requestAnimationFrame(step)
    }
  }
  rafId = requestAnimationFrame(step)
}

onMounted(() => {
  display.value = 0
  animate(0, props.value)
})

watch(() => props.value, (newVal, oldVal) => {
  animate(oldVal || 0, newVal)
})
</script>

<template>
  <span class="tabular-nums tracking-tight">
    {{ prefix }}{{ formatNumber(display) }}{{ suffix }}
  </span>
</template>
