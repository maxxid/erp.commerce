<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Usuarios</h2>
        <p class="text-sm text-slate-500 mt-1">Administración de usuarios del sistema</p>
      </div>
      <BaseButton variant="primary" size="md" @click="openCreateModal">
        <i class="fa-solid fa-user-plus text-sm"></i>
        Nuevo usuario
      </BaseButton>
    </div>

    <BaseCard padding="none">
      <BaseTable :columns="columns" :rows="users">
        <template #username="{ row }">
          <div class="flex items-center gap-3">
            <div class="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-semibold text-slate-500">
              {{ (row.nombre || row.username || '??').charAt(0).toUpperCase() }}
            </div>
            <span class="font-medium text-slate-900">{{ row.username }}</span>
          </div>
        </template>
        <template #role="{ row }">
          <BaseBadge
            :variant="row.role === 'admin' ? 'brand' : row.role === 'encargado' ? 'info' : row.role === 'cajero' ? 'warning' : row.role === 'repositor' ? 'success' : 'default'"
            size="sm"
          >
            <i :class="roleIcon(row.role)" class="mr-1"></i>
            {{ row.role }}
          </BaseBadge>
        </template>
        <template #active="{ row }">
          <BaseBadge :variant="row.active ? 'success' : 'danger'" size="sm" dot :pulse="row.active">
            {{ row.active ? 'Activo' : 'Inactivo' }}
          </BaseBadge>
        </template>
        <template #actions="{ row }">
          <div class="flex items-center gap-2">
            <BaseButton
              variant="ghost"
              size="sm"
              iconOnly
              title="Editar"
              aria-label="Editar"
              @click="openEditModal(row)"
            >
              <i class="fa-solid fa-pen-to-square"></i>
            </BaseButton>
            <BaseButton
              v-if="row.active"
              variant="ghost"
              size="sm"
              iconOnly
              :loading="toggling[row.id]"
              title="Desactivar"
              aria-label="Desactivar"
              @click="toggleUser(row)"
            >
              <i class="fa-solid fa-circle-xmark text-red-600"></i>
            </BaseButton>
            <BaseButton
              v-else
              variant="ghost"
              size="sm"
              iconOnly
              :loading="toggling[row.id]"
              title="Activar"
              aria-label="Activar"
              @click="toggleUser(row)"
            >
              <i class="fa-solid fa-circle-check text-green-600"></i>
            </BaseButton>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal v-model="showModal" :title="editingUser ? 'Editar usuario' : 'Nuevo usuario'" size="md">
      <form @submit.prevent="saveUser" class="space-y-4">
        <BaseInput
          v-model="form.username"
          label="Usuario"
          type="text"
          placeholder="nombre.apellido"
          required
          input-class="font-mono-data"
        />
        <BaseInput
          v-model="form.nombre"
          label="Nombre completo"
          type="text"
          placeholder="Nombre y apellido"
          required
        />
        <BaseInput
          v-model="form.password"
          label="Contraseña"
          type="password"
          autocomplete="new-password"
          :placeholder="editingUser ? 'Dejar vacío para mantener' : 'Ingresar contraseña'"
        />
        <BaseSelect
          v-model="form.role"
          label="Rol"
          required
          placeholder="Seleccionar rol"
          :options="[
            { value: 'Admin', label: 'Administrador' },
            { value: 'Encargado', label: 'Encargado' },
            { value: 'Cajero', label: 'Cajero' },
            { value: 'Repositor', label: 'Repositor' }
          ]"
          option-value="value"
          option-label="label"
        />
        <div class="flex justify-end gap-3 pt-2">
          <BaseButton type="button" variant="secondary" @click="showModal = false">
            Cancelar
          </BaseButton>
          <BaseButton type="submit" variant="primary" :loading="saving">
            <i :class="editingUser ? 'fa-solid fa-check' : 'fa-solid fa-plus'"></i>
            {{ editingUser ? 'Guardar cambios' : 'Crear usuario' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api from '@/services/api'
import { formatCurrency } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'

const columns = [
  { key: 'username', label: 'Usuario' },
  { key: 'nombre', label: 'Nombre' },
  { key: 'role', label: 'Rol' },
  { key: 'active', label: 'Estado' },
  { key: 'lastAccess', label: 'Último acceso' },
  { key: 'actions', label: 'Acciones' }
]

const users = ref([
   { id: 1, username: 'admin.sistema', nombre: 'Administrador Sistema', role: 'admin', active: true, lastAccess: '2026-06-20 18:45' },
   { id: 2, username: 'maria.gomez', nombre: 'María Gómez', role: 'encargado', active: true, lastAccess: '2026-06-20 16:30' },
   { id: 3, username: 'carlos.lopez', nombre: 'Carlos López', role: 'cajero', active: true, lastAccess: '2026-06-20 14:15' },
   { id: 4, username: 'laura.diaz', nombre: 'Laura Díaz', role: 'cajero', active: true, lastAccess: '2026-06-20 12:00' },
   { id: 5, username: 'pedro.sanchez', nombre: 'Pedro Sánchez', role: 'repositor', active: false, lastAccess: '2026-06-10 09:20' },
   { id: 6, username: 'ana.ruiz', nombre: 'Ana Ruiz', role: 'encargado', active: true, lastAccess: '2026-06-19 20:30' },
   { id: 7, username: 'jorge.fernandez', nombre: 'Jorge Fernández', role: 'repositor', active: true, lastAccess: '2026-06-20 08:00' },
])

const showModal = ref(false)
const editingUser = ref(null)
const saving = ref(false)
const toggling = ref({})

const form = reactive({
  username: '',
  nombre: '',
  password: '',
  role: '',
})

function roleClass(role) {
  const map = { admin: 'bg-purple-50 text-purple-700', encargado: 'bg-blue-50 text-blue-700', cajero: 'bg-amber-50 text-amber-700', repositor: 'bg-teal-50 text-teal-700' }
  return map[role] || 'bg-slate-50 text-slate-700'
}

function roleIcon(role) {
  const map = { admin: 'fa-solid fa-shield-halved', encargado: 'fa-solid fa-user-tie', cajero: 'fa-solid fa-calculator', repositor: 'fa-solid fa-box' }
  return map[role] || 'fa-solid fa-user'
}

function openCreateModal() {
  editingUser.value = null
  form.username = ''
  form.nombre = ''
  form.password = ''
  form.role = ''
  showModal.value = true
}

function openEditModal(user) {
  editingUser.value = user
  form.username = user.username
  form.nombre = user.nombre
  form.password = ''
  form.role = user.role
  showModal.value = true
}

async function saveUser() {
  saving.value = true
  try {
    if (editingUser.value) {
      await api.put(`/api/usuarios/${editingUser.value.id}`, form)
      editingUser.value.username = form.username
      editingUser.value.nombre = form.nombre
      editingUser.value.role = form.role
    } else {
      await api.post('/api/usuarios', form)
      users.value.push({
        id: users.value.length + 1,
        username: form.username,
        nombre: form.nombre,
        role: form.role,
        active: true,
        lastAccess: '—',
      })
    }
  } catch {
    if (editingUser.value) {
      editingUser.value.username = form.username
      editingUser.value.nombre = form.nombre
      editingUser.value.role = form.role
    } else {
      users.value.push({
        id: users.value.length + 1,
        username: form.username,
        nombre: form.nombre,
        role: form.role,
        active: true,
        lastAccess: '—',
      })
    }
  }
  saving.value = false
  showModal.value = false
}

async function toggleUser(user) {
  toggling.value[user.id] = true
  try {
    await api.patch(`/api/usuarios/${user.id}/toggle`, { active: !user.active })
  } catch { /* fallback */ }
  user.active = !user.active
  toggling.value[user.id] = false
}
onMounted(async () => {
  try {
    const data = await api.get('/api/usuarios')
    if (data && data.length) users.value = data
  } catch { /* fallback to mock */ }
})
</script>
