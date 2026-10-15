<template>
  <BaseModal v-model="abierto" title="Apertura de Caja" size="md" :hide-footer="true">
    <div class="space-y-5">
      <!-- De dónde sale el número que se sugiere abajo. -->
      <div v-if="efectivoUltimoCierre > 0" class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
        <div class="flex items-center gap-2 mb-2">
          <i class="fa-solid fa-info-circle text-amber-500"></i>
          <span class="font-semibold text-amber-700 dark:text-amber-300 text-sm">Último cierre de caja</span>
          <BaseBadge v-if="ultimoCierre?.fue_automatico" variant="warning" size="xs">Automático</BaseBadge>
        </div>
        <p class="text-xs text-amber-600 dark:text-amber-400 mb-1">
          Efectivo que quedó en el cajón:
          <span class="font-mono-data font-bold">{{ fc(efectivoUltimoCierre) }}</span>
        </p>
        <p class="text-[10px] text-amber-500 dark:text-amber-400">
          Es solo el efectivo del cajón: no incluye lo que quedó en las cuentas digitales
          (MercadoPago, SmartPoint). Se usa como referencia de lo que deberías encontrar.
        </p>
        <p v-if="ultimoCierre?.fecha_local_str" class="text-[10px] text-amber-500 dark:text-amber-400 mt-1">
          Fecha: {{ ultimoCierre.fecha_local_str }}
        </p>
      </div>

      <div class="space-y-4">
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Conté en el cajón</label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">$</span>
            <input
              v-model.number="contado"
              type="number"
              min="0"
              step="100"
              class="w-full pl-7 pr-3 py-2.5 text-lg font-mono-data font-bold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              placeholder="0"
            />
          </div>
          <div class="flex items-center justify-between gap-2 mt-1">
            <p class="text-[10px] text-slate-400">Lo que hay físicamente en el cajón ahora</p>
            <BaseButton variant="ghost" size="xs" @click="abrirContador">
              <i class="fa-solid fa-money-bill-wave"></i> Contar billetes
            </BaseButton>
          </div>
        </div>

        <div class="border-t border-slate-200 dark:border-slate-700 pt-4">
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Dejo en caja (fondo)</label>
          <div class="relative">
            <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">$</span>
            <input
              v-model.number="dejo"
              type="number"
              min="0"
              step="100"
              class="w-full pl-7 pr-3 py-2.5 text-lg font-mono-data font-bold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              placeholder="0"
            />
          </div>
          <p class="text-[10px] text-slate-400 mt-1">Cuánto efectivo querés dejar para vender (fondo / cambio)</p>
        </div>

        <div v-if="retiro > 0" class="border-t border-slate-200 dark:border-slate-700 pt-4">
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Te llevás (retiro)</label>
          <div class="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl px-4 py-3">
            <div class="flex items-center justify-between">
              <span class="text-xs font-semibold text-rose-700 dark:text-rose-300">Sobrante del cajón</span>
              <span class="font-mono-data font-bold text-xl text-rose-600 dark:text-rose-400">{{ fc(retiro) }}</span>
            </div>
            <p class="text-[10px] text-rose-500 dark:text-rose-400 mt-1">
              Se registra como egreso de caja.
            </p>
          </div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1 mt-3">Motivo</label>
          <input
            v-model="motivo_retiro"
            type="text"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            placeholder="Ej: Fondo para cambio, Retiro de efectivo..."
          />
        </div>

        <div class="border-t border-slate-200 dark:border-slate-700 pt-4">
          <div class="flex items-center gap-2 mb-1">
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Saldos iniciales de cuentas digitales</label>
            <BaseButton variant="ghost" size="xs" @click="abrirCuentasDigitales = !abrirCuentasDigitales">
              <i :class="abrirCuentasDigitales ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'"></i>
              {{ abrirCuentasDigitales ? 'Ocultar' : 'Mostrar' }}
            </BaseButton>
          </div>
          <p class="text-[10px] text-slate-400 mb-2">
            Cargá el saldo que muestra hoy cada app. Arranca en 0: se anota lo que ves
            ahora, no lo que quedó ayer.
          </p>
          <div v-if="abrirCuentasDigitales" class="space-y-2">
            <div v-for="cuenta in cuentas" :key="cuenta.valor" class="flex items-center gap-2">
              <div class="flex-1">
                <div class="flex items-center justify-between gap-2">
                  <label class="text-xs text-slate-600 dark:text-slate-300">{{ cuenta.label }}</label>
                  <!-- El saldo de ayer, a la vista pero no cargado. -->
                  <button
                    v-if="saldosUltimos[cuenta.valor] > 0"
                    type="button"
                    class="text-[10px] text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition shrink-0"
                    title="Cargar el saldo con el que quedó en el último cierre"
                    @click="saldos_cuentas[cuenta.valor] = saldosUltimos[cuenta.valor]"
                  >
                    ayer {{ fc(saldosUltimos[cuenta.valor]) }}
                  </button>
                </div>
                <div class="relative mt-0.5">
                  <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">$</span>
                  <input
                    v-model.number="saldos_cuentas[cuenta.valor]"
                    type="number"
                    min="0"
                    step="0.01"
                    inputmode="decimal"
                    class="w-full pl-7 pr-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                    placeholder="0.00"
                  />
                </div>
              </div>
            </div>
          </div>
          <p v-else-if="totalCuentas > 0" class="text-[10px] text-slate-500">
            Cuentas a controlar: {{ cuentasConSaldo }} — total {{ fc(totalCuentas) }}
          </p>
        </div>

        <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Fondo con el que abre la caja</span>
            <span class="font-mono-data font-bold text-2xl text-brand-600 dark:text-brand-400">{{ fc(dejo) }}</span>
          </div>
          <p v-if="retiro > 0" class="text-[10px] text-slate-400 mt-1 text-right">
            conté {{ fc(contado) }} · me llevo {{ fc(retiro) }} · quedan {{ fc(dejo) }}
          </p>
          <div v-if="totalCuentas > 0" class="flex items-center justify-between mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Total a controlar (cajón + cuentas)</span>
            <span class="font-mono-data font-bold text-lg text-indigo-600 dark:text-indigo-400">{{ fc(dejo + totalCuentas) }}</span>
          </div>
        </div>
      </div>

      <div class="flex gap-3 pt-2">
        <BaseButton variant="secondary" class="flex-1" :disabled="loading" @click="cerrar">
          Cancelar
        </BaseButton>
        <BaseButton variant="primary" class="flex-1" :loading="loading" :disabled="loading" @click="confirmar">
          <i :class="loading ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock-open'"></i>
          {{ loading ? 'Abriendo...' : 'Abrir Caja' }}
        </BaseButton>
      </div>

      <ContadorBilletesModal
        v-model="showContador"
        titulo="Contar efectivo — Apertura de caja"
        :valor-actual="contado"
        @aplicar="aplicarConteo"
      />
    </div>
  </BaseModal>
</template>

<script setup>
// Modal único de apertura de caja: el mismo que se usa desde el tab Caja y
// desde el POS. Antes cada vista tenía el suyo, y el del POS quedó con otro
// diseño y otro criterio de cálculo (sugiere el total del cierre anterior,
// incluidas las cuentas digitales, en vez del efectivo del cajón).
//
// Cómo se cuentan los pesos:
//   "Conté en el cajón" es lo que hay físicamente.  "Dejo en caja" es el fondo
//   con el que se quiere abrir.  La diferencia es el retiro, y se calcula sola:
//   el que abre no tiene que hacer la resta de la plata que se lleva.
//
// El backend guarda la apertura con lo que hay en el cajón (max) y genera el
// egreso por el retiro, así que el arqueo del día arranca esperando el fondo.
import { computed, reactive, ref, watch } from 'vue'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc } from '@/composables/useUtils'
import { MEDIOS_CUENTA, MEDIO_LABELS_CUENTA, cuentasEnCero } from '@/composables/cajaCuentas'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import ContadorBilletesModal from '@/components/caja/ContadorBilletesModal.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  // Último cierre de la sesión: monto, saldo_efectivo, fecha_local_str, fue_automatico.
  ultimoCierre: { type: Object, default: null },
  // Saldo con el que quedó cada cuenta digital en el último cierre (solo referencia).
  saldosUltimos: { type: Object, default: () => ({}) },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'confirmar'])

const toast = useToastStore()

const abierto = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const contado = ref(0)
const dejo = ref(0)
const motivo_retiro = ref('')
const saldos_cuentas = reactive(cuentasEnCero())
const abrirCuentasDigitales = ref(false)
const showContador = ref(false)

const cuentas = MEDIOS_CUENTA.map(v => ({ valor: v, label: MEDIO_LABELS_CUENTA[v] }))

// Lo que sugiere "Conté en el cajón": el efectivo del último cierre. No el total
// del cierre, que además suma las cuentas digitales y no está en el cajón.
const efectivoUltimoCierre = computed(() => {
  const u = props.ultimoCierre
  if (!u) return 0
  return Number(u.saldo_efectivo ?? u.monto) || 0
})

const retiro = computed(() => Math.max(0, (Number(contado.value) || 0) - (Number(dejo.value) || 0)))

const cuentasConSaldo = computed(() =>
  cuentas
    .filter(c => (Number(saldos_cuentas[c.valor]) || 0) > 0)
    .map(c => c.label)
    .join(', ')
)

const totalCuentas = computed(() =>
  cuentas.reduce((s, c) => s + (Number(saldos_cuentas[c.valor]) || 0), 0)
)

watch(() => props.modelValue, (abiertoNuevo) => {
  if (!abiertoNuevo) return
  const sugerido = efectivoUltimoCierre.value
  // Se arranca "conté lo del cierre y dejo todo": retiro 0. Si sobra plata en
  // el cajón, baja el fondo y el retiro aparece solo.
  contado.value = sugerido
  dejo.value = sugerido
  motivo_retiro.value = ''
  abrirCuentasDigitales.value = false
  Object.assign(saldos_cuentas, cuentasEnCero())
})

function abrirContador() {
  showContador.value = true
}

function aplicarConteo(total) {
  contado.value = total
  toast.success(`Total contado: ${fc(total)}`)
}

function cerrar() {
  abierto.value = false
}

function confirmar() {
  const contadoNum = Number(contado.value) || 0
  const dejoNum = Number(dejo.value) || 0
  if (contadoNum < 0) {
    toast.error('Lo contado no puede ser negativo')
    return
  }
  if (dejoNum < 0) {
    toast.error('El fondo que dejás no puede ser negativo')
    return
  }
  for (const c of cuentas) {
    if ((Number(saldos_cuentas[c.valor]) || 0) < 0) {
      toast.error(`El saldo inicial de ${c.label} no puede ser negativo`)
      return
    }
  }

  const saldos = {}
  for (const c of cuentas) {
    const v = Number(saldos_cuentas[c.valor]) || 0
    if (v > 0) saldos[c.valor] = v
  }

  emit('confirmar', {
    // Lo que hay en el cajón al abrir. Si el dueño agregó plata propia para
    // completar el fondo, manda ese total: el arqueo tiene que arrancar ahí.
    monto_inicial: Math.max(contadoNum, dejoNum),
    monto_retiro: retiro.value,
    motivo_retiro: motivo_retiro.value,
    saldos_cuentas: saldos,
    // Para el mensaje: fondo con el que abre y plata que se lleva.
    fondo: dejoNum,
    contado: contadoNum,
  })
}
</script>
