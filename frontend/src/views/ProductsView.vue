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
import ProductoProveedoresManager from '@/components/products/ProductoProveedoresManager.vue'
import ProductoLotesManager from '@/components/products/ProductoLotesManager.vue'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()

const searchInput = ref('')
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

const ofertas = ref([])
const showOfertaModal = ref(false)
const editingOferta = ref(null)
const deleteOfertaTarget = ref(null)
const savingOferta = ref(false)
const deletingOferta = ref(false)
const filterEnOferta = ref(false)
const filterSinStock = ref(false)
const filterSinCodigo = ref(false)
const filterPendientes = ref(false)

let searchDebounceTimer = null
function onSearchInput() {
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
  searchDebounceTimer = setTimeout(() => {
    searchQuery.value = searchInput.value
  }, 200)
}

function clearSearch() {
  searchInput.value = ''
  searchQuery.value = ''
  if (searchDebounceTimer) clearTimeout(searchDebounceTimer)
}

const activeFilterCount = computed(() => {
  let n = 0
  if (filterCategory.value) n++
  if (filterStockBajo.value) n++
  if (filterPrecioDefasado.value) n++
  if (filterEnOferta.value) n++
  if (filterSinStock.value) n++
  if (filterSinCodigo.value) n++
  if (filterPendientes.value) n++
  return n
})

const hasSearch = computed(() => searchQuery.value.trim().length > 0)

function clearAllFilters() {
  filterCategory.value = null
  filterStockBajo.value = false
  filterPrecioDefasado.value = false
  filterEnOferta.value = false
  filterSinStock.value = false
  filterSinCodigo.value = false
  filterPendientes.value = false
  clearSearch()
}

const countStockBajo = computed(() => {
  try {
    return products.value.filter(p => p && Number(p.stock_actual) <= Number(p.stock_minimo || 5) && Number(p.stock_actual) >= 0).length
  } catch { return 0 }
})

const countPrecioDefasado = computed(() => {
  try {
    return products.value.filter(p => p && Number(p.precio_venta) > 0 && Number(p.precio_costo) > 0 && Number(p.precio_venta) <= Number(p.precio_costo)).length
  } catch { return 0 }
})

const countEnOferta = computed(() => {
  try {
    const ofertasActivas = Array.isArray(ofertas.value) ? ofertas.value.filter(o => o && o.activo) : []
    const pids = new Set(ofertasActivas.map(o => o.producto_id))
    return products.value.filter(p => p && pids.has(p.id)).length
  } catch { return 0 }
})

const countSinStock = computed(() => {
  try {
    return products.value.filter(p => p && Number(p.stock_actual) === 0).length
  } catch { return 0 }
})

const countSinCodigo = computed(() => {
  try {
    return products.value.filter(p => {
      if (!p) return false
      const cb = p.codigo_barras
      if (!cb || String(cb).trim() === '') return true
      const cbs = String(cb).toLowerCase()
      return cbs.startsWith('gen-') || cbs.startsWith('*manual*')
    }).length
  } catch { return 0 }
})

const countPendientes = computed(() => {
  try {
    return products.value.filter(p => {
      if (!p || !p.codigo_barras) return false
      const cbs = String(p.codigo_barras).toLowerCase()
      return cbs.startsWith('gen-') || cbs.startsWith('*manual*')
    }).length
  } catch { return 0 }
})

const showCatQuick = ref(false)
const newCatNombre = ref('')
const showProvQuick = ref(false)
const newProvNombre = ref('')
const newProvCuit = ref('')

const defaultOfertaForm = () => ({
  producto_id: null,
  tipo: 'porcentaje',
  valor: 10,
  requiere_cantidad: 2,
  fecha_inicio: null,
  fecha_fin: null,
  max_unidades: null,
  descripcion: ''
})
const ofertaForm = reactive(defaultOfertaForm())

const products = ref([
  { id: 1, codigo_barras: '7791234567890', nombre: 'Coca-Cola 2.25L', marca: 'Coca-Cola', precio_venta: 2800, precio_costo: 2100, categoria_id: 1, stock_actual: 45 },
  { id: 2, codigo_barras: '7799876543210', nombre: 'Arroz Gallo 1kg', marca: 'Gallo', precio_venta: 1500, precio_costo: 1100, categoria_id: 2, stock_actual: 120 },
  { id: 3, codigo_barras: '7794561237890', nombre: 'Agua Mineral 1.5L', marca: 'Villa del Sur', precio_venta: 950, precio_costo: 600, categoria_id: 1, stock_actual: 80 }
])

const categories = ref([
  { id: 1, nombre: 'Bebidas' },
  { id: 2, nombre: 'Almacén' }
])

const proveedores = ref([])

const defaultForm = () => ({
  codigo_barras: '',
  nombre: '',
  marca: '',
  precio_venta: 0,
  precio_costo: 0,
  categoria_id: null,
  stock_actual: 0,
  stock_minimo: 0,
  fecha_vencimiento: null,
  proveedor_id: null,
  observaciones: '',
  tipo_venta: 'unidad',
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
  { key: 'oferta', label: 'Oferta', align: 'center', width: 'w-24' },
  { key: 'acciones', label: '', align: 'right', width: 'w-24' }
]

const filteredProducts = computed(() => {
  try {
    let list = Array.isArray(products.value) ? products.value : []

    const safeStr = v => {
      if (v == null) return ''
      const s = String(v).toLowerCase()
      return s === 'null' || s === 'undefined' ? '' : s
    }

    if (filterCategory.value) {
      list = list.filter(p => p && p.categoria_id === filterCategory.value)
    }
    if (filterStockBajo.value) {
      list = list.filter(p => p && Number(p.stock_actual) <= Number(p.stock_minimo || 5) && Number(p.stock_actual) >= 0)
    }
    if (filterPrecioDefasado.value) {
      list = list.filter(p => p && Number(p.precio_venta) > 0 && Number(p.precio_costo) > 0 && Number(p.precio_venta) <= Number(p.precio_costo))
    }
    if (filterEnOferta.value) {
      const ofertasActivas = Array.isArray(ofertas.value) ? ofertas.value.filter(o => o && o.activo) : []
      const pids = new Set(ofertasActivas.map(o => o.producto_id))
      list = list.filter(p => p && pids.has(p.id))
    }
    if (filterSinStock.value) {
      list = list.filter(p => p && Number(p.stock_actual) === 0)
    }
    if (filterSinCodigo.value) {
      list = list.filter(p => {
        if (!p) return false
        const cb = p.codigo_barras
        return !cb || String(cb).trim() === '' || safeStr(cb).startsWith('gen-') || safeStr(cb).startsWith('*manual*')
      })
    }
    if (filterPendientes.value) {
      list = list.filter(p => {
        if (!p) return false
        const cb = p.codigo_barras
        if (!cb) return false
        const cbs = safeStr(cb)
        return cbs.startsWith('gen-') || cbs.startsWith('*manual*')
      })
    }
    if (hasSearch.value) {
      const q = safeStr(searchQuery.value).trim()
      if (q) {
        list = list.filter(p => {
          if (!p) return false
          return safeStr(p.nombre).includes(q)
              || safeStr(p.marca).includes(q)
              || safeStr(p.codigo_barras).includes(q)
              || safeStr(p.categoria_nombre).includes(q)
              || safeStr(p.observaciones).includes(q)
        })
      }
    }
    return list
  } catch (err) {
    console.error('[ProductsView] Error en filteredProducts, fallback a lista completa:', err)
    return Array.isArray(products.value) ? products.value : []
  }
})

const tableRows = computed(() => {
  try {
    return filteredProducts.value.map(p => {
      const oferta = ofertas.value.find(o => o && o.producto_id === p.id && o.activo)
      return { ...p, categoria: categoryName(p.categoria_id), _oferta: oferta || null }
    })
  } catch (err) {
    console.error('[ProductsView] Error en tableRows, fallback a filteredProducts:', err)
    return filteredProducts.value
  }
})

function categoryName(catId) {
  const cat = categories.value.find(c => c.id === catId)
  return cat ? cat.nombre : '\u2014'
}

async function fetchProductsData(checkPendientes = false) {
  loading.value = true
  try {
    const [prods, cats, ofs] = await Promise.all([
      api.get('/api/productos?page_size=200').catch(err => { console.error('[ProductsView] GET /productos:', err); return null }),
      api.get('/api/categorias').catch(err => { console.error('[ProductsView] GET /categorias:', err); return null }),
      api.get('/api/ofertas?page_size=200').catch(err => { console.error('[ProductsView] GET /ofertas:', err); return null })
    ])
    if (Array.isArray(prods) && prods.length) products.value = prods
    if (Array.isArray(cats) && cats.length) categories.value = cats
    if (Array.isArray(ofs)) ofertas.value = ofs

    if (checkPendientes && Array.isArray(prods)) {
      const pendientes = prods.filter(p =>
        (p.codigo_barras && (p.codigo_barras.startsWith('*MANUAL*') || p.codigo_barras.startsWith('GEN-'))) ||
        (p.fuente === 'manual' && p.stock_actual === 0 && !p.precio_costo)
      )
      if (pendientes.length) {
        highlightedIds.value = new Set(pendientes.map(p => p.id))
        setTimeout(() => { highlightedIds.value = new Set() }, 3000)
      }
    }
  } catch (err) {
    console.error('[ProductsView] fetchProductsData error:', err)
  } finally {
    loading.value = false
  }
}

onMounted(() => { fetchProductsData(true); fetchProveedores() })
watch(() => route.path, (path) => {
  if (path === '/products') fetchProductsData()
})

async function syncProducts() {
  syncing.value = true
  try {
    const [prods, cats, ofs] = await Promise.all([
      api.get('/api/productos').catch(err => { console.error('[ProductsView] GET /productos:', err); return null }),
      api.get('/api/categorias').catch(err => { console.error('[ProductsView] GET /categorias:', err); return null }),
      api.get('/api/ofertas?page_size=200').catch(err => { console.error('[ProductsView] GET /ofertas:', err); return null })
    ])
    if (Array.isArray(prods) && prods.length) products.value = prods
    if (Array.isArray(cats) && cats.length) categories.value = cats
    if (Array.isArray(ofs)) ofertas.value = ofs
    toast.success('Productos sincronizados')
  } catch (err) {
    console.error('[ProductsView] syncProducts error:', err)
    toast.info('Usando datos locales')
  } finally {
    syncing.value = false
  }
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
    precio_venta: product.tipo_venta === 'kilo' ? (product.precio_por_kilo || product.precio_venta) : product.precio_venta,
    precio_costo: product.precio_costo,
    categoria_id: product.categoria_id,
    stock_actual: product.stock_actual,
    stock_minimo: product.stock_minimo || 0,
    fecha_vencimiento: product.fecha_vencimiento ? product.fecha_vencimiento.slice(0, 10) : null,
    proveedor_id: product.proveedor_id || null,
    observaciones: product.observaciones || '',
    tipo_venta: product.tipo_venta || 'unidad',
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
  if (!form.nombre || !form.categoria_id) {
    formError.value = 'Completá los campos obligatorios'
    return
  }

  saving.value = true
  try {
    const payload = { ...form }
    if (form.tipo_venta === 'kilo') {
      payload.precio_por_kilo = form.precio_venta
      payload.precio_venta = null
    }
    let productoId = null
    if (editingProduct.value) {
      const resp = await api.put(`/api/productos/${editingProduct.value.id}`, payload)
      productoId = editingProduct.value.id

      const idx = products.value.findIndex(p => p.id === editingProduct.value.id)
      if (idx !== -1) {
        products.value[idx] = { ...products.value[idx], ...resp }
      }
      toast.success('Producto actualizado')
    } else {
      const resp = await api.post('/api/productos', payload)
      productoId = resp.id
      products.value.push({ id: resp.id, ...payload })
      toast.success('Producto creado')
    }

    const oldProveedorId = editingProduct.value?.proveedor_id || null
    if (productoId && form.proveedor_id !== oldProveedorId) {
      try {
        if (form.proveedor_id) {
          await api.post(`/api/productos/${productoId}/proveedores`, { proveedor_id: form.proveedor_id })
        }
      } catch (e) {
        toast.error('Producto guardado, pero no se pudo asociar el proveedor: ' + (e.message || 'error desconocido'))
      }
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

function openCreateOfertaModal(productoId = null) {
  editingOferta.value = null
  Object.assign(ofertaForm, defaultOfertaForm())
  if (productoId) ofertaForm.producto_id = productoId
  showOfertaModal.value = true
}

function openEditOfertaModal(oferta) {
  editingOferta.value = oferta
  Object.assign(ofertaForm, {
    producto_id: oferta.producto_id,
    tipo: oferta.tipo,
    valor: oferta.valor,
    requiere_cantidad: oferta.requiere_cantidad,
    fecha_inicio: oferta.fecha_inicio ? oferta.fecha_inicio.slice(0, 16) : null,
    fecha_fin: oferta.fecha_fin ? oferta.fecha_fin.slice(0, 16) : null,
    max_unidades: oferta.max_unidades,
    descripcion: oferta.descripcion || ''
  })
  showOfertaModal.value = true
}

function closeOfertaModal() {
  showOfertaModal.value = false
  editingOferta.value = null
}

async function saveOferta() {
  if (!ofertaForm.producto_id) {
    toast.error('Seleccioná un producto')
    return
  }
  savingOferta.value = true
  try {
    const payload = {
      ...ofertaForm,
      fecha_inicio: ofertaForm.fecha_inicio || null,
      fecha_fin: ofertaForm.fecha_fin || null,
      max_unidades: ofertaForm.max_unidades || null
    }
    if (editingOferta.value) {
      await api.put(`/api/ofertas/${editingOferta.value.id}`, payload)
      toast.success('Oferta actualizada')
    } else {
      await api.post('/api/ofertas', payload)
      toast.success('Oferta creada')
    }
    closeOfertaModal()
    const ofs = await api.get('/api/ofertas?page_size=200').catch(() => null)
    if (ofs && Array.isArray(ofs)) ofertas.value = ofs
  } catch (e) {
    toast.error(e.message || 'Error al guardar oferta')
  }
  savingOferta.value = false
}

function confirmDeleteOferta(oferta) {
  deleteOfertaTarget.value = oferta
}

async function executeDeleteOferta() {
  if (!deleteOfertaTarget.value) return
  deletingOferta.value = true
  try {
    await api.delete(`/api/ofertas/${deleteOfertaTarget.value.id}`)
    toast.success('Oferta eliminada')
    ofertas.value = ofertas.value.filter(o => o.id !== deleteOfertaTarget.value.id)
  } catch {
    toast.error('Error al eliminar oferta')
  }
  deleteOfertaTarget.value = null
  deletingOferta.value = false
}

function ofertaTipoLabel(tipo) {
  return { '2x1': '2x1', porcentaje: '%', monto_fijo: '$' }[tipo] || tipo
}

function ofertaTipoColor(tipo) {
  return { '2x1': 'warning', porcentaje: 'success', monto_fijo: 'info' }[tipo] || 'default'
}

async function quickCreateCategoria() {
  const nombre = newCatNombre.value.trim()
  if (!nombre) return
  try {
    const resp = await api.post('/api/categorias', { nombre })
    if (resp && resp.id) {
      categories.value.push({ id: resp.id, nombre: resp.nombre })
      form.categoria_id = resp.id
      toast.success(`Categoría "${nombre}" creada`)
    }
  } catch (e) {
    toast.error(e.message || 'Error al crear categoría')
  }
  newCatNombre.value = ''
  showCatQuick.value = false
}

async function quickCreateProveedor() {
  const nombre = newProvNombre.value.trim()
  if (!nombre) return
  try {
    const resp = await api.post('/api/proveedores', { nombre, cuit: newProvCuit.value || undefined })
    if (resp && resp.id) {
      proveedores.value.push({ id: resp.id, nombre: resp.nombre })
      form.proveedor_id = resp.id
      toast.success(`Proveedor "${nombre}" creado`)
    }
  } catch (e) {
    toast.error(e.message || 'Error al crear proveedor')
  }
  newProvNombre.value = ''
  newProvCuit.value = ''
  showProvQuick.value = false
}

async function fetchProveedores() {
  try {
    const data = await api.get('/api/proveedores')
    if (data && data.length) proveedores.value = data
  } catch { /* fallback to mock */ }
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
        <BaseButton variant="secondary" size="sm" @click="openCreateOfertaModal()">
          <i class="fa-solid fa-tag"></i> Nueva Oferta
        </BaseButton>
      </div>
    </div>

    <!-- Filters -->
    <div class="flex flex-col sm:flex-row gap-3">
      <div class="relative flex-1">
        <BaseInput
          v-model="searchInput"
          placeholder="Buscar por nombre, código, marca, categoría u observaciones..."
          input-class="pl-10"
          @input="onSearchInput"
        >
          <template #prefix>
            <i class="fa-solid fa-magnifying-glass text-slate-400"></i>
          </template>
        </BaseInput>
        <button
          v-if="searchInput"
          type="button"
          aria-label="Limpiar búsqueda"
          class="absolute right-3 top-1/2 -translate-y-1/2 w-6 h-6 rounded-full flex items-center justify-center text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          @click="clearSearch"
        >
          <i class="fa-solid fa-xmark text-[10px]"></i>
        </button>
      </div>
      <BaseSelect
        v-model="filterCategory"
        :options="[{ value: null, label: 'Todas las categorías' }, ...categories.map(c => ({ value: c.id, label: c.nombre }))]"
        option-value="value"
        option-label="label"
        class="sm:w-56"
      />
    </div>

    <!-- Quick filter toggles -->
    <div class="flex flex-wrap items-center gap-2">
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterStockBajo
          ? 'bg-red-600 text-white border-red-600 shadow-sm shadow-red-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterStockBajo = !filterStockBajo"
      >
        <i class="fa-solid fa-triangle-exclamation"></i> Bajo stock
        <span
          v-if="countStockBajo > 0"
          class="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full"
          :class="filterStockBajo ? 'bg-white/20 text-white' : 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300'"
        >{{ countStockBajo }}</span>
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterPrecioDefasado
          ? 'bg-amber-500 text-white border-amber-500 shadow-sm shadow-amber-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterPrecioDefasado = !filterPrecioDefasado"
      >
        <i class="fa-solid fa-dollar-sign"></i> Precio ≤ costo
        <span
          v-if="countPrecioDefasado > 0"
          class="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full"
          :class="filterPrecioDefasado ? 'bg-white/20 text-white' : 'bg-amber-100 text-amber-600 dark:bg-amber-900/40 dark:text-amber-300'"
        >{{ countPrecioDefasado }}</span>
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterEnOferta
          ? 'bg-orange-500 text-white border-orange-500 shadow-sm shadow-orange-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterEnOferta = !filterEnOferta"
      >
        <i class="fa-solid fa-tag"></i> En oferta
        <span
          v-if="countEnOferta > 0"
          class="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full"
          :class="filterEnOferta ? 'bg-white/20 text-white' : 'bg-orange-100 text-orange-600 dark:bg-orange-900/40 dark:text-orange-300'"
        >{{ countEnOferta }}</span>
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterSinStock
          ? 'bg-slate-700 text-white border-slate-700 shadow-sm shadow-slate-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterSinStock = !filterSinStock"
      >
        <i class="fa-solid fa-circle-xmark"></i> Sin stock
        <span
          v-if="countSinStock > 0"
          class="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full"
          :class="filterSinStock ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'"
        >{{ countSinStock }}</span>
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterSinCodigo
          ? 'bg-slate-700 text-white border-slate-700 shadow-sm shadow-slate-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterSinCodigo = !filterSinCodigo"
      >
        <i class="fa-solid fa-barcode"></i> Sin código
        <span
          v-if="countSinCodigo > 0"
          class="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full"
          :class="filterSinCodigo ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200'"
        >{{ countSinCodigo }}</span>
      </button>
      <button
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border flex items-center gap-1.5"
        :class="filterPendientes
          ? 'bg-blue-600 text-white border-blue-600 shadow-sm shadow-blue-500/20'
          : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
        @click="filterPendientes = !filterPendientes"
      >
        <i class="fa-solid fa-clock"></i> Pendientes
        <span
          v-if="countPendientes > 0"
          class="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full"
          :class="filterPendientes ? 'bg-white/20 text-white' : 'bg-blue-100 text-blue-600 dark:bg-blue-900/40 dark:text-blue-300'"
        >{{ countPendientes }}</span>
      </button>

      <button
        v-if="activeFilterCount > 0 || hasSearch"
        type="button"
        class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 flex items-center gap-1.5 text-slate-500 dark:text-slate-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 ml-auto"
        title="Limpiar todos los filtros"
        @click="clearAllFilters"
      >
        <i class="fa-solid fa-filter-circle-xmark"></i>
        Limpiar filtros
        <span class="ml-1 px-1.5 py-0.5 text-[10px] font-bold rounded-full bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-300">
          {{ activeFilterCount + (hasSearch ? 1 : 0) }}
        </span>
      </button>
    </div>

    <!-- Products table -->
    <BaseTable
      :columns="tableColumns"
      :rows="tableRows"
      :loading="loading"
      :row-class="row => highlightedIds.has(row.id) ? 'bg-amber-100/40 dark:bg-amber-900/20' : ''"
      empty-title="No se encontraron productos"
      empty-text="Probá limpiar los filtros o ajustá la búsqueda."
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
        <span class="text-xs font-mono-data font-bold text-brand-600 dark:text-brand-400">
          {{ fc(row.tipo_venta === 'kilo' ? row.precio_por_kilo : row.precio_venta) }}
          <span v-if="row.tipo_venta === 'kilo'" class="text-[9px] text-amber-500">/kg</span>
        </span>
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
      <template #oferta="{ row }">
        <div v-if="row._oferta" class="flex items-center justify-center gap-1">
          <BaseBadge :variant="ofertaTipoColor(row._oferta.tipo)" size="xs">
            {{ row._oferta.tipo === '2x1' ? '2x1' : row._oferta.tipo === 'porcentaje' ? row._oferta.valor + '%' : '$' + row._oferta.valor }}
          </BaseBadge>
        </div>
        <span v-else class="text-slate-300 dark:text-slate-600 text-xs">—</span>
      </template>
      <template #acciones="{ row }">
        <div class="flex items-center justify-end gap-1">
          <button
            v-if="row._oferta"
            type="button"
            aria-label="Editar oferta"
            class="w-7 h-7 rounded-lg text-orange-400 hover:text-orange-600 hover:bg-orange-50 dark:hover:bg-orange-900/20 flex items-center justify-center transition"
            @click="openEditOfertaModal(row._oferta)"
          >
            <i class="fa-solid fa-tag text-[10px]"></i>
          </button>
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

    <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 font-medium px-1 pt-1">
      <div class="flex items-center gap-3">
        <span>
          <span class="font-bold text-slate-900 dark:text-white">{{ filteredProducts.length }}</span>
          de <span class="font-semibold">{{ products.length }}</span> producto{{ products.length !== 1 ? 's' : '' }}
        </span>
        <span
          v-if="activeFilterCount > 0 || hasSearch"
          class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-brand-50 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-[10px] font-semibold"
        >
          <i class="fa-solid fa-filter text-[9px]"></i>
          {{ activeFilterCount + (hasSearch ? 1 : 0) }} filtro{{ (activeFilterCount + (hasSearch ? 1 : 0)) !== 1 ? 's' : '' }} activo{{ (activeFilterCount + (hasSearch ? 1 : 0)) !== 1 ? 's' : '' }}
        </span>
      </div>
      <button
        v-if="activeFilterCount > 0 || hasSearch"
        type="button"
        class="text-brand-600 dark:text-brand-400 hover:underline flex items-center gap-1 transition"
        @click="clearAllFilters"
      >
        <i class="fa-solid fa-filter-circle-xmark"></i>
        Limpiar
      </button>
    </div>

    <!-- Create/Edit Modal -->
    <BaseModal v-model="showModal" :title="editingProduct ? 'Editar Producto' : 'Nuevo Producto'" size="lg">
      <form class="space-y-4" @submit.prevent="saveProduct">
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <div class="flex gap-2">
              <BaseInput
                v-model="form.codigo_barras"
                label="Código de Barras"
                placeholder="779..."
                input-class="font-mono-data"
                required
                :disabled="lookingUp"
                :loading="lookingUp"
                @enter="lookupBarcode"
              />
              <BaseButton
                type="button"
                variant="secondary"
                size="md"
                class="self-end mb-1 shrink-0"
                :disabled="lookingUp"
                title="Buscar en fuentes externas"
                @click="lookupBarcode"
              >
                <i class="fa-solid fa-magnifying-glass"></i>
              </BaseButton>
            </div>
            <p v-if="showBarcodeHint" class="text-[10px] text-brand-600 dark:text-brand-400 font-semibold mt-1.5 flex items-center gap-1">
              <i class="fa-solid fa-circle-info"></i> Código genérico. Si el producto tiene código real, reemplazalo acá.
            </p>
          </div>
          <BaseInput v-model="form.marca" label="Marca" placeholder="Marca" />
        </div>

        <BaseInput v-model="form.nombre" label="Nombre del Producto" placeholder="Nombre del producto" required />

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
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
            :label="form.tipo_venta === 'kilo' ? 'Precio por kg' : 'Precio Venta'"
            type="number"
            step="0.01"
            min="0"
            required
            input-class="font-mono-data text-right"
          />
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <BaseInput
            v-model.number="form.stock_actual"
            label="Stock Inicial"
            type="number"
            min="0"
            required
            input-class="font-mono-data text-right"
          />
          <BaseInput
            v-model.number="form.stock_minimo"
            label="Stock Mínimo"
            type="number"
            min="0"
            input-class="font-mono-data text-right"
          >
            <template #hint>
              <span class="text-[10px] text-slate-400">0 = sin alerta de bajo stock</span>
            </template>
          </BaseInput>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="flex items-end gap-2">
            <div class="flex-1">
              <BaseSelect
                v-model="form.categoria_id"
                label="Categoría"
                :options="categories.map(c => ({ value: c.id, label: c.nombre }))"
                option-value="value"
                option-label="label"
                required
              />
            </div>
            <BaseButton variant="ghost" size="sm" aria-label="Nueva categoría" class="shrink-0 mb-0.5" @click="showCatQuick = true">
              <i class="fa-solid fa-plus"></i>
            </BaseButton>
          </div>
          <div v-if="!editingProduct" class="flex items-end gap-2">
            <div class="flex-1">
              <label class="block text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Proveedor</label>
              <select
                v-model="form.proveedor_id"
                class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              >
                <option :value="null">Sin proveedor</option>
                <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </select>
            </div>
            <BaseButton variant="ghost" size="sm" aria-label="Nuevo proveedor" class="shrink-0 mb-0.5" @click="showProvQuick = true">
              <i class="fa-solid fa-plus"></i>
            </BaseButton>
          </div>
        </div>

        <ProductoProveedoresManager
          v-if="editingProduct"
          :producto-id="editingProduct.id"
          :proveedores="proveedores"
        />

        <ProductoLotesManager
          v-if="editingProduct"
          :producto-id="editingProduct.id"
        />

        <BaseInput
          v-model="form.fecha_vencimiento"
          label="Fecha de Vencimiento (opcional)"
          type="date"
        />

        <BaseInput
          v-model="form.observaciones"
          label="Observaciones (opcional)"
          placeholder="Notas internas sobre este producto..."
        />

        <!-- Tipo de venta -->
        <div>
          <label class="block text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-1">Tipo de Venta</label>
          <select
            v-model="form.tipo_venta"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
          >
            <option value="unidad">Por Unidad</option>
            <option value="kilo">Por Kilo</option>
          </select>
        </div>

        <!-- Quick-create Categoria -->
        <div v-if="showCatQuick" class="p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800/40 rounded-xl flex items-center gap-2">
          <BaseInput v-model="newCatNombre" placeholder="Nombre de la categoría" size="sm" class="flex-1" @enter="quickCreateCategoria" />
          <BaseButton variant="primary" size="xs" @click="quickCreateCategoria">Crear</BaseButton>
          <BaseButton variant="ghost" size="xs" @click="showCatQuick = false"><i class="fa-solid fa-xmark"></i></BaseButton>
        </div>

        <!-- Quick-create Proveedor -->
        <div v-if="showProvQuick" class="p-3 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800/40 rounded-xl space-y-2">
          <BaseInput v-model="newProvNombre" placeholder="Nombre del proveedor" size="sm" />
          <BaseInput v-model="newProvCuit" placeholder="CUIT (opcional)" size="sm" />
          <div class="flex items-center gap-2">
            <BaseButton variant="primary" size="xs" @click="quickCreateProveedor">Crear Proveedor</BaseButton>
            <BaseButton variant="ghost" size="xs" @click="showProvQuick = false"><i class="fa-solid fa-xmark"></i></BaseButton>
          </div>
        </div>

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

    <!-- Oferta Modal -->
    <BaseModal v-model="showOfertaModal" :title="editingOferta ? 'Editar Oferta' : 'Nueva Oferta'" size="md">
      <form class="space-y-4" @submit.prevent="saveOferta">
        <BaseSelect
          v-model="ofertaForm.producto_id"
          label="Producto"
          :options="products.map(p => ({ value: p.id, label: p.nombre }))"
          option-value="value"
          option-label="label"
          required
        />

        <BaseSelect
          v-model="ofertaForm.tipo"
          label="Tipo de Oferta"
          :options="[
            { value: 'porcentaje', label: 'Porcentaje (%)' },
            { value: 'monto_fijo', label: 'Monto Fijo ($)' },
            { value: '2x1', label: '2x1 (Llevá 2, Pagá 1)' }
          ]"
          option-value="value"
          option-label="label"
          required
        />

        <div v-if="ofertaForm.tipo !== '2x1'" class="grid grid-cols-2 gap-4">
          <BaseInput
            v-model.number="ofertaForm.valor"
            :label="ofertaForm.tipo === 'porcentaje' ? 'Porcentaje (%)' : 'Monto ($)'"
            type="number"
            step="0.01"
            min="0"
            required
            input-class="font-mono-data text-right"
          />
          <BaseInput
            v-model.number="ofertaForm.requiere_cantidad"
            label="Cantidad Mínima"
            type="number"
            min="1"
            required
            input-class="font-mono-data text-right"
          />
        </div>

        <div v-else class="grid grid-cols-2 gap-4">
          <BaseInput
            v-model.number="ofertaForm.requiere_cantidad"
            label="Cantidad Mínima"
            type="number"
            min="2"
            required
            input-class="font-mono-data text-right"
            placeholder="2"
          />
          <div class="flex items-end">
            <p class="text-xs text-slate-500 dark:text-slate-400">2x1: 50% de descuento automático al llevar 2+ unidades</p>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <BaseInput
            v-model="ofertaForm.fecha_inicio"
            label="Fecha Inicio"
            type="datetime-local"
          />
          <BaseInput
            v-model="ofertaForm.fecha_fin"
            label="Fecha Fin (opcional)"
            type="datetime-local"
          />
        </div>

        <BaseInput
          v-model.number="ofertaForm.max_unidades"
          label="Máx. Unidades en Oferta (opcional)"
          type="number"
          min="1"
          input-class="font-mono-data text-right"
        />

        <BaseInput
          v-model="ofertaForm.descripcion"
          label="Descripción (opcional)"
          placeholder="Ej: Liquidación de stock, Promoción especial..."
        />

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" @click="closeOfertaModal">Cancelar</BaseButton>
          <BaseButton variant="primary" type="submit" :loading="savingOferta" class="flex-1">
            <i :class="savingOferta ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-tag'"></i>
            {{ savingOferta ? 'Guardando...' : (editingOferta ? 'Actualizar' : 'Crear Oferta') }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <!-- Delete Oferta Modal -->
    <BaseModal v-model="deleteOfertaTarget" title="Eliminar Oferta" size="sm" :close-on-overlay="true">
      <div class="text-center">
        <div class="w-12 h-12 rounded-2xl bg-orange-50 dark:bg-orange-900/20 flex items-center justify-center mx-auto mb-3">
          <i class="fa-solid fa-tag text-orange-500 text-xl"></i>
        </div>
        <h3 class="text-lg font-bold text-slate-950 dark:text-white font-display mb-1">Eliminar Oferta</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
          ¿Estás seguro de eliminar esta oferta? Esta acción no se puede deshacer.
        </p>
        <div class="flex items-center gap-3">
          <BaseButton variant="secondary" class="flex-1" @click="deleteOfertaTarget = null">Cancelar</BaseButton>
          <BaseButton variant="danger" :loading="deletingOferta" class="flex-1" @click="executeDeleteOferta">
            <i :class="deletingOferta ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-trash'"></i>
            {{ deletingOferta ? 'Eliminando...' : 'Eliminar' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>


