<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Compras / Stock</h2>
        <p class="text-sm text-slate-500 mt-1">Órdenes de compra y recepción de mercadería</p>
      </div>
      <div class="flex items-center gap-2">
        <button :disabled="syncing" @click="syncData"
                class="px-3 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition shadow-sm">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </button>
        <button @click="abrirModalNuevaCompra"
                class="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl flex items-center gap-2 shadow-sm transition">
          <i class="fa-solid fa-plus"></i> Nueva Compra
        </button>
      </div>
    </div>

    <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-slate-50 text-left">
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">N° Orden</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Proveedor</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Total</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Estado</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Fecha</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="compra in compras" :key="compra.id" class="hover:bg-slate-50 transition">
              <td class="px-5 py-3 text-xs font-bold text-slate-700">{{ compra.numero_orden }}</td>
              <td class="px-5 py-3 text-xs text-slate-600">{{ compra.proveedor }}</td>
              <td class="px-5 py-3 text-xs font-mono-data font-bold text-slate-800">{{ fc(compra.total) }}</td>
              <td class="px-5 py-3">
                <span :class="estadoCompraClass(compra.estado)"
                      class="px-2 py-0.5 rounded-lg text-[10px] font-bold">
                  {{ compra.estado }}
                </span>
              </td>
              <td class="px-5 py-3 text-xs text-slate-600">{{ compra.fecha }}</td>
              <td class="px-5 py-3">
                <div class="flex items-center gap-1">
                  <button v-if="compra.estado === 'Pendiente' || compra.estado === 'Parcial'"
                          :disabled="receiving"
                          @click="openReceiveModal(compra)"
                          class="px-2 py-1 bg-amber-50 hover:bg-amber-100 text-amber-700 rounded-lg text-[10px] font-bold transition">
                    <i class="fa-solid fa-boxes-packing mr-1"></i> Recibir
                  </button>
                  <span v-if="compra.estado !== 'Pendiente' && compra.estado !== 'Parcial'" class="text-[10px] text-slate-300">—</span>
                </div>
              </td>
            </tr>
            <tr v-if="!compras.length">
              <td colspan="6" class="px-5 py-8 text-xs text-slate-400 text-center">Sin órdenes de compra</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Nueva Compra -->
    <div v-if="showModalCompra" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="showModalCompra = false"></div>
      <div class="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-2xl border border-slate-200 space-y-5 max-h-[85vh] overflow-y-auto">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-slate-900 text-lg">Nueva Orden de Compra</h3>
          <button @click="showModalCompra = false" class="text-slate-400 hover:text-slate-600">
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Proveedor</label>
            <select v-model="nuevaCompra.proveedor_id"
                    class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600">
              <option :value="null" disabled>Seleccionar proveedor</option>
              <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
            </select>
          </div>
          <div>
            <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Notas</label>
            <input v-model="nuevaCompra.notas" placeholder="Notas u observaciones"
                   class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600">
          </div>
        </div>

        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-[10px] font-bold text-slate-400 uppercase">Ítems</p>
            <button @click="agregarItem"
                    class="px-3 py-1 bg-brand-50 hover:bg-brand-100 text-brand-600 font-semibold text-xs rounded-lg flex items-center gap-1 transition">
              <i class="fa-solid fa-plus"></i> Agregar ítem
            </button>
          </div>
          <div class="overflow-x-auto border border-slate-200 rounded-xl">
            <table class="w-full text-xs">
              <thead>
                <tr class="bg-slate-50 text-left">
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase">Producto</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase text-center w-20">Cantidad</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase text-right w-28">Precio</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase text-right w-28">Subtotal</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase w-8"></th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="(item, idx) in nuevaCompra.items" :key="idx">
                  <td class="px-4 py-2">
                    <input v-model="item.producto" placeholder="Nombre del producto"
                           class="w-full bg-transparent text-slate-700 text-xs focus:outline-none">
                  </td>
                  <td class="px-4 py-2">
                    <input v-model.number="item.cantidad" type="number" min="1" placeholder="0"
                           class="w-full bg-transparent text-slate-700 text-xs text-center focus:outline-none font-mono-data">
                  </td>
                  <td class="px-4 py-2">
                    <input v-model.number="item.precio" type="number" min="0" placeholder="0.00"
                           class="w-full bg-transparent text-slate-700 text-xs text-right focus:outline-none font-mono-data">
                  </td>
                  <td class="px-4 py-2 text-xs font-mono-data font-bold text-slate-800 text-right">{{ fc(item.cantidad * item.precio || 0) }}</td>
                  <td class="px-4 py-2 text-center">
                    <button @click="quitarItem(idx)" class="text-slate-300 hover:text-rose-500 transition">
                      <i class="fa-solid fa-xmark"></i>
                    </button>
                  </td>
                </tr>
                <tr v-if="!nuevaCompra.items.length">
                  <td colspan="5" class="px-4 py-4 text-xs text-slate-400 text-center">Sin ítems. Agregá productos a la orden.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="nuevaCompra.items.length" class="flex justify-end">
            <span class="text-sm font-mono-data font-bold text-slate-800">
              Total: {{ fc(totalCompra) }}
            </span>
          </div>
        </div>

        <div class="flex gap-2 pt-2">
          <button @click="showModalCompra = false"
                  class="flex-1 px-4 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition">
            Cancelar
          </button>
          <button :disabled="saving" @click="guardarCompra"
                  class="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl transition">
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ saving ? 'Guardando...' : 'Guardar Orden' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Recibir Mercadería -->
    <Teleport to="body">
      <div v-if="showReceiveModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="showReceiveModal = false"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-2xl border border-slate-200 space-y-5 max-h-[85vh] overflow-y-auto">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-slate-900 text-lg">Recibir Mercadería — {{ receiveTarget?.numero_orden }}</h3>
            <button @click="showReceiveModal = false" class="text-slate-400 hover:text-slate-600">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>

          <div class="overflow-x-auto border border-slate-200 rounded-xl">
            <table class="w-full text-xs">
              <thead>
                <tr class="bg-slate-50 text-left">
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase">Producto</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase text-center w-20">Pedido</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase text-center w-20">Recibido</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase text-center w-20">Pendiente</th>
                  <th class="px-4 py-2 text-[10px] font-bold text-slate-400 uppercase text-center w-28">Recibir ahora</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-50">
                <tr v-for="item in receiveTarget?.items" :key="item.id">
                  <td class="px-4 py-2.5 text-xs text-slate-700 font-medium">{{ item.producto }}</td>
                  <td class="px-4 py-2.5 text-xs font-mono-data text-slate-700 text-center">{{ item.cantidad }}</td>
                  <td class="px-4 py-2.5 text-xs font-mono-data text-slate-700 text-center">{{ item.cantidad_recibida || 0 }}</td>
                  <td class="px-4 py-2.5 text-xs font-mono-data font-bold text-slate-700 text-center">{{ item.cantidad - (item.cantidad_recibida || 0) }}</td>
                  <td class="px-4 py-2.5 text-center">
                    <input v-model.number="receiveCantidades[item.id]"
                           type="number"
                           :min="0"
                           :max="item.cantidad - (item.cantidad_recibida || 0)"
                           class="w-20 bg-slate-50 border border-slate-200 rounded-lg px-2 py-1 text-xs text-center focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 font-mono-data">
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="flex gap-2 pt-2">
            <button @click="showReceiveModal = false"
                    class="flex-1 px-4 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition">
              Cancelar
            </button>
            <button :disabled="receiving" @click="confirmarRecepcion"
                    class="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl transition">
              <i :class="receiving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
              {{ receiving ? 'Confirmando...' : 'Confirmar Recepción' }}
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
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'

const auth = useAuthStore()
const toast = useToastStore()

const proveedores = ref([
  { id: 1, nombre: 'Distribuidora Norte SA' },
  { id: 2, nombre: 'Mayorista del Sur' },
  { id: 3, nombre: 'Importadora Central' },
])

const compras = ref([
  {
    id: 1, numero_orden: 'OC-001', proveedor: 'Distribuidora Norte SA',
    total: 45000, estado: 'Pendiente', fecha: '2026-06-19',
    items: [
      { id: 101, producto: 'Coca-Cola 500ml', cantidad: 50, precio: 800, subtotal: 40000, cantidad_recibida: 0 },
      { id: 102, producto: 'Papas Fritas', cantidad: 10, precio: 500, subtotal: 5000, cantidad_recibida: 0 },
    ]
  },
])

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

const totalCompra = computed(() =>
  nuevaCompra.items.reduce((sum, i) => sum + (i.cantidad * i.precio || 0), 0)
)

onMounted(async () => {
  await fetchCompras()
  await fetchProveedores()
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

async function syncData() {
  syncing.value = true
  try {
    await fetchCompras()
    await fetchProveedores()
    toast.add('success', 'Datos sincronizados')
  } catch {
    toast.add('warning', 'Error al sincronizar')
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

function abrirModalNuevaCompra() {
  nuevaCompra.proveedor_id = null
  nuevaCompra.notas = ''
  nuevaCompra.items = []
  showModalCompra.value = true
}

function agregarItem() {
  nuevaCompra.items.push({ producto: '', cantidad: 1, precio: 0, id: Date.now() + Math.random() })
}

function quitarItem(idx) {
  nuevaCompra.items.splice(idx, 1)
}

async function guardarCompra() {
  if (!nuevaCompra.proveedor_id) {
    toast.add('warning', 'Seleccioná un proveedor')
    return
  }
  if (!nuevaCompra.items.length) {
    toast.add('warning', 'Agregá al menos un ítem')
    return
  }
  saving.value = true
  try {
    const proveedor = proveedores.value.find(p => p.id === nuevaCompra.proveedor_id)
    const orden = {
      id: Date.now(),
      numero_orden: 'OC-' + String(compras.value.length + 1).padStart(3, '0'),
      proveedor: proveedor ? proveedor.nombre : '—',
      total: totalCompra.value,
      estado: 'Pendiente',
      fecha: new Date().toISOString().slice(0, 10),
      items: nuevaCompra.items.map(i => ({
        id: i.id || Date.now() + Math.random(),
        producto: i.producto || 'Sin nombre',
        cantidad: i.cantidad,
        precio: i.precio,
        subtotal: i.cantidad * i.precio,
        cantidad_recibida: 0,
      })),
    }
    compras.value.push(orden)
    showModalCompra.value = false
    toast.add('success', 'Orden de compra creada')
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
    toast.add('warning', 'Ingresá al menos una cantidad a recibir')
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
      toast.add('success', `${receiveTarget.value.numero_orden} recibida completamente`)
    } else {
      receiveTarget.value.estado = 'Parcial'
      toast.add('success', `Recepción parcial de ${receiveTarget.value.numero_orden} registrada`)
    }

    showReceiveModal.value = false
    await fetchCompras()
  } catch {
    toast.add('error', 'Error al confirmar recepción')
  } finally {
    receiving.value = false
  }
}
</script>
