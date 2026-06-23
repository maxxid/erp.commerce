<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()

const searchQuery = ref('')
const filterCategory = ref(null)
const filterStockBajo = ref(false)
const filterPrecioDefasado = ref(false)
const syncing = ref(false)
const saving = ref(false)
const deleting = ref(false)
const lookingUp = ref(false)
const loading = ref(true)

const showModal = ref(false)
const editingProduct = ref(null)
const deleteTarget = ref(null)
const formError = ref('')
const highlightedIds = ref(new Set())
const showBarcodeHint = ref(false)

const products = ref([
  { id: 1, codigo_barras: '7791234567890', nombre: 'Coca-Cola 2.25L', marca: 'Coca-Cola', precio_venta: 2800, precio_costo: 2100, categoria_id: 1, stock_actual: 45 },
  { id: 2, codigo_barras: '7799876543210', nombre: 'Arroz Gallo 1kg', marca: 'Gallo', precio_venta: 1500, precio_costo: 1100, categoria_id: 2, stock_actual: 120 },
  { id: 3, codigo_barras: '7794561237890', nombre: 'Agua Mineral 1.5L', marca: 'Villa del Sur', precio_venta: 950, precio_costo: 600, categoria_id: 1, stock_actual: 80 }
])

const categories = ref([
  { id: 1, nombre: 'Bebidas' },
  { id: 2, nombre: 'Almacén' }
])

const defaultForm = () => ({
  codigo_barras: '',
  nombre: '',
  marca: '',
  precio_venta: 0,
  precio_costo: 0,
  categoria_id: null,
  stock_actual: 0
})

const form = reactive(defaultForm())

const tableColumns = [
  { key: 'image', label: '', width: 'w-16' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'codigo_barras', label: 'Código' },
  { key: 'marca', label: 'Marca' },
  { key: 'precio_costo', label: 'Costo', align: 'right' },
  { key: 'precio_venta', label: 'Precio', align: 'right' },
  { key: 'stock_actual', label: 'Stock', align: 'right' },
  { key: 'categoria', label: 'Categoría' },
  { key: 'acciones', label: '', align: 'right', width: 'w-24' }
]

const filteredProducts = computed(() => {
  let list = products.value
  if (filterCategory.value) {
    list = list.filter(p => p.categoria_id === filterCategory.value)
  }
  if (filterStockBajo.value) {
    list = list.filter(p => p.stock_actual <= (p.stock_minimo || 5) && p.stock_actual >= 0)
  }
  if (filterPrecioDefasado.value) {
    list = list.filter(p => p.precio_venta > 0 && p.precio_costo > 0 && p.precio_venta <= p.precio_costo)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(p =>
      p.nombre.toLowerCase().includes(q) ||
      p.marca.toLowerCase().includes(q) ||
      p.codigo_barras.includes(q)
    )
  }
  return list
})

const tableRows = computed(() => filteredProducts.value.map(p => ({ ...p, categoria: categoryName(p.categoria_id) })))

function categoryName(catId) {
  const cat = categories.value.find(c => c.id === catId)
  return cat ? cat.nombre : '\u2014'
}

async function fetchProductsData(checkPendientes = false) {
  loading.value = true
  try {
    const [prods, cats] = await Promise.all([
      api.get('/api/productos?page_size=200').catch(() => null),
      api.get('/api/categorias').catch(() => null)
    ])
    if (prods && prods.length) products.value = prods
    if (cats && cats.length) categories.value = cats

    if (checkPendientes) {
      const pendientes = prods?.filter(p =>
        (p.codigo_barras && (p.codigo_barras.startsWith('*MANUAL*') || p.codigo_barras.startsWith('GEN-'))) ||
        (p.fuente === 'manual' && p.stock_actual === 0 && !p.precio_costo)
      ) || []
      if (pendientes.length) {
        highlightedIds.value = new Set(pendientes.map(p => p.id))
        setTimeout(() => { highlightedIds.value = new Set() }, 3000)
      }
    }
  } catch { /* fallback to mock */ }
  loading.value = false
}

onMounted(() => fetchProductsData(true))
watch(() => route.path, (path) => {
  if (path === '/products') fetchProductsData()
})

async function syncProducts() {
  syncing.value = true
  try {
    const [prods, cats] = await Promise.all([
      api.get('/api/productos').catch(() => null),
      api.get('/api/categorias').catch(() => null)
    ])
    if (prods && prods.length) products.value = prods
    if (cats && cats.length) categories.value = cats
    toast.success('Productos sincronizados')
  } catch {
    toast.info('Usando datos locales')
  }
  syncing.value = false
}

function openCreateModal() {
  editingProduct.value = null
  formError.value = ''
  Object.assign(form, defaultForm())
  showModal.value = true
}

function openEditModal(product) {
  editingProduct.value = product
  formError.value = ''
  showBarcodeHint.value = false
  let barcode = product.codigo_barras
  if (barcode && (barcode.startsWith('*MANUAL*') || barcode.startsWith('GEN-'))) {
    const seq = products.value.filter(p => p.codigo_barras && (p.codigo_barras.startsWith('*MANUAL*') || p.codigo_barras.startsWith('GEN-'))).length + 1
    barcode = `GEN-${String(seq).padStart(8, '0')}`
    showBarcodeHint.value = true
    setTimeout(() => { showBarcodeHint.value = false }, 5000)
  }
  Object.assign(form, {
    codigo_barras: barcode,
    nombre: product.nombre,
    marca: product.marca,
    precio_venta: product.precio_venta,
    precio_costo: product.precio_costo,
    categoria_id: product.categoria_id,
    stock_actual: product.stock_actual
  })
  showModal.value = true
}

function closeModal() {
  showModal.value = false
  editingProduct.value = null
  formError.value = ''
  showBarcodeHint.value = false
}

async function lookupBarcode() {
  const code = form.codigo_barras?.trim()
  if (!code || code.length < 8) return
  lookingUp.value = true
  try {
    const resp = await api.post('/api/productos/lookup', { barcode: code })
    if (resp) {
      form.nombre = resp.nombre || form.nombre
      form.marca = resp.marca || form.marca
      form.precio_costo = resp.precio_referencia || form.precio_costo
      form.categoria_id = categories.value.find(c => c.nombre === resp.categoria)?.id || form.categoria_id
      toast.success(`Encontrado en ${resp.fuente || 'fuente externa'}`)
    } else {
      toast.info('Producto no encontrado en fuentes externas')
    }
  } catch {
    toast.info('Búsqueda sin resultados')
  }
  lookingUp.value = false
}

async function saveProduct() {
  formError.value = ''
  if (!form.nombre || !form.codigo_barras || !form.categoria_id) {
    formError.value = 'Completá los campos obligatorios'
    return
  }

  saving.value = true
  try {
    if (editingProduct.value) {
      try {
        await api.put(`/api/productos/${editingProduct.value.id}`, form)
      } catch { /* local fallback */ }

      const idx = products.value.findIndex(p => p.id === editingProduct.value.id)
      if (idx !== -1) {
        products.value[idx] = { ...products.value[idx], ...form }
      }
      toast.success('Producto actualizado')
    } else {
      let newId = 1
      try {
        const resp = await api.post('/api/productos', form)
        if (resp && resp.id) newId = resp.id
      } catch {
        newId = Math.max(...products.value.map(p => p.id), 0) + 1
      }

      products.value.push({ id: newId, ...form })
      toast.success('Producto creado')
    }
    closeModal()
  } catch (e) {
    formError.value = e.message || 'Error al guardar'
  }
  saving.value = false
}

function confirmDelete(product) {
  deleteTarget.value = product
}

async function executeDelete() {
  if (!deleteTarget.value) return

  deleting.value = true
  try {
    try {
      await api.delete(`/api/productos/${deleteTarget.value.id}`)
    } catch { /* local fallback */ }

    products.value = products.value.filter(p => p.id !== deleteTarget.value.id)
    toast.success('Producto eliminado')
  } catch {
    toast.error('Error al eliminar')
  }
  deleteTarget.value = null
  deleting.value = false
}
</script>

<template>
  <div class="space-y-5">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Productos</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gestión del catálogo</p>
      </div>
      <div class="flex items-center gap-3">
        <BaseButton variant="secondary" size="sm" :loading="syncing" @click="syncProducts">
          <i :class="syncing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
        <BaseButton variant="primary" size="sm" @click="openCreateModal">
          <i class="fa-solid fa-plus"></i> Nuevo Producto
        </BaseButton>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-col sm:flex-row gap-3">
      <BaseInput
        v-model="searchQuery"
        placeholder="Buscar por nombre, código o marca..."
        class="flex-1"
      >
        <template #prefix>
          <i class="fa-solid fa-magnifying-glass text-slate-400"></i>
        </template>
      </BaseInput>
      <BaseSelect
        v-model="filterCategory"
        :options="[{ value: null, label: 'Todas las categorías' }, ...categories.map(c => ({ value: c.id, label: c.nombre }))]"
        option-value="value"
        option-label="label"
        class="sm:w-56"
      />
    </div>

    <!-- Quick filter toggles -->
    <div class="flex flex-wrap gap-2">
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterStockBajo
          ? 'bg-red-600 text-white border-red-600 shadow-sm shadow-red-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterStockBajo = !filterStockBajo; filterPrecioDefasado = false"
      >
        <i class="fa-solid fa-triangle-exclamation"></i> Bajo stock
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterPrecioDefasado
          ? 'bg-amber-500 text-white border-amber-500 shadow-sm shadow-amber-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterPrecioDefasado = !filterPrecioDefasado; filterStockBajo = false"
      >
        <i class="fa-solid fa-dollar-sign"></i> Precio ≤ costo
      </button>
    </div>

    <!-- Products table -->
    <BaseTable
      :columns="tableColumns"
      :rows="tableRows"
      :loading="loading"
      :row-class="row => highlightedIds.has(row.id) ? 'bg-amber-100/40 dark:bg-amber-900/20' : ''"
      empty-title="No se encontraron productos"
      empty-text="Intentá con otros filtros o creá uno nuevo."
      empty-icon="fa-box-open"
    >
      <template #image="{ row }">
        <div class="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-400 dark:text-slate-500">
          <i class="fa-solid fa-box text-sm"></i>
        </div>
      </template>
      <template #nombre="{ row }">
        <p class="text-xs font-bold text-slate-900 dark:text-white truncate max-w-[180px]">{{ row.nombre }}</p>
      </template>
      <template #codigo_barras="{ row }">
        <span class="text-xs font-mono-data text-slate-500 dark:text-slate-400">{{ row.codigo_barras }}</span>
      </template>
      <template #marca="{ row }">
        <span class="text-xs text-slate-600 dark:text-slate-300">{{ row.marca || '\u2014' }}</span>
      </template>
      <template #precio_costo="{ row }">
        <span class="text-xs font-mono-data text-slate-600 dark:text-slate-300">{{ fc(row.precio_costo) }}</span>
      </template>
      <template #precio_venta="{ row }">
        <span class="text-xs font-mono-data font-bold text-brand-600 dark:text-brand-400">{{ fc(row.precio_venta) }}</span>
      </template>
      <template #stock_actual="{ row }">
        <BaseBadge
          :variant="row.stock_actual <= 5 ? 'danger' : 'default'"
          size="xs"
        >
          {{ row.stock_actual }}
        </BaseBadge>
      </template>
      <template #categoria="{ row }">
        <span class="text-xs text-slate-500 dark:text-slate-400">{{ row.categoria }}</span>
      </template>
      <template #acciones="{ row }">
        <div class="flex items-center justify-end gap-1">
          <button
            type="button"
            aria-label="Editar"
            class="w-7 h-7 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 flex items-center justify-center transition"
            @click="openEditModal(row)"
          >
            <i class="fa-solid fa-pen text-[10px]"></i>
          </button>
          <button
            type="button"
            aria-label="Eliminar"
            class="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex items-center justify-center transition"
            @click="confirmDelete(row)"
          >
            <i class="fa-solid fa-trash text-[10px]"></i>
          </button>
        </div>
      </template>
    </BaseTable>

    <div class="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
      {{ filteredProducts.length }} de {{ products.length }} productos
    </div>

    <!-- Create/Edit Modal -->
    <BaseModal v-model="showModal" :title="editingProduct ? 'Editar Producto' : 'Nuevo Producto'" size="lg">
      <form class="space-y-4" @submit.prevent="saveProduct">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <BaseInput
              v-model="form.codigo_barras"
              label="Código de Barras"
              placeholder="779..."
              input-class="font-mono-data"
              required
              @enter="lookupBarcode"
            />
            <p v-if="showBarcodeHint" class="text-[10px] text-brand-600 dark:text-brand-400 font-semibold mt-1.5 flex items-center gap-1">
              <i class="fa-solid fa-circle-info"></i> Código genérico. Si el producto tiene código real, reemplazalo acá.
            </p>
          </div>
          <BaseInput v-model="form.marca" label="Marca" placeholder="Marca" />
        </div>

        <BaseInput v-model="form.nombre" label="Nombre del Producto" placeholder="Nombre del producto" required />

        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <BaseInput
            v-model.number="form.precio_costo"
            label="Precio Costo"
            type="number"
            step="0.01"
            min="0"
            required
            input-class="font-mono-data text-right"
          />
          <BaseInput
            v-model.number="form.precio_venta"
            label="Precio Venta"
            type="number"
            step="0.01"
            min="0"
            required
            input-class="font-mono-data text-right"
          />
          <BaseInput
            v-model.number="form.stock_actual"
            label="Stock Actual"
            type="number"
            min="0"
            required
            input-class="font-mono-data text-right"
          />
        </div>

        <BaseSelect
          v-model="form.categoria_id"
          label="Categoría"
          :options="categories.map(c => ({ value: c.id, label: c.nombre }))"
          option-value="value"
          option-label="label"
          required
        />

        <div v-if="formError" class="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-300 rounded-xl border border-red-100 dark:border-red-800/50 text-xs font-medium flex items-center gap-2">
          <i class="fa-solid fa-triangle-exclamation"></i>{{ formError }}
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" @click="closeModal">Cancelar</BaseButton>
          <BaseButton variant="primary" type="submit" :loading="saving" class="flex-1">
            <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
            {{ saving ? 'Guardando...' : (editingProduct ? 'Actualizar' : 'Crear Producto') }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <!-- Delete confirmation modal -->
    <BaseModal v-model="deleteTarget" title="Eliminar Producto" size="sm" :close-on-overlay="true">
      <div class="text-center">
        <div class="w-12 h-12 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-3">
          <i class="fa-solid fa-triangle-exclamation text-red-500 text-xl"></i>
        </div>
        <h3 class="text-lg font-bold text-slate-950 dark:text-white font-display mb-1">Eliminar Producto</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
          ¿Estás seguro de eliminar <strong class="text-slate-900 dark:text-slate-100">{{ deleteTarget?.nombre }}</strong>? Esta acción no se puede deshacer.
        </p>
        <div class="flex items-center gap-3">
          <BaseButton variant="secondary" class="flex-1" @click="deleteTarget = null">Cancelar</BaseButton>
          <BaseButton variant="danger" :loading="deleting" class="flex-1" @click="executeDelete">
            <i :class="deleting ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-trash'"></i>
            {{ deleting ? 'Eliminando...' : 'Eliminar' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>


