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
        ¿Cómo obtener certificado AFIP?
      </h3>
      <ol class="text-xs text-slate-600 dark:text-slate-400 space-y-1 list-decimal list-inside">
        <li>Ingresar a <a href="https://auth.afip.gob.ar/contribuyente_/login.xhtml" target="_blank" class="text-brand-600 underline">auth.afip.gob.ar</a></li>
        <li>Ir a la aplicación <strong>WSASS</strong> (Administración de Certificados)</li>
        <li>Generar un CSR desde el sistema o usar OpenSSL</li>
        <li>Asociar el certificado al servicio <strong>wsfe</strong></li>
        <li>Copiar el certificado firmado (.crt) y la clave privada (.key) en los campos de arriba</li>
        <li>Configurar el CUIT y Punto de Venta</li>
        <li>Seleccionar "Testing" para probar, luego cambiar a "Producción"</li>
      </ol>
    </BaseCard>
  </div>
</template>
