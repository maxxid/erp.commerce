const API_BASE = ''

function getToken() {
  return localStorage.getItem('apex_token')
}

function setToken(token) {
  localStorage.setItem('apex_token', token)
}

function clearToken() {
  localStorage.removeItem('apex_token')
}

function touchSync() {
  try { localStorage.setItem('apex-last-sync', String(Date.now())) } catch {}
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

  const response = await fetch(`${API_BASE}${path}${buildQuery(params)}`, options)

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
    const error = new Error(data.detail || data.error || `Error ${response.status}`)
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
