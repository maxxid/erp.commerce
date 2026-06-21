<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Licencias</h1>
        <p class="text-sm text-gray-500 mt-1">Gestión de licencias del sistema</p>
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
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Licencias totales</p>
        <p class="text-2xl font-mono-data font-bold text-gray-900 mt-1">{{ licenses.length }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Licencias activas</p>
        <p class="text-2xl font-mono-data font-bold text-green-600 mt-1">{{ licenses.filter(l => l.active).length }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Próximas a vencer (30d)</p>
        <p class="text-2xl font-mono-data font-bold text-amber-600 mt-1">{{ licenses.filter(l => l.daysUntilExpiry <= 30 && l.active).length }}</p>
      </div>
    </div>

    <div class="bg-white rounded-2xl shadow-sm overflow-hidden">
      <div class="overflow-x-auto">
        <table class="w-full text-left text-sm">
          <thead class="bg-gray-50 border-b border-gray-200">
            <tr>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Clave</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Cliente</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">ID Máquina</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Vencimiento</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Días restantes</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Estado</th>
              <th class="px-5 py-3 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Acciones</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="lic in licenses" :key="lic.id" class="hover:bg-gray-50 transition-colors" :class="lic.daysUntilExpiry <= 7 && lic.active ? 'bg-red-50/30' : ''">
              <td class="px-5 py-4">
                <code class="font-mono-data text-xs bg-gray-100 px-2 py-1 rounded-md text-gray-700">{{ lic.key }}</code>
              </td>
              <td class="px-5 py-4 font-medium text-gray-900">{{ lic.client }}</td>
              <td class="px-5 py-4 font-mono-data text-gray-600 text-xs">{{ lic.machineId }}</td>
              <td class="px-5 py-4 text-gray-600">{{ lic.expirationDate }}</td>
              <td class="px-5 py-4">
                <span class="font-mono-data text-sm font-semibold" :class="lic.daysUntilExpiry <= 7 ? 'text-red-600' : lic.daysUntilExpiry <= 30 ? 'text-amber-600' : 'text-gray-700'">
                  {{ lic.daysUntilExpiry }} días
                </span>
              </td>
              <td class="px-5 py-4">
                <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium" :class="lic.active ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'">
                  <span class="w-1.5 h-1.5 rounded-full" :class="lic.active ? 'bg-green-500' : 'bg-red-500'"></span>
                  {{ lic.active ? 'Activa' : 'Inactiva' }}
                </span>
              </td>
              <td class="px-5 py-4">
                <div class="flex items-center gap-2">
                  <button
                    v-if="lic.active"
                    @click="toggleLicense(lic)"
                    class="text-gray-400 hover:text-red-600 transition-colors text-xs"
                    title="Desactivar"
                  >
                    <i class="fa-solid fa-circle-xmark"></i>
                  </button>
                  <button
                    v-else
                    @click="toggleLicense(lic)"
                    class="text-gray-400 hover:text-green-600 transition-colors text-xs"
                    title="Activar"
                  >
                    <i class="fa-solid fa-circle-check"></i>
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
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 class="text-lg font-semibold text-gray-900">Generar nueva licencia</h2>
            <button @click="showGenerateModal = false" class="text-gray-400 hover:text-gray-600 transition-colors">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <form @submit.prevent="generateLicense" class="px-6 py-5 space-y-4">
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Nombre del cliente</label>
              <input v-model="genForm.client" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="Nombre del cliente" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">ID de máquina</label>
              <input v-model="genForm.machineId" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="MACHINE-XXXX-XXXX" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Duración (días)</label>
              <select v-model.number="genForm.days" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all">
                <option value="30">30 días</option>
                <option value="90">90 días</option>
                <option value="180">180 días</option>
                <option value="365">365 días (1 año)</option>
                <option value="730">730 días (2 años)</option>
              </select>
            </div>
            <div class="flex justify-end gap-3 pt-2">
              <button
                type="button"
                @click="showGenerateModal = false"
                class="px-5 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
              >
                Cancelar
              </button>
              <button
                type="submit"
                class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl shadow-sm font-medium transition-colors text-sm flex items-center gap-2"
              >
                <i class="fa-solid fa-wand-magic-sparkles text-xs"></i>
                Generar
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { formatCurrency } from '@/composables/useUtils'

const licenses = ref([
  { id: 1, key: 'LIC-A7B3-9F2C-4D8E', client: 'Supermercado La Esquina', machineId: 'MACH-1928-3F4A', expirationDate: '2026-12-31', daysUntilExpiry: 194, active: true },
  { id: 2, key: 'LIC-C2D9-1E5F-8A3B', client: 'Distribuidora Norte SRL', machineId: 'MACH-3847-9B2C', expirationDate: '2026-09-15', daysUntilExpiry: 87, active: true },
  { id: 3, key: 'LIC-E5F8-7B1D-3C9A', client: 'Carnicería Don Pedro', machineId: 'MACH-5561-7D3E', expirationDate: '2026-07-01', daysUntilExpiry: 11, active: true },
  { id: 4, key: 'LIC-9G2H-4I6J-1K8L', client: 'Almacén El Gaucho', machineId: 'MACH-7739-1F5B', expirationDate: '2026-06-25', daysUntilExpiry: 5, active: true },
  { id: 5, key: 'LIC-M3N5-8O7P-2Q9R', client: 'Kiosco 24hs Centro', machineId: 'MACH-1029-6A4D', expirationDate: '2026-04-15', daysUntilExpiry: -66, active: false },
  { id: 6, key: 'LIC-S6T8-1U2V-5W3X', client: 'Librería Papel y Tinta', machineId: 'MACH-8821-4C8F', expirationDate: '2027-03-10', daysUntilExpiry: 263, active: true },
])

const showGenerateModal = ref(false)

const genForm = reactive({
  client: '',
  machineId: '',
  days: 365,
})

function generateKey() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
  const seg = () => Array.from({ length: 4 }, () => chars[Math.floor(Math.random() * chars.length)]).join('')
  return `LIC-${seg()}-${seg()}-${seg()}`
}

function openGenerateModal() {
  genForm.client = ''
  genForm.machineId = ''
  genForm.days = 365
  showGenerateModal.value = true
}

function generateLicense() {
  const expDate = new Date()
  expDate.setDate(expDate.getDate() + genForm.days)
  const expStr = expDate.toISOString().split('T')[0]
  licenses.value.push({
    id: licenses.value.length + 1,
    key: generateKey(),
    client: genForm.client,
    machineId: genForm.machineId,
    expirationDate: expStr,
    daysUntilExpiry: genForm.days,
    active: true,
  })
  showGenerateModal.value = false
}

function toggleLicense(lic) {
  lic.active = !lic.active
}
</script>
