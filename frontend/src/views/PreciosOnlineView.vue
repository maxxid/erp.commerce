<script setup>
import { ref, computed } from 'vue'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const toast = useToastStore()

const barcodeInput = ref('')
const loading = ref(false)
const resultados = ref([])
const productoInfo = ref(null)
const mostrarStockBajo = ref(false)
const productosStockBajo = ref([])
const loadingStockBajo = ref(false)
const mostrarProductosProveedor = ref(false)
const productosProveedor = ref([])
const proveedorSeleccionado = ref(null)
const loadingProductosProveedor = ref(false)

const fuentesConocidas = {
  carrefour: { nombre: 'Carrefour', color: 'bg-blue-500', icon: 'fa-store' },
  vea: { nombre: 'Vea', color: 'bg-red-500', icon: 'fa-store' },
  masonline: { nombre: 'Mas Online', color: 'bg-green-500', icon: 'fa-store' },
  supercoco: { nombre: 'Super Coco', color: 'bg-purple-500', icon: 'fa-store' },
  catalogo_central: { nombre: 'Catálogo', color: 'bg-gray-500', icon: 'fa-book' },
  local: { nombre: 'Local', color: 'bg-brand-500', icon: 'fa-database' }
}

async function buscarPrecios() {
  const barcode = barcodeInput.value.trim()
  if (!barcode) {
    toast.warning('Ingresá un código de barras')
    return
  }

  loading.value = true
  resultados.value = []
  productoInfo.value = null

  try {
    // Primero buscar en base local
    const localResp = await api.post('/api/productos/lookup', { barcode })
    
    if (localResp && localResp.id) {
      // Obtener info detallada del producto
      const infoResp = await api.get(`/api/productos/${localResp.id}/info-detallada`)
      
      if (infoResp) {
        productoInfo.value = {
          id: localResp.id,
          nombre: infoResp.producto.nombre,
          marca: infoResp.producto.marca,
          precio_local: infoResp.producto.precio_venta,
          stock: infoResp.producto.stock_actual,
          imagen: infoResp.producto.imagen_url,
          proveedores: infoResp.proveedores || [],
          ultima_compra: infoResp.ultima_compra
        }
      }
    }

    // Buscar precios en fuentes externas
    const preciosResp = await api.get(`/api/productos/precios-online/${barcode}`)
    
    if (preciosResp && Array.isArray(preciosResp)) {
      resultados.value = preciosResp.map(r => ({
        fuente: r.fuente,
        nombre: r.nombre,
        marca: r.marca,
        precio: r.precio_referencia || r.precio_venta,
        url: r.url,
        descuento: r.descuento,
        imagen: r.imagen_url
      }))
    }

    if (!productoInfo.value && resultados.value.length === 0) {
      toast.info('No se encontró el producto en ninguna fuente')
    }
  } catch (e) {
    console.error('Error buscando precios:', e)
    toast.error('Error al buscar precios online')
  } finally {
    loading.value = false
  }
}

async function toggleStockBajo() {
  mostrarStockBajo.value = !mostrarStockBajo.value
  
  if (mostrarStockBajo.value && productosStockBajo.value.length === 0) {
    await cargarProductosStockBajo()
  }
}

async function cargarProductosStockBajo() {
  loadingStockBajo.value = true
  try {
    const resp = await api.get('/api/productos/stock-bajo')
    if (Array.isArray(resp)) {
      productosStockBajo.value = resp
    }
  } catch (e) {
    console.error('Error cargando productos con stock bajo:', e)
    toast.error('Error al cargar productos con stock bajo')
  } finally {
    loadingStockBajo.value = false
  }
}

function seleccionarProductoStockBajo(producto) {
  barcodeInput.value = producto.codigo_barras
  mostrarStockBajo.value = false
  buscarPrecios()
}

async function verProductosProveedor(proveedor) {
  proveedorSeleccionado.value = proveedor
  mostrarProductosProveedor.value = true
  loadingProductosProveedor.value = true
  productosProveedor.value = []
  
  try {
    const resp = await api.get(`/api/proveedores/${proveedor.id}/productos`)
    if (Array.isArray(resp)) {
      productosProveedor.value = resp
    }
  } catch (e) {
    console.error('Error cargando productos del proveedor:', e)
    toast.error('Error al cargar productos del proveedor')
  } finally {
    loadingProductosProveedor.value = false
  }
}

function getFuenteInfo(fuente) {
  return fuentesConocidas[fuente?.toLowerCase()] || { 
    nombre: fuente || 'Desconocido', 
    color: 'bg-slate-500', 
    icon: 'fa-globe' 
  }
}

function abrirFuente(url) {
  if (url) {
    window.open(url, '_blank')
  }
}

function formatFecha(fechaStr) {
  if (!fechaStr) return ''
  const fecha = new Date(fechaStr)
  return fecha.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

const precioMasBajo = computed(() => {
  if (resultados.value.length === 0) return null
  return resultados.value.reduce((min, r) => {
    if (!r.precio) return min
    if (!min || r.precio < min.precio) return r
    return min
  }, null)
})
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Precios Online</h2>
        <p class="text-sm text-slate-500 mt-1">Compará precios en supermercados online</p>
      </div>
    </div>

    <!-- Búsqueda -->
    <BaseCard padding="lg">
      <div class="flex gap-3">
        <div class="flex-1">
          <BaseInput
            v-model="barcodeInput"
            label="Código de barras"
            placeholder="Escanear o ingresar código..."
            size="lg"
            @enter="buscarPrecios"
          >
            <template #prefix>
              <i class="fa-solid fa-barcode text-slate-400"></i>
            </template>
          </BaseInput>
        </div>
        <div class="flex items-end gap-2">
          <BaseButton 
            variant="secondary" 
            size="lg" 
            :active="mostrarStockBajo"
            @click="toggleStockBajo"
          >
            <i class="fa-solid fa-triangle-exclamation"></i>
            Stock Bajo
          </BaseButton>
          <BaseButton 
            variant="primary" 
            size="lg" 
            :loading="loading"
            @click="buscarPrecios"
          >
            <i :class="loading ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-search'"></i>
            {{ loading ? 'Buscando...' : 'Buscar' }}
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <!-- Lista de productos con stock bajo -->
    <BaseCard v-if="mostrarStockBajo" padding="none">
      <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-slate-900 text-sm">Productos con Stock Bajo</h3>
          <p class="text-xs text-slate-500 mt-1">
            {{ productosStockBajo.length }} producto(s) necesitan reposición
          </p>
        </div>
        <BaseButton 
          v-if="productosStockBajo.length > 0"
          variant="ghost" 
          size="xs"
          @click="cargarProductosStockBajo"
          :loading="loadingStockBajo"
        >
          <i class="fa-solid fa-refresh"></i>
        </BaseButton>
      </div>

      <div v-if="loadingStockBajo" class="p-8 text-center">
        <i class="fa-solid fa-circle-notch animate-spin text-2xl text-slate-400"></i>
        <p class="text-sm text-slate-500 mt-2">Cargando productos...</p>
      </div>

      <div v-else-if="productosStockBajo.length === 0" class="p-8 text-center">
        <i class="fa-solid fa-check-circle text-4xl text-emerald-500"></i>
        <p class="text-sm text-slate-500 mt-2">Todos los productos tienen stock suficiente</p>
      </div>

      <div v-else class="divide-y divide-slate-100 max-h-96 overflow-y-auto">
        <div 
          v-for="producto in productosStockBajo" 
          :key="producto.id"
          class="p-4 hover:bg-slate-50 transition-colors cursor-pointer"
          @click="seleccionarProductoStockBajo(producto)"
        >
          <div class="flex items-center gap-4">
            <!-- Imagen -->
            <div v-if="producto.imagen_url" class="w-12 h-12 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
              <img :src="producto.imagen_url" :alt="producto.nombre" class="w-full h-full object-cover" />
            </div>
            <div v-else class="w-12 h-12 rounded-lg bg-slate-100 flex items-center justify-center flex-shrink-0">
              <i class="fa-solid fa-box text-slate-400"></i>
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <h4 class="font-semibold text-slate-900 text-sm truncate">{{ producto.nombre }}</h4>
              <p v-if="producto.marca" class="text-xs text-slate-500 truncate">{{ producto.marca }}</p>
              <p class="text-xs text-slate-400 font-mono mt-1">{{ producto.codigo_barras }}</p>
            </div>

            <!-- Stock -->
            <div class="text-right flex-shrink-0">
              <BaseBadge 
                :variant="producto.stock_actual === 0 ? 'danger' : 'warning'" 
                size="sm"
              >
                {{ producto.stock_actual }} / {{ producto.stock_minimo }}
              </BaseBadge>
              <p class="text-xs text-slate-400 mt-1">
                {{ producto.stock_actual === 0 ? 'Sin stock' : 'Stock bajo' }}
              </p>
            </div>

            <!-- Precio local -->
            <div class="text-right flex-shrink-0">
              <p class="font-mono-data font-bold text-sm text-slate-900">{{ fc(producto.precio_venta) }}</p>
              <p class="text-xs text-slate-400">Precio local</p>
            </div>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Info del producto local -->
    <BaseCard v-if="productoInfo" padding="lg">
      <div class="flex items-start gap-4">
        <div v-if="productoInfo.imagen" class="w-20 h-20 rounded-xl overflow-hidden bg-slate-100 flex-shrink-0">
          <img :src="productoInfo.imagen" :alt="productoInfo.nombre" class="w-full h-full object-cover" />
        </div>
        <div class="flex-1">
          <h3 class="font-bold text-lg text-slate-900">{{ productoInfo.nombre }}</h3>
          <p v-if="productoInfo.marca" class="text-sm text-slate-500">{{ productoInfo.marca }}</p>
          <div class="flex items-center gap-4 mt-2">
            <div>
              <span class="text-xs text-slate-400">Precio local:</span>
              <span class="font-mono-data font-bold text-brand-600 ml-1">{{ fc(productoInfo.precio_local) }}</span>
            </div>
            <div>
              <span class="text-xs text-slate-400">Stock:</span>
              <BaseBadge :variant="productoInfo.stock > 0 ? 'success' : 'danger'" size="sm" class="ml-1">
                {{ productoInfo.stock }}
              </BaseBadge>
            </div>
          </div>
          
          <!-- Última compra -->
          <div v-if="productoInfo.ultima_compra" class="mt-3 pt-3 border-t border-slate-100">
            <div class="flex items-center gap-2 text-xs text-slate-500">
              <i class="fa-solid fa-clock"></i>
              <span>Última compra: <strong>{{ formatFecha(productoInfo.ultima_compra.fecha) }}</strong></span>
              <span v-if="productoInfo.ultima_compra.numero" class="text-slate-400">({{ productoInfo.ultima_compra.numero }})</span>
            </div>
          </div>
          
          <!-- Proveedores -->
          <div v-if="productoInfo.proveedores && productoInfo.proveedores.length > 0" class="mt-3 pt-3 border-t border-slate-100">
            <p class="text-xs text-slate-400 mb-2">Proveedores:</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="prov in productoInfo.proveedores"
                :key="prov.id"
                @click="verProductosProveedor(prov)"
                class="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 transition-colors text-xs font-medium text-slate-700"
              >
                <i class="fa-solid fa-truck text-slate-500"></i>
                {{ prov.nombre }}
                <span v-if="prov.costo" class="text-emerald-600 font-mono-data">({{ fc(prov.costo) }})</span>
                <BaseBadge v-if="prov.es_principal" variant="warning" size="xs">Principal</BaseBadge>
              </button>
            </div>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Resultados online -->
    <BaseCard v-if="resultados.length > 0" padding="none">
      <div class="px-5 py-4 border-b border-slate-100">
        <h3 class="font-bold text-slate-900 text-sm">Precios Online</h3>
        <p v-if="precioMasBajo" class="text-xs text-slate-500 mt-1">
          Precio más bajo: 
          <span class="font-mono-data font-bold text-emerald-600">{{ fc(precioMasBajo.precio) }}</span>
          en {{ getFuenteInfo(precioMasBajo.fuente).nombre }}
        </p>
      </div>

      <div class="divide-y divide-slate-100">
        <div 
          v-for="(resultado, idx) in resultados" 
          :key="idx"
          class="p-4 hover:bg-slate-50 transition-colors"
        >
          <div class="flex items-start gap-4">
            <!-- Imagen -->
            <div v-if="resultado.imagen" class="w-16 h-16 rounded-lg overflow-hidden bg-slate-100 flex-shrink-0">
              <img :src="resultado.imagen" :alt="resultado.nombre" class="w-full h-full object-cover" />
            </div>

            <!-- Info -->
            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <h4 class="font-semibold text-slate-900 text-sm truncate">{{ resultado.nombre }}</h4>
                  <p v-if="resultado.marca" class="text-xs text-slate-500 truncate">{{ resultado.marca }}</p>
                </div>

                <!-- Precio -->
                <div class="text-right flex-shrink-0">
                  <div class="font-mono-data font-bold text-lg" :class="resultado === precioMasBajo ? 'text-emerald-600' : 'text-slate-900'">
                    {{ fc(resultado.precio) }}
                  </div>
                  <div v-if="resultado.descuento?.activo" class="text-xs text-emerald-600">
                    <i class="fa-solid fa-tag"></i>
                    {{ fc(resultado.descuento.precio_oferta) }}
                  </div>
                </div>
              </div>

              <!-- Fuente y acciones -->
              <div class="flex items-center justify-between mt-3">
                <BaseBadge :variant="getFuenteInfo(resultado.fuente).color" size="sm">
                  <i :class="`fa-solid ${getFuenteInfo(resultado.fuente).icon} mr-1`"></i>
                  {{ getFuenteInfo(resultado.fuente).nombre }}
                </BaseBadge>

                <BaseButton 
                  v-if="resultado.url"
                  variant="secondary" 
                  size="xs"
                  @click="abrirFuente(resultado.url)"
                >
                  <i class="fa-solid fa-external-link-alt mr-1"></i>
                  Ver en {{ getFuenteInfo(resultado.fuente).nombre }}
                </BaseButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </BaseCard>

    <!-- Empty state -->
    <EmptyState 
      v-if="!loading && resultados.length === 0 && !productoInfo && !mostrarStockBajo"
      icon="fa-globe"
      title="Buscá precios online"
      text="Escaneá o ingresá un código de barras para comparar precios en supermercados online"
    />

    <!-- Modal de productos del proveedor -->
    <BaseModal
      v-model="mostrarProductosProveedor"
      :title="`Productos de ${proveedorSeleccionado?.nombre || 'Proveedor'}`"
      size="lg"
    >
      <div v-if="loadingProductosProveedor" class="py-8 text-center">
        <i class="fa-solid fa-circle-notch animate-spin text-2xl text-slate-400"></i>
        <p class="text-sm text-slate-500 mt-2">Cargando productos...</p>
      </div>
      
      <div v-else-if="productosProveedor.length === 0" class="py-8 text-center">
        <i class="fa-solid fa-box-open text-4xl text-slate-300"></i>
        <p class="text-sm text-slate-500 mt-2">Este proveedor no tiene productos asociados</p>
      </div>
      
      <div v-else class="space-y-3">
        <div
          v-for="producto in productosProveedor"
          :key="producto.id"
          class="flex items-center gap-4 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 transition-colors cursor-pointer"
          @click="barcodeInput.value = producto.codigo_barras; mostrarProductosProveedor = false; buscarPrecios()"
        >
          <!-- Imagen -->
          <div v-if="producto.imagen_url" class="w-12 h-12 rounded-lg overflow-hidden bg-white flex-shrink-0">
            <img :src="producto.imagen_url" :alt="producto.nombre" class="w-full h-full object-cover" />
          </div>
          <div v-else class="w-12 h-12 rounded-lg bg-white flex items-center justify-center flex-shrink-0">
            <i class="fa-solid fa-box text-slate-400"></i>
          </div>

          <!-- Info -->
          <div class="flex-1 min-w-0">
            <h4 class="font-semibold text-slate-900 text-sm truncate">{{ producto.nombre }}</h4>
            <p v-if="producto.marca" class="text-xs text-slate-500 truncate">{{ producto.marca }}</p>
            <p class="text-xs text-slate-400 font-mono mt-1">{{ producto.codigo_barras }}</p>
          </div>

          <!-- Stock y precio -->
          <div class="text-right flex-shrink-0">
            <p class="font-mono-data font-bold text-sm text-slate-900">{{ fc(producto.precio_venta) }}</p>
            <BaseBadge :variant="producto.stock_actual > 0 ? 'success' : 'danger'" size="xs">
              Stock: {{ producto.stock_actual }}
            </BaseBadge>
          </div>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
