const API_BASE = ''

// Sin timeout un fetch quedaba colgado para siempre (p. ej. al despertar
// de sleep con la red caída) y la vista se quedaba en loading eterno.
const REQUEST_TIMEOUT_MS = 30000

let sessionExpiredDispatched = false

function notifySessionExpired() {
  if (sessionExpiredDispatched) return
  sessionExpiredDispatched = true
  window.dispatchEvent(new CustomEvent('apex:session-expired'))
}

function getToken() {
  return localStorage.getItem('apex_token')
}

function setToken(token) {
  sessionExpiredDispatched = false
  localStorage.setItem('apex_token', token)
}

function clearToken() {
  localStorage.removeItem('apex_token')
}

function touchSync() {
  try { localStorage.setItem('apex-last-sync', String(Date.now())) } catch {}
}

// Error de red (sin conexión o el servidor no contesta). Va con status 0 para
// que todo el mundo sepa que **no** es un rechazo del servidor: sin esto la
// app no podía diferenciar "se cortó el internet" de "venció la sesión" y
// terminaba echando al usuario de su propia cuenta.
function errorDeRed(mensaje) {
  const error = new Error(mensaje)
  error.status = 0
  error.red = true
  error.data = { detail: mensaje }
  return error
}

export function esErrorDeRed(error) {
  return Boolean(error?.red) || error?.status === 0
}

// FastAPI devuelve los errores de validación (422) como una lista de objetos
// con `loc` y `msg`. `new Error(detail)` los convertía en "[object Object]" y
// ni el cajero ni quien mira la consola sabían qué campo estaba mal.
function detalleDeError(data, status) {
  const detalle = data?.detail
  if (typeof detalle === 'string') return detalle
  if (Array.isArray(detalle)) {
    const partes = detalle
      .map((d) => {
        const campo = Array.isArray(d?.loc)
          ? d.loc.filter((p) => p !== 'body').join('.')
          : ''
        return campo ? `${campo}: ${d?.msg}` : d?.msg
      })
      .filter(Boolean)
    if (partes.length) return partes.join(' · ')
  }
  return data?.error || `Error ${status}`
}

function buildQuery(params) {
  if (!params) return ''
  const search = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    search.append(key, value)
  }
  const qs = search.toString()
  return qs ? `?${qs}` : ''
}

async function request(method, path, body = null, params = null, fetchOptions = {}) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const options = { method, headers, ...fetchOptions }
  if (body && method !== 'GET') {
    options.body = JSON.stringify(body)
  }
  if (!options.signal && typeof AbortSignal !== 'undefined' && AbortSignal.timeout) {
    options.signal = AbortSignal.timeout(REQUEST_TIMEOUT_MS)
  }

  let response
  try {
    response = await fetch(`${API_BASE}${path}${buildQuery(params)}`, options)
  } catch (e) {
    if (e?.name === 'TimeoutError' || e?.name === 'AbortError') {
      throw errorDeRed('El servidor no responde (timeout)')
    }
    // `fetch` tira un TypeError cuando no hay red o el servidor no contesta.
    throw errorDeRed('Sin conexión con el servidor')
  }

  if (response.status === 401 && !path.startsWith('/api/auth/')) {
    notifySessionExpired()
  }

  if (fetchOptions.responseType === 'blob') {
    const blob = await response.blob()
    if (!response.ok) {
      let text = ''
      try { text = await blob.text() } catch {}
      const error = new Error(text || `Error ${response.status}`)
      error.status = response.status
      error.data = { detail: text }
      throw error
    }
    touchSync()
    return blob
  }

  const text = await response.text()
  let data
  try { data = JSON.parse(text) } catch { data = { detail: text } }

  if (!response.ok) {
    const error = new Error(detalleDeError(data, response.status))
    error.status = response.status
    error.data = data
    throw error
  }

  touchSync()

  if (data && typeof data === 'object' && data.ok !== false && 'data' in data) {
    return data.data
  }
  return data
}

export default {
  request,
  getToken,
  setToken,
  clearToken,
  get(path, params) { return request('GET', path, null, params) },
  post(path, body) { return request('POST', path, body) },
  put(path, body) { return request('PUT', path, body) },
  patch(path, body) { return request('PATCH', path, body) },
  delete(path) { return request('DELETE', path) }
}

export { API_BASE, getToken, setToken, clearToken }
