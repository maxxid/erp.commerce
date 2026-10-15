<script setup>
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useCajaStore } from '@/stores/caja'
import { useNotificacionesStore } from '@/stores/notificaciones'
import { useCalculadoraStore } from '@/stores/calculadora'
import { pageLoading } from '@/router'
import router from '@/router'
import api from '@/services/api'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheHeader from '@/components/layout/TheHeader.vue'
import TheFooter from '@/components/layout/TheFooter.vue'
import TheBottomNav from '@/components/layout/TheBottomNav.vue'
import ToastContainer from '@/components/layout/ToastContainer.vue'
import CommandPalette from '@/components/layout/CommandPalette.vue'
import OfflineIndicator from '@/components/layout/OfflineIndicator.vue'
import KeyboardShortcutsModal from '@/components/layout/KeyboardShortcutsModal.vue'
import CalculadoraFlotante from '@/components/caja/CalculadoraFlotante.vue'

const auth = useAuthStore()
const toast = useToastStore()
const cajaStore = useCajaStore()
const notificacionesStore = useNotificacionesStore()

const apiMode = ref('real')
const apiBaseUrl = ref('')
const apiLogs = ref([])
const currentTime = ref('')
const commandPaletteOpen = ref(false)
const networkActive = ref(false)
const shortcutsModalOpen = ref(false)
const menuAbierto = ref(false)
let clockInterval = null
let networkTimeout = null
let lastTokenCheck = 0

const TOKEN_RECHECK_MS = 5 * 60 * 1000

const globalShortcuts = [
  { key: 'Ctrl+K', description: 'Abrir búsqueda global' },
  { key: 'F2', description: 'Ir al POS de Ventas' },
  { key: '?', description: 'Ver atajos de teclado' },
  { key: 'Esc', description: 'Cerrar modales / búsqueda' }
]

const calculadoraStore = useCalculadoraStore()

const mostrarCalculadora = computed(() => {
  const alcance = calculadoraStore.alcance
  const ruta = router.currentRoute.value.name
  if (alcance === 'global') return true
  if (alcance === 'pos-productos') return ['pos', 'products'].includes(ruta)
  return false
})

function toggleApiMode(mode) {
  apiMode.value = mode
  toast.info(`Modo: ${mode === 'real' ? 'API FastAPI Real' : 'Simulador Offline'}`)
}

function handleNavigate() {}

function openCommandPalette() {
  commandPaletteOpen.value = true
}

function onKeydown(e) {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    commandPaletteOpen.value = true
  }
  if (e.key === 'F2' && auth.authenticated) {
    e.preventDefault()
    router.push('/pos')
  }
  if (e.key === '?' && auth.authenticated) {
    e.preventDefault()
    shortcutsModalOpen.value = true
  }
}

function bumpNetwork() {
  networkActive.value = true
  clearTimeout(networkTimeout)
  networkTimeout = setTimeout(() => { networkActive.value = false }, 400)
}

function syncCatalogoSilently() {
  const lastSync = localStorage.getItem('catalogo_last_sync')
  const hour = 60 * 60 * 1000
  if (lastSync && Date.now() - Number(lastSync) < hour) return
  api.post('/api/catalogo/descargar').then(() => {
    localStorage.setItem('catalogo_last_sync', String(Date.now()))
  }).catch(() => {})
}

// El token vence a las 20 h; sin esto la app seguía "logueada" en memoria
// y todas las llamadas fallaban 401 en silencio hasta un hard refresh.
function onSessionExpired() {
  if (!auth.authenticated) return
  auth.logout()
  toast.warning('Sesión expirada, volvé a iniciar sesión')
  const redirect = router.currentRoute.value.fullPath
  router.push({ path: '/login', query: redirect === '/login' ? {} : { redirect } })
}

// Al volver a la pestaña (p. ej. después de un rato en otra), revalidamos
// el token contra el backend. Throttle de 5 min para no llamar en cada
// ida y vuelta chica.
async function revalidarTokenSilencioso() {
  if (!auth.authenticated) return
  const ahora = Date.now()
  if (ahora - lastTokenCheck < TOKEN_RECHECK_MS) return
  lastTokenCheck = ahora
  try {
    await api.get('/api/auth/me')
  } catch { /* el 401 ya dispara onSessionExpired vía api.js */ }
}

// Volvió la internet: se vuelve a preguntar licencia y token al servidor, así
// sale el modo offline y se ve si algo cambió mientras estuvimos caídos.
function onOnline() {
  auth.revalidar()
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') revalidarTokenSilencioso()
}

// Service worker actualizado → recargamos una sola vez para levantar el
// shell nuevo (si no, el index.html viejo seguía pidiendo chunks 404).
function onControllerChange() {
  window.location.reload()
}

watch(() => router.currentRoute.value.fullPath, () => { menuAbierto.value = false })

watch(() => auth.authenticated, (val) => {
  if (val) {
    cajaStore.fetchEstado()
    notificacionesStore.fetch()
    syncCatalogoSilently()
  }
})

onMounted(async () => {
  clockInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString()
  }, 1000)
  window.addEventListener('keydown', onKeydown)
  // Hook global de red
  const origFetch = window.fetch
  window.fetch = async function (...args) {
    bumpNetwork()
    return origFetch.apply(this, args)
  }
  window.addEventListener('apex:session-expired', onSessionExpired)
  window.addEventListener('online', onOnline)
  document.addEventListener('visibilitychange', onVisibilityChange)
  // Solo recargar si ya había un SW controlando (no en la primera
  // instalación, que claim() también dispara controllerchange).
  if ('serviceWorker' in navigator) {
    const yaHabiaController = !!navigator.serviceWorker.controller
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (yaHabiaController) onControllerChange()
    })
  }
  await auth.checkLicense()
  if (auth.authenticated) {
    cajaStore.fetchEstado()
    notificacionesStore.fetch()
    syncCatalogoSilently()
  }
})

onUnmounted(() => {
  if (clockInterval) clearInterval(clockInterval)
  window.removeEventListener('keydown', onKeydown)
  window.removeEventListener('apex:session-expired', onSessionExpired)
  window.removeEventListener('online', onOnline)
  document.removeEventListener('visibilitychange', onVisibilityChange)
  clearTimeout(networkTimeout)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
    <ToastContainer />
    <OfflineIndicator />
    <CommandPalette v-model="commandPaletteOpen" @help="shortcutsModalOpen = true" />
    <KeyboardShortcutsModal v-model="shortcutsModalOpen" :global-shortcuts="globalShortcuts" />

    <Transition
      enter-active-class="transition duration-300 ease-out-expo"
      enter-from-class="opacity-0 -translate-y-1"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-1"
    >
      <div v-if="pageLoading" class="fixed top-0 left-0 right-0 z-[100] h-0.5 bg-brand-100 dark:bg-brand-900/30 overflow-hidden">
        <div class="h-full bg-brand-600 animate-loading-bar rounded-full"></div>
      </div>
    </Transition>

    <Transition
      enter-active-class="transition duration-300 ease-out-expo"
      enter-from-class="opacity-0 scale-[0.98]"
      enter-to-class="opacity-100 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 scale-100"
      leave-to-class="opacity-0 scale-[0.98]"
      mode="out-in"
    >
      <!-- Loading inicial mientras verifica licencia -->
      <div v-if="auth.initializing" key="loading" class="fixed inset-0 bg-slate-950 z-50 flex items-center justify-center">
        <div class="flex flex-col items-center gap-4">
          <i class="fa-solid fa-cubes-stacked text-brand-500 text-4xl animate-pulse"></i>
          <span class="text-slate-400 text-sm">Verificando...</span>
        </div>
      </div>

      <div v-else-if="!auth.authenticated" key="login" class="fixed inset-0 bg-slate-950 z-50 flex items-center justify-center p-4">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>

      <template v-else key="app">
        <router-view v-if="$route.meta.bare" />
        <div v-else class="flex-1 flex w-full min-h-screen">
          <TheSidebar
            :mobile-open="menuAbierto"
            @navigate="handleNavigate"
            @close-mobile="menuAbierto = false"
          />
          <main class="flex-1 flex flex-col min-w-0 overflow-hidden">
            <TheHeader
              :api-mode="apiMode"
              :time="currentTime"
              :network-active="networkActive"
              @toggle-api-mode="toggleApiMode"
              @open-command-palette="openCommandPalette"
              @toggle-menu="menuAbierto = !menuAbierto"
            />
            <div class="flex-1 overflow-y-auto relative scroll-smooth">
              <div class="p-4 md:p-6 lg:p-8 pt-2 pb-24 md:pb-8">
              <router-view v-slot="{ Component, route }">
                <Transition
                  name="page"
                  mode="out-in"
                  enter-active-class="transition duration-250 ease-out-expo"
                  enter-from-class="opacity-0 translate-y-3 scale-[0.995]"
                  enter-to-class="opacity-100 translate-y-0 scale-100"
                  leave-active-class="transition duration-150 ease-in"
                  leave-from-class="opacity-100 translate-y-0 scale-100"
                  leave-to-class="opacity-0 -translate-y-2 scale-[0.995]"
                >
                  <div :key="route.fullPath">
                    <component :is="Component" />
                  </div>
                </Transition>
              </router-view>

              <Transition
                enter-active-class="transition duration-200 ease-out"
                enter-from-class="opacity-0"
                enter-to-class="opacity-100"
                leave-active-class="transition duration-150 ease-in"
                leave-from-class="opacity-100"
                leave-to-class="opacity-0"
              >
                <div v-if="pageLoading" class="absolute inset-0 bg-white/70 dark:bg-slate-950/70 backdrop-blur-[2px] flex items-center justify-center z-10">
                  <div class="flex flex-col items-center gap-3">
                    <div class="relative">
                      <i class="fa-solid fa-circle-notch animate-spin text-brand-600 text-3xl"></i>
                      <div class="absolute inset-0 animate-ping rounded-full bg-brand-500/20"></div>
                    </div>
                    <span class="text-sm font-semibold text-slate-600 dark:text-slate-300">Cargando...</span>
                  </div>
                </div>
              </Transition>
              </div>
            </div>
            <div class="hidden md:block">
              <TheFooter :api-mode="apiMode" :api-base-url="apiBaseUrl" :logs="apiLogs" />
            </div>
          </main>
        </div>

        <TheBottomNav v-if="!$route.meta.bare" />

        <!-- Calculadora Flotante - Condicional según settings -->
        <CalculadoraFlotante v-if="mostrarCalculadora" />
      </template>
    </Transition>
  </div>
</template>
