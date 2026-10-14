import { createRouter, createWebHistory } from 'vue-router'
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'

export const pageLoading = ref(false)
let loadTimer = null

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guest: true } },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/pos', name: 'pos', component: () => import('@/views/POSView.vue') },
  { path: '/cobrar', name: 'cobrar', component: () => import('@/views/CobroMovilView.vue'), meta: { bare: true, mobile: true } },
  { path: '/products', name: 'products', component: () => import('@/views/ProductsView.vue') },
  { path: '/etiquetas-precios', name: 'etiquetas-precios', component: () => import('@/views/EtiquetasPreciosView.vue') },
  { path: '/recategorizar', name: 'recategorizar', component: () => import('@/views/RecategorizarView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/caja', name: 'caja', component: () => import('@/views/CajaView.vue'), meta: { roles: ['admin', 'cajero'] } },
  { path: '/ventas', name: 'ventas', component: () => import('@/views/VentasView.vue') },
  { path: '/calendario', name: 'calendario', component: () => import('@/views/CalendarioView.vue') },
  { path: '/compras', name: 'compras', component: () => import('@/views/ComprasView.vue'), meta: { roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/cargar-mercaderia', name: 'cargar-mercaderia', component: () => import('@/views/ComprasMovilView.vue'), meta: { bare: true, mobile: true, roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/control-stock', name: 'control-stock', component: () => import('@/views/ControlStockMovilView.vue'), meta: { bare: true, mobile: true, roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/sectores', name: 'sectores', component: () => import('@/views/SectoresMovilView.vue'), meta: { bare: true, mobile: true, roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/precios-online', name: 'precios-online', component: () => import('@/views/PreciosOnlineView.vue'), meta: { roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/proveedores', name: 'proveedores', component: () => import('@/views/ProveedoresView.vue'), meta: { roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/clientes', name: 'clientes', component: () => import('@/views/ClientesView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/reportes', name: 'reportes', component: () => import('@/views/ReportesView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/usuarios', name: 'usuarios', component: () => import('@/views/UsuariosView.vue'), meta: { roles: ['admin'] } },
  { path: '/licencias', name: 'licencias', component: () => import('@/views/LicenciasView.vue'), meta: { roles: ['admin'] } },
  { path: '/auditoria', name: 'auditoria', component: () => import('@/views/AuditoriaView.vue'), meta: { roles: ['admin'] } },
  { path: '/backups', name: 'backups', component: () => import('@/views/BackupsView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/facturacion', name: 'facturacion', component: () => import('@/views/FacturacionView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/ajustes', name: 'ajustes', component: () => import('@/views/AjustesView.vue'), meta: { roles: ['admin'] } },
]

const router = createRouter({
  history: createWebHistory('/app/'),
  routes
})

router.beforeEach((to, from) => {
  const auth = useAuthStore()

  if (!auth.authenticated && !to.meta.guest) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }
  if (auth.authenticated && to.meta.guest) {
    return '/dashboard'
  }
  if (to.meta.roles && auth.currentUser) {
    const userRole = auth.currentUser.rol
    if (!to.meta.roles.includes(userRole)) {
      return '/dashboard'
    }
  }

  if (from.name && to.name !== from.name) {
    pageLoading.value = true
  }
  return
})

router.afterEach((to, from, failure) => {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(() => { pageLoading.value = false }, 300)
  // Navegación exitosa: si veníamos de un reload post-deploy, liberar el
  // flag para que la próxima actualización también pueda recuperarse.
  if (!failure) sessionStorage.removeItem('apex-reload-post-deploy')
})

// Si un chunk lazy ya no existe (deploy nuevo con el index.html viejo
// cacheado), recargamos una sola vez para levantar el shell actualizado.
router.onError((error, to) => {
  const msg = String(error?.message || error || '')
  const esChunkPerdido = /Failed to fetch dynamically imported module|error loading dynamically imported module|Importing a module script failed|Unable to preload CSS/i.test(msg)
  if (!esChunkPerdido) return
  const flag = 'apex-reload-post-deploy'
  if (sessionStorage.getItem(flag)) return
  sessionStorage.setItem(flag, '1')
  window.location.assign(`/app${to?.fullPath || '/'}`)
})

export default router

