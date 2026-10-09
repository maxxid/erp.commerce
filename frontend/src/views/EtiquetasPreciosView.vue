<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency } from '@/composables/useUtils'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const toast = useToastStore()

const hoy = new Date()
const hace30 = new Date()
hace30.setDate(hoy.getDate() - 30)

function fechaISO(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatFechaImpresion(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function formatFechaCorta(iso) {
  return new Date(iso).toLocaleDateString('es-AR')
}

const filtros = reactive({
  desde: fechaISO(hace30),
  hasta: fechaISO(hoy),
  incluir_cambios_precio: true,
  incluir_nuevos: true,
  solo_con_stock: false,
  categoria_id: null,
  orden: 'fecha_desc',
})

const presetActivo = ref('30d')
const presets = [
  { key: 'hoy', label: 'Hoy', dias: 0 },
  { key: '7d', label: '7 días', dias: 6 },
  { key: '30d', label: '30 días', dias: 29 },
  { key: '90d', label: '90 días', dias: 89 },
]

function aplicarPreset(key) {
  presetActivo.value = key
  const p = presets.find(x => x.key === key)
  if (!p) return
  const d = new Date()
  filtros.hasta = fechaISO(d)
  d.setDate(d.getDate() - p.dias)
  filtros.desde = fechaISO(d)
  cargarPreview()
}

function onFechaChange() {
  presetActivo.value = null
}

const ordenOptions = [
  { value: 'fecha_desc', label: 'Más recientes' },
  { value: 'fecha_asc', label: 'Más antiguos' },
  { value: 'nombre', label: 'Nombre (A-Z)' },
  { value: 'categoria', label: 'Categoría' },
]

const tamano = ref('70x35')
const borderless = ref(false)

const categorias = ref([])
const productos = ref([])
const historial = ref([])
const loading = ref(false)
const generando = ref(false)
const marcando = ref(false)
const showHistorial = ref(false)

const descripcionesEditadas = ref({})
const selectedProductos = ref(new Set())

const tableColumns = [
  { key: 'select', label: '', width: 'w-10', align: 'center', mobile: false },
  { key: 'nombre', label: 'Producto' },
  { key: 'motivo', label: '', width: 'w-24', mobile: false },
  { key: 'descripcion', label: 'Descripción', width: 'w-56', mobile: false },
  { key: 'precio', label: 'Precio', align: 'right', width: 'w-28' },
  { key: 'stock', label: 'Stock', align: 'right', width: 'w-16', mobile: false },
]

const tableRows = computed(() => productos.value.map(p => ({
  ...p,
  precio: p.tipo_venta === 'kilo' && p.precio_por_kilo ? p.precio_por_kilo : p.precio_venta,
})))

const sinStockCount = computed(() => productos.value.filter(p => (p.stock_actual || 0) <= 0).length)
const totalEtiquetas = computed(() => productos.value.length)
const productosSeleccionados = computed(() => productos.value.filter(p => selectedProductos.value.has(p.id)))

const previewLabel = computed(() => {
  const lista = productosSeleccionados.value.length ? productosSeleccionados.value : productos.value
  if (!lista.length) return null
  const p = lista[0]
  const desc = descripcionesEditadas.value[p.id] ?? p.descripcion ?? ''
  const precio = p.tipo_venta === 'kilo' && p.precio_por_kilo ? p.precio_por_kilo : p.precio_venta
  return {
    nombre: p.nombre,
    marca: p.marca,
    descripcion: desc,
    precio,
    esKilo: p.tipo_venta === 'kilo' && p.precio_por_kilo,
    codigo: p.codigo_barras,
  }
})

const labelSizeStyle = computed(() => {
  // Aspect ratio real de la etiqueta (70x35 = 2:1, 60x40 = 3:2)
  return tamano.value === '70x35'
    ? { aspectRatio: '70 / 35', maxWidth: '220px' }
    : { aspectRatio: '60 / 40', maxWidth: '200px' }
})

const todosSeleccionados = computed(() => {
  if (!productos.value.length) return false
  return productos.value.every(p => selectedProductos.value.has(p.id))
})

function toggleSelectAll() {
  if (todosSeleccionados.value) {
    selectedProductos.value.clear()
  } else {
    productos.value.forEach(p => selectedProductos.value.add(p.id))
  }
}

function toggleProducto(id) {
  if (selectedProductos.value.has(id)) {
    selectedProductos.value.delete(id)
  } else {
    selectedProductos.value.add(id)
  }
}

function motivoBadge(motivo) {
  if (motivo === 'nuevo') return { variant: 'success', label: 'Nuevo' }
  if (motivo === 'ambos') return { variant: 'info', label: 'Nuevo + Precio' }
  return { variant: 'warning', label: 'Precio' }
}

async function cargarCategorias() {
  try {
    const data = await api.get('/api/categorias?page_size=500')
    categorias.value = Array.isArray(data) ? data : (data?.data || [])
  } catch {
    categorias.value = []
  }
}

async function cargarHistorial() {
  try {
    const data = await api.get('/api/etiquetas/historial')
    historial.value = Array.isArray(data) ? data : (data?.data || [])
  } catch {
    historial.value = []
  }
}

async function cargarPreview(silent = false) {
  loading.value = true
  selectedProductos.value.clear()
  try {
    const params = new URLSearchParams()
    params.set('desde', filtros.desde)
    params.set('hasta', filtros.hasta)
    params.set('incluir_cambios_precio', String(filtros.incluir_cambios_precio))
    params.set('incluir_nuevos', String(filtros.incluir_nuevos))
    params.set('solo_con_stock', String(filtros.solo_con_stock))
    if (filtros.categoria_id) params.set('categoria_id', String(filtros.categoria_id))
    params.set('orden', filtros.orden)
    params.set('page', '1')
    params.set('page_size', '500')

    const data = await api.get(`/api/etiquetas/precios?${params}`)
    productos.value = Array.isArray(data) ? data : (data?.data || [])
    descripcionesEditadas.value = {}
    if (!silent) {
      if (productos.value.length) {
        toast.success(`${productos.value.length} producto(s) para etiquetar`)
      } else {
        toast.info('Sin productos para esos filtros.')
      }
    }
  } catch (e) {
    toast.error(e?.data?.detail || 'Error al cargar productos')
    productos.value = []
  } finally {
    loading.value = false
  }
}

function verTodoCatalogo() {
  filtros.incluir_cambios_precio = false
  filtros.incluir_nuevos = false
  cargarPreview()
}

const stockCeroModal = ref(false)
const stockCeroData = ref(null)

function parsearDetalle409(e) {
  let crudo = e?.data?.detail
  if (typeof crudo === 'string') {
    try { crudo = JSON.parse(crudo) } catch { return null }
  }
  if (crudo?.codigo) return crudo
  if (crudo?.detail && typeof crudo.detail === 'object') return crudo.detail
  return null
}

async function generarPDF(forzar = false) {
  const idsAImprimir = selectedProductos.value.size > 0
    ? [...selectedProductos.value]
    : productos.value.map(p => p.id)

  if (!idsAImprimir.length) {
    toast.error('No hay productos para generar etiquetas')
    return
  }

  generando.value = true
  try {
    const payload = {
      filtros: { ...filtros },
      tamano: tamano.value,
      borderless: borderless.value,
      descripciones_editadas: descripcionesEditadas.value,
      productos_ids: idsAImprimir,
      forzar,
    }

    const response = await api.request('POST', '/api/etiquetas/precios/generar-pdf', payload, null, { responseType: 'blob' })

    if (response instanceof Blob) {
      const url = window.URL.createObjectURL(response)
      const a = document.createElement('a')
      a.href = url
      a.download = `etiquetas-${filtros.desde}-a-${filtros.hasta}-${tamano.value}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      toast.success('PDF generado y descargado')
    } else {
      throw new Error('Respuesta inesperada del servidor')
    }
  } catch (e) {
    const detalle = parsearDetalle409(e)
    if (e?.status === 409 && detalle?.codigo === 'STOCK_CERO') {
      stockCeroData.value = detalle
      stockCeroModal.value = true
    } else {
      toast.error(typeof e?.data?.detail === 'string' ? e.data.detail : (detalle?.mensaje || 'Error al generar PDF'))
    }
  } finally {
    generando.value = false
  }
}

function confirmarGenerarConStockCero() {
  stockCeroModal.value = false
  generarPDF(true)
}

async function marcarImpreso() {
  const idsAMarcar = selectedProductos.value.size > 0
    ? [...selectedProductos.value]
    : productos.value.map(p => p.id)

  if (!idsAMarcar.length) {
    toast.error('No hay productos para marcar')
    return
  }

  marcando.value = true
  try {
    const resp = await api.post('/api/etiquetas/marcar-impreso', {
      productos_ids: idsAMarcar,
      tamano: tamano.value,
      borderless: borderless.value,
    })
    const marcados = resp?.marcados ?? idsAMarcar.length
    toast.success(`${marcados} producto(s) marcados como etiquetados`)
    await cargarHistorial()
    await cargarPreview(true)
  } catch (e) {
    toast.error(e?.data?.detail || 'Error al marcar como impreso')
  } finally {
    marcando.value = false
  }
}

function actualizarDescripcion(id, valor) {
  descripcionesEditadas.value = { ...descripcionesEditadas.value, [id]: valor }
}

onMounted(async () => {
  await cargarCategorias()
  await cargarHistorial()
  await cargarPreview(true)
})
</script>

<template>
  <div class="p-4 md:p-6 space-y-4 md:space-y-5 max-w-[1400px] mx-auto">
    <!-- Header -->
    <div class="flex items-center justify-between gap-3">
      <div class="min-w-0">
        <h1 class="text-xl md:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
          <i class="fa-solid fa-tag text-brand-500"></i>
          Etiquetas de Precios
        </h1>
        <p class="text-xs md:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          Etiquetas para productos con cambios de precio o ingresados en un período
        </p>
      </div>
      <button
        class="shrink-0 flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl transition-colors"
        @click="showHistorial = true"
      >
        <i class="fa-solid fa-clock-rotate-left"></i>
        <span class="hidden sm:inline">Historial</span>
        <span v-if="historial.length" class="text-[10px] font-bold bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400 px-1.5 py-0.5 rounded-full">{{ historial.length }}</span>
      </button>
    </div>

    <!-- Presets de fecha -->
    <div class="flex items-center gap-2 flex-wrap">
      <button
        v-for="p in presets"
        :key="p.key"
        class="px-3.5 py-1.5 text-xs font-semibold rounded-full border transition-colors"
        :class="presetActivo === p.key
          ? 'bg-brand-600 text-white border-brand-600'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-700'"
        @click="aplicarPreset(p.key)"
      >
        {{ p.label }}
      </button>
      <span v-if="!presetActivo" class="text-[11px] text-slate-400 dark:text-slate-500">Personalizado</span>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-4 md:gap-5 items-start">
      <!-- Panel izquierdo: controles -->
      <div class="space-y-4">
        <!-- Filtros -->
        <BaseCard padding="md" class="space-y-4">
          <div class="grid grid-cols-2 gap-3">
            <BaseInput v-model="filtros.desde" type="date" label="Desde" size="sm" @update:modelValue="onFechaChange" />
            <BaseInput v-model="filtros.hasta" type="date" label="Hasta" size="sm" @update:modelValue="onFechaChange" />
          </div>
          <BaseSelect
            v-model="filtros.categoria_id"
            label="Categoría"
            size="sm"
            :options="[{ value: null, label: 'Todas' }, ...categorias.map(c => ({ value: c.id, label: c.nombre }))]"
            option-value="value"
            option-label="label"
          />
          <BaseSelect
            v-model="filtros.orden"
            label="Orden"
            size="sm"
            :options="ordenOptions"
            option-value="value"
            option-label="label"
          />

          <div class="space-y-2 pt-1 border-t border-slate-100 dark:border-slate-800">
            <label class="flex items-center gap-2.5 cursor-pointer group">
              <input type="checkbox" v-model="filtros.incluir_cambios_precio" class="w-3.5 h-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
              <span class="text-xs text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">Cambios de precio</span>
            </label>
            <label class="flex items-center gap-2.5 cursor-pointer group">
              <input type="checkbox" v-model="filtros.incluir_nuevos" class="w-3.5 h-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
              <span class="text-xs text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">Productos nuevos</span>
            </label>
            <label class="flex items-center gap-2.5 cursor-pointer group">
              <input type="checkbox" v-model="filtros.solo_con_stock" class="w-3.5 h-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
              <span class="text-xs text-slate-600 dark:text-slate-300 group-hover:text-slate-900 dark:group-hover:text-white transition-colors">Solo con stock</span>
            </label>
          </div>

          <BaseButton @click="cargarPreview" :loading="loading" variant="secondary" size="sm" class="w-full">
            <i class="fa-solid fa-arrows-rotate mr-1.5"></i> Actualizar vista previa
          </BaseButton>
        </BaseCard>

        <!-- Formato de etiqueta -->
        <BaseCard padding="md" class="space-y-3">
          <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">Formato</h3>
          <div class="grid grid-cols-2 gap-2">
            <button
              v-for="opt in [{ v: '70x35', l: '70×35 mm', s: '30/hoja' }, { v: '60x40', l: '60×40 mm', s: '24/hoja' }]"
              :key="opt.v"
              class="p-2.5 rounded-xl border text-center transition-all"
              :class="tamano === opt.v
                ? 'border-brand-500 bg-brand-50 dark:bg-brand-950/30 ring-1 ring-brand-500'
                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
              @click="tamano = opt.v"
            >
              <div class="text-xs font-bold" :class="tamano === opt.v ? 'text-brand-700 dark:text-brand-300' : 'text-slate-700 dark:text-slate-300'">{{ opt.l }}</div>
              <div class="text-[10px] text-slate-400 mt-0.5">{{ opt.s }}</div>
            </button>
          </div>
          <label class="flex items-center gap-2.5 cursor-pointer">
            <input type="checkbox" v-model="borderless" class="w-3.5 h-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
            <span class="text-xs text-slate-600 dark:text-slate-300">Sin bordes (A4 completo)</span>
          </label>

          <!-- Preview visual de la etiqueta -->
          <div v-if="previewLabel" class="pt-2 border-t border-slate-100 dark:border-slate-800">
            <div class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Así se ve la etiqueta</div>
            <div
              class="bg-white border border-slate-300 rounded-md p-2 shadow-sm mx-auto select-none overflow-hidden"
              :style="labelSizeStyle"
            >
              <div v-if="previewLabel.marca" class="text-[8px] font-bold text-slate-800 truncate leading-none">{{ previewLabel.marca }}</div>
              <div class="border-t border-slate-400 my-1"></div>
              <div class="text-[7px] text-slate-700 leading-tight line-clamp-2 min-h-[14px]">{{ previewLabel.descripcion || previewLabel.nombre }}</div>
              <!-- Barcode mockup -->
              <div class="flex items-end gap-[1px] h-[18px] my-1 justify-center overflow-hidden">
                <div v-for="i in 40" :key="i" class="bg-slate-800" :style="{ width: (i % 3 === 0 ? '2px' : '1px'), height: (i % 5 === 0 ? '100%' : '80%') }"></div>
              </div>
              <div class="flex items-baseline justify-between">
                <span class="text-[13px] font-extrabold text-slate-900 leading-none">
                  {{ formatCurrency(previewLabel.precio) }}<span v-if="previewLabel.esKilo" class="text-[9px] font-bold ml-0.5">/kg</span>
                </span>
                <span class="text-[6px] text-slate-400">{{ new Date().toLocaleDateString('es-AR') }}</span>
              </div>
              <div class="text-center text-[6px] font-mono text-slate-500 mt-0.5 truncate">{{ previewLabel.codigo }}</div>
            </div>
          </div>
        </BaseCard>

        <!-- Acciones -->
        <BaseCard padding="md" class="space-y-3">
          <div class="flex items-center justify-between text-xs">
            <span class="text-slate-500 dark:text-slate-400">
              <span class="font-bold text-slate-900 dark:text-white text-sm">{{ totalEtiquetas }}</span> etiqueta(s)
            </span>
            <span v-if="selectedProductos.size > 0" class="px-2 py-0.5 rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 font-medium">
              {{ selectedProductos.size }} sel.
            </span>
            <span v-else-if="sinStockCount > 0" class="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 font-medium">
              {{ sinStockCount }} sin stock
            </span>
          </div>

          <BaseButton
            @click="generarPDF"
            :loading="generando"
            variant="primary"
            class="w-full"
            :disabled="!productos.length"
          >
            <i class="fa-solid fa-file-pdf mr-1.5"></i>
            {{ selectedProductos.size > 0 ? `Generar ${selectedProductos.size} etiqueta(s)` : 'Generar PDF' }}
          </BaseButton>

          <div class="grid grid-cols-2 gap-2">
            <BaseButton @click="marcarImpreso" :loading="marcando" variant="success" size="sm" :disabled="!productos.length">
              <i class="fa-solid fa-check mr-1"></i> Marcar impreso
            </BaseButton>
            <BaseButton @click="toggleSelectAll" variant="ghost" size="sm" :disabled="!productos.length">
              <i :class="todosSeleccionados ? 'fa-solid fa-square-minus' : 'fa-solid fa-square-check'"></i>
              {{ todosSeleccionados ? 'Limpiar' : 'Todo' }}
            </BaseButton>
          </div>
        </BaseCard>
      </div>

      <!-- Panel derecho: tabla -->
      <div>
        <BaseCard v-if="productos.length" padding="none">
          <BaseTable
            :columns="tableColumns"
            :rows="tableRows"
            :loading="loading"
            empty-title="No hay productos"
            empty-text="Ajustá los filtros y dale a Actualizar"
            empty-icon="fa-tag"
          >
            <template #select="{ row }">
              <input
                type="checkbox"
                class="w-3.5 h-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
                :checked="selectedProductos.has(row.id)"
                @click="toggleProducto(row.id)"
              />
            </template>
            <template #nombre="{ row }">
              <div class="min-w-0">
                <div class="text-xs font-medium text-slate-800 dark:text-slate-100 truncate">{{ row.nombre }}</div>
                <div class="text-[10px] text-slate-400 truncate">{{ row.categoria_nombre || row.codigo_barras }}</div>
              </div>
            </template>
            <template #motivo="{ row }">
              <BaseBadge :variant="motivoBadge(row.motivo).variant" size="xs">
                {{ motivoBadge(row.motivo).label }}
              </BaseBadge>
            </template>
            <template #descripcion="{ row }">
              <BaseInput
                :value="descripcionesEditadas[row.id] ?? row.descripcion ?? ''"
                @input="actualizarDescripcion(row.id, $event.target.value)"
                size="sm"
                input-class="text-[11px]"
                placeholder="Descripción opcional"
              />
            </template>
            <template #precio="{ row }">
              <span class="font-mono-data font-bold text-xs text-brand-600 dark:text-brand-400">
                {{ formatCurrency(row.precio) }}
                <span v-if="row.tipo_venta === 'kilo'" class="text-[9px] text-amber-500 ml-0.5">/kg</span>
              </span>
            </template>
            <template #stock="{ row }">
              <span
                class="font-mono-data text-xs font-semibold"
                :class="row.stock_actual <= 0 ? 'text-rose-500' : row.stock_actual <= 5 ? 'text-amber-500' : 'text-slate-600 dark:text-slate-400'"
              >
                {{ row.stock_actual }}
              </span>
            </template>
          </BaseTable>
        </BaseCard>

        <EmptyState
          v-else-if="!loading"
          icon="fa-tag"
          title="Sin productos para etiquetar"
          text="No hubo cambios de precio ni altas en ese período. Ampliá las fechas o mirá todo el catálogo."
          action-text="Ver todo el catálogo"
          compact
          @action="verTodoCatalogo"
        />
      </div>
    </div>

    <!-- Modal: Historial -->
    <BaseModal v-model="showHistorial" title="Historial de impresiones" size="md">
      <div v-if="historial.length" class="space-y-2">
        <div
          v-for="(h, i) in historial"
          :key="i"
          class="flex items-center gap-3 px-3.5 py-2.5 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-100 dark:border-slate-800"
        >
          <div class="w-9 h-9 rounded-lg bg-brand-100 dark:bg-brand-900/30 flex items-center justify-center shrink-0">
            <i class="fa-solid fa-print text-brand-500 text-sm"></i>
          </div>
          <div class="flex-1 min-w-0">
            <div class="text-xs font-medium text-slate-800 dark:text-slate-200">{{ formatFechaImpresion(h.fecha_impresion) }}</div>
            <div class="text-[10px] text-slate-400 mt-0.5">{{ formatFechaCorta(h.desde) }} – {{ formatFechaCorta(h.hasta) }}</div>
          </div>
          <div class="flex items-center gap-1.5 shrink-0">
            <BaseBadge variant="default" size="xs">{{ h.total_etiquetas }}</BaseBadge>
            <BaseBadge :variant="h.tamano === '70x35' ? 'info' : 'success'" size="xs">{{ h.tamano }}</BaseBadge>
          </div>
        </div>
      </div>
      <p v-else class="text-sm text-slate-400 text-center py-6">Sin impresiones previas</p>
    </BaseModal>

    <!-- Modal: stock cero -->
    <BaseModal v-model="stockCeroModal" title="Productos con stock cero" size="md">
      <div class="space-y-3">
        <p class="text-sm text-slate-600 dark:text-slate-300">
          {{ stockCeroData?.mensaje }}. Se generarán las etiquetas igualmente.
        </p>
        <ul v-if="stockCeroData?.productos?.length" class="max-h-48 overflow-y-auto space-y-1">
          <li
            v-for="p in stockCeroData.productos"
            :key="p.id"
            class="flex items-center justify-between gap-3 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 text-sm"
          >
            <span class="text-slate-700 dark:text-slate-300 truncate text-xs">{{ p.nombre }}</span>
            <BaseBadge variant="danger" size="xs" class="shrink-0">stock {{ p.stock }}</BaseBadge>
          </li>
        </ul>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <BaseButton variant="secondary" size="sm" @click="stockCeroModal = false">Cancelar</BaseButton>
          <BaseButton variant="primary" size="sm" @click="confirmarGenerarConStockCero">Generar igual</BaseButton>
        </div>
      </template>
    </BaseModal>
  </div>
</template>
