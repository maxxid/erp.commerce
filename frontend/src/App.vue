<template>
  <div class="min-h-screen flex flex-col">
    <ToastContainer />

    <!-- Login / License Screen -->
    <div v-if="!auth.authenticated" class="fixed inset-0 bg-brand-900 z-50 flex items-center justify-center p-4">
      <router-view />
    </div>

    <!-- Main ERP Layout -->
    <template v-else>
      <div class="flex-1 flex w-full" style="min-height:calc(100vh - 40px)">
        <TheSidebar :cajaAbierta="cajaState.abierta" @navigate="handleNavigate" />
        <main class="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TheHeader :apiMode="apiMode" :time="currentTime" @toggleApiMode="toggleApiMode" />
          <div class="flex-1 overflow-y-auto p-8">
            <router-view />
          </div>
          <TheFooter :apiMode="apiMode" :apiBaseUrl="apiBaseUrl" :logs="apiLogs" />
        </main>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheHeader from '@/components/layout/TheHeader.vue'
import TheFooter from '@/components/layout/TheFooter.vue'
import ToastContainer from '@/components/layout/ToastContainer.vue'
import api from '@/services/api'

const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()

const apiMode = ref('mock')
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
  } catch { /* fallback: sin backend */ }
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
