<template>
  <footer class="bg-slate-900 border-t border-slate-800 text-slate-300 transition-all duration-300 relative shrink-0" :class="consoleOpen ? 'h-64' : 'h-10'">
    <div class="h-10 bg-slate-950 flex items-center justify-between px-6 cursor-pointer" @click="consoleOpen = !consoleOpen">
      <span class="text-xs font-semibold uppercase tracking-widest text-brand-200 flex items-center gap-2">
        <i class="fa-solid fa-terminal" :class="apiMode === 'real' ? 'text-emerald-400' : 'text-amber-400'"></i>
        API Network Live Inspector
      </span>
      <div class="flex items-center gap-4">
        <div class="flex items-center gap-1 text-[11px] font-mono-data">
          <span class="text-slate-400">Endpoint Base:</span>
          <input v-model="apiBaseUrl" @click.stop class="bg-slate-800 border border-slate-700 rounded px-2 py-0.5 text-white text-[10px] focus:outline-none w-48">
        </div>
        <button class="text-slate-400 hover:text-white text-xs">
          <i class="fa-solid" :class="consoleOpen ? 'fa-chevron-down' : 'fa-chevron-up'"></i>
        </button>
      </div>
    </div>
    <div v-show="consoleOpen && isDev" class="h-54 overflow-y-auto p-4 space-y-2 font-mono text-[11px] leading-relaxed">
      <div v-if="logs.length === 0" class="text-center text-slate-500 py-8">Sin peticiones registradas.</div>
      <div v-for="log in logs" :key="log.timestamp" class="border-b border-slate-800 pb-2 space-y-1">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <span class="text-slate-500 font-semibold">{{ log.time }}</span>
            <span :class="log.status < 300 ? 'bg-emerald-500/20 text-accent-success' : 'bg-rose-500/20 text-accent-danger'"
                  class="px-1.5 py-0.5 rounded text-[9px] font-bold">{{ log.status }}</span>
            <span class="text-brand-300 font-bold">{{ log.method }}</span>
            <span class="text-white font-semibold">{{ log.url }}</span>
          </div>
        </div>
      </div>
    </div>
  </footer>
</template>

<script setup>
import { ref } from 'vue'

defineProps({ apiMode: String, logs: Array })

const consoleOpen = ref(false)
const apiBaseUrl = ref('')
const isDev = import.meta.env.DEV
</script>
