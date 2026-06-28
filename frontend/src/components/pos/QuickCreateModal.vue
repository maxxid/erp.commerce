<template>
  <BaseModal :model-value="show" title="Nuevo Producto" size="md" @update:model-value="emit('close')">
    <form class="space-y-4" @submit.prevent="save">
      <div class="space-y-1">
        <BaseInput v-model="form.codigo_barras" label="Código de Barras" placeholder="779... o dejar vacío para auto-generar" input-class="font-mono-data" :disabled="lookingUp">
          <template #suffix>
            <button type="button" class="w-7 h-7 rounded-lg flex items-center justify-center text-brand-500 hover:text-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition" title="Buscar en fuentes externas" :disabled="lookingUp || !form.codigo_barras.trim()" @click="lookupBarcode">
              <i v-if="lookingUp" class="fa-solid fa-circle-notch fa-spin text-sm"></i>
              <i v-else class="fa-solid fa-magnifying-glass text-sm"></i>
            </button>
          </template>
        </BaseInput>
        <p class="text-[10px] text-slate-400 dark:text-slate-500">Si se deja vacío, se asigna automáticamente un código secuencial</p>
      </div>

      <BaseInput v-model="form.nombre" label="Nombre del Producto" placeholder="Nombre del producto" required :disabled="lookingUp" :loading="lookingUp" />

      <div class="grid grid-cols-2 gap-4">
        <BaseInput v-model="form.marca" label="Marca" placeholder="Marca" :disabled="lookingUp" />
        <BaseInput v-model.number="form.precio_venta" label="Precio Venta" type="number" step="0.01" min="0" required input-class="font-mono-data text-right" />
      </div>

      <BaseSelect v-model="form.categoria_id" label="Categoría" :options="catOptions" option-value="value" option-label="label" required />

      <div v-if="formError" class="p-3 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-300 rounded-xl border border-red-100 dark:border-red-800/50 text-xs font-medium flex items-center gap-2">
        <i class="fa-solid fa-triangle-exclamation"></i>{{ formError }}
      </div>

      <div class="flex items-center gap-3 pt-2">
        <BaseButton variant="secondary" class="flex-1" @click="onClose">Cancelar</BaseButton>
        <BaseButton variant="primary" type="submit" :loading="saving" class="flex-1">
          <i :class="saving ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-floppy-disk'"></i>
          {{ saving ? 'Guardando...' : 'Crear Producto' }}
        </BaseButton>
      </div>
    </form>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import api from '@/services/api'
import { useToastStore } from '@/stores/toasts'

const toast = useToastStore()

const props = defineProps({
  show: { type: Boolean, default: false },
  barcode: { type: String, default: '' },
  categories: { type: Array, default: () => [] },
  nextGenCode: { type: String, default: 'GEN-00000001' }
})

const emit = defineEmits(['close', 'created'])

const saving = ref(false)
const lookingUp = ref(false)
const formError = ref('')

const form = reactive({
  codigo_barras: '',
  nombre: '',
  marca: '',
  precio_venta: 0,
  categoria_id: null
})

watch(() => props.show, (val) => {
  if (val) {
    formError.value = ''
    form.nombre = ''
    form.marca = ''
    form.precio_venta = 0
    form.categoria_id = props.categories[0]?.id || null
    form.codigo_barras = props.barcode || ''
  }
})

const catOptions = computed(() =>
  props.categories.map(c => ({ value: c.id, label: c.nombre }))
)

async function lookupBarcode() {
  const code = form.codigo_barras?.trim()
  if (!code || code.length < 8) {
    toast.warning('Ingresá al menos 8 dígitos para buscar')
    return
  }
  lookingUp.value = true
  try {
    const resp = await api.post('/api/productos/lookup', { barcode: code })
    if (resp && resp.nombre) {
      form.nombre = resp.nombre || form.nombre
      form.marca = resp.marca || form.marca
      const cat = props.categories.find(c => c.nombre === resp.categoria)
      if (cat) form.categoria_id = cat.id
      toast.success(`Encontrado: ${resp.nombre}`)
    } else {
      toast.info('Producto no encontrado en fuentes externas. Podés cargar los datos manualmente.')
    }
  } catch {
    toast.info('Búsqueda sin resultados. Ingresá los datos manualmente.')
  }
  lookingUp.value = false
}

async function save() {
  formError.value = ''
  if (!form.nombre?.trim()) {
    formError.value = 'El nombre del producto es obligatorio'
    return
  }

  let barcode = form.codigo_barras?.trim()
  if (!barcode) {
    barcode = props.nextGenCode
  }

  saving.value = true
  try {
    const resp = await api.post('/api/productos', {
      codigo_barras: barcode,
      nombre: form.nombre.trim(),
      marca: form.marca?.trim() || '',
      precio_venta: form.precio_venta || 0,
      categoria_id: form.categoria_id
    })
    toast.success('Producto creado')
    emit('created', resp?.data || { id: Date.now(), codigo_barras: barcode, nombre: form.nombre.trim(), marca: form.marca?.trim() || '', precio_venta: form.precio_venta || 0, categoria_id: form.categoria_id })
    onClose()
  } catch (e) {
    formError.value = e?.response?.data?.detail || e.message || 'Error al guardar el producto'
  }
  saving.value = false
}

function onClose() {
  emit('close')
}
</script>
