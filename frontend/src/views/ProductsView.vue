<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Productos</h2>
        <p class="text-sm text-slate-500 mt-1">Gestión del catálogo</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          @click="syncProducts"
          :disabled="syncing"
          class="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl flex items-center gap-2 shadow-sm transition"
        >
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'" class="text-brand-500"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </button>
        <button
          @click="openCreateModal"
          class="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl flex items-center gap-2 shadow-sm transition"
        >
          <i class="fa-solid fa-plus"></i> Nuevo Producto
        </button>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-col sm:flex-row gap-3">
      <div class="relative flex-1">
        <i class="fa-solid fa-magnifying-glass absolute left-4 top-3.5 text-slate-400"></i>
        <input
          v-model="searchQuery"
          placeholder="Buscar por nombre, código o marca..."
          class="w-full bg-white border border-slate-200 rounded-xl pl-11 pr-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition shadow-sm"
        />
      </div>
      <select
        v-model="filterCategory"
        class="bg-white border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition shadow-sm"
      >
        <option :value="null">Todas las categorías</option>
        <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.nombre }}</option>
      </select>
    </div>

    <!-- Quick filter toggles -->
    <div class="flex gap-2">
      <button @click="filterStockBajo = !filterStockBajo; filterPrecioDefasado = false"
              :class="filterStockBajo ? 'bg-rose-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm">
        <i class="fa-solid fa-triangle-exclamation"></i> Bajo stock
      </button>
      <button @click="filterPrecioDefasado = !filterPrecioDefasado; filterStockBajo = false"
              :class="filterPrecioDefasado ? 'bg-amber-500 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:bg-slate-50'"
              class="px-3 py-1.5 rounded-lg text-xs font-semibold transition flex items-center gap-1.5 shadow-sm">
        <i class="fa-solid fa-dollar-sign"></i> Precio ≤ costo
      </button>
    </div>

    <!-- Products table -->
    <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 bg-slate-50 text-left">
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase w-14">Img</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase">Nombre</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase">Código</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase">Marca</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase text-right">Costo</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase text-right">Precio</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase text-right">Stock</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase">Categoría</th>
              <th class="px-4 py-3 text-[10px] font-bold text-slate-400 uppercase text-right w-24">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr
              v-for="p in filteredProducts"
              :key="p.id"
              :class="['hover:bg-slate-50 transition', highlightedIds.has(p.id) ? 'flash-highlight' : '']"
            >
              <td class="px-4 py-3">
                <div class="w-10 h-10 rounded-lg bg-slate-100 flex items-center justify-center text-slate-400">
                  <i class="fa-solid fa-box text-sm"></i>
                </div>
              </td>
              <td class="px-4 py-3">
                <p class="text-xs font-bold text-slate-900 truncate max-w-[180px]">{{ p.nombre }}</p>
              </td>
              <td class="px-4 py-3">
                <span class="text-xs font-mono-data text-slate-500">{{ p.codigo_barras }}</span>
              </td>
              <td class="px-4 py-3">
                <span class="text-xs text-slate-600">{{ p.marca || '\u2014' }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <span class="text-xs font-mono-data text-slate-600">{{ fc(p.precio_costo) }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <span class="text-xs font-mono-data font-bold text-brand-600">{{ fc(p.precio_venta) }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <span
                  :class="p.stock_actual <= 5 ? 'text-rose-600 bg-rose-50 px-2 py-0.5 rounded-full' : 'text-slate-600'"
                  class="text-xs font-mono-data font-bold"
                >{{ p.stock_actual }}</span>
              </td>
              <td class="px-4 py-3">
                <span class="text-xs text-slate-500">{{ categoryName(p.categoria_id) }}</span>
              </td>
              <td class="px-4 py-3 text-right">
                <div class="flex items-center justify-end gap-1">
                  <button
                    @click="openEditModal(p)"
                    class="w-7 h-7 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 flex items-center justify-center transition"
                  >
                    <i class="fa-solid fa-pen text-[10px]"></i>
                  </button>
                  <button
                    @click="confirmDelete(p)"
                    class="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 flex items-center justify-center transition"
                  >
                    <i class="fa-solid fa-trash text-[10px]"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty state -->
      <div v-if="!filteredProducts.length" class="p-12 text-center">
        <div class="w-16 h-16 rounded-2xl bg-slate-100 flex items-center justify-center mx-auto mb-3">
          <i class="fa-solid fa-box-open text-slate-300 text-2xl"></i>
        </div>
        <p class="text-sm text-slate-400 font-semibold">No se encontraron productos</p>
        <p class="text-xs text-slate-300 mt-1">Intentá con otros filtros o creá uno nuevo</p>
      </div>

      <!-- Footer -->
      <div class="px-4 py-2.5 border-t border-slate-100 bg-slate-50 flex items-center">
        <span class="text-[10px] text-slate-400 font-bold">{{ filteredProducts.length }} de {{ products.length }} productos</span>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
      <div
        v-if="showModal"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="closeModal"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <div class="p-5 border-b border-slate-100 flex items-center justify-between">
            <h3 class="text-lg font-bold text-slate-950 font-display">
              {{ editingProduct ? 'Editar Producto' : 'Nuevo Producto' }}
            </h3>
            <button
              @click="closeModal"
              class="w-8 h-8 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition"
            >
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>

          <form @submit.prevent="saveProduct" class="p-5 space-y-4">
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Código de Barras</label>
                <div class="flex gap-2">
                  <input
                    v-model="form.codigo_barras"
                    required
                    placeholder="779..."
                    @keydown.enter="lookupBarcode"
                    class="flex-1 bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
                  />
                  <button @click="lookupBarcode" :disabled="lookingUp" type="button"
                          class="px-3 py-2 bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 text-white rounded-xl text-xs font-semibold transition flex items-center gap-1">
                    <i :class="lookingUp ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-magnifying-glass'"></i>
                    {{ lookingUp ? '' : 'Buscar' }}
                  </button>
                </div>
              </div>
              <div>
                <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Marca</label>
                <input
                  v-model="form.marca"
                  placeholder="Marca"
                  class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
                />
              </div>
            </div>

            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Nombre del Producto <span class="text-rose-500">*</span></label>
              <input
                v-model="form.nombre"
                required
                placeholder="Nombre del producto"
                class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
              />
            </div>

            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Precio Costo</label>
                <input
                  v-model.number="form.precio_costo"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
                />
              </div>
              <div>
                <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Precio Venta <span class="text-rose-500">*</span></label>
                <input
                  v-model.number="form.precio_venta"
                  type="number"
                  step="0.01"
                  min="0"
                  required
                  class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
                />
              </div>
              <div>
                <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Stock Actual</label>
                <input
                  v-model.number="form.stock_actual"
                  type="number"
                  min="0"
                  required
                  class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm font-mono-data focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
                />
              </div>
            </div>

            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase block mb-1">Categoría</label>
              <select
                v-model="form.categoria_id"
                required
                class="w-full bg-slate-50 border border-slate-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 transition"
              >
                <option :value="null" disabled>Seleccionar categoría</option>
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">{{ cat.nombre }}</option>
              </select>
            </div>

            <!-- Error message -->
            <div v-if="formError" class="p-3 bg-rose-50 text-rose-600 rounded-xl border border-rose-100 text-xs font-medium">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>{{ formError }}
            </div>

            <div class="flex items-center gap-3 pt-2">
              <button
                type="button"
                @click="closeModal"
                class="flex-1 px-4 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition"
              >
                Cancelar
              </button>
              <button
                type="submit"
                :disabled="saving"
                class="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-sm transition flex items-center justify-center gap-2"
              >
                <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-floppy-disk'"></i>
                {{ saving ? 'Guardando...' : (editingProduct ? 'Actualizar' : 'Crear Producto') }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Delete confirmation modal -->
    <Teleport to="body">
      <div
        v-if="deleteTarget"
        class="fixed inset-0 z-50 flex items-center justify-center p-4"
      >
        <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="deleteTarget = null"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-sm p-6 text-center">
          <div class="w-12 h-12 rounded-2xl bg-rose-50 flex items-center justify-center mx-auto mb-3">
            <i class="fa-solid fa-triangle-exclamation text-rose-500 text-xl"></i>
          </div>
          <h3 class="text-lg font-bold text-slate-950 font-display mb-1">Eliminar Producto</h3>
          <p class="text-sm text-slate-500 mb-5">
            ¿Estás seguro de eliminar <strong>{{ deleteTarget.nombre }}</strong>? Esta acción no se puede deshacer.
          </p>
          <div class="flex items-center gap-3">
            <button
              @click="deleteTarget = null"
              class="flex-1 px-4 py-2.5 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition"
            >
              Cancelar
            </button>
            <button
              @click="executeDelete"
              :disabled="deleting"
              class="flex-1 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-semibold text-sm rounded-xl shadow-sm transition flex items-center justify-center gap-2"
            >
              <i :class="deleting ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-trash'"></i>
              {{ deleting ? 'Eliminando...' : 'Eliminar' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'

const auth = useAuthStore()
const toast = useToastStore()

const searchQuery = ref('')
const filterCategory = ref(null)
const filterStockBajo = ref(false)
const filterPrecioDefasado = ref(false)
const syncing = ref(false)
const saving = ref(false)
const deleting = ref(false)
const lookingUp = ref(false)

const showModal = ref(false)
const editingProduct = ref(null)
const deleteTarget = ref(null)
const formError = ref('')
const highlightedIds = ref(new Set())

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

function categoryName(catId) {
  const cat = categories.value.find(c => c.id === catId)
  return cat ? cat.nombre : '\u2014'
}

onMounted(async () => {
  try {
    const [prods, cats] = await Promise.all([
      api.get('/api/productos?page_size=200').catch(() => null),
      api.get('/api/categorias').catch(() => null)
    ])
    if (prods && prods.length) products.value = prods
    if (cats && cats.length) categories.value = cats

    const pendientes = prods?.filter(p =>
      (p.codigo_barras && p.codigo_barras.startsWith('*MANUAL*')) ||
      (p.fuente === 'manual' && p.stock_actual === 0 && !p.precio_costo)
    ) || []
    if (pendientes.length) {
      highlightedIds.value = new Set(pendientes.map(p => p.id))
      setTimeout(() => { highlightedIds.value = new Set() }, 3000)
    }
  } catch { /* fallback to mock */ }
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
    toast.add('success', 'Productos sincronizados')
  } catch {
    toast.add('info', 'Usando datos locales')
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
  Object.assign(form, {
    codigo_barras: product.codigo_barras,
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
      toast.add('success', `Encontrado en ${resp.fuente || 'fuente externa'}`)
    } else {
      toast.add('info', 'Producto no encontrado en fuentes externas')
    }
  } catch {
    toast.add('info', 'Búsqueda sin resultados')
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
      toast.add('success', 'Producto actualizado')
    } else {
      let newId = 1
      try {
        const resp = await api.post('/api/productos', form)
        if (resp && resp.id) newId = resp.id
      } catch {
        newId = Math.max(...products.value.map(p => p.id), 0) + 1
      }

      products.value.push({ id: newId, ...form })
      toast.add('success', 'Producto creado')
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
    toast.add('success', 'Producto eliminado')
  } catch {
    toast.add('error', 'Error al eliminar')
  }
  deleteTarget.value = null
  deleting.value = false
}
</script>

<style scoped>
.flash-highlight {
  animation: flashPulse 2s ease-in-out 3;
  background: #fef3c7 !important;
}
@keyframes flashPulse {
  0%, 100% { background: #fef3c7; }
  50% { background: #fde68a; }
}
</style>
