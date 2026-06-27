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
  { path: '/products', name: 'products', component: () => import('@/views/ProductsView.vue') },
  { path: '/caja', name: 'caja', component: () => import('@/views/CajaView.vue'), meta: { roles: ['admin', 'cajero'] } },
  { path: '/ventas', name: 'ventas', component: () => import('@/views/VentasView.vue') },
  { path: '/calendario', name: 'calendario', component: () => import('@/views/CalendarioView.vue') },
  { path: '/compras', name: 'compras', component: () => import('@/views/ComprasView.vue'), meta: { roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/proveedores', name: 'proveedores', component: () => import('@/views/ProveedoresView.vue'), meta: { roles: ['admin', 'encargado', 'repositor'] } },
  { path: '/clientes', name: 'clientes', component: () => import('@/views/ClientesView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/reportes', name: 'reportes', component: () => import('@/views/ReportesView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/usuarios', name: 'usuarios', component: () => import('@/views/UsuariosView.vue'), meta: { roles: ['admin'] } },
  { path: '/licencias', name: 'licencias', component: () => import('@/views/LicenciasView.vue'), meta: { roles: ['admin'] } },
  { path: '/auditoria', name: 'auditoria', component: () => import('@/views/AuditoriaView.vue'), meta: { roles: ['admin'] } },
  { path: '/backups', name: 'backups', component: () => import('@/views/BackupsView.vue'), meta: { roles: ['admin', 'encargado'] } },
  { path: '/ajustes', name: 'ajustes', component: () => import('@/views/AjustesView.vue'), meta: { roles: ['admin'] } },
]

const router = createRouter({
  history: createWebHistory('/app/'),
  routes
})

router.beforeEach((to, from) => {
  const auth = useAuthStore()

  if (!auth.authenticated && !to.meta.guest) {
    return '/login'
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

router.afterEach(() => {
  clearTimeout(loadTimer)
  loadTimer = setTimeout(() => { pageLoading.value = false }, 300)
})

export default router
