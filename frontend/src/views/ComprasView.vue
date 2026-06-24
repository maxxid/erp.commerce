<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Compras / Stock</h2>
        <p class="text-sm text-slate-500 mt-1">Órdenes de compra y recepción de mercadería</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton variant="secondary" size="sm" :disabled="syncing" @click="syncData">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
        <BaseButton variant="primary" size="sm" @click="abrirModalNuevaCompra">
          <i class="fa-solid fa-plus"></i> Nueva Compra
        </BaseButton>
      </div>
    </div>

    <BaseCard padding="none">
      <BaseTable
        :columns="[
          { key: 'numero_orden', label: 'N° Orden' },
          { key: 'proveedor', label: 'Proveedor' },
          { key: 'total', label: 'Total', align: 'right' },
          { key: 'estado', label: 'Estado', align: 'center' },
          { key: 'fecha', label: 'Fecha' },
          { key: 'acciones', label: 'Acciones', align: 'center' }
        ]"
        :rows="compras"
        empty-title="Sin órdenes de compra"
        empty-text="No hay órdenes de compra registradas."
        empty-icon="fa-inbox"
      >
        <template #numero_orden="{ row }">
          <span class="text-xs font-bold text-slate-700">{{ row.numero_orden }}</span>
        </template>
        <template #proveedor="{ row }">
          <span class="text-xs text-slate-600">{{ row.proveedor }}</span>
        </template>
        <template #total="{ row }">
          <span class="text-xs font-mono-data font-bold text-slate-800">{{ fc(row.total) }}</span>
        </template>
        <template #estado="{ row }">
          <BaseBadge :variant="estadoBadgeVariant(row.estado)" size="xs">{{ row.estado }}</BaseBadge>
        </template>
        <template #fecha="{ row }">
          <span class="text-xs text-slate-600">{{ row.fecha }}</span>
        </template>
        <template #acciones="{ row }">
          <div class="flex items-center justify-center gap-1">
            <BaseButton
              v-if="row.estado === 'Pendiente' || row.estado === 'Parcial'"
              variant="primary"
              size="xs"
              :disabled="receiving"
              @click="openReceiveModal(row)"
            >
              <i class="fa-solid fa-boxes-packing"></i> Recibir
            </BaseButton>
            <span v-else class="text-[10px] text-slate-300">—</span>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal v-model="showModalCompra" title="Nueva Orden de Compra" size="2xl">
      <div class="space-y-5">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <BaseSelect
            label="Proveedor"
            :model-value="nuevaCompra.proveedor_id"
            :options="proveedores"
            option-value="id"
            option-label="nombre"
            placeholder="Seleccionar proveedor"
            @update:modelValue="nuevaCompra.proveedor_id = Number($event)"
          />
          <BaseInput
            v-model="nuevaCompra.notas"
            label="Notas"
            placeholder="Notas u observaciones"
          />
        </div>

        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-[10px] font-bold text-slate-400 uppercase">Ítems</p>
            <span class="text-[10px] text-slate-400">{{ nuevaCompra.items.length }} producto(s)</span>
          </div>

          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
            <div class="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wide border-b border-slate-200 dark:border-slate-700">
              <span class="col-span-4">Producto</span>
              <span class="col-span-3">Código de Barras</span>
              <span class="col-span-2 text-center">Cantidad</span>
              <span class="col-span-2 text-right">Precio</span>
              <span class="col-span-1"></span>
            </div>

            <TransitionGroup
              name="item-row"
              tag="div"
              enter-active-class="transition duration-200 ease-out-expo"
              enter-from-class="opacity-0 -translate-y-1"
              enter-to-class="opacity-100 translate-y-0"
              leave-active-class="transition duration-150 ease-in"
              leave-from-class="opacity-100"
              leave-to-class="opacity-0"
              move-class="transition duration-200 ease-out-expo"
            >
              <div
                v-for="(item, idx) in nuevaCompra.items"
                :key="item._key"
                class="grid grid-cols-12 gap-2 px-3 py-2 items-center border-b border-slate-100 dark:border-slate-700/50 hover:bg-white dark:hover:bg-slate-800/80 transition-colors"
              >
                <!-- Producto combobox -->
                <div class="col-span-4">
                  <input
                    :ref="el => { if (el) itemRefs[idx] = el }"
                    v-model="item.producto"
                    type="text"
                    list="productos-datalist"
                    placeholder="Elegir o escribir..."
                    class="w-full px-2 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                    :class="idx === nuevaCompra.items.length - 1 ? 'ring-1 ring-brand-300 dark:ring-brand-700' : ''"
                    @focus="onItemFocus(idx)"
                    @input="onProductoInput(idx, $event)"
                    @keydown.enter.prevent="onItemEnter(idx, $event)"
                    @keydown.tab="onItemTab(idx, $event)"
                  />
                </div>

                <!-- Código de barras -->
                <div class="col-span-3">
                  <input
                    v-model="item.codigo_barras"
                    type="text"
                    placeholder="Escanear..."
                    class="w-full px-2 py-1.5 text-xs font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition"
                    @keydown.enter.prevent="onBarcodeEnter(idx)"
                    @input="item._barcodeEdited = true"
                  />
                  <span v-if="item._scanning" class="text-[9px] text-amber-500 font-bold mt-0.5 block">
                    <i class="fa-solid fa-circle-notch fa-spin mr-1"></i>Buscando...
                  </span>
                </div>

                <!-- Cantidad -->
                <div class="col-span-2">
                  <input
                    v-model.number="item.cantidad"
                    type="number"
                    min="1"
                    placeholder="1"
                    class="w-full px-2 py-1.5 text-xs text-center font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                    @focus="item._cantidadFocused = true"
                    @keydown.enter.prevent="onCantidadEnter(idx)"
                  />
                </div>

                <!-- Precio -->
                <div class="col-span-2">
                  <input
                    v-model.number="item.precio"
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                    class="w-full px-2 py-1.5 text-xs text-right font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                  />
                </div>

                <!-- Acciones -->
                <div class="col-span-1 flex justify-center">
                  <button
                    type="button"
                    aria-label="Quitar ítem"
                    class="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex items-center justify-center transition"
                    @click="quitarItem(idx)"
                  >
                    <i class="fa-solid fa-trash text-[10px]"></i>
                  </button>
                </div>
              </div>
            </TransitionGroup>

            <datalist id="productos-datalist">
              <option v-for="p in productosCatalogo" :key="p.id" :value="p.nombre">
                {{ p.codigo_barras }} · {{ p.marca || '' }}
              </option>
            </datalist>

            <div v-if="!nuevaCompra.items.length" class="p-6 text-center">
              <p class="text-xs text-slate-400 dark:text-slate-500">
                Escribí un nombre, elegí de la lista, o escaneá un código de barras para empezar
              </p>
            </div>
          </div>

          <div v-if="nuevaCompra.items.length" class="flex justify-end">
            <span class="text-sm font-mono-data font-bold text-slate-800">
              Total: {{ fc(totalCompra) }}
            </span>
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <BaseButton variant="secondary" class="flex-1" @click="showModalCompra = false">
            Cancelar
          </BaseButton>
          <BaseButton variant="primary" class="flex-1" :disabled="saving" @click="guardarCompra">
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ saving ? 'Guardando...' : 'Guardar Orden' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <BaseModal v-model="showReceiveModal" :title="'Recibir Mercadería — ' + receiveTarget?.numero_orden" size="2xl">
      <div class="space-y-5">
        <BaseTable
          :columns="[
            { key: 'producto', label: 'Producto' },
            { key: 'cantidad', label: 'Pedido', align: 'center', width: 'w-20' },
            { key: 'cantidad_recibida', label: 'Recibido', align: 'center', width: 'w-20' },
            { key: 'pendiente', label: 'Pendiente', align: 'center', width: 'w-20' },
            { key: 'recibir', label: 'Recibir ahora', align: 'center', width: 'w-28' }
          ]"
          :rows="receiveTarget?.items || []"
          compact
        >
          <template #producto="{ row }">
            <span class="text-xs text-slate-700 font-medium">{{ row.producto }}</span>
          </template>
          <template #cantidad="{ row }">
            <span class="text-xs font-mono-data text-slate-700">{{ row.cantidad }}</span>
          </template>
          <template #cantidad_recibida="{ row }">
            <span class="text-xs font-mono-data text-slate-700">{{ row.cantidad_recibida || 0 }}</span>
          </template>
          <template #pendiente="{ row }">
            <span class="text-xs font-mono-data font-bold text-slate-700">{{ row.cantidad - (row.cantidad_recibida || 0) }}</span>
          </template>
          <template #recibir="{ row }">
            <BaseInput
              :model-value="receiveCantidades[row.id]"
              type="number"
              placeholder="0"
              size="sm"
              input-class="w-20 text-center font-mono-data"
              @update:modelValue="receiveCantidades[row.id] = Number($event)"
            />
          </template>
        </BaseTable>

        <div class="flex gap-2 pt-2">
          <BaseButton variant="secondary" class="flex-1" @click="showReceiveModal = false">
            Cancelar
          </BaseButton>
          <BaseButton variant="primary" class="flex-1" :disabled="receiving" @click="confirmarRecepcion">
            <i :class="receiving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ receiving ? 'Confirmando...' : 'Confirmar Recepción' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'

const auth = useAuthStore()
const toast = useToastStore()

const proveedores = ref([])
const productosCatalogo = ref([])
const itemRefs = reactive({})
let _itemCounter = 0

const compras = ref([])

const showModalCompra = ref(false)
const showReceiveModal = ref(false)
const syncing = ref(false)
const receiving = ref(false)
const saving = ref(false)
const receiveTarget = ref(null)
const receiveCantidades = reactive({})

const nuevaCompra = reactive({
  proveedor_id: null,
  notas: '',
  items: [],
})

function _nuevoItem(producto = '', codigo_barras = '', cantidad = 1, precio = 0) {
  _itemCounter++
  return {
    _key: `item-${_itemCounter}-${Date.now()}`,
    producto,
    codigo_barras,
    cantidad,
    precio,
    _scanning: false,
    _barcodeEdited: false,
    _cantidadFocused: false,
  }
}

const totalCompra = computed(() =>
  nuevaCompra.items.reduce((sum, i) => sum + (i.cantidad * i.precio || 0), 0)
)

onMounted(async () => {
  await Promise.all([fetchCompras(), fetchProveedores(), fetchProductosCatalogo()])
})

async function fetchCompras() {
  try {
    const data = await api.get('/api/compras')
    if (data && data.length) compras.value = data
  } catch { /* fallback to mock */ }
}

async function fetchProveedores() {
  try {
    const data = await api.get('/api/proveedores')
    if (data && data.length) proveedores.value = data
  } catch { /* fallback to mock */ }
}

async function fetchProductosCatalogo() {
  try {
    const data = await api.get('/api/productos?page_size=200')
    if (data && data.length) productosCatalogo.value = data
  } catch { /* fallback to mock */ }
}

async function syncData() {
  syncing.value = true
  try {
    await Promise.all([fetchCompras(), fetchProveedores(), fetchProductosCatalogo()])
    toast.success('Datos sincronizados')
  } catch {
    toast.warning('Error al sincronizar')
  } finally {
    syncing.value = false
  }
}

function estadoCompraClass(estado) {
  const map = {
    'Pendiente': 'bg-amber-50 text-amber-700',
    'Recibido': 'bg-emerald-50 text-emerald-700',
    'Parcial': 'bg-blue-50 text-blue-700',
    'Cancelado': 'bg-rose-50 text-rose-700',
  }
  return map[estado] || 'bg-slate-50 text-slate-600'
}

function estadoBadgeVariant(estado) {
  const map = {
    'Pendiente': 'warning',
    'Recibido': 'success',
    'Parcial': 'info',
    'Cancelado': 'danger',
  }
  return map[estado] || 'default'
}

function abrirModalNuevaCompra() {
  nuevaCompra.proveedor_id = null
  nuevaCompra.notas = ''
  nuevaCompra.items = [_nuevoItem()]
  _itemCounter = 0
  showModalCompra.value = true
  nextTick(() => focusUltimaFila())
}

function asegurarFilaVacia() {
  const ultima = nuevaCompra.items[nuevaCompra.items.length - 1]
  if (!ultima || ultima.producto.trim() || ultima.codigo_barras.trim()) {
    nuevaCompra.items.push(_nuevoItem())
  }
}

function focusUltimaFila() {
  const idx = nuevaCompra.items.length - 1
  if (idx < 0) return
  nextTick(() => {
    const el = itemRefs[idx]
    if (el && el.focus) el.focus()
  })
}

function onItemFocus(idx) {
  if (idx === nuevaCompra.items.length - 1) return
}

function onProductoInput(idx, event) {
  const val = (event.target.value || '').trim()
  const prodEncontrado = productosCatalogo.value.find(
    p => p.nombre.toLowerCase() === val.toLowerCase()
  )
  if (prodEncontrado) {
    rellenarDesdeCatalogo(idx, prodEncontrado)
  }
}

function onItemEnter(idx, event) {
  const item = nuevaCompra.items[idx]
  if (!item) return

  // Si es la última fila y está vacía, no hacer nada
  if (idx === nuevaCompra.items.length - 1 && !item.producto.trim()) return

  // Rellenar datos si seleccionó de la lista
  const val = item.producto.trim()
  const prodEncontrado = productosCatalogo.value.find(
    p => p.nombre.toLowerCase() === val.toLowerCase()
  )
  if (prodEncontrado) {
    rellenarDesdeCatalogo(idx, prodEncontrado)
  }

  asegurarFilaVacia()
  focusUltimaFila()
}

function onItemTab(idx, event) {
  const item = nuevaCompra.items[idx]
  if (!item || !item.producto.trim()) return

  const val = item.producto.trim()
  const prodEncontrado = productosCatalogo.value.find(
    p => p.nombre.toLowerCase() === val.toLowerCase()
  )
  if (prodEncontrado) {
    rellenarDesdeCatalogo(idx, prodEncontrado)
  }
}

function onCantidadEnter(idx) {
  const item = nuevaCompra.items[idx]
  if (!item || !item.producto.trim()) return

  asegurarFilaVacia()
  focusUltimaFila()
}

async function onBarcodeEnter(idx) {
  const item = nuevaCompra.items[idx]
  if (!item) return
  const code = item.codigo_barras.trim()
  if (!code) return

  // Buscar en catálogo local primero
  const local = productosCatalogo.value.find(p => p.codigo_barras === code)
  if (local) {
    rellenarDesdeCatalogo(idx, local)
    item._scanning = false
    asegurarFilaVacia()
    focusUltimaFila()
    return
  }

  // Buscar en fuentes externas
  item._scanning = true
  try {
    const resp = await api.post('/api/productos/lookup', { barcode: code }).catch(() => null)
    if (resp && resp.nombre) {
      item.producto = resp.nombre
      item.codigo_barras = code
      item.precio = resp.precio_referencia || 0
      toast.info(`Encontrado: ${resp.nombre}`)
    } else {
      item.producto = code
      toast.warning('Código no encontrado. Ingresá el nombre manualmente.')
    }
  } catch {
    item.producto = code
    toast.warning('Error al buscar. Ingresá el nombre manualmente.')
  }
  item._scanning = false
  asegurarFilaVacia()
  focusUltimaFila()
}

function rellenarDesdeCatalogo(idx, prod) {
  const item = nuevaCompra.items[idx]
  if (!item) return
  item.producto = prod.nombre
  item.codigo_barras = prod.codigo_barras
  if (!item.precio || item.precio === 0) {
    item.precio = prod.precio_costo || prod.precio_referencia || 0
  }
}

function quitarItem(idx) {
  nuevaCompra.items.splice(idx, 1)
  if (!nuevaCompra.items.length) {
    nuevaCompra.items.push(_nuevoItem())
    focusUltimaFila()
  }
}

async function guardarCompra() {
  if (!nuevaCompra.proveedor_id) {
    toast.warning('Seleccioná un proveedor')
    return
  }
  const itemsValidos = nuevaCompra.items.filter(i => i.producto.trim())
  if (!itemsValidos.length) {
    toast.warning('Agregá al menos un ítem')
    return
  }
  saving.value = true
  try {
    const payload = {
      proveedor_id: nuevaCompra.proveedor_id,
      notas: nuevaCompra.notas,
      items: itemsValidos.map(i => ({
        producto: i.producto,
        codigo_barras: i.codigo_barras || '',
        cantidad: i.cantidad || 1,
        precio: i.precio || 0,
      })),
    }
    const resp = await api.post('/api/compras', payload)
    if (resp && resp.id) {
      toast.success(`Orden ${resp.numero || 'creada'}`)
    } else {
      const proveedor = proveedores.value.find(p => p.id === nuevaCompra.proveedor_id)
      compras.value.push({
        id: Date.now(),
        numero_orden: 'OC-' + String(compras.value.length + 1).padStart(3, '0'),
        proveedor: proveedor ? proveedor.nombre : '—',
        total: totalCompra.value,
        estado: 'Pendiente',
        fecha: new Date().toISOString().slice(0, 10),
        items: itemsValidos.map(i => ({
          id: Date.now() + Math.random(),
          producto: i.producto,
          cantidad: i.cantidad,
          precio: i.precio,
          subtotal: i.cantidad * i.precio,
          cantidad_recibida: 0,
        })),
      })
      toast.success('Orden de compra creada')
    }
    showModalCompra.value = false
    await fetchCompras()
  } catch (e) {
    toast.error(e.message || 'Error al guardar compra')
  } finally {
    saving.value = false
  }
}

function openReceiveModal(compra) {
  receiveTarget.value = compra
  Object.keys(receiveCantidades).forEach(k => delete receiveCantidades[k])
  compra.items.forEach(item => {
    receiveCantidades[item.id] = item.cantidad - (item.cantidad_recibida || 0)
  })
  showReceiveModal.value = true
}

async function confirmarRecepcion() {
  if (!receiveTarget.value) return
  const tieneCantidad = Object.values(receiveCantidades).some(v => v > 0)
  if (!tieneCantidad) {
    toast.warning('Ingresá al menos una cantidad a recibir')
    return
  }
  receiving.value = true
  try {
    const payload = { cantidades: { ...receiveCantidades } }
    await api.put(`/api/compras/${receiveTarget.value.id}/recibir`, payload)

    const totalRecibido = Object.values(payload.cantidades).reduce((sum, v) => sum + (Number(v) || 0), 0)
    const totalPedido = receiveTarget.value.items.reduce((sum, i) => sum + i.cantidad, 0)
    let totalPrevio = 0
    receiveTarget.value.items.forEach(item => {
      const recibidoAhora = Number(receiveCantidades[item.id]) || 0
      const recibidoPrevio = item.cantidad_recibida || 0
      totalPrevio += recibidoPrevio
      item.cantidad_recibida = (recibidoPrevio + recibidoAhora)
    })
    const totalAcumulado = totalPrevio + totalRecibido

    if (totalAcumulado >= totalPedido) {
      receiveTarget.value.estado = 'Recibido'
      toast.success(`${receiveTarget.value.numero_orden} recibida completamente`)
    } else {
      receiveTarget.value.estado = 'Parcial'
      toast.success(`Recepción parcial de ${receiveTarget.value.numero_orden} registrada`)
    }

    showReceiveModal.value = false
    await fetchCompras()
  } catch {
    toast.error('Error al confirmar recepción')
  } finally {
    receiving.value = false
  }
}
</script>
