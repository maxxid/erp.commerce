<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm"
         @click.self="$emit('close')">
      <div class="bg-white rounded-2xl shadow-2xl max-w-sm w-full max-h-[90vh] overflow-y-auto">
        <div class="flex items-center justify-between p-4 border-b border-slate-100">
          <h3 class="font-bold text-slate-900 text-sm">Ticket de Venta</h3>
          <div class="flex items-center gap-2">
            <button @click="printTicket" class="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1">
              <i class="fa-solid fa-print"></i> Imprimir
            </button>
            <button @click="$emit('close')" class="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition">
              <i class="fa-solid fa-xmark text-xs"></i>
            </button>
          </div>
        </div>

        <!-- Ticket contenido (formato 80/58mm) -->
        <div id="thermal-ticket" class="p-4 font-mono text-[11px] leading-snug text-slate-900"
             :style="{ width: '100%', maxWidth: ticketWidth + 'mm', margin: '0 auto', fontFamily: \"'Courier New',monospace\" }">
          <!-- Encabezado -->
          <div class="text-center border-b-2 border-slate-900 pb-2 mb-2">
            <p class="font-bold text-sm">ApexERP</p>
            <p class="text-[9px] text-slate-500">{{ ticket.sucursal || 'Sucursal Principal' }}</p>
            <p class="text-[9px] text-slate-400">{{ ticket.fecha }}</p>
            <p class="font-bold text-sm mt-1">TICKET #{{ ticket.numero }}</p>
          </div>

          <!-- Items -->
          <div class="space-y-0.5 mb-2">
            <div class="flex justify-between text-[9px] font-bold text-slate-400 border-b border-dotted border-slate-300 pb-0.5">
              <span class="flex-1">Producto</span>
              <span class="w-10 text-right">Cant</span>
              <span class="w-20 text-right">Precio</span>
              <span class="w-20 text-right">Subtotal</span>
            </div>
            <div v-for="(item, i) in ticket.items" :key="i" class="flex justify-between text-[10px]">
              <span class="flex-1 truncate">{{ item.nombre }}</span>
              <span class="w-10 text-right">{{ item.cantidad }}</span>
              <span class="w-20 text-right font-mono-data">{{ fcShort(item.precio_unitario) }}</span>
              <span class="w-20 text-right font-bold">{{ fcShort(item.precio_unitario * item.cantidad) }}</span>
            </div>
          </div>

          <!-- Totales -->
          <div class="border-t border-slate-300 pt-1 space-y-0.5">
            <div class="flex justify-between text-[10px]" v-if="ticket.descuento">
              <span>Descuento</span>
              <span class="font-bold">- {{ fcShort(ticket.descuento) }}</span>
            </div>
            <div class="flex justify-between text-sm font-bold">
              <span>TOTAL</span>
              <span>{{ fcShort(ticket.total) }}</span>
            </div>
          </div>

          <!-- Método de pago y cliente -->
          <div class="border-t border-dotted border-slate-300 mt-2 pt-1 text-[10px] space-y-0.5">
            <div class="flex justify-between">
              <span>Medio de pago</span>
              <span class="font-bold capitalize">{{ ticket.medio_pago }}</span>
            </div>
            <div class="flex justify-between" v-if="ticket.cliente">
              <span>Cliente</span>
              <span class="font-bold">{{ ticket.cliente }}</span>
            </div>
          </div>

          <!-- Footer -->
          <div class="text-center text-[8px] text-slate-400 mt-3 pt-2 border-t border-slate-200">
            <p>Gracias por su compra</p>
            <p>{{ ticket.fecha }}</p>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'

defineProps({
  show: Boolean,
  ticket: { type: Object, default: () => ({ items: [] }) }
})
defineEmits(['close'])

const ticketWidth = computed(() => {
  try {
    const saved = JSON.parse(localStorage.getItem('apex_lookup_settings'))
    return saved?.ticketWidth || 80
  } catch { return 80 }
})

function fcShort(v) {
  if (v == null) return '$0'
  return '$' + Number(v).toLocaleString('es-AR', { minimumFractionDigits: 2 })
}

function printTicket() {
  const el = document.getElementById('thermal-ticket')
  if (!el) return
  const win = window.open('', '_blank', 'width=300,height=600')
  win.document.write(`
    <!DOCTYPE html><html><head><meta charset="UTF-8"><title>Ticket</title>
    <style>
      * { margin:0; padding:0; box-sizing:border-box; }
      body { font-family:'Courier New',monospace; font-size:11px; width:${ticketWidth.value}mm; margin:0 auto; padding:4mm; }
      @page { size:${ticketWidth.value}mm auto; margin:0; }
      @media print { body { width:${ticketWidth.value}mm; } }
    </style></head><body>${el.innerHTML}</body></html>
  `)
  win.document.close()
  setTimeout(() => win.print(), 300)
}
</script>
