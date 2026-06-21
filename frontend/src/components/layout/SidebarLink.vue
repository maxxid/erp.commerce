<template>
  <router-link :to="to" custom v-slot="{ navigate, isActive }">
    <a @click.prevent="$emit('navigate'); navigate()"
       :class="[isActive ? 'bg-brand-600 text-white font-semibold' : 'hover:bg-slate-800 hover:text-white', { 'text-slate-400': muted }]"
       class="w-full flex items-center gap-3.5 px-4 py-3 rounded-xl text-sm transition duration-150">
      <i :class="`fa-solid ${icon} text-lg w-5 text-center`"></i>
      <span>{{ label }}</span>
      <slot />
    </a>
  </router-link>
</template>

<script setup>
defineProps({
  to: String,
  icon: String,
  label: String,
  muted: { type: Boolean, default: false }
})
</script>
