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

const config = ref({
  afip_mode: 'testing',
  afip_cuit: '',
  afip_pto_vta: '1',
  afip_cert: '',
  afip_key: '',
  banco_nombre: '',
  banco_titular: '',
  banco_alias: '',
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
    certInfo.value = resp.data || null
  } catch {
    certInfo.value = null
  }
}

async function saveConfig() {
  saving.value = true
  try {
    for (const [clave, valor] of Object.entries(config.value)) {
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
    csrContent.value = resp.data.csr_pem
    csrGenerado.value = true
    toast.success('CSR generado. Descargalo y subilo a ARCA.')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al generar CSR')
  }
  generando.value = false
}

function descargarCsr() {
  const blob = new Blob([csrContent.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `afip_csr_${config.value.afip_cuit}.csr`
  a.click()
  URL.revokeObjectURL(url)
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
    certInfo.value = resp.data
    certUpload.value = ''
    toast.success(resp.data.mensaje)
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al subir certificado')
  }
  subiendo.value = false
}

function copiarCsr() {
  navigator.clipboard.writeText(csrContent.value)
  toast.success('CSR copiado al portapapeles')
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
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        <i class="fa-regular fa-file-lines text-brand-600"></i>
        Factura Electrónica AFIP / ARCA
      </h3>

      <div class="space-y-4 max-w-lg">
        <BaseSelect v-model="config.afip_mode" label="Entorno">
          <option value="testing">Testing (Homologación)</option>
          <option value="production">Producción</option>
        </BaseSelect>

        <BaseInput v-model="config.afip_cuit" label="CUIT" placeholder="20123456789" maxlength="11" hint="11 dígitos sin guiones" />

        <BaseInput v-model="config.afip_pto_vta" label="Punto de Venta" placeholder="1" maxlength="4" hint="Número habilitado en AFIP" />

        <div class="border-t border-slate-200 dark:border-slate-700 pt-4 mt-4">
          <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
            <i class="fa-solid fa-shield-halved text-green-500 mr-1"></i>
            Certificado: <span v-if="certInfo" class="text-green-600 font-medium">
              {{ certInfo.subject }} — válido hasta {{ certInfo.valido_hasta }} ({{ certInfo.dias_restantes }} días)
            </span>
            <span v-else class="text-amber-500">No configurado</span>
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading && !csrGenerado">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
        <i class="fa-solid fa-key text-brand-600"></i>
        Generar clave y CSR desde el sistema
      </h3>
      <p class="text-xs text-slate-500 dark:text-slate-400 mb-4">
        El sistema genera la clave privada RSA y el CSR. Descargá el CSR, subilo a ARCA, y cuando te den el certificado .crt, volvé acá y pegalo.
      </p>

      <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3 mb-4">
        <p class="text-xs text-amber-700 dark:text-amber-300">
          <i class="fa-solid fa-triangle-exclamation mr-1"></i>
          <strong>Importante:</strong> Al generar la clave privada se descargará automáticamente. Guardala en un lugar seguro. Si la perdés, debés revocar el certificado en AFIP y generar uno nuevo.
        </p>
      </div>

      <BaseButton variant="secondary" :loading="generando" @click="generarCsr">
        <i class="fa-solid fa-wand-magic-sparkles"></i> Generar CSR
      </BaseButton>
    </BaseCard>

    <BaseCard v-if="!loading && csrGenerado">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
        <i class="fa-solid fa-file-signature text-brand-600"></i>
        CSR generado — Paso 3 de la guía
      </h3>
      <p class="text-xs text-slate-500 dark:text-slate-400 mb-3">
        Descargá el CSR y subilo a ARCA. Cuando te devuelvan el certificado .crt, pegalo abajo.
      </p>

      <div class="bg-slate-100 dark:bg-slate-800 rounded p-3 mb-3">
        <pre class="text-[10px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap break-all font-mono">{{ csrContent }}</pre>
      </div>

      <div class="flex gap-2 mb-4">
        <BaseButton variant="secondary" @click="copiarCsr">
          <i class="fa-regular fa-copy"></i> Copiar CSR
        </BaseButton>
        <BaseButton variant="secondary" @click="descargarCsr">
          <i class="fa-solid fa-download"></i> Descargar .csr
        </BaseButton>
      </div>

      <hr class="border-slate-200 dark:border-slate-700 mb-4" />

      <h4 class="text-xs font-bold text-slate-700 dark:text-slate-300 mb-2">Subir certificado de ARCA</h4>
      <p class="text-[11px] text-slate-500 dark:text-slate-400 mb-3">
        Pegá acá el contenido del archivo <code>.crt</code> que te generó ARCA:
      </p>
      <textarea
        v-model="certUpload"
        class="w-full border border-slate-300 dark:border-slate-600 rounded px-3 py-2 text-xs font-mono bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
        rows="5"
        placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
      />
      <div class="mt-3">
        <BaseButton variant="primary" :loading="subiendo" @click="subirCertificado">
          <i class="fa-solid fa-upload"></i> Guardar Certificado
        </BaseButton>
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
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 1: Generar CSR desde el sistema</p>
          <p>Click en el botón <strong>"Generar CSR"</strong> más arriba. Se descargará automáticamente la clave privada RSA. Guardala muy bien.</p>
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
          <p>Subir el archivo <code>.crt</code> en el campo de arriba. El sistema queda listo para facturar.</p>
        </div>
        <div class="border-t border-slate-200 dark:border-slate-700 pt-2">
          <p class="text-[10px] text-slate-400"><i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i> Guardá la clave privada en un lugar seguro. Sin ella no se puede usar el certificado.</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
        <i class="fa-solid fa-building-columns text-brand-600"></i>
        Datos Bancarios para Transferencias
      </h3>

      <div class="space-y-4 max-w-lg">
        <BaseInput v-model="config.banco_nombre" label="Banco" placeholder="Banco Francés, Galicia, etc." />

        <BaseInput v-model="config.banco_titular" label="Titular" placeholder="Nombre completo del titular" />

        <BaseInput v-model="config.banco_alias" label="Alias" placeholder="alias.cbutransferencia" />

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>
  </div>
</template>
