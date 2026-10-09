const CACHE_VERSION = 'apex-erp-v5'
const STATIC_CACHE = `${CACHE_VERSION}-static`
const DATA_CACHE = `${CACHE_VERSION}-data`

const STATIC_ASSETS = [
  '/app/',
  '/app/index.html',
  '/app/manifest.json',
  '/app/icons/icon-180.png',
  '/app/icons/icon-192.png',
  '/app/icons/icon-512.png'
]

const CACHEABLE_API_PATTERNS = [
  /\/api\/productos/,
  /\/api\/clientes/,
  /\/api\/categorias/,
  /\/api\/catalogo\/estado/,
  /\/api\/caja\/estado/,
  /\/api\/proveedores/,
  /\/api\/lotes/,
  /\/api\/config\/ajustes/,
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => cache.addAll(STATIC_ASSETS))
  )
  self.skipWaiting()
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((k) => k.startsWith('apex-erp-') && k !== STATIC_CACHE && k !== DATA_CACHE)
          .map((k) => caches.delete(k))
      )
    )
  )
  self.clients.claim()
})

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url)

  if (url.pathname.startsWith('/api/')) {
    if (event.request.method !== 'GET') return

    const isCacheable = CACHEABLE_API_PATTERNS.some((pattern) => pattern.test(url.pathname))

    if (isCacheable) {
      event.respondWith(
        caches.open(DATA_CACHE).then((cache) =>
          fetch(event.request)
            .then((response) => {
              if (response && response.status === 200) {
                const clone = response.clone()
                cache.put(event.request, clone)
              }
              return response
            })
            .catch(() => cache.match(event.request))
        )
      )
      return
    }
    return
  }

  if (event.request.method !== 'GET') return

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) {
        fetch(event.request)
          .then((response) => {
            if (response && response.status === 200) {
              const clone = response.clone()
              caches.open(STATIC_CACHE).then((cache) => cache.put(event.request, clone))
            }
          })
          .catch(() => {})
        return cached
      }

      return fetch(event.request).then((response) => {
        if (response && response.status === 200) {
          const clone = response.clone()
          caches.open(STATIC_CACHE).then((cache) => cache.put(event.request, clone))
        }
        return response
      }).catch(() => {
        if (event.request.mode === 'navigate') {
          return caches.match('/app/index.html')
        }
      })
    })
  )
})

self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting()
})