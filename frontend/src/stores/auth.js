import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { esErrorDeRed } from '@/services/api'

// Lo último que supimos del servidor. No es una caché de datos: es la única
// forma de que un corte de luz o un bache de internet no le cierre la puerta
// al dueño que ya estaba trabajando.
const CLAVE_LICENCIA = 'apex-licencia-cache'
const CLAVE_SESION = 'apex-sesion-offline'

function leerCache(clave) {
  try { return JSON.parse(localStorage.getItem(clave)) || null } catch { return null }
}

function escribirCache(clave, valor) {
  try { localStorage.setItem(clave, JSON.stringify(valor)) } catch {}
}

export const useAuthStore = defineStore('auth', () => {
  const initializing = ref(true)
  const authenticated = ref(false)
  const currentUser = ref(null)
  const loginForm = ref({ username: '', password: '' })
  const loginError = ref('')
  const loggingIn = ref(false)

  // True cuando la app está andando con lo último que se sabe del servidor
  // (token y licencia de la última conexión) porque no hay red.
  const offline = ref(false)

  const licenseChecked = ref(false)
  const hasLicense = ref(false)
  const licenseValid = ref(false)
  const licenseKey = ref('')
  const licenseError = ref('')
  const licenseOk = ref('')
  const machineId = ref('')

  function usarLicenciaCache(cache) {
    hasLicense.value = Boolean(cache.hasLicense)
    licenseValid.value = Boolean(cache.licenseValid)
    machineId.value = cache.machineId || ''
    offline.value = true
  }

  async function checkLicense() {
    const cache = leerCache(CLAVE_LICENCIA)
    // Sin tarjeta de red el fetch tarda hasta el timeout en fallar: no tiene
    // sentido esperar 30 segundos para llegar al mismo resultado.
    if (!navigator.onLine && cache) {
      usarLicenciaCache(cache)
    } else {
      try {
        const resp = await api.get('/api/licencia/estado')
        if (resp) {
          hasLicense.value = resp.tiene_licencia || false
          licenseValid.value = resp.valida || false
        }
        const mid = await api.get('/api/licencia/machine-id')
        if (mid) machineId.value = mid.machine_id || ''
        escribirCache(CLAVE_LICENCIA, {
          hasLicense: hasLicense.value,
          licenseValid: licenseValid.value,
          machineId: machineId.value,
        })
      } catch (e) {
        if (esErrorDeRed(e) && cache) {
          // Sin red no hay manera de preguntarle al servidor. La última
          // licencia que vimos seguía siendo buena, así que seguimos: cortarle
          // el acceso a todo el local porque se cortó el internet no arregla
          // nada y no deja a nadie para levantarlo.
          usarLicenciaCache(cache)
        } else {
          hasLicense.value = false
          licenseValid.value = false
        }
      }
    }
    licenseChecked.value = true
    if (hasLicense.value && licenseValid.value) {
      await checkAutoLogin()
    }
    initializing.value = false
  }

  async function checkAutoLogin() {
    const savedToken = api.getToken()
    if (!savedToken) return
    const cache = leerCache(CLAVE_SESION)
    if (!navigator.onLine && cache) {
      currentUser.value = cache
      authenticated.value = true
      offline.value = true
      return
    }
    try {
      const userData = await api.get('/api/auth/me')
      if (userData) {
        authenticated.value = true
        currentUser.value = {
          id: userData.id,
          username: userData.username,
          nombre: userData.nombre,
          rol: userData.rol,
        }
        escribirCache(CLAVE_SESION, currentUser.value)
      }
    } catch (e) {
      if (esErrorDeRed(e) && cache) {
        // No se pudo confirmar el token contra el servidor, pero es el mismo
        // que ya se venía usando en este equipo: se entra con la última
        // sesión abierta y se sigue trabajando con lo cacheado.
        currentUser.value = cache
        authenticated.value = true
        offline.value = true
        return
      }
      api.clearToken()
      authenticated.value = false
      currentUser.value = null
    }
  }

  // Volvió la internet: se vuelve a preguntar licencia y token al servidor.
  async function revalidar() {
    offline.value = false
    await checkLicense()
  }

  async function activateLicense() {
    licenseError.value = ''
    licenseOk.value = ''
    if (!licenseKey.value) return
    try {
      const resp = await api.post('/api/licencia/activar', { clave: licenseKey.value })
      if (resp) {
        licenseOk.value = resp.message || 'Licencia activada'
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
      const loginData = await api.post('/api/auth/login', loginForm.value)
      if (loginData && loginData.access_token) {
        api.setToken(loginData.access_token)
        authenticated.value = true
        currentUser.value = {
          id: 1,
          username: loginData.username || loginForm.value.username,
          nombre: loginData.nombre || loginForm.value.username,
          rol: loginData.rol || 'cajero'
        }
        loggingIn.value = false
        return true
      }
      loginError.value = 'Respuesta inválida del servidor'
    } catch (e) {
      loginError.value = esErrorDeRed(e)
        ? 'Sin conexión con el servidor: no se pudo iniciar sesión.'
        : (e.message || 'Credenciales inválidas')
    }
    loggingIn.value = false
    return false
  }

  function logout() {
    api.clearToken()
    // Cerrar sesión es una decisión: no se puede volver a entrar a la fuerza
    // sin red, así que se borra también lo cacheado.
    try { localStorage.removeItem(CLAVE_SESION) } catch {}
    authenticated.value = false
    currentUser.value = null
  }

  const isAdmin = computed(() => currentUser.value?.rol === 'admin')
  const isEncargado = computed(() => currentUser.value?.rol === 'admin' || currentUser.value?.rol === 'encargado')
  const isCajero = computed(() => currentUser.value?.rol === 'cajero')
  const isRepositor = computed(() => currentUser.value?.rol === 'repositor')

  return {
    authenticated, currentUser, loginForm, loginError, loggingIn, offline,
    licenseChecked, hasLicense, licenseValid, licenseKey, licenseError, licenseOk, machineId,
    checkLicense, checkAutoLogin, activateLicense, handleLogin, logout, revalidar,
    isAdmin, isEncargado, isCajero, isRepositor
  }
})
