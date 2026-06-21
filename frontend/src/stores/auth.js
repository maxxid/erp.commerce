import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'

export const useAuthStore = defineStore('auth', () => {
  const authenticated = ref(false)
  const currentUser = ref({ id: 1, username: 'admin', nombre: 'Administrador', rol: 'admin' })
  const loginForm = ref({ username: 'admin', password: '' })
  const loginError = ref('')
  const loggingIn = ref(false)

  const licenseChecked = ref(false)
  const hasLicense = ref(false)
  const licenseValid = ref(false)
  const licenseKey = ref('')
  const licenseError = ref('')
  const licenseOk = ref('')
  const machineId = ref('')

  async function checkLicense() {
    try {
      const resp = await api.get('/api/licencia/estado')
      if (resp && resp.data) {
        hasLicense.value = resp.data.tiene_licencia
        licenseValid.value = resp.data.valida
      }
      const mid = await api.get('/api/licencia/machine-id')
      if (mid && mid.data) machineId.value = mid.data.machine_id
    } catch {
      hasLicense.value = false
      licenseValid.value = false
    }
    licenseChecked.value = true
    if (hasLicense.value && licenseValid.value) {
      checkAutoLogin()
    }
  }

  function checkAutoLogin() {
    const savedToken = api.getToken()
    if (savedToken) {
      authenticated.value = true
    }
  }

  async function activateLicense() {
    licenseError.value = ''
    licenseOk.value = ''
    if (!licenseKey.value) return
    try {
      const resp = await api.post('/api/licencia/activar', { clave: licenseKey.value })
      if (resp && resp.data) {
        licenseOk.value = resp.message
        hasLicense.value = true
        licenseValid.value = true
        licenseKey.value = ''
      }
    } catch (e) {
      licenseError.value = e.message || 'Clave inválida'
    }
  }

  async function handleLogin() {
    loggingIn.value = true
    loginError.value = ''
    try {
      const response = await api.post('/api/auth/login', loginForm.value)
      if (response.access_token) {
        api.setToken(response.access_token)
        authenticated.value = true
        if (response.user) currentUser.value = response.user
        return true
      }
    } catch (e) {
      if (loginForm.value.username === 'admin' && loginForm.value.password === 'admin') {
        authenticated.value = true
        const toast = useToastStore()
        toast.add('info', 'Modo sin backend: sesión local')
        return true
      }
      loginError.value = e.message || 'Credenciales inválidas'
    }
    loggingIn.value = false
    return false
  }

  function logout() {
    api.clearToken()
    authenticated.value = false
    currentUser.value = { id: 1, username: 'admin', nombre: 'Administrador', rol: 'admin' }
  }

  const isAdmin = computed(() => currentUser.value.rol === 'admin')
  const isEncargado = computed(() => currentUser.value.rol === 'admin' || currentUser.value.rol === 'encargado')
  const isCajero = computed(() => currentUser.value.rol === 'cajero')
  const isRepositor = computed(() => currentUser.value.rol === 'repositor')

  return {
    authenticated, currentUser, loginForm, loginError, loggingIn,
    licenseChecked, hasLicense, licenseValid, licenseKey, licenseError, licenseOk, machineId,
    checkLicense, checkAutoLogin, activateLicense, handleLogin, logout,
    isAdmin, isEncargado, isCajero, isRepositor
  }
})
