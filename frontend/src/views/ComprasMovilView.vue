<template>
  <div class="h-[100dvh] flex flex-col bg-slate-100 dark:bg-slate-950 overflow-hidden">
    <div class="max-w-md mx-auto w-full h-full flex flex-col">
      <header class="bg-slate-900 text-white px-4 py-3 flex items-center gap-3 relative">
        <div class="relative" ref="menuRef">
          <button class="p-2 rounded-lg hover:bg-slate-700/50" @click="menuOpen=!menuOpen" aria-label="Menú"><i class="fa-solid fa-bars text-base"></i></button>
          <div v-if="menuOpen" class="absolute left-0 top-full mt-1 w-44 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 py-1 z-50 animate-fade-in">
            <button v-for="m in menuItems" :key="m.value" @click="navigateMenu(m)" class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700" :class="m.active && 'font-semibold text-brand-600 dark:text-brand-400'">
              <i :class="['fa-solid', m.icon, 'w-5 text-center']"></i>
              <span>{{ m.label }}</span>
            </button>
          </div>
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-semibold leading-tight truncate">Cargar Mercaderia</div>
          <div class="text-xs text-slate-300 truncate">{{ auth.currentUser.nombre || auth.currentUser.username }}</div>
        </div>
        <button class="p-2 rounded-lg hover:bg-slate-700/50" @click="syncData" :disabled="syncing" aria-label="Sincronizar">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
        </button>
      </header>
      <div class="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        <div class="flex gap-2">
          <div class="relative flex-1">
            <input v-model="scannerInput" type="text" inputmode="numeric" placeholder="Codigo de barras" class="w-full rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-4 py-3 text-base" @keyup.enter="procesarCodigo" />
            <i class="fa-solid fa-barcode absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
          </div>
          <button class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-brand-600 text-white active:bg-brand-700" @click="abrirScanner">
            <i class="fa-solid fa-camera"></i><span class="text-sm font-medium">Escanear</span>
          </button>
        </div>
        <div class="flex items-center gap-2">
          <BaseSelect v-model="proveedorId" :options="proveedores" option-value="id" option-label="nombre" placeholder="Proveedor" class="flex-1"></BaseSelect>
        </div>
        <div v-if="items.length > 0" class="rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-3 flex flex-col gap-3">
          <div class="text-sm font-semibold flex justify-between"><span>Items ({{ items.length }})</span><button class="text-xs text-red-500" @click="vaciar">Vaciar</button></div>
        </div>
        <div v-else class="text-center text-slate-400 text-sm py-8">Escanea o ingresa codigo</div>
      </div>
      <div class="border-t bg-white dark:bg-slate-900 px-4 pt-3 pb-4">
        <BaseButton block variant="primary" @click="guardar">Guardar y recibir</BaseButton>
      </div>
    </div>
  </div>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useProductosStore } from '@/stores/productos'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()
const productosStore = useProductosStore()
const proveedores = ref([])
const categorias = computed(() => productosStore.categorias || [])
const syncing = ref(false)
const guardando = ref(false)
const proveedorId = ref(null)
const scannerInput = ref('')
const items = ref([])
const menuOpen = ref(false)
const menuRef = ref(null)
const tabActivo = ref('cobro') // cobro | control | pc
const menuItems = computed(() => [
  { label: 'Cargar Mercadería', icon: 'fa-box-open', value: 'cobro', active: tabActivo.value === 'cobro', route: null },
  { label: 'Control Móvil', icon: 'fa-boxes-stacked', value: 'control', active: tabActivo.value === 'control', route: null },
  { label: 'Compras (PC)', icon: 'fa-desktop', value: 'pc', active: tabActivo.value === 'pc', route: '/compras' },
])
function volver() { router.back() }
async function syncData() {
  syncing.value = true
  try {
    await Promise.all([
      api.get('/api/proveedores').then(r => { proveedores.value = Array.isArray(r) ? r : (r.data || []) }),
      productosStore.fetchCategorias(),
      productosStore.fetchAll()
    ])
    toast.success('ok')
  } catch (e) {
    toast.warning('err')
  } finally {
    syncing.value = false
  }
}
onMounted(async () => {
  await syncData()
  document.addEventListener('click', handleClickOutside)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) {
    menuOpen.value = false
  }
}
function navigateMenu(m) {
  menuOpen.value = false
  if (m.route) {
    router.push(m.route)
  } else {
    tabActivo.value = m.value
  }
}
function vaciar() { items.value = [] }
const totalCantidad = computed(() => items.value.reduce((s, x) => s + (Number(x.cantidad) || 0), 0))
const totalImporte = computed(() => items.value.reduce((s, x) => s + (Number(x.cantidad) || 0) * (Number(x.precio) || 0), 0))
function guardar() {}
</script>
