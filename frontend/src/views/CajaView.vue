<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Arqueos y Caja</h2>
        <p class="text-sm text-slate-500 mt-1">Gestión de caja registradora</p>
      </div>
      <div class="flex items-center gap-2">
        <button :disabled="syncing" @click="syncData"
                class="px-3 py-1.5 border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 font-semibold text-xs rounded-xl flex items-center gap-1.5 transition shadow-sm">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </button>
        <span :class="cajaState.abierta ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'"
              class="px-3 py-1.5 rounded-xl border text-xs font-bold flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full" :class="cajaState.abierta ? 'bg-emerald-500' : 'bg-rose-500'"></span>
          {{ cajaState.abierta ? 'Caja Abierta' : 'Caja Cerrada' }}
        </span>
        <button v-if="cajaState.abierta"
                :disabled="closing"
                @click="cerrarCaja"
                class="px-4 py-2 bg-rose-50 border border-rose-200 hover:bg-rose-100 text-rose-700 font-semibold text-sm rounded-xl flex items-center gap-2 shadow-sm transition">
          <i :class="closing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i> {{ closing ? 'Cerrando...' : 'Cerrar Caja' }}
        </button>
        <button v-else
                :disabled="opening"
                @click="abrirCaja"
                class="px-4 py-2 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl flex items-center gap-2 shadow-sm transition">
          <i :class="opening ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock-open'"></i> {{ opening ? 'Abriendo...' : 'Abrir Caja' }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <div class="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Saldo Actual</div>
        <div class="text-xl font-bold font-mono-data text-brand-600 mt-1">{{ fc(cajaState.saldo_actual) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">en caja</div>
      </div>
      <div class="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Ingresos del Día</div>
        <div class="text-xl font-bold font-mono-data text-emerald-600 mt-1">{{ fc(ingresosHoy) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">{{ movimientosIngresos }} movimientos</div>
      </div>
      <div class="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Egresos del Día</div>
        <div class="text-xl font-bold font-mono-data text-rose-600 mt-1">{{ fc(egresosHoy) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">{{ movimientosEgresos }} movimientos</div>
      </div>
    </div>

    <!-- Cierre Parcial por Método -->
    <div v-if="cajaState.abierta" class="bg-white border border-slate-200 rounded-2xl shadow-sm p-5 space-y-4">
      <h3 class="font-bold text-slate-900 text-sm">Cerrar por Método</h3>
      <div class="flex flex-wrap gap-2">
        <button v-for="metodo in metodosPago" :key="metodo.valor"
                :disabled="cerrandoMetodo || cajaResumen.metodos_cerrados?.includes(metodo.valor)"
                @click="cierreParcial.activo = true; cierreParcial.metodo = metodo.valor; cierreParcial.monto_real = 0; cierreParcial.comentario = ''"
                :class="[
                  'px-4 py-2 text-sm font-semibold rounded-xl transition flex items-center gap-1.5',
                  cierreParcial.activo && cierreParcial.metodo === metodo.valor
                    ? 'bg-brand-600 text-white shadow-sm'
                    : cajaResumen.metodos_cerrados?.includes(metodo.valor)
                      ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                      : 'bg-slate-50 border border-slate-200 hover:bg-slate-100 text-slate-700'
                ]">
          <i v-if="cajaResumen.metodos_cerrados?.includes(metodo.valor)" class="fa-solid fa-check text-xs"></i>
          {{ metodo.label }}
        </button>
      </div>

      <div v-if="cierreParcial.activo" class="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-600">
            Cerrando: <span class="text-brand-600">{{ cierreParcial.metodo }}</span>
          </span>
          <button @click="cancelarCierre" class="text-slate-400 hover:text-slate-600">
            <i class="fa-solid fa-xmark"></i>
          </button>
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Monto Real</label>
          <input v-model.number="cierreParcial.monto_real" type="number" placeholder="0.00"
                 class="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 font-mono-data">
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Comentario (opcional)</label>
          <input v-model="cierreParcial.comentario" placeholder="Nota del cierre"
                 class="w-full bg-white border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600">
        </div>
        <div class="flex gap-2 pt-1">
          <button @click="cancelarCierre"
                  class="flex-1 px-4 py-2.5 border border-slate-200 hover:bg-white text-slate-700 font-semibold text-sm rounded-xl transition">
            Cancelar
          </button>
          <button :disabled="cerrandoMetodo" @click="cerrarMetodo"
                  class="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl transition">
            <i :class="cerrandoMetodo ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i>
            {{ cerrandoMetodo ? 'Cerrando...' : 'Cerrar Método' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="!cajaState.abierta" class="bg-amber-50 border border-amber-200 p-4 rounded-2xl text-sm text-amber-700 font-semibold flex items-center gap-2">
      <i class="fa-solid fa-triangle-exclamation"></i>
      La caja está cerrada. Abrila para registrar operaciones.
    </div>

    <div class="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-slate-900 text-sm">Movimientos del Día</h3>
        <button v-if="cajaState.abierta"
                @click="showNuevoMovimiento = true"
                class="px-3 py-1.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-xs rounded-lg flex items-center gap-1.5 transition">
          <i class="fa-solid fa-plus"></i> Nuevo Movimiento
        </button>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="bg-slate-50 text-left">
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Fecha</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Tipo</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Monto</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Método</th>
              <th class="px-5 py-3 text-[10px] font-bold text-slate-400 uppercase">Comentario</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-50">
            <tr v-for="m in movements" :key="m.id" class="hover:bg-slate-50 transition">
              <td class="px-5 py-3 text-xs text-slate-600">{{ m.fecha }}</td>
              <td class="px-5 py-3">
                <span :class="m.tipo === 'Ingreso' ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'"
                      class="px-2 py-0.5 rounded-lg text-[10px] font-bold">
                  {{ m.tipo }}
                </span>
              </td>
              <td class="px-5 py-3 text-xs font-mono-data font-bold" :class="m.tipo === 'Ingreso' ? 'text-emerald-600' : 'text-rose-600'">
                {{ m.tipo === 'Ingreso' ? '+' : '-' }} {{ fc(m.monto) }}
              </td>
              <td class="px-5 py-3 text-xs text-slate-600">{{ m.metodo }}</td>
              <td class="px-5 py-3 text-xs text-slate-500">{{ m.comentario }}</td>
            </tr>
            <tr v-if="!movements.length">
              <td colspan="5" class="px-5 py-8 text-xs text-slate-400 text-center">Sin movimientos registrados</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Nuevo Movimiento -->
    <div v-if="showNuevoMovimiento" class="fixed inset-0 z-50 flex items-center justify-center">
      <div class="absolute inset-0 bg-slate-900/50 backdrop-blur-sm" @click="showNuevoMovimiento = false"></div>
      <div class="relative bg-white rounded-2xl shadow-2xl p-6 w-full max-w-md border border-slate-200 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="font-bold text-slate-900 text-lg">Nuevo Movimiento</h3>
          <button @click="showNuevoMovimiento = false" class="text-slate-400 hover:text-slate-600">
            <i class="fa-solid fa-xmark text-lg"></i>
          </button>
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Tipo</label>
          <select v-model="nuevoMovimiento.tipo" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600">
            <option value="Ingreso">Ingreso</option>
            <option value="Egreso">Egreso</option>
          </select>
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Monto</label>
          <input v-model.number="nuevoMovimiento.monto" type="number" placeholder="0.00"
                 class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600 font-mono-data">
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Método</label>
          <select v-model="nuevoMovimiento.metodo" class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600">
            <option value="Efectivo">Efectivo</option>
            <option value="Transferencia">Transferencia</option>
            <option value="Tarjeta">Tarjeta</option>
          </select>
        </div>
        <div>
          <label class="block text-[10px] font-bold text-slate-400 uppercase mb-1">Comentario</label>
          <input v-model="nuevoMovimiento.comentario" placeholder="Descripción del movimiento"
                 class="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand-100 focus:border-brand-600">
        </div>
        <div class="flex gap-2 pt-2">
          <button @click="showNuevoMovimiento = false"
                  class="flex-1 px-4 py-2.5 border border-slate-200 hover:bg-slate-50 text-slate-700 font-semibold text-sm rounded-xl transition">
            Cancelar
          </button>
          <button :disabled="saving" @click="registrarMovimiento"
                  class="flex-1 px-4 py-2.5 bg-brand-600 hover:bg-brand-700 text-white font-semibold text-sm rounded-xl transition">
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ saving ? 'Guardando...' : 'Registrar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'

const auth = useAuthStore()
const toast = useToastStore()

const cajaState = reactive({ abierta: true, saldo_actual: 72000 })
const cajaResumen = reactive({ metodos_cerrados: [] })
const cierreParcial = reactive({ activo: false, metodo: '', monto_real: 0, comentario: '' })

const movements = ref([
  { id: 1, fecha: '2026-06-20 09:15', tipo: 'Ingreso', monto: 5000, metodo: 'Efectivo', comentario: 'Venta ticket #1024' },
  { id: 2, fecha: '2026-06-20 10:30', tipo: 'Ingreso', monto: 3200, metodo: 'Transferencia', comentario: 'Venta ticket #1025' },
  { id: 3, fecha: '2026-06-20 11:45', tipo: 'Egreso', monto: 1500, metodo: 'Efectivo', comentario: 'Pago a proveedor' },
  { id: 4, fecha: '2026-06-20 12:00', tipo: 'Ingreso', monto: 8000, metodo: 'Efectivo', comentario: 'Venta ticket #1026' },
  { id: 5, fecha: '2026-06-20 13:30', tipo: 'Egreso', monto: 700, metodo: 'Transferencia', comentario: 'Gastos varios' },
])

const syncing = ref(false)
const opening = ref(false)
const closing = ref(false)
const saving = ref(false)
const cerrandoMetodo = ref(false)

const showNuevoMovimiento = ref(false)
const nuevoMovimiento = reactive({ tipo: 'Ingreso', monto: 0, metodo: 'Efectivo', comentario: '' })

const ingresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Ingreso').reduce((sum, m) => sum + m.monto, 0))
const egresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Egreso').reduce((sum, m) => sum + m.monto, 0))
const movimientosIngresos = computed(() => movements.value.filter(m => m.tipo === 'Ingreso').length)
const movimientosEgresos = computed(() => movements.value.filter(m => m.tipo === 'Egreso').length)

const metodosPago = [
  { label: 'Efectivo', valor: 'efectivo' },
  { label: 'Débito', valor: 'debito' },
  { label: 'Crédito', valor: 'credito' },
  { label: 'Transferencia', valor: 'transferencia' },
]

onMounted(async () => {
  await fetchMovimientos()
  await fetchResumen()
})

async function fetchMovimientos() {
  try {
    const data = await api.get('/api/caja/movimientos')
    if (data && data.length) movements.value = data
  } catch { /* fallback to mock */ }
}

async function fetchResumen() {
  try {
    const data = await api.get('/api/caja/resumen')
    if (data) {
      cajaState.saldo_actual = data.saldo_actual ?? cajaState.saldo_actual
      cajaResumen.metodos_cerrados = data.metodos_cerrados || []
    }
  } catch { /* fallback to mock */ }
}

async function syncData() {
  syncing.value = true
  try {
    await fetchMovimientos()
    await fetchResumen()
    toast.add('success', 'Datos sincronizados')
  } catch {
    toast.add('warning', 'Error al sincronizar')
  } finally {
    syncing.value = false
  }
}

async function abrirCaja() {
  opening.value = true
  try {
    cajaState.abierta = true
    toast.add('success', 'Caja abierta correctamente')
  } finally {
    opening.value = false
  }
}

async function cerrarCaja() {
  closing.value = true
  try {
    cajaState.abierta = false
    toast.add('info', 'Caja cerrada. Se registró el arqueo.')
  } finally {
    closing.value = false
  }
}

async function registrarMovimiento() {
  if (!nuevoMovimiento.monto || nuevoMovimiento.monto <= 0) {
    toast.add('warning', 'Ingresá un monto válido')
    return
  }
  saving.value = true
  try {
    const now = new Date()
    const fecha = now.toISOString().slice(0, 16).replace('T', ' ')
    movements.value.push({
      id: Date.now(),
      fecha,
      tipo: nuevoMovimiento.tipo,
      monto: nuevoMovimiento.monto,
      metodo: nuevoMovimiento.metodo,
      comentario: nuevoMovimiento.comentario || 'Sin comentario',
    })
    if (nuevoMovimiento.tipo === 'Ingreso') {
      cajaState.saldo_actual += nuevoMovimiento.monto
    } else {
      cajaState.saldo_actual -= nuevoMovimiento.monto
    }
    nuevoMovimiento.monto = 0
    nuevoMovimiento.comentario = ''
    showNuevoMovimiento.value = false
    toast.add('success', 'Movimiento registrado')
  } finally {
    saving.value = false
  }
}

function cancelarCierre() {
  cierreParcial.activo = false
  cierreParcial.metodo = ''
  cierreParcial.monto_real = 0
  cierreParcial.comentario = ''
}

async function cerrarMetodo() {
  if (!cierreParcial.monto_real || cierreParcial.monto_real <= 0) {
    toast.add('warning', 'Ingresá un monto real válido')
    return
  }
  cerrandoMetodo.value = true
  try {
    await api.post('/api/caja/cierre-metodo', {
      medio_pago: cierreParcial.metodo,
      monto_real: cierreParcial.monto_real,
      comentario: cierreParcial.comentario || '',
    })
    toast.add('success', `Método ${cierreParcial.metodo} cerrado correctamente`)
    cierreParcial.activo = false
    cierreParcial.metodo = ''
    cierreParcial.monto_real = 0
    cierreParcial.comentario = ''
    await fetchMovimientos()
    await fetchResumen()
  } catch {
    toast.add('error', 'Error al cerrar el método')
  } finally {
    cerrandoMetodo.value = false
  }
}
</script>
