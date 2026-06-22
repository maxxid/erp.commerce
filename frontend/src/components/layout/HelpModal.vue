<template>
  <Teleport to="body">
    <div v-if="show" class="fixed inset-0 z-50 flex items-center justify-center p-4">
      <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="$emit('close')"></div>
      <div class="relative bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-lg max-h-[85vh] overflow-y-auto">
        <div class="flex items-center justify-between p-5 border-b border-slate-100 sticky top-0 bg-white rounded-t-2xl z-10">
          <h3 class="text-lg font-bold text-slate-950 font-display">Guía Rápida y Atajos de Teclado</h3>
          <button @click="$emit('close')" class="w-8 h-8 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div class="p-5 space-y-4 text-xs text-slate-600 leading-relaxed">

          <div class="p-3 bg-brand-50 border border-brand-100 rounded-xl">
            <h4 class="font-bold text-brand-700 text-sm mb-2"><i class="fa-solid fa-cash-register mr-1"></i> POS de Ventas — Escáner</h4>
            <ul class="space-y-1.5 list-disc pl-4">
              <li><strong>Código de barras:</strong> escaneá o tipeá y presioná <kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">Enter</kbd>. Busca en BD local, catálogo central y Carrefour/Vea/Masonline.</li>
              <li><strong>Carga manual rápida:</strong> <kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">*Nombre*Precio</kbd> + <kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">Enter</kbd>. Ej: <kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">*COCA 1.5L*1500</kbd>. Crea producto al vuelo con stock=10.</li>
              <li><strong>Búsqueda por texto:</strong> tipeá cualquier palabra y la grilla se filtra en vivo. <kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">Enter</kbd> agrega el primer resultado.</li>
            </ul>
          </div>

          <div class="p-3 bg-amber-50 border border-amber-100 rounded-xl">
            <h4 class="font-bold text-amber-700 text-sm mb-2"><i class="fa-solid fa-keyboard mr-1"></i> Atajos de Teclado</h4>
            <div class="grid grid-cols-2 gap-1.5">
              <div class="flex justify-between"><span>Escanear / Buscar</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">Enter</kbd></div>
              <div class="flex justify-between"><span>Ir a medios de pago</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">Tab</kbd></div>
              <div class="flex justify-between"><span>Efectivo</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">1</kbd></div>
              <div class="flex justify-between"><span>Débito</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">2</kbd></div>
              <div class="flex justify-between"><span>Crédito</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">3</kbd></div>
              <div class="flex justify-between"><span>Transferencia</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">4</kbd></div>
              <div class="flex justify-between"><span>Cta. Corriente</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">5</kbd></div>
              <div class="flex justify-between"><span>Navegar medios de pago</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">← →</kbd></div>
              <div class="flex justify-between"><span>Confirmar venta</span><kbd class="bg-slate-200 px-1.5 py-0.5 rounded font-mono text-[10px]">Enter</kbd> (en pagos)</div>
            </div>
          </div>

          <div class="p-3 bg-emerald-50 border border-emerald-100 rounded-xl">
            <h4 class="font-bold text-emerald-700 text-sm mb-2"><i class="fa-solid fa-truck-ramp-box mr-1"></i> Órdenes de Compra (2 pasos)</h4>
            <ol class="space-y-1.5 list-decimal pl-4">
              <li><strong>Crear OC:</strong> elegí proveedor, agregá productos con cantidad y costo. Queda <span class="text-amber-600 font-bold">pendiente</span>.</li>
              <li><strong>Recibir:</strong> cuando llega, botón <span class="text-emerald-600 font-bold">Recibir</span>. Se puede recibir parcial (ej: 7 de 10).</li>
            </ol>
          </div>

          <div class="p-3 bg-slate-50 border border-slate-200 rounded-xl">
            <h4 class="font-bold text-slate-700 text-sm mb-2"><i class="fa-solid fa-lightbulb mr-1"></i> Conceptos Clave</h4>
            <ul class="space-y-1.5 list-disc pl-4">
              <li><strong>Stock en tránsito:</strong> mercadería pedida al proveedor aún no recibida.</li>
              <li><strong>Caja — cierre por método:</strong> cada medio de pago se cierra por separado.</li>
              <li><strong>Cuenta corriente:</strong> ventas a crédito no generan movimiento de caja.</li>
              <li><strong>Soft-delete:</strong> productos y clientes se desactivan, no se borran.</li>
            </ul>
          </div>

          <div class="p-3 bg-indigo-50 border border-indigo-100 rounded-xl">
            <h4 class="font-bold text-indigo-700 text-sm mb-2"><i class="fa-solid fa-magnifying-glass mr-1"></i> Fuentes de Búsqueda</h4>
            <div class="grid grid-cols-2 gap-1 text-[11px]">
              <div><strong>Carrefour</strong> — API VTEX</div>
              <div><strong>Vea</strong> — Scraping HTML</div>
              <div><strong>Masonline</strong> — Scraping HTML</div>
              <div><strong>Super Coco</strong> — Scraping HTML</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
defineProps({ show: Boolean })
defineEmits(['close'])
</script>
