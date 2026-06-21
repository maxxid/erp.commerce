import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/', redirect: '/dashboard' },
  { path: '/login', name: 'login', component: () => import('@/views/LoginView.vue'), meta: { guest: true } },
  { path: '/dashboard', name: 'dashboard', component: () => import('@/views/DashboardView.vue') },
  { path: '/pos', name: 'pos', component: () => import('@/views/POSView.vue') },
  { path: '/products', name: 'products', component: () => import('@/views/ProductsView.vue') },
  { path: '/caja', name: 'caja', component: () => import('@/views/CajaView.vue') },
  { path: '/ventas', name: 'ventas', component: () => import('@/views/VentasView.vue') },
  { path: '/calendario', name: 'calendario', component: () => import('@/views/CalendarioView.vue') },
  { path: '/compras', name: 'compras', component: () => import('@/views/ComprasView.vue') },
  { path: '/proveedores', name: 'proveedores', component: () => import('@/views/ProveedoresView.vue') },
  { path: '/clientes', name: 'clientes', component: () => import('@/views/ClientesView.vue') },
  { path: '/reportes', name: 'reportes', component: () => import('@/views/ReportesView.vue') },
  { path: '/usuarios', name: 'usuarios', component: () => import('@/views/UsuariosView.vue') },
  { path: '/licencias', name: 'licencias', component: () => import('@/views/LicenciasView.vue') },
  { path: '/auditoria', name: 'auditoria', component: () => import('@/views/AuditoriaView.vue') },
  { path: '/backups', name: 'backups', component: () => import('@/views/BackupsView.vue') },
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
  next()
})

export default router
