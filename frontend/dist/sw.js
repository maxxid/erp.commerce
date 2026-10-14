// El placeholder lo stampa scripts/postbuild.cjs en dist/ con el commit:
// así cada deploy cambia los bytes del SW y el browser lo instala solo
// (limpia los caches viejos en activate y deja de servir un index.html
// obsoleto que pedía chunks hasheados que ya no existen).
const CACHE_VERSION = 'apex-erp-633589d'
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

  // Shell (navegación e index.html): network-first. Un deploy nuevo tiene
  // que llegar apenas se publique; si no, el index.html cacheado seguía
  // referenciando chunks hasheados borrados del server y la app se trababa.
  if (event.request.mode === 'navigate' || url.pathname === '/app/' || url.pathname === '/app/index.html') {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          if (response && response.status === 200) {
            const clone = response.clone()
            caches.open(STATIC_CACHE).then((cache) => cache.put('/app/index.html', clone))
          }
          return response
        })
        .catch(() => caches.match('/app/index.html'))
    )
    return
  }

  // Assets hasheados (inmutables): cache-first con revalidación en background.
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
      })
    })
  )
})

self.addEventListener('message', (event) => {
  if (event.data === 'SKIP_WAITING') self.skipWaiting()
})