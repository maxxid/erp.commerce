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
            <!-- El efectivo se cuenta por denominación; las cuentas, por
                 transferencia. Un solo botón porque la operación es la misma:
                 cargar el monto real que dice la app. -->
            <BaseButton
              v-else
              variant="ghost"
              size="xs"
              :disabled="bloqueado(metodo)"
              @click="$emit('contar-medio', metodo)"
            >
              <i class="fa-solid fa-list-ol"></i> Contar
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

    <!-- Extracción: en vez de decir cuánto saco, se puede decir cuánto dejo y
         el sistema calcula cuánto sale. Al cerrar caja la pregunta real es "cuánta
         plata dejo en el cajón para mañana", no "cuánto me llevo". -->
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

      <!-- Los dos egressos de la sesión: extracción y pago a proveedor. Van en la
           misma lista porque los dos bajan el esperado del mismo modo. -->
      <div v-if="retiros.length" class="space-y-1">
        <div
          v-for="r in retiros"
          :key="r.id"
          class="flex items-center justify-between gap-2 rounded-lg px-3 py-2"
          :class="r.tipo === 'pago_proveedor'
            ? 'bg-violet-50 dark:bg-violet-900/20'
            : 'bg-rose-50 dark:bg-rose-900/20'"
        >
          <div class="min-w-0">
            <span
              class="font-mono-data font-bold"
              :class="r.tipo === 'pago_proveedor'
                ? 'text-violet-700 dark:text-violet-300'
                : 'text-rose-700 dark:text-rose-300'"
            >{{ fc(r.monto) }}</span>
            <span class="text-[10px] ml-2" :class="r.tipo === 'pago_proveedor' ? 'text-violet-500 dark:text-violet-400' : 'text-rose-500 dark:text-rose-400'">
              {{ r.descripcion || (r.tipo === 'pago_proveedor' ? 'Pago a proveedor' : 'Extracción') }}
            </span>
          </div>
          <button
            type="button"
            class="text-slate-400 hover:text-rose-500 transition shrink-0"
            :disabled="disabled"
            :title="r.tipo === 'pago_proveedor' ? 'Anular el pago' : 'Deshacer la extracción'"
            @click="$emit('borrar-retiro', r)"
          >
            <i class="fa-solid fa-trash-can text-xs"></i>
          </button>
        </div>
        <div v-if="esperadoEfectivo > 0" class="flex items-center justify-between text-[11px] px-1">
          <span class="text-slate-500 dark:text-slate-400">Queda en el cajón con lo ya registrado</span>
          <span class="font-mono-data font-bold text-slate-700 dark:text-slate-200">{{ fc(esperadoEfectivo) }}</span>
        </div>
      </div>

      <!-- El resumen que pedía: cuánto se lleva y cuánto queda. Es la foto de lo
           que pasa si se aprieta el botón, antes de apretarlo. -->
      <div class="grid grid-cols-2 gap-2">
        <div class="rounded-lg bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 px-3 py-2">
          <p class="text-[9px] uppercase tracking-wider text-rose-500 dark:text-rose-400 font-bold">Me llevo</p>
          <p class="font-mono-data font-bold text-lg text-rose-700 dark:text-rose-300">{{ fc(porExtraer) }}</p>
        </div>
        <div class="rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 px-3 py-2">
          <p class="text-[9px] uppercase tracking-wider text-emerald-600 dark:text-emerald-400 font-bold">Queda en cajón</p>
          <p class="font-mono-data font-bold text-lg text-emerald-700 dark:text-emerald-300">{{ fc(esperadoEfectivo - porExtraer) }}</p>
        </div>
      </div>

      <!-- El toggle: elegir cómo se piensa la extracción. -->
      <div class="flex gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-lg">
        <button
          type="button"
          class="flex-1 py-1.5 rounded-md text-[11px] font-semibold transition"
          :class="!porDejo ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400'"
          :disabled="disabled"
          @click="desactivarPorDejo"
        >
          Indico cuánto saco
        </button>
        <button
          type="button"
          class="flex-1 py-1.5 rounded-md text-[11px] font-semibold transition"
          :class="porDejo ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm' : 'text-slate-500 dark:text-slate-400'"
          :disabled="disabled"
          @click="activarPorDejo"
        >
          Indico cuánto dejo
        </button>
      </div>

      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">
            {{ porDejo ? 'Dejo en el cajón' : 'Monto a extraer' }}
          </label>
          <input
            v-model.number="montoRetiro"
            type="number"
            min="0"
            step="0.01"
            inputmode="decimal"
            placeholder="0.00"
            class="w-full px-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="disabled"
            @keyup.enter="extraer()"
          />
        </div>
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Motivo (opcional)</label>
          <input
            v-model="motivoRetiro"
            type="text"
            :placeholder="porDejo ? 'Ej: fondo del día siguiente' : 'Ej: traspaso a caja fuerte'"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="disabled"
            @keyup.enter="extraer()"
          />
        </div>
      </div>

      <p v-if="porDejo" class="text-[10px] text-slate-500 dark:text-slate-400">
        Con {{ fc(montoDejoIngresado) }} en el cajón quedan {{ fc(esperadoEfectivo) - montoDejoIngresado }} para llevarte.
      </p>

      <div class="flex justify-end">
        <BaseButton variant="secondary" size="sm" :loading="guardandoRetiro" :disabled="puedeExtraer" @click="extraer">
          <i class="fa-solid fa-arrow-up-from-bracket"></i> Registrar extracción
        </BaseButton>
      </div>
    </div>

    <!-- Pago a proveedor: es un egreso más, pero lo que se necesita para pagarlo
         no aparece en la app de caja sino en la lista de proveedores. -->
    <div class="rounded-xl p-4 border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 space-y-3">
      <div class="flex items-center justify-between gap-2 flex-wrap">
        <div class="flex items-center gap-2">
          <i class="fa-solid fa-truck-field text-slate-400"></i>
          <span class="font-semibold text-slate-900 dark:text-white text-sm">Pago a proveedor</span>
        </div>
        <span v-if="totalPagosProveedor > 0" class="font-mono-data font-bold text-violet-600 dark:text-violet-400">-{{ fc(totalPagosProveedor) }}</span>
      </div>

      <p class="text-[10px] text-slate-500 dark:text-slate-400">
        Registrá lo que pagaste a un proveedor con plata de la caja. Queda como egreso
        de la sesión, así el arqueo descuenta de la cuenta de la que salió el dinero.
      </p>

      <div class="grid grid-cols-2 gap-2">
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Monto a pagar</label>
          <input
            v-model.number="pagoMonto"
            type="number"
            min="0"
            step="0.01"
            inputmode="decimal"
            placeholder="0.00"
            class="w-full px-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="disabled"
            @keyup.enter="registrarPago()"
          />
        </div>
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Sale de</label>
          <select
            v-model="pagoMedio"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="disabled"
          >
            <option v-for="m in MEDIOS_EGRESO" :key="m.valor" :value="m.valor">{{ m.label }}</option>
          </select>
        </div>
      </div>

      <!-- Elegir de la lista o escribir a mano: los proveedores informales no
           siempre están cargados, y obligar a dar de alta uno para pagar un
           flete es una barrera innecesaria. -->
      <div>
        <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Proveedor</label>
        <input
          v-if="!pagoUsaLista"
          v-model="pagoNombre"
          type="text"
          placeholder="Nombre de a quién le pagaste"
          class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
          :disabled="disabled"
          @keyup.enter="registrarPago()"
        />
        <select
          v-else
          v-model="pagoProveedorId"
          class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
          :disabled="disabled"
          @keyup.enter="registrarPago()"
        >
          <option :value="null">Elegir proveedor...</option>
          <option v-for="p in proveedores" :key="p.id" :value="p.id">{{ p.nombre }}</option>
        </select>
        <button
          v-if="proveedores.length"
          type="button"
          class="text-[10px] font-semibold text-brand-600 dark:text-brand-400 hover:underline mt-1"
          :disabled="disabled"
          @click="pagoUsaLista = !pagoUsaLista"
        >
          {{ pagoUsaLista ? 'Escribir el nombre a mano' : 'Elegir de la lista de proveedores' }}
        </button>
        <p v-else class="text-[10px] text-slate-400 dark:text-slate-500 mt-1">
          No hay proveedores cargados: escribí el nombre a mano.
        </p>
      </div>

      <input
        v-model="pagoDetalle"
        type="text"
        placeholder="Qué compraste (opcional)"
        class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
        :disabled="disabled"
        @keyup.enter="registrarPago()"
      />

      <div class="flex justify-end">
        <BaseButton
          variant="secondary"
          size="sm"
          :loading="guardandoPago"
          :disabled="!puedePagar"
          @click="registrarPago"
        >
          <i class="fa-solid fa-file-invoice-dollar"></i> Registrar pago
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
  proveedores: { type: Array, default: () => [] },
  guardandoPago: { type: Boolean, default: false },
})

const emit = defineEmits(['contar', 'contar-medio', 'agregar-retiro', 'borrar-retiro', 'pago-proveedor'])

const montoRetiro = ref(0)
const motivoRetiro = ref('')

// --- Extracción: por cuánto saco, o por cuánto dejo ---
// Al cerrar caja lo que hay que responder es "cuánta plata dejo para mañana",
// no "cuánto saco". Invertir la cuenta evita el error de restar mal: el
// operador cuenta lo que ve en el cajón y el sistema deduce el resto.
const porDejo = ref(false)

const esperadoEfectivo = computed(() => {
  const fila = props.filas.find(f => f.valor === 'efectivo')
  return fila ? Number(fila.esperado) || 0 : 0
})

// Lo que efectivamente sale del cajón, sea por la vía que se haya elegido.
const porExtraer = computed(() => {
  if (porDejo.value) {
    // Lo que se deja no puede ser más de lo que hay, ni negativo: si el
    // operador se pasa, la extracción es 0 y el error se ve en el arqueo.
    const dejo = Math.min(Math.max(Number(montoRetiro.value) || 0, 0), esperadoEfectivo.value)
    return Math.round((esperadoEfectivo.value - dejo) * 100) / 100
  }
  const monto = Number(montoRetiro.value) || 0
  return Math.min(Math.max(monto, 0), esperadoEfectivo.value)
})

const montoDejoIngresado = computed(() => {
  if (!porDejo.value) return 0
  return Math.min(Math.max(Number(montoRetiro.value) || 0, 0), esperadoEfectivo.value)
})

// La lista de egresos mezcla extracción y pago a proveedor, así que los totales
// se separan por tipo para que cada encabezado muestre lo suyo.
const esPagoProveedor = (r) => r.tipo === 'pago_proveedor'
const totalRetiros = computed(() =>
  props.retiros.filter(r => !esPagoProveedor(r)).reduce((sum, r) => sum + (Number(r.monto) || 0), 0)
)
const totalPagosProveedor = computed(() =>
  props.retiros.filter(esPagoProveedor).reduce((sum, r) => sum + (Number(r.monto) || 0), 0)
)

const puedeExtraer = computed(() => props.disabled || porExtraer.value <= 0)

function activarPorDejo() {
  porDejo.value = true
  // El campo pasa a ser "dejo". Se precarga con lo que quedaría si no se saca
  // nada, que es el punto de partida más común.
  montoRetiro.value = round2(esperadoEfectivo.value)
  motivoRetiro.value = motivoRetiro.value || 'Fondo para el día siguiente'
}

function desactivarPorDejo() {
  if (!porDejo.value) return
  // El número tipeado significa otra cosa en cada modo. Si se lo deja tal cual
  // al volver a "cuánto saco", el operador que escribió 50000 para dejar el
  // fondo del día siguiente termina extrayendo 50000.
  porDejo.value = false
  montoRetiro.value = round2(porExtraer.value)
}

function round2(n) {
  return Math.round((Number(n) || 0) * 100) / 100
}

// Cambiar de medio de pago en el arqueo mueve el esperado de la fila, así que
// el valor precargado en modo "dejo" quedaría desfasado.
watch(esperadoEfectivo, (nuevo) => {
  if (porDejo.value && Number(montoRetiro.value) > 0) {
    montoRetiro.value = round2(nuevo)
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
  emit('agregar-retiro', {
    monto: porExtraer.value,
    motivo: motivoRetiro.value.trim(),
    // Se manda el modo para que el mensaje de la vista sepa si fue extracción
    // o "dejé esto y me llevé el resto".
    por_dejo: porDejo.value,
    dejo: montoDejoIngresado.value,
  })
}

// --- Pago a proveedor ---

const MEDIOS_EGRESO = [
  { valor: 'efectivo', label: 'Efectivo' },
  { valor: 'smartpoint', label: 'SmartPoint' },
  { valor: 'mercadopago_qr', label: 'MercadoPago QR' },
  { valor: 'mercadopago_pos', label: 'MercadoPago POS' },
  { valor: 'qr_interop', label: 'QR Interoperable' },
  { valor: 'transferencia', label: 'Transferencia' },
]

const pagoMonto = ref(0)
const pagoMedio = ref('efectivo')
const pagoNombre = ref('')
const pagoProveedorId = ref(null)
const pagoUsaLista = ref(false)
const pagoDetalle = ref('')

// El nombre del proveedor sale de la lista si se eligió uno, si no del texto.
// El id solo va si de verdad se eligió de la lista: mandar un id con el nombre
// escrito a mano mezclaría los dos datos.
const pagoNombreEfectivo = computed(() => {
  if (pagoUsaLista.value) {
    const p = props.proveedores.find(x => x.id === pagoProveedorId.value)
    return p ? p.nombre : ''
  }
  return pagoNombre.value.trim()
})
const pagoIdEfectivo = computed(() => (pagoUsaLista.value ? pagoProveedorId.value : null))

const puedePagar = computed(() =>
  props.disabled
  || !(Number(pagoMonto.value) > 0)
  || !pagoNombreEfectivo.value
)

function registrarPago() {
  if (puedePagar.value) return
  emit('pago-proveedor', {
    monto: Number(pagoMonto.value),
    proveedor_id: pagoIdEfectivo.value,
    proveedor_nombre: pagoNombreEfectivo.value,
    descripcion: pagoDetalle.value.trim(),
    medio_pago: pagoMedio.value,
  })
}

// Después de guardar, los forms quedan limpios para el siguiente movimiento:
// encadenar varios egresos al cierre es lo normal.
//
// Volver al modo "cuánto saco" no es solo estética. En modo "dejo" con 0 en el
// campo, "Me llevo" muestra todo el efectivo del cajón: si el operador escribe
// a continuación sin mirar la etiqueta, registra una extracción por el monto
// entero. El modo por defecto tiene que ser el que no puede trabarse.
watch(() => props.retiros.length, (nuevo, previo) => {
  if (nuevo <= previo) return
  porDejo.value = false
  montoRetiro.value = 0
  motivoRetiro.value = ''
  // El reset del pago va solo si lo que se agregó fue un pago. Se discrimina
  // por el tipo del primer movimiento de la lista, que el backend devuelve del
  // más nuevo al más viejo.
  if (esPagoProveedor(props.retiros[0])) {
    pagoMonto.value = 0
    pagoNombre.value = ''
    pagoProveedorId.value = null
    pagoDetalle.value = ''
  }
})
</script>
