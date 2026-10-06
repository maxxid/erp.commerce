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
          <div class="font-semibold leading-tight truncate">Control Stock</div>
          <div class="text-xs text-slate-300 truncate">{{ auth.currentUser?.nombre || auth.currentUser?.username }}</div>
        </div>
        <button class="p-2 rounded-lg hover:bg-slate-700/50" @click="syncData" :disabled="syncing" aria-label="Sincronizar">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
        </button>
      </header>
      <div class="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        <div class="flex gap-2">
          <div class="relative flex-1">
            <input v-model="scannerInput" type="text" inputmode="numeric" placeholder="Código de barras..." class="w-full rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-4 py-3 text-base" @keyup.enter="procesarCodigo" />
            <i class="fa-solid fa-barcode absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
          </div>
          <button class="flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-brand-600 text-white active:bg-brand-700" @click="abrirScanner">
            <i class="fa-solid fa-camera"></i><span class="text-sm font-medium">Escanear</span>
          </button>
        </div>
        <div class="flex gap-2 items-center">
          <i class="fa-solid fa-magnifying-glass text-slate-400"></i>
          <input v-model="searchText" type="text" placeholder="Buscar producto..." class="flex-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2 text-sm" />
        </div>
        <div v-if="loading" class="flex justify-center py-8">
          <i class="fa-solid fa-circle-notch animate-spin text-2xl text-brand-600"></i>
        </div>
        <div v-else-if="filteredProducts.length === 0" class="text-center text-slate-400 text-sm py-8">
          {{ searchText || scannerInput ? 'Sin coincidencias' : 'Escanea o busca un producto' }}
        </div>
        <div v-else class="flex-1 overflow-y-auto">
          <div v-for="p in filteredProducts" :key="p.id" class="rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3 mb-3 flex flex-col gap-2">
            <div class="flex items-start justify-between gap-2">
              <div class="flex-1 min-w-0">
                <div class="font-medium truncate">{{ p.nombre }}</div>
                <div class="text-xs text-slate-500 truncate">{{ p.marca || 'Sin marca' }} · {{ p.codigo_barras }}</div>
              </div>
              <div class="text-right shrink-0">
                <div class="text-lg font-bold text-brand-600">{{ fc(p.precio_venta || 0) }}</div>
                <div class="text-xs text-slate-500">Precio venta</div>
              </div>
            </div>
            <div class="grid grid-cols-3 gap-2 text-center">
              <div class="rounded-lg bg-slate-50 dark:bg-slate-900/50 p-2">
                <div class="text-2xl font-bold text-slate-900 dark:text-white">{{ p.stock_actual || 0 }}</div>
                <div class="text-[10px] text-slate-500 uppercase tracking-wider">Stock actual</div>
              </div>
              <div class="rounded-lg bg-slate-50 dark:bg-slate-900/50 p-2">
                <div class="text-2xl font-bold" :class="stockEsperadoClass(p)">{{ p.stock_esperado || 0 }}</div>
                <div class="text-[10px] text-slate-500 uppercase tracking-wider">Esperado</div>
              </div>
              <div class="rounded-lg bg-slate-50 dark:bg-slate-900/50 p-2">
                <div class="text-xl font-bold" :class="vencimientoClass(p)">{{ formatVencimiento(p.proximo_vencimiento) }}</div>
                <div class="text-[10px] text-slate-500 uppercase tracking-wider">Próx. venc.</div>
              </div>
            </div>
            <div v-if="p.lotes && p.lotes.length" class="border-t border-slate-200 dark:border-slate-700 pt-2 space-y-1">
              <div class="text-xs font-semibold text-slate-500">Lotes:</div>
              <div v-for="lote in p.lotes.slice(0, 3)" :key="lote.id" class="text-xs text-slate-600 dark:text-slate-400 flex justify-between gap-2 px-1">
                <span>{{ lote.codigo_lote || 'SIN LOTE' }}</span>
                <span class="font-mono">{{ lote.cantidad_actual || 0 }}</span>
                <span :class="vencimientoClass({ proximo_vencimiento: lote.fecha_vencimiento })">{{ lote.fecha_vencimiento ? formatDate(lote.fecha_vencimiento) : 'Sin venc.' }}</span>
              </div>
              <div v-if="p.lotes.length > 3" class="text-xs text-slate-400 text-center">+ {{ p.lotes.length - 3 }} lote(s) más</div>
            </div>
          </div>
        </div>
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
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useProductosStore } from '@/stores/productos'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()
const productosStore = useProductosStore()
const loading = ref(true)
const syncing = ref(false)
const scannerInput = ref('')
const searchText = ref('')
const menuOpen = ref(false)
const menuRef = ref(null)
const tabActivo = ref('control')
// Escáner de cámara
const scannerOpen = ref(false)
const scannerError = ref('')
const videoEl = ref(null)
const barcodeDetector = ref(null)
const scanTimer = ref(null)
const cameraStream = ref(null)
const lastScannedCode = ref('')
const scanCooldown = ref(false)
const menuItems = computed(() => [
  { label: 'Cobro Móvil', icon: 'fa-cash-register', value: 'cobro', active: tabActivo.value === 'cobro', route: '/cobrar' },
  { label: 'Cargar Mercadería', icon: 'fa-box-open', value: 'cargar', active: tabActivo.value === 'cargar', route: '/cargar-mercaderia' },
  { label: 'Control Stock', icon: 'fa-clipboard-list', value: 'control', active: tabActivo.value === 'control', route: null },
  { label: 'POS (PC)', icon: 'fa-desktop', value: 'pc', active: tabActivo.value === 'pc', route: '/pos' },
])
async function syncData() {
  syncing.value = true
  loading.value = true
  try {
    await Promise.all([
      productosStore.fetchAll(),
      api.get('/api/lotes?page_size=10000').then(r => { lotesMap.value = buildLotesMap(Array.isArray(r) ? r : (r.data || [])) }),
      api.post('/api/catalogo/descargar').then(() => {
        localStorage.setItem('catalogo_last_sync', String(Date.now()))
      }).catch(() => {})
    ])
    toast.success('ok')
  } catch (e) {
    toast.warning('err')
  } finally {
    syncing.value = false
    loading.value = false
  }
}
const lotesMap = ref({})
function buildLotesMap(lotes) {
  const map = {}
  for (const l of lotes) {
    if (!l.activo) continue
    if (!map[l.producto_id]) map[l.producto_id] = []
    map[l.producto_id].push(l)
  }
  for (const pid in map) {
    map[pid].sort((a, b) => (a.fecha_vencimiento || '9999-12-31').localeCompare(b.fecha_vencimiento || '9999-12-31'))
  }
  return map
}
const products = computed(() => productosStore.productos || [])
const filteredProducts = computed(() => {
  let list = products.value
  const s = searchText.value.trim().toLowerCase()
  const code = scannerInput.value.trim()
  if (code) {
    list = list.filter(p => p.codigo_barras === code)
  } else if (s) {
    list = list.filter(p =>
      (p.nombre || '').toLowerCase().includes(s) ||
      (p.marca || '').toLowerCase().includes(s) ||
      (p.codigo_barras || '').toLowerCase().includes(s)
    )
  }
  return list.map(p => {
    const lotes = lotesMap.value[p.id] || []
    const vencidos = lotes.filter(l => l.fecha_vencimiento && new Date(l.fecha_vencimiento) < new Date())
    const proximo = lotes.find(l => l.fecha_vencimiento && new Date(l.fecha_vencimiento) >= new Date())
    const stockEsperado = lotes.reduce((sum, l) => sum + (Number(l.cantidad_actual) || 0), 0)
    return {
      ...p,
      lotes: lotes.slice(0, 5),
      proximo_vencimiento: proximo?.fecha_vencimiento || null,
      stock_esperado: stockEsperado || p.stock_actual || 0,
      tiene_vencidos: vencidos.length > 0
    }
  })
})
function vencimientoClass(p) {
  if (!p.proximo_vencimiento) return 'text-slate-400'
  const diff = Math.ceil((new Date(p.proximo_vencimiento) - new Date()) / (1000 * 60 * 60 * 24))
  if (diff < 0) return 'text-red-500'
  if (diff <= 7) return 'text-red-600'
  if (diff <= 30) return 'text-amber-600'
  return 'text-green-600'
}
function stockEsperadoClass(p) {
  const actual = Number(p.stock_actual) || 0
  const esperado = Number(p.stock_esperado) || 0
  if (esperado > actual) return 'text-green-600'
  if (esperado < actual) return 'text-red-500'
  return 'text-slate-900 dark:text-white'
}
function formatVencimiento(fecha) {
  if (!fecha) return '—'
  const d = new Date(fecha)
  const hoy = new Date()
  const diff = Math.ceil((d - hoy) / (1000 * 60 * 60 * 24))
  if (diff < 0) return `Vencido (${formatDate(fecha)})`
  if (diff === 0) return `Hoy (${formatDate(fecha)})`
  if (diff === 1) return `Mañana (${formatDate(fecha)})`
  return `${diff}d (${formatDate(fecha)})`
}
function formatDate(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}
onMounted(async () => {
  await syncData()
  document.addEventListener('click', handleClickOutside)
})
onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  closeCamera()
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
  searchText.value = ''
  await syncData()
}
const supportsBarcodeDetector = () => typeof window !== 'undefined' && 'BarcodeDetector' in window
async function abrirScanner() {
  if (!supportsBarcodeDetector()) {
    toast.warning('Tu navegador no soporta escaneo por cámara. Usá el campo manual.')
    return
  }
  scannerError.value = ''
  scannerOpen.value = true
  await nextTick()
  try {
    barcodeDetector.value = new BarcodeDetector({
      formats: ['ean_13', 'ean_8', 'code_128', 'code_39', 'upc_a', 'upc_e', 'codabar']
    })
    cameraStream.value = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
    if (videoEl.value) {
      videoEl.value.srcObject = cameraStream.value
      await videoEl.value.play().catch(() => {})
    }
    scanTimer.value = setInterval(() => detectFromCamera(), 350)
  } catch {
    scannerError.value = 'No se pudo acceder a la cámara. Permití el acceso e intentá de nuevo.'
    closeCamera()
  }
}

async function detectFromCamera() {
  if (!barcodeDetector.value || !videoEl.value || !cameraStream.value) return
  if (scanCooldown.value) return
  try {
    const codes = await barcodeDetector.value.detect(videoEl.value)
    if (codes && codes.length && codes[0].rawValue) {
      const raw = codes[0].rawValue.trim()
      if (raw === lastScannedCode.value) return
      lastScannedCode.value = raw
      scannerInput.value = raw
      scanCooldown.value = true
      await procesarCodigo()
      toast.success(`Escaneado: ${raw}`)
      setTimeout(() => {
        scanCooldown.value = false
        lastScannedCode.value = ''
        scannerInput.value = ''
      }, 1500)
    }
  } catch {
    // ignorar frames sin detección
  }
}

function closeCamera() {
  if (scanTimer.value) {
    clearInterval(scanTimer.value)
    scanTimer.value = null
  }
  if (cameraStream.value) {
    cameraStream.value.getTracks().forEach(t => t.stop())
    cameraStream.value = null
  }
  barcodeDetector.value = null
  scannerOpen.value = false
}
</script>