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
          { key: 'cantidad', label: 'Canti.', align: 'right' },
          { key: 'pendiente', label: 'Pendiente', align: 'right' },
          { key: 'estado', label: 'Estado', align: 'center' },
          { key: 'fecha', label: 'Fecha' },
          { key: 'comentarios', label: '', align: 'center', skeleton: false },
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
          <span class="text-xs font-mono-data font-bold text-brand-600">{{ fc(row.total) }}</span>
        </template>
        <template #cantidad="{ row }">
          <span class="text-xs font-mono-data text-slate-700">{{ row.total_cantidad || 0 }}</span>
        </template>
        <template #pendiente="{ row }">
          <span class="text-xs font-mono-data font-bold" :class="row.total_pendiente > 0 ? 'text-amber-600' : 'text-slate-400'">
            {{ row.total_pendiente || 0 }}
          </span>
        </template>
        <template #estado="{ row }">
          <BaseBadge :variant="estadoBadgeVariant(row.estado)" size="xs">{{ row.estado }}</BaseBadge>
        </template>
        <template #fecha="{ row }">
          <span class="text-xs text-slate-600">{{ row.fecha_hora }}</span>
        </template>
        <template #comentarios="{ row }">
          <button
            v-if="row.notas"
            class="text-brand-500 hover:text-brand-700 transition-colors p-1"
            title="Ver comentarios"
            @click="openVerComentario(row)"
          >
            <i class="fa-solid fa-comment-dots text-sm"></i>
          </button>
        </template>
        <template #acciones="{ row }">
          <div class="flex items-center justify-center gap-1">
            <a
              v-if="row.proveedor_telefono"
              :href="`https://wa.me/${row.proveedor_telefono.replace(/\D/g,'')}`"
              target="_blank"
              rel="noopener"
              class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-emerald-500 hover:bg-emerald-600 text-white transition-colors"
              title="WhatsApp"
            >
              <i class="fa-brands fa-whatsapp text-sm"></i>
            </a>
            <BaseButton
              v-if="row.estado === 'pendiente' || row.estado === 'parcial'"
              variant="primary"
              size="xs"
              :disabled="receiving"
              @click="openReceiveModal(row)"
            >
              <i class="fa-solid fa-boxes-packing"></i> Recibir
            </BaseButton>
            <BaseButton
              v-else-if="row.estado === 'anulada'"
              variant="ghost"
              size="xs"
              disabled
            >
              <i class="fa-solid fa-ban"></i>
            </BaseButton>
            <span v-else class="text-[10px] text-emerald-600 font-medium">Recibida</span>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal v-model="showModalCompra" title="Cargar Mercadería" size="2xl">
      <div class="space-y-5">
        <div class="p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800/40 rounded-xl text-xs text-brand-700 dark:text-brand-300 flex items-start gap-2">
          <i class="fa-solid fa-circle-info mt-0.5"></i>
          <span>Un solo paso: escaneás o escribís los productos, y al dar <strong>Guardar</strong> la mercadería entra directo al stock como <strong>lote</strong> (con vencimiento si lo cargás). Los productos nuevos se crean automáticamente con la categoría que elijas.</span>
        </div>

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
            <div class="grid grid-cols-12 gap-2 px-3 py-2 text-[10px] font-bold text-slate-400 uppercase tracking-wide border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <span class="col-span-4">Producto</span>
              <span class="col-span-3">Código de Barras</span>
              <span class="col-span-2 text-center">Cantidad</span>
              <span class="col-span-2 text-right">Precio</span>
              <span class="col-span-1"></span>
            </div>
            <div class="max-h-[400px] overflow-y-auto overscroll-contain">

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
              <div v-for="(item, idx) in nuevaCompra.items" :key="item._key" class="px-3 py-2 border-b border-slate-100 dark:border-slate-700/50 hover:bg-white dark:hover:bg-slate-800/70 transition-colors">
          <div class="grid grid-cols-12 gap-2 items-center">
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

          <!-- Segunda fila: vencimiento + categoría + datos del producto nuevo -->
          <div class="flex flex-wrap items-center gap-3 mt-2 ml-0.5">
            <div class="flex items-center gap-2">
              <label class="text-[9px] uppercase tracking-wide font-bold text-slate-400">Vencimiento</label>
              <input
                v-model="item.vencimiento"
                type="date"
                class="px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              />
            </div>

            <template v-if="esNuevoProducto(item)">
              <div class="flex items-center gap-2">
                <label class="text-[9px] uppercase tracking-wide font-bold text-amber-500">Marca</label>
                <input
                  v-model="item.marca"
                  type="text"
                  placeholder="Opcional"
                  class="w-28 px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-700 rounded-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition"
                />
              </div>
              <div class="flex items-center gap-2">
                <label class="text-[9px] uppercase tracking-wide font-bold text-amber-500">P. Venta</label>
                <input
                  v-model.number="item.precio_venta"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  class="w-24 px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-700 rounded-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition"
                />
              </div>
              <div class="flex items-center gap-2">
                <label class="text-[9px] uppercase tracking-wide font-bold text-amber-500">Categoría</label>
                <select
                  v-model="item.categoria_id"
                  class="px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-700 rounded-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition"
                >
                  <option :value="null">Seleccionar...</option>
                  <option v-for="cat in categorias" :key="cat.id" :value="cat.id">{{ cat.nombre }}</option>
                </select>
                <BaseBadge variant="warning" size="xs">Nuevo</BaseBadge>
              </div>
            </template>
            <span v-else class="text-[9px] text-slate-400">Producto existente — se actualizará su costo</span>
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
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-boxes-packing'"></i>
            {{ saving ? 'Guardando...' : 'Guardar y Recibir' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <BaseModal v-model="showReceiveModal" :title="'Recibir Mercadería — ' + receiveTarget?.numero_orden" size="2xl">
      <div class="space-y-5">
        <div class="p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800/40 rounded-xl text-xs text-brand-700 dark:text-brand-300 flex items-start gap-2">
          <i class="fa-solid fa-circle-info mt-0.5"></i>
          <span>Cada producto se ingresa como un <strong>lote</strong>. Si tiene vencimiento, completalo para que se aplique el despacho FEFO (los más viejos primero).</span>
        </div>

        <BaseTable
          :columns="[
            { key: 'producto', label: 'Producto' },
            { key: 'cantidad', label: 'Pedido', align: 'center', width: 'w-20' },
            { key: 'cantidad_recibida', label: 'Recibido', align: 'center', width: 'w-20' },
            { key: 'pendiente', label: 'Pendiente', align: 'center', width: 'w-20' },
            { key: 'recibir', label: 'Recibir ahora', align: 'center', width: 'w-28' },
            { key: 'vencimiento', label: 'Vencimiento', align: 'center', width: 'w-44' }
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
          <template #vencimiento="{ row }">
            <BaseInput
              :model-value="receiveVencimientos[row.id] || ''"
              type="date"
              size="sm"
              input-class="text-center"
              @update:modelValue="receiveVencimientos[row.id] = $event"
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

    <!-- Modal Ver/Agregar Comentarios -->
    <BaseModal v-model="showVerComentario" :title="`Comentarios — ${verComentarioTarget?.numero_orden || ''}`" size="md">
      <div class="space-y-4">
        <div v-if="verComentarioTarget?.notas" class="bg-slate-50 dark:bg-slate-800 rounded-lg p-3 text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto border border-slate-200 dark:border-slate-700">
          {{ verComentarioTarget.notas }}
        </div>
        <p v-else class="text-sm text-slate-400 text-center py-4">Sin comentarios</p>
        <hr class="border-slate-200 dark:border-slate-700" />
        <div class="space-y-2">
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">Agregar comentario</label>
          <textarea
            v-model="comentarioTexto"
            rows="3"
            placeholder="Escribí un comentario..."
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none resize-none transition"
          ></textarea>
        </div>
        <div class="flex gap-2">
          <BaseButton variant="secondary" class="flex-1" @click="showVerComentario = false">Cerrar</BaseButton>
          <BaseButton variant="primary" class="flex-1" :disabled="savingComentario || !comentarioTexto.trim()" @click="guardarComentario">
            <i :class="savingComentario ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-paper-plane'"></i>
            {{ savingComentario ? 'Guardando...' : 'Agregar' }}
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
const categorias = ref([])
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
const receiveVencimientos = reactive({})
const showVerComentario = ref(false)
const verComentarioTarget = ref(null)
const comentarioTexto = ref('')
const savingComentario = ref(false)

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
    marca: '',
    precio_venta: 0,
    vencimiento: '',
    categoria_id: null,
    _scanning: false,
    _barcodeEdited: false,
    _cantidadFocused: false,
  }
}

function esNuevoProducto(item) {
  if (!item) return false
  const nombre = (item.producto || '').trim().toLowerCase()
  const code = (item.codigo_barras || '').trim()
  const existe = productosCatalogo.value.some(p =>
    (code && p.codigo_barras === code) ||
    (nombre && p.nombre && p.nombre.toLowerCase() === nombre)
  )
  return !existe && (!!nombre || !!code)
}

const totalCompra = computed(() =>
  nuevaCompra.items.reduce((sum, i) => sum + (i.cantidad * i.precio || 0), 0)
)

onMounted(async () => {
  await Promise.all([fetchCompras(), fetchProveedores(), fetchProductosCatalogo(), fetchCategorias()])
})

async function fetchCompras() {
  try {
    const data = await api.get('/api/compras')
    if (data && data.length) {
      compras.value = data.map(c => {
        const items = (c.items || []).map(i => ({
          id: i.id,
          producto: i.producto_nombre || '',
          cantidad: i.cantidad || 0,
          cantidad_recibida: i.cantidad_recibida || 0,
          precio: i.precio_unitario || 0,
          subtotal: i.subtotal || 0,
        }))
        const total_cantidad = items.reduce((s, i) => s + i.cantidad, 0)
        const total_pendiente = items.reduce((s, i) => s + Math.max(0, i.cantidad - (i.cantidad_recibida || 0)), 0)
        return {
          id: c.id,
          numero_orden: c.numero,
          proveedor: c.proveedor_nombre || '',
          proveedor_telefono: c.proveedor_telefono || '',
          total: c.total || 0,
          estado: c.estado || '',
          fecha: c.fecha ? new Date(c.fecha).toLocaleDateString('es-AR') : '',
          fecha_hora: c.fecha ? new Date(c.fecha).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '',
          notas: c.notas || '',
          total_cantidad,
          total_pendiente,
          items,
        }
      })
    }
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
    const data = await api.get('/api/productos?page_size=100000')
    if (data && data.length) productosCatalogo.value = data
  } catch { /* fallback to mock */ }
}

async function fetchCategorias() {
  try {
    const data = await api.get('/api/categorias')
    if (data && data.length) categorias.value = data
  } catch { /* fallback to mock */ }
}

async function syncData() {
  syncing.value = true
  try {
    await Promise.all([fetchCompras(), fetchProveedores(), fetchProductosCatalogo(), fetchCategorias()])
    toast.success('Datos sincronizados')
  } catch {
    toast.warning('Error al sincronizar')
  } finally {
    syncing.value = false
  }
}

function estadoCompraClass(estado) {
  const map = {
    'pendiente': 'bg-amber-50 text-amber-700',
    'parcial': 'bg-blue-50 text-blue-700',
    'recibida': 'bg-emerald-50 text-emerald-700',
    'anulada': 'bg-rose-50 text-rose-700',
  }
  return map[estado] || 'bg-slate-50 text-slate-600'
}

function estadoBadgeVariant(estado) {
  const map = {
    'pendiente': 'warning',
    'parcial': 'info',
    'recibida': 'success',
    'anulada': 'danger',
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
    if (el && el.focus) {
      el.focus()
      el.scrollIntoView({ block: 'nearest' })
    }
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
  if (idx === nuevaCompra.items.length - 1 && val) {
    asegurarFilaVacia()
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
  const itemsValidos = nuevaCompra.items.filter(i => (i.producto || '').trim() || (i.codigo_barras || '').trim())
  if (!itemsValidos.length) {
    toast.warning('Agregá al menos un ítem')
    return
  }
  // Validar categoría para productos nuevos
  const sinCategoria = itemsValidos.filter(i => esNuevoProducto(i) && !i.categoria_id)
  if (sinCategoria.length) {
    toast.warning(`Elegí la categoría para: ${sinCategoria.map(i => i.producto || i.codigo_barras).join(', ')}`)
    return
  }
  saving.value = true
  try {
    const payload = {
      proveedor_id: nuevaCompra.proveedor_id,
      notas: nuevaCompra.notas,
      recibir_directo: true,
      items: itemsValidos.map(i => ({
        producto: i.producto,
        codigo_barras: i.codigo_barras || '',
        cantidad: i.cantidad || 1,
        precio: i.precio || 0,
        marca: i.marca || '',
        precio_venta: i.precio_venta || 0,
        categoria_id: i.categoria_id || null,
        vencimiento: i.vencimiento || null,
      })),
    }
    const resp = await api.post('/api/compras', payload)
    if (resp && resp.id) {
      toast.success(resp.message || `Compra ${resp.numero || ''} recibida`)
    } else {
      toast.success('Mercadería cargada y recibida')
    }
    showModalCompra.value = false
    await fetchCompras()
    await fetchProductosCatalogo()
  } catch (e) {
    toast.error(e.message || 'Error al guardar compra')
  } finally {
    saving.value = false
  }
}

function openReceiveModal(compra) {
  receiveTarget.value = compra
  Object.keys(receiveCantidades).forEach(k => delete receiveCantidades[k])
  Object.keys(receiveVencimientos).forEach(k => delete receiveVencimientos[k])
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
    const payload = {
      cantidades: { ...receiveCantidades },
      vencimientos: { ...receiveVencimientos },
    }
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
      receiveTarget.value.estado = 'recibida'
      toast.success(`${receiveTarget.value.numero_orden} recibida completamente`)
    } else {
      receiveTarget.value.estado = 'parcial'
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

function openVerComentario(row) {
  verComentarioTarget.value = row
  comentarioTexto.value = ''
  showVerComentario.value = true
}

async function guardarComentario() {
  if (!comentarioTexto.value.trim() || !verComentarioTarget.value) return
  savingComentario.value = true
  try {
    const resp = await api.post(`/api/compras/${verComentarioTarget.value.id}/comentario`, { texto: comentarioTexto.value.trim() })
    if (resp && resp.notas) {
      verComentarioTarget.value.notas = resp.notas
      const compra = compras.value.find(c => c.id === verComentarioTarget.value.id)
      if (compra) compra.notas = resp.notas
    }
    comentarioTexto.value = ''
    toast.success('Comentario agregado')
  } catch {
    toast.error('Error al guardar comentario')
  } finally {
    savingComentario.value = false
  }
}
</script>
