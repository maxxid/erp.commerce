<script setup>
import { computed } from 'vue'

const props = defineProps({
  to: String,
  icon: String,
  label: String,
  muted: { type: Boolean, default: false },
  badge: { type: [String, Number], default: '' },
  badgeVariant: { type: String, default: 'default' },
  collapsed: { type: Boolean, default: false }
})

const emit = defineEmits(['navigate'])

const badgeClass = computed(() => {
  const map = {
    default: 'bg-slate-700 text-slate-200',
    brand: 'bg-brand-500 text-white',
    success: 'bg-emerald-500 text-white',
    warning: 'bg-amber-500 text-white',
    danger: 'bg-rose-500 text-white'
  }
  return map[props.badgeVariant] || map.default
})
</script>

<template>
  <router-link :to="to" custom v-slot="{ navigate, isActive, isExactActive }">
    <a
      :aria-current="isActive ? 'page' : undefined"
      :title="collapsed ? label : undefined"
      class="group relative flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ease-out-expo outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
      :class="[
        isActive || isExactActive
          ? 'bg-brand-600 text-white shadow-md shadow-brand-900/20'
          : 'text-slate-400 hover:bg-slate-800 hover:text-white hover:translate-x-0.5',
        muted && !(isActive || isExactActive) ? 'text-slate-500' : '',
        collapsed ? 'justify-center px-2' : ''
      ]"
      @click.prevent="emit('navigate'); navigate()"
    >
      <span
        v-if="isActive || isExactActive"
        class="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 bg-white rounded-r-full opacity-80"
      ></span>
      <i :class="`fa-solid ${icon} text-lg w-5 text-center transition-transform duration-200 group-hover:scale-105 ${collapsed ? '' : ''}`"></i>
      <span v-if="!collapsed" class="truncate">{{ label }}</span>
      <span v-if="badge && !collapsed" class="ml-auto text-[10px] font-bold px-1.5 py-0.5 rounded-full" :class="badgeClass">
        {{ badge }}
      </span>
      <span
        v-if="badge && collapsed"
        class="absolute -top-1 -right-1 w-4 h-4 text-[9px] font-bold rounded-full flex items-center justify-center"
        :class="badgeClass"
      >
        {{ badge > 9 ? '9+' : badge }}
      </span>
      <slot />
    </a>
  </router-link>
</template>
