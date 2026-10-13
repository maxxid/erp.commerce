<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useNotificacionesStore } from '@/stores/notificaciones'
import { timeAgo } from '@/composables/useUtils'

const store = useNotificacionesStore()
const router = useRouter()
const raiz = ref(null)

const pendientes = computed(() => store.avisos.filter(a => !a.leida))

function toggle() {
  store.panelAbierto = !store.panelAbierto
}

function fueraDelPanel(e) {
  if (raiz.value && !raiz.value.contains(e.target)) store.panelAbierto = false
}

onMounted(() => document.addEventListener('click', fueraDelPanel))
onUnmounted(() => document.removeEventListener('click', fueraDelPanel))

// A dónde lleva cada tipo de aviso cuando se hace clic.
const destinos = {
  stock_bajo: { name: 'products', query: { stock: 'bajo' } },
  sin_stock: { name: 'products', query: { stock: 'bajo' } },
  caja_abierta: { name: 'caja' },
  licencia: { name: 'licencias' },
  lotes_vencidos: { name: 'products' },
  lotes_por_vencer: { name: 'products' },
}

async function abrir(aviso) {
  store.panelAbierto = false
  await store.marcarLeida(aviso.id)
  const destino = destinos[aviso.tipo]
  if (destino) router.push(destino)
}

async function marcarTodas() {
  await store.marcarTodas()
}
</script>

<template>
  <div class="relative" ref="raiz">
    <button
      type="button"
      aria-label="Avisos"
      :title="`${store.noLeidas} aviso(s) sin leer`"
      class="relative w-9 h-9 rounded-lg flex items-center justify-center transition-colors outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
      :class="store.noLeidas > 0
        ? 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20'
        : 'text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
      @click="toggle"
    >
      <i class="fa-solid fa-bell"></i>
      <span
        v-if="store.noLeidas > 0"
        class="absolute -top-0.5 -right-0.5 min-w-[18px] h-[18px] px-1 rounded-full bg-red-500 text-white text-[10px] font-bold flex items-center justify-center"
      >{{ store.noLeidas > 99 ? '99+' : store.noLeidas }}</span>
    </button>

    <div
      v-if="store.panelAbierto"
      class="absolute right-0 mt-2 w-[22rem] max-w-[92vw] rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 shadow-xl z-50 overflow-hidden"
    >
      <div class="flex items-center justify-between px-4 py-3 border-b border-slate-100 dark:border-slate-800">
        <span class="text-sm font-semibold text-slate-800 dark:text-white">Avisos</span>
        <button
          v-if="store.noLeidas > 0"
          type="button"
          class="text-xs text-brand-600 dark:text-brand-400 hover:underline"
          @click="marcarTodas"
        >Marcar todas como leídas</button>
      </div>

      <div v-if="store.cargando && !store.avisos.length" class="p-4 space-y-2">
        <div v-for="i in 3" :key="i" class="h-10 rounded-lg bg-slate-100 dark:bg-slate-800 animate-pulse"></div>
      </div>

      <div v-else-if="!store.avisos.length" class="p-6 text-center">
        <i class="fa-solid fa-check-circle text-emerald-500 text-xl"></i>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-2">Todo en orden: no hay avisos.</p>
      </div>

      <div v-else class="max-h-[22rem] overflow-y-auto">
        <button
          v-for="a in store.avisos"
          :key="a.id"
          type="button"
          class="w-full text-left px-4 py-3 flex gap-3 border-b border-slate-50 dark:border-slate-800/50 transition-colors hover:bg-slate-50 dark:hover:bg-slate-800/60"
          :class="a.leida ? 'opacity-60' : ''"
          @click="abrir(a)"
        >
          <span
            class="mt-1 w-2 h-2 rounded-full shrink-0"
            :class="a.leida
              ? 'bg-slate-300 dark:bg-slate-600'
              : (a.nivel === 'danger' ? 'bg-red-500' : 'bg-amber-500')"
          ></span>
          <span class="min-w-0">
            <span class="flex items-center gap-2">
              <span class="text-xs font-semibold text-slate-800 dark:text-white truncate">{{ a.titulo }}</span>
              <span class="text-[10px] text-slate-400 shrink-0">{{ timeAgo(a.creada_en) }}</span>
            </span>
            <span class="block text-xs text-slate-500 dark:text-slate-400 break-words">{{ a.mensaje }}</span>
          </span>
        </button>
      </div>
    </div>
  </div>
</template>
