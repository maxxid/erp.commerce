<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Usuarios</h2>
        <p class="text-sm text-slate-500 mt-1">Administración de usuarios del sistema</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="openCreateModal"
          class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-2xl shadow-sm font-medium transition-colors flex items-center gap-2"
        >
          <i class="fa-solid fa-user-plus text-sm"></i>
          Nuevo usuario
        </button>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-50 border-b border-gray-200">
            <tr>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Usuario</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Nombre</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Rol</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Estado</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Último acceso</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="user in users" :key="user.id" class="hover:bg-slate-50 transition-colors">
              <td class="px-5 py-4">
                <div class="flex items-center gap-3">
                  <div class="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-xs font-semibold text-slate-500">
                    {{ user.name.charAt(0).toUpperCase() }}
                  </div>
                  <span class="font-medium text-slate-900">{{ user.username }}</span>
                </div>
              </td>
              <td class="px-5 py-4 text-slate-700">{{ user.name }}</td>
              <td class="px-5 py-4">
                <span
                  class="inline-flex px-2.5 py-1 rounded-full text-xs font-medium"
                  :class="roleClass(user.role)"
                >
                  <i :class="roleIcon(user.role)" class="mr-1"></i>
                  {{ user.role }}
                </span>
              </td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" :class="user.active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'">
                  <span class="w-1.5 h-1.5 rounded-full" :class="user.active ? 'bg-green-500 animate-pulse' : 'bg-red-500'"></span>
                  {{ user.active ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="px-5 py-4 text-slate-500 text-xs">{{ user.lastAccess }}</td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <button
                    @click="openEditModal(user)"
                    class="text-slate-400 hover:text-brand-600 transition-colors"
                    title="Editar"
                  >
                    <i class="fa-solid fa-pen-to-square"></i>
                  </button>
                  <button
                    v-if="user.active"
                    :disabled="toggling[user.id]"
                    @click="toggleUser(user)"
                    class="text-slate-400 hover:text-red-600 transition-colors disabled:opacity-50"
                    title="Desactivar"
                  >
                    <i :class="toggling[user.id] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-circle-xmark'"></i>
                  </button>
                  <button
                    v-else
                    :disabled="toggling[user.id]"
                    @click="toggleUser(user)"
                    class="text-slate-400 hover:text-green-600 transition-colors disabled:opacity-50"
                    title="Activar"
                  >
                    <i :class="toggling[user.id] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-circle-check'"></i>
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
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 class="text-lg font-semibold text-slate-900">{{ editingUser ? 'Editar usuario' : 'Nuevo usuario' }}</h2>
            <button @click="showModal = false" class="text-slate-400 hover:text-slate-600 transition-colors">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <form @submit.prevent="saveUser" class="px-6 py-5 space-y-4">
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Usuario</label>
              <input v-model="form.username" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="nombre.apellido" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Nombre completo</label>
              <input v-model="form.name" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="Nombre y apellido" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Contraseña</label>
              <input v-model="form.password" type="password" class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" :placeholder="editingUser ? 'Dejar vacío para mantener' : 'Ingresar contraseña'" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Rol</label>
              <select v-model="form.role" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all">
                <option value="">Seleccionar rol</option>
                <option value="Admin">Administrador</option>
                <option value="Encargado">Encargado</option>
                <option value="Cajero">Cajero</option>
                <option value="Repositor">Repositor</option>
              </select>
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
            class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl shadow-sm font-medium transition-colors text-sm flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : editingUser ? 'fa-solid fa-check' : 'fa-solid fa-plus'"></i>
            {{ saving ? 'Guardando...' : editingUser ? 'Guardar cambios' : 'Crear usuario' }}
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
import api from '@/services/api'
import { formatCurrency } from '@/composables/useUtils'

const users = ref([
  { id: 1, username: 'admin.sistema', name: 'Administrador Sistema', role: 'admin', active: true, lastAccess: '2026-06-20 18:45' },
  { id: 2, username: 'maria.gomez', name: 'María Gómez', role: 'encargado', active: true, lastAccess: '2026-06-20 16:30' },
  { id: 3, username: 'carlos.lopez', name: 'Carlos López', role: 'cajero', active: true, lastAccess: '2026-06-20 14:15' },
  { id: 4, username: 'laura.diaz', name: 'Laura Díaz', role: 'cajero', active: true, lastAccess: '2026-06-20 12:00' },
  { id: 5, username: 'pedro.sanchez', name: 'Pedro Sánchez', role: 'repositor', active: false, lastAccess: '2026-06-10 09:20' },
  { id: 6, username: 'ana.ruiz', name: 'Ana Ruiz', role: 'encargado', active: true, lastAccess: '2026-06-19 20:30' },
  { id: 7, username: 'jorge.fernandez', name: 'Jorge Fernández', role: 'repositor', active: true, lastAccess: '2026-06-20 08:00' },
])

const showModal = ref(false)
const editingUser = ref(null)
const saving = ref(false)
const toggling = ref({})

const form = reactive({
  username: '',
  name: '',
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
  form.name = ''
  form.password = ''
  form.role = ''
  showModal.value = true
}

function openEditModal(user) {
  editingUser.value = user
  form.username = user.username
  form.name = user.name
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
      editingUser.value.name = form.name
      editingUser.value.role = form.role
    } else {
      await api.post('/api/usuarios', form)
      users.value.push({
        id: users.value.length + 1,
        username: form.username,
        name: form.name,
        role: form.role,
        active: true,
        lastAccess: '—',
      })
    }
  } catch {
    if (editingUser.value) {
      editingUser.value.username = form.username
      editingUser.value.name = form.name
      editingUser.value.role = form.role
    } else {
      users.value.push({
        id: users.value.length + 1,
        username: form.username,
        name: form.name,
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

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1.5s linear infinite;
}
</style>
