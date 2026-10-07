<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { formatCurrency as fc, formatCurrencyShort as fcCorto } from '@/composables/useUtils'
import api from '@/services/api'
import KpiCard from '@/components/ui/KpiCard.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSkeleton from '@/components/ui/BaseSkeleton.vue'
import EmptyState from '@/components/ui/EmptyState.vue'

const auth = useAuthStore()
const router = useRouter()
const simple = ref(false)
const loading = ref(true)
const alertas = ref([])
const data = ref({})
const alertasLotes = ref({})
// true cuando la API falló y estamos mostrando el mockData: los números de
// abajo son de ejemplo y el template avisa con un banner.
const datosDemo = ref(false)

const mockData = {
  total_productos: 3, valor_stock: 450000, stock_bajo: 1,
  ventas_hoy: 22000, cant_ventas_hoy: 5,
  ventas_mes: 22000, cant_ventas_mes: 5,
  ticket_promedio: 4400, medio_favorito: 'efectivo',
  tendencia: 12, margen_bruto_hoy: 8000, margen_bruto_mes: 8000,
  margen_pct_hoy: 36, margen_pct_mes: 36,
  margen_bruto_semana: 24000, margen_bruto_trimestre: 65000,
  margen_pct_semana: 34, margen_pct_trimestre: 33,
  // ventas_por_hora no va acá: el gráfico por hora tiene su propio endpoint con
  // rango propio, así que el fallback no lo necesita.
  top_productos_mes: [
    { id: 1, nombre: 'Coca Cola 2.25L', cantidad_vendida: 24, total_vendido: 60000 },
    { id: 2, nombre: 'Yerba Mate Playadito 1kg', cantidad_vendida: 15, total_vendido: 48000 },
  ],
  stock_critico: [{ id: 3, nombre: 'Aceite de Girasol Natura 1.5L', stock_actual: 2, stock_minimo: 8 }],
  sin_stock: [],
  efectivo_hoy: 12000, transferencia_hoy: 5500,
  // vs_hoy/vs_mes: los KPIs muestran la flecha de variación. Sin esto, el
  // fallback los deja sin delta, que es el dato más útil del card.
  vs_hoy: { ventas: { actual: 0, anterior: 0, pct: null }, margen: { actual: 0, anterior: 0, pct: null }, ticket: { actual: 0, anterior: 0, pct: null } },
  vs_mes: { ventas: { actual: 0, anterior: 0, pct: null }, margen: { actual: 0, anterior: 0, pct: null } }
}

// --- "vs. período anterior" ---
// El backend ya devuelve actual/anterior/pct por KPI. Acá solo se formatea.
function delta(que, metrica) {
  return data.value[que]?.[metrica]?.pct ?? null
}

function textoDelta(que) {
  if (que === 'vs_hoy') return 'vs ayer'
  if (que === 'vs_mes') return 'vs mes anterior'
  return 'vs período anterior'
}

const maxBar = computed(() => {
  const vals = tendVals.value
  return Math.max(...vals, 1)
})
const tendSinDatos = computed(() => tendVals.value.length > 0 && tendVals.value.every((v) => !v))

// --- Gráfico de ventas por período ---
// Antes el backend clavaba "últimos 7 días" y el front no tenía por dónde
// mirar la semana ni el mes anterior.
const tendPeriodo = ref('7dias')
const tendData = ref(null)
const tendLoading = ref(false)
const RANGOS = [
  { value: '7dias', label: '7 días' },
  { value: 'semana', label: 'Esta semana' },
  { value: 'semana_anterior', label: 'Semana pasada' },
  { value: 'mes', label: 'Este mes' },
  { value: 'mes_anterior', label: 'Mes pasado' },
  // Los mismos dos meses pero agrupados por día de la semana: 7 barras que
  // dicen qué día se mueve más, que con 4 semanas promediadas no se ve.
  { value: 'mes_por_dia', label: 'Este mes · por día' },
  { value: 'mes_anterior_por_dia', label: 'Mes pasado · por día' },
]
const tendLabels = computed(() => tendData.value?.labels || [])
const tendVals = computed(() => tendData.value?.valores || [])

// Para los textos de estado vacío: nombrar el rango elegido en vez de decir
// "sin datos" a secas, que no dice si hay que cambiar el filtro o no.
function rangoActual(cual) {
  const lista = cual === 'hora' ? RANGOS_HORA : RANGOS
  const valor = cual === 'hora' ? horaPeriodo.value : tendPeriodo.value
  return lista.find((r) => r.value === valor) || lista[0]
}

async function loadTendencia() {
  tendLoading.value = true
  try {
    // Ojo: api.get(path, params) recibe los params sueltos, no un { params: {...} }.
    // Envueltos salían como ?params[periodo]=7dias y el backend los ignoraba.
    tendData.value = await api.get('/api/dashboard/ventas-periodo', {
      periodo: tendPeriodo.value,
    })
  } catch {
    tendData.value = null
  } finally {
    tendLoading.value = false
  }
}

// Sólo las horas con venta: el backend manda 24 y casi todas valen 0, así que
// mostrar las 24 deja las barras finísimas y los rótulos ilegibles.
const horasConVenta = computed(() => {
  const labels = horaData.value?.labels || []
  const valores = horaData.value?.valores || []
  return labels
    .map((l, i) => ({ label: l, valor: valores[i] || 0 }))
    .filter((h) => h.valor > 0)
})

const maxHour = computed(() => {
  const vals = horasConVenta.value.map((h) => h.valor)
  return Math.max(...vals, 1)
})

// --- Ventas por hora ---
// Estaba clavado en "hoy" dentro de /resumen. Mirar un solo día esconde el
// patrón del local: si siempre se vende de 9 a 13, la hora promedio cacarea y
// el resto del día parece que no vende nada.
const horaPeriodo = ref('hoy')
const horaData = ref(null)
const horaLoading = ref(false)
const RANGOS_HORA = [
  { value: 'hoy', label: 'Hoy' },
  { value: '7dias', label: '7 días' },
  { value: 'semana', label: 'Esta semana' },
  { value: 'semana_anterior', label: 'Semana pasada' },
  { value: 'mes', label: 'Este mes' },
  { value: 'mes_anterior', label: 'Mes pasado' },
]

async function loadHoras() {
  horaLoading.value = true
  try {
    horaData.value = await api.get('/api/dashboard/por-hora', { periodo: horaPeriodo.value })
  } catch {
    horaData.value = null
  } finally {
    horaLoading.value = false
  }
}

// --- Ventas por categoría ---
const catMetrica = ref('importe')
const catPeriodo = ref('mes')
const catLoading = ref(false)
const catData = ref(null)

const METRICAS = [
  { value: 'importe', label: 'Importe', money: true },
  { value: 'ganancia', label: 'Ganancia', money: true },
  { value: 'cantidad', label: 'Cantidad', money: false },
  { value: 'margen_pct', label: 'Margen %', money: false },
]
const PERIODOS = [
  { value: 'hoy', label: 'Hoy' },
  { value: 'semana', label: 'Semana' },
  { value: 'mes', label: 'Mes' },
  { value: 'trimestre', label: 'Trim.' },
]

const metricaActual = computed(() => METRICAS.find((m) => m.value === catMetrica.value) || METRICAS[0])
const catFilas = computed(() => catData.value?.categorias || [])
const maxCat = computed(() => Math.max(...catFilas.value.map((r) => r[catMetrica.value] || 0), 1))

function pctCat(v) {
  return ((v || 0) / maxCat.value) * 100
}

// Formatea el valor de la métrica elegida. Sirve para categorías y productos:
// la respuesta trae siempre las cuatro columnas.
function fmtMetrica(r) {
  const m = metricaActual.value
  if (m.money) return fc(r[m.value] || 0)
  if (m.value === 'cantidad') return (r.cantidad || 0) + ' u'
  return (r.margen_pct || 0) + '%'
}

function catAbierta(clave) {
  return catAbiertas.value[clave] === 'listo' || catAbiertas.value[clave] === 'cargando'
}

async function loadCategorias() {
  catLoading.value = true
  try {
    const resp = await api.get('/api/dashboard/por-categoria', {
      metrica: catMetrica.value,
      periodo: catPeriodo.value,
      limite: 10,
    })
    catData.value = resp
  } catch {
    catData.value = null
  } finally {
    catLoading.value = false
  }
}

// Al cambiar de métrica o período, lo que quedó desplegado pasa a ser de otro
// corte: cerrarlo siempre es más simple que invalidarlo en cada fila.
function resetDesplegado() {
  catAbiertas.value = {}
  catProductos.value = {}
}

function setCatPeriodo(p) {
  catPeriodo.value = p
  resetDesplegado()
  loadCategorias()
}

function setCatMetrica(m) {
  catMetrica.value = m
  resetDesplegado()
  loadCategorias()
}

// --- Drill-down de categorías ---
// Por cada clave: 'cargando' | 'listo' | 'error'
const catAbiertas = ref({})
const catProductos = ref({})

async function toggleCategoria(fila) {
  // "Otras" es un agrupamiento del gráfico, no una categoría real: no tiene
  // productos que mirar.
  if (fila.clave === 'otras') return
  if (catAbiertas.value[fila.clave] === 'listo') {
    delete catAbiertas.value[fila.clave]
    return
  }
  catAbiertas.value[fila.clave] = 'cargando'
  try {
    const resp = await api.get('/api/dashboard/por-categoria/productos', {
      categoria: fila.clave,
      periodo: catPeriodo.value,
      metrica: catMetrica.value,
      limite: 15,
    })
    catProductos.value[fila.clave] = resp.productos || []
    catAbiertas.value[fila.clave] = 'listo'
  } catch {
    catProductos.value[fila.clave] = []
    catAbiertas.value[fila.clave] = 'error'
  }
}

function irAProducto(p) {
  router.push({ name: 'products', query: { editar: p.id } })
}

// --- Stock por velocidad de venta ---
// El "stock crítico" clásico compara contra un mínimo estático que alguien cargó
// a mano, y ese mínimo no sabe si un producto sale 2 o 50 por día. Acá se cruza
// con el ritmo real de venta, que es lo que dice qué comprar hoy.
const velDias = ref(30)
const velData = ref(null)
const velLoading = ref(false)
const velTodos = ref(false)

async function loadVelocidad() {
  velLoading.value = true
  try {
    velData.value = await api.get('/api/dashboard/stock-por-velocidad', {
      dias: velDias.value,
      solo_criticos: !velTodos.value,
      limite: 12,
    })
  } catch {
    velData.value = null
  } finally {
    velLoading.value = false
  }
}

// "4 hs", "2 días", "1,5 meses". El número crudo en días no sirve para 45.
function diasLegibles(d) {
  if (d == null) return '—'
  if (d < 1) return `${Math.max(1, Math.round(d * 24))} hs`
  if (d < 2) return '1 día'
  if (d < 60) return `${Math.round(d)} días`
  return `${(d / 30).toFixed(1).replace('.', ',')} meses`
}

// --- Datos sucios ---
// Falta de costo infla el margen; falta de categoría saca el producto del
// gráfico. Con el importe afectado se ve si vale la pena ir a corregirlo.
const sucioPeriodo = ref('mes')
const sucioData = ref(null)
const sucioLoading = ref(false)
const suciosAbiertos = ref(false)

async function loadSucios() {
  sucioLoading.value = true
  try {
    sucioData.value = await api.get('/api/dashboard/datos-sucios', {
      periodo: sucioPeriodo.value,
    })
  } catch {
    sucioData.value = null
  } finally {
    sucioLoading.value = false
  }
}

function setSucioPeriodo(p) {
  sucioPeriodo.value = p
  loadSucios()
}

onMounted(() => load())

async function load() {
  loading.value = true
  alertas.value = []
  try {
    const [resp, lotesAlert] = await Promise.all([
      api.get('/api/dashboard/resumen').catch(() => null),
      api.get('/api/dashboard/alertas-lotes').catch(() => null),
    ])
    // Ojo: antes se chequeaba `resp.total_productos`, que es 0 en una
    // instalación recién vacía, y eso mandaba al mockData con la API
    // funcionando. Alcanza con que la respuesta exista.
    if (resp) {
      data.value = resp
      datosDemo.value = false
    } else {
      Object.assign(data.value, mockData)
      datosDemo.value = true
    }
    if (lotesAlert) alertasLotes.value = lotesAlert
    buildLoteAlerts()
  } catch {
    Object.assign(data.value, mockData)
    datosDemo.value = true
  } finally {
    loading.value = false
  }
  // Los tres gráficos son independientes: si uno de estos endpoints falla, el
  // resto del dashboard sigue funcionando igual.
  loadCategorias()
  loadTendencia()
  loadHoras()
  loadVelocidad()
  loadSucios()
}

// Alturas de skeleton estables: Math.random() en el template se re-evalúa en
// cada render y las barras dan saltos.
function skeletonHeight(n, base = 60) {
  return `${20 + ((n * 37) % base)}%`
}

function buildLoteAlerts() {
  const a = alertasLotes.value
  if (!a || !a.totales) return
  const t = a.totales
  if (t.vencidos > 0) {
    alertas.value.push({
      tipo: 'lotes_vencidos',
      nivel: 'danger',
      mensaje: `${t.vencidos} lote(s) vencido(s) con stock. Revisá el stock antes de seguir vendiendo.`,
    })
  }
  if (t.por_vencer_7d > 0) {
    alertas.value.push({
      tipo: 'lotes_por_vencer_7d',
      nivel: 'danger',
      mensaje: `${t.por_vencer_7d} lote(s) vence(n) en los próximos 7 días.`,
    })
  } else if (t.por_vencer_15d > 0) {
    alertas.value.push({
      tipo: 'lotes_por_vencer_15d',
      nivel: 'warning',
      mensaje: `${t.por_vencer_15d} lote(s) vence(n) en los próximos 15 días.`,
    })
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">KPIs en tiempo real</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          v-if="auth.isAdmin || auth.isEncargado"
          type="button"
          class="text-xs font-semibold text-slate-500 dark:text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition flex items-center gap-1.5 px-3 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
          @click="simple = !simple"
        >
          <i :class="simple ? 'fa-toggle-off' : 'fa-toggle-on'" class="fa-solid text-base"></i>
          {{ simple ? 'Vista simple' : 'Vista completa' }}
        </button>
        <BaseButton variant="secondary" size="sm" :loading="loading" @click="load">
          <i class="fa-solid fa-arrows-rotate" :class="loading ? 'animate-spin' : ''"></i>
          Sincronizar
        </BaseButton>
      </div>
    </div>

    <!-- Datos de ejemplo: sin esto, un fallo de red muestra "$22.000" como si fuera real -->
    <div
      v-if="datosDemo"
      class="px-4 py-3 rounded-xl border text-xs font-semibold flex items-start gap-2.5 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/50 text-red-700 dark:text-red-300"
    >
      <i class="fa-solid fa-triangle-exclamation text-red-500 mt-0.5"></i>
      <span>
        No se pudo sincronizar con el servidor. Los números de abajo son
        <strong>datos de ejemplo, no ventas reales</strong>. Revisá la conexión y
        volvé a tocar <em>Sincronizar</em>.
      </span>
    </div>

    <!-- Alertas -->
    <TransitionGroup
      v-if="alertas.length"
      tag="div"
      class="space-y-2"
      enter-active-class="transition duration-300 ease-out-expo"
      enter-from-class="opacity-0 -translate-x-2"
      enter-to-class="opacity-100 translate-x-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-x-0"
      leave-to-class="opacity-0 translate-x-2"
    >
      <div
        v-for="a in alertas"
        :key="a.tipo"
        class="px-4 py-3 rounded-xl border text-xs font-semibold flex items-center gap-2.5"
        :class="a.nivel === 'danger'
          ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/50 text-red-700 dark:text-red-300'
          : 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/50 text-amber-700 dark:text-amber-300'"
      >
        <i :class="a.nivel === 'danger' ? 'fa-solid fa-circle-exclamation text-red-500' : 'fa-solid fa-triangle-exclamation text-amber-500'"></i>
        <span>{{ a.mensaje }}</span>
      </div>
    </TransitionGroup>

    <!-- KPIs -->
    <div v-if="simple" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <KpiCard label="Ventas Hoy" :value="data.ventas_hoy || 0" prefix="$" :loading="loading" icon="fa-sack-dollar" icon-color="success" :trend="delta('vs_hoy', 'ventas')" trend-label="vs ayer" :sublabel="(data.cant_ventas_hoy || 0) + ' tickets'" />
      <KpiCard label="Ganancia Hoy" :value="data.margen_bruto_hoy || 0" prefix="$" :loading="loading" :trend="delta('vs_hoy', 'margen')" trend-label="vs ayer" :sublabel="(data.margen_pct_hoy || 0) + '% de margen'" icon="fa-coins" icon-color="warning" />
      <KpiCard label="Efectivo Hoy" :value="data.efectivo_hoy || 0" prefix="$" :loading="loading" icon="fa-money-bill-wave" icon-color="brand" />
      <KpiCard label="Transferencia" :value="data.transferencia_hoy || 0" prefix="$" :loading="loading" icon="fa-mobile-screen-button" icon-color="info" />
      <KpiCard label="Stock Crítico" :value="data.stock_bajo || 0" :loading="loading" icon="fa-triangle-exclamation" icon-color="danger" sublabel="bajo mínimo" />
    </div>

    <div v-else class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <KpiCard label="Ventas Hoy" :value="data.ventas_hoy || 0" prefix="$" :loading="loading" icon="fa-sack-dollar" icon-color="success" :trend="delta('vs_hoy', 'ventas')" trend-label="vs ayer" :sublabel="(data.cant_ventas_hoy || 0) + ' tickets'" />
      <KpiCard label="Ventas Mes" :value="data.ventas_mes || 0" prefix="$" :loading="loading" icon="fa-chart-line" icon-color="brand" :trend="delta('vs_mes', 'ventas')" trend-label="vs mes anterior" :sublabel="(data.cant_ventas_mes || 0) + ' tickets'" />
      <KpiCard label="Ganancia Hoy" :value="data.margen_bruto_hoy || 0" prefix="$" :loading="loading" :trend="delta('vs_hoy', 'margen')" trend-label="vs ayer" :sublabel="(data.margen_pct_hoy || 0) + '% de margen'" icon="fa-coins" icon-color="warning" />
      <KpiCard label="Ganancia Semana" :value="data.margen_bruto_semana || 0" prefix="$" :loading="loading" :sublabel="(data.margen_pct_semana || 0) + '% de margen'" icon="fa-coins" icon-color="warning" />
      <KpiCard label="Ganancia Mes" :value="data.margen_bruto_mes || 0" prefix="$" :loading="loading" :trend="delta('vs_mes', 'margen')" trend-label="vs mes anterior" :sublabel="(data.margen_pct_mes || 0) + '% de margen'" icon="fa-coins" icon-color="warning" />
      <KpiCard label="Ganancia Trim." :value="data.margen_bruto_trimestre || 0" prefix="$" :loading="loading" :sublabel="(data.margen_pct_trimestre || 0) + '% de margen'" icon="fa-coins" icon-color="warning" />
      <KpiCard label="Ticket Prom." :value="data.ticket_promedio || 0" prefix="$" :loading="loading" icon="fa-receipt" icon-color="info" :trend="delta('vs_hoy', 'ticket')" trend-label="vs ayer" :sublabel="'Medio: ' + (data.medio_favorito || '—')" />
      <KpiCard label="Stock" :value="data.valor_stock || 0" prefix="$" :loading="loading" icon="fa-boxes-stacked" icon-color="warning" :sublabel="(data.total_productos || 0) + ' productos'" />
      <KpiCard label="Stock Crítico" :value="data.stock_bajo || 0" :loading="loading" icon="fa-triangle-exclamation" icon-color="danger" sublabel="bajo mínimo" />
      <KpiCard label="Tendencia" :value="data.tendencia || 0" suffix="%" :trend="data.tendencia || 0" trend-label="vs semana anterior" :loading="loading" icon="fa-arrow-trend-up" icon-color="success" />
      <KpiCard
        v-if="data.recargas_hoy && data.recargas_hoy.recargas"
        label="Recargas Hoy"
        :value="data.recargas_hoy.monto_cargado || 0"
        prefix="$"
        :loading="loading"
        icon="fa-mobile-screen-button"
        icon-color="brand"
        :sublabel="(data.recargas_hoy.recargas || 0) + ' recargas · +$' + (data.recargas_hoy.ganancia || 0)"
      />
    </div>

    <!-- Charts -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <BaseCard padding="lg">
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
          <h3 class="font-bold text-slate-900 dark:text-white text-sm">Ventas</h3>
          <div class="flex items-center gap-2">
            <BaseBadge variant="brand" size="xs">{{ fc(tendData?.total || 0) }} total</BaseBadge>
            <select
              v-model="tendPeriodo"
              class="text-[11px] font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-2 py-1.5 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 max-w-[150px]"
              @change="loadTendencia"
            >
              <option v-for="r in RANGOS" :key="r.value" :value="r.value">{{ r.label }}</option>
            </select>
          </div>
        </div>
        <!-- Las fechas del rango: al 1º del mes "Semana" arranca el lunes
             anterior y puede dar más que "Mes". Mostrarlas evita que el número
             parezca un error de cálculo. -->
        <p v-if="tendData?.desde" class="text-[10px] text-slate-400 dark:text-slate-500 -mt-3 mb-3">
          {{ tendData.desde }} &ndash; {{ tendData.hasta }}
        </p>
        <div v-if="tendLoading" class="h-40 flex items-end gap-3">
          <BaseSkeleton v-for="n in 7" :key="n" class="flex-1 rounded-t-lg" :style="{ height: skeletonHeight(n, 60) }" />
        </div>
        <EmptyState
          v-else-if="!tendLabels.length"
          icon="fa-chart-line"
          title="Sin datos de ventas"
          text="No se pudo obtener la serie para este período."
          compact
        />
        <EmptyState
          v-else-if="tendSinDatos"
          icon="fa-calendar-xmark"
        title="Sin ventas en el período"
        :text="`No hay ventas confirmadas para ${rangoActual('venta').label.toLowerCase()}. Probá con un rango más amplio.`"
          compact
        />
        <div v-else class="h-40 flex items-stretch gap-3">
          <div
            v-for="(v, i) in tendVals"
            :key="i"
            class="flex-1 flex flex-col items-center gap-1 group min-w-0 h-full"
          >
            <span
              class="text-[9px] font-semibold text-slate-500 dark:text-slate-400 tabular-nums truncate w-full text-center leading-none"
              :title="fc(v)"
            >{{ fcCorto(v) }}</span>
            <div class="w-full flex-1 min-h-0 bg-slate-100 dark:bg-slate-800 rounded-t-lg relative overflow-hidden">
              <div
                class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-brand-600 to-brand-400 rounded-t-lg transition-all duration-500 ease-out-expo group-hover:from-brand-500 group-hover:to-brand-300"
                :style="{ height: `${(v / maxBar) * 100}%` }"
              ></div>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap bg-white dark:bg-slate-800 px-2 py-1 rounded-md shadow-sm border border-slate-100 dark:border-slate-700 pointer-events-none">
                {{ fc(v) }}
              </div>
            </div>
            <span class="text-[10px] font-medium text-slate-500 dark:text-slate-400 truncate w-full text-center">{{ tendLabels[i] }}</span>
          </div>
        </div>
      </BaseCard>

    <BaseCard padding="lg">
      <div class="flex items-center justify-between mb-5">
        <h3 class="font-bold text-slate-900 dark:text-white text-sm">Picos por Hora</h3>
        <BaseBadge variant="success" size="xs">{{ horasConVenta.length || 0 }} hs</BaseBadge>
      </div>
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
        <span class="text-[10px] text-slate-400 dark:text-slate-500">
          Horario local<template v-if="horaData?.desde"> &middot; {{ horaData.desde }} &ndash; {{ horaData.hasta }}</template>
        </span>
        <select
          :value="horaPeriodo"
          class="bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1 text-xs font-medium text-slate-700 dark:text-slate-200 focus:ring-brand-500"
          @change="horaPeriodo = $event.target.value; loadHoras()"
        >
          <option v-for="r in RANGOS_HORA" :key="r.value" :value="r.value">{{ r.label }}</option>
        </select>
      </div>
      <div v-if="loading || horaLoading" class="h-40 flex items-end gap-1">
        <BaseSkeleton v-for="n in 12" :key="n" class="flex-1 rounded-t-sm" :style="{ height: skeletonHeight(n, 50) }" />
      </div>
      <EmptyState
        v-else-if="!horasConVenta.length"
        icon="fa-clock"
        title="Sin ventas en el período"
        :text="`No hay ventas registradas para ${rangoActual('hora').label.toLowerCase()}. Probá con un rango más amplio.`"
        compact
      />
      <div v-else class="h-40 flex items-stretch gap-1">
        <div
          v-for="h in horasConVenta"
          :key="h.label"
          class="flex-1 flex flex-col items-center gap-1 group min-w-0 h-full"
        >
          <span
            class="text-[9px] font-semibold text-slate-500 dark:text-slate-400 tabular-nums truncate w-full text-center leading-none"
            :title="fc(h.valor)"
          >{{ fcCorto(h.valor) }}</span>
          <div class="w-full flex-1 min-h-0 bg-slate-100 dark:bg-slate-800 rounded-t-sm relative overflow-hidden">
            <div
              class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-emerald-500 to-emerald-300 rounded-t-sm transition-all duration-500 ease-out-expo group-hover:from-emerald-400 group-hover:to-emerald-200"
              :style="{ height: `${(h.valor / maxHour) * 100}%` }"
            ></div>
              <div class="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 opacity-0 group-hover:opacity-100 transition-opacity text-[10px] font-semibold text-slate-700 dark:text-slate-200 whitespace-nowrap bg-white dark:bg-slate-800 px-2 py-1 rounded-md shadow-sm border border-slate-100 dark:border-slate-700 pointer-events-none">
                {{ fc(h.valor) }}
              </div>
            </div>
            <span class="text-[9px] font-medium text-slate-500 dark:text-slate-400">{{ h.label.replace(':00', '') }}</span>
          </div>
        </div>
      </BaseCard>
    </div>

    <!-- Ventas por categoría -->
    <BaseCard padding="lg">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <h3 class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
          <i class="fa-solid fa-layer-group text-brand-500"></i>
          Ventas por Categoría
        </h3>
        <div class="flex items-center gap-2 flex-wrap">
          <div class="flex items-center gap-1 p-0.5 bg-slate-100 dark:bg-slate-800 rounded-lg">
            <button
              v-for="p in PERIODOS"
              :key="p.value"
              type="button"
              class="px-2.5 py-1 text-[11px] font-semibold rounded-md transition"
              :class="catPeriodo === p.value
                ? 'bg-white dark:bg-slate-700 text-brand-600 dark:text-brand-400 shadow-sm'
                : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
              @click="setCatPeriodo(p.value)"
            >
              {{ p.label }}
            </button>
          </div>
          <select
            :value="catMetrica"
            class="text-[11px] font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-2.5 py-1.5 focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
            @change="setCatMetrica($event.target.value)"
          >
            <option v-for="m in METRICAS" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
        </div>
      </div>
      <p v-if="catData?.desde" class="text-[10px] text-slate-400 dark:text-slate-500 -mt-3 mb-3">
        {{ catData.desde }} &ndash; {{ catData.hasta }}
      </p>

      <div v-if="catLoading" class="space-y-3">
        <BaseSkeleton v-for="n in 5" :key="n" class="h-8 rounded-lg" />
      </div>
      <EmptyState
        v-else-if="!catFilas.length"
        icon="fa-layer-group"
        title="Sin ventas por categoría"
        text="No hay ventas confirmadas en el período seleccionado."
        compact
      />
      <div v-else class="space-y-2">
        <div
          v-for="r in catFilas"
          :key="r.clave"
          class="rounded-xl border border-transparent hover:border-slate-200 dark:hover:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors"
        >
          <button
            type="button"
            class="w-full text-left px-3 py-2.5"
            :class="r.clave === 'otras' ? 'cursor-default' : 'cursor-pointer'"
            @click="toggleCategoria(r)"
          >
            <div class="flex items-center justify-between gap-3 mb-1.5">
              <span class="text-xs font-medium text-slate-700 dark:text-slate-200 truncate flex items-center gap-1.5">
                <i
                  v-if="r.clave !== 'otras'"
                  class="fa-solid text-[9px] text-slate-400 dark:text-slate-500 transition-transform"
                  :class="catAbierta(r.clave) ? 'rotate-90' : ''"
                ></i>
                <i v-else class="fa-solid fa-ellipsis text-[9px] text-slate-400 dark:text-slate-500"></i>
                {{ r.categoria }}
                <i
                  v-if="r.items_sin_costo > 0"
                  class="fa-solid fa-circle-exclamation text-amber-500 text-[10px] shrink-0"
                  :title="`${r.items_sin_costo} producto(s) sin costo cargado: la ganancia de esta categoría no es exacta`"
                ></i>
              </span>
              <span class="text-xs font-mono-data font-semibold text-slate-800 dark:text-slate-100 shrink-0">
                {{ fmtMetrica(r) }}
              </span>
            </div>
            <div class="h-2.5 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-500 ease-out-expo"
                :class="catMetrica === 'ganancia' ? 'bg-gradient-to-r from-emerald-500 to-emerald-300'
                  : catMetrica === 'margen_pct' ? 'bg-gradient-to-r from-amber-500 to-amber-300'
                  : catMetrica === 'cantidad' ? 'bg-gradient-to-r from-sky-500 to-sky-300'
                  : 'bg-gradient-to-r from-brand-600 to-brand-400'"
                :style="{ width: pctCat(r[catMetrica]) + '%' }"
              ></div>
            </div>
          </button>

          <!-- Productos de la categoría: para ver cuáles son los que venden y
               de qué subcategoría viene cada uno (ojo si no corresponde) -->
          <div v-if="catAbierta(r.clave)" class="px-3 pb-2.5">
            <div class="border-t border-slate-100 dark:border-slate-800 pt-2 space-y-0.5">
              <div v-if="catAbiertas[r.clave] === 'cargando'" class="space-y-2 pt-1">
                <BaseSkeleton v-for="n in 3" :key="n" class="h-9 rounded-lg" />
              </div>
              <template v-else>
                <p v-if="catAbiertas[r.clave] === 'error'" class="text-[11px] text-red-500 py-2">
                  No se pudieron cargar los productos.
                </p>
                <p v-else-if="!(catProductos[r.clave] || []).length" class="text-[11px] text-slate-400 dark:text-slate-500 py-2">
                  Sin productos para mostrar.
                </p>
                <button
                  v-for="p in (catProductos[r.clave] || [])"
                  :key="p.id"
                  type="button"
                  class="w-full flex items-center gap-3 px-2 py-1.5 rounded-lg text-left hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors group"
                  @click="irAProducto(p)"
                >
                  <span class="flex-1 min-w-0">
                    <span class="block text-xs font-medium text-slate-700 dark:text-slate-200 truncate">
                      {{ p.nombre }}
                    </span>
                    <span class="block text-[10px] text-slate-400 dark:text-slate-500 truncate">
                      {{ p.categoria }}
                      <i
                        v-if="p.items_sin_costo > 0"
                        class="fa-solid fa-circle-exclamation text-amber-500 ml-1"
                        :title="`${p.items_sin_costo} venta(s) sin costo cargado`"
                      ></i>
                    </span>
                  </span>
                  <span class="text-[10px] font-mono-data text-slate-500 dark:text-slate-400 shrink-0">
                    {{ p.cantidad }} u
                  </span>
                  <span class="text-xs font-mono-data font-semibold text-slate-800 dark:text-slate-100 shrink-0 w-20 text-right">
                    {{ fmtMetrica(p) }}
                  </span>
                  <i class="fa-solid fa-pen text-[9px] text-slate-300 dark:text-slate-600 group-hover:text-brand-500 transition-colors shrink-0"></i>
                </button>
              </template>
            </div>
          </div>
        </div>
        <p v-if="catData?.categorias?.some((r) => r.clave === 'otras')" class="text-[10px] text-slate-400 dark:text-slate-500 pt-1 px-3">
          {{ catData.cantidad_categorias }} categorías con ventas; las últimas están agrupadas en "Otras".
        </p>
      </div>
    </BaseCard>

    <!-- Lists -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <BaseCard padding="lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
            <i class="fa-solid fa-trophy text-amber-500"></i>
            Top Productos del Mes
          </h3>
        </div>
        <div v-if="loading" class="space-y-3">
          <BaseSkeleton v-for="n in 3" :key="n" class="h-10 rounded-lg" />
        </div>
        <div v-else-if="(data.top_productos_mes || []).length" class="space-y-2">
          <div
            v-for="(p, idx) in (data.top_productos_mes || [])"
            :key="p.id"
            class="flex items-center gap-3 p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl text-sm transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
          >
            <span class="w-6 h-6 flex items-center justify-center rounded-lg bg-white dark:bg-slate-700 text-xs font-bold text-slate-500 dark:text-slate-300 shadow-sm">{{ idx + 1 }}</span>
            <span class="flex-1 font-medium text-slate-800 dark:text-slate-100 truncate">{{ p.nombre }}</span>
            <span class="text-xs text-slate-500 dark:text-slate-400">{{ p.cantidad_vendida }} u</span>
            <span class="font-mono-data font-semibold text-emerald-600 dark:text-emerald-400">{{ fc(p.total_vendido) }}</span>
          </div>
        </div>
        <EmptyState v-else icon="fa-cart-arrow-down" title="Sin ventas este mes" text="Aún no hay productos destacados." compact />
      </BaseCard>

      <BaseCard padding="lg">
        <div class="flex items-center justify-between mb-4">
          <h3 class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
            <i class="fa-solid fa-triangle-exclamation text-red-500"></i>
            Alertas de Stock
          </h3>
        </div>
        <div v-if="loading" class="space-y-3">
          <BaseSkeleton v-for="n in 3" :key="n" class="h-10 rounded-lg" />
        </div>
        <div v-else-if="(data.stock_critico || []).length || (data.sin_stock || []).length" class="space-y-4">
          <div v-if="(data.stock_critico || []).length">
            <p class="text-[10px] font-bold text-red-500 uppercase tracking-wider mb-2">Críticos (bajo mínimo)</p>
            <div v-for="p in data.stock_critico" :key="'c'+p.id" class="flex justify-between text-sm p-3 bg-red-50 dark:bg-red-900/20 rounded-xl mb-2">
              <span class="font-medium truncate flex-1 text-slate-800 dark:text-slate-100">{{ p.nombre }}</span>
              <span class="font-mono-data font-semibold text-red-600 dark:text-red-300">{{ p.stock_actual }} / {{ p.stock_minimo }}</span>
            </div>
          </div>
          <div v-if="(data.sin_stock || []).length">
            <p class="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">Sin stock</p>
            <div v-for="p in data.sin_stock" :key="'s'+p.id" class="flex justify-between text-sm p-3 bg-slate-100 dark:bg-slate-800 rounded-xl mb-2">
              <span class="font-medium truncate flex-1 text-slate-800 dark:text-slate-100">{{ p.nombre }}</span>
              <span class="font-mono-data text-slate-500 dark:text-slate-400">{{ p.codigo_barras }}</span>
            </div>
          </div>
        </div>
        <EmptyState v-else icon="fa-check-circle" title="Todo en orden" text="No hay alertas de stock activas." compact />
      </BaseCard>
    </div>

    <!-- Qué comprar: stock real cruzado con el ritmo de venta -->
    <BaseCard padding="lg" class="mt-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <h3 class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
          <i class="fa-solid fa-gauge-high text-brand-500"></i>
          Se agota pronto
          <span v-if="velData?.total_criticos" class="text-[10px] font-bold text-red-500 bg-red-50 dark:bg-red-900/30 px-1.5 py-0.5 rounded-full">
            {{ velData.total_criticos }}
          </span>
        </h3>
        <div class="flex items-center gap-2">
          <label class="flex items-center gap-1.5 text-[11px] text-slate-500 dark:text-slate-400">
            <input v-model="velTodos" type="checkbox" class="rounded border-slate-300" @change="loadVelocidad" />
            ver todos
          </label>
          <select
            :value="velDias"
            class="text-[11px] font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-2 py-1.5"
            @change="velDias = +$event.target.value; loadVelocidad()"
          >
            <option :value="7">Ritmo 7 días</option>
            <option :value="30">Ritmo 30 días</option>
            <option :value="90">Ritmo 90 días</option>
          </select>
        </div>
      </div>

      <div v-if="velLoading" class="space-y-2">
        <BaseSkeleton v-for="n in 4" :key="n" class="h-11 rounded-lg" />
      </div>
      <template v-else-if="velData?.productos?.length">
        <div class="space-y-2">
          <div
            v-for="p in velData.productos"
            :key="p.id"
            class="flex items-center justify-between gap-3 p-3 rounded-xl border"
            :class="p.urgente
              ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/50'
              : 'bg-slate-50 dark:bg-slate-800/50 border-slate-100 dark:border-slate-700'"
          >
            <div class="min-w-0 flex-1">
              <p class="text-sm font-semibold text-slate-800 dark:text-slate-100 truncate">{{ p.nombre }}</p>
              <p class="text-[11px] text-slate-500 dark:text-slate-400">
                quedan {{ p.stock_actual }} &middot; vende {{ p.por_dia }}/día
                <span v-if="p.stock_minimo > 0"> &middot; mínimo {{ p.stock_minimo }}</span>
              </p>
            </div>
            <span
              class="text-xs font-bold font-mono-data shrink-0"
              :class="p.urgente ? 'text-red-600 dark:text-red-300' : 'text-amber-600 dark:text-amber-300'"
            >
              {{ diasLegibles(p.dias_stock) }}
            </span>
            <BaseButton size="xs" variant="ghost" @click="irAProducto(p)">
              <i class="fa-solid fa-pen"></i>
            </BaseButton>
          </div>
        </div>
        <p class="text-[10px] text-slate-400 dark:text-slate-500 mt-3">
          Calculado con las ventas de los últimos {{ velData.dias }} días.
        </p>
      </template>
      <EmptyState
        v-else
        icon="fa-check-circle"
        title="Nada se está agotando"
        :text="velTodos
          ? 'No hay productos activos en el catálogo.'
          : `Ningún producto baja de 7 días de stock con el ritmo de los últimos ${velData?.dias || velDias} días.`"
        compact
      />
    </BaseCard>

    <!-- Calidad de datos: lo que hace que los números de arriba mientan -->
    <BaseCard padding="lg" class="mt-6">
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-5">
        <h3 class="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
          <i class="fa-solid fa-triangle-exclamation text-amber-500"></i>
          Datos a corregir
        </h3>
        <select
          :value="sucioPeriodo"
          class="text-[11px] font-semibold rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-700 dark:text-slate-200 px-2 py-1.5"
          @change="setSucioPeriodo($event.target.value)"
        >
          <option value="hoy">Hoy</option>
          <option value="semana">Semana</option>
          <option value="mes">Mes</option>
          <option value="trimestre">Trimestre</option>
        </select>
      </div>

      <div v-if="sucioLoading" class="space-y-2">
        <BaseSkeleton v-for="n in 3" :key="n" class="h-10 rounded-lg" />
      </div>
      <template v-else-if="sucioData?.cantidad">
        <div class="flex items-center gap-3 p-3 mb-3 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800/50">
          <i class="fa-solid fa-circle-info text-amber-500"></i>
          <p class="text-xs text-amber-800 dark:text-amber-200">
            <strong>{{ sucioData.cantidad }}</strong> producto{{ sucioData.cantidad === 1 ? '' : 's' }}
            con datos incompletos representa{{ sucioData.cantidad === 1 ? '' : 'n' }}
            <strong>{{ fc(sucioData.importe_afectado) }}</strong>
            ({{ sucioData.pct_afectado }}% de lo vendido en el período).
          </p>
        </div>

        <button
          type="button"
          class="text-[11px] font-semibold text-brand-600 dark:text-brand-400 hover:underline mb-2"
          @click="suciosAbiertos = !suciosAbiertos"
        >
          {{ suciosAbiertos ? 'Ocultar' : 'Ver' }} el detalle
        </button>

        <div v-if="suciosAbiertos" class="space-y-3">
          <div v-if="sucioData.sin_costo.length">
            <p class="text-[10px] font-bold text-red-500 uppercase tracking-wider mb-1.5">
              Sin costo cargado (margen inflado)
            </p>
            <div
              v-for="p in sucioData.sin_costo"
              :key="'c'+p.id"
              class="flex items-center justify-between gap-2 text-sm p-2.5 bg-red-50 dark:bg-red-900/20 rounded-lg mb-1.5"
            >
              <span class="font-medium truncate flex-1 text-slate-800 dark:text-slate-100">{{ p.nombre }}</span>
              <span class="font-mono-data text-xs text-red-600 dark:text-red-300 shrink-0">{{ fc(p.importe) }}</span>
              <BaseButton size="xs" variant="ghost" @click="irAProducto(p)"><i class="fa-solid fa-pen"></i></BaseButton>
            </div>
          </div>
          <div v-if="sucioData.sin_categoria.length">
            <p class="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
              Sin categoría (no aparece en el gráfico)
            </p>
            <div
              v-for="p in sucioData.sin_categoria"
              :key="'s'+p.id"
              class="flex items-center justify-between gap-2 text-sm p-2.5 bg-slate-100 dark:bg-slate-800 rounded-lg mb-1.5"
            >
              <span class="font-medium truncate flex-1 text-slate-800 dark:text-slate-100">{{ p.nombre }}</span>
              <span class="font-mono-data text-xs text-slate-500 dark:text-slate-400 shrink-0">{{ fc(p.importe) }}</span>
              <BaseButton size="xs" variant="ghost" @click="irAProducto(p)"><i class="fa-solid fa-pen"></i></BaseButton>
            </div>
          </div>
        </div>
      </template>
      <EmptyState
        v-else
        icon="fa-check-circle"
        title="Datos completos"
        text="Todos los productos vendidos en el período tienen costo y categoría."
        compact
      />
    </BaseCard>
  </div>
</template>
