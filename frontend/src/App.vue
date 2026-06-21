<template>
  <div class="min-h-screen flex flex-col">
    <ToastContainer />

    <!-- Loading bar global -->
    <div v-if="pageLoading" class="fixed top-0 left-0 right-0 z-[100] h-0.5 bg-brand-100">
      <div class="h-full bg-brand-600 animate-loading-bar"></div>
    </div>

    <!-- Login / License Screen -->
    <div v-if="!auth.authenticated" class="fixed inset-0 bg-brand-900 z-50 flex items-center justify-center p-4">
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </div>

    <!-- Main ERP Layout -->
    <template v-else>
      <div class="flex-1 flex w-full" style="min-height:calc(100vh - 40px)">
        <TheSidebar :cajaAbierta="cajaState.abierta" @navigate="handleNavigate" />
        <main class="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TheHeader :apiMode="apiMode" :time="currentTime" @toggleApiMode="toggleApiMode" />
          <div class="flex-1 overflow-y-auto p-8 relative">
            <!-- Vista activa con transición fade -->
            <router-view v-slot="{ Component }">
              <transition name="fade" mode="out-in">
                <component :is="Component" />
              </transition>
            </router-view>
            <!-- Spinner overlay durante carga de vista -->
            <div v-if="pageLoading" class="absolute inset-0 bg-white/60 flex items-center justify-center z-10">
              <div class="flex flex-col items-center gap-3">
                <i class="fa-solid fa-circle-notch animate-spin text-brand-600 text-3xl"></i>
                <span class="text-sm text-slate-500 font-semibold">Cargando...</span>
              </div>
            </div>
          </div>
          <TheFooter :apiMode="apiMode" :apiBaseUrl="apiBaseUrl" :logs="apiLogs" />
        </main>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { pageLoading } from '@/router'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheHeader from '@/components/layout/TheHeader.vue'
import TheFooter from '@/components/layout/TheFooter.vue'
import ToastContainer from '@/components/layout/ToastContainer.vue'
import api from '@/services/api'

const auth = useAuthStore()
const toast = useToastStore()

const apiMode = ref('real')
const apiBaseUrl = ref('')
const apiLogs = ref([])
const currentTime = ref('')
const cajaState = ref({ abierta: false, saldo_actual: 0 })
let clockInterval = null

function toggleApiMode(mode) {
  apiMode.value = mode
  toast.add('info', `Modo: ${mode === 'real' ? 'API FastAPI Real' : 'Simulador Offline'}`)
}

function handleNavigate() {}

async function fetchCajaState() {
  if (!auth.authenticated) return
  try {
    const state = await api.get('/api/caja/estado')
    if (state) cajaState.value = state
  } catch { /* fallback */ }
}

watch(() => auth.authenticated, (val) => {
  if (val) fetchCajaState()
})

onMounted(async () => {
  clockInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString()
  }, 1000)
  await auth.checkLicense()
  if (auth.authenticated) fetchCajaState()
})
onUnmounted(() => {
  if (clockInterval) clearInterval(clockInterval)
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.animate-loading-bar {
  animation: loadingBar 1.5s ease-in-out infinite;
  width: 30%;
}
@keyframes loadingBar {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(400%); }
}
</style>
