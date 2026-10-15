<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { useOfflineSales } from '@/composables/useOfflineSales'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const hayRed = ref(navigator.onLine)
const pendingSalesCount = ref(0)
const sincronizando = ref(false)

const { syncPendingSales } = useOfflineSales()

function onOnline() {
  hayRed.value = true
  // Al reconectar, sincronizar sin esperar a que abran el POS
  syncPendingSales()
}
function onOffline() { hayRed.value = false }

async function sincronizarAhora() {
  if (sincronizando.value) return
  sincronizando.value = true
  try {
    await syncPendingSales()
  } finally {
    sincronizando.value = false
  }
}

function loadPendingCount() {
  try {
    const stored = localStorage.getItem('apex-offline-sales')
    const sales = stored ? JSON.parse(stored) : []
    pendingSalesCount.value = sales.filter((s) => !s.synced).length
  } catch {
    pendingSalesCount.value = 0
  }
}

onMounted(() => {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
  window.addEventListener('apex-pending-sales-updated', loadPendingCount)
  loadPendingCount()
})

onUnmounted(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
  window.removeEventListener('apex-pending-sales-updated', loadPendingCount)
})

// `navigator.onLine` solo sabe si hay una tarjeta de red conectada: hay
// locales con el wifi levantado y sin internet. Por eso el aviso también
// mira `auth.offline`, que se pone cuando el servidor dejó de contestar.
const isOffline = computed(() => !hayRed.value || auth.offline)
const showIndicator = computed(() => isOffline.value || pendingSalesCount.value > 0)
const indicatorClass = computed(() => isOffline.value ? 'bg-red-600' : 'bg-amber-500')
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0 -translate-y-1"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 -translate-y-1"
  >
    <div v-if="showIndicator" class="fixed top-0 left-0 right-0 z-[200] text-white text-xs text-center py-1.5 px-4 font-medium" :class="indicatorClass">
      <template v-if="isOffline">
        <i class="fa-solid fa-circle-exclamation mr-1.5"></i>
        Modo offline — trabajando con los datos de la última sesión.
        <span v-if="pendingSalesCount > 0" class="ml-1">
          {{ pendingSalesCount }} venta(s) se sincronizan al volver la conexión.
        </span>
      </template>
      <template v-else-if="pendingSalesCount > 0">
        <i class="fa-solid fa-clock-rotate-left mr-1.5"></i>
        {{ pendingSalesCount }} venta(s) pendiente(s) de sincronizar.
        <button
          type="button"
          class="ml-1.5 underline underline-offset-2 font-semibold hover:opacity-80 disabled:opacity-50"
          :disabled="sincronizando"
          @click="sincronizarAhora"
        >
          {{ sincronizando ? 'Sincronizando…' : 'Sincronizar ahora' }}
        </button>
      </template>
    </div>
  </Transition>
</template>
