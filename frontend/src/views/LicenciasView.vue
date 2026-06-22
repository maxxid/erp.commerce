<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Licencias</h1>
        <p class="text-sm text-slate-500 mt-1">Gestión de licencias del sistema</p>
      </div>
      <button
        @click="openGenerateModal"
        class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-2xl shadow-sm font-medium transition-colors flex items-center gap-2"
      >
        <i class="fa-solid fa-key text-sm"></i>
        Generar licencia
      </button>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Licencias totales</p>
        <p class="text-2xl font-mono-data font-bold text-slate-900 mt-1">{{ licenses.length }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Licencias activas</p>
        <p class="text-2xl font-mono-data font-bold text-emerald-600 mt-1">{{ licenses.filter(l => l.active).length }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Próximas a vencer (30d)</p>
        <p class="text-2xl font-mono-data font-bold text-amber-600 mt-1">{{ licenses.filter(l => l.daysUntilExpiry <= 30 && l.active).length }}</p>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-slate-50 border-b border-slate-200">
            <tr>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Clave</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Cliente</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">ID Máquina</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Vencimiento</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Días restantes</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Estado</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="lic in licenses" :key="lic.id" class="hover:bg-slate-50 transition-colors" :class="lic.daysUntilExpiry <= 7 && lic.active ? 'bg-rose-50/30' : ''">
              <td class="px-5 py-4">
                <code class="font-mono-data text-xs bg-slate-100 px-2 py-1 rounded-md text-slate-700">{{ lic.clave || lic.key }}</code>
              </td>
              <td class="px-5 py-4 font-medium text-slate-900">{{ lic.client || lic.cliente }}</td>
              <td class="px-5 py-4 font-mono-data text-slate-600 text-xs">{{ lic.machineId }}</td>
              <td class="px-5 py-4 text-slate-600">{{ lic.expirationDate }}</td>
              <td class="px-5 py-4">
                <span class="font-mono-data text-sm font-semibold" :class="lic.daysUntilExpiry <= 7 ? 'text-red-600' : lic.daysUntilExpiry <= 30 ? 'text-amber-600' : 'text-slate-700'">
                  {{ lic.daysUntilExpiry }} días
                </span>
              </td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" :class="lic.active ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'">
                  <span class="w-1.5 h-1.5 rounded-full" :class="lic.active ? 'bg-emerald-500' : 'bg-rose-500'"></span>
                  {{ lic.active ? 'Activa' : 'Inactiva' }}
                </span>
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <button
                    v-if="!lic.active"
                    :disabled="activatingId === lic.id"
                    @click="activateLicense(lic)"
                    class="text-emerald-600 hover:text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors disabled:opacity-50 flex items-center gap-1.5"
                    title="Activar"
                  >
                    <i :class="activatingId === lic.id ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-circle-check'"></i>
                    {{ activatingId === lic.id ? 'Activando...' : 'Activar' }}
                  </button>
                  <button
                    v-if="lic.active"
                    :disabled="toggling[lic.id]"
                    @click="deactivateLicense(lic)"
                    class="text-slate-400 hover:text-red-600 transition-colors text-xs disabled:opacity-50"
                    title="Desactivar"
                  >
                    <i :class="toggling[lic.id] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-circle-xmark'"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showGenerateModal" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showGenerateModal = false"></div>
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
          <div class="flex items-center justify-between px-6 py-4 border-b border-slate-100">
            <h2 class="text-lg font-semibold text-slate-900">Generar nueva licencia</h2>
            <button @click="showGenerateModal = false" class="text-slate-400 hover:text-slate-600 transition-colors">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <form @submit.prevent="generateLicense" class="px-6 py-5 space-y-4">
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Nombre del cliente</label>
              <input v-model="genForm.client" type="text" required class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="Nombre del cliente" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">ID de máquina</label>
              <input v-model="genForm.machineId" type="text" required class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="MACHINE-XXXX-XXXX" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-1">Duración (días)</label>
              <select v-model.number="genForm.days" required class="w-full border border-slate-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all">
                <option value="30">30 días</option>
                <option value="90">90 días</option>
                <option value="180">180 días</option>
                <option value="365">365 días (1 año)</option>
                <option value="730">730 días (2 años)</option>
              </select>
            </div>

            <div v-if="generatedKey" class="bg-emerald-50 border border-emerald-200 rounded-xl p-4 space-y-2">
              <p class="text-[10px] uppercase tracking-wider text-emerald-700 font-semibold">Clave generada</p>
              <code
                class="block w-full font-mono-data text-lg font-bold text-emerald-900 bg-white border border-emerald-100 rounded-lg px-3 py-2 select-all cursor-pointer break-all"
                @click="copyKey"
                title="Clic para copiar"
              >{{ generatedKey }}</code>
              <p class="text-[10px] text-emerald-600">Clic en la clave para copiarla</p>
            </div>

            <div class="flex justify-end gap-3 pt-2">
              <button
                type="button"
                @click="showGenerateModal = false"
                class="px-5 py-2.5 text-sm font-medium text-slate-600 bg-slate-100 rounded-xl hover:bg-slate-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                v-if="!generatedKey"
                type="submit"
                :disabled="generating"
                class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl shadow-sm font-medium transition-colors text-sm flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <i :class="generating ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-wand-magic-sparkles text-xs'"></i>
                {{ generating ? 'Generando...' : 'Generar' }}
              </button>
              <button
                v-else
                type="button"
                @click="showGenerateModal = false; generatedKey = ''"
                class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl shadow-sm font-medium transition-colors text-sm"
              >
                Listo
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
import { useToastStore } from '@/stores/toasts'

const toast = useToastStore()

const licenses = ref([
  { id: 1, clave: 'LIC-A7B3-9F2C-4D8E', client: 'Supermercado La Esquina', machineId: 'MACH-1928-3F4A', expirationDate: '2026-12-31', daysUntilExpiry: 194, active: true },
  { id: 2, clave: 'LIC-C2D9-1E5F-8A3B', client: 'Distribuidora Norte SRL', machineId: 'MACH-3847-9B2C', expirationDate: '2026-09-15', daysUntilExpiry: 87, active: true },
  { id: 3, clave: 'LIC-E5F8-7B1D-3C9A', client: 'Carnicería Don Pedro', machineId: 'MACH-5561-7D3E', expirationDate: '2026-07-01', daysUntilExpiry: 11, active: true },
  { id: 4, clave: 'LIC-9G2H-4I6J-1K8L', client: 'Almacén El Gaucho', machineId: 'MACH-7739-1F5B', expirationDate: '2026-06-25', daysUntilExpiry: 5, active: true },
  { id: 5, clave: 'LIC-M3N5-8O7P-2Q9R', client: 'Kiosco 24hs Centro', machineId: 'MACH-1029-6A4D', expirationDate: '2026-04-15', daysUntilExpiry: -66, active: false },
  { id: 6, clave: 'LIC-S6T8-1U2V-5W3X', client: 'Librería Papel y Tinta', machineId: 'MACH-8821-4C8F', expirationDate: '2027-03-10', daysUntilExpiry: 263, active: true },
])

const showGenerateModal = ref(false)
const generating = ref(false)
const generatedKey = ref('')
const activatingId = ref(null)
const toggling = ref({})

const genForm = reactive({
  client: '',
  machineId: '',
  days: 30,
})

function openGenerateModal() {
  genForm.client = ''
  genForm.machineId = ''
  genForm.days = 30
  generatedKey.value = ''
  showGenerateModal.value = true
}

async function generateLicense() {
  generating.value = true
  try {
    const resp = await api.post('/api/licencia/generar', {
      cliente: genForm.client,
      machine_id: genForm.machineId,
      dias: genForm.days,
    })
    generatedKey.value = resp.clave
    toast.add('success', 'Licencia generada correctamente')
    await loadLicenses()
  } catch (e) {
    toast.add('error', e.message || 'Error al generar licencia')
  }
  generating.value = false
}

async function activateLicense(lic) {
  activatingId.value = lic.id
  try {
    await api.post('/api/licencia/activar', { clave: lic.clave || lic.key })
    lic.active = true
    toast.add('success', 'Licencia activada correctamente')
  } catch (e) {
    toast.add('error', e.message || 'Error al activar licencia')
  }
  activatingId.value = null
}

async function deactivateLicense(lic) {
  toggling.value[lic.id] = true
  try {
    await api.patch(`/api/licencia/${lic.id}/toggle`, { active: false })
  } catch { /* fallback */ }
  lic.active = false
  toggling.value[lic.id] = false
}

function copyKey() {
  navigator.clipboard.writeText(generatedKey.value)
  toast.add('info', 'Clave copiada al portapapeles')
}

async function loadLicenses() {
  try {
    const data = await api.get('/api/licencia/historial')
    if (data && data.length) licenses.value = data
  } catch { /* fallback to mock */ }
}

onMounted(() => {
  loadLicenses()
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
