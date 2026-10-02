<template>
  <BaseModal
    :model-value="modelValue"
    size="lg"
    :close-on-esc="false"
    :title="titulo"
    :hide-footer="true"
    @update:model-value="cerrar"
  >
    <div class="space-y-4">
      <p class="text-[11px] text-slate-500 dark:text-slate-400">
        Cargá una transferencia por fila y apretá
        <span class="px-1 py-0.5 rounded border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 font-mono-data font-bold text-[10px]">Enter</span>
        para pasar a la siguiente. El total es la suma de todas.
      </p>

      <div class="space-y-2">
        <div
          v-for="(fila, i) in filas"
          :key="fila.id"
          class="flex items-center gap-2"
        >
          <span class="w-2 h-2 rounded-full shrink-0" :class="MEDIO_COLORS[fila.medio] || 'bg-amber-500'"></span>
          <select
            v-model="fila.medio"
            class="text-[11px] font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-2 py-2.5 shrink-0 w-[104px]"
          >
            <option v-for="m in MEDIOS" :key="m" :value="m">{{ MEDIO_LABELS[m] }}</option>
          </select>
          <div class="relative flex-1">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-xs font-semibold">$</span>
            <input
              :ref="el => registrarRef(el, i)"
              v-model.number="fila.monto"
              type="number"
              min="0"
              step="0.01"
              inputmode="decimal"
              placeholder="0.00"
              class="w-full pl-7 pr-3 py-2.5 text-sm font-mono-data font-bold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              @keydown.enter.prevent="agregarFila(i)"
            />
          </div>
          <button
            v-if="filas.length > 1"
            type="button"
            class="text-slate-400 hover:text-rose-500 transition shrink-0 w-7"
            title="Quitar esta transferencia"
            @click="quitarFila(i)"
          >
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
      </div>

      <button
        type="button"
        class="w-full py-2 text-[11px] font-semibold text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 border border-dashed border-slate-300 dark:border-slate-600 rounded-lg transition"
        @click="agregarFila(filas.length - 1)"
      >
        <i class="fa-solid fa-plus"></i> Agregar otra transferencia
      </button>

      <div
        v-if="sobrante != 0"
        class="flex items-start gap-2 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-2.5"
      >
        <i class="fa-solid fa-circle-exclamation text-amber-500 mt-0.5"></i>
        <p class="text-[11px] text-amber-700 dark:text-amber-300">
          Te faltan {{ fc(Math.abs(sobrante)) }} para llegar al monto de la app.
        </p>
      </div>

      <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4 flex items-center justify-between">
        <span class="text-sm font-semibold text-slate-700 dark:text-slate-200">
          {{ filas.length }} transferencia{{ filas.length === 1 ? '' : 's' }}
        </span>
        <span class="font-mono-data font-bold text-2xl text-amber-600 dark:text-amber-400">
          {{ fc(total) }}
        </span>
      </div>

      <div class="flex gap-3 pt-1">
        <BaseButton variant="secondary" class="flex-1" @click="cerrar">Cancelar</BaseButton>
        <BaseButton variant="primary" class="flex-1" :disabled="total <= 0" @click="aplicar">
          <i class="fa-solid fa-check"></i> Usar {{ fc(total) }}
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  titulo: { type: String, default: 'Contar transferencias' },
  valorActual: { type: Number, default: 0 },
  valorEsperado: { type: Number, default: 0 },
  medioPorDefecto: { type: String, default: 'transferencia' },
})

const emit = defineEmits(['update:modelValue', 'aplicar', 'close'])

// Solo los medios que no son efectivo: acá no se cuenta plata, se cuentan
// transferencias. El cajón tiene su propio contador de billetes.
const MEDIOS = ['transferencia', 'smartpoint', 'mercadopago_qr', 'mercadopago_pos', 'qr_interop', 'debito', 'credito']
const MEDIO_LABELS = {
  transferencia: 'Transferencia',
  smartpoint: 'SmartPoint',
  mercadopago_qr: 'MP QR',
  mercadopago_pos: 'MP POS',
  qr_interop: 'QR Interop.',
  debito: 'Débito',
  credito: 'Crédito',
}
const MEDIO_COLORS = {
  transferencia: 'bg-amber-500',
  smartpoint: 'bg-indigo-500',
  mercadopago_qr: 'bg-sky-500',
  mercadopago_pos: 'bg-cyan-500',
  qr_interop: 'bg-teal-500',
  debito: 'bg-violet-500',
  credito: 'bg-pink-500',
}

let seq = 0
const filas = ref([nuevaFila()])
const inputs = ref([])

function nuevaFila(monto = 0, medio = null) {
  seq += 1
  return { id: seq, monto, medio: medio || props.medioPorDefecto }
}

const total = computed(() =>
  filas.value.reduce((suma, f) => suma + (Number(f.monto) || 0), 0)
)

// Solo sirve para el aviso: si el monto cargado no cierra con lo que dice la
// app, avisarlo. No bloquea, porque el arqueo tiene que registrar lo que la
// persona cuenta, no lo que debería haber contado.
const sobrante = computed(() => (Number(props.valorEsperado) || 0) - total.value)

function registrarRef(el, i) {
  // Vue llama con null cuando el elemento se desmonta.
  if (el) inputs.value[i] = el
  else inputs.value[i] = null
}

function enfocar(i) {
  const el = inputs.value[i]
  if (el) {
    el.focus()
    el.select()
  }
}

function agregarFila(desde) {
  filas.value.push(nuevaFila())
  nextTick(() => enfocar(filas.value.length - 1))
}

function quitarFila(i) {
  filas.value.splice(i, 1)
  nextTick(() => enfocar(Math.min(i, filas.value.length - 1)))
}

function reiniciar() {
  filas.value = [nuevaFila()]
  inputs.value = []
  nextTick(() => enfocar(0))
}

function cerrar() {
  emit('update:modelValue', false)
  emit('close')
}

function aplicar() {
  emit('aplicar', total.value)
  cerrar()
}

// Con un solo monto cargado conviene que venga en la primera fila en vez de
// obligar a escribirlo: es el caso normal cuando el saldo de la app ya se
// conoce y se está confirmando.
watch(() => props.modelValue, (abierto) => {
  if (!abierto) return
  const valor = Number(props.valorActual) || 0
  filas.value = valor > 0 ? [nuevaFila(valor)] : [nuevaFila()]
  inputs.value = []
  nextTick(() => enfocar(0))
})

// El BaseModal tiene :close-on-esc="false" para que este manejo no pelee con
// el suyo. Se registra en fase capture, como en ContadorBilletesModal.
function onKeydown(e) {
  if (e.key !== 'Escape' || !props.modelValue) return
  e.stopImmediatePropagation()
  cerrar()
}
onMounted(() => document.addEventListener('keydown', onKeydown, true))
onUnmounted(() => document.removeEventListener('keydown', onKeydown, true))
</script>
