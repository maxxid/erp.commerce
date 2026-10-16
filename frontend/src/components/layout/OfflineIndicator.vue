<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { totalDeVenta } from '@/composables/useOfflineSales'
import { useOfflineSync } from '@/composables/useOfflineSync'
import { useOfflineCaja } from '@/composables/useOfflineCaja'
import { useAuthStore } from '@/stores/auth'
import { useProductosStore } from '@/stores/productos'
import { formatCurrency as fc } from '@/composables/useUtils'

const auth = useAuthStore()
const productosStore = useProductosStore()
const hayRed = ref(navigator.onLine)
const pendingSalesCount = ref(0)
const pendingCajaCount = ref(0)
const montoSinSubir = ref(0)
const sincronizando = ref(false)

const { sincronizarPendientes } = useOfflineSync()
const { pendientes: operacionesDeCajaPendientes } = useOfflineCaja()

function onOnline() {
  hayRed.value = true
  // Al reconectar, sincronizar sin esperar a que abran el POS
  sincronizarPendientes()
}
function onOffline() { hayRed.value = false }

async function sincronizarAhora() {
  if (sincronizando.value) return
  sincronizando.value = true
  try {
    await sincronizarPendientes()
  } finally {
    sincronizando.value = false
  }
}

function loadPendingCount() {
  try {
    const stored = localStorage.getItem('apex-offline-sales')
    const sales = stored ? JSON.parse(stored) : []
    const pendientes = sales.filter((s) => !s.synced)
    pendingSalesCount.value = pendientes.length
    // "3 ventas sin subir" no dice si son $3.000 o $300.000: es la diferencia
    // entre un detalle y algo que hay que resolver antes de cerrar.
    montoSinSubir.value = pendientes.reduce(
      (suma, s) => suma + (typeof s.total === 'number' ? s.total : totalDeVenta(s.data)),
      0
    )
    // Una apertura o un cierre sin subir también es plata/jornada en el aire,
    // y no tiene importe: se cuenta nomás.
    pendingCajaCount.value = operacionesDeCajaPendientes().length
  } catch {
    pendingSalesCount.value = 0
    pendingCajaCount.value = 0
    montoSinSubir.value = 0
  }
}

onMounted(() => {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
  window.addEventListener('apex-pending-sales-updated', loadPendingCount)
  window.addEventListener('apex-pending-caja-updated', loadPendingCount)
  loadPendingCount()
})

onUnmounted(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
  window.removeEventListener('apex-pending-sales-updated', loadPendingCount)
  window.removeEventListener('apex-pending-caja-updated', loadPendingCount)
})

// `navigator.onLine` solo sabe si hay una tarjeta de red conectada: hay
// locales con el wifi levantado y sin internet. Por eso el aviso también
// mira `auth.offline`, que se pone cuando el servidor dejó de contestar.
const isOffline = computed(() => !hayRed.value || auth.offline)
const showIndicator = computed(() =>
  isOffline.value || productosStore.sinRed || pendingSalesCount.value > 0
    || pendingCajaCount.value > 0
)
const indicatorClass = computed(() => isOffline.value ? 'bg-red-600' : 'bg-amber-500')

// Cuánto tiene el catálogo que se está usando. Es la pregunta que importa
// cuando no hay red: si el precio que se cobra es el de hoy o el de ayer.
function haceCuanto(iso) {
  if (!iso) return null
  const ms = Date.now() - new Date(iso).getTime()
  if (!Number.isFinite(ms) || ms < 0) return null
  const min = Math.round(ms / 60000)
  if (min < 1) return 'recién actualizado'
  if (min < 60) return `de hace ${min} min`
  const horas = Math.round(min / 60)
  if (horas < 24) return `de hace ${horas} h`
  return `de hace ${Math.round(horas / 24)} d`
}

const antiguedadCatalogo = computed(() => haceCuanto(productosStore.datosDe))
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
        <span v-if="antiguedadCatalogo" class="ml-1">
          Catálogo {{ antiguedadCatalogo }}.
        </span>
        <span v-if="pendingSalesCount > 0" class="ml-1">
          {{ pendingSalesCount }} venta(s) sin subir ({{ fc(montoSinSubir) }}): se mandan solas al volver la conexión.
        </span>
        <span v-if="pendingCajaCount > 0" class="ml-1">
          {{ pendingCajaCount }} movimiento(s) de caja sin subir.
        </span>
      </template>
      <template v-else-if="productosStore.sinRed">
        <i class="fa-solid fa-triangle-exclamation mr-1.5"></i>
        No se pudo actualizar el catálogo — se vende con los datos
        {{ antiguedadCatalogo || 'de la última sesión' }}.
        <span v-if="pendingSalesCount > 0" class="ml-1">
          {{ pendingSalesCount }} venta(s) sin subir: {{ fc(montoSinSubir) }}.
        </span>
        <span v-if="pendingCajaCount > 0" class="ml-1">
          {{ pendingCajaCount }} movimiento(s) de caja sin subir.
        </span>
      </template>
      <template v-else-if="pendingSalesCount > 0 || pendingCajaCount > 0">
        <i class="fa-solid fa-clock-rotate-left mr-1.5"></i>
        <span v-if="pendingSalesCount > 0">
          {{ pendingSalesCount }} venta(s) sin subir — {{ fc(montoSinSubir) }}.
        </span>
        <span v-else>
          {{ pendingCajaCount }} movimiento(s) de caja sin subir.
        </span>
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
