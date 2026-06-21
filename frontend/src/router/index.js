import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

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
  { path: '/movil', name: 'movil', component: () => import('@/views/MovilView.vue') },
]

const router = createRouter({
  history: createWebHistory('/app/'),
  routes
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()

  if (!auth.authenticated && !to.meta.guest) {
    return next('/login')
  }
  if (auth.authenticated && to.meta.guest) {
    return next('/dashboard')
  }
  if (to.meta.roles && auth.currentUser) {
    const userRole = auth.currentUser.rol
    if (!to.meta.roles.includes(userRole)) {
      return next('/dashboard')
    }
  }
  next()
})

export default router
