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

const ordenOptions = [
  { value: 'fecha_desc', label: 'Más recientes primero (por ingreso)' },
  { value: 'fecha_asc', label: 'Más antiguos primero' },
  { value: 'nombre', label: 'Por nombre (A-Z)' },
  { value: 'categoria', label: 'Por categoría' },
]

const tamano = ref('70x35')
const borderless = ref(false)

const categorias = ref([])
const productos = ref([])
const historial = ref([])
const loading = ref(false)
const generando = ref(false)
const marcando = ref(false)

const descripcionesEditadas = ref({})
const selectedProductos = ref(new Set())

const tableColumns = [
  { key: 'select', label: '', width: 'w-12', align: 'center' },
  { key: 'codigo_barras', label: 'Código', width: 'w-36' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'marca', label: 'Marca' },
  { key: 'descripcion', label: 'Descripción', width: 'w-72' },
  { key: 'categoria_nombre', label: 'Categoría', width: 'w-40' },
  { key: 'precio', label: 'Precio', align: 'right', width: 'w-36' },
  { key: 'stock', label: 'Stock', align: 'right', width: 'w-24' },
]

const tableRows = computed(() => productos.value.map(p => ({
  ...p,
  precio: p.tipo_venta === 'kilo' && p.precio_por_kilo ? p.precio_por_kilo : p.precio_venta,
  stock: p.stock_actual,
})))

const sinStockCount = computed(() => productos.value.filter(p => (p.stock_actual || 0) <= 0).length)
const totalEtiquetas = computed(() => productos.value.length)

const todosSeleccionados = computed(() => {
  if (!productos.value.length) return false
  return productos.value.every(p => selectedProductos.value.has(p.id))
})

const algunosSeleccionados = computed(() => {
  if (!productos.value.length) return false
  return productos.value.some(p => selectedProductos.value.has(p.id)) && !todosSeleccionados.value
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

    // api.js desenvuelve el body: el endpoint responde {data: [...]} y acá ya
    // llega el array directo.
    const data = await api.get(`/api/etiquetas/precios?${params}`)
    productos.value = Array.isArray(data) ? data : (data?.data || [])
    descripcionesEditadas.value = {}
    if (!silent) {
      if (productos.value.length) {
        toast.success(`${productos.value.length} producto(s) para etiquetar`)
      } else {
        toast.info('Sin productos para esos filtros. Ampliá el período o desactivá los checkboxes de cambios/nuevos.')
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

// El backend responde 409 con {detail: {...}}; con responseType blob el helper
// de api deja el cuerpo crudo como string en error.data.detail.
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
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
          <i class="fa-solid fa-tag text-brand-500"></i>
          Etiquetas de Precios
        </h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Genera etiquetas para productos con cambios de precio o ingresados en un período
        </p>
      </div>
    </div>

    <!-- Historial de impresiones -->
    <BaseCard class="space-y-3">
      <h3 class="font-semibold text-slate-900 dark:text-white flex items-center gap-2">
        <i class="fa-solid fa-history text-brand-500"></i>
        Últimas 5 impresiones
      </h3>
      <div v-if="historial.length" class="space-y-2">
        <div
          v-for="h in historial"
          :key="h.fecha_impresion"
          class="flex flex-wrap items-center gap-3 px-3 py-2 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700"
        >
          <span class="font-mono-data text-sm text-slate-900 dark:text-white">
          {{ formatFechaImpresion(h.fecha_impresion) }}
        </span>
        <span class="text-xs text-slate-500 dark:text-slate-400">
          {{ formatFechaCorta(h.desde) }} – {{ formatFechaCorta(h.hasta) }}
        </span>
          <BaseBadge variant="default" size="sm">{{ h.total_etiquetas }} etiquetas</BaseBadge>
          <BaseBadge :variant="h.tamano === '70x35' ? 'info' : 'success'" size="sm">{{ h.tamano }}</BaseBadge>
          <BaseBadge v-if="h.borderless" variant="warning" size="sm">
            <i class="fa-solid fa-expand mr-1"></i> Sin bordes
          </BaseBadge>
        </div>
      </div>
      <p v-else class="text-sm text-slate-500 dark:text-slate-400 py-2">Sin impresiones previas</p>
    </BaseCard>

    <!-- Filtros -->
    <BaseCard class="space-y-4">
      <h3 class="font-semibold text-slate-900 dark:text-white">Filtros</h3>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <BaseInput v-model="filtros.desde" type="date" label="Desde" />
        <BaseInput v-model="filtros.hasta" type="date" label="Hasta" />
        <BaseSelect
          v-model="filtros.categoria_id"
          label="Categoría"
          :options="[{ value: null, label: 'Todas' }, ...categorias.map(c => ({ value: c.id, label: c.nombre }))]"
          option-value="value"
          option-label="label"
          placeholder="Todas"
        />
        <BaseSelect
          v-model="filtros.orden"
          label="Ordenar por"
          :options="ordenOptions"
          option-value="value"
          option-label="label"
        />
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" v-model="filtros.incluir_cambios_precio" class="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
          <span class="text-sm text-slate-700 dark:text-slate-300">Cambios de precio</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" v-model="filtros.incluir_nuevos" class="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
          <span class="text-sm text-slate-700 dark:text-slate-300">Productos nuevos</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" v-model="filtros.solo_con_stock" class="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
          <span class="text-sm text-slate-700 dark:text-slate-300">Solo con stock > 0</span>
        </label>
      </div>

      <div class="flex flex-wrap items-center gap-4 pt-2 border-t border-slate-200 dark:border-slate-700">
        <div class="flex items-center gap-2">
          <label class="text-sm font-medium text-slate-700 dark:text-slate-300">Tamaño:</label>
          <select v-model="tamano" class="px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none">
            <option value="70x35">70×35 mm (30 por hoja)</option>
            <option value="60x40">60×40 mm (24 por hoja)</option>
          </select>
        </div>
        <label class="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" v-model="borderless" class="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
          <span class="text-sm text-slate-700 dark:text-slate-300">Sin bordes (A4 completo)</span>
        </label>
      </div>

      <div class="flex flex-wrap items-center gap-2">
        <BaseButton @click="cargarPreview" :loading="loading" variant="secondary">
          <i class="fa-solid fa-eye mr-1"></i> Vista previa
        </BaseButton>
        <BaseButton @click="generarPDF" :loading="generando" variant="primary">
          <i class="fa-solid fa-file-pdf mr-1"></i> Generar PDF
        </BaseButton>
        <BaseButton @click="marcarImpreso" :loading="marcando" variant="success" :disabled="!productos.length">
          <i class="fa-solid fa-check mr-1"></i> Marcar como impreso
        </BaseButton>
        <BaseButton @click="toggleSelectAll" variant="secondary" size="sm" :disabled="!productos.length">
          <i :class="todosSeleccionados ? 'fa-solid fa-minus-square' : 'fa-solid fa-check-square'"></i>
          {{ todosSeleccionados ? 'Deseleccionar todo' : 'Seleccionar todo' }}
        </BaseButton>
      </div>

      <div v-if="productos.length" class="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200 dark:border-slate-700">
        <span class="font-semibold text-slate-900 dark:text-white">{{ totalEtiquetas }} producto(s)</span>
        <span v-if="selectedProductos.size > 0" class="px-2 py-0.5 rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300 text-xs font-medium">
          {{ selectedProductos.size }} seleccionado{{ selectedProductos.size !== 1 ? 's' : '' }}
        </span>
        <span v-if="sinStockCount > 0" class="px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 text-xs font-medium">
          {{ sinStockCount }} sin stock
        </span>
      </div>
    </BaseCard>

    <!-- Preview tabla -->
    <BaseCard v-if="productos.length" class="space-y-3">
      <h3 class="font-semibold text-slate-900 dark:text-white">Vista previa (editable)</h3>
      <p class="text-xs text-slate-500 dark:text-slate-400">
        Editá la descripción si querés que salga diferente en la etiqueta. Orden: categoría → nombre.
      </p>
      <BaseTable
        :columns="tableColumns"
        :rows="tableRows"
        :loading="loading"
        empty-title="No hay productos"
        empty-text="Ajustá los filtros y dale a Vista previa"
        empty-icon="fa-tag"
      >
        <template #select="{ row }">
          <input
            type="checkbox"
            class="w-4 h-4 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
            :checked="selectedProductos.has(row.id)"
            @click="toggleProducto(row.id)"
          />
        </template>
        <template #descripcion="{ row }">
          <BaseInput
            :value="descripcionesEditadas[row.id] ?? row.descripcion ?? ''"
            @input="actualizarDescripcion(row.id, $event.target.value)"
            size="sm"
            input-class="text-xs"
            placeholder="Descripción opcional"
          />
        </template>
        <template #precio="{ row }">
          <span class="font-mono-data font-bold text-brand-600 dark:text-brand-400">
            {{ formatCurrency(row.precio) }}
            <span v-if="row.tipo_venta === 'kilo'" class="text-[10px] text-amber-500 ml-1">/kg</span>
          </span>
        </template>
        <template #stock="{ row }">
          <BaseBadge
            :variant="row.stock <= 0 ? 'danger' : row.stock <= 5 ? 'warning' : 'success'"
            size="xs"
          >
            {{ row.stock }}
          </BaseBadge>
        </template>
        <template #categoria_nombre="{ row }">
          <span class="text-xs text-slate-500 dark:text-slate-400">{{ row.categoria_nombre || '—' }}</span>
        </template>
      </BaseTable>
    </BaseCard>

    <EmptyState
      v-else-if="!loading"
      icon="fa-tag"
      title="Sin productos para etiquetar"
      text="No hubo cambios de precio ni altas en ese período. Ampliá las fechas, o mirá todo el catálogo."
      action-text="Ver todo el catálogo"
      compact
      @action="verTodoCatalogo"
    />

    <!-- Modal: stock cero al generar PDF -->
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
            <span class="text-slate-700 dark:text-slate-300 truncate">{{ p.nombre }}</span>
            <BaseBadge variant="danger" size="xs" class="shrink-0">stock {{ p.stock }}</BaseBadge>
          </li>
        </ul>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <BaseButton variant="secondary" @click="stockCeroModal = false">Cancelar</BaseButton>
          <BaseButton variant="primary" @click="confirmarGenerarConStockCero">Generar igual</BaseButton>
        </div>
      </template>
    </BaseModal>
  </div>
</template>