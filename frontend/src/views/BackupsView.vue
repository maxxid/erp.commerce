<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-gray-900">Backups</h1>
        <p class="text-sm text-gray-500 mt-1">Gestión de respaldos locales y en la nube (R2)</p>
      </div>
      <div class="flex items-center gap-2">
        <button
          @click="openR2Config"
          class="px-4 py-2.5 rounded-xl shadow-sm text-sm font-medium text-gray-600 bg-white border border-gray-300 hover:bg-gray-50 transition-colors flex items-center gap-2"
        >
          <i class="fa-solid fa-cloud text-gray-500"></i>
          Configurar R2
        </button>
        <button
          @click="createBackup"
          :disabled="creatingBackup"
          class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-2xl shadow-sm font-medium transition-colors flex items-center gap-2 disabled:opacity-60 disabled:cursor-not-allowed"
        >
          <i :class="creatingBackup ? 'fa-solid fa-spinner animate-spin' : 'fa-solid fa-floppy-disk'"></i>
          {{ creatingBackup ? 'Creando...' : 'Crear backup' }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Último backup local</p>
        <p class="text-sm font-medium text-gray-900 mt-1">{{ localBackups.length > 0 ? localBackups[0].date : '—' }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Tamaño último backup</p>
        <p class="font-mono-data font-bold text-gray-900 mt-1">{{ localBackups.length > 0 ? localBackups[0].size : '—' }}</p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Sincronización R2</p>
        <p class="text-sm mt-1 flex items-center gap-1.5" :class="r2SyncOk ? 'text-green-600' : 'text-red-500'">
          <span class="w-1.5 h-1.5 rounded-full" :class="r2SyncOk ? 'bg-green-500' : 'bg-red-500'"></span>
          {{ r2SyncOk ? 'Sincronizado' : 'No sincronizado' }}
        </p>
      </div>
      <div class="bg-white rounded-2xl shadow-sm p-5">
        <p class="text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Próximo backup automático</p>
        <p class="text-sm font-medium text-gray-900 mt-1">2026-06-21 03:00</p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-white rounded-2xl shadow-sm">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center">
            <i class="fa-solid fa-hard-drive text-gray-600"></i>
          </div>
          <h2 class="font-semibold text-gray-900">Backups locales</h2>
          <span class="ml-auto text-xs text-gray-400">{{ localBackups.length }} archivos</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Nombre</th>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Tamaño</th>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Fecha</th>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Acciones</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="backup in localBackups" :key="backup.id">
                <td class="px-5 py-3">
                  <div class="flex items-center gap-2">
                    <i class="fa-solid fa-file-zipper text-gray-400"></i>
                    <span class="font-mono-data text-xs text-gray-700">{{ backup.name }}</span>
                  </div>
                </td>
                <td class="px-5 py-3 text-gray-600 font-mono-data text-xs">{{ backup.size }}</td>
                <td class="px-5 py-3 text-gray-500 text-xs">{{ backup.date }}</td>
                <td class="px-5 py-3">
                  <div class="flex items-center gap-2">
                    <button
                      @click="downloadBackup(backup)"
                      class="text-gray-400 hover:text-brand-600 transition-colors"
                      title="Descargar"
                    >
                      <i class="fa-solid fa-download"></i>
                    </button>
                    <button
                      @click="deleteBackup(backup)"
                      class="text-gray-400 hover:text-red-600 transition-colors"
                      title="Eliminar"
                    >
                      <i class="fa-solid fa-trash-can"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="localBackups.length === 0" class="text-center py-8 text-gray-400 text-sm">
          <i class="fa-solid fa-database text-2xl mb-2 block"></i>
          No hay backups locales
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow-sm">
        <div class="px-5 py-4 border-b border-gray-100 flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-orange-100 flex items-center justify-center">
            <i class="fa-solid fa-cloud text-orange-500"></i>
          </div>
          <h2 class="font-semibold text-gray-900">Backups en R2 Cloud</h2>
          <span class="ml-auto text-xs text-gray-400">{{ r2Backups.length }} archivos</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 border-b border-gray-200">
              <tr>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Nombre</th>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Tamaño</th>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Fecha</th>
                <th class="px-5 py-2.5 text-[10px] uppercase tracking-wider text-gray-500 font-semibold">Sinc</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="backup in r2Backups" :key="backup.id">
                <td class="px-5 py-3">
                  <div class="flex items-center gap-2">
                    <i class="fa-solid fa-cloud-arrow-up text-orange-400"></i>
                    <span class="font-mono-data text-xs text-gray-700">{{ backup.name }}</span>
                  </div>
                </td>
                <td class="px-5 py-3 text-gray-600 font-mono-data text-xs">{{ backup.size }}</td>
                <td class="px-5 py-3 text-gray-500 text-xs">{{ backup.date }}</td>
                <td class="px-5 py-3">
                  <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium" :class="backup.synced ? 'bg-green-50 text-green-700' : 'bg-amber-50 text-amber-700'">
                    <i :class="backup.synced ? 'fa-solid fa-circle-check text-[10px]' : 'fa-solid fa-clock text-[10px]'"></i>
                    {{ backup.synced ? 'Sinc' : 'Pend' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="r2Backups.length === 0" class="text-center py-8 text-gray-400 text-sm">
          <i class="fa-solid fa-cloud text-2xl mb-2 block"></i>
          No hay backups en la nube
        </div>
      </div>
    </div>

    <Teleport to="body">
      <div v-if="showR2Config" class="fixed inset-0 z-50 flex items-center justify-center">
        <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" @click="showR2Config = false"></div>
        <div class="relative bg-white rounded-2xl shadow-xl w-full max-w-md mx-4">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h2 class="text-lg font-semibold text-gray-900">Configuración R2 Cloud</h2>
            <button @click="showR2Config = false" class="text-gray-400 hover:text-gray-600 transition-colors">
              <i class="fa-solid fa-xmark text-lg"></i>
            </button>
          </div>
          <form @submit.prevent="saveR2Config" class="px-6 py-5 space-y-4">
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Endpoint</label>
              <input v-model="r2Form.endpoint" type="url" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="https://<account>.r2.cloudflarestorage.com" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Access Key</label>
              <input v-model="r2Form.accessKey" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="xxxxxxxxxxxxxxxx" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Secret Key</label>
              <input v-model="r2Form.secretKey" type="password" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all font-mono-data" placeholder="••••••••••••••••" />
            </div>
            <div>
              <label class="block text-[10px] uppercase tracking-wider text-gray-500 font-semibold mb-1">Bucket</label>
              <input v-model="r2Form.bucket" type="text" required class="w-full border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-600/20 focus:border-brand-600 outline-none transition-all" placeholder="erp-backups" />
            </div>
            <div class="flex items-center justify-between pt-2">
              <button
                type="button"
                @click="testConnection"
                :disabled="testingConnection"
                class="px-4 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors disabled:opacity-60 flex items-center gap-2"
              >
                <i :class="testingConnection ? 'fa-solid fa-spinner animate-spin' : 'fa-solid fa-plug'"></i>
                {{ testingConnection ? 'Probando...' : 'Probar conexión' }}
              </button>
              <div class="flex gap-3">
                <button
                  type="button"
                  @click="showR2Config = false"
                  class="px-5 py-2.5 text-sm font-medium text-gray-600 bg-gray-100 rounded-xl hover:bg-gray-200 transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  class="bg-brand-600 hover:bg-brand-700 text-white px-5 py-2.5 rounded-xl shadow-sm font-medium transition-colors text-sm"
                >
                  Guardar
                </button>
              </div>
            </div>
            <div v-if="connectionResult" class="text-sm rounded-xl p-3" :class="connectionResult.success ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'">
              {{ connectionResult.message }}
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

const localBackups = ref([
  { id: 1, name: 'backup_20260620_0300.zip', size: '134 MB', date: '2026-06-20 03:00' },
  { id: 2, name: 'backup_20260619_0300.zip', size: '128 MB', date: '2026-06-19 03:00' },
  { id: 3, name: 'backup_20260618_0300.zip', size: '130 MB', date: '2026-06-18 03:00' },
  { id: 4, name: 'backup_20260617_0300.zip', size: '126 MB', date: '2026-06-17 03:00' },
  { id: 5, name: 'backup_20260615_manual.zip', size: '131 MB', date: '2026-06-15 16:45' },
])

const r2Backups = ref([
  { id: 1, name: 'backup_20260620_0300.zip', size: '134 MB', date: '2026-06-20', synced: true },
  { id: 2, name: 'backup_20260619_0300.zip', size: '128 MB', date: '2026-06-19', synced: true },
  { id: 3, name: 'backup_20260618_0300.zip', size: '130 MB', date: '2026-06-18', synced: true },
  { id: 4, name: 'backup_20260617_0300.zip', size: '126 MB', date: '2026-06-17', synced: false },
])

const creatingBackup = ref(false)
const showR2Config = ref(false)
const testingConnection = ref(false)
const r2SyncOk = ref(true)
const connectionResult = ref(null)

const r2Form = reactive({
  endpoint: 'https://abc123.r2.cloudflarestorage.com',
  accessKey: 'AKIAIOSFODNN7EXAMPLE',
  secretKey: '',
  bucket: 'erp-backups',
})

function createBackup() {
  creatingBackup.value = true
  setTimeout(() => {
    const now = new Date()
    const name = `backup_${now.toISOString().slice(0, 10).replace(/-/g, '')}_manual.zip`
    localBackups.value.unshift({
      id: localBackups.value.length + 1,
      name,
      size: '132 MB',
      date: now.toISOString().slice(0, 16).replace('T', ' '),
    })
    creatingBackup.value = false
  }, 2000)
}

function downloadBackup(backup) {
  const toast = document.createElement('div')
  toast.className = 'fixed bottom-6 right-6 bg-gray-900 text-white px-5 py-3 rounded-xl shadow-lg text-sm z-[100] transition-all'
  toast.textContent = `Descargando ${backup.name}...`
  document.body.appendChild(toast)
  setTimeout(() => {
    toast.style.opacity = '0'
    setTimeout(() => toast.remove(), 300)
  }, 2500)
}

function deleteBackup(backup) {
  localBackups.value = localBackups.value.filter(b => b.id !== backup.id)
}

function openR2Config() {
  showR2Config.value = true
  connectionResult.value = null
}

function saveR2Config() {
  showR2Config.value = false
  r2SyncOk.value = true
}

function testConnection() {
  testingConnection.value = true
  connectionResult.value = null
  setTimeout(() => {
    testingConnection.value = false
    connectionResult.value = { success: true, message: 'Conexión exitosa con R2. Bucket "erp-backups" accesible.' }
  }, 1500)
}
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
