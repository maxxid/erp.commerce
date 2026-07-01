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
  } catch {
    toast.warning('No se pudieron cargar ajustes')
  }
  loading.value = false
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
        Factura Electrónica AFIP
      </h3>

      <div class="space-y-4 max-w-lg">
        <BaseSelect v-model="config.afip_mode" label="Entorno">
          <option value="testing">Testing (Homologación)</option>
          <option value="production">Producción</option>
        </BaseSelect>

        <BaseInput v-model="config.afip_cuit" label="CUIT" placeholder="20123456789" maxlength="11" hint="11 dígitos sin guiones" />

        <BaseInput v-model="config.afip_pto_vta" label="Punto de Venta" placeholder="1" maxlength="4" hint="Número habilitado en AFIP" />

        <BaseInput
          v-model="config.afip_cert"
          label="Certificado (.crt)"
          type="textarea"
          :rows="4"
          placeholder="-----BEGIN CERTIFICATE-----&#10;..."
          hint="Pegar el contenido del certificado X.509 en formato PEM"
        />

        <BaseInput
          v-model="config.afip_key"
          label="Clave Privada (.key)"
          type="textarea"
          :rows="4"
          placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;..."
          hint="Pegar la clave privada en formato PEM"
        />

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
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

    <BaseCard v-if="!loading">
      <h3 class="text-sm font-bold text-slate-900 dark:text-white mb-2 flex items-center gap-2">
        <i class="fa-solid fa-circle-info text-sky-600"></i>
        Guía para obtener certificado AFIP
      </h3>
      <div class="text-xs text-slate-600 dark:text-slate-400 space-y-3">
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 1: Ingresar a AFIP</p>
          <p>Ir a <a href="https://auth.afip.gob.ar/contribuyente_/login.xhtml" target="_blank" class="text-brand-600 underline">auth.afip.gob.ar</a> con CUIT y clave fiscal nivel 3 o superior.</p>
        </div>
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 2: Generar clave privada y CSR (OpenSSL)</p>
          <pre class="bg-slate-100 dark:bg-slate-800 p-2 rounded text-[10px] overflow-x-auto"># Generar clave privada (NO compartir ni perder)
openssl genrsa -out mi_clave_privada.key 2048

# Generar CSR (Certificate Signing Request)
openssl req -new -key mi_clave_privada.key -out mi_csr.csr

# Mostrar el CSR para copiar en AFIP
cat mi_csr.csr</pre>
        </div>
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 3: Asociar en AFIP</p>
          <ul class="list-disc list-inside space-y-0.5">
            <li>Ir a <strong>Administración de Certificados</strong> (WSASS)</li>
            <li>Crear un nuevo certificado</li>
            <li>Pegar el contenido del archivo <code class="bg-slate-200 dark:bg-slate-700 px-1 rounded">mi_csr.csr</code> (todo el texto desde <code>-----BEGIN CERTIFICATE REQUEST-----</code>)</li>
            <li>Seleccionar servicio: <strong>WSFEV1</strong> (Factura Electrónica)</li>
            <li>Descargar el certificado firmado (<code>.crt</code>)</li>
          </ul>
        </div>
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 4: Subir archivos en el sistema</p>
          <ul class="list-disc list-inside space-y-0.5">
            <li><strong>Certificado:</strong> el archivo <code>.crt</code> descargado de AFIP</li>
            <li><strong>Clave privada:</strong> el archivo <code>mi_clave_privada.key</code> generado en el paso 2</li>
            <li><strong>CUIT:</strong> número de CUIT sin guiones (11 dígitos)</li>
            <li><strong>Punto de Venta:</strong> número habilitado en AFIP para factura electrónica</li>
          </ul>
        </div>
        <div class="pt-2 border-t border-slate-200 dark:border-slate-700">
          <p class="text-[10px] text-slate-400"><i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i> Mantené la clave privada segura. Si la perdés, debés revocar el certificado y generar uno nuevo.</p>
        </div>
      </div>
    </BaseCard>
  </div>
</template>
