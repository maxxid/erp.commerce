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
const hovered = ref(false)
const showCollapsed = computed(() => collapsed.value && !isMobile.value && !hovered.value)
const isDark = ref(document.documentElement.classList.contains('dark'))
const pendientesCount = ref(0)
const defasadosCount = ref(0)

// Registro de metadatos de cada link del menú (icono, etiqueta, roles, muted).
// La configuración persistida solo guarda la referencia (path `to`) y el orden;
// icono/etiqueta/roles se resuelven acá para no duplicar datos.
const LINK_META = {
  '/dashboard': { icon: 'fa-chart-pie', label: 'Dashboard' },
  '/pos': { icon: 'fa-cash-register', label: 'POS de Ventas' },
  '/products': { icon: 'fa-boxes-stacked', label: 'Productos' },
  '/etiquetas-precios': { icon: 'fa-tag', label: 'Etiquetas' },
  '/caja': { icon: 'fa-vault', label: 'Arqueos y Caja', roles: ['admin', 'cajero'] },
  '/ventas': { icon: 'fa-receipt', label: 'Ventas' },
  '/calendario': { icon: 'fa-calendar', label: 'Calendario' },
  '/compras': { icon: 'fa-truck-ramp-box', label: 'Compras / Stock', roles: ['admin', 'encargado', 'repositor'] },
  '/precios-online': { icon: 'fa-globe', label: 'Precios Online', roles: ['admin', 'encargado', 'repositor'] },
  '/proveedores': { icon: 'fa-industry', label: 'Proveedores', roles: ['admin', 'encargado', 'repositor'] },
  '/clientes': { icon: 'fa-address-book', label: 'Clientes y Ctas. Ctes', roles: ['admin', 'encargado'] },
  '/backups': { icon: 'fa-cloud-arrow-up', label: 'Respaldos', roles: ['admin', 'encargado'], muted: true },
  '/facturacion': { icon: 'fa-file-invoice', label: 'Facturación', roles: ['admin', 'encargado'], muted: true },
  '/usuarios': { icon: 'fa-users-gear', label: 'Usuarios', roles: ['admin'], muted: true },
  '/reportes': { icon: 'fa-chart-line', label: 'Reportes', roles: ['admin', 'encargado'], muted: true },
  '/recategorizar': { icon: 'fa-wand-magic-sparkles', label: 'Recategorizar', roles: ['admin', 'encargado'], muted: true },
  '/licencias': { icon: 'fa-key', label: 'Licencias', roles: ['admin'], muted: true },
  '/ajustes': { icon: 'fa-sliders', label: 'Ajustes', roles: ['admin'], muted: true },
  '/auditoria': { icon: 'fa-shield-halved', label: 'Auditoría', roles: ['admin'], muted: true },
  '/cobrar': { icon: 'fa-mobile-screen', label: 'Cobro Móvil' },
  '/cargar-mercaderia': { icon: 'fa-box-open', label: 'Cargar Mercadería' },
  '/control-stock': { icon: 'fa-clipboard-list', label: 'Control Stock' },
  '/sectores': { icon: 'fa-location-dot', label: 'Sectores', roles: ['admin', 'encargado', 'repositor'] },
}

const DEFAULT_BLOCKS = [
  { type: 'link', to: '/dashboard' },
  { type: 'link', to: '/pos' },
  { type: 'link', to: '/products' },
  { type: 'link', to: '/etiquetas-precios' },
  { type: 'link', to: '/caja' },
  { type: 'link', to: '/ventas' },
  { type: 'link', to: '/calendario' },
  { type: 'link', to: '/compras' },
  { type: 'link', to: '/precios-online' },
  { type: 'link', to: '/proveedores' },
  { type: 'link', to: '/clientes' },
  { type: 'separator' },
  { type: 'subtitle', text: 'Gestión' },
  { type: 'link', to: '/backups' },
  { type: 'link', to: '/facturacion' },
  { type: 'link', to: '/usuarios' },
  { type: 'link', to: '/reportes' },
  { type: 'link', to: '/recategorizar' },
  { type: 'link', to: '/licencias' },
  { type: 'link', to: '/ajustes' },
  { type: 'link', to: '/auditoria' },
  { type: 'separator' },
  { type: 'subtitle', text: 'Vista Móvil' },
  { type: 'link', to: '/cobrar' },
  { type: 'link', to: '/cargar-mercaderia' },
  { type: 'link', to: '/control-stock' },
  { type: 'link', to: '/sectores' },
]

const blocks = ref(null) // null => usar DEFAULT_BLOCKS
const loaded = ref(false)

async function loadSidebarConfig() {
  try {
    const res = await api.get('/api/config/sidebar')
    const b = res?.blocks ?? res?.data?.blocks
    blocks.value = Array.isArray(b) && b.length ? b : null
  } catch {
    blocks.value = null
  } finally {
    loaded.value = true
  }
}

const effectiveBlocks = computed(() => blocks.value || DEFAULT_BLOCKS)

function allowed(link) {
  if (!link.roles) return true
  const r = (auth.currentUser?.rol || 'repositor').toLowerCase()
  return link.roles.includes(r)
}

function linkMeta(to) {
  return LINK_META[to] || null
}

function blockVisible(block) {
  if (block.type !== 'link') return true
  const meta = linkMeta(block.to)
  if (!meta) return false
  return allowed(meta)
}

function onNavigate() {
  emit('navigate')
  emit('close-mobile')
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
  localStorage.setItem('apex-sidebar-collapsed', String(collapsed.value))
  emit('toggle-collapse', collapsed.value)
  hovered.value = false
}

function onMouseEnter() {
  if (collapsed.value && !isMobile.value) hovered.value = true
}

function onMouseLeave() {
  hovered.value = false
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
  if (isMobile.value) hovered.value = false
}

onMounted(() => {
  fetchBadgeCounts()
  loadSidebarConfig()
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
    class="fixed md:relative inset-y-0 left-0 z-50 md:z-20 w-64 shrink-0 bg-slate-900 text-slate-300 flex flex-col border-r border-slate-800 transition-all duration-200 ease-out-expo"
    :class="[
      mobileOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0',
      (collapsed && !isMobile) ? (hovered ? 'md:w-64 md:shadow-2xl md:z-30' : 'md:w-20') : 'md:w-64'
    ]"
    @mouseenter="onMouseEnter"
    @mouseleave="onMouseLeave"
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
        <template v-for="(block, idx) in effectiveBlocks" :key="idx">
          <template v-if="block.type === 'separator'">
            <hr class="border-slate-800/70 my-2">
          </template>
          <template v-else-if="block.type === 'subtitle'">
            <div v-if="!showCollapsed" class="px-2 py-1 text-[10px] font-semibold text-slate-500 uppercase tracking-wider">
              {{ block.text }}
            </div>
          </template>
          <template v-else-if="block.type === 'link'">
            <SidebarLink
              v-if="blockVisible(block)"
              :to="block.to"
              :icon="linkMeta(block.to).icon"
              :label="linkMeta(block.to).label"
              :muted="!!linkMeta(block.to).muted"
              :collapsed="showCollapsed"
              @navigate="onNavigate"
            >
              <template v-if="block.to === '/pos' && !showCollapsed">
                <BaseBadge
                  :variant="cajaStore.abierta ? 'success' : 'danger'"
                  size="xs"
                  :dot="true"
                  class="ml-auto"
                >
                  {{ cajaStore.abierta ? 'ABIERTA' : 'CERRADA' }}
                </BaseBadge>
              </template>
              <template v-if="block.to === '/products' && !showCollapsed">
                <div class="ml-auto flex items-center gap-1">
                  <BaseBadge v-if="defasadosCount > 0" variant="warning" size="xs">{{ defasadosCount }}</BaseBadge>
                  <BaseBadge v-if="pendientesCount > 0" variant="danger" size="xs">{{ pendientesCount }}</BaseBadge>
                </div>
              </template>
            </SidebarLink>
          </template>
        </template>

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
          <p class="text-[10px] text-slate-500 uppercase tracking-wider truncate font-semibold">{{ auth.currentUser?.rol || '—' }}</p>
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