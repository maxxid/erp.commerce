<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const toast = useToastStore()

const MODOS = [
  { key: 'pendientes', label: 'Sin categorizar' },
  { key: 'sin_categoria', label: 'Sin categoría' },
  { key: 'general', label: 'En "General"' },
  { key: 'todos', label: 'Todos' },
]
const TAMANO_LOTE_IA = 20

const modo = ref('pendientes')
const q = ref('')
const page = ref(1)
const pageSize = 50
const total = ref(0)
const filas = ref([])
const categorias = ref([])
const cargando = ref(false)
const aplicando = ref(false)

// destino elegido por producto: id de categoría o -1 (crear la nueva que propuso la IA)
const destinos = reactive({})
const nuevas = reactive({})
const propuestas = reactive({})
const marcados = ref(new Set())

const iaDisponible = ref(false)
const iaEstado = ref('')
const progreso = reactive({ activo: false, hecho: 0, total: 0 })

const showConfirm = ref(false)

const tableColumns = [
  { key: 'select', label: '', width: 'w-10', align: 'center', mobile: false },
  { key: 'producto', label: 'Producto' },
  { key: 'actual', label: 'Actual', width: 'w-40' },
  { key: 'destino', label: 'Destino', width: 'w-56' },
  { key: 'sugerencia', label: 'Sugerencia', width: 'w-56', mobile: false },
]

const tableRows = computed(() => filas.value.map(f => ({
  ...f,
  _nueva: nuevas[f.producto_id] || null,
})))

const opcionesBase = computed(() => categorias.value.map(c => ({ value: c.id, label: c.nombre })))

const seleccionados = computed(() => filas.value.filter(f => marcados.value.has(f.producto_id)))

// Filas que se pueden aplicar: seleccionadas, con destino elegido y con algo
// que de verdad cambie (mover un producto a su propia categoría no es un cambio).
const aplicables = computed(() => seleccionados.value.filter(f => {
  const d = destinos[f.producto_id]
  if (d === -1) return !!nuevas[f.producto_id]
  return !!d && d !== f.categoria_actual_id
}))

const descartados = computed(() => seleccionados.value.length - aplicables.value.length)

const progresoPct = computed(() => {
  if (!progreso.total) return 0
  return Math.round((progreso.hecho / progreso.total) * 100)
})

const resumen = computed(() => {
  const sin = filas.value.filter(f => !f.categoria_actual_id).length
  const con = filas.value.filter(f => !!f.categoria_actual_id).length
  return { sin, con }
})

function opcionesFila(row) {
  const base = [...opcionesBase.value]
  if (row._nueva) base.unshift({ value: -1, label: `Nueva: ${row._nueva}` })
  return base
}

function motivoDe(f) {
  const p = propuestas[f.producto_id]
  if (p?.motivo) return p.motivo
  return f.sugerencia?.motivo || ''
}

function etiquetaDe(f) {
  if (nuevas[f.producto_id] && destinos[f.producto_id] === -1) return 'Nueva'
  if (propuestas[f.producto_id]) return 'IA'
  if (f.sugerencia) return 'Local'
  return null
}

function toggle(id) {
  const s = new Set(marcados.value)
  if (s.has(id)) s.delete(id)
  else s.add(id)
  marcados.value = s
}

function toggleTodos() {
  const todos = filas.value.every(f => marcados.value.has(f.producto_id))
  marcados.value = todos ? new Set() : new Set(filas.value.map(f => f.producto_id))
}

async function cargar() {
  cargando.value = true
  try {
    const params = new URLSearchParams()
    params.set('modo', modo.value)
    if (q.value.trim()) params.set('q', q.value.trim())
    params.set('page', String(page.value))
    params.set('page_size', String(pageSize))
    const resp = await api.get(`/api/productos/sugerencias/candidatos?${params}`)
    filas.value = Array.isArray(resp?.items) ? resp.items : []
    total.value = resp?.total || 0

    const conservar = new Set(filas.value.map(f => f.producto_id))
    marcados.value = new Set([...marcados.value].filter(id => conservar.has(id)))
    filas.value.forEach(f => {
      if (destinos[f.producto_id] === undefined) destinos[f.producto_id] = f.destino_id
    })
  } catch (e) {
    toast.error(e?.message || 'No se pudieron cargar los candidatos')
    filas.value = []
    total.value = 0
  } finally {
    cargando.value = false
  }
}

function cambiarModo(key) {
  modo.value = key
  page.value = 1
  cargar()
}

function buscar() {
  page.value = 1
  cargar()
}

function paginas() {
  return Math.max(1, Math.ceil(total.value / pageSize))
}

function irA(p) {
  page.value = Math.min(Math.max(1, p), paginas())
  cargar()
}

function opcionesIA() {
  if (marcados.value.size) return [...marcados.value]
  return filas.value.map(f => f.producto_id)
}

function partirEnLotes(ids, tam) {
  const lotes = []
  for (let i = 0; i < ids.length; i += tam) lotes.push(ids.slice(i, i + tam))
  return lotes
}

async function buscarConIa() {
  const ids = opcionesIA()
  if (!ids.length) {
    toast.warning('No hay productos para analizar')
    return
  }
  const lotes = partirEnLotes(ids, TAMANO_LOTE_IA)
  progreso.activo = true
  progreso.hecho = 0
  progreso.total = ids.length

  for (const lote of lotes) {
    try {
      const resp = await api.post('/api/productos/sugerencias/ia', { productos_ids: lote })
      for (const s of resp?.lote || []) {
        if (s.nueva_categoria) {
          nuevas[s.producto_id] = s.nueva_categoria
          destinos[s.producto_id] = -1
        } else {
          delete nuevas[s.producto_id]
          destinos[s.producto_id] = s.categoria_id
        }
        propuestas[s.producto_id] = s
        marcados.value.add(s.producto_id)
      }
      progreso.hecho += lote.length
    } catch (e) {
      const detalle = e?.message || 'No se pudo consultar la IA'
      if (e?.status === 402 && /plan/i.test(detalle)) toast.error(detalle)
      else if (e?.status === 409) toast.error(detalle)
      else toast.error(detalle)
      break
    }
  }
  progreso.activo = false
  const n = Object.keys(propuestas).length
  if (n) toast.success(`${n} producto(s) con propuesta de la IA — revisalos antes de aplicar`)
}

function aplicarSeleccion() {
  if (!aplicables.value.length) {
    toast.warning('Elegí una categoría destino distinta de la actual en los productos seleccionados')
    return
  }
  showConfirm.value = true
}

async function confirmarAplicar() {
  showConfirm.value = false
  aplicando.value = true
  try {
    const cambios = aplicables.value.map(f => {
      const d = destinos[f.producto_id]
      return d === -1
        ? { producto_id: f.producto_id, categoria_id: null, nueva_categoria: nuevas[f.producto_id] }
        : { producto_id: f.producto_id, categoria_id: d }
    })
    const resp = await api.post('/api/productos/aplicar-sugerencias', { cambios })
    const errores = resp?.data?.errores || []
    toast.success(resp?.message || `${resp?.data?.aplicados ?? 0} producto(s) recategorizado(s)`)
    if (errores.length) toast.warning(`${errores.length} producto(s) no se pudieron aplicar`)
    if (resp?.data?.categorias_creadas?.length) {
      toast.info(`Categorías creadas: ${resp.data.categorias_creadas.map(c => c.nombre).join(', ')}`)
    }
    Object.keys(propuestas).forEach(k => delete propuestas[k])
    Object.keys(nuevas).forEach(k => delete nuevas[k])
    marcados.value = new Set()
    await cargarCategorias()
    await cargar()
  } catch (e) {
    toast.error(e?.message || 'No se pudieron aplicar los cambios')
  } finally {
    aplicando.value = false
  }
}

async function cargarCategorias() {
  try {
    const data = await api.get('/api/categorias?page_size=500')
    categorias.value = Array.isArray(data) ? data : (data?.data || [])
  } catch {
    categorias.value = []
  }
}

async function cargarEstadoIa() {
  try {
    const resp = await api.get('/api/licencia/estado')
    iaDisponible.value = !!resp?.ia_disponible
    if (!resp?.features?.ia) iaEstado.value = 'Tu plan no incluye IA'
    else if (!resp?.ia_configurada) iaEstado.value = 'Configurá la IA en Ajustes'
    else iaEstado.value = ''
  } catch {
    iaEstado.value = ''
  }
}

onMounted(async () => {
  await Promise.all([cargarCategorias(), cargarEstadoIa()])
  await cargar()
})
</script>

<template>
  <div class="p-4 md:p-6 space-y-4 md:space-y-5 max-w-[1500px] mx-auto">
    <!-- Header -->
    <div class="flex items-start justify-between gap-3">
      <div class="min-w-0">
        <h1 class="text-xl md:text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2.5">
          <i class="fa-solid fa-wand-magic-sparkles text-brand-500"></i>
          Recategorizar productos
        </h1>
        <p class="text-xs md:text-sm text-slate-500 dark:text-slate-400 mt-0.5">
          El sistema propone, vos confirmás. Nada se mueve hasta que apretás "Aplicar".
        </p>
      </div>
      <span class="shrink-0 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-brand-100 dark:bg-brand-900/40 text-brand-700 dark:text-brand-300">
        {{ total }} en vista
      </span>
    </div>

    <!-- Modos + búsqueda -->
    <BaseCard padding="md" class="space-y-3">
      <div class="flex items-center gap-2 flex-wrap">
        <button
          v-for="m in MODOS"
          :key="m.key"
          class="px-3.5 py-1.5 text-xs font-semibold rounded-full border transition-colors"
          :class="modo === m.key
            ? 'bg-brand-600 text-white border-brand-600'
            : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-brand-300 dark:hover:border-brand-700'"
          @click="cambiarModo(m.key)"
        >
          {{ m.label }}
        </button>
        <div class="flex-1 min-w-[220px]">
          <BaseInput
            v-model="q"
            placeholder="Buscar por nombre, marca, código o descripción"
            size="sm"
            @enter="buscar"
          />
        </div>
        <BaseButton variant="secondary" size="sm" :loading="cargando" @click="buscar">
          <i class="fa-solid fa-arrows-rotate mr-1.5"></i> Buscar
        </BaseButton>
      </div>

      <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>
          <span class="font-bold text-slate-900 dark:text-white">{{ resumen.sin }}</span> sin categoría ·
          <span class="font-bold text-slate-900 dark:text-white">{{ resumen.con }}</span> ya categorizadas
        </span>
        <span v-if="marcados.size">{{ marcados.size }} seleccionado(s)</span>
      </div>
    </BaseCard>

    <!-- IA -->
    <BaseCard padding="md" class="space-y-3">
      <div class="flex items-start justify-between gap-3">
        <div class="min-w-0">
          <h3 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
            Segundo parecer con IA
          </h3>
          <p class="text-[11px] text-slate-400 dark:text-slate-500 mt-0.5">
            Analiza de a lotes de {{ TAMANO_LOTE_IA }} productos contra tu catálogo.
            <span v-if="marcados.size"> Se analizarán los {{ marcados.size }} seleccionados.</span>
            <span v-else> Sin selección, analiza la página actual.</span>
          </p>
        </div>
        <BaseBadge v-if="iaEstado" variant="warning" size="xs">{{ iaEstado }}</BaseBadge>
      </div>

      <div v-if="progreso.activo" class="space-y-1.5">
        <div class="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
          <span>Analizando… {{ progreso.hecho }}/{{ progreso.total }}</span>
          <span>{{ progresoPct }}%</span>
        </div>
        <div class="h-2 rounded-full bg-slate-100 dark:bg-slate-800 overflow-hidden">
          <div
            class="h-full rounded-full bg-brand-500 transition-all duration-300"
            :style="{ width: progresoPct + '%' }"
          ></div>
        </div>
      </div>

      <BaseButton
        v-else
        variant="secondary"
        size="sm"
        class="w-full"
        :disabled="!filas.length || (!iaDisponible && !!iaEstado)"
        @click="buscarConIa"
      >
        <i class="fa-solid fa-robot mr-1.5"></i>
        Analizar con IA
      </BaseButton>
    </BaseCard>

    <!-- Tabla -->
    <BaseCard v-if="filas.length" padding="none">
      <div class="px-4 py-3 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between gap-2">
        <span class="text-xs text-slate-500 dark:text-slate-400">
          <span class="font-bold text-slate-900 dark:text-white text-sm">{{ total }}</span> producto(s)
        </span>
        <div class="flex items-center gap-2">
          <BaseButton variant="ghost" size="sm" :disabled="!filas.length" @click="toggleTodos">
            <i :class="filas.every(f => marcados.has(f.producto_id)) ? 'fa-solid fa-square-minus' : 'fa-solid fa-square-check'"></i>
            {{ filas.every(f => marcados.has(f.producto_id)) ? 'Limpiar' : 'Todo' }}
          </BaseButton>
          <BaseButton
            variant="primary"
            size="sm"
            :loading="aplicando"
            :disabled="!aplicables.length"
            @click="aplicarSeleccion"
          >
            <i class="fa-solid fa-check-double mr-1.5"></i>
            Aplicar {{ aplicables.length }}<span v-if="descartados"> ({{ descartados }} sin cambios)</span>
          </BaseButton>
        </div>
      </div>

      <BaseTable
        :columns="tableColumns"
        :rows="tableRows"
        :loading="cargando"
        empty-title="Nada por acá"
        empty-text="No hay productos para ese filtro."
        empty-icon="fa-folder-open"
      >
        <template #select="{ row }">
          <input
            type="checkbox"
            class="w-3.5 h-3.5 rounded border-slate-300 text-brand-600 focus:ring-brand-500 cursor-pointer"
            :checked="marcados.has(row.producto_id)"
            @click="toggle(row.producto_id)"
          />
        </template>

        <template #producto="{ row }">
          <div class="min-w-0">
            <div class="text-xs font-medium text-slate-800 dark:text-slate-100 truncate">{{ row.nombre }}</div>
            <div class="text-[10px] text-slate-400 truncate">
              {{ [row.marca, row.codigo_barras].filter(Boolean).join(' · ') || '—' }}
            </div>
          </div>
        </template>

        <template #actual="{ row }">
          <span
            class="text-[11px] truncate block"
            :class="row.categoria_actual ? 'text-slate-600 dark:text-slate-300' : 'text-amber-500'"
          >
            {{ row.categoria_actual || 'Sin categoría' }}
          </span>
        </template>

        <template #destino="{ row }">
          <BaseSelect
            :model-value="destinos[row.producto_id]"
            size="sm"
            :options="opcionesFila(row)"
            option-value="value"
            option-label="label"
            placeholder="Elegir categoría…"
            @update:model-value="val => { destinos[row.producto_id] = Number(val); if (Number(val) !== -1) delete nuevas[row.producto_id] }"
          />
        </template>

        <template #sugerencia="{ row }">
          <div class="min-w-0">
            <BaseBadge v-if="etiquetaDe(row)" :variant="etiquetaDe(row) === 'IA' ? 'info' : 'brand'" size="xs">
              {{ etiquetaDe(row) }}
            </BaseBadge>
            <div class="text-[10px] text-slate-400 truncate mt-0.5">{{ motivoDe(row) || '—' }}</div>
          </div>
        </template>
      </BaseTable>

      <!-- Paginación -->
      <div v-if="paginas() > 1" class="px-4 py-3 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between">
        <span class="text-[11px] text-slate-400">Página {{ page }} de {{ paginas() }}</span>
        <div class="flex gap-2">
          <BaseButton variant="ghost" size="sm" :disabled="page <= 1" @click="irA(page - 1)">
            <i class="fa-solid fa-chevron-left"></i> Anterior
          </BaseButton>
          <BaseButton variant="ghost" size="sm" :disabled="page >= paginas()" @click="irA(page + 1)">
            Siguiente <i class="fa-solid fa-chevron-right"></i>
          </BaseButton>
        </div>
      </div>
    </BaseCard>

    <EmptyState
      v-else-if="!cargando"
      icon="fa-wand-magic-sparkles"
      title="Todo categorizado"
      text="No hay productos pendientes para este filtro. Si querés revisar el catálogo entero, cambiá el filtro a Todos."
    />

    <!-- Confirmación: acá está la confirmación humana obligatoria -->
    <BaseModal v-model="showConfirm" title="Confirmar recategorización" size="md">
      <div class="space-y-3">
        <p class="text-sm text-slate-700 dark:text-slate-300">
          Vas a mover <span class="font-bold">{{ aplicables.length }}</span> producto(s) de categoría.
        </p>
        <div class="max-h-64 overflow-y-auto rounded-xl border border-slate-200 dark:border-slate-700 divide-y divide-slate-100 dark:divide-slate-800">
          <div v-for="f in aplicables" :key="f.producto_id" class="px-3 py-2 flex items-center justify-between gap-3">
            <div class="min-w-0">
              <div class="text-xs font-medium text-slate-800 dark:text-slate-100 truncate">{{ f.nombre }}</div>
              <div class="text-[10px] text-slate-400 truncate">{{ f.categoria_actual || 'Sin categoría' }} →</div>
            </div>
            <div class="text-xs font-semibold text-brand-600 dark:text-brand-400 text-right shrink-0">
              {{ destinos[f.producto_id] === -1
                ? `Nueva: ${nuevas[f.producto_id]}`
                : (categorias.find(c => c.id === destinos[f.producto_id])?.nombre || '—') }}
            </div>
          </div>
        </div>
        <p class="text-[11px] text-slate-400">
          <i class="fa-solid fa-circle-info mr-1"></i>
          Esto modifica el catálogo de verdad. Se registra en la auditoría.
        </p>
      </div>
      <template #footer>
        <div class="flex gap-2">
          <BaseButton variant="secondary" class="flex-1" @click="showConfirm = false">Cancelar</BaseButton>
          <BaseButton variant="primary" class="flex-1" @click="confirmarAplicar">
            <i class="fa-solid fa-check mr-1.5"></i> Aplicar
          </BaseButton>
        </div>
      </template>
    </BaseModal>
  </div>
</template>
