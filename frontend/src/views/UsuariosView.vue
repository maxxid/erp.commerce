<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between gap-3 flex-wrap">
      <div>
        <p class="text-sm text-slate-500 dark:text-slate-400">Gestión de usuarios del sistema</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton variant="secondary" size="md" @click="abrirMatriz">
          <i class="fa-solid fa-shield-halved text-sm"></i>
          Qué puede hacer cada rol
        </BaseButton>
        <BaseButton variant="primary" size="md" @click="openCreateModal">
          <i class="fa-solid fa-user-plus text-sm"></i>
          Nuevo usuario
        </BaseButton>
      </div>
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
        <template #permisos="{ row }">
          <span v-if="row.role === 'admin'" class="text-xs text-slate-400 dark:text-slate-500">
            Tiene todo
          </span>
          <div v-else-if="row.permisos.length" class="flex flex-wrap gap-1">
            <BaseBadge
              v-for="clave in row.permisos"
              :key="clave"
              variant="info"
              size="sm"
            >
              {{ etiquetaPermiso(clave) }}
            </BaseBadge>
          </div>
          <span v-else class="text-xs text-slate-400 dark:text-slate-500">—</span>
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

        <!-- Permisos especiales: pases sueltos que se le dan a una persona
             puntual sin tener que cambiarle el rol. El dueño no necesita
             ninguno porque ya tiene todo. -->
        <div
          v-if="permisosDisponibles.length"
          class="rounded-xl border border-slate-200 dark:border-slate-700 p-3 space-y-2.5"
        >
          <p class="text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
            <i class="fa-solid fa-key mr-1.5"></i>Permisos especiales
          </p>
          <p v-if="form.rol === 'admin'" class="text-[11px] text-slate-500 dark:text-slate-400">
            El Administrador ya tiene todo: estos permisos no le suman nada.
          </p>
          <label
            v-for="p in permisosDisponibles"
            :key="p.clave"
            class="flex items-start gap-2.5 text-sm text-slate-700 dark:text-slate-300"
            :class="form.rol === 'admin' ? 'opacity-50' : 'cursor-pointer'"
          >
            <input
              type="checkbox"
              class="mt-1"
              :checked="form.permisos.includes(p.clave)"
              :disabled="form.rol === 'admin'"
              @change="togglePermiso(p.clave)"
            />
            <span>
              <span class="font-medium">{{ p.etiqueta }}</span>
              <span class="block text-[11px] text-slate-500 dark:text-slate-400">{{ p.descripcion }}</span>
            </span>
          </label>
        </div>

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

    <!-- La matriz en modo lectura, desde el mismo lugar que decide los
         permisos del backend: si alguien agrega una pantalla y no la anota
         ahí, se ve acá antes de que sorprenda a alguien en el mostrador. -->
    <BaseModal v-model="showMatriz" title="Qué puede hacer cada rol" size="4xl">
      <div v-if="cargandoMatriz" class="py-12 text-center text-sm text-slate-500 dark:text-slate-400">
        <i class="fa-solid fa-circle-notch animate-spin"></i>
        Cargando...
      </div>

      <div v-else class="space-y-5">
        <p class="text-sm text-slate-500 dark:text-slate-400">
          Esta lista es la que usa el sistema, no una copia. Los
          <strong class="font-semibold text-slate-700 dark:text-slate-300">permisos especiales</strong>
          son pases sueltos: se le pueden dar a una persona puntual desde
          "Nuevo usuario" o "Editar" sin cambiarle el rol. El dueño tiene todo
          siempre.
        </p>

        <div
          v-for="area in areasMatriz"
          :key="area.area"
          class="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden"
        >
          <p class="px-3 py-2 bg-slate-50 dark:bg-slate-800/60 text-xs font-bold uppercase tracking-wider text-slate-600 dark:text-slate-300">
            <i :class="area.icono" class="mr-1.5"></i>{{ area.area }}
          </p>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500">
                  <th class="text-left font-semibold px-3 py-2">Acción</th>
                  <th
                    v-for="r in rolesMatriz"
                    :key="r.clave"
                    class="w-16 font-semibold px-1 py-2 text-center whitespace-nowrap"
                    :title="r.etiqueta"
                  >
                    {{ rolCorto(r.clave) }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="a in area.acciones"
                  :key="a.accion"
                  class="border-t border-slate-100 dark:border-slate-800"
                >
                  <td class="px-3 py-2 text-slate-700 dark:text-slate-300">
                    {{ a.accion }}
                    <i
                      v-if="a.permiso"
                      class="fa-solid fa-key ml-1 text-[10px] text-amber-500"
                      :title="'También se lo puede dar a una persona puntual: ' + etiquetaPermiso(a.permiso)"
                    ></i>
                  </td>
                  <td v-for="r in rolesMatriz" :key="r.clave" class="text-center px-1 py-2">
                    <i v-if="a.roles.includes(r.clave)" class="fa-solid fa-check text-green-600"></i>
                    <i
                      v-else-if="a.permiso"
                      class="fa-solid fa-minus text-slate-300 dark:text-slate-600"
                      title="Solo con el permiso especial"
                    ></i>
                    <i v-else class="fa-solid fa-xmark text-slate-200 dark:text-slate-700"></i>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
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
  { key: 'permisos', label: 'Permisos extra' },
  { key: 'active', label: 'Estado' },
  { key: 'lastAccess', label: 'Último acceso' },
  { key: 'actions', label: 'Acciones' }
]

const users = ref([
   { id: 1, username: 'admin.sistema', nombre: 'Administrador Sistema', role: 'admin', permisos: [], active: true, lastAccess: '2026-06-20 18:45' },
   { id: 2, username: 'maria.gomez', nombre: 'María Gómez', role: 'encargado', permisos: [], active: true, lastAccess: '2026-06-20 16:30' },
   { id: 3, username: 'carlos.lopez', nombre: 'Carlos López', role: 'cajero', permisos: [], active: true, lastAccess: '2026-06-20 14:15' },
   { id: 4, username: 'laura.diaz', nombre: 'Laura Díaz', role: 'cajero', permisos: [], active: true, lastAccess: '2026-06-20 12:00' },
   { id: 5, username: 'pedro.sanchez', nombre: 'Pedro Sánchez', role: 'repositor', permisos: [], active: false, lastAccess: '2026-06-10 09:20' },
   { id: 6, username: 'ana.ruiz', nombre: 'Ana Ruiz', role: 'encargado', permisos: [], active: true, lastAccess: '2026-06-19 20:30' },
   { id: 7, username: 'jorge.fernandez', nombre: 'Jorge Fernández', role: 'repositor', permisos: [], active: true, lastAccess: '2026-06-20 08:00' },
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
    permisos: Array.isArray(u.permisos) ? u.permisos : [],
    active: !!u.activo,
    lastAccess: u.ultimo_login || null,
  }
}

// La matriz de permisos viene del backend desde un solo lugar
// (app/auth/permisos.py): no se copia acá para que no se pueda desincronizar.
const matriz = ref(null)
const showMatriz = ref(false)
const cargandoMatriz = ref(false)

const rolesMatriz = computed(() => matriz.value?.roles || [])
const permisosDisponibles = computed(() => matriz.value?.permisos_especiales || [])
const areasMatriz = computed(() => matriz.value?.matriz || [])

async function cargarMatriz() {
  if (matriz.value || cargandoMatriz.value) return
  cargandoMatriz.value = true
  try {
    const data = await api.get('/api/permisos')
    if (data) matriz.value = data
  } catch {
    toast.error('No se pudo cargar la lista de permisos')
  }
  cargandoMatriz.value = false
}

function abrirMatriz() {
  showMatriz.value = true
  cargarMatriz()
}

function etiquetaPermiso(clave) {
  return permisosDisponibles.value.find(p => p.clave === clave)?.etiqueta || clave
}

function rolCorto(clave) {
  return { admin: 'Dueño', encargado: 'Encarg.', cajero: 'Cajero', repositor: 'Repos.' }[clave] || clave
}

function formatFechaHora(fecha) {
  return fecha ? formatDateTime(fecha) : '—'
}

const form = reactive({
  username: '',
  nombre: '',
  password: '',
  rol: '',
  permisos: [],
})

function togglePermiso(clave) {
  const i = form.permisos.indexOf(clave)
  if (i >= 0) form.permisos.splice(i, 1)
  else form.permisos.push(clave)
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
  form.rol = ''
  form.permisos = []
  showModal.value = true
}

function openEditModal(user) {
  editingUser.value = user
  form.username = user.username
  form.nombre = user.nombre
  form.password = ''
  form.rol = user.role
  form.permisos = [...(user.permisos || [])]
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
    const payload = {
      nombre: form.nombre,
      rol: form.rol,
      // Al dueño no se le guardan permisos sueltos: ya tiene todo, y dejarle
      // unos cargados en la base es ruido para el próximo que lo mire.
      permisos: form.rol === 'admin' ? [] : [...form.permisos],
    }
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
  cargarMatriz()
  try {
    const data = await api.get('/api/usuarios', { solo_activos: false, page_size: 200 })
    if (data && data.length) users.value = data.map(aFila)
  } catch { /* fallback to mock */ }
})
</script>
