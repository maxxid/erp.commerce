<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'

const auth = useAuthStore()
const toast = useToastStore()
const router = useRouter()

const showPassword = ref(false)
const copied = ref(false)

onMounted(() => {
  if (auth.authenticated) {
    router.replace('/dashboard')
  }
})

const title = computed(() => {
  if (!auth.licenseChecked) return 'Cargando...'
  if (auth.hasLicense && auth.licenseValid) return 'Ingresar a ApexERP'
  return 'Activar Licencia'
})

async function doLogin() {
  const ok = await auth.handleLogin()
  if (ok) {
    toast.success(`Bienvenido, ${auth.currentUser?.nombre || auth.loginForm.username}`)
    router.push('/dashboard')
  }
}

function copyMachineId() {
  if (!auth.machineId) return
  navigator.clipboard.writeText(auth.machineId).then(() => {
    copied.value = true
    setTimeout(() => { copied.value = false }, 1500)
  })
}
</script>

<template>
  <div class="w-full max-w-md relative z-10">
    <Transition
      enter-active-class="transition duration-500 ease-out-expo"
      enter-from-class="opacity-0 translate-y-6 scale-[0.97]"
      enter-to-class="opacity-100 translate-y-0 scale-100"
      leave-active-class="transition duration-300 ease-in"
      leave-from-class="opacity-100 translate-y-0 scale-100"
      leave-to-class="opacity-0 -translate-y-4 scale-[0.97]"
      appear
    >
      <div class="glass rounded-3xl p-8 w-full shadow-2xl shadow-brand-900/20">
        <div class="text-center mb-8">
          <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-white flex items-center justify-center text-3xl mx-auto shadow-lg shadow-brand-600/30 mb-4 ring-4 ring-brand-500/10">
            <i class="fa-solid fa-cubes-stacked"></i>
          </div>
          <h2 class="text-2xl font-bold text-slate-900 dark:text-white font-display">
            {{ title }}
          </h2>
          <p v-if="!auth.licenseChecked" class="text-sm text-slate-500 dark:text-slate-400 mt-2 flex items-center justify-center gap-2">
            <i class="fa-solid fa-circle-notch animate-spin"></i>
            Verificando licencia...
          </p>
          <p v-if="auth.licenseChecked && auth.hasLicense && auth.licenseValid" class="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Sistema comercial unificado
          </p>
          <p v-if="auth.licenseChecked && auth.hasLicense && !auth.licenseValid" class="text-sm text-red-500 mt-2 font-semibold flex items-center justify-center gap-2">
            <i class="fa-solid fa-triangle-exclamation"></i>
            Tu licencia expiró. Ingresá una nueva clave.
          </p>
          <p v-if="auth.licenseChecked && !auth.hasLicense" class="text-sm text-slate-500 dark:text-slate-400 mt-2">
            Ingresá la clave de licencia proporcionada por tu proveedor
          </p>
        </div>

        <!-- License Activation -->
        <div v-if="auth.licenseChecked && (!auth.hasLicense || !auth.licenseValid)" class="space-y-5">
          <div v-if="auth.machineId" class="p-3 bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 rounded-xl text-center group cursor-pointer transition-colors hover:bg-slate-100 dark:hover:bg-slate-800" @click="copyMachineId">
            <span class="text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-1">ID de esta máquina</span>
            <div class="flex items-center justify-center gap-2">
              <span class="text-xs font-mono-data font-bold text-slate-700 dark:text-slate-200 select-all">{{ auth.machineId }}</span>
              <BaseBadge v-if="copied" variant="success" size="xs"><i class="fa-solid fa-check mr-1"></i>Copiado</BaseBadge>
              <i v-else class="fa-regular fa-copy text-slate-400 group-hover:text-brand-500 transition-colors"></i>
            </div>
            <span class="text-[9px] text-slate-400 dark:text-slate-500 block mt-1">Enviá este ID a tu proveedor para recibir la clave</span>
          </div>

          <BaseInput
            v-model="auth.licenseKey"
            label="Clave de Licencia"
            placeholder="APX-XXXX-XXXX-XXXX"
            input-class="font-mono uppercase text-center tracking-wider"
            :loading="auth.activatingLicense"
            @enter="auth.activateLicense()"
          />

          <div v-if="auth.licenseError" class="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-300 rounded-xl border border-red-100 dark:border-red-800/50 text-xs font-medium flex items-center gap-2 animate-fade-in">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>{{ auth.licenseError }}</span>
          </div>
          <div v-if="auth.licenseOk" class="p-3 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-300 rounded-xl border border-emerald-100 dark:border-emerald-800/50 text-xs font-medium flex items-center gap-2 animate-fade-in">
            <i class="fa-solid fa-circle-check"></i>
            <span>{{ auth.licenseOk }}</span>
          </div>

          <BaseButton variant="primary" block :loading="auth.activatingLicense" @click="auth.activateLicense()">
            <i class="fa-solid fa-key"></i>
            Activar Licencia
          </BaseButton>
        </div>

        <!-- Login Form -->
        <div v-if="auth.licenseChecked && auth.hasLicense && auth.licenseValid" class="space-y-5">
          <BaseInput
            v-model="auth.loginForm.username"
            label="Usuario"
            placeholder="admin"
            size="lg"
            autocomplete="username"
            @enter="$refs.loginPassword?.focus()"
          >
            <template #prefix>
              <i class="fa-regular fa-user text-slate-400"></i>
            </template>
          </BaseInput>

          <div class="relative">
            <BaseInput
              ref="loginPassword"
              v-model="auth.loginForm.password"
              label="Contraseña"
              :type="showPassword ? 'text' : 'password'"
              placeholder="••••••••"
              size="lg"
              autocomplete="current-password"
              @enter="doLogin()"
            />
            <button
              type="button"
              class="absolute right-3 top-[30px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              tabindex="-1"
              @click="showPassword = !showPassword"
            >
              <i class="fa-solid" :class="showPassword ? 'fa-eye-slash' : 'fa-eye'"></i>
            </button>
          </div>

          <div v-if="auth.loginError" class="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-300 rounded-xl border border-red-100 dark:border-red-800/50 text-xs font-medium flex items-center gap-2 animate-fade-in">
            <i class="fa-solid fa-triangle-exclamation"></i>
            <span>{{ auth.loginError }}</span>
          </div>

          <BaseButton
            variant="primary"
            block
            size="lg"
            :loading="auth.loggingIn"
            @click="doLogin()"
          >
            <span>{{ auth.loggingIn ? 'Conectando...' : 'Conectar' }}</span>
            <i class="fa-solid" :class="auth.loggingIn ? 'fa-circle-notch fa-spin' : 'fa-arrow-right'"></i>
          </BaseButton>

          <p class="text-center text-xs text-slate-400 dark:text-slate-500">
            Presioná <kbd class="px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono-data">Enter</kbd> para ingresar
          </p>
        </div>
      </div>
    </Transition>
  </div>
</template>
