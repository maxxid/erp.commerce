<script setup>
import { ref, computed, watch, nextTick, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import api from '@/services/api'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'help'])

const router = useRouter()
const auth = useAuthStore()
const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref(null)

const searchProducts = ref([])
const searchClients = ref([])
const searchLoading = ref(false)
let debounceTimer = null

const commands = [
  { id: 'pos', title: 'Abrir POS de Ventas', subtitle: 'Punto de venta rápido', icon: 'fa-cash-register', shortcut: 'F2', action: () => router.push('/pos') },
  { id: 'new-sale', title: 'Nueva venta', subtitle: 'Iniciar venta en POS', icon: 'fa-cart-plus', action: () => router.push('/pos') },
  { id: 'products', title: 'Productos', subtitle: 'Catálogo y stock', icon: 'fa-boxes-stacked', action: () => router.push('/products') },
  { id: 'new-product', title: 'Nuevo producto', subtitle: 'Agregar al catálogo', icon: 'fa-plus-circle', action: () => router.push('/products') },
  { id: 'caja', title: 'Arqueos y Caja', subtitle: 'Apertura, cierre y movimientos', icon: 'fa-vault', action: () => router.push('/caja') },
  { id: 'open-caja', title: 'Abrir caja', subtitle: 'Iniciar jornada', icon: 'fa-lock-open', action: () => router.push('/caja') },
  { id: 'close-caja', title: 'Cerrar caja', subtitle: 'Finalizar jornada', icon: 'fa-lock', action: () => router.push('/caja') },
  { id: 'ventas', title: 'Ventas', subtitle: 'Historial de ventas', icon: 'fa-receipt', action: () => router.push('/ventas') },
  { id: 'dashboard', title: 'Dashboard', subtitle: 'Resumen general', icon: 'fa-chart-pie', action: () => router.push('/dashboard') },
  { id: 'clientes', title: 'Clientes', subtitle: 'Cuentas corrientes', icon: 'fa-address-book', action: () => router.push('/clientes') },
  { id: 'new-client', title: 'Nuevo cliente', subtitle: 'Registrar cliente', icon: 'fa-user-plus', action: () => router.push('/clientes') },
  { id: 'compras', title: 'Compras / Stock', subtitle: 'Órdenes y recepciones', icon: 'fa-truck-ramp-box', action: () => router.push('/compras') },
  { id: 'proveedores', title: 'Proveedores', subtitle: 'Gestión de proveedores', icon: 'fa-truck', action: () => router.push('/proveedores') },
  { id: 'calendario', title: 'Calendario', subtitle: 'Resumen diario', icon: 'fa-calendar-day', action: () => router.push('/calendario') },
  { id: 'reportes', title: 'Reportes', subtitle: 'Análisis de ventas', icon: 'fa-chart-line', action: () => router.push('/reportes') },
  { id: 'usuarios', title: 'Usuarios', subtitle: 'Gestión de usuarios', icon: 'fa-users-gear', action: () => router.push('/usuarios') },
  { id: 'licencias', title: 'Licencias', subtitle: 'Gestión de licencias', icon: 'fa-key', action: () => router.push('/licencias') },
  { id: 'generate-license', title: 'Generar licencia', subtitle: 'Nueva clave de licencia', icon: 'fa-wand-magic-sparkles', action: () => router.push('/licencias') },
  { id: 'auditoria', title: 'Auditoría', subtitle: 'Registro de actividad', icon: 'fa-shield-halved', action: () => router.push('/auditoria') },
  { id: 'backups', title: 'Respaldos', subtitle: 'Backups locales y R2', icon: 'fa-cloud-arrow-up', action: () => router.push('/backups') },
  { id: 'create-backup', title: 'Crear backup', subtitle: 'Respaldo manual', icon: 'fa-floppy-disk', action: () => router.push('/backups') },
  { id: 'theme', title: 'Cambiar tema', subtitle: 'Alternar modo claro/oscuro', icon: 'fa-moon', action: toggleTheme },
  { id: 'help', title: 'Ayuda y atajos', subtitle: 'Ver guía de teclado', icon: 'fa-circle-question', action: () => emit('help') },
  { id: 'logout', title: 'Cerrar sesión', subtitle: 'Salir del sistema', icon: 'fa-power-off', action: () => { auth.logout(); router.push('/login') } }
]

const filteredCommands = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return commands
  return commands.filter(c =>
    c.title.toLowerCase().includes(q) ||
    c.subtitle.toLowerCase().includes(q) ||
    c.id.includes(q)
  )
})

const hasSearch = computed(() => query.value.trim().length >= 3)

const allItems = computed(() => {
  const items = []
  if (hasSearch.value) {
    if (searchProducts.value.length) {
      items.push({ type: 'header', label: 'Productos' })
      for (const p of searchProducts.value) {
        items.push({ type: 'product', id: `prod-${p.id}`, title: p.nombre, subtitle: `Stock: ${p.stock_actual} | ${p.codigo_barras || '—'}`, icon: 'fa-box', action: () => router.push('/products') })
      }
    }
    if (searchClients.value.length) {
      items.push({ type: 'header', label: 'Clientes' })
      for (const c of searchClients.value) {
        items.push({ type: 'client', id: `cli-${c.id}`, title: c.name || c.nombre, subtitle: `${c.docType || ''} ${c.docNumber || ''}`.trim(), icon: 'fa-user', action: () => router.push('/clientes') })
      }
    }
  }
  if (filteredCommands.value.length) {
    if (items.length) items.push({ type: 'header', label: 'Comandos' })
    for (const c of filteredCommands.value) {
      items.push({ type: 'command', ...c })
    }
  }
  return items
})

const navigableItems = computed(() => allItems.value.filter(i => i.type !== 'header'))

watch(query, (val) => {
  clearTimeout(debounceTimer)
  if (val.trim().length < 3) {
    searchProducts.value = []
    searchClients.value = []
    searchLoading.value = false
    return
  }
  searchLoading.value = true
  debounceTimer = setTimeout(async () => {
    try {
      const [prods, clis] = await Promise.allSettled([
        api.get(`/api/productos?search=${encodeURIComponent(val.trim())}`),
        api.get(`/api/clientes?search=${encodeURIComponent(val.trim())}`)
      ])
      searchProducts.value = prods.status === 'fulfilled' && Array.isArray(prods.value) ? prods.value.slice(0, 5) : []
      searchClients.value = clis.status === 'fulfilled' && Array.isArray(clis.value) ? clis.value.slice(0, 5) : []
    } catch {}
    searchLoading.value = false
  }, 300)
})

watch(() => props.modelValue, async (val) => {
  if (val) {
    query.value = ''
    searchProducts.value = []
    searchClients.value = []
    selectedIndex.value = 0
    await nextTick()
    inputRef.value?.focus()
  }
})

watch(navigableItems, () => { selectedIndex.value = 0 })

onUnmounted(() => { clearTimeout(debounceTimer) })

function close() {
  emit('update:modelValue', false)
}

function run(item) {
  if (!item || !item.action) return
  close()
  setTimeout(() => item.action(), 200)
}

function onKeydown(e) {
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value + 1) % navigableItems.value.length
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value - 1 + navigableItems.value.length) % navigableItems.value.length
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    const item = navigableItems.value[selectedIndex.value]
    if (item) run(item)
  }
}

function isSelected(item) {
  const navIdx = navigableItems.value.indexOf(item)
  return navIdx === selectedIndex.value
}

function toggleTheme() {
  const html = document.documentElement
  const isDark = html.classList.contains('dark')
  if (isDark) {
    html.classList.remove('dark')
    localStorage.setItem('apex-theme', 'light')
  } else {
    html.classList.add('dark')
    localStorage.setItem('apex-theme', 'dark')
  }
}
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out-expo"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-[110] bg-slate-950/50 dark:bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[12vh] px-4"
        @click.self="close"
      >
        <Transition
          enter-active-class="transition duration-250 ease-out-expo"
          enter-from-class="opacity-0 scale-[0.96] -translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition duration-200 ease-in"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-[0.96] -translate-y-4"
        >
          <div
            v-if="modelValue"
            class="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden"
          >
            <div class="flex items-center gap-3 px-4 border-b border-slate-100 dark:border-slate-800">
              <i class="fa-solid fa-magnifying-glass text-slate-400"></i>
              <input
                ref="inputRef"
                v-model="query"
                type="text"
                placeholder="Buscar acción, producto, cliente o comando..."
                class="flex-1 py-4 bg-transparent text-slate-900 dark:text-white placeholder:text-slate-400 outline-none text-base"
                @keydown="onKeydown"
              >
              <div v-if="searchLoading" class="flex items-center gap-1.5 text-xs text-slate-400">
                <i class="fa-solid fa-circle-notch animate-spin"></i>
              </div>
              <kbd class="hidden sm:inline-flex items-center px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">ESC</kbd>
            </div>
            <div class="max-h-[55vh] overflow-y-auto py-2">
              <template v-for="(item, idx) in allItems" :key="item.id || item.label">
                <div v-if="item.type === 'header'" class="px-5 pt-3 pb-1.5">
                  <span class="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500 font-semibold">{{ item.label }}</span>
                </div>
                <div
                  v-else
                  class="mx-2 flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-colors outline-none"
                  :class="isSelected(item)
                    ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
                    : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'"
                  @click="run(item)"
                  @mouseenter="selectedIndex = navigableItems.indexOf(item)"
                >
                  <div class="w-8 h-8 rounded-lg flex items-center justify-center bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
                    <i :class="`fa-solid ${item.icon}`"></i>
                  </div>
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ item.title }}</p>
                    <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ item.subtitle }}</p>
                  </div>
                  <kbd v-if="item.shortcut" class="px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">{{ item.shortcut }}</kbd>
                </div>
              </template>
              <div v-if="!allItems.length" class="py-8 text-center text-sm text-slate-500">
                No se encontraron resultados para "{{ query }}"
              </div>
            </div>
            <div class="px-4 py-2 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-800 flex items-center gap-4 text-xs text-slate-500">
              <span class="flex items-center gap-1"><kbd class="px-1 rounded bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600">↑</kbd><kbd class="px-1 rounded bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600">↓</kbd> navegar</span>
              <span class="flex items-center gap-1"><kbd class="px-1 rounded bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600">↵</kbd> seleccionar</span>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>
