<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Clientes</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gestión de clientes y cuentas corrientes</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton
          variant="secondary"
          size="sm"
          :loading="syncing"
          :disabled="syncing"
          @click="syncClients"
        >
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-sync'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
        <BaseButton variant="primary" size="sm" @click="openCreateModal">
          <i class="fa-solid fa-plus text-sm"></i>
          Nuevo cliente
        </BaseButton>
      </div>
    </div>

    <BaseCard padding="none">
      <BaseTable
        :columns="[
          { key: 'name', label: 'Nombre' },
          { key: 'docType', label: 'Doc. Tipo' },
          { key: 'docNumber', label: 'Doc. Número' },
          { key: 'phone', label: 'Teléfono' },
          { key: 'creditLimit', label: 'Límite crédito', align: 'right' },
          { key: 'balance', label: 'Saldo', align: 'right' },
          { key: 'actions', label: 'Acciones', align: 'right' },
        ]"
        :rows="clients"
        empty-title="Sin clientes"
        empty-text="No hay clientes registrados."
        empty-icon="fa-users-slash"
      >
        <template #name="{ row }">
          <span class="font-medium text-slate-900 dark:text-white">{{ row.name }}</span>
        </template>
        <template #docType="{ row }">
          <span class="text-xs text-slate-600 dark:text-slate-300">{{ row.docType }}</span>
        </template>
        <template #docNumber="{ row }">
          <span class="font-mono-data text-slate-700 dark:text-slate-300">{{ row.docNumber }}</span>
        </template>
        <template #phone="{ row }">
          <span class="text-xs text-slate-600 dark:text-slate-300">{{ row.phone }}</span>
        </template>
        <template #creditLimit="{ row }">
          <span class="font-mono-data text-slate-700 dark:text-slate-300">{{ formatCurrency(row.creditLimit) }}</span>
        </template>
        <template #balance="{ row }">
          <span
            class="font-mono-data font-semibold"
            :class="row.balance > row.creditLimit * 0.8 ? 'text-red-600 dark:text-red-400' : 'text-slate-700 dark:text-slate-300'"
          >
            {{ formatCurrency(row.balance) }}
          </span>
        </template>
        <template #actions="{ row }">
          <div class="flex items-center justify-end gap-2">
            <BaseButton
              variant="ghost"
              size="sm"
              icon-only
              title="Editar"
              aria-label="Editar"
              @click="openEditModal(row)"
            >
              <i class="fa-solid fa-pen-to-square"></i>
            </BaseButton>
            <BaseButton
              variant="ghost"
              size="sm"
              icon-only
              title="Ver tickets"
              aria-label="Ver tickets"
              @click="openTicketsModal(row)"
            >
              <i class="fa-solid fa-ticket"></i>
            </BaseButton>
            <BaseButton
              v-if="row.balance > 0"
              variant="warning"
              size="sm"
              icon-only
              title="Cobrar deuda"
              aria-label="Cobrar deuda"
              @click="openCobroModal(row)"
            >
              <i class="fa-solid fa-hand-holding-dollar"></i>
            </BaseButton>
          </div>
        </template>
      </BaseTable>

      <div class="px-5 py-3 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400">
        Mostrando {{ clients.length }} clientes
      </div>
    </BaseCard>

    <BaseModal
      v-model="showModal"
      :title="editingClient ? 'Editar cliente' : 'Nuevo cliente'"
      size="lg"
    >
      <form class="space-y-4" @submit.prevent="saveClient">
        <BaseInput
          v-model="form.name"
          label="Nombre"
          type="text"
          placeholder="Nombre o razón social"
          required
        />
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <BaseSelect
            v-model="form.docType"
            label="Tipo documento"
            :options="[
              { value: '', label: 'Seleccionar' },
              { value: 'DNI', label: 'DNI' },
              { value: 'CUIT', label: 'CUIT' },
              { value: 'CUIL', label: 'CUIL' },
              { value: 'Pasaporte', label: 'Pasaporte' },
            ]"
            option-value="value"
            option-label="label"
            required
          />
          <BaseInput
            v-model="form.docNumber"
            label="Número documento"
            type="text"
            placeholder="Número"
            required
            input-class="font-mono-data"
          />
        </div>
        <BaseInput
          v-model="form.phone"
          label="Teléfono"
          type="text"
          placeholder="+54 11 1234-5678"
        />
        <BaseInput
          v-model.number="form.creditLimit"
          label="Límite de crédito"
          type="number"
          step="0.01"
          min="0"
          placeholder="0.00"
          required
          input-class="font-mono-data text-right"
        />
        <div class="flex justify-end gap-3 pt-2">
          <BaseButton type="button" variant="secondary" @click="showModal = false">
            Cancelar
          </BaseButton>
          <BaseButton
            type="submit"
            variant="primary"
            :loading="saving"
            :disabled="saving"
          >
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : editingClient ? 'fa-solid fa-check' : 'fa-solid fa-plus'"></i>
            {{ saving ? 'Guardando...' : editingClient ? 'Guardar cambios' : 'Crear cliente' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <BaseModal
      v-model="showTicketsModal"
      title="Historial de tickets"
      size="2xl"
      padding="none"
    >
      <div v-if="selectedClient" class="px-6 py-4 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
        <div class="flex items-center justify-between">
          <div>
            <span class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Cliente</span>
            <p class="text-sm font-medium text-slate-900 dark:text-white">{{ selectedClient.name }}</p>
          </div>
          <div class="text-right">
            <span class="text-[10px] uppercase tracking-wider text-slate-500 dark:text-slate-400 font-semibold">Deuda total</span>
            <p
              class="text-sm font-mono-data font-semibold"
              :class="selectedClient.balance > 0 ? 'text-red-600 dark:text-red-400' : 'text-slate-700 dark:text-slate-300'"
            >
              {{ formatCurrency(selectedClient.balance) }}
            </p>
          </div>
        </div>
      </div>

      <div class="overflow-y-auto max-h-[50vh]">
        <div v-if="loadingTickets" class="flex items-center justify-center py-16">
          <i class="fa-solid fa-circle-notch animate-spin text-3xl text-brand-600"></i>
        </div>

        <EmptyState
          v-else-if="tickets.length === 0"
          icon="fa-ticket"
          title="Sin tickets registrados"
          text="No se encontraron tickets para este cliente."
        />

        <div v-else class="divide-y divide-slate-100 dark:divide-slate-800">
          <div v-for="ticket in tickets" :key="ticket.id">
            <div
              class="flex items-center px-6 py-3.5 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
              @click="toggleTicket(ticket.id)"
            >
              <i
                class="fa-solid text-xs w-4 text-slate-400 transition-transform"
                :class="expandedTickets.has(ticket.id) ? 'fa-chevron-down' : 'fa-chevron-right'"
              ></i>
              <span class="font-mono-data text-slate-700 dark:text-slate-300 w-28">#{{ String(ticket.numero || ticket.id).padStart(6, '0') }}</span>
              <span class="text-sm text-slate-600 dark:text-slate-400 w-44">{{ ticket.fecha }}</span>
              <BaseBadge
                :variant="ticket.medio_pago === 'efectivo' ? 'success' : ticket.medio_pago === 'tarjeta' ? 'info' : ticket.medio_pago === 'transferencia' ? 'brand' : ticket.medio_pago === 'cuenta_corriente' || ticket.medio_pago === 'cta_cte' ? 'warning' : 'default'"
                size="sm"
              >
                {{ medioPagoLabel(ticket.medio_pago) }}
              </BaseBadge>
              <span class="ml-auto font-mono-data font-medium text-slate-900 dark:text-white">{{ formatCurrency(ticket.total) }}</span>
            </div>

            <div v-if="expandedTickets.has(ticket.id)" class="bg-slate-50/60 dark:bg-slate-800/30 px-6 py-3 border-t border-slate-100 dark:border-slate-800">
              <BaseTable
                :columns="[
                  { key: 'producto_nombre', label: 'Producto' },
                  { key: 'cantidad', label: 'Cantidad', align: 'center' },
                  { key: 'precio_unitario', label: 'Precio Unit.', align: 'right' },
                  { key: 'subtotal', label: 'Subtotal', align: 'right' },
                ]"
                :rows="ticket.items"
                compact
              >
                <template #cantidad="{ row }">
                  <span class="text-slate-600 dark:text-slate-400 text-center font-mono-data block">{{ row.cantidad }}</span>
                </template>
                <template #precio_unitario="{ row }">
                  <span class="text-slate-600 dark:text-slate-400 text-right font-mono-data block">{{ formatCurrency(row.precio_unitario) }}</span>
                </template>
                <template #subtotal="{ row }">
                  <span class="text-slate-900 dark:text-slate-100 text-right font-mono-data font-medium block">{{ formatCurrency(row.subtotal) }}</span>
                </template>
              </BaseTable>
            </div>
          </div>
        </div>
      </div>

      <div v-if="tickets.length > 0" class="px-6 py-3 border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-800/50">
        <div class="flex items-center justify-between mb-3">
          <span class="text-sm font-semibold text-slate-700 dark:text-slate-200">Total deuda en tickets</span>
          <span class="text-sm font-mono-data font-semibold text-red-600 dark:text-red-400">{{ formatCurrency(totalDebt) }}</span>
        </div>
        <BaseButton variant="secondary" block @click="imprimirResumen">
          <i class="fa-solid fa-print"></i>
          Imprimir resumen
        </BaseButton>
      </div>
    </BaseModal>

    <BaseModal v-model="showCobroModal" :title="`Cobrar Deuda — ${cobroTarget?.name}`" size="md">
      <div class="space-y-4">
        <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-4 text-center">
          <p class="text-xs uppercase tracking-wider text-red-500 font-semibold mb-1">Deuda actual</p>
          <p class="text-2xl font-mono-data font-bold text-red-600 dark:text-red-400">{{ formatCurrency(cobroTarget?.balance || 0) }}</p>
        </div>

        <BaseInput
          v-model="cobroMonto"
          label="Monto a cobrar"
          type="number"
          step="0.01"
          :min="0.01"
          :max="cobroTarget?.balance"
          placeholder="0.00"
        />
        <p class="text-xs text-slate-500 -mt-2">
          El monto no puede superar la deuda. Podés cobrar en partes.
        </p>

        <BaseInput
          v-model="cobroNotas"
          label="Notas (opcional)"
          placeholder="Ej: Pago parcial, Pago total..."
        />

        <div v-if="cobroMonto > 0 && cobroMonto <= (cobroTarget?.balance || 0)" class="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4 text-center">
          <p class="text-xs uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-semibold mb-1">Quedará debiendo</p>
          <p class="text-xl font-mono-data font-bold text-emerald-600 dark:text-emerald-400">{{ formatCurrency((cobroTarget?.balance || 0) - cobroMonto) }}</p>
        </div>

        <div class="flex gap-2 pt-2">
          <BaseButton variant="secondary" class="flex-1" @click="showCobroModal = false">
            Cancelar
          </BaseButton>
          <BaseButton variant="primary" class="flex-1" :disabled="cobrando || !cobroMonto" @click="confirmarCobro">
            <i :class="cobrando ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ cobrando ? 'Cobrando...' : 'Confirmar Cobro' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { formatCurrency } from '@/composables/useUtils'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const toast = useToastStore()

const syncing = ref(false)
const saving = ref(false)

const clients = ref([])

function apiToClient(item) {
  return {
    id: item.id,
    name: item.nombre || '',
    docType: item.tipo_documento || '',
    docNumber: item.numero_documento || '',
    phone: item.telefono || '',
    email: item.email || '',
    creditLimit: item.limite_credito || 0,
    balance: item.saldo_cta_corriente || 0,
    notas: item.notas || '',
    direccion: item.direccion || '',
    activo: item.activo !== false,
  }
}

function formToPayload() {
  return {
    nombre: form.name,
    tipo_documento: form.docType,
    numero_documento: form.docNumber,
    telefono: form.phone,
    limite_credito: form.creditLimit,
  }
}

const tickets = ref([])
const loadingTickets = ref(false)
const expandedTickets = ref(new Set())

const showModal = ref(false)
const showTicketsModal = ref(false)
const showCobroModal = ref(false)
const editingClient = ref(null)
const selectedClient = ref(null)
const cobroTarget = ref(null)
const cobroMonto = ref(0)
const cobroNotas = ref('')
const cobrando = ref(false)

const form = reactive({
  name: '',
  docType: '',
  docNumber: '',
  phone: '',
  creditLimit: 0,
})

const totalDebt = computed(() => {
  return tickets.value.reduce((sum, t) => sum + (parseFloat(t.total) || 0), 0)
})

const MEDIO_PAGO_LABELS = {
  efectivo: 'Efectivo',
  tarjeta: 'Tarjeta',
  transferencia: 'Transferencia',
  cuenta_corriente: 'Cta. cte.',
  cta_cte: 'Cta. cte.',
}

function medioPagoLabel(value) {
  return MEDIO_PAGO_LABELS[value] || value || '—'
}

function toggleTicket(id) {
  const next = new Set(expandedTickets.value)
  if (next.has(id)) {
    next.delete(id)
  } else {
    next.add(id)
  }
  expandedTickets.value = next
}

onMounted(async () => {
  try {
    const resp = await api.get('/api/clientes')
    const items = resp?.data || resp || []
    if (Array.isArray(items)) clients.value = items.map(apiToClient)
  } catch { /* sin datos */ }
})

async function syncClients() {
  syncing.value = true
  try {
    const resp = await api.get('/api/clientes')
    const items = resp?.data || resp || []
    if (Array.isArray(items)) clients.value = items.map(apiToClient)
  } catch { /* sin datos */ }
  syncing.value = false
}

function openCreateModal() {
  editingClient.value = null
  form.name = ''
  form.docType = ''
  form.docNumber = ''
  form.phone = ''
  form.creditLimit = 0
  showModal.value = true
}

function openEditModal(client) {
  editingClient.value = client
  form.name = client.name
  form.docType = client.docType
  form.docNumber = client.docNumber
  form.phone = client.phone
  form.creditLimit = client.creditLimit
  showModal.value = true
}

async function openTicketsModal(client) {
  selectedClient.value = client
  showTicketsModal.value = true
  tickets.value = []
  expandedTickets.value = new Set()
  loadingTickets.value = true
  try {
    const data = await api.get(`/api/ventas?cliente_id=${client.id}`)
    if (Array.isArray(data)) tickets.value = data
  } catch {
    toast.error('Error al cargar el historial de tickets')
  } finally {
    loadingTickets.value = false
  }
}

function openCobroModal(client) {
  cobroTarget.value = client
  cobroMonto.value = 0
  cobroNotas.value = ''
  showCobroModal.value = true
}

async function confirmarCobro() {
  if (!cobroMonto.value || cobroMonto.value <= 0) {
    toast.warning('Ingresá un monto válido')
    return
  }
  if (cobroMonto.value > (cobroTarget.value?.balance || 0)) {
    toast.warning('El monto no puede superar la deuda')
    return
  }
  cobrando.value = true
  try {
    const resp = await api.post(`/api/clientes/${cobroTarget.value.id}/abonar`, {
      monto: parseFloat(cobroMonto.value),
      notas: cobroNotas.value || null,
    })
    const updatedClient = apiToClient(resp?.data || resp)
    const idx = clients.value.findIndex(c => c.id === cobroTarget.value.id)
    if (idx !== -1) {
      clients.value[idx] = { ...clients.value[idx], ...updatedClient }
    }
    toast.success(`Cobro registrado: ${formatCurrency(cobroMonto.value)}`)
    showCobroModal.value = false
  } catch (e) {
    toast.error(e.message || 'Error al registrar el cobro')
  } finally {
    cobrando.value = false
  }
}

async function saveClient() {
  saving.value = true
  try {
    if (editingClient.value) {
      const resp = await api.put(`/api/clientes/${editingClient.value.id}`, formToPayload())
      Object.assign(editingClient.value, apiToClient(resp?.data || resp))
      toast.success('Cliente actualizado')
    } else {
      const resp = await api.post('/api/clientes', formToPayload())
      clients.value.push(apiToClient(resp?.data || resp))
      toast.success('Cliente creado')
    }
    showModal.value = false
  } catch (e) {
    toast.error(e?.data?.detail || 'Error al guardar el cliente')
  } finally {
    saving.value = false
  }
}

function imprimirResumen() {
  if (!selectedClient.value || tickets.value.length === 0) return

  const lines = []
  lines.push(`Resumen de tickets — ${selectedClient.value.name}`)
  lines.push(`Deuda total: ${formatCurrency(selectedClient.value.balance)}`)
  lines.push('')
  lines.push('Ticket # | Fecha | Medio de pago | Total')
  lines.push('-'.repeat(60))

  for (const t of tickets.value) {
    const num = String(t.numero || t.id).padStart(6, '0')
    lines.push(`#${num} | ${t.fecha} | ${medioPagoLabel(t.medio_pago)} | ${formatCurrency(t.total)}`)

    if (t.items && t.items.length) {
      for (const item of t.items) {
        lines.push(`  - ${item.producto_nombre} x${item.cantidad} | ${formatCurrency(item.precio_unitario)} c/u | ${formatCurrency(item.subtotal)}`)
      }
    }
  }

  lines.push('')
  lines.push(`Total acumulado: ${formatCurrency(totalDebt.value)}`)

  const win = window.open('', '_blank', 'width=600,height=600')
  if (win) {
    win.document.write(`<pre style="font-family:monospace;font-size:13px;padding:24px;white-space:pre-wrap">${lines.join('\n')}</pre>`)
    win.document.close()
    win.print()
  }
}
</script>
