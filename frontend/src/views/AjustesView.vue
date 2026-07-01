<script setup>
import { ref, onMounted } from 'vue'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const toast = useToastStore()

const saving = ref(false)
const loading = ref(true)
const generando = ref(false)
const subiendo = ref(false)
const csrGenerado = ref(false)
const csrContent = ref('')
const claveContent = ref('')
const certInfo = ref(null)
const certUpload = ref('')
const showGuide = ref(false)
const certContent = ref('')
const afipExpanded = ref(false)
const bancariosExpanded = ref(false)

const config = ref({
  afip_mode: 'testing',
  afip_cuit: '',
  afip_pto_vta: '1',
  afip_cert: '',
  afip_key: '',
  banco_nombre: '',
  banco_titular: '',
  banco_alias: '',
  empresa_nombre: '',
})

async function loadConfig() {
  loading.value = true
  try {
    const data = await api.get('/api/config/ajustes')
    if (data) {
      for (const key of Object.keys(config.value)) {
        if (data[key]) config.value[key] = data[key].valor || ''
      }
    }
    await loadCertInfo()
  } catch {
    toast.warning('No se pudieron cargar ajustes')
  }
  loading.value = false
}

async function loadCertInfo() {
  try {
    const resp = await api.get('/api/facturacion/afip/certificado-info')
    certInfo.value = (resp && resp !== null) ? resp : null
  } catch {
    certInfo.value = null
  }
  try {
    const pemResp = await api.get('/api/facturacion/afip/certificado-pem')
    if (pemResp && pemResp.cert_pem) {
      certUpload.value = pemResp.cert_pem
      certContent.value = pemResp.cert_pem
    }
  } catch {
    // no saved cert
  }
  try {
    const csrResp = await api.get('/api/facturacion/afip/csr-guardado')
    if (csrResp && csrResp.csr_pem) {
      csrContent.value = csrResp.csr_pem
      csrGenerado.value = true
    }
  } catch {
    // no saved CSR
  }
}

const AFIP_BASIC_KEYS = ['afip_mode', 'afip_cuit', 'afip_pto_vta']
const BANCOS_KEYS = ['banco_nombre', 'banco_titular', 'banco_alias']

const descs = {
  afip_mode: 'Entorno AFIP: testing | production',
  afip_cuit: 'CUIT del emisor (11 dígitos sin guiones)',
  afip_pto_vta: 'Número de punto de venta habilitado en AFIP',
  afip_cert: 'Certificado X.509 (.crt) en formato PEM',
  afip_key: 'Clave privada RSA (.key) en formato PEM',
  banco_nombre: 'Nombre del banco para transferencias',
  banco_titular: 'Nombre del titular de la cuenta',
  banco_alias: 'Alias de CBU/Alias para transferencias',
}

async function saveConfig(keys = null) {
  saving.value = true
  try {
    const entries = keys
      ? Object.entries(config.value).filter(([k]) => keys.includes(k))
      : Object.entries(config.value)
    for (const [clave, valor] of entries) {
      await api.put('/api/config/ajustes', { clave, valor, descripcion: descs[clave] || '' })
    }
    toast.success('Configuración guardada')
  } catch {
    toast.error('Error al guardar configuración')
  }
  saving.value = false
}

async function generarCsr() {
  if (!config.value.afip_cuit || config.value.afip_cuit.length !== 11) {
    toast.warning('Ingresá un CUIT de 11 dígitos primero')
    return
  }
  generando.value = true
  try {
    const resp = await api.post('/api/facturacion/afip/generar-csr', {
      cuit: config.value.afip_cuit,
      pto_vta: parseInt(config.value.afip_pto_vta) || 1,
      razon_social: '',
    })
    csrContent.value = resp.csr_pem
    csrGenerado.value = true
    toast.success('CSR generado. Descargalo y subilo a ARCA.')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al generar CSR')
  }
  generando.value = false
}

function descargarCsr() {
  const content = csrContent.value.replace(/\\n/g, '\n')
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `afip_csr_${config.value.afip_cuit}.csr`
  a.click()
  URL.revokeObjectURL(url)
}

async function descargarKey() {
  try {
    const resp = await api.get('/api/facturacion/afip/descargar-clave')
    const content = resp.clave_pem
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `afip_key_${config.value.afip_cuit}.key`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Clave privada descargada')
  } catch {
    toast.error('No hay clave para descargar')
  }
}

async function subirCertificado() {
  if (!certUpload.value.trim()) {
    toast.warning('Pegá el contenido del certificado .crt')
    return
  }
  subiendo.value = true
  try {
    const resp = await api.post('/api/facturacion/afip/subir-certificado', {
      cert_pem: certUpload.value,
    })
    certInfo.value = resp
    certContent.value = certUpload.value
    certUpload.value = ''
    toast.success(resp.message || resp.mensaje || 'Certificado guardado')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al subir certificado')
  }
  subiendo.value = false
}

function cargarCsrDesdeArchivo(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async (e) => {
    const content = e.target.result
    csrContent.value = content.replace(/\n/g, '\\n')
    csrGenerado.value = true
    try {
      await api.post('/api/facturacion/afip/cargar-csr', { csr_pem: content })
    } catch {
      // guardar igual en memoria aunque falle el sync
    }
    toast.success('CSR cargado. Ahora subilo a ARCA para obtener el certificado.')
  }
  reader.readAsText(file)
}

function cargarCertDesdeArchivo(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    certUpload.value = e.target.result
    toast.success('Certificado cargado. Click en Guardar para guardarlo.')
  }
  reader.readAsText(file)
}

function copiarCsr() {
  navigator.clipboard.writeText(csrContent.value.replace(/\\n/g, '\n'))
  toast.success('CSR copiado al portapapeles')
}

function displayCsr() {
  return csrContent.value.replace(/\\n/g, '\n')
}

onMounted(loadConfig)
</script>

<template>
  <div class="space-y-5">
    <div>
      <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Ajustes</h2>
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Configuración del sistema y AFIP</p>
    </div>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="afipExpanded = !afipExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-regular fa-file-lines text-brand-600"></i>
            Factura Electrónica AFIP / ARCA
          </h3>
          <div class="flex items-center gap-3">
            <span v-if="certInfo" class="text-xs text-green-600 dark:text-green-400">
              <i class="fa-solid fa-check-circle mr-1"></i>{{ certInfo.subject }} — {{ certInfo.valido_hasta }}
            </span>
            <span v-else class="text-xs text-amber-500">
              <i class="fa-solid fa-circle-xmark mr-1"></i>No configurado
            </span>
            <i :class="['fa-solid fa-chevron-down text-xs transition-transform', afipExpanded ? 'rotate-180' : '']"></i>
          </div>
        </div>
      </button>

      <div v-if="afipExpanded" class="mt-4 space-y-4">
        <div class="space-y-4 max-w-lg">
          <BaseSelect
            v-model="config.afip_mode"
            label="Entorno"
            :options="[
              { value: 'testing', label: 'Testing (Homologación)' },
              { value: 'production', label: 'Producción' }
            ]"
            option-value="value"
            option-label="label"
          />

          <BaseInput v-model="config.afip_cuit" label="CUIT" placeholder="20123456789" maxlength="11" hint="11 dígitos sin guiones" />

          <BaseInput v-model="config.afip_pto_vta" label="Punto de Venta" placeholder="1" maxlength="4" hint="Número habilitado en AFIP" />

          <div class="flex items-center gap-3 pt-2">
            <BaseButton variant="primary" :loading="saving" @click="saveConfig(AFIP_BASIC_KEYS)">
              <i class="fa-solid fa-floppy-disk"></i> Guardar
            </BaseButton>
            <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
          </div>
        </div>

        <hr class="border-slate-200 dark:border-slate-700" />

        <div v-if="!csrGenerado">
          <p class="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Clave RSA y CSR</p>
          <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3 mb-3">
            <p class="text-xs text-amber-700 dark:text-amber-300">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>
              <strong>Importante:</strong> Al generar se descarga la clave privada automáticamente. Guardala en lugar seguro. Si la perdés, revocá el certificado en AFIP y generá uno nuevo.
            </p>
          </div>
          <div class="flex gap-3 flex-wrap">
            <BaseButton variant="secondary" :loading="generando" @click="generarCsr">
              <i class="fa-solid fa-wand-magic-sparkles"></i> Generar CSR
            </BaseButton>
            <label class="cursor-pointer inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-600 rounded text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <i class="fa-solid fa-upload"></i> Cargar CSR existente
              <input type="file" accept=".csr,.pem,.txt" class="hidden" @change="cargarCsrDesdeArchivo" />
            </label>
          </div>
        </div>

        <div v-if="csrGenerado">
          <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3 mb-3">
            <p class="text-xs text-red-700 dark:text-red-300">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>
              <strong>Antes de continuar, bajá la clave privada (.key)</strong> — sin ella no vas a poder facturar.
            </p>
          </div>
          <div class="flex gap-2 mb-4">
            <BaseButton variant="danger" @click="descargarKey">
              <i class="fa-solid fa-key"></i> Descargar .key
            </BaseButton>
          </div>

          <div class="flex items-start justify-between mb-2">
            <p class="text-xs font-semibold text-slate-700 dark:text-slate-300">CSR</p>
            <button class="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 underline" @click="csrGenerado = false">
              Generar nuevo
            </button>
          </div>
          <p class="text-[11px] text-slate-500 dark:text-slate-400 mb-2">
            Subí este CSR a ARCA. Cuando te devuelvan el certificado .crt, cargalo abajo.
          </p>
          <div class="bg-slate-100 dark:bg-slate-800 rounded p-3 mb-3">
            <pre class="text-[10px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap break-all font-mono">{{ displayCsr() }}</pre>
          </div>
          <div class="flex gap-2 mb-4">
            <BaseButton variant="secondary" @click="copiarCsr">
              <i class="fa-regular fa-copy"></i> Copiar
            </BaseButton>
            <BaseButton variant="secondary" @click="descargarCsr">
              <i class="fa-solid fa-download"></i> Descargar .csr
            </BaseButton>
          </div>

          <hr class="border-slate-200 dark:border-slate-700 mb-4" />

          <p class="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Certificado de ARCA</p>
          <div class="flex items-center gap-3 mb-3">
            <label class="cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <i class="fa-solid fa-upload"></i> Cargar .crt desde archivo
              <input type="file" accept=".crt,.pem,.txt" class="hidden" @change="cargarCertDesdeArchivo" />
            </label>
          </div>
          <textarea
            v-model="certUpload"
            class="w-full border border-slate-300 dark:border-slate-600 rounded px-3 py-2 text-xs font-mono bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
            rows="5"
            placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
          />
          <div class="mt-3">
            <BaseButton variant="primary" :loading="subiendo" @click="subirCertificado">
              <i class="fa-solid fa-floppy-disk"></i> Guardar Certificado
            </BaseButton>
          </div>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="showGuide = !showGuide">
        <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <i class="fa-solid fa-circle-info text-sky-600"></i>
          Guía paso a paso para obtener certificado AFIP / ARCA
          <i :class="['fa-solid fa-chevron-down text-xs transition-transform', showGuide ? 'rotate-180' : '']"></i>
        </h3>
      </button>

      <div v-if="showGuide" class="mt-4 text-xs text-slate-600 dark:text-slate-400 space-y-4">
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 1: Generar CSR</p>
          <p>Expandí la sección <strong>"Factura Electrónica AFIP / ARCA"</strong> arriba, completá CUIT y Pto. Venta, guardá, y click en <strong>"Generar CSR"</strong>. Se descarga automáticamente la clave privada RSA — guardala muy bien.</p>
        </div>
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 2: Subir CSR a ARCA</p>
          <ul class="list-disc list-inside space-y-0.5">
            <li>Ingresá a <a href="https://auth.afip.gob.ar/contribuyente_/login.xhtml" target="_blank" class="text-brand-600 underline">auth.afip.gob.ar</a></li>
            <li>Ir a <strong>Administración de Certificados</strong> (WSASS)</li>
            <li>Crear un nuevo certificado</li>
            <li>Pegar el contenido del archivo <code class="bg-slate-200 dark:bg-slate-700 px-1 rounded">.csr</code> descargado</li>
            <li>Seleccionar servicio: <strong>WSFEV1</strong></li>
            <li>Confirmar y descargar el <code>.crt</code></li>
          </ul>
        </div>
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 3: Volver al sistema</p>
          <p>En la misma sección expandida, cargá o pegá el <code>.crt</code> y guardá. El sistema queda listo para facturar.</p>
        </div>
        <div class="border-t border-slate-200 dark:border-slate-700 pt-2">
          <p class="text-[10px] text-slate-400"><i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i> Guardá la clave privada en un lugar seguro. Sin ella no se puede usar el certificado.</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="bancariosExpanded = !bancariosExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-building-columns text-brand-600"></i>
            Datos Bancarios para Transferencias
          </h3>
          <div class="flex items-center gap-3">
            <span v-if="config.banco_nombre" class="text-xs text-green-600 dark:text-green-400">
              <i class="fa-solid fa-check-circle mr-1"></i>{{ config.banco_nombre }}
            </span>
            <span v-else class="text-xs text-amber-500">
              <i class="fa-solid fa-circle-xmark mr-1"></i>No configurado
            </span>
            <i :class="['fa-solid fa-chevron-down text-xs transition-transform', bancariosExpanded ? 'rotate-180' : '']"></i>
          </div>
        </div>
      </button>

      <div v-if="bancariosExpanded" class="mt-4 space-y-4 max-w-lg">
        <BaseInput v-model="config.banco_nombre" label="Banco" placeholder="Banco Francés, Galicia, etc." />

        <BaseInput v-model="config.banco_titular" label="Titular" placeholder="Nombre completo del titular" />

        <BaseInput v-model="config.banco_alias" label="Alias" placeholder="alias.cbutransferencia" />

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig(BANCOS_KEYS)">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>
  </div>
</template>
