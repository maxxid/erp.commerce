<template>
  <div class="h-[100dvh] flex flex-col bg-slate-100 dark:bg-slate-950 overflow-hidden">
    <div class="max-w-md mx-auto w-full h-full flex flex-col">
      <header class="bg-slate-900 text-white px-4 py-3 flex items-center gap-3 relative shrink-0">
        <div class="relative" ref="menuRef">
          <button class="p-2 rounded-lg hover:bg-slate-700/50" @click="menuOpen = !menuOpen" aria-label="Menú">
            <i class="fa-solid fa-bars text-base"></i>
          </button>
          <div v-if="menuOpen" class="absolute left-0 top-full mt-1 w-48 bg-white dark:bg-slate-800 rounded-xl shadow-lg border border-slate-200 dark:border-slate-700 py-1 z-50 animate-fade-in">
            <button
              v-for="m in menuItems"
              :key="m.value"
              class="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-700"
              :class="m.active && 'font-semibold text-brand-600 dark:text-brand-400'"
              @click="navigateMenu(m)"
            >
              <i :class="['fa-solid', m.icon, 'w-5 text-center']"></i>
              <span>{{ m.label }}</span>
            </button>
          </div>
        </div>
        <div class="flex-1 min-w-0">
          <div class="font-semibold leading-tight truncate">Sectores</div>
          <div class="text-xs text-slate-300 truncate">{{ auth.currentUser?.nombre || auth.currentUser?.username }}</div>
        </div>
        <button class="p-2 rounded-lg hover:bg-slate-700/50" @click="cargarTodo" :disabled="cargando" aria-label="Sincronizar">
          <i :class="cargando ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
        </button>
      </header>

      <div class="flex-1 overflow-y-auto px-4 py-3 flex flex-col gap-3">
        <!-- Sin sector activo: elegir dónde estás parado -->
        <template v-if="!sectorActivo">
          <div v-if="cargando" class="flex justify-center py-10">
            <i class="fa-solid fa-circle-notch animate-spin text-2xl text-brand-600"></i>
          </div>
          <template v-else>
            <div class="rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3 flex items-center gap-3">
              <div class="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center shrink-0">
                <i class="fa-solid fa-location-dot text-amber-600 dark:text-amber-400"></i>
              </div>
              <div class="min-w-0">
                <div class="text-xs text-slate-500 dark:text-slate-400">Tocá el sector donde estás parado y escaneá los productos</div>
                <div v-if="sinSectorCount > 0" class="text-xs font-semibold text-amber-600 dark:text-amber-400 mt-0.5">
                  {{ sinSectorCount }} producto(s) todavía sin sector
                </div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-2">
              <button
                v-for="s in sectores"
                :key="s.id"
                class="rounded-xl border p-3 text-left transition-all active:scale-[0.98] bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-brand-400 dark:hover:border-brand-600"
                @click="elegirSector(s)"
              >
                <div class="text-sm font-semibold text-slate-800 dark:text-white leading-tight truncate">{{ s.nombre }}</div>
                <div class="text-[11px] text-slate-400 mt-1">
                  {{ conteoDe(s) }} producto(s)
                  <span v-if="sesionPorSector[s.id]" class="text-brand-600 dark:text-brand-400 font-semibold"> (+{{ sesionPorSector[s.id] }} hoy)</span>
                </div>
              </button>
            </div>

            <div v-if="!sectores.length" class="text-center text-slate-400 text-sm py-8">
              No hay sectores cargados. Crealos desde Productos en la PC.
            </div>
          </template>
        </template>

        <!-- Con sector activo: escanear y ver lo que se fue asignando -->
        <template v-else>
          <div class="rounded-xl bg-brand-600 text-white p-3 flex items-center gap-3">
            <div class="w-10 h-10 rounded-lg bg-white/15 flex items-center justify-center shrink-0">
              <i class="fa-solid fa-location-dot"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-[10px] uppercase tracking-wider text-brand-100 font-semibold">Ubicando en</div>
              <div class="font-bold leading-tight truncate">{{ sectorActivo.nombre }}</div>
            </div>
            <button class="px-3 py-1.5 rounded-lg bg-white/15 text-xs font-semibold" @click="salirDelSector">
              Cambiar
            </button>
          </div>

          <button
            class="w-full rounded-xl bg-slate-900 dark:bg-slate-800 text-white py-4 flex items-center justify-center gap-2 active:scale-[0.99] transition-transform"
            @click="openScanner"
          >
            <i class="fa-solid fa-camera text-lg"></i>
            <span class="font-semibold">Escanear con la cámara</span>
          </button>

          <div class="flex gap-2">
            <div class="relative flex-1">
              <input
                v-model="codigoManual"
                type="text"
                inputmode="numeric"
                placeholder="O tipeá el código…"
                class="w-full rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-4 py-3 text-base pr-10"
                @keyup.enter="procesarCodigo(codigoManual); codigoManual = ''"
              />
              <i class="fa-solid fa-barcode absolute right-3 top-1/2 -translate-y-1/2 text-slate-400"></i>
            </div>
            <button
              v-if="escaneados.length"
              class="px-3 rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-xs font-semibold"
              @click="deshacerUltimo"
            >
              <i class="fa-solid fa-rotate-left mr-1"></i>Deshacer
            </button>
          </div>

          <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400 px-1">
            <span>
              <b class="text-slate-800 dark:text-white text-sm">{{ escaneados.length }}</b> asignado(s) en esta vuelta
              <span v-if="movidosCount"> · <b class="text-amber-600 dark:text-amber-400">{{ movidosCount }}</b> movidos de otro sector</span>
            </span>
            <button v-if="escaneados.length" class="text-[11px] text-slate-400 hover:text-slate-600" @click="limpiarVuelta">
              Limpiar
            </button>
          </div>

          <div v-if="!escaneados.length && !noEncontrados.length" class="text-center text-slate-400 text-sm py-8">
            Escaneá el primer producto de este sector.
            <div class="text-[11px] mt-1">Cada código que leas queda asignado acá al toque.</div>
          </div>

          <div v-for="(e, i) in escaneados" :key="`${e.id}-${i}`" class="rounded-xl bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 p-3 flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/30 flex items-center justify-center shrink-0">
              <i class="fa-solid fa-check text-emerald-600 dark:text-emerald-400 text-sm"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-slate-800 dark:text-white truncate">{{ e.nombre }}</div>
              <div class="text-[11px] text-slate-400 truncate">
                {{ e.marca || e.codigo_barras }}
                <span v-if="e.sector_anterior_id" class="text-amber-600 dark:text-amber-400"> · venía de {{ e.sector_anterior }}</span>
              </div>
            </div>
          </div>

          <div v-for="(n, i) in noEncontrados" :key="`nf-${i}`" class="rounded-xl bg-white dark:bg-slate-800 border border-rose-200 dark:border-rose-900/50 p-3 flex items-center gap-3">
            <div class="w-8 h-8 rounded-lg bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center shrink-0">
              <i class="fa-solid fa-question text-rose-600 dark:text-rose-400 text-sm"></i>
            </div>
            <div class="flex-1 min-w-0">
              <div class="text-sm font-medium text-slate-800 dark:text-white">Código no encontrado</div>
              <div class="text-[11px] text-slate-400 font-mono">{{ n }}</div>
            </div>
            <button
              v-if="puedeCrear"
              class="px-3 py-1.5 rounded-lg bg-brand-600 text-white text-xs font-semibold shrink-0"
              @click="abrirAlta(n)"
            >
              Crear
            </button>
          </div>
        </template>
      </div>
    </div>
  </div>

  <!-- Cámara a pantalla completa: se usa mucho, así que no va en un modal chico -->
  <div v-if="scannerOpen" class="fixed inset-0 z-[60] bg-black flex flex-col">
    <div class="flex items-center justify-between px-4 py-3 text-white shrink-0">
      <div class="min-w-0">
        <div class="text-[10px] uppercase tracking-wider text-slate-400">Ubicando en</div>
        <div class="font-semibold truncate">{{ sectorActivo?.nombre }}</div>
      </div>
      <button class="px-3 py-2 rounded-lg bg-white/10 text-sm font-semibold" @click="closeCamera">
        <i class="fa-solid fa-xmark mr-1"></i>Cerrar
      </button>
    </div>
    <div class="flex-1 relative overflow-hidden">
      <video ref="videoEl" class="absolute inset-0 w-full h-full object-cover" muted playsinline></video>
      <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
        <div class="w-[85%] max-w-sm aspect-[3/4] rounded-2xl border-2 border-white/60 shadow-[0_0_0_9999px_rgba(0,0,0,0.35)] flex items-end justify-center pb-3">
          <span class="text-white/80 text-xs bg-black/40 px-2 py-1 rounded-full">Apuntá al código de barras</span>
        </div>
      </div>
      <div v-if="scannerError" class="absolute inset-x-4 bottom-4 rounded-xl bg-rose-600 text-white text-sm p-3">
        {{ scannerError }}
      </div>
      <div v-if="ultimoFlash" class="absolute top-4 inset-x-4 rounded-xl bg-emerald-500 text-white text-sm p-2.5 text-center font-semibold animate-fade-in">
        <i class="fa-solid fa-check mr-1"></i>{{ ultimoFlash }}
      </div>
      <div v-if="ultimoErrorFlash" class="absolute top-4 inset-x-4 rounded-xl bg-rose-500 text-white text-sm p-2.5 text-center font-semibold animate-fade-in">
        <i class="fa-solid fa-triangle-exclamation mr-1"></i>{{ ultimoErrorFlash }}
      </div>
      <div v-if="ultimoNoEncontrado && puedeCrear" class="absolute bottom-16 inset-x-4 animate-fade-in">
        <button
          class="w-full rounded-xl bg-white text-slate-900 py-3 font-semibold text-sm shadow-lg"
          @click="abrirAlta(ultimoNoEncontrado)"
        >
          <i class="fa-solid fa-plus mr-1"></i>Crear producto con el código {{ ultimoNoEncontrado }}
        </button>
      </div>
    </div>
  </div>

  <!-- Alta rápida: producto que apareció en el estante y todavía no existe en el sistema -->
  <BaseModal v-model="altaAbierta" title="Crear producto" size="md">
    <div class="flex flex-col gap-3">
      <div class="text-xs text-slate-500 dark:text-slate-400">
        Se va a crear y asignar a <b class="text-brand-600 dark:text-brand-400">{{ sectorActivo?.nombre }}</b>
      </div>
      <div>
        <label class="text-xs font-semibold text-slate-600 dark:text-slate-300">Código de barras</label>
        <input
          v-model="altaForm.codigo_barras"
          type="text"
          inputmode="numeric"
          class="mt-1 w-full rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2.5 text-sm"
        />
      </div>
      <div>
        <label class="text-xs font-semibold text-slate-600 dark:text-slate-300">Nombre *</label>
        <input
          v-model="altaForm.nombre"
          type="text"
          class="mt-1 w-full rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2.5 text-sm"
          placeholder="Ej: Galletitas Oreo"
        />
      </div>
      <div>
        <label class="text-xs font-semibold text-slate-600 dark:text-slate-300">Marca</label>
        <input
          v-model="altaForm.marca"
          type="text"
          class="mt-1 w-full rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2.5 text-sm"
        />
      </div>
      <div>
        <label class="text-xs font-semibold text-slate-600 dark:text-slate-300">Precio de venta</label>
        <input
          v-model="altaForm.precio_venta"
          type="number"
          inputmode="decimal"
          min="0"
          step="0.01"
          class="mt-1 w-full rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2.5 text-sm"
        />
      </div>
      <div>
        <label class="text-xs font-semibold text-slate-600 dark:text-slate-300">Categoría</label>
        <select
          v-model="altaForm.categoria_id"
          class="mt-1 w-full rounded-lg bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 px-3 py-2.5 text-sm"
        >
          <option :value="null">Sin categoría</option>
          <option v-for="c in productosStore.categorias" :key="c.id" :value="c.id">{{ c.nombre }}</option>
        </select>
      </div>
      <button
        class="w-full rounded-xl bg-brand-600 text-white py-3 font-semibold disabled:opacity-50"
        :disabled="altaGuardando || !altaForm.nombre.trim()"
        @click="guardarAlta"
      >
        <i v-if="altaGuardando" class="fa-solid fa-circle-notch animate-spin mr-1"></i>
        Crear y asignar
      </button>
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
import { useBarcodeScanner } from '@/composables/useBarcodeScanner'
import BaseModal from '@/components/ui/BaseModal.vue'

const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()
const productosStore = useProductosStore()

const cargando = ref(true)
const sectores = ref([])
const sectorActivo = ref(null)
const escaneados = ref([])
const noEncontrados = ref([])
const codigoManual = ref('')
const sesionPorSector = ref({})
const menuOpen = ref(false)
const menuRef = ref(null)
const ultimoFlash = ref('')
const ultimoErrorFlash = ref('')
const altaAbierta = ref(false)
const altaGuardando = ref(false)
const altaForm = ref({ codigo_barras: '', nombre: '', marca: '', precio_venta: null, categoria_id: null })
// Último código que no existía, para ofrecer el alta rápida desde la cámara.
const ultimoNoEncontrado = ref('')

const menuItems = [
  { label: 'Cobro Móvil', icon: 'fa-cash-register', value: 'cobro', route: '/cobrar' },
  { label: 'Cargar Mercadería', icon: 'fa-box-open', value: 'cargar', route: '/cargar-mercaderia' },
  { label: 'Control Stock', icon: 'fa-clipboard-list', value: 'control', route: '/control-stock' },
  { label: 'Sectores', icon: 'fa-location-dot', value: 'sectores', active: true, route: null },
  { label: 'POS (PC)', icon: 'fa-desktop', value: 'pc', route: '/pos' },
]

const productos = computed(() => productosStore.productos || [])
const sinSectorCount = computed(() => productos.value.filter(p => p.activo && !p.sector_id).length)
const movidosCount = computed(() => escaneados.value.filter(e => e.sector_anterior_id).length)
// El backend sólo deja crear productos a admin y encargado.
const puedeCrear = computed(() => ['admin', 'encargado'].includes((auth.currentUser?.rol || '').toLowerCase()))

const nombresSector = computed(() => {
  const map = {}
  for (const s of sectores.value) map[s.id] = s.nombre
  return map
})

function conteoDe(s) {
  // El conteo del backend, ajustado con lo asignado en esta vuelta.
  const delta = sesionPorSector.value[s.id] || 0
  return (s.cantidad_productos || 0) + delta
}

const {
  scannerOpen,
  scannerError,
  videoEl,
  openScanner,
  closeCamera,
} = useBarcodeScanner({
  continuous: true,
  cooldownMs: 1200,
  onDetect: (raw) => procesarCodigo(raw),
})

async function cargarTodo() {
  cargando.value = true
  try {
    const [secs] = await Promise.all([
      api.get('/api/sectores').catch(() => null),
      productosStore.fetchAll(),
    ])
    sectores.value = Array.isArray(secs) ? secs : (secs?.data || [])
  } catch {
    sectores.value = []
  }
  cargando.value = false
}

function elegirSector(s) {
  sectorActivo.value = s
  escaneados.value = []
  noEncontrados.value = []
  ultimoNoEncontrado.value = ''
  // iOS sólo deja abrir la cámara desde un toque, y el toque acaba de pasar.
  openScanner()
}

function salirDelSector() {
  closeCamera()
  sectorActivo.value = null
}

function vibrar(ms = 40) {
  try { navigator.vibrate?.(ms) } catch { /* sin soporte */ }
}

function flashOk(texto) {
  ultimoFlash.value = texto
  setTimeout(() => { if (ultimoFlash.value === texto) ultimoFlash.value = '' }, 1400)
}

function flashError(texto) {
  ultimoErrorFlash.value = texto
  setTimeout(() => { if (ultimoErrorFlash.value === texto) ultimoErrorFlash.value = '' }, 2200)
}

async function procesarCodigo(raw) {
  const codigo = String(raw || '').trim()
  if (!codigo || !sectorActivo.value) return

  const p = productos.value.find(x => x.codigo_barras === codigo)
  if (!p) {
    noEncontrados.value.unshift(codigo)
    if (noEncontrados.value.length > 20) noEncontrados.value.pop()
    ultimoNoEncontrado.value = codigo
    vibrar([60, 60, 60])
    flashError(`No existe el código ${codigo}`)
    toast.error(`Código ${codigo} no encontrado`)
    return
  }
  ultimoNoEncontrado.value = ''

  if (p.sector_id === sectorActivo.value.id) {
    flashOk(`${p.nombre} ya estaba acá`)
    return
  }

  const sectorAnteriorId = p.sector_id || null
  const sectorAnterior = sectorAnteriorId ? (nombresSector.value[sectorAnteriorId] || '') : ''
  try {
    await api.post('/api/productos/asignar-sector', {
      productos_ids: [p.id],
      sector_id: sectorActivo.value.id,
    })
    productosStore.updateProductoLocal({ id: p.id, sector_id: sectorActivo.value.id })
    escaneados.value.unshift({
      id: p.id,
      nombre: p.nombre,
      marca: p.marca,
      codigo_barras: p.codigo_barras,
      sector_anterior_id: sectorAnteriorId,
      sector_anterior: sectorAnterior,
    })
    sesionPorSector.value = {
      ...sesionPorSector.value,
      [sectorActivo.value.id]: (sesionPorSector.value[sectorActivo.value.id] || 0) + 1,
    }
    vibrar()
    flashOk(`${p.nombre} → ${sectorActivo.value.nombre}`)
  } catch (e) {
    vibrar([60, 60, 60])
    flashError('No se pudo asignar')
    toast.error(e?.data?.detail || 'Error al asignar sector')
  }
}

async function deshacerUltimo() {
  const ultimo = escaneados.value.shift()
  if (!ultimo) return
  try {
    await api.post('/api/productos/asignar-sector', {
      productos_ids: [ultimo.id],
      sector_id: ultimo.sector_anterior_id,
    })
    productosStore.updateProductoLocal({ id: ultimo.id, sector_id: ultimo.sector_anterior_id })
    sesionPorSector.value = {
      ...sesionPorSector.value,
      [sectorActivo.value.id]: Math.max(0, (sesionPorSector.value[sectorActivo.value.id] || 0) - 1),
    }
    toast.success(`Deshecho: ${ultimo.nombre}`)
  } catch (e) {
    escaneados.value.unshift(ultimo)
    toast.error(e?.data?.detail || 'No se pudo deshacer')
  }
}

function limpiarVuelta() {
  escaneados.value = []
  noEncontrados.value = []
  ultimoNoEncontrado.value = ''
}

function abrirAlta(codigo) {
  // En iOS el teclado con la cámara viva se comporta mal, así que cerramos la cámara.
  closeCamera()
  // El producto está en la mano: abrimos con el código ya puesto y el sector de esta vuelta.
  altaForm.value = { codigo_barras: codigo, nombre: '', marca: '', precio_venta: null, categoria_id: null }
  altaAbierta.value = true
}

async function guardarAlta() {
  const form = altaForm.value
  if (!form.nombre.trim() || altaGuardando.value) return
  altaGuardando.value = true
  try {
    const producto = await api.post('/api/productos', {
      codigo_barras: form.codigo_barras.trim() || null,
      nombre: form.nombre.trim(),
      marca: form.marca.trim() || null,
      // El input number de Vue devuelve string; vacío no es un precio válido.
      precio_venta: form.precio_venta === '' || form.precio_venta === null ? null : Number(form.precio_venta),
      categoria_id: form.categoria_id,
      sector_id: sectorActivo.value.id,
    })
    productosStore.updateProductoLocal(producto)
    noEncontrados.value = noEncontrados.value.filter(c => c !== form.codigo_barras)
    ultimoNoEncontrado.value = ''
    escaneados.value.unshift({
      id: producto.id,
      nombre: producto.nombre,
      marca: producto.marca,
      codigo_barras: producto.codigo_barras,
      sector_anterior_id: null,
      sector_anterior: '',
    })
    sesionPorSector.value = {
      ...sesionPorSector.value,
      [sectorActivo.value.id]: (sesionPorSector.value[sectorActivo.value.id] || 0) + 1,
    }
    altaAbierta.value = false
    vibrar()
    flashOk(`Creado: ${producto.nombre}`)
    toast.success(`${producto.nombre} creado en ${sectorActivo.value.nombre}`)
  } catch (e) {
    toast.error(e?.data?.detail || 'No se pudo crear el producto')
  } finally {
    altaGuardando.value = false
  }
}

function navigateMenu(m) {
  menuOpen.value = false
  if (m.route) router.push(m.route)
}

function handleClickOutside(e) {
  if (menuRef.value && !menuRef.value.contains(e.target)) menuOpen.value = false
}

onMounted(async () => {
  document.addEventListener('click', handleClickOutside)
  await cargarTodo()
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
  closeCamera()
})
</script>
