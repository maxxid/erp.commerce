<script setup>
/**
 * Laboratorio de QR interoperable.
 *
 * Sirve para probar payloads contra una billetera real sin deployar. Se pueden
 * generar QRs con los datos de Ajustes o sobreescribiendo cualquier campo, y
 * también analizar un payload pegado a mano (por ejemplo, el QR que da el banco
 * desde el home banking) para compararlo contra el que genera el ERP.
 */
import { ref } from 'vue'
import QRCode from 'qrcode'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const props = defineProps({
  cuit: { type: String, default: '' },
  cuenta: { type: String, default: '' },
  nombre: { type: String, default: '' },
  ciudad: { type: String, default: '' },
  mcc: { type: String, default: '' },
})

const toast = useToastStore()

const monto = ref(100)
const useConfig = ref(true)
const overrides = ref({
  cuit: '',
  cuenta: '',
  nombre: '',
  ciudad: '',
  mcc: '',
})

const generando = ref(false)
const resultado = ref(null)
const imagen = ref('')

const payloadPegado = ref('')
const analisis = ref(null)
const analizando = ref(false)

const CAMPOS = [
  { key: 'cuit', label: 'CUIT', placeholder: '20123456789' },
  { key: 'cuenta', label: 'CBU / alias', placeholder: '0140356312345678901233' },
  { key: 'nombre', label: 'Nombre', placeholder: 'MI COMERCIO' },
  { key: 'ciudad', label: 'Ciudad', placeholder: 'CORDOBA' },
  { key: 'mcc', label: 'MCC', placeholder: '9700' },
]

async function generar(dinamico) {
  generando.value = true
  try {
    const body = {
      monto: Number(monto.value) || 0,
      dinamico,
    }
    if (!useConfig.value) {
      for (const c of CAMPOS) {
        if (overrides.value[c.key]) body[c.key] = overrides.value[c.key]
      }
    }
    const resp = await api.post('/api/pagos/qr-interop/laboratorio', body)
    resultado.value = resp
    imagen.value = resp.qr_data
      ? await QRCode.toDataURL(resp.qr_data, { width: 420, margin: 2 })
      : ''
  } catch (e) {
    resultado.value = null
    imagen.value = ''
    toast.error(e.response?.data?.detail || e.message || 'No se pudo generar el QR')
  } finally {
    generando.value = false
  }
}

async function analizarPegado() {
  const payload = payloadPegado.value.trim()
  if (!payload) {
    toast.warning('Pegá un payload de QR para analizarlo')
    return
  }
  analizando.value = true
  try {
    const resp = await api.post('/api/pagos/qr-interop/analizar', { payload })
    analisis.value = resp
  } catch (e) {
    analisis.value = null
    toast.error(e.response?.data?.detail || e.message || 'No se pudo analizar')
  } finally {
    analizando.value = false
  }
}

function copiar(texto, que) {
  navigator.clipboard.writeText(texto)
  toast.success(`${que} copiado`)
}

</script>

<template>
  <div class="space-y-4">
    <div class="bg-violet-50 dark:bg-violet-900/20 border border-violet-200 dark:border-violet-800 rounded p-3">
      <p class="text-xs text-violet-700 dark:text-violet-300">
        <i class="fa-solid fa-flask mr-1"></i>
        Laboratorio. Generá QRs y probalos con la billetera del celular sin
        deployar nada. El QR se dibuja en el navegador, no se manda a ningún
        servicio externo.
      </p>
    </div>

    <!-- Datos de la prueba -->
    <div class="space-y-3">
      <div class="flex items-center gap-3">
        <span class="text-xs font-semibold text-slate-700 dark:text-slate-300">Datos:</span>
        <button
          v-for="op in [
            { v: true, t: 'De Ajustes' },
            { v: false, t: 'Personalizados' },
          ]"
          :key="String(op.v)"
          :class="[
            'px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors',
            useConfig === op.v
              ? 'bg-brand-500 text-white border-brand-500'
              : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300',
          ]"
          @click="useConfig = op.v"
        >
          {{ op.t }}
        </button>
      </div>

      <div v-if="useConfig" class="bg-slate-50 dark:bg-slate-800/50 rounded p-3 space-y-1">
        <p class="text-xs text-slate-600 dark:text-slate-400">
          <span class="font-semibold">CUIT:</span>
          <span class="font-mono">{{ cuit || '(sin configurar)' }}</span>
        </p>
        <p class="text-xs text-slate-600 dark:text-slate-400">
          <span class="font-semibold">Cuenta:</span>
          <span class="font-mono">{{ cuenta || '(sin configurar)' }}</span>
        </p>
        <p class="text-xs text-slate-600 dark:text-slate-400">
          <span class="font-semibold">Nombre:</span> {{ nombre || '(sin configurar)' }}
          <span v-if="ciudad" class="ml-2"><span class="font-semibold">Ciudad:</span> {{ ciudad }}</span>
          <span class="ml-2"><span class="font-semibold">MCC:</span> {{ mcc || '9700' }}</span>
        </p>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <BaseInput
          v-for="c in CAMPOS"
          :key="c.key"
          v-model="overrides[c.key]"
          :label="c.label"
          :placeholder="c.placeholder"
          size="sm"
        />
      </div>

      <BaseInput
        v-model="monto"
        label="Monto a probar"
        type="number"
        size="sm"
      />

      <div class="flex flex-wrap items-center gap-2 pt-1">
        <BaseButton variant="primary" size="sm" :loading="generando" @click="generar(true)">
          <i class="fa-solid fa-qrcode"></i> Dinámico (monto precargado)
        </BaseButton>
        <BaseButton variant="secondary" size="sm" :loading="generando" @click="generar(false)">
          <i class="fa-solid fa-qrcode"></i> Estático (cliente carga el monto)
        </BaseButton>
      </div>
    </div>

    <!-- Resultado -->
    <div v-if="resultado" class="border border-slate-200 dark:border-slate-700 rounded-lg p-4 space-y-3">
      <div class="flex items-center gap-2 flex-wrap">
        <span
          :class="[
            'text-xs font-semibold px-2 py-1 rounded',
            resultado.dinamico
              ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300'
              : 'bg-sky-100 text-sky-700 dark:bg-sky-900/40 dark:text-sky-300',
          ]"
        >
          {{ resultado.dinamico ? 'DINÁMICO · importe precargado' : 'ESTÁTICO · sin importe' }}
        </span>
        <span
          :class="[
            'text-xs font-semibold px-2 py-1 rounded',
            resultado.crc_ok
              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
              : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
          ]"
        >
          CRC {{ resultado.crc }} {{ resultado.crc_ok ? 'OK' : 'MAL' }}
        </span>
        <span class="text-xs text-slate-500 dark:text-slate-400">
          {{ resultado.qr_data.length }} caracteres
        </span>
      </div>

      <div v-if="resultado.avisos?.length" class="space-y-1">
        <p
          v-for="(a, i) in resultado.avisos"
          :key="i"
          class="text-xs text-amber-700 dark:text-amber-400 flex items-start gap-1"
        >
          <i class="fa-solid fa-triangle-exclamation mt-0.5"></i> {{ a }}
        </p>
      </div>

      <div class="flex flex-col sm:flex-row gap-4 items-start">
        <div v-if="imagen" class="shrink-0 bg-white p-3 rounded-lg border border-slate-200">
          <img :src="imagen" alt="QR de prueba" class="w-56 h-56 sm:w-64 sm:h-64">
        </div>
        <div class="flex-1 min-w-0 space-y-2">
          <p class="text-xs font-semibold text-slate-700 dark:text-slate-300">Payload</p>
          <div class="flex gap-2">
            <textarea
              :value="resultado.qr_data"
              readonly
              rows="4"
              class="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-3 py-2 text-xs font-mono text-slate-800 dark:text-slate-200 break-all resize-none"
            ></textarea>
          </div>
          <button
            class="text-xs text-brand-600 dark:text-brand-400 hover:underline inline-flex items-center gap-1"
            @click="copiar(resultado.qr_data, 'Payload')"
          >
            <i class="fa-solid fa-copy"></i> Copiar payload
          </button>

          <p class="text-xs font-semibold text-slate-700 dark:text-slate-300 pt-2">Campos</p>
          <div class="overflow-x-auto">
            <table class="w-full text-xs font-mono">
              <tbody>
                <tr
                  v-for="c in resultado.campos"
                  :key="c.tag"
                  class="border-b border-slate-100 dark:border-slate-800"
                >
                  <td class="py-1 pr-2 text-slate-400 w-10">{{ c.tag }}</td>
                  <td class="py-1 pr-2 text-slate-400 w-10 text-right">{{ c.largo }}</td>
                  <td class="py-1 text-slate-700 dark:text-slate-300 break-all">{{ c.valor }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Analizar un payload externo -->
    <div class="border-t border-slate-200 dark:border-slate-700 pt-4 space-y-3">
      <p class="text-xs font-semibold text-slate-700 dark:text-slate-300">
        <i class="fa-solid fa-magnifying-glass mr-1"></i>
        Analizar un QR que no es nuestro
      </p>
      <p class="text-[11px] text-slate-500 dark:text-slate-400">
        Pegá el contenido de un QR del banco, de un PSP o de otro ERP para ver
        cómo está armado y compararlo con el nuestro.
      </p>
      <textarea
        v-model="payloadPegado"
        rows="3"
        placeholder="000201010212..."
        class="w-full rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-3 py-2 text-xs font-mono text-slate-800 dark:text-slate-100 placeholder:text-slate-400 focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all"
      ></textarea>
      <BaseButton variant="secondary" size="sm" :loading="analizando" @click="analizarPegado">
        Analizar
      </BaseButton>

      <div v-if="analisis" class="space-y-2 bg-slate-50 dark:bg-slate-800/50 rounded p-3">
        <div class="flex items-center gap-2 flex-wrap">
          <span
            :class="[
              'text-xs font-semibold px-2 py-1 rounded',
              analisis.crc_ok
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
            ]"
          >
            CRC {{ analisis.crc }} {{ analisis.crc_ok ? 'OK' : 'MAL' }}
          </span>
          <span class="text-xs text-slate-500 dark:text-slate-400">
            {{ analisis.campos.length }} campos · {{ analisis.payload.length }} caracteres
          </span>
        </div>

        <p
          v-if="!analisis.crc_ok"
          class="text-xs text-red-600 dark:text-red-400 flex items-start gap-1"
        >
          <i class="fa-solid fa-circle-exclamation mt-0.5"></i>
          El CRC no cierra. O el payload está incompleto, o tiene caracteres que
          se perdieron al copiarlo.
        </p>
        <p v-else-if="!analisis.completo" class="text-xs text-amber-700 dark:text-amber-400">
          <i class="fa-solid fa-triangle-exclamation mr-1"></i>
          Hay bytes después del último campo. Puede ser basura al copiar.
        </p>

        <table class="w-full text-xs font-mono mt-2">
          <tbody>
            <tr
              v-for="c in analisis.campos"
              :key="c.tag + c.largo"
              class="border-b border-slate-200 dark:border-slate-700"
            >
              <td class="py-1 pr-2 text-slate-400 w-10">{{ c.tag }}</td>
              <td class="py-1 pr-2 text-slate-400 w-10 text-right">{{ c.largo }}</td>
              <td class="py-1 text-slate-700 dark:text-slate-300 break-all">{{ c.valor }}</td>
            </tr>
          </tbody>
        </table>

        <details v-if="analisis.comentarios?.length" class="mt-2">
          <summary class="text-xs text-slate-600 dark:text-slate-400 cursor-pointer">
            Observaciones del formato
          </summary>
          <ul class="mt-1 space-y-0.5">
            <li
              v-for="(c, i) in analisis.comentarios"
              :key="i"
              class="text-xs text-slate-600 dark:text-slate-400 list-disc list-inside"
            >
              {{ c }}
            </li>
          </ul>
        </details>
      </div>
    </div>
  </div>
</template>