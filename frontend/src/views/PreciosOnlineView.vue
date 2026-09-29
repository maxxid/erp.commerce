<script setup>
import { ref, computed } from 'vue'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc, formatDateShort as fd } from '@/composables/useUtils'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import KpiCard from '@/components/ui/KpiCard.vue'

const toast = useToastStore()

const barcodeInput = ref('')
const loading = ref(false)
const loadingInfo = ref(false)
const resultados = ref([])
const productoInfo = ref(null)
const noEstaEnLocal = ref(false)
const mostrarStockBajo = ref(false)
const productosStockBajo = ref([])
const loadingStockBajo = ref(false)
const mostrarProductosProveedor = ref(false)
const productosProveedor = ref([])
const proveedorSeleccionado = ref(null)
const loadingProductosProveedor = ref(false)

const fuentesConocidas = {
  carrefour: { nombre: 'Carrefour', variant: 'info', icon: 'fa-store' },
  vea: { nombre: 'Vea', variant: 'danger', icon: 'fa-store' },
  masonline: { nombre: 'MasOnline', variant: 'success', icon: 'fa-store' },
  supercoco: { nombre: 'Supercoco (experimental)', variant: 'brand', icon: 'fa-store', experimental: true }
}

function getFuenteInfo(fuente) {
  return fuentesConocidas[String(fuente || '').toLowerCase()] || {
    nombre: fuente || 'Desconocido',
    variant: 'default',
    icon: 'fa-globe'
  }
}

// El nombre canonico lo manda el backend (lookup_service.FUENTES). El mapa local
// solo aporta el color y el icono, que son cosas de presentacion.
function nombreFuenteDe(resultado) {
  if (!resultado) return ''
  return resultado.nombre_fuente || getFuenteInfo(resultado.fuente).nombre
}

function esFuenteExperimental(resultado) {
  if (!resultado) return false
  if (typeof resultado.experimental === 'boolean') return resultado.experimental
  return !!getFuenteInfo(resultado.fuente).experimental
}

function num(v) {
  const n = Number(v)
  return Number.isFinite(n) ? n : null
}

async function cargarInfoLocal(id) {
  loadingInfo.value = true
  try {
    const info = await api.get(`/api/productos/${id}/info-detallada`)
    if (info?.producto) {
      productoInfo.value = {
        id,
        nombre: info.producto.nombre,
        marca: info.producto.marca,
        precio_local: num(info.producto.precio_venta),
        precio_costo: num(info.producto.precio_costo),
        stock: num(info.producto.stock_actual),
        stock_minimo: num(info.producto.stock_minimo),
        imagen: info.producto.imagen_url,
        proveedores: Array.isArray(info.proveedores) ? info.proveedores : [],
        ultima_compra: info.ultima_compra
      }
    }
  } catch (e) {
    toast.error(e?.data?.detail || e.message || 'No se pudo leer la info del producto')
  } finally {
    loadingInfo.value = false
  }
}

async function buscarPrecios() {
  const barcode = barcodeInput.value.trim()
  if (!barcode) {
    toast.warning('Ingresá un código de barras')
    return
  }
  if (loading.value) return

  loading.value = true
  resultados.value = []
  productoInfo.value = null
  noEstaEnLocal.value = false

  try {
    let idLocal = null
    try {
      const lookup = await api.post('/api/productos/lookup', { barcode })
      idLocal = lookup?.id ?? null
    } catch (e) {
      if (e?.status === 404) {
        noEstaEnLocal.value = true
      } else {
        toast.error(e?.data?.detail || e.message || 'No se pudo consultar el catálogo')
      }
    }

    if (idLocal) {
      await cargarInfoLocal(idLocal)
      cargarAnalisis(idLocal)
    }

    try {
      const precios = await api.get(`/api/productos/precios-online/${barcode}`)
      if (Array.isArray(precios)) {
        resultados.value = precios
          .map(r => ({
            fuente: r.fuente,
            nombre_fuente: r.nombre_fuente || '',
            experimental: r.experimental === true,
            nombre: r.nombre,
            marca: r.marca || '',
            precio: num(r.precio),
            url: r.url,
            descuento: r.descuento || null,
            imagen: r.imagen_url || '',
            diferencia_vs_local: num(r.diferencia_vs_local),
            porcentaje_vs_local: num(r.porcentaje_vs_local)
          }))
          .filter(r => r.precio !== null)
          .sort((a, b) => a.precio - b.precio)
      }
    } catch (e) {
      toast.error(e?.data?.detail || e.message || 'Error al buscar precios online')
    }

    if (!productoInfo.value && resultados.value.length === 0) {
      toast.info('No se encontró el producto en ninguna fuente')
    }
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
    productosStockBajo.value = Array.isArray(resp) ? resp : []
  } catch (e) {
    toast.error(e?.data?.detail || e.message || 'Error al cargar productos con stock bajo')
  } finally {
    loadingStockBajo.value = false
  }
}

function buscarDesdeStockBajo(producto) {
  barcodeInput.value = producto.codigo_barras
  mostrarStockBajo.value = false
  buscarPrecios()
}

function buscarDesdeProveedor(producto) {
  barcodeInput.value = producto.codigo_barras
  mostrarProductosProveedor.value = false
  buscarPrecios()
}

async function verProductosProveedor(proveedor) {
  proveedorSeleccionado.value = proveedor
  mostrarProductosProveedor.value = true
  loadingProductosProveedor.value = true
  productosProveedor.value = []

  try {
    const resp = await api.get(`/api/proveedores/${proveedor.id}/productos`)
    productosProveedor.value = Array.isArray(resp) ? resp : []
  } catch (e) {
    toast.error(e?.data?.detail || e.message || 'Error al cargar productos del proveedor')
  } finally {
    loadingProductosProveedor.value = false
  }
}

function abrirFuente(url) {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

const precioMasBajo = computed(() => {
  const conPrecio = resultados.value.filter(r => r.precio !== null)
  return conPrecio.length ? conPrecio[0] : null
})

const precioLocal = computed(() => {
  const p = productoInfo.value?.precio_local
  return p === null || p === undefined ? null : p
})

const ahorroContraLocal = computed(() => {
  const local = precioLocal.value
  const bajo = precioMasBajo.value
  if (local === null || !bajo) return null
  return Number((local - bajo.precio).toFixed(2))
})

const porcentajeContraLocal = computed(() => {
  const local = precioLocal.value
  const bajo = precioMasBajo.value
  if (local === null || !bajo || !bajo.precio) return null
  return Number((((local - bajo.precio) / bajo.precio) * 100).toFixed(1))
})

const gananciaPorUnidad = computed(() => {
  const local = precioLocal.value
  const bajo = precioMasBajo.value
  if (local === null || !bajo) return null
  return Number((local - bajo.precio).toFixed(2))
})

const renderedResultados = computed(() =>
  resultados.value.map(r => ({ ...r, esMasBajo: precioMasBajo.value?.fuente === r.fuente && r.precio === precioMasBajo.value?.precio }))
)

const hayBusqueda = computed(() => loading.value || !!productoInfo.value || resultados.value.length > 0 || noEstaEnLocal.value)

const analisis = ref(null)
const loadingAnalisis = ref(false)
const descargandoPdf = ref(false)

async function cargarAnalisis(id) {
  loadingAnalisis.value = true
  analisis.value = null
  try {
    const resp = await api.get(`/api/productos/${id}/analisis-precios`)
    analisis.value = resp
  } catch (e) {
    toast.error(e?.data?.detail || e.message || 'No se pudo cargar el historial de precios')
  } finally {
    loadingAnalisis.value = false
  }
}

async function descargarAnalisisPdf() {
  if (!productoInfo.value?.id || descargandoPdf.value) return
  descargandoPdf.value = true
  try {
    const url = `/api/productos/${productoInfo.value.id}/analisis-precios/pdf`
    const { data } = await api.get(url, { responseType: 'blob' })
    const blob = new Blob([data], { type: 'application/pdf' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `analisis-precios-${productoInfo.value.id}.pdf`
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(link.href)
  } catch (e) {
    toast.error(e?.data?.detail || e.message || 'No se pudo generar el PDF')
  } finally {
    descargandoPdf.value = false
  }
}

const proveedoresOrdenados = computed(() => {
  const lista = Array.isArray(analisis.value?.proveedores) ? analisis.value.proveedores : []
  const mejor = num(analisis.value?.mejor_oferta_proveedor)
  return lista.map(p => ({ ...p, esMejorOferta: mejor !== null && num(p.costo_actual) === mejor }))
})

const historialOrdenado = computed(() => {
  const lista = Array.isArray(analisis.value?.historial) ? analisis.value.historial : []
  const mejorId = analisis.value?.mejor_historico?.compra_id
  return lista.map(h => ({ ...h, esMejorPrecio: mejorId !== null && h.compra_id === mejorId }))
})

const sinHistorial = computed(() => (analisis.value ? !analisis.value.tiene_historico : false))
const sinProveedores = computed(() => proveedoresOrdenados.value.length === 0)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Precios Online</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Compará precios en supermercados online</p>
      </div>
    </div>

    <BaseCard padding="lg">
      <div class="flex gap-3">
        <div class="flex-1">
          <BaseInput
            v-model="barcodeInput"
            label="Código de barras"
            placeholder="Escanear o ingresar código..."
            size="lg"
            :loading="loading"
            @enter="buscarPrecios"
          >
            <template #prefix>
              <i class="fa-solid fa-barcode text-slate-400"></i>
            </template>
          </BaseInput>
        </div>
        <div class="flex items-end gap-2">
          <BaseButton
            :variant="mostrarStockBajo ? 'primary' : 'secondary'"
            size="lg"
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
            <i v-if="!loading" class="fa-solid fa-search"></i>
            {{ loading ? 'Buscando...' : 'Buscar' }}
          </BaseButton>
        </div>
      </div>
      <p v-if="loading" class="text-xs text-slate-500 dark:text-slate-400 mt-3">
        <i class="fa-solid fa-circle-notch fa-spin mr-1"></i>
        Consultando las fuentes online. Puede tardar unos segundos.
      </p>
    </BaseCard>

    <BaseCard v-if="mostrarStockBajo" padding="none">
      <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white text-sm">Productos con Stock Bajo</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {{ productosStockBajo.length }} producto(s) necesitan reposición
          </p>
        </div>
        <BaseButton
          v-if="productosStockBajo.length > 0"
          variant="ghost"
          size="xs"
          :loading="loadingStockBajo"
          @click="cargarProductosStockBajo"
        >
          <i class="fa-solid fa-refresh"></i>
        </BaseButton>
      </div>

      <div v-if="loadingStockBajo" class="p-6 space-y-3">
        <div v-for="i in 4" :key="i" class="flex items-center gap-4">
          <BaseSkeleton width="3rem" height="3rem" rounded="lg" />
          <div class="flex-1 space-y-2">
            <BaseSkeleton height="0.875rem" width="60%" />
            <BaseSkeleton height="0.75rem" width="30%" />
          </div>
          <BaseSkeleton width="4rem" height="1.5rem" rounded="full" />
        </div>
      </div>

      <div v-else-if="productosStockBajo.length === 0" class="p-8 text-center">
        <i class="fa-solid fa-check-circle text-4xl text-emerald-500"></i>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">Todos los productos tienen stock suficiente</p>
      </div>

      <div v-else class="divide-y divide-slate-100 dark:divide-slate-800 max-h-96 overflow-y-auto">
        <div
          v-for="producto in productosStockBajo"
          :key="producto.id"
          class="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
          @click="buscarDesdeStockBajo(producto)"
        >
          <div class="flex items-center gap-4">
            <div v-if="producto.imagen_url" class="w-12 h-12 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 flex-shrink-0">
              <img :src="producto.imagen_url" :alt="producto.nombre" class="w-full h-full object-cover" />
            </div>
            <div v-else class="w-12 h-12 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
              <i class="fa-solid fa-box text-slate-400"></i>
            </div>

            <div class="flex-1 min-w-0">
              <h4 class="font-semibold text-slate-900 dark:text-white text-sm truncate">{{ producto.nombre }}</h4>
              <p v-if="producto.marca" class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ producto.marca }}</p>
              <p class="text-xs text-slate-400 font-mono mt-1">{{ producto.codigo_barras }}</p>
            </div>

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

            <div class="text-right flex-shrink-0">
              <p class="font-mono-data font-bold text-sm text-slate-900 dark:text-white">{{ fc(producto.precio_venta) }}</p>
              <p class="text-xs text-slate-400">Precio local</p>
            </div>
          </div>
        </div>
      </div>
    </BaseCard>

    <div v-if="loadingInfo" class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <BaseCard v-for="i in 3" :key="i" padding="lg">
        <BaseSkeleton height="1.5rem" width="70%" />
        <BaseSkeleton height="2rem" width="50%" class="mt-3" />
      </BaseCard>
    </div>

    <div v-else-if="productoInfo && precioMasBajo" class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <KpiCard
        label="Precio de venta local"
        :value="precioLocal ?? 0"
        :decimals="2"
        prefix="$ "
        icon="fa-tag"
        icon-color="brand"
        :sublabel="productoInfo.marca || productoInfo.nombre"
      />
      <KpiCard
        label="Mejor precio online"
        :value="precioMasBajo.precio ?? 0"
        :decimals="2"
        prefix="$ "
        icon="fa-cart-shopping"
        icon-color="info"
        :sublabel="nombreFuenteDe(precioMasBajo)"
      />
      <KpiCard
        label="Ganancia por unidad"
        :value="Math.abs(gananciaPorUnidad ?? 0)"
        :decimals="2"
        prefix="$ "
        :icon="(ahorroContraLocal ?? 0) >= 0 ? 'fa-arrow-trend-up' : 'fa-arrow-trend-down'"
        :icon-color="(ahorroContraLocal ?? 0) >= 0 ? 'success' : 'warning'"
        :sublabel="(ahorroContraLocal ?? 0) >= 0
          ? `Comprar online te deja ${fc(ahorroContraLocal)} de margen`
          : `Tu precio está ${fc(Math.abs(ahorroContraLocal ?? 0))} por debajo del online`"
      />
    </div>

    <BaseCard v-if="productoInfo" padding="lg">
      <div class="flex items-start justify-between gap-4">
        <div class="flex items-start gap-4 flex-1 min-w-0">
        <div v-if="productoInfo.imagen" class="w-20 h-20 rounded-xl overflow-hidden bg-slate-100 dark:bg-slate-800 flex-shrink-0">
          <img :src="productoInfo.imagen" :alt="productoInfo.nombre" class="w-full h-full object-cover" />
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <h3 class="font-bold text-lg text-slate-900 dark:text-white">{{ productoInfo.nombre }}</h3>
            <BaseBadge v-if="productoInfo.id" variant="default" size="xs">En tu catálogo</BaseBadge>
          </div>
          <p v-if="productoInfo.marca" class="text-sm text-slate-500 dark:text-slate-400">{{ productoInfo.marca }}</p>
          <div class="flex items-center gap-4 mt-2 flex-wrap">
            <div>
              <span class="text-xs text-slate-400">Precio local:</span>
              <span class="font-mono-data font-bold text-brand-600 dark:text-brand-400 ml-1">{{ fc(productoInfo.precio_local) }}</span>
            </div>
            <div v-if="productoInfo.precio_costo !== null">
              <span class="text-xs text-slate-400">Costo:</span>
              <span class="font-mono-data font-bold text-slate-700 dark:text-slate-300 ml-1">{{ fc(productoInfo.precio_costo) }}</span>
            </div>
            <div>
              <span class="text-xs text-slate-400">Stock:</span>
              <BaseBadge :variant="productoInfo.stock > 0 ? 'success' : 'danger'" size="sm" class="ml-1">
                {{ productoInfo.stock }}
              </BaseBadge>
            </div>
          </div>

          <div v-if="productoInfo.ultima_compra" class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <div class="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 flex-wrap">
              <i class="fa-solid fa-clock"></i>
              <span>Última compra: <strong>{{ fd(productoInfo.ultima_compra.fecha) }}</strong></span>
              <span v-if="productoInfo.ultima_compra.numero" class="text-slate-400">({{ productoInfo.ultima_compra.numero }})</span>
            </div>
          </div>

          <div v-if="productoInfo.proveedores.length" class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <p class="text-xs text-slate-400 mb-2">Proveedores:</p>
            <div class="flex flex-wrap gap-2">
              <button
                v-for="prov in productoInfo.proveedores"
                :key="prov.id"
                type="button"
                class="inline-flex items-center gap-1 px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 transition-colors text-xs font-medium text-slate-700 dark:text-slate-300"
                @click="verProductosProveedor(prov)"
              >
                <i class="fa-solid fa-truck text-slate-500 dark:text-slate-400"></i>
                {{ prov.nombre }}
                <span v-if="prov.costo" class="text-emerald-600 dark:text-emerald-400 font-mono-data">({{ fc(prov.costo) }})</span>
                <BaseBadge v-if="prov.es_principal" variant="warning" size="xs">Principal</BaseBadge>
              </button>
            </div>
          </div>
        </div>
        </div>
        <BaseButton
          variant="outline"
          size="sm"
          class="flex-shrink-0"
          :loading="descargandoPdf"
          @click="descargarAnalisisPdf"
        >
          <i class="fa-solid fa-file-pdf"></i>
          <span class="hidden sm:inline">Ficha PDF</span>
        </BaseButton>
      </div>
    </BaseCard>

    <BaseCard v-if="productoInfo" padding="none">
      <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white text-sm">Análisis de Compra</h3>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Lo que realmente pagaste contra lo que hay hoy
          </p>
        </div>
        <BaseButton
          variant="ghost"
          size="xs"
          :loading="loadingAnalisis"
          @click="cargarAnalisis(productoInfo.id)"
        >
          <i class="fa-solid fa-refresh"></i>
        </BaseButton>
      </div>

      <div v-if="loadingAnalisis" class="p-5 space-y-3">
        <div v-for="i in 3" :key="i" class="flex items-center gap-4">
          <BaseSkeleton width="6rem" height="1.25rem" />
          <BaseSkeleton height="0.875rem" width="40%" />
        </div>
      </div>

      <div v-else-if="!analisis" class="p-6 text-center text-sm text-slate-400">
        No se pudo cargar el análisis
      </div>

      <div v-else class="p-5 space-y-6">
        <div class="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <div class="p-3 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-900">
            <p class="text-xs text-amber-700 dark:text-amber-400">Último costo pagado</p>
            <p class="font-mono-data font-bold text-amber-900 dark:text-amber-200 mt-1">
              {{ analisis.ultimo_costo ? fc(analisis.ultimo_costo.precio_unitario) : '—' }}
            </p>
            <p v-if="analisis.ultimo_costo" class="text-xs text-amber-700/80 dark:text-amber-500/80 mt-1 truncate">
              {{ fd(analisis.ultimo_costo.fecha) }} · {{ analisis.ultimo_costo.proveedor_nombre }}
            </p>
          </div>

          <div class="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900">
            <p class="text-xs text-emerald-700 dark:text-emerald-400">Mejor costo histórico</p>
            <p class="font-mono-data font-bold text-emerald-900 dark:text-emerald-200 mt-1">
              {{ analisis.mejor_historico ? fc(analisis.mejor_historico.precio_unitario) : '—' }}
            </p>
            <p v-if="analisis.mejor_historico" class="text-xs text-emerald-700/80 dark:text-emerald-500/80 mt-1 truncate">
              {{ fd(analisis.mejor_historico.fecha) }} · {{ analisis.mejor_historico.proveedor_nombre }}
            </p>
          </div>

          <div class="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
            <p class="text-xs text-slate-500 dark:text-slate-400">Mejor oferta proveedor</p>
            <p class="font-mono-data font-bold text-slate-900 dark:text-white mt-1">
              {{ analisis.mejor_oferta_proveedor !== null ? fc(analisis.mejor_oferta_proveedor) : '—' }}
            </p>
            <p class="text-xs text-slate-400 mt-1">Costo de lista actual</p>
          </div>

          <div class="p-3 rounded-xl bg-blue-50 dark:bg-blue-950/30 border border-blue-200 dark:border-blue-900">
            <p class="text-xs text-blue-700 dark:text-blue-400">Mejor precio online</p>
            <p class="font-mono-data font-bold text-blue-900 dark:text-blue-200 mt-1">
              {{ analisis.online ? fc(analisis.online.precio) : '—' }}
            </p>
            <p v-if="analisis.online" class="text-xs text-blue-700/80 dark:text-blue-500/80 mt-1">
              {{ nombreFuenteDe(analisis.online) }} hoy
            </p>
          </div>
        </div>

        <div
          v-if="analisis.ahorro_vs_mejor_historico"
          class="p-3 rounded-xl text-sm"
          :class="analisis.ahorro_vs_mejor_historico.conviene_online
            ? 'bg-emerald-50 dark:bg-emerald-950/30 text-emerald-800 dark:text-emerald-300'
            : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300'"
        >
          <i
            class="fa-solid mr-1"
            :class="analisis.ahorro_vs_mejor_historico.conviene_online ? 'fa-circle-check' : 'fa-circle-info'"
          ></i>
          <template v-if="analisis.ahorro_vs_mejor_historico.conviene_online">
            Comprar hoy online sale
            <strong>{{ fc(analisis.ahorro_vs_mejor_historico.diferencia) }}</strong>
            menos que tu mejor compra histórica
            ({{ analisis.ahorro_vs_mejor_historico.porcentaje }}% menos).
          </template>
          <template v-else>
            Hoy ningún canal online le gana a tu mejor compra histórica por
            <strong>{{ fc(Math.abs(analisis.ahorro_vs_mejor_historico.diferencia)) }}</strong>.
          </template>
        </div>

        <div v-if="analisis.margen_actual" class="p-3 rounded-xl text-sm bg-slate-50 dark:bg-slate-800/50 text-slate-700 dark:text-slate-300">
          <i class="fa-solid fa-calculator mr-1"></i>
          Vendiendo a <strong>{{ fc(analisis.margen_actual.precio_venta) }}</strong> y comprando al
          precio online más bajo te quedan
          <strong :class="analisis.margen_actual.positivo ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">
            {{ fc(analisis.margen_actual.utilidad) }}
          </strong>
          por unidad ({{ analisis.margen_actual.porcentaje }}%).
        </div>

        <div>
          <h4 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            Costo por proveedor
          </h4>
          <p v-if="sinProveedores" class="text-sm text-slate-400 py-2">
            Este producto no tiene proveedores cargados.
          </p>
          <div v-else class="overflow-x-auto -mx-5 px-5">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                  <th class="py-2 pr-3 font-medium">Proveedor</th>
                  <th class="py-2 px-3 font-medium text-right">Costo actual</th>
                  <th class="py-2 px-3 font-medium text-right">Último pagado</th>
                  <th class="py-2 pl-3 font-medium text-right">Plazo</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="p in proveedoresOrdenados"
                  :key="p.proveedor_id"
                  class="border-b border-slate-100 dark:border-slate-800 last:border-0"
                  :class="p.esMejorOferta ? 'bg-emerald-50/60 dark:bg-emerald-950/20' : ''"
                >
                  <td class="py-2 pr-3 text-slate-900 dark:text-white">
                    {{ p.nombre }}
                    <BaseBadge v-if="p.es_principal" variant="warning" size="xs" class="ml-1">Principal</BaseBadge>
                    <BaseBadge v-if="p.esMejorOferta" variant="success" size="xs" class="ml-1">Mejor</BaseBadge>
                  </td>
                  <td class="py-2 px-3 text-right font-mono-data" :class="p.esMejorOferta ? 'text-emerald-700 dark:text-emerald-400 font-bold' : 'text-slate-700 dark:text-slate-300'">
                    {{ p.costo_actual !== null ? fc(p.costo_actual) : '—' }}
                  </td>
                  <td class="py-2 px-3 text-right font-mono-data text-slate-600 dark:text-slate-400">
                    {{ p.ultimo_precio_pagado !== null ? fc(p.ultimo_precio_pagado) : 'Nunca' }}
                    <span v-if="p.ultima_fecha_pago" class="block text-xs text-slate-400">{{ fd(p.ultima_fecha_pago) }}</span>
                  </td>
                  <td class="py-2 pl-3 text-right text-slate-500 dark:text-slate-400">
                    {{ p.plazo_entrega_dias !== null ? `${p.plazo_entrega_dias} d` : '—' }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <h4 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            Historial de compras
          </h4>
          <p v-if="sinHistorial" class="text-sm text-slate-400 py-2">
            Este producto todavía no tiene compras registradas.
          </p>
          <div v-else class="overflow-x-auto -mx-5 px-5">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-xs text-slate-500 dark:text-slate-400 border-b border-slate-200 dark:border-slate-700">
                  <th class="py-2 pr-3 font-medium">Fecha</th>
                  <th class="py-2 px-3 font-medium">Proveedor</th>
                  <th class="py-2 px-3 font-medium text-right">Cant.</th>
                  <th class="py-2 pl-3 font-medium text-right">Precio unit.</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="h in historialOrdenado"
                  :key="h.compra_id"
                  class="border-b border-slate-100 dark:border-slate-800 last:border-0"
                  :class="h.esMejorPrecio ? 'bg-amber-50/60 dark:bg-amber-950/20' : ''"
                >
                  <td class="py-2 pr-3 text-slate-700 dark:text-slate-300 whitespace-nowrap">
                    {{ fd(h.fecha) }}
                    <BaseBadge v-if="h.esMejorPrecio" variant="warning" size="xs" class="ml-1">Mínimo</BaseBadge>
                  </td>
                  <td class="py-2 px-3 text-slate-900 dark:text-white">{{ h.proveedor_nombre }}</td>
                  <td class="py-2 px-3 text-right font-mono-data text-slate-600 dark:text-slate-400">{{ h.cantidad_recibida }}</td>
                  <td class="py-2 pl-3 text-right font-mono-data font-semibold" :class="h.esMejorPrecio ? 'text-amber-700 dark:text-amber-400' : 'text-slate-900 dark:text-white'">
                    {{ fc(h.precio_unitario) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p class="text-xs text-slate-400 pt-2 border-t border-slate-100 dark:border-slate-800">
          Las compras anuladas quedan excluidas del historial.
        </p>
      </div>
    </BaseCard>

    <BaseCard v-if="loading && !productoInfo" padding="none">
      <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800">
        <h3 class="font-bold text-slate-900 dark:text-white text-sm">Precios Online</h3>
        <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">Buscando en las fuentes...</p>
      </div>
      <div class="p-4 space-y-4">
        <div v-for="i in 3" :key="i" class="flex items-start gap-4">
          <BaseSkeleton width="4rem" height="4rem" rounded="lg" />
          <div class="flex-1 space-y-2">
            <BaseSkeleton height="0.875rem" width="70%" />
            <BaseSkeleton height="0.75rem" width="40%" />
            <BaseSkeleton height="1.5rem" width="30%" class="mt-2" />
          </div>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-else-if="resultados.length > 0" padding="none">
      <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 class="font-bold text-slate-900 dark:text-white text-sm">Precios Online</h3>
          <p v-if="precioMasBajo" class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Precio más bajo:
            <span class="font-mono-data font-bold text-emerald-600 dark:text-emerald-400">{{ fc(precioMasBajo.precio) }}</span>
            en {{ nombreFuenteDe(precioMasBajo) }}
            <span v-if="porcentajeContraLocal !== null" class="text-slate-400">
              ({{ porcentajeContraLocal > 0 ? '+' : '' }}{{ porcentajeContraLocal }}% vs tu precio)
            </span>
          </p>
        </div>
        <span class="text-xs text-slate-400">{{ resultados.length }} fuente(s)</span>
      </div>

      <div class="divide-y divide-slate-100 dark:divide-slate-800">
        <div
          v-for="resultado in renderedResultados"
          :key="resultado.fuente"
          class="p-4 transition-colors"
          :class="resultado.esMasBajo ? 'bg-emerald-50/50 dark:bg-emerald-900/10' : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'"
        >
          <div class="flex items-start gap-4">
            <div v-if="resultado.imagen" class="w-16 h-16 rounded-lg overflow-hidden bg-slate-100 dark:bg-slate-800 flex-shrink-0">
              <img :src="resultado.imagen" :alt="resultado.nombre" class="w-full h-full object-cover" />
            </div>
            <div v-else class="w-16 h-16 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center flex-shrink-0">
              <i class="fa-solid fa-store text-slate-300 dark:text-slate-600"></i>
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-start justify-between gap-3">
                <div class="flex-1 min-w-0">
                  <div class="flex items-center gap-2">
                    <BaseBadge :variant="getFuenteInfo(resultado.fuente).variant" size="xs">
                      <i :class="`fa-solid ${getFuenteInfo(resultado.fuente).icon} mr-1`"></i>
                      {{ nombreFuenteDe(resultado) }}
                    </BaseBadge>
                    <BaseBadge v-if="resultado.esMasBajo" variant="success" size="xs">Más barato</BaseBadge>
                  </div>
                  <p v-if="esFuenteExperimental(resultado)" class="text-xs text-amber-600 dark:text-amber-400 mt-1.5 flex items-center gap-1">
                    <i class="fa-solid fa-triangle-exclamation"></i>
                    El precio puede no corresponder al mismo producto
                  </p>
                  <h4 class="font-semibold text-slate-900 dark:text-white text-sm truncate mt-1.5">{{ resultado.nombre }}</h4>
                  <p v-if="resultado.marca" class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ resultado.marca }}</p>
                </div>

                <div class="text-right flex-shrink-0">
                  <div
                    class="font-mono-data font-bold text-lg"
                    :class="resultado.esMasBajo ? 'text-emerald-600 dark:text-emerald-400' : 'text-slate-900 dark:text-white'"
                  >
                    {{ fc(resultado.precio) }}
                  </div>
                  <div v-if="resultado.diferencia_vs_local !== null" class="text-xs mt-0.5">
                    <span :class="resultado.diferencia_vs_local >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">
                      {{ resultado.diferencia_vs_local >= 0 ? '-' : '+' }}{{ fc(Math.abs(resultado.diferencia_vs_local)) }} vs tu precio
                    </span>
                  </div>
                  <div v-if="resultado.descuento?.activo && resultado.descuento.precio_oferta" class="text-xs text-emerald-600 dark:text-emerald-400 mt-0.5">
                    <i class="fa-solid fa-tag"></i>
                    {{ fc(resultado.descuento.precio_oferta) }}
                  </div>
                </div>
              </div>

              <div v-if="resultado.descuento?.activo && resultado.descuento.promocion" class="mt-2">
                <BaseBadge variant="amber" size="xs">
                  <i class="fa-solid fa-bolt mr-1"></i>{{ resultado.descuento.promocion }}
                </BaseBadge>
              </div>

              <div class="flex items-center justify-end mt-3">
                <BaseButton
                  v-if="resultado.url"
                  variant="secondary"
                  size="xs"
                  @click="abrirFuente(resultado.url)"
                >
                  <i class="fa-solid fa-external-link-alt mr-1"></i>
                  Ver en {{ nombreFuenteDe(resultado) }}
                </BaseButton>
              </div>
            </div>
          </div>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading && noEstaEnLocal && resultados.length === 0" padding="lg">
      <div class="flex items-start gap-3">
        <i class="fa-solid fa-circle-info text-amber-500 mt-0.5"></i>
        <div>
          <p class="text-sm font-semibold text-slate-900 dark:text-white">Ese producto no está en tu catálogo</p>
          <p class="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Podés crearlo desde Productos para tener precio de venta, costo y proveedores cargados.
          </p>
        </div>
      </div>
    </BaseCard>

    <EmptyState
      v-if="!hayBusqueda"
      icon="fa-globe"
      title="Buscá precios online"
      text="Escaneá o ingresá un código de barras para comparar precios en supermercados online"
    />

    <BaseModal
      :model-value="mostrarProductosProveedor"
      :title="`Productos de ${proveedorSeleccionado?.nombre || 'Proveedor'}`"
      size="lg"
      @update:model-value="mostrarProductosProveedor = $event"
    >
      <div v-if="loadingProductosProveedor" class="py-6 space-y-3">
        <div v-for="i in 5" :key="i" class="flex items-center gap-4">
          <BaseSkeleton width="3rem" height="3rem" rounded="lg" />
          <div class="flex-1 space-y-2">
            <BaseSkeleton height="0.875rem" width="60%" />
            <BaseSkeleton height="0.75rem" width="30%" />
          </div>
          <BaseSkeleton width="4rem" height="1rem" />
        </div>
      </div>

      <div v-else-if="productosProveedor.length === 0" class="py-8 text-center">
        <i class="fa-solid fa-box-open text-4xl text-slate-300 dark:text-slate-600"></i>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-2">Este proveedor no tiene productos asociados</p>
      </div>

      <div v-else class="space-y-3">
        <div
          v-for="producto in productosProveedor"
          :key="producto.id"
          class="flex items-center gap-4 p-3 rounded-xl bg-slate-50 hover:bg-slate-100 dark:bg-slate-800/50 dark:hover:bg-slate-800 transition-colors cursor-pointer"
          @click="buscarDesdeProveedor(producto)"
        >
          <div v-if="producto.imagen_url" class="w-12 h-12 rounded-lg overflow-hidden bg-white dark:bg-slate-900 flex-shrink-0">
            <img :src="producto.imagen_url" :alt="producto.nombre" class="w-full h-full object-cover" />
          </div>
          <div v-else class="w-12 h-12 rounded-lg bg-white dark:bg-slate-900 flex items-center justify-center flex-shrink-0">
            <i class="fa-solid fa-box text-slate-400"></i>
          </div>

          <div class="flex-1 min-w-0">
            <h4 class="font-semibold text-slate-900 dark:text-white text-sm truncate">{{ producto.nombre }}</h4>
            <p v-if="producto.marca" class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ producto.marca }}</p>
            <p class="text-xs text-slate-400 font-mono mt-1">{{ producto.codigo_barras }}</p>
          </div>

          <div class="text-right flex-shrink-0">
            <p class="font-mono-data font-bold text-sm text-slate-900 dark:text-white">{{ fc(producto.precio_venta) }}</p>
            <BaseBadge :variant="producto.stock_actual > 0 ? 'success' : 'danger'" size="xs">
              Stock: {{ producto.stock_actual }}
            </BaseBadge>
          </div>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
