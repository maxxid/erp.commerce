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

async function request(method, path, body = null) {
  const headers = { 'Content-Type': 'application/json' }
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`

  const options = { method, headers }
  if (body && method !== 'GET') {
    options.body = JSON.stringify(body)
  }

  const response = await fetch(`${API_BASE}${path}`, options)
  const text = await response.text()
  let data
  try { data = JSON.parse(text) } catch { data = { detail: text } }

  if (!response.ok) {
    const error = new Error(data.detail || `Error ${response.status}`)
    error.status = response.status
    error.data = data
    throw error
  }

  return data
}

export default {
  request,
  getToken,
  setToken,
  clearToken,
  get(path) { return request('GET', path) },
  post(path, body) { return request('POST', path, body) },
  put(path, body) { return request('PUT', path, body) },
  delete(path) { return request('DELETE', path) }
}

export { API_BASE, getToken, setToken, clearToken }
