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
          <div class="text-xs text-slate-300 truncate">{{ auth.currentUser?.nombre || auth.currentUser?.username }}</div>
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
          <button class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-brand-600 text-white active:bg-brand-700" @click="openScanner">
            <i class="fa-solid fa-camera"></i><span class="text-sm font-medium">Escanear</span>
          </button>
        </div>
        <div class="flex items-center gap-2">
          <BaseSelect v-model="proveedorId" :options="proveedores" option-value="id" option-label="nombre" placeholder="Proveedor" class="flex-1"></BaseSelect>
        </div>
        <div v-if="items.length > 0" class="rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-3 flex flex-col gap-3">
          <div class="text-sm font-semibold flex justify-between items-center">
            <span>Items ({{ items.length }})</span>
            <button class="text-xs text-red-500" @click="vaciar">Vaciar</button>
          </div>
          <div v-for="(item, idx) in items" :key="item.producto_id" class="flex items-center gap-2 border-b border-slate-200 dark:border-slate-700 last:border-0 pb-2 last:pb-0">
            <button class="text-red-500 p-1" @click="quitarItem(idx)" aria-label="Quitar"><i class="fa-solid fa-xmark"></i></button>
            <div class="flex-1 min-w-0">
              <div class="text-sm truncate">{{ item.nombre }}</div>
              <div class="text-xs text-slate-500">{{ fc(item.precio) }} c/u</div>
            </div>
            <div class="flex items-center gap-1">
              <button class="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-700" @click="cambiarCantidad(idx, -1)">−</button>
              <span class="w-7 text-center text-sm font-semibold">{{ item.cantidad }}</span>
              <button class="w-8 h-8 rounded-lg bg-slate-200 dark:bg-slate-700" @click="cambiarCantidad(idx, 1)">+</button>
            </div>
            <input
              v-model="item.precio"
              type="text"
              inputmode="decimal"
              title="Precio de compra"
              class="w-16 text-center text-sm rounded-md bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600"
            />
          </div>
          <div class="flex justify-between text-xs text-slate-500 border-t border-slate-200 dark:border-slate-700 pt-2">
            <span>{{ totalCantidad }} und.</span>
            <span class="font-semibold text-slate-700 dark:text-slate-200">Total {{ fc(totalImporte) }}</span>
          </div>
        </div>
        <div v-else class="text-center text-slate-400 text-sm py-8">Escaneá o ingresá un código</div>
      </div>
<div class="border-t bg-white dark:bg-slate-900 px-4 pt-3 pb-4">
        <BaseButton block variant="primary" :loading="guardando" @click="guardar">Guardar y recibir</BaseButton>
      </div>
    </div>
  </div>

  <!-- Modal escáner -->
  <BaseModal v-model="scannerOpen" title="Escanear código" :persistent="true">
    <div class="flex flex-col gap-3">
      <div v-if="!scannerError" class="relative rounded-xl overflow-hidden bg-black aspect-video mx-auto max-w-sm w-full">
        <video ref="videoEl" class="w-full h-full object-cover" muted playsinline></video>
      </div>
      <div v-else class="text-amber-600 text-sm">{{ scannerError }}</div>
      <div class="flex gap-2">
        <BaseButton variant="secondary" block @click="closeCamera">Cancelar</BaseButton>
      </div>
    </div>
  </BaseModal>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useProductosStore } from '@/stores/productos'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import { useBarcodeScanner } from '@/composables/useBarcodeScanner'
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()
const productosStore = useProductosStore()
const proveedores = ref([])
const syncing = ref(false)
const guardando = ref(false)
const proveedorId = ref(null)
const scannerInput = ref('')
const items = ref([])
const menuOpen = ref(false)
const menuRef = ref(null)
const tabActivo = ref('cargar')
const menuItems = computed(() => [
  { label: 'Cobro Móvil', icon: 'fa-cash-register', value: 'cobro', active: tabActivo.value === 'cobro', route: '/cobrar' },
  { label: 'Cargar Mercadería', icon: 'fa-box-open', value: 'cargar', active: tabActivo.value === 'cargar', route: '/cargar-mercaderia' },
  { label: 'Control Stock', icon: 'fa-clipboard-list', value: 'control', active: tabActivo.value === 'control', route: '/control-stock' },
  { label: 'Compras (PC)', icon: 'fa-desktop', value: 'pc', active: tabActivo.value === 'pc', route: '/compras' },
])

const {
  scannerOpen,
  scannerError,
  videoEl,
  openScanner,
  closeCamera,
} = useBarcodeScanner({
  continuous: true,
  cooldownMs: 1500,
  onDetect: async (raw) => {
    scannerInput.value = raw
    await procesarCodigo()
    toast.success(`Escaneado: ${raw}`)
  },
})
async function syncData() {
  syncing.value = true
  try {
    await Promise.all([
      api.get('/api/proveedores').then(r => { proveedores.value = Array.isArray(r) ? r : [] }),
      productosStore.fetchAll(),
    ])
    toast.success('Datos actualizados')
  } catch (e) {
    toast.error('No se pudieron actualizar los datos')
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
async function procesarCodigo() {
  const raw = scannerInput.value.trim()
  if (!raw) return
  try {
    const local = productosStore.productos.find(p => p.codigo_barras === raw)
    if (local) {
      agregarItem(local)
      scannerInput.value = ''
      return
    }
    const resp = await api.post('/api/productos/lookup', { barcode: raw }).catch(() => null)
    if (resp && resp.id) {
      const newP = {
        id: resp.id,
        codigo_barras: resp.codigo_barras,
        nombre: resp.nombre,
        marca: resp.marca || '',
        precio_venta: resp.precio_venta || 0,
        stock_actual: resp.stock_actual || 0,
      }
      agregarItem(newP)
      productosStore.productos.push(newP)
      scannerInput.value = ''
      return
    }
    if (resp && resp.nombre) {
      toast.info(`Producto: ${resp.nombre} - ${fc(resp.precio_referencia || resp.precio_venta || 0)}`)
      return
    }
    toast.warning('Producto no encontrado en fuentes externas')
  } catch {
    toast.error('Error buscando producto')
  }
}
function agregarItem(product) {
  const existing = items.value.find(i => i.producto_id === product.id)
  if (existing) {
    existing.cantidad += 1
  } else {
    items.value.push({
      producto_id: product.id,
      nombre: product.nombre,
      codigo_barras: product.codigo_barras,
      precio: product.precio_costo || product.precio_venta || 0,
      precio_venta: product.precio_venta || 0,
      categoria_id: product.categoria_id || null,
      cantidad: 1,
    })
  }
}
function quitarItem(idx) { items.value.splice(idx, 1) }
function cambiarCantidad(idx, delta) {
  const it = items.value[idx]
  const nueva = (Number(it.cantidad) || 0) + delta
  if (nueva <= 0) {
    quitarItem(idx)
    return
  }
  it.cantidad = nueva
}
function vaciar() { items.value = [] }
const totalCantidad = computed(() => items.value.reduce((s, x) => s + (Number(x.cantidad) || 0), 0))
const totalImporte = computed(() => items.value.reduce((s, x) => s + (Number(x.cantidad) || 0) * (Number(x.precio) || 0), 0))
async function guardar() {
  if (!proveedorId.value) {
    toast.warning('Seleccioná un proveedor')
    return
  }
  if (!items.value.length) {
    toast.warning('Escaneá al menos un producto')
    return
  }
  guardando.value = true
  try {
    const payload = {
      proveedor_id: proveedorId.value,
      recibir_directo: true,
      items: items.value.map(i => ({
        producto: i.nombre,
        codigo_barras: i.codigo_barras || '',
        cantidad: Number(i.cantidad) || 1,
        precio: Number(i.precio) || 0,
        precio_venta: i.precio_venta || null,
        categoria_id: i.categoria_id || null,
      })),
    }
    const resp = await api.post('/api/compras', payload)
    toast.success(resp?.message || 'Mercadería cargada y recibida')
    items.value = []
    scannerInput.value = ''
    await productosStore.refreshProductos()
  } catch (e) {
    toast.error(e.data?.detail || e.message || 'No se pudo guardar la compra')
  } finally {
    guardando.value = false
  }
}
</script>
