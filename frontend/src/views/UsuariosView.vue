<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-slate-500 dark:text-slate-400">Gestión de usuarios del sistema</p>
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
        <template #lastAccess="{ row }">
          <span class="text-xs text-slate-500 dark:text-slate-400">
            {{ row.lastAccess ? formatFechaHora(row.lastAccess) : '—' }}
          </span>
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
              v-if="!esAdminProtegido(row)"
              variant="ghost"
              size="sm"
              iconOnly
              :loading="toggling[row.id]"
              :title="row.active ? 'Desactivar' : 'Activar'"
              :aria-label="row.active ? 'Desactivar' : 'Activar'"
              @click="toggleUser(row)"
            >
              <i
                :class="row.active
                  ? 'fa-solid fa-circle-xmark text-red-600'
                  : 'fa-solid fa-circle-check text-green-600'"
              ></i>
            </BaseButton>
            <span
              v-else
              class="text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase px-1"
              title="Un Administrador no se puede desactivar"
            >
              <i class="fa-solid fa-lock mr-1"></i>Protegido
            </span>
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
          v-model="form.rol"
          label="Rol"
          required
          placeholder="Seleccionar rol"
          :options="[
            { value: 'admin', label: 'Administrador' },
            { value: 'encargado', label: 'Encargado' },
            { value: 'cajero', label: 'Cajero' },
            { value: 'repositor', label: 'Repositor' }
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
import { useToastStore } from '@/stores/toasts'
import { formatDateTime } from '@/composables/useUtils'
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
const toast = useToastStore()

// El backend manda { rol, activo, ultimo_login } y la vista usa
// { role, active, lastAccess }.
function aFila(u) {
  return {
    id: u.id,
    username: u.username,
    nombre: u.nombre,
    role: u.rol,
    active: !!u.activo,
    lastAccess: u.ultimo_login || null,
  }
}

function formatFechaHora(fecha) {
  return fecha ? formatDateTime(fecha) : '—'
}

const form = reactive({
  username: '',
  nombre: '',
  password: '',
  rol: '',
})

function roleIcon(role) {
  const map = { admin: 'fa-solid fa-shield-halved', encargado: 'fa-solid fa-user-tie', cajero: 'fa-solid fa-calculator', repositor: 'fa-solid fa-box' }
  return map[role] || 'fa-solid fa-user'
}

function openCreateModal() {
  editingUser.value = null
  form.username = ''
  form.nombre = ''
  form.password = ''
  form.rol = ''
  showModal.value = true
}

function openEditModal(user) {
  editingUser.value = user
  form.username = user.username
  form.nombre = user.nombre
  form.password = ''
  form.rol = user.role
  showModal.value = true
}

// El admin no se desactiva (ni propio ni ajeno): lo decide el backend y acá
// se oculta la acción para que no parezca que falta.
function esAdminProtegido(user) {
  return (user.role || '').toLowerCase() === 'admin'
}

async function saveUser() {
  saving.value = true
  try {
    // La clave solo viaja si se escribió una nueva: mandarla vacía hacía que el
    // backend la rechace y la edición entera fallara.
    const payload = { nombre: form.nombre, rol: form.rol }
    if (form.password) payload.password = form.password
    if (editingUser.value) {
      const resp = await api.put(`/api/usuarios/${editingUser.value.id}`, payload)
      if (resp && resp.id) Object.assign(editingUser.value, aFila(resp))
    } else {
      const resp = await api.post('/api/usuarios', { ...payload, username: form.username })
      if (resp && resp.id) users.value.push(aFila(resp))
    }
  } catch (e) {
    toast.error(e.message || 'No se pudo guardar el usuario')
    saving.value = false
    return
  }
  saving.value = false
  showModal.value = false
}

async function toggleUser(user) {
  if (esAdminProtegido(user)) return
  toggling.value[user.id] = true
  try {
    // Mandamos el estado que queremos, no "niega": dos clicks rápidos sobre la
    // misma fila terminaban dejando al usuario como estaba al principio.
    const resp = await api.patch(`/api/usuarios/${user.id}/toggle`, { activo: !user.active })
    if (resp && typeof resp.activo === 'boolean') user.active = resp.activo
    toast.success(resp?.message || 'Usuario actualizado')
  } catch (e) {
    toast.error(e.message || 'No se pudo cambiar el estado')
  }
  toggling.value[user.id] = false
}

onMounted(async () => {
  try {
    const data = await api.get('/api/usuarios', { solo_activos: false, page_size: 200 })
    if (data && data.length) users.value = data.map(aFila)
  } catch { /* fallback to mock */ }
})
</script>
