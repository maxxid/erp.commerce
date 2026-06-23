<script setup>
const props = defineProps({
  width: { type: String, default: '100%' },
  height: { type: String, default: '1rem' },
  circle: { type: Boolean, default: false },
  rounded: { type: String, default: 'md' }, // none, sm, md, lg, full
  class: { type: String, default: '' }
})
</script>

<template>
  <div
    class="skeleton"
    :class="props.class"
    :style="{
      width,
      height,
      borderRadius: circle ? '9999px' : undefined
    }"
  ></div>
</template>
