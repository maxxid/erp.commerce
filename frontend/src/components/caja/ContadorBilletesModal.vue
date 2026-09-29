<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { formatCurrency as fc } from '@/composables/useUtils'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  titulo: { type: String, default: 'Conteo de efectivo' },
  valorActual: { type: Number, default: 0 },
})

const emit = defineEmits(['update:modelValue', 'aplicar', 'close'])

const BILLETES = [100000, 50000, 20000, 10000, 5000, 2000, 1000]
const MONEDAS = [500, 200, 100, 50, 20, 10, 5, 1]
const DENOMINACIONES = [...BILLETES, ...MONEDAS]

const conteo = ref({})

function reiniciar(conMontoInicial) {
  const nuevo = {}
  for (const d of DENOMINACIONES) nuevo[d] = 0
  let resto = conMontoInicial ? Math.round(Number(props.valorActual) || 0) : 0
  for (const d of DENOMINACIONES) {
    const c = Math.floor(resto / d)
    if (c > 0) {
      nuevo[d] = c
      resto -= c * d
    }
  }
  conteo.value = nuevo
}

watch(() => props.modelValue, val => {
  if (val) reiniciar(true)
}, { immediate: true })

function cantidad(d) {
  return Math.max(0, Number(conteo.value[d]) || 0)
}

function subtotal(d) {
  return cantidad(d) * d
}

function totalDe(lista) {
  return lista.reduce((sum, d) => sum + subtotal(d), 0)
}

function piezasDe(lista) {
  return lista.reduce((sum, d) => sum + cantidad(d), 0)
}

const totalBilletes = computed(() => totalDe(BILLETES))
const totalMonedas = computed(() => totalDe(MONEDAS))
const total = computed(() => totalBilletes.value + totalMonedas.value)
const totalPiezas = computed(() => piezasDe(BILLETES) + piezasDe(MONEDAS))

function formatDenominacion(d) {
  return '$ ' + Number(d).toLocaleString('es-AR')
}

function cerrar() {
  emit('update:modelValue', false)
  emit('close')
}

function aplicar() {
  emit('aplicar', total.value)
  cerrar()
}

function onKeydown(e) {
  if (e.key !== 'Escape' || !props.modelValue) return
  e.stopImmediatePropagation()
  cerrar()
}

onMounted(() => document.addEventListener('keydown', onKeydown, true))
onUnmounted(() => document.removeEventListener('keydown', onKeydown, true))
</script>

<template>
  <BaseModal
    :model-value="modelValue"
    :title="titulo"
    size="lg"
    :close-on-esc="false"
    @update:model-value="cerrar"
  >
    <div class="space-y-4">
      <div class="flex items-center justify-between gap-3">
        <p class="text-xs text-slate-500">Ingresá la cantidad contada de cada denominación. El total se suma solo.</p>
        <BaseButton variant="ghost" size="xs" @click="reiniciar(false)">
          <i class="fa-solid fa-eraser"></i> Limpiar
        </BaseButton>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div class="space-y-2">
          <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Billetes</div>
          <div v-for="d in BILLETES" :key="'b' + d" class="flex items-center gap-2">
            <div class="w-[86px] shrink-0 text-xs font-semibold text-slate-600 dark:text-slate-300 font-mono-data">
              {{ formatDenominacion(d) }}
            </div>
            <input
              v-model.number="conteo[d]"
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              placeholder="0"
              class="w-[70px] shrink-0 px-2 py-1.5 text-sm text-center font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            />
            <div class="flex-1 text-right text-xs font-mono-data" :class="subtotal(d) > 0 ? 'text-slate-700 dark:text-slate-200 font-semibold' : 'text-slate-300 dark:text-slate-600'">
              {{ subtotal(d) > 0 ? fc(subtotal(d)) : '—' }}
            </div>
          </div>
        </div>

        <div class="space-y-2">
          <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Monedas</div>
          <div v-for="d in MONEDAS" :key="'m' + d" class="flex items-center gap-2">
            <div class="w-[86px] shrink-0 text-xs font-semibold text-slate-600 dark:text-slate-300 font-mono-data">
              {{ formatDenominacion(d) }}
            </div>
            <input
              v-model.number="conteo[d]"
              type="number"
              min="0"
              step="1"
              inputmode="numeric"
              placeholder="0"
              class="w-[70px] shrink-0 px-2 py-1.5 text-sm text-center font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            />
            <div class="flex-1 text-right text-xs font-mono-data" :class="subtotal(d) > 0 ? 'text-slate-700 dark:text-slate-200 font-semibold' : 'text-slate-300 dark:text-slate-600'">
              {{ subtotal(d) > 0 ? fc(subtotal(d)) : '—' }}
            </div>
          </div>
        </div>
      </div>

      <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
        <div class="flex items-end justify-between gap-3">
          <div>
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Total contado</div>
            <div class="text-[10px] text-slate-400 mt-0.5">
              {{ totalPiezas }} piezas · billetes {{ fc(totalBilletes) }} · monedas {{ fc(totalMonedas) }}
            </div>
          </div>
          <div class="font-mono-data font-bold text-2xl text-brand-600 dark:text-brand-400">{{ fc(total) }}</div>
        </div>
      </div>

      <div class="flex gap-3">
        <BaseButton variant="secondary" class="flex-1" @click="cerrar">Cancelar</BaseButton>
        <BaseButton variant="primary" class="flex-1" :disabled="total <= 0" @click="aplicar">
          <i class="fa-solid fa-check"></i> Usar {{ fc(total) }}
        </BaseButton>
      </div>
    </div>
  </BaseModal>
</template>
