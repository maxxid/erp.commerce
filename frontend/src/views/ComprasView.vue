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
            <BaseButton variant="primary" size="xs" @click="agregarItem">
              <i class="fa-solid fa-plus"></i> Agregar ítem
            </BaseButton>
          </div>

          <BaseTable
            :columns="[
              { key: 'producto', label: 'Producto' },
              { key: 'cantidad', label: 'Cantidad', align: 'center', width: 'w-20' },
              { key: 'precio', label: 'Precio', align: 'right', width: 'w-28' },
              { key: 'subtotal', label: 'Subtotal', align: 'right', width: 'w-28' },
              { key: 'acciones', label: '', align: 'center', width: 'w-8' }
            ]"
            :rows="nuevaCompra.items"
            compact
            empty-title="Sin ítems"
            empty-text="Agregá productos a la orden."
            empty-icon="fa-box-open"
          >
            <template #producto="{ row }">
              <BaseInput
                v-model="row.producto"
                placeholder="Nombre del producto"
                size="sm"
              />
            </template>
            <template #cantidad="{ row }">
              <BaseInput
                :model-value="row.cantidad"
                type="number"
                placeholder="0"
                size="sm"
                input-class="text-center font-mono-data"
                @update:modelValue="row.cantidad = Number($event)"
              />
            </template>
            <template #precio="{ row }">
              <BaseInput
                :model-value="row.precio"
                type="number"
                placeholder="0.00"
                size="sm"
                input-class="text-right font-mono-data"
                @update:modelValue="row.precio = Number($event)"
              />
            </template>
            <template #subtotal="{ row }">
              <span class="text-xs font-mono-data font-bold text-slate-800">{{ fc(row.cantidad * row.precio || 0) }}</span>
            </template>
            <template #acciones="{ row }">
              <BaseButton
                icon-only
                variant="ghost"
                size="xs"
                aria-label="Quitar"
                @click="quitarItem(nuevaCompra.items.indexOf(row))"
              >
                <i class="fa-solid fa-xmark"></i>
              </BaseButton>
            </template>
          </BaseTable>

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
import { ref, reactive, computed, onMounted } from 'vue'
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
import EmptyState from '@/components/ui/EmptyState.vue'

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
    toast.warning('Seleccioná un proveedor')
    return
  }
  if (!nuevaCompra.items.length) {
    toast.warning('Agregá al menos un ítem')
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
    toast.success('Orden de compra creada')
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
