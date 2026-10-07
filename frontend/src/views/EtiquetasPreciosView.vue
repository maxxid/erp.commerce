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
})

const tamano = ref('70x35')
const borderless = ref(false)

const productos = ref([])
const historial = ref([])
const loading = ref(false)
const generando = ref(false)
const marcando = ref(false)

const descripcionesEditadas = ref({})

const tableColumns = [
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

async function cargarHistorial() {
  try {
    const data = await api.get('/api/etiquetas/historial')
    historial.value = data || []
  } catch (e) {
    console.error('Error cargando historial:', e)
    historial.value = []
  }
}

async function cargarPreview() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    params.set('desde', filtros.desde)
    params.set('hasta', filtros.hasta)
    params.set('incluir_cambios_precio', String(filtros.incluir_cambios_precio))
    params.set('incluir_nuevos', String(filtros.incluir_nuevos))
    params.set('solo_con_stock', String(filtros.solo_con_stock))
    params.set('page', '1')
    params.set('page_size', '500')

    const data = await api.get(`/api/etiquetas/precios?${params}`)
    productos.value = data.data || []
    descripcionesEditadas.value = {}
    toast.success(`${productos.value.length} producto(s) encontrado(s)`)
  } catch (e) {
    console.error('Error cargando preview:', e)
    toast.error(e?.data?.detail || 'Error al cargar productos')
    productos.value = []
  } finally {
    loading.value = false
  }
}

async function generarPDF() {
  if (!productos.value.length) {
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
    if (e?.status === 409 && e?.data?.codigo === 'STOCK_CERO') {
      const confirmado = confirm(
        `${e.data.mensaje}.\n\n` +
        `Productos: ${e.data.productos.map(p => `${p.nombre} (stock: ${p.stock})`).join(', ')}\n\n` +
        `¿Deseas continuar y generar las etiquetas igualmente?`
      )
      if (confirmado) {
        filtros.solo_con_stock = false
        return generarPDF()
      }
    } else {
      console.error('Error generando PDF:', e)
      toast.error(e?.data?.detail || e?.data?.mensaje || 'Error al generar PDF')
    }
  } finally {
    generando.value = false
  }
}

async function marcarImpreso() {
  if (!productos.value.length) {
    toast.error('No hay productos para marcar')
    return
  }

  const ids = productos.value.map(p => p.id)
  marcando.value = true
  try {
    const resp = await api.post('/api/etiquetas/marcar-impreso', {
      productos_ids: ids,
      tamano: tamano.value,
      borderless: borderless.value,
    })
    toast.success(resp.message)
    await cargarHistorial()
    await cargarPreview()
  } catch (e) {
    console.error('Error marcando como impreso:', e)
    toast.error(e?.data?.detail || 'Error al marcar como impreso')
  } finally {
    marcando.value = false
  }
}

function actualizarDescripcion(id, valor) {
  descripcionesEditadas.value = { ...descripcionesEditadas.value, [id]: valor }
}

onMounted(async () => {
  await cargarHistorial()
  await cargarPreview()
})
</script>

<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Etiquetas de Precios</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">
          Genera etiquetas para productos con cambios de precio o nuevos en un período
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

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <BaseInput v-model="filtros.desde" type="date" label="Desde" />
        <BaseInput v-model="filtros.hasta" type="date" label="Hasta" />
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
      </div>

      <div v-if="productos.length" class="flex items-center gap-3 text-sm text-slate-500 dark:text-slate-400 pt-2 border-t border-slate-200 dark:border-slate-700">
        <span class="font-semibold text-slate-900 dark:text-white">{{ totalEtiquetas }} producto(s)</span>
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

    <EmptyState v-else-if="!loading" icon="fa-tag" title="Sin productos para etiquetar" text="Ajustá los filtros de fecha y dale a Vista previa" compact />
  </div>
</template>