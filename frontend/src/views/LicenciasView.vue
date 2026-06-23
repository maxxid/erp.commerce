<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Licencias</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gestión de licencias del sistema</p>
      </div>
      <BaseButton variant="primary" @click="openGenerateModal">
        <i class="fa-solid fa-key text-sm"></i>
        Generar licencia
      </BaseButton>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <KpiCard label="Licencias totales" :value="licenses.length" icon="fa-key" icon-color="brand" />
      <KpiCard label="Licencias activas" :value="licenses.filter(l => l.active).length" icon="fa-check-circle" icon-color="success" />
      <KpiCard label="Próximas a vencer (30d)" :value="licenses.filter(l => l.daysUntilExpiry <= 30 && l.active).length" icon="fa-clock" icon-color="warning" />
    </div>

    <BaseCard padding="none">
      <BaseTable
        :columns="[
          { key: 'clave', label: 'Clave' },
          { key: 'client', label: 'Cliente' },
          { key: 'machineId', label: 'ID Máquina' },
          { key: 'expirationDate', label: 'Vencimiento' },
          { key: 'daysUntilExpiry', label: 'Días restantes', align: 'right' },
          { key: 'active', label: 'Estado', align: 'center' },
          { key: 'actions', label: 'Acciones', align: 'center' }
        ]"
        :rows="licenses"
        :row-class="row => row.daysUntilExpiry <= 7 && row.active ? 'bg-rose-50/30 dark:bg-rose-900/20' : ''"
        empty-icon="fa-key"
        empty-title="Sin licencias"
        empty-text="No hay licencias registradas en este momento."
      >
        <template #clave="{ row }">
          <code class="font-mono-data text-xs bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded-md text-slate-700 dark:text-slate-300">{{ row.clave || row.key }}</code>
        </template>
        <template #client="{ row }">
          <span class="font-medium text-slate-900 dark:text-slate-100">{{ row.client || row.cliente }}</span>
        </template>
        <template #machineId="{ row }">
          <span class="font-mono-data text-slate-600 dark:text-slate-400 text-xs">{{ row.machineId }}</span>
        </template>
        <template #expirationDate="{ row }">
          <span class="text-slate-600 dark:text-slate-400">{{ row.expirationDate }}</span>
        </template>
        <template #daysUntilExpiry="{ row }">
          <span class="font-mono-data text-sm font-semibold" :class="row.daysUntilExpiry <= 7 ? 'text-red-600 dark:text-red-400' : row.daysUntilExpiry <= 30 ? 'text-amber-600 dark:text-amber-400' : 'text-slate-700 dark:text-slate-300'">
            {{ row.daysUntilExpiry }} días
          </span>
        </template>
        <template #active="{ row }">
          <BaseBadge :variant="row.active ? 'success' : 'danger'" dot>
            {{ row.active ? 'Activa' : 'Inactiva' }}
          </BaseBadge>
        </template>
        <template #actions="{ row }">
          <div class="flex items-center justify-center gap-2">
            <BaseButton
              v-if="!row.active"
              variant="primary"
              size="sm"
              :loading="activatingId === row.id"
              @click="activateLicense(row)"
              title="Activar"
            >
              <i :class="activatingId === row.id ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-circle-check'"></i>
              {{ activatingId === row.id ? 'Activando...' : 'Activar' }}
            </BaseButton>
            <BaseButton
              v-if="row.active"
              variant="ghost"
              size="sm"
              icon-only
              aria-label="Desactivar"
              :loading="toggling[row.id]"
              @click="deactivateLicense(row)"
              title="Desactivar"
            >
              <i :class="toggling[row.id] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-circle-xmark'"></i>
            </BaseButton>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal v-model="showGenerateModal" title="Generar nueva licencia" size="md">
      <form @submit.prevent="generateLicense" class="space-y-4">
        <BaseInput v-model="genForm.client" label="Nombre del cliente" placeholder="Nombre del cliente" required />
        <BaseInput v-model="genForm.machineId" label="ID de máquina" placeholder="MACHINE-XXXX-XXXX" required input-class="font-mono-data" />
        <BaseSelect
          :model-value="genForm.days"
          @update:modelValue="genForm.days = Number($event)"
          label="Duración (días)"
          :options="[
            { value: 30, label: '30 días' },
            { value: 90, label: '90 días' },
            { value: 180, label: '180 días' },
            { value: 365, label: '365 días (1 año)' },
            { value: 730, label: '730 días (2 años)' }
          ]"
          option-value="value"
          option-label="label"
          required
        />

        <div v-if="generatedKey" class="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-4 space-y-2">
          <p class="text-[10px] uppercase tracking-wider text-emerald-700 dark:text-emerald-300 font-semibold">Clave generada</p>
          <code
            class="block w-full font-mono-data text-lg font-bold text-emerald-900 dark:text-emerald-100 bg-white dark:bg-slate-900 border border-emerald-100 dark:border-emerald-800 rounded-lg px-3 py-2 select-all cursor-pointer break-all"
            @click="copyKey"
            title="Clic para copiar"
          >{{ generatedKey }}</code>
          <p class="text-[10px] text-emerald-600 dark:text-emerald-400">Clic en la clave para copiarla</p>
        </div>

        <div class="flex justify-end gap-3 pt-2">
          <BaseButton
            type="button"
            variant="secondary"
            @click="showGenerateModal = false"
          >
            Cancelar
          </BaseButton>
          <BaseButton
            v-if="!generatedKey"
            type="submit"
            variant="primary"
            :loading="generating"
          >
            <i :class="generating ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-wand-magic-sparkles text-xs'"></i>
            {{ generating ? 'Generando...' : 'Generar' }}
          </BaseButton>
          <BaseButton
            v-else
            type="button"
            variant="primary"
            @click="showGenerateModal = false; generatedKey = ''"
          >
            Listo
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
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import KpiCard from '@/components/ui/KpiCard.vue'

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
    toast.success('Licencia generada correctamente')
    await loadLicenses()
  } catch (e) {
    toast.error(e.message || 'Error al generar licencia')
  }
  generating.value = false
}

async function activateLicense(lic) {
  activatingId.value = lic.id
  try {
    await api.post('/api/licencia/activar', { clave: lic.clave || lic.key })
    lic.active = true
    toast.success('Licencia activada correctamente')
  } catch (e) {
    toast.error(e.message || 'Error al activar licencia')
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
  toast.info('Clave copiada al portapapeles')
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
