<template>
  <header class="bg-white border-b border-slate-200 h-16 shrink-0 flex items-center justify-between px-8 z-10">
    <div class="flex items-center gap-3">
      <span class="text-slate-400 text-sm">ERP Fase 5 Vue</span>
      <i class="fa-solid fa-chevron-right text-xs text-slate-300"></i>
      <span class="text-brand-600 font-semibold text-sm uppercase tracking-wider font-display">{{ route.name }}</span>
    </div>
    <div class="flex items-center gap-4">
      <button @click="$emit('toggleApiMode', 'mock')" :class="apiMode === 'mock' ? 'bg-white shadow-sm font-bold text-slate-800' : 'text-slate-500'"
              class="px-3 py-1 rounded-lg text-[11px] uppercase tracking-wide bg-slate-100 border border-slate-200 transition duration-150">
        Simulador
      </button>
      <button @click="$emit('toggleApiMode', 'real')" :class="apiMode === 'real' ? 'bg-brand-600 text-white font-bold' : 'text-slate-500'"
              class="px-3 py-1 rounded-lg text-[11px] uppercase tracking-wide bg-slate-100 border border-slate-200 transition duration-150">
        API Real
      </button>
      <span class="text-slate-300">|</span>
      <button class="text-slate-400 hover:text-slate-600 transition" title="Ajustes">
        <i class="fa-solid fa-gear"></i>
      </button>
      <span class="text-xs font-mono-data text-slate-400">{{ time }}</span>
    </div>
  </header>
</template>

<script setup>
import { useRoute } from 'vue-router'

defineProps({ apiMode: String, time: String })
defineEmits(['toggleApiMode'])

const route = useRoute()
</script>
