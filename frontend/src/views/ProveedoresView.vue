<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Proveedores</h1>
        <p class="text-sm text-gray-500 mt-1">Gestión de proveedores de mercadería</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          :disabled="syncing"
          @click="syncProveedores"
          class="bg-white border border-gray-300 rounded-2xl px-4 py-2.5 text-sm font-medium hover:bg-gray-50 transition-colors flex items-center gap-2 shadow-sm disabled:opacity-60"
          title="Sincronizar proveedores"
        >
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-sync'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </button>
        <button
          @click="openCreateModal"
          class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-2xl shadow-sm font-medium transition-colors flex items-center gap-2"
        >
          <i class="fa-solid fa-plus text-sm"></i>
          Nuevo proveedor
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Total proveedores</p>
        <p class="text-2xl font-mono-data font-bold text-gray-900 mt-1">{{ suppliers.length }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Activos</p>
        <p class="text-2xl font-mono-data font-bold text-green-600 mt-1">{{ suppliers.filter(s => s.active).length }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Inactivos</p>
        <p class="text-2xl font-mono-data font-bold text-red-500 mt-1">{{ suppliers.filter(s => !s.active).length }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Último agregado</p>
        <p class="text-sm font-medium text-gray-900 mt-1 truncate">{{ suppliers[suppliers.length - 1]?.name || '—' }}</p>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Nombre</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">CUIT</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Teléfono</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Email</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Contacto</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Estado</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="supplier in suppliers" :key="supplier.id" class="hover:bg-gray-50 transition-colors">
              <td class="px-5 py-4 font-medium text-gray-900">{{ supplier.name }}</td>
              <td class="px-5 py-4 font-mono-data text-gray-700">{{ supplier.cuit }}</td>
              <td class="px-5 py-4 text-gray-600">{{ supplier.phone }}</td>
              <td class="px-5 py-4 text-gray-600">
                <a :href="'mailto:' + supplier.email" class="text-brand-600 hover:underline">{{ supplier.email }}</a>
              </td>
              <td class="px-5 py-4 text-gray-600">{{ supplier.contact }}</td>
              <td class="px-5 py-4">
                <span
                  class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
                  :class="supplier.active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'"
                >
                  <span class="w-1.5 h-1.5 rounded-full" :class="supplier.active ? 'bg-green-500' : 'bg-red-500'"></span>
                  {{ supplier.active ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <button
                    @click="openEditModal(supplier)"
                    class="text-gray-400 hover:text-brand-600 transition-colors"
                    title="Editar"
                  >
                    <i class="fa-solid fa-pen-to-square"></i>
                  </button>
                  <button
                    @click="toggleActive(supplier)"
                    :disabled="togglingId === supplier.id"
                    class="transition-colors disabled:opacity-60"
                    :class="supplier.active ? 'text-gray-400 hover:text-red-600' : 'text-gray-400 hover:text-green-600'"
                    title="Cambiar estado"
                  >
                    <i v-if="togglingId === supplier.id" class="fa-solid fa-circle-notch animate-spin"></i>
                    <i v-else :class="supplier.active ? 'fa-solid fa-circle-xmark' : 'fa-solid fa-circle-check'"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showModal = false"></div>
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 class="text-lg font-semibold text-gray-900">{{ editingSupplier ? 'Editar proveedor' : 'Nuevo proveedor' }}</h2>
            <button @click="showModal = false" class="text-gray-400 hover:text-gray-600 transition-colors">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <form @submit.prevent="saveSupplier" class="px-6 py-5 space-y-4">
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Nombre / Razón social</label>
              <input v-model="form.name" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="Nombre del proveedor" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">CUIT</label>
              <input v-model="form.cuit" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="XX-XXXXXXXX-X" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Teléfono</label>
              <input v-model="form.phone" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="+54 11 1234-5678" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Email</label>
              <input v-model="form.email" type="email" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="email@proveedor.com" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Persona de contacto</label>
              <input v-model="form.contact" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="Nombre del contacto" />
            </div>
            <div class="flex justify-end gap-3 pt-2">
              <button
                type="button"
                @click="showModal = false"
                class="px-5 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                :disabled="saving"
                class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl shadow-sm font-medium transition-colors text-sm disabled:opacity-60"
              >
                <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : editingSupplier ? 'fa-solid fa-check' : 'fa-solid fa-plus'"></i>
                {{ saving ? 'Guardando...' : editingSupplier ? 'Guardar cambios' : 'Crear proveedor' }}
              </button>
            </div>
          </form>
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
const togglingId = ref(null)

const suppliers = ref([
  { id: 1, name: 'Frigorífico Las Pampas SA', cuit: '30-51234567-8', phone: '+54 11 4321-9876', email: 'ventas@frigopampas.com.ar', contact: 'Carlos Méndez', active: true },
  { id: 2, name: 'Distribuidora Bebidas Norte', cuit: '33-99887766-5', phone: '+54 11 4678-2345', email: 'pedidos@bebidasnorte.com.ar', contact: 'Lucía Ramírez', active: true },
  { id: 3, name: 'Lácteos Santa Rosa SRL', cuit: '30-77654321-9', phone: '+54 11 3890-1122', email: 'info@lacteosantarosa.com.ar', contact: 'Jorge Peralta', active: true },
  { id: 4, name: 'Envasados del Sur', cuit: '27-33445566-1', phone: '+54 11 5555-7890', email: 'admin@envasadossur.com.ar', contact: 'Marina Díaz', active: false },
  { id: 5, name: 'Panificadora El Trigo', cuit: '20-12349876-3', phone: '+54 11 6123-4567', email: 'ventas@eltrigo.com.ar', contact: 'Roberto Suárez', active: true },
])

const showModal = ref(false)
const editingSupplier = ref(null)

const form = reactive({
  name: '',
  cuit: '',
  phone: '',
  email: '',
  contact: '',
})

onMounted(async () => {
  try {
    const data = await api.get('/api/proveedores')
    if (data && data.length) suppliers.value = data
  } catch { /* fallback to mock */ }
})

async function syncProveedores() {
  syncing.value = true
  try {
    const data = await api.get('/api/proveedores')
    if (data && data.length) suppliers.value = data
  } catch { /* fallback to mock */ }
  syncing.value = false
}

function openCreateModal() {
  editingSupplier.value = null
  form.name = ''
  form.cuit = ''
  form.phone = ''
  form.email = ''
  form.contact = ''
  showModal.value = true
}

function openEditModal(supplier) {
  editingSupplier.value = supplier
  form.name = supplier.name
  form.cuit = supplier.cuit
  form.phone = supplier.phone
  form.email = supplier.email
  form.contact = supplier.contact
  showModal.value = true
}

async function saveSupplier() {
  saving.value = true
  if (editingSupplier.value) {
    Object.assign(editingSupplier.value, { ...form })
  } else {
    suppliers.value.push({
      id: suppliers.value.length + 1,
      ...form,
      active: true,
    })
  }
  showModal.value = false
  saving.value = false
}

async function toggleActive(supplier) {
  togglingId.value = supplier.id
  supplier.active = !supplier.active
  togglingId.value = null
}
</script>
