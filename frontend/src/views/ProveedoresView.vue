<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Proveedores</h1>
        <p class="text-sm text-slate-500 mt-1">Gestión de proveedores de mercadería</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton
          variant="secondary"
          size="md"
          :loading="syncing"
          :disabled="syncing"
          @click="syncProveedores"
          title="Sincronizar proveedores"
        >
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-sync'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
        <BaseButton
          variant="primary"
          size="md"
          @click="openCreateModal"
        >
          <i class="fa-solid fa-plus text-sm"></i>
          Nuevo proveedor
        </BaseButton>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <BaseCard padding="md">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Total proveedores</p>
        <p class="text-2xl font-mono-data font-bold text-slate-900 mt-1">{{ suppliers.length }}</p>
      </BaseCard>
      <BaseCard padding="md">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Activos</p>
        <p class="text-2xl font-mono-data font-bold text-emerald-600 mt-1">{{ suppliers.filter(s => s.active).length }}</p>
      </BaseCard>
      <BaseCard padding="md">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Inactivos</p>
        <p class="text-2xl font-mono-data font-bold text-red-500 mt-1">{{ suppliers.filter(s => !s.active).length }}</p>
      </BaseCard>
      <BaseCard padding="md">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Último agregado</p>
        <p class="text-sm font-medium text-slate-900 mt-1 truncate">{{ suppliers[suppliers.length - 1]?.name || '—' }}</p>
      </BaseCard>
    </div>

    <BaseCard padding="none">
      <BaseTable
        :columns="columns"
        :rows="suppliers"
        :loading="false"
      >
        <template #name="{ row }">
          <span class="font-medium text-slate-900">{{ row.name }}</span>
        </template>
        <template #cuit="{ row }">
          <span class="font-mono-data text-slate-700">{{ row.cuit }}</span>
        </template>
        <template #phone="{ row }">
          <span class="text-slate-600">{{ row.phone }}</span>
        </template>
        <template #email="{ row }">
          <a :href="'mailto:' + row.email" class="text-brand-600 hover:underline">{{ row.email }}</a>
        </template>
        <template #contact="{ row }">
          <span class="text-slate-600">{{ row.contact }}</span>
        </template>
        <template #active="{ row }">
          <BaseBadge
            :variant="row.active ? 'success' : 'danger'"
            size="sm"
            dot
          >
            {{ row.active ? 'Activo' : 'Inactivo' }}
          </BaseBadge>
        </template>
        <template #actions="{ row }">
          <div class="flex items-center gap-2">
            <BaseButton
              variant="ghost"
              size="sm"
              icon-only
              @click="openEditModal(row)"
              title="Editar"
            >
              <i class="fa-solid fa-pen-to-square"></i>
            </BaseButton>
            <BaseButton
              variant="ghost"
              size="sm"
              icon-only
              :loading="togglingId === row.id"
              :disabled="togglingId === row.id"
              @click="toggleActive(row)"
              title="Cambiar estado"
            >
              <i v-if="togglingId === row.id" class="fa-solid fa-circle-notch animate-spin"></i>
              <i v-else :class="row.active ? 'fa-solid fa-circle-xmark' : 'fa-solid fa-circle-check'"></i>
            </BaseButton>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal
      v-model="showModal"
      :title="editingSupplier ? 'Editar proveedor' : 'Nuevo proveedor'"
      size="lg"
      @close="showModal = false"
    >
      <form @submit.prevent="saveSupplier" class="space-y-4">
        <BaseInput
          v-model="form.name"
          label="Nombre / Razón social"
          type="text"
          placeholder="Nombre del proveedor"
          required
        />
        <BaseInput
          v-model="form.cuit"
          label="CUIT"
          type="text"
          placeholder="XX-XXXXXXXX-X"
          input-class="font-mono-data"
          required
        />
        <BaseInput
          v-model="form.phone"
          label="Teléfono"
          type="text"
          placeholder="+54 11 1234-5678"
          required
        />
        <BaseInput
          v-model="form.email"
          label="Email"
          type="email"
          placeholder="email@proveedor.com"
          required
        />
        <BaseInput
          v-model="form.contact"
          label="Persona de contacto"
          type="text"
          placeholder="Nombre del contacto"
          required
        />
        <div class="flex justify-end gap-3 pt-2">
          <BaseButton
            type="button"
            variant="secondary"
            size="md"
            @click="showModal = false"
          >
            Cancelar
          </BaseButton>
          <BaseButton
            type="submit"
            variant="primary"
            size="md"
            :loading="saving"
            :disabled="saving"
          >
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : editingSupplier ? 'fa-solid fa-check' : 'fa-solid fa-plus'"></i>
            {{ saving ? 'Guardando...' : editingSupplier ? 'Guardar cambios' : 'Crear proveedor' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { formatCurrency } from '@/composables/useUtils'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

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

const columns = [
  { key: 'name', label: 'Nombre' },
  { key: 'cuit', label: 'CUIT' },
  { key: 'phone', label: 'Teléfono' },
  { key: 'email', label: 'Email' },
  { key: 'contact', label: 'Contacto' },
  { key: 'active', label: 'Estado' },
  { key: 'actions', label: 'Acciones' },
]

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
