<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useCalculadoraStore } from '@/stores/calculadora'
import BaseButton from '@/components/ui/BaseButton.vue'
import { formatCurrency as fc } from '@/composables/useUtils'

const calculadoraStore = useCalculadoraStore()

const isDragging = ref(false)
const dragOffset = ref({ x: 0, y: 0 })
const historialVisible = ref(false)
const btnRef = ref(null)
const panelRef = ref(null)

// Calcular ancho del panel expandido
const panelWidth = 280

// Arrastrar en estado minimizado (icono flotante)
function onMouseDownMin(e) {
  if (!e.target.closest('.calc-drag-handle')) return
  isDragging.value = true
  const rect = btnRef.value.getBoundingClientRect()
  dragOffset.value.x = e.clientX - rect.left
  dragOffset.value.y = e.clientY - rect.top
  document.addEventListener('mousemove', onMouseMove)
  document.addEventListener('mouseup', onMouseUp)
  e.preventDefault()
}

function onMouseMove(e) {
  if (!isDragging.value) return
  const store = useCalculadoraStore()
  const w = minimizada.value ? 56 : panelWidth
  const h = minimizada.value ? 56 : 420
  const x = Math.max(0, Math.min(window.innerWidth - w, e.clientX - dragOffset.value.x))
  const y = Math.max(0, Math.min(window.innerHeight - h, e.clientY - dragOffset.value.y))
  store.setPosicion(x, y)
}

function onMouseUp() {
  if (!isDragging.value) return
  isDragging.value = false
  document.removeEventListener('mousemove', onMouseMove)
  document.removeEventListener('mouseup', onMouseUp)
}

// Arrastrar en estado expandido (solo por el header)
function onMouseDownHeader(e) {
  if (!e.target.closest('.calc-drag-handle')) return
  isDragging.value = true
  const panel = e.target.closest('.calc-panel')
  const rect = panel.getBoundingClientRect()
  dragOffset.value.x = e.clientX - rect.left
  dragOffset.value.y = e.clientY - rect.top
  document.addEventListener('mousemove', onMouseMoveExpand)
  document.addEventListener('mouseup', onMouseUpExpand)
  e.preventDefault()
}

function onMouseMoveExpand(e) {
  if (!isDragging.value) return
  const x = Math.max(0, Math.min(window.innerWidth - panelWidth, e.clientX - dragOffset.value.x))
  const y = Math.max(0, Math.min(window.innerHeight - 420, e.clientY - dragOffset.value.y))
  useCalculadoraStore().setPosicion(x, y)
}

function onMouseUpExpand() {
  if (!isDragging.value) return
  isDragging.value = false
  document.removeEventListener('mousemove', onMouseMoveExpand)
  document.removeEventListener('mouseup', onMouseUpExpand)
}

// Atajos de teclado
function onKeydown(e) {
  // Ignorar si está minimizada y no está en el panel
  if (!e.target.closest('.calc-panel') && useCalculadoraStore().minimizada) return

  // Enter = calcular/igual
  if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey) {
    e.preventDefault()
    useCalculadoraStore().calcular()
    return
  }

  // ESC = minimizar
  if (e.key === 'Escape') {
    useCalculadoraStore().toggleMinimizar()
    return
  }

  // Operadores por teclado
  if (['+', '-', '*', '/', '.'].includes(e.key)) {
    e.preventDefault()
    const op = e.key === '*' ? '×' : e.key === '/' ? '÷' : e.key
    useCalculadoraStore().agregarOperador(op)
    return
  }

  // Backspace = borrar último carácter
  if (e.key === 'Backspace') {
    e.preventDefault()
    const store = useCalculadoraStore()
    if (store.expresion.length > 0) {
      store.expresion = store.expresion.slice(0, -1)
    }
    return
  }

  // Escape = minimizar
  if (e.key === 'Escape') {
    useCalculadoraStore().toggleMinimizar()
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})

// Referencias a store
const {
  alcance,
  historial: historialStore,
  toggleMinimizar,
  historialVisible: historialVisibleStore,
  historialVisible: historialVisibleRef
} = useCalculadoraStore()

// Referencias locales para template
const expresion = computed(() => useCalculadoraStore().expresion)
const resultado = computed(() => useCalculadoraStore().resultado)
const minimizada = computed(() => useCalculadoraStore().minimizada)
const historial = computed(() => useCalculadoraStore().historial)
const maximoHistorial = computed(() => useCalculadoraStore().maximoHistorial)

function agregarOperador(op) {
  const calc = useCalculadoraStore()
  calc.agregarOperador(op)
}

function calcular() {
  const calc = useCalculadoraStore()
  calc.calcular()
}

function limpiar() {
  const calc = useCalculadoraStore()
  calc.limpiar()
}

function limpiarTodo() {
  const calc = useCalculadoraStore()
  calc.limpiarTodo()
}

function minimizar() {
  const calc = useCalculadoraStore()
  calc.toggleMinimizar()
}

function toggleHistorial() {
  const calc = useCalculadoraStore()
  calc.historialVisible = !calc.historialVisible
}

function limpiarHistorial() {
  const calc = useCalculadoraStore()
  calc.limpiarHistorial()
}

const botones = [
  { op: '+', label: '+', clase: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' },
  { op: '-', label: '−', clase: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300' },
  { op: '×', label: '×', clase: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' },
  { op: '÷', label: '÷', clase: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300' },
  { op: '.', label: '.', clase: 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300' },
  { op: '=', label: '=', clase: 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300', accion: 'calcular' },
  { op: 'C', label: 'C', clase: 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300', accion: 'limpiar' },
  { op: 'AC', label: 'AC', clase: 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300', accion: 'limpiarTodo' }
]

const displayValue = computed(() => {
  const calc = useCalculadoraStore()
  if (calculadoraStore.expresion) return calculadoraStore.expresion
  if (calculadoraStore.resultado !== null) return String(calculadoraStore.resultado)
  return '0'
})

// Helper para formatear números con separador de miles
function formatearNumero(n) {
  if (n === null || n === undefined) return '0'
  return Number(n).toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

</script>

<template>
  <!-- Estado minimizado: botón flotante -->
  <div
    v-if="minimizada"
    ref="btnRef"
    class="calc-fab fixed z-[100] w-14 h-14 rounded-2xl shadow-lg flex items-center justify-center cursor-move bg-brand-600 text-white shadow-xl hover:shadow-2xl transition-all duration-200"
    :style="{ left: posicion.x + 'px', top: posicion.y + 'px' }"
    @mousedown="onMouseDownMin"
    @click="minimizada = false"
    title="Calculadora - Click para expandir"
  >
    <i class="fa-solid fa-calculator text-2xl"></i>
    <div class="calc-drag-handle absolute inset-0" @mousedown="onMouseDownMin" />
  </div>

  <!-- Estado expandido: panel calculadora -->
  <div
    v-else
    ref="panelRef"
    class="calc-panel fixed z-[100] rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900"
    :style="{ width: panelWidth + 'px', left: posicion.x + 'px', top: posicion.y + 'px' }"
  >
    <!-- Header con drag handle y botones -->
    <div class="calc-drag-handle flex items-center justify-between p-3 border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 rounded-t-2xl px-4">
      <div class="flex items-center gap-2">
        <i class="fa-solid fa-calculator text-brand-600 text-lg"></i>
        <span class="font-semibold text-slate-900 dark:text-white text-sm">Calculadora</span>
      </div>
      <div class="flex items-center gap-1">
        <button
          @click="historialVisible = !historialVisible"
          class="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          :title="historialVisible ? 'Ocultar historial' : 'Ver historial'"
        >
          <i class="fa-solid fa-history" :class="historialVisible ? 'text-brand-600' : 'text-slate-400'"></i>
        </button>
        <button
          @click="toggleMinimizar"
          class="p-1.5 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          title="Minimizar (ESC)"
        >
          <i class="fa-solid fa-window-minimize"></i>
        </button>
      </div>
    </div>

    <!-- Historial lateral -->
    <div v-if="historialVisible" class="absolute left-full top-0 h-full w-64 bg-white dark:bg-slate-900 border-l border-slate-200 dark:border-slate-700 rounded-tr-2xl rounded-br-2xl overflow-y-auto p-3">
      <div class="flex items-center justify-between mb-3">
        <h4 class="font-semibold text-slate-900 dark:text-white text-sm">Historial ({{ historial.length }})</h4>
        <button @click="limpiarHistorial" class="text-xs text-red-600 hover:text-red-700 font-medium">Limpiar</button>
      </div>
      <div v-if="historial.length" class="space-y-2 max-h-[300px] overflow-y-auto">
        <div v-for="h in historial" :key="h.id" class="p-2 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-700">
          <div class="text-xs text-slate-500 dark:text-slate-400 mb-1">{{ h.expresion }}</div>
          <div class="font-mono-data font-bold text-slate-900 dark:text-white text-right">{{ fc(h.resultado) }}</div>
          <div class="text-[10px] text-slate-400 mt-0.5">{{ new Date(h.fecha).toLocaleString('es-AR') }}</div>
        </div>
      </div>
      <div v-else class="text-center py-6 text-slate-400 text-sm">Sin historial</div>
    </div>

    <!-- Display -->
    <div class="p-4 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
      <div class="text-right min-h-[40px]">
        <div class="text-sm text-slate-500 dark:text-slate-400 mb-1 h-5">{{ expresion || ' ' }}</div>
        <div class="font-mono-data font-bold text-3xl text-slate-900 dark:text-white min-h-[40px] truncate">{{ displayValue }}</div>
      </div>
    </div>

    <!-- Botones de operaciones -->
    <div class="grid grid-cols-4 gap-2 p-3">
      <template v-for="btn in botones" :key="btn.op">
        <button
          :class="[
            'w-full h-12 rounded-xl font-bold text-base transition-all duration-100',
            'active:scale-95',
            'focus:outline-none focus:ring-2 focus:ring-brand-500/50',
            btn.clase,
            btn.accion === 'calcular' && 'ring-2 ring-emerald-500/50',
            btn.accion === 'limpiar' && 'ring-2 ring-rose-500/50',
            btn.accion === 'limpiarTodo' && 'ring-2 ring-rose-500/50'
          ]"
          @click="btn.accion ? window[btn.accion]() : agregarOperador(btn.op)"
          :disabled="btn.accion === 'calcular' && !expresion"
        >
          {{ btn.label }}
        </button>
      </template>
    </div>

    <!-- Historial inferior (cuando no hay panel lateral) -->
    <div v-if="!historialVisible && historial.length" class="border-t border-slate-200 dark:border-slate-700 p-3 max-h-32 overflow-y-auto">
      <div class="flex items-center justify-between mb-2">
        <span class="text-xs font-semibold text-slate-500 dark:text-slate-400">Historial ({{ historial.length }})</span>
        <button @click="limpiarHistorial" class="text-xs text-red-600 hover:text-red-700 font-medium">Limpiar</button>
      </div>
      <div class="space-y-1 max-h-24 overflow-y-auto">
        <div v-for="h in historial.slice().reverse()" :key="h.id" class="p-1.5 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-100 dark:border-slate-700">
          <div class="text-xs text-slate-500 dark:text-slate-400 truncate">{{ h.expresion }}</div>
          <div class="flex justify-between items-center">
            <span class="text-[10px] text-slate-400">{{ new Date(h.fecha).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }) }}</span>
            <span class="font-mono-data font-bold text-slate-900 dark:text-white">{{ fc(h.resultado) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>