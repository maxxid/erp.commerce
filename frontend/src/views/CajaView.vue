<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Arqueos y Caja</h2>
        <p class="text-sm text-slate-500 mt-1">Gestión de caja registradora</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton :loading="syncing" :disabled="syncing" variant="secondary" size="sm" @click="syncData">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
        <BaseBadge :variant="cajaStore.abierta ? 'success' : 'danger'" size="sm" dot>
          {{ cajaStore.abierta ? 'Caja Abierta' : 'Caja Cerrada' }}
        </BaseBadge>
        <BaseButton v-if="cajaStore.abierta" :loading="closing" :disabled="closing" variant="danger" size="sm" @click="cerrarCaja">
          <i :class="closing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i>
          {{ closing ? 'Cerrando...' : 'Cerrar Caja' }}
        </BaseButton>
        <BaseButton v-else :loading="opening" :disabled="opening" variant="primary" size="sm" @click="abrirCaja">
          <i :class="opening ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock-open'"></i>
          {{ opening ? 'Abriendo...' : 'Abrir Caja' }}
        </BaseButton>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Saldo Actual</div>
        <div class="text-xl font-bold font-mono-data text-brand-600 mt-1">{{ fc(cajaStore.saldo_actual) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">en caja</div>
      </BaseCard>
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Ingresos del Día</div>
        <div class="text-xl font-bold font-mono-data text-emerald-600 mt-1">{{ fc(ingresosHoy) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">{{ movimientosIngresos }} movimientos</div>
      </BaseCard>
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Egresos del Día</div>
        <div class="text-xl font-bold font-mono-data text-rose-600 mt-1">{{ fc(egresosHoy) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">{{ movimientosEgresos }} movimientos</div>
      </BaseCard>
    </div>

    <!-- Cierre Parcial por Método -->
    <BaseCard v-if="cajaStore.abierta" padding="md" class="space-y-4">
      <h3 class="font-bold text-slate-900 text-sm">Cerrar por Método</h3>
      <div class="flex flex-wrap gap-2">
        <BaseButton v-for="metodo in metodosPago" :key="metodo.valor"
                    :variant="cierreParcial.activo && cierreParcial.metodo === metodo.valor ? 'primary' : 'secondary'"
                    :disabled="cerrandoMetodo || cajaResumen.metodos_cerrados?.includes(metodo.valor)"
                    size="sm"
                    @click="cierreParcial.activo = true; cierreParcial.metodo = metodo.valor; cierreParcial.monto_real = 0; cierreParcial.comentario = ''">
          <i v-if="cajaResumen.metodos_cerrados?.includes(metodo.valor)" class="fa-solid fa-check text-xs"></i>
          {{ metodo.label }}
        </BaseButton>
      </div>

      <div v-if="cierreParcial.activo" class="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-600">
            Cerrando: <span class="text-brand-600">{{ cierreParcial.metodo }}</span>
          </span>
          <BaseButton variant="ghost" size="xs" iconOnly @click="cancelarCierre">
            <i class="fa-solid fa-xmark"></i>
          </BaseButton>
        </div>
        <BaseInput v-model.number="cierreParcial.monto_real" label="Monto Real" type="number" placeholder="0.00" input-class="font-mono-data" />
        <BaseInput v-model="cierreParcial.comentario" label="Comentario (opcional)" placeholder="Nota del cierre" />
        <div class="flex gap-2 pt-1">
          <BaseButton variant="secondary" size="sm" block @click="cancelarCierre">Cancelar</BaseButton>
          <BaseButton :loading="cerrandoMetodo" :disabled="cerrandoMetodo" variant="primary" size="sm" block @click="cerrarMetodo">
            <i :class="cerrandoMetodo ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i>
            {{ cerrandoMetodo ? 'Cerrando...' : 'Cerrar Método' }}
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <div v-if="!cajaStore.abierta" class="bg-amber-50 border border-amber-200 p-4 rounded-2xl text-sm text-amber-700 font-semibold flex items-center gap-2">
      <i class="fa-solid fa-triangle-exclamation"></i>
      La caja está cerrada. Abrila para registrar operaciones.
    </div>

    <BaseCard padding="none">
      <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-slate-900 text-sm">Movimientos del Día</h3>
        <BaseButton v-if="cajaStore.abierta" variant="primary" size="xs" @click="showNuevoMovimiento = true">
          <i class="fa-solid fa-plus"></i> Nuevo Movimiento
        </BaseButton>
      </div>
      <div class="overflow-x-auto">
        <BaseTable v-if="movements.length" :columns="movementColumns" :rows="movements">
          <template #tipo="{ row }">
            <BaseBadge :variant="row.tipo === 'Ingreso' ? 'success' : 'danger'" size="xs">{{ row.tipo }}</BaseBadge>
          </template>
          <template #monto="{ row }">
            <span class="font-mono-data font-bold" :class="row.tipo === 'Ingreso' ? 'text-emerald-600' : 'text-rose-600'">
              {{ row.tipo === 'Ingreso' ? '+' : '-' }} {{ fc(row.monto) }}
            </span>
          </template>
        </BaseTable>
        <EmptyState v-else icon="fa-receipt" title="Sin movimientos" text="No hay movimientos registrados." />
      </div>
    </BaseCard>

    <!-- Modal Nuevo Movimiento -->
    <BaseModal v-model="showNuevoMovimiento" title="Nuevo Movimiento" size="md">
      <div class="space-y-4">
        <BaseSelect v-model="nuevoMovimiento.tipo" label="Tipo" :options="[{ value: 'Ingreso', label: 'Ingreso' }, { value: 'Egreso', label: 'Egreso' }]" />
        <BaseInput v-model.number="nuevoMovimiento.monto" label="Monto" type="number" placeholder="0.00" input-class="font-mono-data" />
        <BaseSelect v-model="nuevoMovimiento.metodo" label="Método" :options="['Efectivo', 'Transferencia', 'Tarjeta']" />
        <BaseInput v-model="nuevoMovimiento.comentario" label="Comentario" placeholder="Descripción del movimiento" />
        <div class="flex gap-2 pt-2">
          <BaseButton variant="secondary" size="sm" block @click="showNuevoMovimiento = false">Cancelar</BaseButton>
          <BaseButton :loading="saving" :disabled="saving" variant="primary" size="sm" block @click="registrarMovimiento">
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ saving ? 'Guardando...' : 'Registrar' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useCajaStore } from '@/stores/caja'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { useSounds } from '@/composables/useSounds'
import { useHeldTickets } from '@/composables/useHeldTickets'

const auth = useAuthStore()
const toast = useToastStore()
const cajaStore = useCajaStore()
const { playOpenCash, playCloseCash } = useSounds()
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

const movementColumns = [
  { key: 'fecha', label: 'Fecha' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'monto', label: 'Monto' },
  { key: 'metodo', label: 'Método' },
  { key: 'comentario', label: 'Comentario' },
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
      cajaStore.saldo_actual = data.saldo_actual ?? cajaStore.saldo_actual
      cajaResumen.metodos_cerrados = data.metodos_cerrados || []
    }
  } catch { /* fallback to mock */ }
}

async function syncData() {
  syncing.value = true
  try {
    await fetchMovimientos()
    await fetchResumen()
    toast.success('Datos sincronizados')
  } catch {
    toast.warning('Error al sincronizar')
  } finally {
    syncing.value = false
  }
}

async function abrirCaja() {
  const monto = parseFloat(prompt('Monto inicial de caja:', '50000') || '0')
  if (!monto || monto <= 0) return
  opening.value = true
  try {
    await api.post('/api/caja/apertura', { monto_inicial: monto })
    await cajaStore.fetchEstado()
    await fetchMovimientos()
    toast.success(`Caja abierta con $${monto.toLocaleString()}`)
    playOpenCash()
  } catch (e) {
    toast.error('Error al abrir caja: ' + (e.message || ''))
  } finally {
    opening.value = false
  }
}

async function cerrarCaja() {
  const { heldCount, deleteHeldTicket, getHeldAuditLog } = useHeldTickets()
  if (heldCount.value > 0) {
    if (!confirm(`Hay ${heldCount.value} ticket(s) apartados en POS. Si cerrás la caja sin recuperarlos se marcarán como huérfanos en la auditoría. ¿Cerrar de todas formas?`)) return
    // mark all current held as orphaned
    const held = JSON.parse(localStorage.getItem('apex-pos-held') || '[]')
    held.forEach(t => { t._orphaned = true })
    localStorage.setItem('apex-pos-held', JSON.stringify(held))
  }
  if (!confirm('¿Cerrar la caja y finalizar la jornada?')) return
  closing.value = true
  try {
    await api.post('/api/caja/cierre-total', { comentario: '' })
    await cajaStore.fetchEstado()
    await fetchMovimientos()
    toast.success('Jornada finalizada. Caja cerrada.')
    playCloseCash()
  } catch (e) {
    toast.error('Error al cerrar caja: ' + (e.message || ''))
  } finally {
    closing.value = false
  }
}

async function registrarMovimiento() {
  if (!nuevoMovimiento.monto || nuevoMovimiento.monto <= 0) {
    toast.warning('Ingresá un monto válido')
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
      cajaStore.saldo_actual += nuevoMovimiento.monto
    } else {
      cajaStore.saldo_actual -= nuevoMovimiento.monto
    }
    nuevoMovimiento.monto = 0
    nuevoMovimiento.comentario = ''
    showNuevoMovimiento.value = false
    toast.success('Movimiento registrado')
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
    toast.warning('Ingresá un monto real válido')
    return
  }
  cerrandoMetodo.value = true
  try {
    await api.post('/api/caja/cierre-metodo', {
      medio_pago: cierreParcial.metodo,
      monto_real: cierreParcial.monto_real,
      comentario: cierreParcial.comentario || '',
    })
    toast.success(`Método ${cierreParcial.metodo} cerrado correctamente`)
    cierreParcial.activo = false
    cierreParcial.metodo = ''
    cierreParcial.monto_real = 0
    cierreParcial.comentario = ''
    await fetchMovimientos()
    await fetchResumen()
  } catch {
    toast.error('Error al cerrar el método')
  } finally {
    cerrandoMetodo.value = false
  }
}
</script>
