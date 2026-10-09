<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCajaStore } from '@/stores/caja'
import api from '@/services/api'
import SidebarLink from './SidebarLink.vue'
import HelpModal from './HelpModal.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'

const auth = useAuthStore()
const cajaStore = useCajaStore()
const router = useRouter()
const route = useRoute()
const props = defineProps({
  mobileOpen: { type: Boolean, default: false }
})
const emit = defineEmits(['navigate', 'toggle-collapse', 'close-mobile'])

const showHelp = ref(false)
const collapsed = ref(localStorage.getItem('apex-sidebar-collapsed') === 'true')
const isMobile = ref(false)
const showCollapsed = computed(() => collapsed.value && !isMobile.value)
const isDark = ref(document.documentElement.classList.contains('dark'))
const pendientesCount = ref(0)
const defasadosCount = ref(0)

const mainLinks = [
  { to: '/dashboard', icon: 'fa-chart-pie', label: 'Dashboard' },
  { to: '/pos', icon: 'fa-cash-register', label: 'POS de Ventas' },
  { to: '/products', icon: 'fa-boxes-stacked', label: 'Productos' },
  { to: '/etiquetas-precios', icon: 'fa-tag', label: 'Etiquetas' },
  { to: '/caja', icon: 'fa-vault', label: 'Arqueos y Caja', roles: ['admin', 'cajero'] },
  { to: '/ventas', icon: 'fa-receipt', label: 'Ventas' },
  { to: '/calendario', icon: 'fa-calendar', label: 'Calendario' },
  { to: '/compras', icon: 'fa-truck-ramp-box', label: 'Compras / Stock', roles: ['admin', 'encargado', 'repositor'] },
  { to: '/cargar-mercaderia', icon: 'fa-box-open', label: 'Cargar Mercadería', roles: ['admin', 'encargado', 'repositor'] },
  { to: '/precios-online', icon: 'fa-globe', label: 'Precios Online', roles: ['admin', 'encargado', 'repositor'] },
  { to: '/proveedores', icon: 'fa-industry', label: 'Proveedores', roles: ['admin', 'encargado', 'repositor'] },
  { to: '/clientes', icon: 'fa-address-book', label: 'Clientes y Ctas. Ctes', roles: ['admin', 'encargado'] }
]

const adminLinks = [
  { to: '/backups', icon: 'fa-cloud-arrow-up', label: 'Respaldos', roles: ['admin', 'encargado'] },
  { to: '/facturacion', icon: 'fa-file-invoice', label: 'Facturación', roles: ['admin', 'encargado'] },
  { to: '/usuarios', icon: 'fa-users-gear', label: 'Usuarios', roles: ['admin'] },
  { to: '/reportes', icon: 'fa-chart-line', label: 'Reportes', roles: ['admin', 'encargado'] },
  { to: '/licencias', icon: 'fa-key', label: 'Licencias', roles: ['admin'] },
  { to: '/ajustes', icon: 'fa-sliders', label: 'Ajustes', roles: ['admin'] },
  { to: '/auditoria', icon: 'fa-shield-halved', label: 'Auditoría', roles: ['admin'] }
]

function allowed(link) {
  if (!link.roles) return true
  const r = (auth.currentUser?.rol || 'admin').toLowerCase()
  return link.roles.includes(r)
}

function onNavigate() {
  emit('navigate')
  emit('close-mobile')
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem('apex-sidebar-collapsed', String(collapsed.value))
  emit('toggle-collapse', collapsed.value)
}

function toggleTheme() {
  isDark.value = !isDark.value
  if (isDark.value) {
    document.documentElement.classList.add('dark')
    localStorage.setItem('apex-theme', 'dark')
  } else {
    document.documentElement.classList.remove('dark')
    localStorage.setItem('apex-theme', 'light')
  }
}

async function fetchBadgeCounts() {
  try {
    const prods = await api.get('/api/productos?page_size=100000')
    if (prods && Array.isArray(prods)) {
      pendientesCount.value = prods.filter(p =>
        (p.codigo_barras && (p.codigo_barras.startsWith('*MANUAL*') || p.codigo_barras.startsWith('GEN-'))) ||
        (p.fuente === 'manual' && p.stock_actual === 0 && !p.precio_costo)
      ).length
      defasadosCount.value = prods.filter(p =>
        p.precio_venta > 0 && p.precio_costo > 0 && p.precio_venta <= p.precio_costo
      ).length
    }
  } catch { /* silencioso */ }
}

function onKeydown(e) {
  if (e.key === 'Escape' && props.mobileOpen) emit('close-mobile')
}

let mediaQuery = null

function onMediaChange(e) {
  isMobile.value = e.matches
}

onMounted(() => {
  fetchBadgeCounts()
  mediaQuery = window.matchMedia('(max-width: 767px)')
  isMobile.value = mediaQuery.matches
  mediaQuery.addEventListener('change', onMediaChange)
  window.addEventListener('keydown', onKeydown)
})

onUnmounted(() => {
  if (mediaQuery) mediaQuery.removeEventListener('change', onMediaChange)
  window.removeEventListener('keydown', onKeydown)
})

watch(() => route.path, () => fetchBadgeCounts())

function doLogout() {
  auth.logout()
  router.push('/login')
}
</script>

<template>
  <div
    v-if="mobileOpen"
    class="fixed inset-0 bg-slate-950/60 backdrop-blur-[2px] z-40 md:hidden"
    aria-hidden="true"
    @click="emit('close-mobile')"
  ></div>

  <aside
    class="fixed md:relative inset-y-0 left-0 z-50 md:z-20 w-64 shrink-0 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 transition-transform duration-300 ease-out-expo"
    :class="[
      mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      showCollapsed ? 'md:w-20' : 'md:w-64'
    ]"
  >
    <div class="flex-1 flex flex-col min-h-0 overflow-y-auto no-scrollbar">
      <div class="p-4 flex items-center gap-3 border-b border-slate-800 h-16">
        <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-brand-700 flex items-center justify-center text-white shadow-lg shadow-brand-600/20 shrink-0">
          <i class="fa-solid fa-cubes-stacked text-xl"></i>
        </div>
        <div v-if="!showCollapsed" class="overflow-hidden">
          <h1 class="text-white font-bold text-base leading-tight">ApexERP</h1>
          <span class="text-[10px] text-slate-500 font-semibold tracking-widest uppercase">Commerce</span>
        </div>
        <button
          v-if="mobileOpen"
          type="button"
          aria-label="Cerrar menú"
          class="ml-auto md:hidden w-9 h-9 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-slate-800 transition-colors shrink-0"
          @click="emit('close-mobile')"
        >
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>

      <nav class="p-3 space-y-1">
        <template v-for="link in mainLinks" :key="link.to">
          <SidebarLink
            v-if="allowed(link)"
            :to="link.to"
            :icon="link.icon"
            :label="link.label"
            :collapsed="showCollapsed"
            @navigate="onNavigate"
          >
            <template v-if="link.to === '/pos' && !showCollapsed">
              <BaseBadge
                :variant="cajaStore.abierta ? 'success' : 'danger'"
                size="xs"
                :dot="true"
                class="ml-auto"
              >
                {{ cajaStore.abierta ? 'ABIERTA' : 'CERRADA' }}
              </BaseBadge>
            </template>
            <template v-if="link.to === '/products' && !showCollapsed">
              <div class="ml-auto flex items-center gap-1">
                <BaseBadge v-if="defasadosCount > 0" variant="warning" size="xs">{{ defasadosCount }}</BaseBadge>
                <BaseBadge v-if="pendientesCount > 0" variant="danger" size="xs">{{ pendientesCount }}</BaseBadge>
              </div>
            </template>
          </SidebarLink>
        </template>

        <hr class="border-slate-800/70 my-2">

        <template v-for="link in adminLinks" :key="link.to">
          <SidebarLink
            v-if="allowed(link)"
            :to="link.to"
            :icon="link.icon"
            :label="link.label"
            muted
            :collapsed="showCollapsed"
            @navigate="onNavigate"
          />
        </template>

        <hr class="border-slate-800/70 my-2">

        <div v-if="!showCollapsed" class="px-2 py-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
          Vista Móvil
        </div>
        <nav v-if="!showCollapsed" class="px-2 space-y-1">
          <SidebarLink
            to="/cobrar"
            icon="fa-mobile-screen"
            label="Cobro Móvil"
            @navigate="onNavigate"
          />
          <SidebarLink
            to="/cargar-mercaderia"
            icon="fa-box-open"
            label="Cargar Mercadería"
            @navigate="onNavigate"
          />
          <SidebarLink
            to="/control-stock"
            icon="fa-clipboard-list"
            label="Control Stock"
            @navigate="onNavigate"
          />
        </nav>

        <hr class="border-slate-800/70 my-2">

        <button
          type="button"
          class="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
          :class="showCollapsed ? 'justify-center' : ''"
          :title="showCollapsed ? 'Ayuda y Atajos' : undefined"
          @click="showHelp = true"
        >
          <i class="fa-solid fa-circle-question text-lg w-5 text-center"></i>
          <span v-if="!showCollapsed">Ayuda y Atajos</span>
        </button>
      </nav>
    </div>

    <div class="p-3 border-t border-slate-800 space-y-2">
      <button
        type="button"
        class="w-full flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium text-slate-400 hover:bg-slate-800 hover:text-white transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-brand-500/50"
        :class="showCollapsed ? 'justify-center' : ''"
        :title="showCollapsed ? (isDark ? 'Modo claro' : 'Modo oscuro') : undefined"
        @click="toggleTheme"
      >
        <i :class="`fa-solid ${isDark ? 'fa-sun' : 'fa-moon'} text-lg w-5 text-center`"></i>
        <span v-if="!showCollapsed">{{ isDark ? 'Modo claro' : 'Modo oscuro' }}</span>
      </button>

      <div
        class="flex items-center gap-3 p-2 bg-slate-950/40 rounded-xl border border-slate-800"
        :class="showCollapsed ? 'justify-center' : ''"
      >
        <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-slate-700 to-slate-800 flex items-center justify-center font-bold text-xs text-white uppercase shrink-0">
          {{ auth.currentUser?.username?.slice(0, 2) || 'AD' }}
        </div>
        <div v-if="!showCollapsed" class="overflow-hidden flex-1 min-w-0">
          <h4 class="text-xs font-semibold text-white truncate">{{ auth.currentUser?.nombre || 'Administrador' }}</h4>
          <p class="text-[10px] text-slate-500 uppercase tracking-wider truncate font-semibold">{{ auth.currentUser?.rol || 'admin' }}</p>
        </div>
        <button
          v-if="!showCollapsed"
          type="button"
          aria-label="Cerrar Sesión"
          class="w-8 h-8 rounded-lg flex items-center justify-center text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-rose-500/40"
          @click="doLogout"
        >
          <i class="fa-solid fa-power-off text-sm"></i>
        </button>
      </div>
    </div>

    <button
      type="button"
      aria-label="Colapsar sidebar"
      class="absolute -right-3 top-20 w-6 h-6 rounded-full bg-slate-800 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-700 hidden md:flex items-center justify-center shadow-md transition-all duration-200 z-30"
      @click="toggleCollapse"
    >
      <i :class="`fa-solid fa-chevron-${collapsed ? 'right' : 'left'} text-xs`"></i>
    </button>
  </aside>
  <HelpModal :show="showHelp" @close="showHelp = false" />
</template>
