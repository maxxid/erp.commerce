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
        <p class="text-2xl font-mono-data font-bold text-emerald-600 mt-1">{{ suppliers.filter(s => s.activo).length }}</p>
      </BaseCard>
      <BaseCard padding="md">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Inactivos</p>
        <p class="text-2xl font-mono-data font-bold text-red-500 mt-1">{{ suppliers.filter(s => !s.activo).length }}</p>
      </BaseCard>
      <BaseCard padding="md">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Último agregado</p>
        <p class="text-sm font-medium text-slate-900 mt-1 truncate">{{ ultimoAgregado?.nombre || '—' }}</p>
      </BaseCard>
    </div>

    <BaseCard padding="none">
      <BaseTable
        :columns="columns"
        :rows="suppliers"
        :loading="loading"
      >
        <template #nombre="{ row }">
          <span class="font-medium text-slate-900">{{ row.nombre }}</span>
        </template>
        <template #cuit="{ row }">
          <span class="font-mono-data text-slate-700">{{ row.cuit || '—' }}</span>
        </template>
        <template #telefono="{ row }">
          <span class="text-slate-600">{{ row.telefono || '—' }}</span>
        </template>
        <template #email="{ row }">
          <a v-if="row.email" :href="'mailto:' + row.email" class="text-brand-600 hover:underline">{{ row.email }}</a>
          <span v-else class="text-slate-400">—</span>
        </template>
        <template #nombre_contacto="{ row }">
          <span class="text-slate-600">{{ row.nombre_contacto || '—' }}</span>
        </template>
        <template #activo="{ row }">
          <BaseBadge
            :variant="row.activo ? 'success' : 'danger'"
            size="sm"
            dot
          >
            {{ row.activo ? 'Activo' : 'Inactivo' }}
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
              <i v-else :class="row.activo ? 'fa-solid fa-circle-xmark' : 'fa-solid fa-circle-check'"></i>
            </BaseButton>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal
      :model-value="showModal"
      :title="editingSupplier ? 'Editar proveedor' : 'Nuevo proveedor'"
      size="lg"
      @update:model-value="showModal = $event"
    >
      <form @submit.prevent="saveSupplier" class="space-y-4">
        <BaseInput
          v-model="form.nombre"
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
        />
        <BaseInput
          v-model="form.telefono"
          label="Teléfono"
          type="text"
          placeholder="+54 11 1234-5678"
        />
        <BaseInput
          v-model="form.email"
          label="Email"
          type="email"
          placeholder="email@proveedor.com"
        />
        <BaseInput
          v-model="form.nombre_contacto"
          label="Persona de contacto"
          type="text"
          placeholder="Nombre del contacto"
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
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'

const toast = useToastStore()

const syncing = ref(false)
const saving = ref(false)
const togglingId = ref(null)
const loading = ref(true)

const suppliers = ref([])

const columns = [
  { key: 'nombre', label: 'Nombre' },
  { key: 'cuit', label: 'CUIT' },
  { key: 'telefono', label: 'Teléfono' },
  { key: 'email', label: 'Email' },
  { key: 'nombre_contacto', label: 'Contacto' },
  { key: 'activo', label: 'Estado' },
  { key: 'actions', label: 'Acciones' },
]

const showModal = ref(false)
const editingSupplier = ref(null)

const form = reactive({
  nombre: '',
  cuit: '',
  telefono: '',
  email: '',
  nombre_contacto: '',
})

const ultimoAgregado = computed(() => {
  if (!suppliers.value.length) return null
  return suppliers.value
    .filter(s => s.created_at)
    .reduce((max, s) => !max || new Date(s.created_at) > new Date(max.created_at) ? s : max, null)
    || suppliers.value[suppliers.value.length - 1]
})

async function fetchProveedores() {
  loading.value = true
  try {
    const data = await api.get('/api/proveedores?page_size=200')
    suppliers.value = Array.isArray(data) ? data : []
  } catch (e) {
    toast.error('No se pudieron cargar los proveedores')
    suppliers.value = []
  } finally {
    loading.value = false
  }
}

async function syncProveedores() {
  syncing.value = true
  try {
    const data = await api.get('/api/proveedores?page_size=200')
    suppliers.value = Array.isArray(data) ? data : []
    toast.success(`${suppliers.value.length} proveedor(es) sincronizados`)
  } catch (e) {
    toast.error('No se pudieron sincronizar los proveedores')
  } finally {
    syncing.value = false
  }
}

onMounted(fetchProveedores)

function openCreateModal() {
  editingSupplier.value = null
  form.nombre = ''
  form.cuit = ''
  form.telefono = ''
  form.email = ''
  form.nombre_contacto = ''
  showModal.value = true
}

function openEditModal(supplier) {
  editingSupplier.value = supplier
  form.nombre = supplier.nombre || ''
  form.cuit = supplier.cuit || ''
  form.telefono = supplier.telefono || ''
  form.email = supplier.email || ''
  form.nombre_contacto = supplier.nombre_contacto || ''
  showModal.value = true
}

async function saveSupplier() {
  if (!form.nombre.trim()) {
    toast.error('El nombre es obligatorio')
    return
  }
  saving.value = true
  try {
    const payload = {
      nombre: form.nombre.trim(),
      cuit: form.cuit.trim() || null,
      telefono: form.telefono.trim() || null,
      email: form.email.trim() || null,
      nombre_contacto: form.nombre_contacto.trim() || null,
    }
    if (editingSupplier.value) {
      const updated = await api.put(`/api/proveedores/${editingSupplier.value.id}`, payload)
      const idx = suppliers.value.findIndex(s => s.id === editingSupplier.value.id)
      if (idx !== -1) suppliers.value[idx] = { ...suppliers.value[idx], ...updated }
      toast.success('Proveedor actualizado')
    } else {
      const created = await api.post('/api/proveedores', payload)
      suppliers.value.push(created)
      toast.success(`Proveedor "${created.nombre}" creado`)
    }
    showModal.value = false
  } catch (e) {
    toast.error(e?.response?.data?.detail || e?.data?.detail || e.message || 'Error al guardar proveedor')
  } finally {
    saving.value = false
  }
}

async function toggleActive(supplier) {
  togglingId.value = supplier.id
  try {
    const updated = await api.put(`/api/proveedores/${supplier.id}`, { activo: !supplier.activo })
    const idx = suppliers.value.findIndex(s => s.id === supplier.id)
    if (idx !== -1) suppliers.value[idx] = { ...suppliers.value[idx], ...updated }
  } catch (e) {
    toast.error(e?.response?.data?.detail || e?.data?.detail || e.message || 'Error al cambiar estado')
  } finally {
    togglingId.value = null
  }
}
</script>
