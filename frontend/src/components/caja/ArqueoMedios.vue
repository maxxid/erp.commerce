<template>
  <div class="space-y-3">
    <div
      v-for="metodo in filas"
      :key="metodo.valor"
      class="rounded-xl p-4 border"
      :class="metodo.es_cuenta_digital
        ? 'bg-indigo-50 dark:bg-indigo-900/20 border-indigo-200 dark:border-indigo-800'
        : 'bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700'"
    >
      <div class="flex items-center justify-between mb-3">
        <div class="flex items-center gap-2">
          <span class="w-2 h-2 rounded-full" :class="metodo.colorClass"></span>
          <span class="font-semibold text-slate-900 dark:text-white text-sm">{{ metodo.label }}</span>
          <span v-if="metodo.es_cuenta_digital" class="text-[10px] px-1.5 py-0.5 rounded bg-indigo-100 dark:bg-indigo-900/40 text-indigo-600 dark:text-indigo-300 font-bold">CUENTA DIGITAL</span>
          <span v-if="metodo.cerrado" class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 font-bold">CERRADO</span>
        </div>
        <div class="text-right">
          <p class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Esperado</p>
          <p class="font-mono-data font-bold text-slate-900 dark:text-white">{{ fc(metodo.esperado) }}</p>
        </div>
      </div>

      <div v-if="metodo.es_cuenta_digital" class="flex flex-wrap items-center gap-x-4 gap-y-1 mb-3 text-[10px] font-mono-data text-slate-500 dark:text-slate-400">
        <span>Saldo inicial {{ fc(metodo.apertura) }}</span>
        <span class="text-emerald-600 dark:text-emerald-400">+ ingresos {{ fc(metodo.ingresos) }}</span>
        <span class="text-rose-600 dark:text-rose-400">- egresos {{ fc(metodo.egresos) }}</span>
      </div>

      <div v-if="metodo.falta_saldo_inicial" class="flex items-start gap-2 mb-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg p-2">
        <i class="fa-solid fa-circle-exclamation text-amber-500 mt-0.5"></i>
        <p class="text-[10px] text-amber-700 dark:text-amber-300">
          Esta cuenta se movió pero se abrió caja sin su saldo inicial. Cargá el saldo real de la app igual, pero la diferencia no va a cuadrar hasta que registres el saldo inicial al abrir.
        </p>
      </div>

      <div class="grid grid-cols-2 gap-3">
        <div>
          <div class="flex items-center justify-between gap-2 mb-1">
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">{{ metodo.es_cuenta_digital ? 'Saldo real en la app' : 'Monto Real Contado' }}</label>
            <BaseButton
              v-if="metodo.valor === 'efectivo'"
              variant="ghost"
              size="xs"
              :disabled="bloqueado(metodo)"
              @click="$emit('contar', metodo)"
            >
              <i class="fa-solid fa-money-bill-wave"></i> Contar billetes
            </BaseButton>
          </div>
          <input
            v-model.number="metodo.montoReal"
            type="number"
            min="0"
            step="0.01"
            placeholder="0.00"
            class="w-full px-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="bloqueado(metodo)"
          />
        </div>
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Diferencia</label>
          <div
            class="h-[38px] px-3 py-2 flex items-center rounded-lg border border-slate-200 dark:border-slate-700"
            :class="{
              'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800': diferencia(metodo) > 0,
              'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800': diferencia(metodo) < 0,
              'bg-slate-50 dark:bg-slate-800': diferencia(metodo) === 0 || !metodo.montoReal
            }"
          >
            <span v-if="!metodo.montoReal" class="text-xs text-slate-400">—</span>
            <span v-else-if="diferencia(metodo) > 0" class="font-mono-data font-bold text-emerald-600 dark:text-emerald-400">+{{ fc(diferencia(metodo)) }}</span>
            <span v-else-if="diferencia(metodo) < 0" class="font-mono-data font-bold text-red-600 dark:text-red-400">{{ fc(diferencia(metodo)) }}</span>
            <span v-else class="font-mono-data font-bold text-slate-500">OK</span>
          </div>
        </div>
      </div>

      <div v-if="metodo.montoReal && diferencia(metodo) !== 0" class="mt-2">
        <input
          v-model="metodo.comentario"
          type="text"
          placeholder="Comentario por diferencia (ej: faltante por robo, sobrante por error de precio)"
          class="w-full px-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition"
          :disabled="bloqueado(metodo)"
        />
      </div>
    </div>

    <div class="rounded-xl p-4 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-3">
      <div class="flex items-center justify-between gap-2 flex-wrap">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-money-bill-transfer text-slate-400"></i>
          <span class="font-semibold text-slate-900 dark:text-white text-sm">Extracción de efectivo</span>
        </div>
        <span v-if="totalRetiros > 0" class="font-mono-data font-bold text-rose-600 dark:text-rose-400">-{{ fc(totalRetiros) }}</span>
      </div>

      <p class="text-[10px] text-slate-500 dark:text-slate-400">
        Si dejás plata en el cajón para el día siguiente o la llevás a la caja fuerte, registrala acá. Queda como egreso de la sesión y se descuenta del efectivo esperado, así la cuenta digital sigue cuadrando con lo que ves en la app.
      </p>

      <div v-if="retiros.length" class="space-y-1">
        <div
          v-for="r in retiros"
          :key="r.id"
          class="flex items-center justify-between gap-2 bg-rose-50 dark:bg-rose-900/20 rounded-lg px-3 py-2"
        >
          <div class="min-w-0">
            <span class="font-mono-data font-bold text-rose-700 dark:text-rose-300">{{ fc(r.monto) }}</span>
            <span class="text-[10px] text-rose-500 dark:text-rose-400 ml-2">{{ r.descripcion || 'Extracción' }}</span>
          </div>
          <button
            type="button"
            class="text-slate-400 hover:text-rose-500 transition shrink-0"
            :disabled="disabled"
            title="Deshacer la extracción"
            @click="$emit('borrar-retiro', r)"
          >
            <i class="fa-solid fa-trash-can text-xs"></i>
          </button>
        </div>
        <div v-if="esperadoEfectivo > 0" class="flex items-center justify-between text-[11px] px-1">
          <span class="text-slate-500 dark:text-slate-400">Queda en el cajón</span>
          <span class="font-mono-data font-bold text-slate-700 dark:text-slate-200">{{ fc(esperadoEfectivo) }}</span>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Monto a extraer</label>
          <input
            v-model.number="montoRetiro"
            type="number"
            min="0"
            step="0.01"
            placeholder="0.00"
            class="w-full px-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="disabled"
          />
        </div>
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Motivo (opcional)</label>
          <input
            v-model="motivoRetiro"
            type="text"
            placeholder="Ej: traspaso a caja fuerte"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="disabled"
            @keyup.enter="extraer()"
          />
        </div>
      </div>

      <div class="flex justify-end">
        <BaseButton variant="secondary" size="sm" :loading="guardandoRetiro" :disabled="puedeExtraer" @click="extraer">
          <i class="fa-solid fa-arrow-up-from-bracket"></i> Registrar extracción
        </BaseButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'

const props = defineProps({
  filas: { type: Array, default: () => [] },
  retiros: { type: Array, default: () => [] },
  disabled: { type: Boolean, default: false },
  guardandoRetiro: { type: Boolean, default: false },
  bloquearCerrados: { type: Boolean, default: true },
})

const emit = defineEmits(['contar', 'agregar-retiro', 'borrar-retiro'])

const montoRetiro = ref(0)
const motivoRetiro = ref('')

const totalRetiros = computed(() => props.retiros.reduce((sum, r) => sum + (Number(r.monto) || 0), 0))
const esperadoEfectivo = computed(() => {
  const fila = props.filas.find(f => f.valor === 'efectivo')
  return fila ? Number(fila.esperado) || 0 : 0
})
const puedeExtraer = computed(() => props.disabled || !montoRetiro.value || montoRetiro.value <= 0)

watch(() => props.retiros.length, (nuevo, previo) => {
  if (nuevo > previo) {
    montoRetiro.value = 0
    motivoRetiro.value = ''
  }
})

function diferencia(metodo) {
  return (Number(metodo.montoReal) || 0) - (Number(metodo.esperado) || 0)
}

function bloqueado(metodo) {
  return props.disabled || (props.bloquearCerrados && metodo.cerrado)
}

function extraer() {
  if (puedeExtraer.value) return
  emit('agregar-retiro', { monto: Number(montoRetiro.value), motivo: motivoRetiro.value.trim() })
}
</script>
