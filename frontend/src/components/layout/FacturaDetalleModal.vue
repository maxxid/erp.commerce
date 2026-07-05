<script setup>
import { ref, computed } from 'vue'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'

const props = defineProps({
  show: Boolean,
  factura: { type: Object, default: null },
  venta: { type: Object, default: null },
  emisor: { type: Object, default: () => ({}) }
})

const emit = defineEmits(['close', 'reemitir'])
const toast = useToastStore()

const showWhatsappInput = ref(false)
const whatsappNumber = ref('')
const downloadingPdf = ref(false)
const sendingWhatsapp = ref(false)

const condicionIvaLabel = computed(() => {
  const map = {
    'responsable_inscripto': 'Responsable Inscripto',
    'monotributista': 'Monotributista',
    'exento': 'Exento'
  }
  return map[props.emisor.condicion_iva] || props.emisor.condicion_iva || ''
})

const tipoFacturaLabel = computed(() => {
  const tipoMap = { '11': 'C', '1': 'A', '6': 'B' }
  return tipoMap[props.factura?.tipo] || 'C'
})

const numeroFiscalFormateado = computed(() => {
  if (!props.factura?.numero_fiscal) return ''
  const num = String(props.factura.numero_fiscal).padStart(8, '0')
  const ptoVta = String(props.factura.punto_venta || 1).padStart(5, '0')
  return `${ptoVta} - ${num}`
})

const ventaNumero = computed(() => {
  return props.venta?.numero || `V-${String(props.venta?.id || '').padStart(8, '0')}`
})

const fechaEmision = computed(() => {
  if (!props.venta?.fecha) return ''
  return new Date(props.venta.fecha).toLocaleDateString('es-AR')
})

const vencimientoCae = computed(() => {
  if (!props.factura?.vencimiento_cae) return ''
  return new Date(props.factura.vencimiento_cae).toLocaleDateString('es-AR')
})

const receptorLabel = computed(() => {
  if (props.venta?.cliente_nombre && props.venta?.cliente_nombre !== 'Consumidor Final') {
    return props.venta.cliente_nombre
  }
  return 'A CONSUMIDOR FINAL'
})

const receptorDoc = computed(() => {
  if (props.factura?.nro_doc_comprador && props.factura?.nro_doc_comprador !== '0') {
    return `CUIT: ${props.factura.nro_doc_comprador}`
  }
  if (props.venta?.cliente_nombre && props.venta?.cliente_nombre !== 'Consumidor Final') {
    return 'Consumidor Final'
  }
  return ''
})

async function downloadPdf() {
  if (!props.venta?.id) return
  downloadingPdf.value = true
  try {
    const response = await api.get(`/api/facturacion/facturas/${props.venta.id}/pdf`, {
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([response]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `factura_${ventaNumero.value.replace(/[^a-zA-Z0-9]/g, '')}.pdf`)
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(url)
    toast.success('PDF descargado')
  } catch (e) {
    toast.error('Error al descargar PDF')
  } finally {
    downloadingPdf.value = false
  }
}

function printFactura() {
  window.print()
}

async function sendWhatsapp() {
  if (!whatsappNumber.value || whatsappNumber.value.length < 8) {
    toast.warning('Ingresá un número válido')
    return
  }
  sendingWhatsapp.value = true
  try {
    await downloadPdf()
    const message = encodeURIComponent(
      `Hola! Te envío la factura de tu compra.\n` +
      `Número: ${ventaNumero.value}\n` +
      `Total: $${(props.venta?.total || 0).toLocaleString('es-AR', { minimumFractionDigits: 2 })}\n` +
      `CAE: ${props.factura?.cae || 'N/A'}`
    )
    const cleanNumber = whatsappNumber.value.replace(/\D/g, '')
    const fullNumber = cleanNumber.startsWith('54') ? cleanNumber : `54${cleanNumber}`
    window.open(`https://wa.me/${fullNumber}?text=${message}`, '_blank')
    showWhatsappInput.value = false
    whatsappNumber.value = ''
  } catch (e) {
    toast.error('Error al enviar por WhatsApp')
  } finally {
    sendingWhatsapp.value = false
  }
}

function formatCurrency(v) {
  if (v == null) return '$0'
  return '$' + Number(v).toLocaleString('es-AR', { minimumFractionDigits: 2 })
}
</script>

<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm" @click.self="$emit('close')">
      <div class="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between p-4 border-b border-slate-100">
          <h3 class="font-bold text-slate-900 text-sm">Factura Electrónica</h3>
          <div class="flex items-center gap-2">
            <button v-if="factura?.estado === 'rechazada'" @click="$emit('reemitir')" class="px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-xs font-bold transition">
              <i class="fa-solid fa-rotate mr-1"></i> Reemitir
            </button>
            <button @click="$emit('close')" class="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition">
              <i class="fa-solid fa-xmark text-xs"></i>
            </button>
          </div>
        </div>

        <div id="factura-imprimir" class="p-4 font-mono text-[11px] leading-snug text-slate-900 bg-white" style="width: 80mm; margin: 0 auto; font-family: 'Courier New', monospace;">
          <div class="text-center border-b-2 border-slate-900 pb-2 mb-2">
            <p class="font-bold text-sm">{{ emisor.nombre || 'Empresa' }}</p>
            <p class="text-[9px] text-slate-500">{{ emisor.domicilio || '' }}</p>
            <p class="text-[9px] text-slate-400">CUIT: {{ emisor.cuit || '' }}</p>
            <p class="text-[9px] text-slate-400">{{ condicionIvaLabel }}</p>
            <p class="text-[9px] text-slate-400">Ing. Brutos: {{ emisor.ingresos_brutos || 'Exento' }}</p>
            <p class="text-[9px] text-slate-400">Fecha Inicio: {{ emisor.fecha_inicio || '' }}</p>
          </div>

          <div class="text-center border-2 border-slate-900 rounded p-2 mb-2">
            <p class="text-lg font-bold">{{ tipoFacturaLabel }}</p>
            <p class="text-[9px] text-slate-500">Código: {{ factura?.tipo || '011' }}</p>
          </div>

          <div class="text-center border-b border-dotted border-slate-300 pb-2 mb-2">
            <p class="text-[10px] font-bold">Punto de Venta: {{ factura?.punto_venta || '00001' }}</p>
            <p class="text-[10px] font-bold">Comp. Nro: {{ numeroFiscalFormateado || '00000000' }}</p>
            <p class="text-[10px]">Fecha: {{ fechaEmision }}</p>
          </div>

          <div class="border-b border-dotted border-slate-300 pb-2 mb-2">
            <p class="text-[9px] font-bold mb-1">RECEPTOR:</p>
            <p class="text-[10px]">{{ receptorLabel }}</p>
            <p class="text-[9px] text-slate-500">{{ receptorDoc }}</p>
          </div>

          <div class="space-y-0.5 mb-2">
            <div class="flex justify-between text-[9px] font-bold text-slate-400 border-b border-dotted border-slate-300 pb-0.5">
              <span class="flex-1">Producto</span>
              <span class="w-8 text-right">Cant</span>
              <span class="w-16 text-right">Precio</span>
              <span class="w-16 text-right">Subtotal</span>
            </div>
            <div v-for="(item, i) in (venta?.items || [])" :key="i" class="flex justify-between text-[10px]">
              <span class="flex-1 truncate">{{ item.producto_nombre || item.nombre || 'Producto' }}</span>
              <span class="w-8 text-right">{{ item.cantidad }}</span>
              <span class="w-16 text-right">{{ formatCurrency(item.precio_unitario) }}</span>
              <span class="w-16 text-right font-bold">{{ formatCurrency(item.subtotal) }}</span>
            </div>
          </div>

          <div class="border-t border-dotted border-slate-300 pt-1 space-y-0.5">
            <div class="flex justify-between text-[10px]" v-if="venta?.descuento > 0">
              <span>Descuento</span>
              <span class="font-bold">- {{ formatCurrency(venta.descuento) }}</span>
            </div>
            <div class="flex justify-between text-[10px]">
              <span>Neto</span>
              <span>{{ formatCurrency(factura?.neto || venta?.total || 0) }}</span>
            </div>
            <div class="flex justify-between text-[10px]" v-if="factura?.iva > 0">
              <span>IVA</span>
              <span>{{ formatCurrency(factura.iva) }}</span>
            </div>
            <div class="flex justify-between text-sm font-bold border-t border-slate-300 pt-1 mt-1">
              <span>TOTAL</span>
              <span>{{ formatCurrency(factura?.total || venta?.total || 0) }}</span>
            </div>
          </div>

          <div class="border-t border-dotted border-slate-300 mt-2 pt-1 text-center">
            <p class="text-[9px] mb-1">CAI: {{ factura?.cae || 'N/A' }}</p>
            <p class="text-[9px] mb-1">Vencimiento: {{ vencimientoCae || 'N/A' }}</p>
            <p class="text-[9px] text-slate-400">¡Gracias por su compra!</p>
          </div>
        </div>

        <div class="p-4 border-t border-slate-100">
          <p class="text-[10px] text-slate-500 mb-3 text-center">¿Qué desea hacer con esta factura?</p>
          <div class="flex items-center justify-center gap-2">
            <button @click="downloadPdf" :disabled="downloadingPdf" class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-2 disabled:opacity-50">
              <i :class="downloadingPdf ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-file-pdf'"></i>
              PDF
            </button>
            <button @click="printFactura" class="px-4 py-2 bg-slate-600 hover:bg-slate-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-2">
              <i class="fa-solid fa-print"></i>
              Imprimir
            </button>
            <button @click="showWhatsappInput = !showWhatsappInput" class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-2">
              <i class="fa-brands fa-whatsapp"></i>
              WhatsApp
            </button>
          </div>

          <div v-if="showWhatsappInput" class="mt-3 flex items-center gap-2">
            <input v-model="whatsappNumber" type="tel" placeholder="Número sin 0 ni 15" class="flex-1 px-3 py-2 text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500" />
            <button @click="sendWhatsapp" :disabled="sendingWhatsapp" class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs font-bold transition disabled:opacity-50">
              <i :class="sendingWhatsapp ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-paper-plane'"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
@media print {
  body * {
    visibility: hidden;
  }
  #factura-imprimir, #factura-imprimir * {
    visibility: visible;
  }
  #factura-imprimir {
    position: absolute;
    left: 0;
    top: 0;
    width: 80mm;
  }
}
</style>
