<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({ modelValue: { type: Boolean, default: false } })
const emit = defineEmits(['update:modelValue', 'help'])

const router = useRouter()
const auth = useAuthStore()
const query = ref('')
const selectedIndex = ref(0)
const inputRef = ref(null)

const commands = [
  { id: 'pos', title: 'Abrir POS de Ventas', subtitle: 'Punto de venta rápido', icon: 'fa-cash-register', shortcut: 'F2', action: () => router.push('/pos') },
  { id: 'products', title: 'Productos', subtitle: 'Catálogo y stock', icon: 'fa-boxes-stacked', action: () => router.push('/products') },
  { id: 'caja', title: 'Arqueos y Caja', subtitle: 'Apertura, cierre y movimientos', icon: 'fa-vault', action: () => router.push('/caja') },
  { id: 'ventas', title: 'Ventas', subtitle: 'Historial de ventas', icon: 'fa-receipt', action: () => router.push('/ventas') },
  { id: 'dashboard', title: 'Dashboard', subtitle: 'Resumen general', icon: 'fa-chart-pie', action: () => router.push('/dashboard') },
  { id: 'clientes', title: 'Clientes', subtitle: 'Cuentas corrientes', icon: 'fa-address-book', action: () => router.push('/clientes') },
  { id: 'compras', title: 'Compras / Stock', subtitle: 'Órdenes y recepciones', icon: 'fa-truck-ramp-box', action: () => router.push('/compras') },
  { id: 'reportes', title: 'Reportes', subtitle: 'Análisis de ventas', icon: 'fa-chart-line', action: () => router.push('/reportes') },
  { id: 'usuarios', title: 'Usuarios', subtitle: 'Gestión de usuarios', icon: 'fa-users-gear', action: () => router.push('/usuarios') },
  { id: 'backups', title: 'Respaldos', subtitle: 'Backups locales y R2', icon: 'fa-cloud-arrow-up', action: () => router.push('/backups') },
  { id: 'theme', title: 'Cambiar tema', subtitle: 'Alternar modo claro/oscuro', icon: 'fa-moon', action: toggleTheme },
  { id: 'help', title: 'Ayuda y atajos', subtitle: 'Ver guía de teclado', icon: 'fa-circle-question', action: () => emit('help') },
  { id: 'logout', title: 'Cerrar sesión', subtitle: 'Salir del sistema', icon: 'fa-power-off', action: () => { auth.logout(); router.push('/login') } }
]

const filtered = computed(() => {
  const q = query.value.trim().toLowerCase()
  if (!q) return commands
  return commands.filter(c =>
    c.title.toLowerCase().includes(q) ||
    c.subtitle.toLowerCase().includes(q) ||
    c.id.includes(q)
  )
})

watch(() => props.modelValue, async (val) => {
  if (val) {
    query.value = ''
    selectedIndex.value = 0
    await nextTick()
    inputRef.value?.focus()
  }
})

watch(filtered, () => { selectedIndex.value = 0 })

function close() {
  emit('update:modelValue', false)
}

function run(cmd) {
  close()
  setTimeout(() => cmd.action(), 200)
}

function onKeydown(e) {
  if (e.key === 'Escape') close()
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value + 1) % filtered.value.length
  }
  if (e.key === 'ArrowUp') {
    e.preventDefault()
    selectedIndex.value = (selectedIndex.value - 1 + filtered.value.length) % filtered.value.length
  }
  if (e.key === 'Enter') {
    e.preventDefault()
    const cmd = filtered.value[selectedIndex.value]
    if (cmd) run(cmd)
  }
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
        class="fixed inset-0 z-[110] bg-slate-950/50 dark:bg-black/60 backdrop-blur-sm flex items-start justify-center pt-[15vh] px-4"
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
                placeholder="Buscar acción, vista o comando..."
                class="flex-1 py-4 bg-transparent text-slate-900 dark:text-white placeholder:text-slate-400 outline-none text-base"
                @keydown="onKeydown"
              >
              <kbd class="hidden sm:inline-flex items-center px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">ESC</kbd>
            </div>
            <div class="max-h-[50vh] overflow-y-auto py-2">
              <div
                v-for="(cmd, idx) in filtered"
                :key="cmd.id"
                class="mx-2 flex items-center gap-3 px-3 py-2.5 rounded-xl cursor-pointer transition-colors outline-none"
                :class="selectedIndex === idx
                  ? 'bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300'
                  : 'text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800'"
                @click="run(cmd)"
                @mouseenter="selectedIndex = idx"
              >
                <div class="w-8 h-8 rounded-lg flex items-center justify-center bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400">
                  <i :class="`fa-solid ${cmd.icon}`"></i>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium truncate">{{ cmd.title }}</p>
                  <p class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ cmd.subtitle }}</p>
                </div>
                <kbd v-if="cmd.shortcut" class="px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-800 text-xs font-medium text-slate-500 dark:text-slate-400">{{ cmd.shortcut }}</kbd>
              </div>
              <div v-if="!filtered.length" class="py-8 text-center text-sm text-slate-500">
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
