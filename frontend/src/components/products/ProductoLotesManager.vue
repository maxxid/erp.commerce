<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc, formatDateShort } from '@/composables/useUtils'
import api from '@/services/api'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'

const props = defineProps({
  productoId: { type: [Number, null], required: true },
})

const toast = useToastStore()

const lotes = ref([])
const resumen = ref(null)
const loading = ref(false)
const saving = ref(false)
const removing = ref(false)

const editing = ref(null)
const editForm = reactive({
  codigo_lote: '',
  fecha_vencimiento: '',
  fecha_fabricacion: '',
  costo: null,
  activo: true,
  notas: '',
})

const creating = ref(false)
const createForm = reactive({
  codigo_lote: '',
  fecha_vencimiento: '',
  fecha_fabricacion: '',
  cantidad: 1,
  costo: null,
  notas: '',
})

const removeTarget = ref(null)

async function load() {
  if (!props.productoId) return
  loading.value = true
  try {
    const [l, r] = await Promise.all([
      api.get(`/api/lotes?producto_id=${props.productoId}&page_size=200`),
      api.get(`/api/lotes/producto/${props.productoId}/resumen`),
    ])
    lotes.value = Array.isArray(l) ? l : []
    resumen.value = r || null
  } catch {
    lotes.value = []
    resumen.value = null
  }
  loading.value = false
}

watch(() => props.productoId, (val) => {
  if (val) load()
}, { immediate: true })

onMounted(() => {
  if (props.productoId) load()
})

function vtoBadge(lote) {
  if (!lote.fecha_vencimiento) return null
  if (lote.vencido) return { variant: 'danger', label: 'Vencido' }
  const d = lote.dias_para_vencer
  if (d <= 7) return { variant: 'danger', label: `Vence en ${d}d` }
  if (d <= 15) return { variant: 'warning', label: `Vence en ${d}d` }
  if (d <= 30) return { variant: 'info', label: `Vence en ${d}d` }
  return null
}

function openEdit(lote) {
  editing.value = lote
  Object.assign(editForm, {
    codigo_lote: lote.codigo_lote || '',
    fecha_vencimiento: lote.fecha_vencimiento ? lote.fecha_vencimiento.slice(0, 10) : '',
    fecha_fabricacion: lote.fecha_fabricacion ? lote.fecha_fabricacion.slice(0, 10) : '',
    costo: lote.costo ?? null,
    activo: lote.activo,
    notas: lote.notas || '',
  })
}

function closeEdit() {
  editing.value = null
}

async function saveEdit() {
  if (!editing.value) return
  saving.value = true
  try {
    const payload = {
      codigo_lote: editForm.codigo_lote || null,
      fecha_vencimiento: editForm.fecha_vencimiento ? new Date(editForm.fecha_vencimiento).toISOString() : null,
      fecha_fabricacion: editForm.fecha_fabricacion ? new Date(editForm.fecha_fabricacion).toISOString() : null,
      costo: editForm.costo ?? null,
      activo: editForm.activo,
      notas: editForm.notas || null,
    }
    await api.put(`/api/lotes/${editing.value.id}`, payload)
    await load()
    toast.success('Lote actualizado')
    closeEdit()
  } catch (e) {
    toast.error(e.message || 'Error al guardar')
  }
  saving.value = false
}

function openCreate() {
  Object.assign(createForm, {
    codigo_lote: '',
    fecha_vencimiento: '',
    fecha_fabricacion: '',
    cantidad: 1,
    costo: null,
    notas: '',
  })
  creating.value = true
}

function closeCreate() {
  creating.value = false
}

async function saveCreate() {
  if (!createForm.cantidad || createForm.cantidad <= 0) {
    toast.error('La cantidad debe ser mayor a 0')
    return
  }
  saving.value = true
  try {
    const payload = {
      producto_id: props.productoId,
      codigo_lote: createForm.codigo_lote || null,
      fecha_vencimiento: createForm.fecha_vencimiento ? new Date(createForm.fecha_vencimiento).toISOString() : null,
      fecha_fabricacion: createForm.fecha_fabricacion ? new Date(createForm.fecha_fabricacion).toISOString() : null,
      cantidad_inicial: createForm.cantidad,
      cantidad_actual: createForm.cantidad,
      costo: createForm.costo ?? null,
      notas: createForm.notas || null,
    }
    await api.post('/api/lotes', payload)
    await load()
    toast.success('Lote creado')
    closeCreate()
  } catch (e) {
    toast.error(e.message || 'Error al crear lote')
  }
  saving.value = false
}

function confirmRemove(lote) {
  removeTarget.value = lote
}

function cancelRemove() {
  removeTarget.value = null
}

async function executeRemove() {
  if (!removeTarget.value) return
  removing.value = true
  try {
    await api.post(`/api/lotes/${removeTarget.value.id}/desactivar`, {})
    await load()
    toast.success('Lote desactivado')
    removeTarget.value = null
  } catch (e) {
    toast.error(e.message || 'Error al desactivar lote')
  }
  removing.value = false
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <label class="block text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
        Lotes
      </label>
      <div v-if="resumen" class="flex items-center gap-2 text-[10px] font-semibold">
        <span class="text-slate-500 dark:text-slate-400">
          {{ resumen.lotes_activos }} activo{{ resumen.lotes_activos !== 1 ? 's' : '' }}
        </span>
        <BaseBadge v-if="resumen.lotes_vencidos > 0" variant="danger" size="xs">
          {{ resumen.lotes_vencidos }} vencido{{ resumen.lotes_vencidos !== 1 ? 's' : '' }}
        </BaseBadge>
        <BaseBadge v-if="resumen.lotes_por_vencer_30d > 0" variant="warning" size="xs">
          {{ resumen.lotes_por_vencer_30d }} x vencer (30d)
        </BaseBadge>
      </div>
    </div>

    <div v-if="loading" class="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl flex items-center gap-2 text-xs text-slate-500">
      <i class="fa-solid fa-circle-notch fa-spin"></i>
      Cargando lotes...
    </div>

    <div v-else-if="lotes.length === 0" class="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-dashed border-slate-200 dark:border-slate-700 text-center">
      <i class="fa-solid fa-boxes-stacked text-slate-300 dark:text-slate-600 text-lg mb-1"></i>
      <p class="text-xs text-slate-500 dark:text-slate-400">Sin lotes registrados</p>
      <p class="text-[10px] text-slate-400 dark:text-slate-500 mt-1">Se crean automáticamente al recibir compras</p>
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="lote in lotes"
        :key="lote.id"
        class="p-3 bg-white dark:bg-slate-800/40 border rounded-xl"
        :class="[
          lote.vencido ? 'border-red-300 dark:border-red-700/50' :
          lote.dias_para_vencer != null && lote.dias_para_vencer <= 30 ? 'border-amber-300 dark:border-amber-700/50' :
          'border-slate-200 dark:border-slate-700'
        ]"
      >
        <div class="flex items-start gap-3">
          <div class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
            :class="lote.cantidad_actual > 0 ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-slate-100 dark:bg-slate-700'">
            <i class="fa-solid fa-boxes-stacked text-sm"
              :class="lote.cantidad_actual > 0 ? 'text-emerald-500' : 'text-slate-400'"></i>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="text-sm font-semibold text-slate-900 dark:text-white">
                {{ lote.codigo_lote || `Lote #${lote.id}` }}
              </p>
              <BaseBadge v-if="lote.vencido" variant="danger" size="xs">Vencido</BaseBadge>
              <BaseBadge v-else-if="lote.dias_para_vencer != null && lote.dias_para_vencer <= 30" variant="warning" size="xs">
                <i class="fa-solid fa-clock text-[8px]"></i>
                {{ lote.dias_para_vencer }}d
              </BaseBadge>
              <BaseBadge v-if="!lote.activo" variant="default" size="xs">Inactivo</BaseBadge>
            </div>
            <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-500 dark:text-slate-400 font-medium flex-wrap">
              <span class="font-mono-data">
                <i class="fa-solid fa-cubes text-slate-400"></i>
                {{ lote.cantidad_actual }} / {{ lote.cantidad_inicial }}
              </span>
              <span v-if="lote.costo != null">
                <i class="fa-solid fa-coins text-slate-400"></i> {{ fc(lote.costo) }}
              </span>
              <span v-if="lote.fecha_vencimiento">
                <i class="fa-solid fa-calendar text-slate-400"></i> Vto {{ formatDateShort(lote.fecha_vencimiento) }}
              </span>
              <span v-else>
                <i class="fa-solid fa-infinity text-slate-400"></i> Sin vencimiento
              </span>
            </div>
            <p v-if="lote.notas" class="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400 italic line-clamp-2">
              {{ lote.notas }}
            </p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button
              type="button"
              title="Editar"
              class="w-7 h-7 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 flex items-center justify-center transition"
              @click="openEdit(lote)"
            >
              <i class="fa-solid fa-pen text-[10px]"></i>
            </button>
            <button
              v-if="lote.activo"
              type="button"
              title="Desactivar"
              class="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex items-center justify-center transition"
              @click="confirmRemove(lote)"
            >
              <i class="fa-solid fa-trash text-[10px]"></i>
            </button>
          </div>
        </div>
      </li>
    </ul>

    <div class="flex justify-end">
      <BaseButton variant="secondary" size="sm" @click="openCreate">
        <i class="fa-solid fa-plus"></i> Nuevo Lote Manual
      </BaseButton>
    </div>

    <BaseModal :model-value="!!editing" :title="`Editar lote: ${editing?.codigo_lote || ''}`" size="md" @update:model-value="closeEdit">
      <form class="space-y-4" @submit.prevent="saveEdit">
        <BaseInput v-model="editForm.codigo_lote" label="Código del lote" placeholder="Ej: C-00001-I1" input-class="font-mono-data" />

        <div class="grid grid-cols-2 gap-4">
          <BaseInput v-model="editForm.fecha_fabricacion" label="Fecha de fabricación" type="date" />
          <BaseInput v-model="editForm.fecha_vencimiento" label="Fecha de vencimiento" type="date" />
        </div>

        <BaseInput
          v-model.number="editForm.costo"
          label="Costo unitario"
          type="number"
          step="0.01"
          min="0"
          input-class="font-mono-data text-right"
        />

        <div>
          <label class="block mb-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">Notas</label>
          <textarea
            v-model="editForm.notas"
            rows="2"
            placeholder="Observaciones del lote..."
            class="w-full px-3.5 py-2.5 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition resize-none"
          />
        </div>

        <label class="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300">
          <input v-model="editForm.activo" type="checkbox" class="rounded border-slate-300 text-brand-600 focus:ring-brand-500" />
          Lote activo (participa en FEFO)
        </label>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" type="button" @click="closeEdit">Cancelar</BaseButton>
          <BaseButton variant="primary" type="submit" :loading="saving" class="flex-1">
            <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
            {{ saving ? 'Guardando...' : 'Guardar' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <BaseModal :model-value="creating" title="Nuevo lote manual" size="md" @update:model-value="closeCreate">
      <form class="space-y-4" @submit.prevent="saveCreate">
        <p class="text-xs text-slate-500 dark:text-slate-400 -mt-2">
          Crea un lote sin asociar a una compra. Útil para mermas, ajustes, donaciones o stock inicial.
        </p>

        <div class="grid grid-cols-2 gap-4">
          <BaseInput v-model="createForm.codigo_lote" label="Código (opcional)" placeholder="Ej: MANUAL-01" input-class="font-mono-data" />
          <BaseInput
            v-model.number="createForm.cantidad"
            label="Cantidad"
            type="number"
            step="0.01"
            min="0.01"
            required
            input-class="font-mono-data text-right"
          />
        </div>

        <div class="grid grid-cols-2 gap-4">
          <BaseInput v-model="createForm.fecha_fabricacion" label="Fabricación (opcional)" type="date" />
          <BaseInput v-model="createForm.fecha_vencimiento" label="Vencimiento (opcional)" type="date" />
        </div>

        <BaseInput
          v-model.number="createForm.costo"
          label="Costo unitario (opcional)"
          type="number"
          step="0.01"
          min="0"
          input-class="font-mono-data text-right"
        />

        <div>
          <label class="block mb-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">Notas</label>
          <textarea
            v-model="createForm.notas"
            rows="2"
            placeholder="Origen del lote..."
            class="w-full px-3.5 py-2.5 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition resize-none"
          />
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" type="button" @click="closeCreate">Cancelar</BaseButton>
          <BaseButton variant="primary" type="submit" :loading="saving" class="flex-1">
            <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-plus'"></i>
            {{ saving ? 'Creando...' : 'Crear Lote' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <BaseModal :model-value="!!removeTarget" title="Desactivar lote" size="sm" @update:model-value="cancelRemove">
      <div class="text-center">
        <div class="w-12 h-12 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-3">
          <i class="fa-solid fa-boxes-stacked text-red-500 text-xl"></i>
        </div>
        <h3 class="text-lg font-bold text-slate-950 dark:text-white font-display mb-1">Desactivar lote</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
          ¿Desactivar el lote <strong class="text-slate-900 dark:text-slate-100">{{ removeTarget?.codigo_lote }}</strong>? No se incluirá en el despacho FEFO. Solo se permite si no tiene stock.
        </p>
        <div class="flex items-center gap-3">
          <BaseButton variant="secondary" class="flex-1" @click="cancelRemove">Cancelar</BaseButton>
          <BaseButton variant="danger" :loading="removing" class="flex-1" @click="executeRemove">
            <i :class="removing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-trash'"></i>
            {{ removing ? 'Desactivando...' : 'Desactivar' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
