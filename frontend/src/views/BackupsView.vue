<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">Backups</h1>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gestión de respaldos locales y en la nube (R2)</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton variant="secondary" @click="openR2Config">
          <i class="fa-solid fa-cloud text-slate-500"></i>
          Configurar R2
        </BaseButton>
        <BaseButton :loading="creatingBackup" @click="createBackup">
          <i class="fa-solid fa-floppy-disk"></i>
          {{ creatingBackup ? 'Creando...' : 'Crear backup' }}
        </BaseButton>
      </div>
    </div>

    <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <KpiCard label="Último backup local" :value="localBackups.length > 0 ? localBackups[0].date : '—'" icon="fa-hard-drive" icon-color="info" :animate="false" />
      <KpiCard label="Tamaño último backup" :value="localBackups.length > 0 ? localBackups[0].size : '—'" icon="fa-database" icon-color="brand" :animate="false" />
      <KpiCard label="Sincronización R2" :value="r2SyncOk ? 'Sincronizado' : 'No sincronizado'" :icon="r2SyncOk ? 'fa-check-circle' : 'fa-triangle-exclamation'" :icon-color="r2SyncOk ? 'success' : 'danger'" :animate="false" />
      <KpiCard label="Próximo backup automático" value="2026-06-21 03:00" icon="fa-clock" icon-color="warning" :animate="false" />
    </div>

    <div v-if="authError" class="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 px-4 py-3 flex items-start gap-3">
      <i class="fa-solid fa-triangle-exclamation text-red-500 mt-0.5"></i>
      <div class="flex-1">
        <p class="text-sm font-medium text-red-800 dark:text-red-300">Sesión expirada o no autenticado</p>
        <p class="text-sm text-red-600 dark:text-red-400 mt-1">Las APIs requieren autenticación. Recargá la página o <a href="/login" class="underline font-medium">iniciá sesión</a> de nuevo.</p>
      </div>
      <button @click="authError = false" class="text-red-400 hover:text-red-600 dark:hover:text-red-200 text-sm">×</button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <BaseCard padding="none">
        <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
            <i class="fa-solid fa-hard-drive text-slate-600 dark:text-slate-400"></i>
          </div>
          <h2 class="font-semibold text-slate-900 dark:text-white">Backups locales</h2>
          <BaseBadge variant="default" size="xs" class="ml-1">este equipo</BaseBadge>
          <span class="ml-auto text-xs text-slate-400 dark:text-slate-500">{{ localBackups.length }} archivos</span>
        </div>
        <BaseTable
          :columns="[{ key: 'name', label: 'Nombre' }, { key: 'size', label: 'Tamaño' }, { key: 'date', label: 'Fecha' }, { key: 'actions', label: 'Acciones' }]"
          :rows="localBackups"
          empty-title="No hay backups locales"
          empty-text="No se encontraron archivos de respaldo locales."
          empty-icon="fa-database"
          compact
        >
          <template #name="{ row }">
            <div class="flex items-center gap-2">
              <i class="fa-solid fa-file-zipper text-slate-400"></i>
              <span class="font-mono-data text-xs text-slate-700 dark:text-slate-300" :class="{'text-brand-600 dark:text-brand-400 font-bold': highlightName === row.name}">{{ row.name }}</span>
              <span v-if="highlightName === row.name" class="inline-flex gap-1">
                <span class="px-1.5 py-0.5 rounded bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 text-[9px] font-bold">NUEVO</span>
              </span>
            </div>
          </template>
          <template #size="{ row }">
            <span class="font-mono-data text-xs" :class="highlightName === row.name ? 'text-brand-600 dark:text-brand-400 font-bold' : 'text-slate-600 dark:text-slate-400'">{{ row.size }}</span>
          </template>
          <template #date="{ row }">
            <span class="text-xs" :class="highlightName === row.name ? 'text-brand-600 dark:text-brand-400 font-bold' : 'text-slate-500 dark:text-slate-400'">{{ row.date }}</span>
          </template>
          <template #actions="{ row }">
            <div class="flex items-center gap-2">
              <BaseButton variant="ghost" size="sm" icon-only aria-label="Descargar" :loading="downloadingFile[row.name]" @click="downloadBackup(row)">
                <i :class="downloadingFile[row.name] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-download'"></i>
              </BaseButton>
              <BaseButton variant="ghost" size="sm" icon-only aria-label="Subir a R2" :loading="uploadingFile[row.name]" @click="uploadBackup(row)">
                <i :class="uploadingFile[row.name] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-cloud-arrow-up'"></i>
              </BaseButton>
              <BaseButton variant="ghost" size="sm" icon-only aria-label="Eliminar" :loading="deletingFile[row.name]" @click="deleteBackup(row)">
                <i :class="deletingFile[row.name] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-trash-can'"></i>
              </BaseButton>
            </div>
          </template>
        </BaseTable>
      </BaseCard>

      <BaseCard padding="none">
        <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-orange-100 dark:bg-orange-900/30 flex items-center justify-center">
            <i class="fa-solid fa-cloud text-orange-500 dark:text-orange-400"></i>
          </div>
          <h2 class="font-semibold text-slate-900 dark:text-white">Backups en R2 Cloud</h2>
          <span class="ml-auto text-xs text-slate-400 dark:text-slate-500">{{ r2Backups.length }} archivos</span>
        </div>
        <BaseTable
          :columns="[{ key: 'name', label: 'Nombre' }, { key: 'size', label: 'Tamaño' }, { key: 'date', label: 'Fecha' }, { key: 'actions', label: 'Acciones' }]"
          :rows="r2Backups"
          empty-title="No hay backups en la nube"
          empty-text="No se encontraron respaldos en R2 Cloud."
          empty-icon="fa-cloud"
          compact
        >
          <template #name="{ row }">
            <div class="flex items-center gap-2">
              <i class="fa-solid fa-cloud-arrow-up text-orange-400"></i>
              <span class="font-mono-data text-xs text-slate-700 dark:text-slate-300">{{ row.name }}</span>
            </div>
          </template>
          <template #size="{ row }">
            <span class="font-mono-data text-xs text-slate-600 dark:text-slate-400">{{ row.size }}</span>
          </template>
          <template #date="{ row }">
            <span class="text-xs text-slate-500 dark:text-slate-400">{{ row.date }}</span>
          </template>
          <template #actions="{ row }">
            <div class="flex items-center gap-2">
              <BaseButton variant="ghost" size="sm" icon-only aria-label="Descargar de R2" :loading="downloadingFile[row.name]" @click="downloadFromR2(row)">
                <i :class="downloadingFile[row.name] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-download'"></i>
              </BaseButton>
              <BaseButton variant="ghost" size="sm" icon-only aria-label="Eliminar de R2" :loading="deletingR2File[row.name]" @click="deleteR2Backup(row)">
                <i :class="deletingR2File[row.name] ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-trash-can'"></i>
              </BaseButton>
            </div>
          </template>
        </BaseTable>
      </BaseCard>
    </div>

    <BaseCard padding="none">
      <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2.5">
        <div class="w-8 h-8 rounded-lg bg-violet-100 dark:bg-violet-900/30 flex items-center justify-center">
          <i class="fa-solid fa-tags text-violet-500 dark:text-violet-400"></i>
        </div>
        <h2 class="font-semibold text-slate-900 dark:text-white">Catálogo</h2>
        <span class="ml-auto text-xs text-slate-400 dark:text-slate-500">Exportación a R2</span>
      </div>
      <div class="p-5 space-y-5">
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <KpiCard label="Productos exportables" :value="catalogoStatus.exportables" icon="fa-box-open" icon-color="brand" />
          <KpiCard label="Última exportación" :value="catalogoStatus.lastExport || '—'" icon="fa-calendar-check" icon-color="info" :animate="false" />
          <KpiCard label="Catálogo cargado" :value="catalogoStatus.loaded ? 'Cargado' : 'No cargado'" :icon="catalogoStatus.loaded ? 'fa-check-circle' : 'fa-clock'" :icon-color="catalogoStatus.loaded ? 'success' : 'warning'" :animate="false" />
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <BaseButton :loading="exportingCatalogo" @click="exportarCatalogo">
            <i class="fa-solid fa-file-export"></i>
            {{ exportingCatalogo ? 'Exportando...' : 'Exportar y Subir Catálogo' }}
          </BaseButton>
          <BaseButton variant="secondary" :loading="downloadingCatalogoCentral" @click="descargarCatalogoCentral">
            <i class="fa-solid fa-cloud-download-alt"></i>
            {{ downloadingCatalogoCentral ? 'Descargando...' : 'Descargar Catálogo Central' }}
          </BaseButton>
          <BaseButton variant="secondary" :loading="reloadingCatalogo" @click="recargarCatalogo">
            <i class="fa-solid fa-rotate"></i>
            {{ reloadingCatalogo ? 'Recargando...' : 'Recargar Catálogo' }}
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <BaseModal v-model="showR2Config" title="Configuración R2 Cloud" size="md">
      <form @submit.prevent="saveR2Config" class="space-y-4">
        <BaseInput v-model="r2Form.endpoint" label="Endpoint" type="url" required placeholder="https://&lt;account&gt;.r2.cloudflarestorage.com" input-class="font-mono-data" />
        <BaseInput v-model="r2Form.accessKey" label="Access Key" type="text" required placeholder="xxxxxxxxxxxxxxxx" input-class="font-mono-data" />
        <BaseInput v-model="r2Form.secretKey" label="Secret Key" type="password" required placeholder="••••••••••••••••" input-class="font-mono-data" />
        <BaseInput v-model="r2Form.bucket" label="Bucket" type="text" required placeholder="erp-backups" />
        <div class="flex items-center justify-between pt-2">
          <BaseButton type="button" variant="secondary" :loading="testingConnection" @click="testConnection">
            <i class="fa-solid fa-plug"></i>
            {{ testingConnection ? 'Probando...' : 'Probar conexión' }}
          </BaseButton>
          <div class="flex gap-3">
            <BaseButton type="button" variant="secondary" @click="showR2Config = false">Cancelar</BaseButton>
            <BaseButton type="submit">Guardar</BaseButton>
          </div>
        </div>
        <div v-if="connectionResult" class="text-sm rounded-xl p-3" :class="connectionResult.success ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300' : 'bg-rose-50 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'">
          {{ connectionResult.message }}
        </div>
      </form>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import api, { getToken } from '@/services/api'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import KpiCard from '@/components/ui/KpiCard.vue'

const toast = useToastStore()

const localBackups = ref([])
const r2Backups = ref([])

const creatingBackup = ref(false)
const downloadingFile = ref({})
const deletingFile = ref({})
const deletingR2File = ref({})
const uploadingFile = ref({})
const showR2Config = ref(false)
const testingConnection = ref(false)
const r2SyncOk = ref(false)
const connectionResult = ref(null)
const exportingCatalogo = ref(false)
const downloadingCatalogoCentral = ref(false)
const reloadingCatalogo = ref(false)

const highlightName = ref('')
const authError = ref(false)

const catalogoStatus = reactive({
  exportables: 0,
  lastExport: null,
  loaded: false,
})

const r2Form = reactive({
  endpoint: '',
  accessKey: '',
  secretKey: '',
  bucket: '',
})

function formatBytes(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  const val = bytes / Math.pow(1024, i)
  return `${val.toFixed(i === 0 ? 0 : 1)} ${units[i]}`
}

function formatDate(iso) {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleString('es-AR', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

function mapBackup(b, idx) {
  return {
    id: idx,
    name: b.nombre || b.name,
    size: b.size_display || formatBytes(b.size),
    size_bytes: b.size,
    date: b.fecha_display || formatDate(b.fecha || b.date),
    raw: b,
  }
}

function clearHighlight() {
  setTimeout(() => { highlightName.value = '' }, 6000)
}

async function fetchAll() {
  try {
    const [estado, locales, r2] = await Promise.all([
      api.get('/api/backups/estado'),
      api.get('/api/backups/local'),
      api.get('/api/backups/r2'),
    ])
    if (locales && Array.isArray(locales)) {
      localBackups.value = locales.map(mapBackup)
    }
    if (r2 && Array.isArray(r2)) {
      r2Backups.value = r2.map(mapBackup)
    }
    if (estado) {
      r2SyncOk.value = estado.r2_habilitado ?? false
    }
  } catch (e) {
    if (e?.status === 401) authError.value = true
    else toast.error('Error al cargar backups')
  }
  fetchCatalogoStatus()
}

async function createBackup() {
  creatingBackup.value = true
  try {
    const resp = await api.post('/api/backups/crear')
    const filename = resp?.data?.filename || resp?.filename || ''
    toast.success(`Backup creado: ${filename}`)
    await fetchAll()
    if (filename) {
      highlightName.value = filename
      clearHighlight()
    }
  } catch (e) {
    if (e?.status === 401) authError.value = true
    else toast.error(e?.message || 'Error al crear backup')
  }
  creatingBackup.value = false
}

async function downloadBackup(backup) {
  downloadingFile.value[backup.name] = true
  try {
    const resp = await fetch(`/api/backups/descargar/${encodeURIComponent(backup.name)}`, {
      headers: { 'Authorization': `Bearer ${getToken()}` },
    })
    if (!resp.ok) {
      const err = await resp.text().catch(() => '')
      throw new Error(err || `Error ${resp.status}`)
    }
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = backup.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 10000)
  } catch (e) {
    toast.error(`Error al descargar ${backup.name}: ${e.message}`)
  }
  downloadingFile.value[backup.name] = false
}

async function uploadBackup(backup) {
  uploadingFile.value[backup.name] = true
  try {
    const resp = await api.post(`/api/backups/subir?filename=${encodeURIComponent(backup.name)}`)
    toast.success(resp?.message || `${backup.name} subido a R2`)
    await fetchAll()
  } catch (e) {
    toast.error(e?.response?.data?.detail || `Error al subir ${backup.name} a R2`)
  }
  uploadingFile.value[backup.name] = false
}

async function downloadFromR2(backup) {
  downloadingFile.value[backup.name] = true
  try {
    // Download from R2 to local server, then serve the file
    await api.post(`/api/backups/descargar?filename=${encodeURIComponent(backup.name)}`)
    // Now trigger browser download of the local copy
    const resp = await fetch(`/api/backups/descargar/${encodeURIComponent(backup.name)}`, {
      headers: { 'Authorization': `Bearer ${getToken()}` },
    })
    if (!resp.ok) {
      const err = await resp.text().catch(() => '')
      throw new Error(err || `Error ${resp.status}`)
    }
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = backup.name
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 10000)
    toast.success(`${backup.name} descargado de R2`)
  } catch (e) {
    toast.error(`Error al descargar ${backup.name} de R2: ${e.message}`)
  }
  downloadingFile.value[backup.name] = false
}

async function deleteBackup(backup) {
  if (!confirm(`¿Eliminar "${backup.name}" (${backup.size}) del equipo local? Esta acción no se puede deshacer.`)) return
  deletingFile.value[backup.name] = true
  try {
    const resp = await api.delete(`/api/backups/local/${encodeURIComponent(backup.name)}`)
    toast.success(resp?.message || `Backup eliminado: ${backup.name}`)
    localBackups.value = localBackups.value.filter(b => b.name !== backup.name)
  } catch (e) {
    toast.error(e?.response?.data?.detail || `Error al eliminar ${backup.name}`)
  }
  deletingFile.value[backup.name] = false
}

async function deleteR2Backup(backup) {
  if (!confirm(`¿Eliminar "${backup.name}" (${backup.size}) de la nube R2? Esta acción no se puede deshacer.`)) return
  deletingR2File.value[backup.name] = true
  try {
    const resp = await api.delete(`/api/backups/r2/${encodeURIComponent(backup.name)}`)
    toast.success(resp?.message || `Backup eliminado de R2: ${backup.name}`)
    r2Backups.value = r2Backups.value.filter(b => b.name !== backup.name)
  } catch (e) {
    toast.error(e?.response?.data?.detail || `Error al eliminar ${backup.name} de R2`)
  }
  deletingR2File.value[backup.name] = false
}

async function fetchCatalogoStatus() {
  try {
    const data = await api.get('/api/catalogo/estado')
    if (data) Object.assign(catalogoStatus, data)
  } catch { /* fallback */ }
}

async function exportarCatalogo() {
  exportingCatalogo.value = true
  try {
    await api.post('/api/catalogo/exportar')
    toast.success('Catálogo exportado a R2')
    await fetchCatalogoStatus()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error al exportar catálogo')
  }
  exportingCatalogo.value = false
}

async function descargarCatalogoCentral() {
  downloadingCatalogoCentral.value = true
  try {
    await api.post('/api/catalogo/descargar')
    toast.success('Catálogo central descargado')
    await fetchCatalogoStatus()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error al descargar catálogo central')
  }
  downloadingCatalogoCentral.value = false
}

async function recargarCatalogo() {
  reloadingCatalogo.value = true
  try {
    await api.post('/api/catalogo/recargar')
    toast.success('Catálogo recargado')
    await fetchCatalogoStatus()
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error al recargar catálogo')
  }
  reloadingCatalogo.value = false
}

function openR2Config() {
  showR2Config.value = true
  connectionResult.value = null
}

async function saveR2Config() {
  try {
    await api.put('/api/backups/config-r2', r2Form)
    toast.success('Configuración R2 guardada')
    showR2Config.value = false
    r2SyncOk.value = true
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'Error al guardar configuración R2')
  }
}

async function testConnection() {
  testingConnection.value = true
  connectionResult.value = null
  try {
    await api.post('/api/backups/test-r2', r2Form)
    connectionResult.value = { success: true, message: 'Conexión exitosa con R2.' }
  } catch (e) {
    connectionResult.value = { success: false, message: e?.response?.data?.detail || 'Error de conexión' }
  }
  testingConnection.value = false
}

onMounted(() => {
  fetchAll()
})
</script>
