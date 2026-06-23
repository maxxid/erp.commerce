<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useCajaStore } from '@/stores/caja'
import { pageLoading } from '@/router'
import router from '@/router'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheHeader from '@/components/layout/TheHeader.vue'
import TheFooter from '@/components/layout/TheFooter.vue'
import ToastContainer from '@/components/layout/ToastContainer.vue'
import CommandPalette from '@/components/layout/CommandPalette.vue'

const auth = useAuthStore()
const toast = useToastStore()
const cajaStore = useCajaStore()

const apiMode = ref('real')
const apiBaseUrl = ref('')
const apiLogs = ref([])
const currentTime = ref('')
const commandPaletteOpen = ref(false)
const networkActive = ref(false)
let clockInterval = null
let networkTimeout = null

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
}

function bumpNetwork() {
  networkActive.value = true
  clearTimeout(networkTimeout)
  networkTimeout = setTimeout(() => { networkActive.value = false }, 400)
}

watch(() => auth.authenticated, (val) => {
  if (val) cajaStore.fetchEstado()
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
  await auth.checkLicense()
  if (auth.authenticated) cajaStore.fetchEstado()
})

onUnmounted(() => {
  if (clockInterval) clearInterval(clockInterval)
  window.removeEventListener('keydown', onKeydown)
  clearTimeout(networkTimeout)
})
</script>

<template>
  <div class="min-h-screen flex flex-col bg-slate-50 dark:bg-slate-950 transition-colors duration-300">
    <ToastContainer />
    <CommandPalette v-model="commandPaletteOpen" @help="toast.info('Atajos: Ctrl+K para buscar, F2 para POS')" />

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
      <div v-if="!auth.authenticated" key="login" class="fixed inset-0 bg-slate-950 z-50 flex items-center justify-center p-4">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>

      <template v-else key="app">
        <div class="flex-1 flex w-full min-h-screen">
          <TheSidebar @navigate="handleNavigate" />
          <main class="flex-1 flex flex-col min-w-0 overflow-hidden">
            <TheHeader
              :api-mode="apiMode"
              :time="currentTime"
              :network-active="networkActive"
              @toggle-api-mode="toggleApiMode"
              @open-command-palette="openCommandPalette"
            />
            <div class="flex-1 overflow-y-auto p-6 lg:p-8 relative scroll-smooth">
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
            <TheFooter :api-mode="apiMode" :api-base-url="apiBaseUrl" :logs="apiLogs" />
          </main>
        </div>
      </template>
    </Transition>
  </div>
</template>
