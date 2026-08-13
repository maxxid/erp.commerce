<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'

const props = defineProps({
  productoId: { type: [Number, null], required: true },
  proveedores: { type: Array, default: () => [] },
})

const toast = useToastStore()

const items = ref([])
const loading = ref(false)
const saving = ref(false)
const removing = ref(false)
const selectedToAdd = ref(null)
const adding = ref(false)

const editing = ref(null)
const editForm = reactive({
  codigo_proveedor: '',
  costo: null,
  plazo_entrega_dias: null,
  es_principal: false,
  activo: true,
  notas: '',
})

const removeTarget = ref(null)

const availableProveedores = computed(() => {
  const assigned = new Set(items.value.map(i => i.id))
  return props.proveedores.filter(p => !assigned.has(p.id))
})

const addOptions = computed(() => [
  { value: null, label: 'Seleccionar proveedor...' },
  ...availableProveedores.value.map(p => ({ value: p.id, label: p.nombre })),
])

async function load() {
  if (!props.productoId) {
    items.value = []
    return
  }
  loading.value = true
  try {
    const data = await api.get(`/api/productos/${props.productoId}/proveedores`)
    items.value = Array.isArray(data) ? data : []
  } catch (e) {
    console.error('[ProductoProveedoresManager] load failed:', e)
    items.value = []
  }
  loading.value = false
}

watch(() => props.productoId, (val) => {
  if (val) load()
}, { immediate: true })

onMounted(() => {
  if (props.productoId) load()
})

async function addProveedor() {
  if (!selectedToAdd.value) return
  adding.value = true
  try {
    await api.post(`/api/productos/${props.productoId}/proveedores`, { proveedor_id: selectedToAdd.value })
    await load()
    selectedToAdd.value = null
    toast.success('Proveedor agregado')
  } catch (e) {
    toast.error(e.message || 'Error al agregar proveedor')
  }
  adding.value = false
}

function openEdit(item) {
  editing.value = item
  Object.assign(editForm, {
    codigo_proveedor: item.codigo_proveedor || '',
    costo: item.costo ?? null,
    plazo_entrega_dias: item.plazo_entrega_dias ?? null,
    es_principal: Boolean(item.es_principal),
    activo: item.activo !== 0,
    notas: item.notas || '',
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
      codigo_proveedor: editForm.codigo_proveedor || null,
      costo: editForm.costo ?? null,
      plazo_entrega_dias: editForm.plazo_entrega_dias ?? null,
      es_principal: editForm.es_principal,
      activo: editForm.activo,
      notas: editForm.notas || null,
    }
    await api.put(`/api/productos/${props.productoId}/proveedores/${editing.value.id}`, payload)
    await load()
    toast.success('Datos del proveedor actualizados')
    closeEdit()
  } catch (e) {
    toast.error(e.message || 'Error al guardar')
  }
  saving.value = false
}

async function togglePrincipal(item) {
  if (item.es_principal) return
  try {
    await api.put(`/api/productos/${props.productoId}/proveedores/${item.id}`, { es_principal: true })
    await load()
  } catch (e) {
    toast.error(e.message || 'Error al marcar como principal')
  }
}

async function toggleActivo(item) {
  try {
    await api.put(`/api/productos/${props.productoId}/proveedores/${item.id}`, { activo: !item.activo })
    await load()
  } catch (e) {
    toast.error(e.message || 'Error al cambiar estado')
  }
}

function confirmRemove(item) {
  removeTarget.value = item
}

function cancelRemove() {
  removeTarget.value = null
}

async function executeRemove() {
  if (!removeTarget.value) return
  removing.value = true
  try {
    await api.delete(`/api/productos/${props.productoId}/proveedores/${removeTarget.value.id}`)
    await load()
    toast.success('Proveedor quitado del producto')
    removeTarget.value = null
  } catch (e) {
    toast.error(e.message || 'Error al quitar proveedor')
  }
  removing.value = false
}
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <label class="block text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase">
        Proveedores
      </label>
      <span v-if="items.length" class="text-[10px] text-slate-400 dark:text-slate-500 font-medium">
        {{ items.length }} asignado{{ items.length !== 1 ? 's' : '' }}
      </span>
    </div>

    <div v-if="loading" class="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl flex items-center gap-2 text-xs text-slate-500">
      <i class="fa-solid fa-circle-notch fa-spin"></i>
      Cargando proveedores...
    </div>

    <div v-else-if="items.length === 0" class="p-4 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-dashed border-slate-200 dark:border-slate-700 text-center">
      <i class="fa-solid fa-truck-field text-slate-300 dark:text-slate-600 text-lg mb-1"></i>
      <p class="text-xs text-slate-500 dark:text-slate-400">Sin proveedores asignados</p>
    </div>

    <ul v-else class="space-y-2">
      <li
        v-for="item in items"
        :key="item.id"
        class="p-3 bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 rounded-xl"
      >
        <div class="flex items-start gap-3">
          <div class="w-9 h-9 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center shrink-0">
            <i class="fa-solid fa-truck text-slate-500 dark:text-slate-400 text-sm"></i>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center gap-2 flex-wrap">
              <p class="text-sm font-semibold text-slate-900 dark:text-white truncate">{{ item.nombre }}</p>
              <BaseBadge v-if="item.es_principal" variant="brand" size="xs">
                <i class="fa-solid fa-star text-[8px]"></i> Principal
              </BaseBadge>
              <BaseBadge v-if="!item.activo" variant="default" size="xs">Inactivo</BaseBadge>
            </div>
            <div class="flex items-center gap-3 mt-1 text-[11px] text-slate-500 dark:text-slate-400 font-medium">
              <span v-if="item.codigo_proveedor" class="font-mono-data">
                <i class="fa-solid fa-barcode text-slate-400"></i> {{ item.codigo_proveedor }}
              </span>
              <span v-if="item.costo != null">
                <i class="fa-solid fa-coins text-slate-400"></i> {{ fc(item.costo) }}
              </span>
              <span v-if="item.plazo_entrega_dias != null">
                <i class="fa-solid fa-clock text-slate-400"></i> {{ item.plazo_entrega_dias }}d
              </span>
              <span v-if="item.cuit">
                <i class="fa-solid fa-id-card text-slate-400"></i> {{ item.cuit }}
              </span>
            </div>
            <p v-if="item.notas" class="mt-1.5 text-[11px] text-slate-500 dark:text-slate-400 italic line-clamp-2">
              {{ item.notas }}
            </p>
          </div>
          <div class="flex items-center gap-1 shrink-0">
            <button
              v-if="!item.es_principal"
              type="button"
              title="Marcar como principal"
              class="w-7 h-7 rounded-lg text-slate-400 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/20 flex items-center justify-center transition"
              @click="togglePrincipal(item)"
            >
              <i class="fa-regular fa-star text-[10px]"></i>
            </button>
            <button
              type="button"
              title="Editar datos"
              class="w-7 h-7 rounded-lg text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 flex items-center justify-center transition"
              @click="openEdit(item)"
            >
              <i class="fa-solid fa-pen text-[10px]"></i>
            </button>
            <button
              type="button"
              title="Quitar del producto"
              class="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex items-center justify-center transition"
              @click="confirmRemove(item)"
            >
              <i class="fa-solid fa-trash text-[10px]"></i>
            </button>
          </div>
        </div>
      </li>
    </ul>

    <div v-if="availableProveedores.length" class="flex items-end gap-2">
      <div class="flex-1">
        <BaseSelect
          v-model="selectedToAdd"
          :options="addOptions"
          option-value="value"
          option-label="label"
          placeholder="Seleccionar proveedor..."
        />
      </div>
      <BaseButton
        variant="primary"
        size="md"
        :disabled="!selectedToAdd"
        :loading="adding"
        class="shrink-0"
        @click="addProveedor"
      >
        <i class="fa-solid fa-plus"></i> Agregar
      </BaseButton>
    </div>
    <p v-else-if="!loading && props.proveedores.length > 0" class="text-[11px] text-slate-400 dark:text-slate-500 italic">
      Todos los proveedores disponibles ya están asignados.
    </p>

    <BaseModal :model-value="!!editing" :title="`Editar proveedor: ${editing?.nombre || ''}`" size="md" @update:model-value="closeEdit">
      <form class="space-y-4" @submit.prevent="saveEdit">
        <BaseInput
          v-model="editForm.codigo_proveedor"
          label="Código del proveedor"
          placeholder="SKU / código que usa el proveedor"
          input-class="font-mono-data"
        />

        <div class="grid grid-cols-2 gap-4">
          <BaseInput
            v-model.number="editForm.costo"
            label="Costo"
            type="number"
            step="0.01"
            min="0"
            input-class="font-mono-data text-right"
          />
          <BaseInput
            v-model.number="editForm.plazo_entrega_dias"
            label="Plazo de entrega (días)"
            type="number"
            min="0"
            input-class="font-mono-data text-right"
          />
        </div>

        <div class="space-y-2">
          <BaseToggle
            v-model="editForm.es_principal"
            label="Proveedor principal"
            description="Se usa por defecto al generar órdenes de compra"
          />
          <BaseToggle
            v-model="editForm.activo"
            label="Activo"
            description="Si está inactivo, no se sugiere en nuevas compras"
          />
        </div>

        <div>
          <label class="block mb-1.5 text-xs font-semibold text-slate-700 dark:text-slate-300">
            Notas
          </label>
          <textarea
            v-model="editForm.notas"
            rows="3"
            placeholder="Ej: Mínimo de pedido $20.000, paga a 30 días, entrega martes y viernes..."
            class="w-full px-3.5 py-2.5 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition resize-none"
          />
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" type="button" @click="closeEdit">Cancelar</BaseButton>
          <BaseButton variant="primary" type="submit" :loading="saving" class="flex-1">
            <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
            {{ saving ? 'Guardando...' : 'Guardar' }}
          </BaseButton>
        </div>
      </form>
    </BaseModal>

    <BaseModal :model-value="!!removeTarget" title="Quitar proveedor" size="sm" @update:model-value="cancelRemove">
      <div class="text-center">
        <div class="w-12 h-12 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mx-auto mb-3">
          <i class="fa-solid fa-truck text-red-500 text-xl"></i>
        </div>
        <h3 class="text-lg font-bold text-slate-950 dark:text-white font-display mb-1">Quitar proveedor</h3>
        <p class="text-sm text-slate-500 dark:text-slate-400 mb-5">
          ¿Quitar a <strong class="text-slate-900 dark:text-slate-100">{{ removeTarget?.nombre }}</strong> de este producto? No se elimina el proveedor, solo la relación.
        </p>
        <div class="flex items-center gap-3">
          <BaseButton variant="secondary" class="flex-1" @click="cancelRemove">Cancelar</BaseButton>
          <BaseButton variant="danger" :loading="removing" class="flex-1" @click="executeRemove">
            <i :class="removing ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-trash'"></i>
            {{ removing ? 'Quitando...' : 'Quitar' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>
