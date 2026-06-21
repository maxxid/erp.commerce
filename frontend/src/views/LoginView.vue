<template>
  <div class="bg-white rounded-3xl p-8 max-w-md w-full shadow-2xl border border-slate-100 flex flex-col space-y-6">
    <div class="text-center">
      <div class="w-16 h-16 rounded-2xl bg-brand-600 text-white flex items-center justify-center text-3xl mx-auto shadow-lg shadow-brand-600/30">
        <i class="fa-solid fa-cubes-stacked"></i>
      </div>
      <h2 class="text-2xl font-bold text-slate-900 mt-4 font-display">
        {{ title }}
      </h2>
      <p v-if="!auth.licenseChecked" class="text-sm text-slate-400 mt-1">
        <i class="fa-solid fa-circle-notch animate-spin mr-1"></i> Verificando licencia...
      </p>
      <p v-if="auth.licenseChecked && auth.hasLicense && auth.licenseValid" class="text-sm text-slate-500 mt-1">Conexión unificada con el Core de DeepSeek</p>
      <p v-if="auth.licenseChecked && auth.hasLicense && !auth.licenseValid" class="text-sm text-rose-500 mt-1 font-bold">Tu licencia expiró. Ingresá una nueva clave.</p>
      <p v-if="auth.licenseChecked && !auth.hasLicense" class="text-sm text-slate-500 mt-1">Ingresá la clave de licencia proporcionada por tu proveedor</p>
    </div>

    <!-- License Activation -->
    <div v-if="auth.licenseChecked && (!auth.hasLicense || !auth.licenseValid)" class="space-y-4">
      <div v-if="auth.machineId" class="p-2 bg-slate-50 border border-slate-200 rounded-lg text-center">
        <span class="text-[9px] text-slate-400 uppercase block">ID de esta máquina</span>
        <span class="text-xs font-mono-data font-bold text-slate-600 select-all">{{ auth.machineId }}</span>
        <span class="text-[9px] text-slate-400 block mt-0.5">Enviá este ID a tu proveedor para recibir la clave</span>
      </div>
      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Clave de Licencia</label>
        <input v-model="auth.licenseKey" @keydown.enter="auth.activateLicense()"
               placeholder="APX-XXXX-XXXX-XXXX" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-3 text-sm font-mono text-center uppercase focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition">
      </div>
      <div v-if="auth.licenseError" class="p-2 bg-rose-50 text-rose-600 rounded-lg text-xs text-center">{{ auth.licenseError }}</div>
      <div v-if="auth.licenseOk" class="p-2 bg-emerald-50 text-emerald-600 rounded-lg text-xs text-center">{{ auth.licenseOk }}</div>
      <button @click="auth.activateLicense()" class="w-full bg-brand-600 hover:bg-brand-700 text-white py-3 rounded-xl text-sm font-semibold transition">
        <i class="fa-solid fa-key mr-2"></i> Activar Licencia
      </button>
    </div>

    <!-- Login Form -->
    <div v-if="auth.licenseChecked && auth.hasLicense && auth.licenseValid" class="space-y-4">
      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Usuario</label>
        <div class="relative">
          <i class="fa-regular fa-user absolute left-4 top-3.5 text-slate-400"></i>
          <input v-model="auth.loginForm.username" @keydown.enter.prevent="$refs.loginPassword?.focus()"
                 class="w-full bg-slate-50 border border-slate-200 rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition">
        </div>
      </div>
      <div>
        <label class="block text-xs font-semibold uppercase tracking-wider text-slate-500 mb-1.5">Contraseña</label>
        <div class="relative">
          <i class="fa-solid fa-lock absolute left-4 top-3.5 text-slate-400"></i>
          <input ref="loginPassword" v-model="auth.loginForm.password" type="password" @keydown.enter="doLogin()"
                 class="w-full bg-slate-50 border border-slate-200 rounded-xl pl-11 pr-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition">
        </div>
      </div>

      <div v-if="auth.loginError" class="p-3 bg-rose-50 text-accent-danger rounded-xl border border-rose-100 text-xs font-medium flex items-center gap-2">
        <i class="fa-solid fa-triangle-exclamation"></i>
        <span>{{ auth.loginError }}</span>
      </div>

      <button @click="doLogin()" class="w-full bg-brand-600 hover:bg-brand-700 text-white py-3.5 rounded-xl text-sm font-semibold shadow-lg shadow-brand-600/25 transition flex items-center justify-center gap-2">
        <span>{{ auth.loggingIn ? 'Conectando...' : 'Conectar' }}</span>
        <i class="fa-solid" :class="auth.loggingIn ? 'fa-spinner animate-spin' : 'fa-arrow-right'"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'

const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()

const title = computed(() => {
  if (!auth.licenseChecked) return 'Cargando...'
  if (auth.hasLicense && auth.licenseValid) return 'Ingresar a ApexERP'
  return 'Activar Licencia'
})

async function doLogin() {
  const ok = await auth.handleLogin()
  if (ok) {
    router.push('/dashboard')
  }
}
</script>
