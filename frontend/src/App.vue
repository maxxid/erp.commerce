<template>
  <div class="min-h-screen flex flex-col">
    <ToastContainer />

    <div v-if="pageLoading" class="fixed top-0 left-0 right-0 z-[100] h-0.5 bg-brand-100">
      <div class="h-full bg-brand-600 animate-loading-bar"></div>
    </div>

    <div v-if="!auth.authenticated" class="fixed inset-0 bg-brand-900 z-50 flex items-center justify-center p-4">
      <router-view v-slot="{ Component }">
        <component :is="Component" />
      </router-view>
    </div>

    <template v-else>
      <div class="flex-1 flex w-full" style="min-height:calc(100vh - 40px)">
        <TheSidebar @navigate="handleNavigate" />
        <main class="flex-1 flex flex-col min-w-0 overflow-hidden">
          <TheHeader :apiMode="apiMode" :time="currentTime" @toggleApiMode="toggleApiMode" />
          <div class="flex-1 overflow-y-auto p-8 relative">
            <router-view :key="$route.fullPath" />
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
import { useCajaStore } from '@/stores/caja'
import { pageLoading } from '@/router'
import TheSidebar from '@/components/layout/TheSidebar.vue'
import TheHeader from '@/components/layout/TheHeader.vue'
import TheFooter from '@/components/layout/TheFooter.vue'
import ToastContainer from '@/components/layout/ToastContainer.vue'

const auth = useAuthStore()
const toast = useToastStore()
const cajaStore = useCajaStore()

const apiMode = ref('real')
const apiBaseUrl = ref('')
const apiLogs = ref([])
const currentTime = ref('')
let clockInterval = null

function toggleApiMode(mode) {
  apiMode.value = mode
  toast.add('info', `Modo: ${mode === 'real' ? 'API FastAPI Real' : 'Simulador Offline'}`)
}

function handleNavigate() {}

watch(() => auth.authenticated, (val) => {
  if (val) cajaStore.fetchEstado()
})

onMounted(async () => {
  clockInterval = setInterval(() => {
    currentTime.value = new Date().toLocaleTimeString()
  }, 1000)
  await auth.checkLicense()
  if (auth.authenticated) cajaStore.fetchEstado()
})
onUnmounted(() => {
  if (clockInterval) clearInterval(clockInterval)
})
</script>
