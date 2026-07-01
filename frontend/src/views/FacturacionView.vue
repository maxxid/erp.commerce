<script setup>
import { ref, onMounted } from 'vue'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'

const toast = useToastStore()
const facturas = ref([])
const loading = ref(false)
const emitModal = ref(false)
const selectedVentaId = ref(null)
const emitiendo = ref(false)
const emitResult = ref(null)

async function fetchFacturas() {
  loading.value = true
  try {
    const data = await api.get('/api/facturacion/facturas')
    facturas.value = data || []
  } catch (e) {
    toast.error('Error al cargar facturas')
  }
  loading.value = false
}

function abrirEmitirModal(ventaId) {
  selectedVentaId.value = ventaId
  emitResult.value = null
  emitModal.value = true
}

async function emitirFactura() {
  if (!selectedVentaId.value) return
  emitiendo.value = true
  emitResult.value = null
  try {
    const resp = await api.post(`/api/facturacion/facturas/${selectedVentaId.value}/emitir`)
    emitResult.value = resp
    if (resp.estado === 'rechazada' || resp.error_message) {
      toast.error(`Factura rechazada: ${resp.error_message || resp.estado}`)
    } else {
      toast.success('Factura emitida exitosamente')
    }
    fetchFacturas()
  } catch (e) {
    emitResult.value = { error: e.data?.detail || e.message || 'Error al emitir' }
    toast.error('Error al emitir factura')
  }
  emitiendo.value = false
}

function formatoFecha(fecha) {
  if (!fecha) return '-'
  return new Date(fecha).toLocaleString('es-AR')
}

function estadoBadge(tipo) {
  const map = {
    'emitida': 'success',
    'rechazada': 'danger',
    'pendiente': 'warning',
    'anulada': 'default'
  }
  return map[tipo] || 'default'
}

async function reemitirFactura(ventaId) {
  selectedVentaId.value = ventaId
  await emitirFactura()
}

onMounted(fetchFacturas)
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Facturación Electrónica</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gestión de facturas AFIP</p>
      </div>
      <BaseButton variant="secondary" :loading="loading" @click="fetchFacturas">
        <i class="fa-solid fa-refresh mr-2"></i>Actualizar
      </BaseButton>
    </div>

    <BaseCard>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 dark:border-slate-700">
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">#</th>
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">Venta</th>
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">Tipo</th>
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">CAE</th>
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">Total</th>
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">Estado</th>
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">Fecha</th>
              <th class="text-left py-3 px-4 font-semibold text-slate-600 dark:text-slate-300">Errores</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="9" class="py-8 text-center text-slate-400">
                <i class="fa-solid fa-circle-notch animate-spin text-2xl"></i>
              </td>
            </tr>
            <tr v-else-if="facturas.length === 0">
              <td colspan="9" class="py-8 text-center text-slate-400">
                No hay facturas emitidas
              </td>
            </tr>
            <tr v-for="f in facturas" :key="f.id" class="border-b border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <td class="py-3 px-4 text-slate-500">{{ f.id }}</td>
              <td class="py-3 px-4 font-medium">{{ f.venta_numero || `#${f.venta_id}` }}</td>
              <td class="py-3 px-4">
                <span v-if="f.tipo == '1'" class="text-slate-600 dark:text-slate-300">Factura A</span>
                <span v-else-if="f.tipo == '6'" class="text-slate-600 dark:text-slate-300">Factura B</span>
                <span v-else class="text-slate-600 dark:text-slate-300">Factura C</span>
                <span class="text-slate-400 text-xs ml-1">#{{ f.punto_venta }}-{{ f.numero_fiscal || '-' }}</span>
              </td>
              <td class="py-3 px-4 font-mono text-xs">
                <span v-if="f.cae">{{ f.cae }}</span>
                <span v-else class="text-slate-400">-</span>
              </td>
              <td class="py-3 px-4 font-medium">${{ Number(f.total || 0).toLocaleString('es-AR', { minimumFractionDigits: 2 }) }}</td>
              <td class="py-3 px-4">
                <BaseBadge :variant="estadoBadge(f.estado)" size="sm">
                  {{ f.estado }}
                </BaseBadge>
              </td>
              <td class="py-3 px-4 text-slate-500 text-xs">{{ formatoFecha(f.created_at) }}</td>
              <td class="py-3 px-4 text-red-500 text-xs max-w-[200px] truncate">
                {{ f.error_message || f.resultado === 'R' ? 'Rechazada' : '' }}
              </td>
              <td class="py-3 px-4">
                <BaseButton
                  v-if="f.estado === 'rechazada'"
                  variant="danger"
                  size="xs"
                  :loading="emitiendo && selectedVentaId === f.venta_id"
                  @click="reemitirFactura(f.venta_id)"
                >
                  <i class="fa-solid fa-repeat mr-1"></i>Re-emitir
                </BaseButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseCard>

    <BaseCard title="Configuración AFIP" collapsible>
      <div class="space-y-4 text-sm text-slate-600 dark:text-slate-300">
        <p>La configuración de AFIP se realiza en <router-link to="/ajustes" class="text-brand-600 hover:underline">Ajustes > Facturación</router-link>.</p>
        <ul class="list-disc list-inside space-y-1 text-slate-500">
          <li>CUIT del emisor</li>
          <li>Certificado X.509 (.crt)</li>
          <li>Clave privada RSA (.key)</li>
          <li>Punto de venta habilitado</li>
          <li>Entorno (testing / production)</li>
        </ul>
      </div>
    </BaseCard>

    <BaseCard title="Estado del Sistema" collapsible>
      <div class="space-y-3 text-sm">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-circle text-emerald-500"></i>
          <span class="text-slate-600 dark:text-slate-300">Router de facturación activo</span>
        </div>
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-circle text-emerald-500"></i>
          <span class="text-slate-600 dark:text-slate-300">Integración AFIP (zeep SOAP) lista</span>
        </div>
        <p class="text-xs text-slate-400 mt-2">Para emitir facturas, configurá AFIP en Ajustes y luego usá el botón "Emitir Factura" en cada venta confirmada.</p>
      </div>
    </BaseCard>
  </div>
</template>
