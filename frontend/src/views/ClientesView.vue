<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Clientes</h1>
        <p class="text-sm text-slate-500 mt-1">Gestión de clientes y cuentas corrientes</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          :disabled="syncing"
          @click="syncClients"
          class="bg-white border border-slate-300 rounded-2xl px-4 py-2.5 text-sm font-medium hover:bg-slate-50 transition-colors flex items-center gap-2 shadow-sm disabled:opacity-60"
          title="Sincronizar clientes"
        >
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-sync'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </button>
        <button
          @click="openCreateModal"
          class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-2xl shadow-sm font-medium transition-colors flex items-center gap-2"
        >
          <i class="fa-solid fa-plus text-sm"></i>
          Nuevo cliente
        </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Nombre</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Doc. Tipo</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Doc. Número</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Teléfono</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Límite crédito</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Saldo</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="client in clients" :key="client.id" class="hover:bg-slate-50 transition-colors">
              <td class="px-5 py-4 font-medium text-slate-900">{{ client.name }}</td>
              <td class="px-5 py-4 text-slate-600">{{ client.docType }}</td>
              <td class="px-5 py-4 font-mono-data text-slate-700">{{ client.docNumber }}</td>
              <td class="px-5 py-4 text-slate-600">{{ client.phone }}</td>
              <td class="px-5 py-4 font-mono-data text-slate-700">{{ formatCurrency(client.creditLimit) }}</td>
              <td class="px-5 py-4 font-mono-data" :class="client.balance > client.creditLimit * 0.8 ? 'text-red-600' : 'text-slate-700'">{{ formatCurrency(client.balance) }}</td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <button
                    @click="openEditModal(client)"
                    class="text-slate-400 hover:text-brand-600 transition-colors"
                    title="Editar"
                  >
                    <i class="fa-solid fa-pen-to-square"></i>
                  </button>
                  <button
                    @click="openTicketsModal(client)"
                    class="text-slate-400 hover:text-blue-600 transition-colors"
                    title="Ver tickets"
                  >
                    <i class="fa-solid fa-ticket"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div class="px-5 py-3 border-t border-slate-100 text-sm text-slate-500">
        Mostrando {{ clients.length }} clientes
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showModal = false"></div>
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 class="text-lg font-semibold text-slate-900">{{ editingClient ? 'Editar cliente' : 'Nuevo cliente' }}</h2>
            <button @click="showModal = false" class="text-slate-400 hover:text-slate-600 transition-colors">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <form @submit.prevent="saveClient" class="px-6 py-5 space-y-4">
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Nombre</label>
              <input v-model="form.name" type="text" required class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="Nombre o razón social" />
            </div>
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Tipo documento</label>
                <select v-model="form.docType" required class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all">
                  <option value="">Seleccionar</option>
                  <option value="DNI">DNI</option>
                  <option value="CUIT">CUIT</option>
                  <option value="CUIL">CUIL</option>
                  <option value="Pasaporte">Pasaporte</option>
                </select>
              </div>
              <div>
                <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Número documento</label>
                <input v-model="form.docNumber" type="text" required class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="Número" />
              </div>
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Teléfono</label>
              <input v-model="form.phone" type="text" class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="+54 11 1234-5678" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Límite de crédito</label>
              <input v-model.number="form.creditLimit" type="number" step="0.01" min="0" required class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="0.00" />
            </div>
            <div class="flex justify-end gap-3 pt-2">
              <button
                type="button"
                @click="showModal = false"
                class="px-5 py-2.5 text-sm font-medium text-slate-600 bg-slate-100 rounded-xl hover:bg-slate-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                :disabled="saving"
                class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl shadow-sm font-medium transition-colors text-sm disabled:opacity-60"
              >
                <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : editingClient ? 'fa-solid fa-check' : 'fa-solid fa-plus'"></i>
                {{ saving ? 'Guardando...' : editingClient ? 'Guardar cambios' : 'Crear cliente' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <Teleport to="body">
      <div v-if="showTicketsModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showTicketsModal = false"></div>
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-2xl mx-4 max-h-[85vh] overflow-y-auto">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 class="text-lg font-semibold text-slate-900">Tickets de {{ selectedClient?.name }}</h2>
            <button @click="showTicketsModal = false" class="text-slate-400 hover:text-slate-600 transition-colors">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <div class="px-6 py-5">
            <table class="w-full text-left text-sm">
              <thead class="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ticket #</th>
                  <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Fecha</th>
                  <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Productos</th>
                  <th class="px-4 py-2.5 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Total</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-gray-100">
                <tr v-for="ticket in tickets" :key="ticket.id" class="hover:bg-slate-50">
                  <td class="px-4 py-3 font-mono-data text-slate-700">#{{ String(ticket.id).padStart(6, '0') }}</td>
                  <td class="px-4 py-3 text-slate-600">{{ ticket.date }}</td>
                  <td class="px-4 py-3 text-slate-600">{{ ticket.itemCount }} items</td>
                  <td class="px-4 py-3 font-mono-data font-medium text-slate-900">{{ formatCurrency(ticket.total) }}</td>
                </tr>
              </tbody>
            </table>
            <div v-if="tickets.length === 0" class="text-center py-8 text-slate-400">
              <i class="fa-solid fa-ticket text-3xl mb-2 block"></i>
              Sin tickets registrados
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { formatCurrency } from '@/composables/useUtils'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'

const toast = useToastStore()

const syncing = ref(false)
const saving = ref(false)

const clients = ref([
  { id: 1, name: 'Carnicería Don Pedro', docType: 'CUIT', docNumber: '20-30123456-7', phone: '+54 11 4123-7890', creditLimit: 500000, balance: 234500 },
  { id: 2, name: 'Supermercado La Esquina', docType: 'CUIT', docNumber: '30-70897654-2', phone: '+54 11 4567-1234', creditLimit: 800000, balance: 720000 },
  { id: 3, name: 'Distribuidora Norte SRL', docType: 'CUIT', docNumber: '33-55123478-9', phone: '+54 11 4890-5678', creditLimit: 1200000, balance: 345000 },
  { id: 4, name: 'María González', docType: 'DNI', docNumber: '28.456.789', phone: '+54 11 6123-9012', creditLimit: 200000, balance: 45000 },
  { id: 5, name: 'Almacén El Gaucho', docType: 'CUIT', docNumber: '23-18123456-4', phone: '+54 11 3987-6543', creditLimit: 350000, balance: 310000 },
])

const tickets = ref([
  { id: 1023, date: '2026-06-19 14:30', itemCount: 12, total: 67500 },
  { id: 982, date: '2026-06-16 10:15', itemCount: 8, total: 42300 },
  { id: 901, date: '2026-06-14 16:45', itemCount: 5, total: 18750 },
  { id: 845, date: '2026-06-10 09:30', itemCount: 15, total: 98500 },
  { id: 798, date: '2026-06-08 11:00', itemCount: 6, total: 31200 },
])

const showModal = ref(false)
const showTicketsModal = ref(false)
const editingClient = ref(null)
const selectedClient = ref(null)

const form = reactive({
  name: '',
  docType: '',
  docNumber: '',
  phone: '',
  creditLimit: 0,
})

onMounted(async () => {
  try {
    const data = await api.get('/api/clientes')
    if (data && data.length) clients.value = data
  } catch { /* fallback to mock */ }
})

async function syncClients() {
  syncing.value = true
  try {
    const data = await api.get('/api/clientes')
    if (data && data.length) clients.value = data
  } catch { /* fallback to mock */ }
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

function openTicketsModal(client) {
  selectedClient.value = client
  showTicketsModal.value = true
}

async function saveClient() {
  saving.value = true
  if (editingClient.value) {
    Object.assign(editingClient.value, { ...form })
  } else {
    clients.value.push({
      id: clients.value.length + 1,
      ...form,
      balance: 0,
    })
  }
  showModal.value = false
  saving.value = false
}
</script>
