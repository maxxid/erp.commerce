<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'

const toast = useToastStore()

const saving = ref(false)
const loading = ref(true)
const generando = ref(false)
const subiendo = ref(false)
const csrGenerado = ref(false)
const csrContent = ref('')
const claveContent = ref('')
const certInfo = ref(null)
const certUpload = ref('')
const showGuide = ref(false)
const certContent = ref('')
const keyUpload = ref('')
const pemUpload = ref('')
const afipExpanded = ref(false)
const facturacionExpanded = ref(false)
const bancariosExpanded = ref(false)
const mercadopagoExpanded = ref(false)
const qrInteropExpanded = ref(false)
const ventasExpanded = ref(false)
const denominacionesExpanded = ref(false)
const recargasExpanded = ref(false)

// --- Servicio de recargas ---
const savingRecargas = ref(false)
const recargas = ref({ monto_base: 1000, adicional_pct: 10, medio_pago_carga: 'smartpoint', producto_id: null })
const productosRecarga = ref([])

const MEDIOS_CARGA = [
  { value: 'smartpoint', label: 'Smart Point' },
  { value: 'mercadopago_qr', label: 'MercadoPago QR' },
  { value: 'mercadopago_pos', label: 'MercadoPago POS' },
  { value: 'qr_interop', label: 'QR BCRA (Interoperable)' },
  { value: 'debito', label: 'Débito' },
  { value: 'credito', label: 'Crédito' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'efectivo', label: 'Efectivo' },
]
const mediosCarga = computed(() => MEDIOS_CARGA)
const productosSinStock = computed(() => productosRecarga.value)
const recargaPrecioUnitario = computed(() => {
  const base = recargas.value.monto_base || 0
  const pct = recargas.value.adicional_pct || 0
  return Math.round(base * (1 + pct / 100) * 100) / 100
})

async function loadRecargas() {
  try {
    const [cfg, prods] = await Promise.all([
      api.get('/api/recargas/config'),
      api.get('/api/productos?page_size=500').catch(() => null),
    ])
    if (cfg) {
      recargas.value = {
        monto_base: cfg.monto_base ?? 1000,
        adicional_pct: cfg.adicional_pct ?? 10,
        medio_pago_carga: cfg.medio_pago_carga || 'smartpoint',
        producto_id: cfg.producto_id ?? null,
      }
    }
    const lista = prods?.data || prods || []
    if (Array.isArray(lista)) {
      productosRecarga.value = lista
        .filter(p => p.controla_stock === false)
        .map(p => ({ id: p.id, nombre: p.nombre, precio_venta: p.precio_venta }))
    }
  } catch { /* la card queda con los defaults */ }
}

async function saveRecargas() {
  savingRecargas.value = true
  try {
    const data = await api.put('/api/recargas/config', {
      monto_base: recargas.value.monto_base,
      adicional_pct: recargas.value.adicional_pct,
      medio_pago_carga: recargas.value.medio_pago_carga,
      producto_id: recargas.value.producto_id,
    })
    if (data) {
      recargas.value = { ...recargas.value, ...data }
    }
    toast.success('Configuración de recargas guardada')
  } catch (e) {
    toast.error(e?.response?.data?.detail || 'No se pudo guardar la configuración')
  } finally {
    savingRecargas.value = false
  }
}

const denominaciones = ref([])
const denominacionesEliminadas = ref([])
const guardandoDenoms = ref(false)
const cargandoDenoms = ref(false)

// Carritos del POS por defecto ("Mostrador", "Mesa 1", ...). Se guardan como
// JSON en la config pos_carritos_default y el POS los respeta por nombre.
const carritosDefault = ref([])
const nombreCarritoDefault = ref('')
const carritosDefaultExpanded = ref(false)

const TIPOS_DENOM = [
  { value: 'billete', label: 'Billete' },
  { value: 'moneda', label: 'Moneda' },
]

// MercadoPago store/POS creation
const creandoStore = ref(false)
const creandoCaja = ref(false)
const storeCreado = ref(false)
const cajaCreada = ref(false)
const mpStoreId = ref('')
const mpCajaId = ref('')
const qrFijoUrl = ref('')
const storeForm = ref({
  nombre: '',
  external_id: 'SUC001',
  street_number: '',
  street_name: '',
  city_name: 'San Salvador de Jujuy',
  state_name: 'Jujuy',
  latitude: -34.6037,
  longitude: -58.3816,
  reference: ''
})
const cajaForm = ref({
  nombre: '',
  external_id: 'CAJA001',
  external_store_id: ''
})

const config = ref({
    afip_mode: 'testing',
    facturacion_provider: 's360',
    afip_cuit: '',
    afip_pto_vta: '1',
    afip_cert: '',
    afip_key: '',
    facturacion_s360_token: '',
    banco_nombre: '',
    banco_titular: '',
    banco_alias: '',
    pos_carritos_default: '',
    empresa_nombre: '',
  empresa_domicilio: '',
  empresa_condicion_iva: 'responsable_inscripto',
  empresa_ingresos_brutos: '',
  empresa_fecha_inicio: '',
  mercadopago_enabled: 'false',
  mercadopago_access_token: '',
  mercadopago_user_id: '',
  mercadopago_store_id: '',
  mercadopago_external_store_id: '',
  mercadopago_external_pos_id: '',
  mercadopago_pos_id_qr: '',
  mercadopago_pos_id_smart: '',
  mercadopago_mode: 'sandbox',
  mercadopago_qr_fijo_url: '',
  mercadopago_qr_fijo_modo: 'dinamico',
  mercadopago_webhook_secret: '',
  qr_interop_cuit: '',
  qr_interop_cuenta: '',
  qr_interop_nombre: '',
  qr_interop_ciudad: '',
  qr_interop_mcc: '9700',
})

const facturaAuto = ref({
  efectivo: false,
  debito: false,
  credito: false,
  transferencia: false,
  cta_corriente: false,
  mercadopago_qr: true,
  mercadopago_pos: true,
})

async function loadConfig() {
  loading.value = true
  try {
    const data = await api.get('/api/config/ajustes')
    if (data) {
      for (const key of Object.keys(config.value)) {
        if (data[key]) config.value[key] = data[key].valor || ''
      }
      try {
        const lista = JSON.parse(config.value.pos_carritos_default || '[]')
        carritosDefault.value = (Array.isArray(lista) ? lista : []).map(n => String(n).trim()).filter(Boolean)
      } catch {
        carritosDefault.value = []
      }
      const medios = ['efectivo', 'debito', 'credito', 'transferencia', 'cta_corriente', 'mercadopago_qr', 'mercadopago_pos']
      for (const medio of medios) {
        const configKey = `factura_auto_${medio}`
        if (data[configKey]) {
          facturaAuto.value[medio] = data[configKey].valor === 'true'
        }
      }
    }
    await loadCertInfo()
  } catch {
    toast.warning('No se pudieron cargar ajustes')
  }
  loading.value = false
}

async function loadCertInfo() {
  try {
    const resp = await api.get('/api/facturacion/afip/certificado-info')
    certInfo.value = (resp && resp !== null) ? resp : null
  } catch {
    certInfo.value = null
  }
  try {
    const pemResp = await api.get('/api/facturacion/afip/certificado-pem')
    if (pemResp && pemResp.cert_pem) {
      certUpload.value = pemResp.cert_pem
      certContent.value = pemResp.cert_pem
    }
  } catch {
    // no saved cert
  }
  try {
    const csrResp = await api.get('/api/facturacion/afip/csr-guardado')
    if (csrResp && csrResp.csr_pem) {
      csrContent.value = csrResp.csr_pem
      csrGenerado.value = true
    }
  } catch {
    // no saved CSR
  }
}

const AFIP_BASIC_KEYS = ['afip_mode', 'facturacion_provider', 'afip_cuit', 'afip_pto_vta']
const BANCOS_KEYS = ['banco_nombre', 'banco_titular', 'banco_alias']
const EMISOR_KEYS = ['empresa_nombre', 'empresa_domicilio', 'empresa_condicion_iva', 'empresa_ingresos_brutos', 'empresa_fecha_inicio']
const AFIP_ALL_KEYS = [...AFIP_BASIC_KEYS, ...EMISOR_KEYS]

const descs = {
  afip_mode: 'Entorno AFIP: testing | production',
  facturacion_provider: 'Proveedor: s360 (recomendado) o afip (directo)',
  afip_cuit: 'CUIT del emisor (11 dígitos sin guiones)',
  afip_pto_vta: 'Número de punto de venta habilitado en AFIP',
  afip_cert: 'Certificado X.509 (.crt) en formato PEM',
  afip_key: 'Clave privada RSA (.key) en formato PEM',
  banco_nombre: 'Nombre del banco para transferencias',
  banco_titular: 'Nombre del titular de la cuenta',
  banco_alias: 'Alias de CBU/Alias para transferencias',
  empresa_nombre: 'Razón Social para facturas electrónicas',
  empresa_domicilio: 'Domicilio comercial para facturas',
  empresa_condicion_iva: 'Condición frente al IVA: responsable_inscripto, monotributista, exento',
  empresa_ingresos_brutos: 'Número de Ingresos Brutos (o "Exento")',
  empresa_fecha_inicio: 'Fecha de inicio de actividades (YYYY-MM-DD)',
  mercadopago_enabled: 'Habilitar cobros con QR de MercadoPago',
  mercadopago_access_token: 'Access Token de MercadoPago (del portal de desarrolladores)',
  mercadopago_pos_id_qr: 'ID del POS para QR (genera códigos QR dinámicos)',
  mercadopago_pos_id_smart: 'ID del Smart Point (dispositivo físico)',
  mercadopago_mode: 'Entorno: sandbox (pruebas) o prod (producción)',
  mercadopago_qr_fijo_url: 'URL o código base64 del QR fijo (imagen para imprimir)',
  mercadopago_qr_fijo_modo: 'Modo QR: dinamico (solo QR en pantalla) o hibrido (QR fijo + dinámico)',
  mercadopago_webhook_secret: 'Clave secreta para validar webhooks de MercadoPago',
  qr_interop_cuit: 'CUIT/CUIL del comercio (11 dígitos, obligatorio en el QR interoperable)',
  qr_interop_cuenta: 'CBU (22) o CVU (23), o alias de la cuenta donde llega el pago',
  qr_interop_nombre: 'Nombre corto del comercio que se muestra en el QR (máx. 25 caracteres)',
  qr_interop_ciudad: 'Ciudad del comercio (opcional, máx. 15 caracteres)',
  qr_interop_mcc: 'Código de categoría del comercio (MCC, 4 dígitos). "9700" es el valor estándar de los QRs de transferencia',
  factura_auto_efectivo: 'Emitir factura electrónica automáticamente al cobrar en efectivo',
  factura_auto_debito: 'Emitir factura electrónica automáticamente al cobrar con débito',
  factura_auto_credito: 'Emitir factura electrónica automáticamente al cobrar con crédito',
  factura_auto_transferencia: 'Emitir factura electrónica automáticamente al cobrar con transferencia',
  factura_auto_cta_corriente: 'Emitir factura electrónica automáticamente al cobrar a cuenta corriente',
  factura_auto_mercadopago_qr: 'Emitir factura electrónica automáticamente al cobrar con MercadoPago QR',
  factura_auto_mercadopago_pos: 'Emitir factura electrónica automáticamente al cobrar con MercadoPago POS',
}

const MP_KEYS = ['mercadopago_enabled', 'mercadopago_access_token', 'mercadopago_user_id', 'mercadopago_store_id', 'mercadopago_external_store_id', 'mercadopago_external_pos_id', 'mercadopago_pos_id_qr', 'mercadopago_pos_id_smart', 'mercadopago_mode', 'mercadopago_qr_fijo_url', 'mercadopago_qr_fijo_modo', 'mercadopago_webhook_secret']

const QR_INTEROP_KEYS = ['qr_interop_cuit', 'qr_interop_cuenta', 'qr_interop_nombre', 'qr_interop_ciudad', 'qr_interop_mcc']

const VENTAS_KEYS = ['factura_auto_efectivo', 'factura_auto_debito', 'factura_auto_credito', 'factura_auto_transferencia', 'factura_auto_cta_corriente', 'factura_auto_mercadopago_qr', 'factura_auto_mercadopago_pos']

async function saveConfig(keys = null) {
  saving.value = true
  try {
    if (keys && keys === VENTAS_KEYS) {
      for (const [key, value] of Object.entries(facturaAuto.value)) {
        const configKey = `factura_auto_${key}`
        await api.put('/api/config/ajustes', { clave: configKey, valor: String(value), descripcion: descs[configKey] || '' })
      }
    } else {
      const entries = keys
        ? Object.entries(config.value).filter(([k]) => keys.includes(k))
        : Object.entries(config.value)
      for (const [clave, valor] of entries) {
        await api.put('/api/config/ajustes', { clave, valor, descripcion: descs[clave] || '' })
      }
    }
    toast.success('Configuración guardada')
  } catch {
    toast.error('Error al guardar configuración')
  }
  saving.value = false
}

function agregarCarritoDefault() {
  const nombre = nombreCarritoDefault.value.trim().slice(0, 40)
  if (!nombre) return
  if (carritosDefault.value.includes(nombre)) {
    toast.warning(`"${nombre}" ya esta en la lista`)
    return
  }
  carritosDefault.value.push(nombre)
  nombreCarritoDefault.value = ''
}

function quitarCarritoDefault(nombre) {
  carritosDefault.value = carritosDefault.value.filter(n => n !== nombre)
}

async function saveCarritosDefault() {
  saving.value = true
  try {
    await api.put('/api/config/ajustes', {
      clave: 'pos_carritos_default',
      valor: JSON.stringify(carritosDefault.value),
      descripcion: 'Lista de carritos por defecto del POS (JSON)',
    })
    config.value.pos_carritos_default = JSON.stringify(carritosDefault.value)
    toast.success('Carritos por defecto guardados')
  } catch {
    toast.error('Error al guardar la configuración')
  }
  saving.value = false
}

async function loadDenominaciones() {
  cargandoDenoms.value = true
  try {
    const resp = await api.get('/api/denominaciones?incluir_inactivas=true')
    denominaciones.value = (resp || []).map(d => ({ ...d }))
    denominacionesEliminadas.value = []
  } catch {
    toast.warning('No se pudieron cargar las denominaciones')
  }
  cargandoDenoms.value = false
}

function agregarDenominacion() {
  const ultimo = denominaciones.value[denominaciones.value.length - 1]
  denominaciones.value.push({
    id: null,
    valor: null,
    tipo: ultimo ? ultimo.tipo : 'moneda',
    activo: true,
  })
}

function quitarDenominacion(d) {
  if (d.id) denominacionesEliminadas.value.push(d.id)
  denominaciones.value = denominaciones.value.filter(x => x !== d)
}

function cambiarTipoDenominacion(d, tipo) {
  d.tipo = tipo
}

function formatearDenominacion(valor) {
  const n = Number(valor)
  return n > 0 ? '$ ' + n.toLocaleString('es-AR') : '—'
}

async function guardarDenominaciones() {
  const lista = denominaciones.value
  if (lista.length === 0) {
    toast.warning('Debe haber al menos una denominación')
    return
  }
  if (lista.some(d => !(Number(d.valor) > 0))) {
    toast.warning('Todas las denominaciones necesitan un valor mayor a 0')
    return
  }
  const valores = lista.map(d => Number(d.valor))
  if (new Set(valores).size !== valores.length) {
    toast.warning('No puede haber dos denominaciones con el mismo valor')
    return
  }
  guardandoDenoms.value = true
  try {
    for (const id of denominacionesEliminadas.value) {
      await api.delete(`/api/denominaciones/${id}`)
    }
    for (const d of lista) {
      const body = { valor: Number(d.valor), tipo: d.tipo, activo: !!d.activo }
      if (d.id) await api.put(`/api/denominaciones/${d.id}`, body)
      else await api.post('/api/denominaciones', body)
    }
    toast.success('Denominaciones guardadas')
    await loadDenominaciones()
  } catch (e) {
    toast.error(e?.message || 'Error al guardar las denominaciones')
    await loadDenominaciones()
  }
  guardandoDenoms.value = false
}

async function restaurarDefaultsDenominaciones() {
  if (!confirm('¿Restaurar las denominaciones por defecto? Se pierden los valores, tipos y estados actuales.')) return
  guardandoDenoms.value = true
  try {
    await api.post('/api/denominaciones/restaurar-defaults')
    toast.success('Denominaciones restauradas')
    await loadDenominaciones()
  } catch {
    toast.error('Error al restaurar las denominaciones')
  }
  guardandoDenoms.value = false
}

async function crearSucursalMp() {
  if (!storeForm.value.nombre) {
    toast.warning('Ingresá un nombre para la sucursal')
    return
  }
  if (!storeForm.value.external_id) {
    toast.warning('Ingresá un ID externo para la sucursal')
    return
  }
  creandoStore.value = true
  try {
    const resp = await api.post('/api/pagos/mercadopago/crear-sucursal', storeForm.value)
    if (resp && resp.success) {
      mpStoreId.value = resp.store_id
      storeCreado.value = true
      cajaForm.value.external_store_id = storeForm.value.external_id
      config.value.mercadopago_store_id = String(resp.store_id)
      config.value.mercadopago_external_store_id = storeForm.value.external_id
      await saveConfig(['mercadopago_store_id', 'mercadopago_external_store_id'])
      toast.success(`Sucursal creada! ID: ${resp.store_id}`)
    }
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al crear sucursal')
  }
  creandoStore.value = false
}

async function crearCajaMp() {
  if (!mpStoreId.value) {
    toast.warning('Primero tenés que crear una sucursal')
    return
  }
  if (!cajaForm.value.nombre) {
    toast.warning('Ingresá un nombre para la caja')
    return
  }
  if (!cajaForm.value.external_id) {
    toast.warning('Ingresá un ID externo para la caja')
    return
  }
  creandoCaja.value = true
  try {
    const resp = await api.post('/api/pagos/mercadopago/crear-caja', {
      nombre: cajaForm.value.nombre,
      external_id: cajaForm.value.external_id,
      external_store_id: storeForm.value.external_id,
      fixed_amount: true,
      category: 621102
    })
    if (resp && resp.success) {
      mpCajaId.value = resp.pos_id
      qrFijoUrl.value = resp.qr_image_url || ''
      config.value.mercadopago_pos_id_qr = String(resp.pos_id)
      config.value.mercadopago_external_pos_id = cajaForm.value.external_id
      config.value.mercadopago_qr_fijo_url = resp.qr_image_url || ''
      cajaCreada.value = true
      await saveConfig(['mercadopago_pos_id_qr', 'mercadopago_external_pos_id', 'mercadopago_qr_fijo_url'])
      toast.success(`Caja creada! POS ID: ${resp.pos_id}`)
    }
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al crear caja')
  }
  creandoCaja.value = false
}

async function generarCsr() {
  if (!config.value.afip_cuit || config.value.afip_cuit.length !== 11) {
    toast.warning('Ingresá un CUIT de 11 dígitos primero')
    return
  }
  generando.value = true
  try {
    const resp = await api.post('/api/facturacion/afip/generar-csr', {
      cuit: config.value.afip_cuit,
      pto_vta: parseInt(config.value.afip_pto_vta) || 1,
      razon_social: '',
    })
    csrContent.value = resp.csr_pem
    csrGenerado.value = true
    toast.success('CSR generado. Descargalo y subilo a ARCA.')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al generar CSR')
  }
  generando.value = false
}

function descargarCsr() {
  const content = csrContent.value.replace(/\\n/g, '\n')
  const blob = new Blob([content], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `afip_csr_${config.value.afip_cuit}.csr`
  a.click()
  URL.revokeObjectURL(url)
}

async function descargarKey() {
  try {
    const resp = await api.get('/api/facturacion/afip/descargar-clave')
    const content = resp.clave_pem
    const blob = new Blob([content], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `afip_key_${config.value.afip_cuit}.key`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Clave privada descargada')
  } catch {
    toast.error('No hay clave para descargar')
  }
}

async function subirCertificado() {
  if (!certUpload.value.trim()) {
    toast.warning('Pegá el contenido del certificado .crt')
    return
  }
  subiendo.value = true
  try {
    const resp = await api.post('/api/facturacion/afip/subir-certificado', {
      cert_pem: certUpload.value,
    })
    certInfo.value = resp
    certContent.value = certUpload.value
    certUpload.value = ''
    toast.success(resp.message || resp.mensaje || 'Certificado guardado')
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al subir certificado')
  }
  subiendo.value = false
}

function cargarCsrDesdeArchivo(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async (e) => {
    const content = e.target.result
    csrContent.value = content.replace(/\n/g, '\\n')
    csrGenerado.value = true
    try {
      await api.post('/api/facturacion/afip/cargar-csr', { csr_pem: content })
    } catch {
      // guardar igual en memoria aunque falle el sync
    }
    toast.success('CSR cargado. Ahora subilo a ARCA para obtener el certificado.')
  }
  reader.readAsText(file)
}

function cargarCertDesdeArchivo(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => {
    certUpload.value = e.target.result
    toast.success('Certificado cargado. Click en Guardar para guardarlo.')
  }
  reader.readAsText(file)
}

function cargarKeyDesdeArchivo(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async (e) => {
    keyUpload.value = e.target.result
    try {
      await api.post('/api/facturacion/afip/subir-key', { key_pem: e.target.result })
      toast.success('Clave privada .key guardada')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al guardar clave')
    }
  }
  reader.readAsText(file)
}

function cargarPemDesdeArchivo(event) {
  const file = event.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async (e) => {
    pemUpload.value = e.target.result
    try {
      await api.post('/api/facturacion/afip/subir-pem', { contenido: e.target.result })
      toast.success('Archivo .pem guardado')
      await loadCertInfo()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al guardar .pem')
    }
  }
  reader.readAsText(file)
}

function copiarCsr() {
  navigator.clipboard.writeText(csrContent.value.replace(/\\n/g, '\n'))
  toast.success('CSR copiado al portapapeles')
}

function displayCsr() {
  return csrContent.value.replace(/\\n/g, '\n')
}

onMounted(async () => {
  await loadConfig()
  await loadDenominaciones()
  await loadRecargas()
})
</script>

<template>
  <div class="space-y-5">
    <div>
      <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">Ajustes</h2>
      <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Configuración del sistema y AFIP</p>
    </div>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="afipExpanded = !afipExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-regular fa-file-lines text-brand-600"></i>
            Factura Electrónica AFIP / ARCA
          </h3>
          <div class="flex items-center gap-3">
            <span v-if="certInfo" class="text-xs text-green-600 dark:text-green-400">
              <i class="fa-solid fa-check-circle mr-1"></i>{{ certInfo.subject }} — {{ certInfo.valido_hasta }}
            </span>
            <span v-else class="text-xs text-amber-500">
              <i class="fa-solid fa-circle-xmark mr-1"></i>No configurado
            </span>
            <i :class="['fa-solid fa-chevron-down text-xs transition-transform', afipExpanded ? 'rotate-180' : '']"></i>
          </div>
        </div>
      </button>

      <div v-if="afipExpanded" class="mt-4 space-y-4">
        <div class="space-y-4 max-w-lg">
          <BaseSelect
            v-model="config.afip_mode"
            label="Entorno"
            :options="[
              { value: 'testing', label: 'Testing (Homologación)' },
              { value: 'production', label: 'Producción' }
            ]"
            option-value="value"
            option-label="label"
          />

          <BaseSelect
            v-model="config.facturacion_provider"
            label="Proveedor"
            :options="[
              { value: 's360', label: 'Sistemas360 (recomendado - sin certs)' },
              { value: 'afip', label: 'AFIP directo (requiere cert de producción)' }
            ]"
            option-value="value"
            option-label="label"
          />

          <BaseInput v-model="config.afip_cuit" label="CUIT" placeholder="20123456789" maxlength="11" hint="11 dígitos sin guiones" />

          <BaseInput v-model="config.afip_pto_vta" label="Punto de Venta" placeholder="1" maxlength="4" hint="Número habilitado en AFIP" />

          <div class="flex items-center gap-3 pt-2">
            <BaseButton variant="primary" :loading="saving" @click="saveConfig(AFIP_BASIC_KEYS)">
              <i class="fa-solid fa-floppy-disk"></i> Guardar
            </BaseButton>
            <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
          </div>
        </div>

        <hr class="border-slate-200 dark:border-slate-700" />

        <div v-if="!csrGenerado">
          <p class="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Clave RSA y CSR</p>
          <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3 mb-3">
            <p class="text-xs text-amber-700 dark:text-amber-300">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>
              <strong>Importante:</strong> Al generar se descarga la clave privada automáticamente. Guardala en lugar seguro. Si la perdés, revocá el certificado en AFIP y generá uno nuevo.
            </p>
          </div>
          <div class="flex gap-3 flex-wrap">
            <BaseButton variant="secondary" :loading="generando" @click="generarCsr">
              <i class="fa-solid fa-wand-magic-sparkles"></i> Generar CSR
            </BaseButton>
            <label class="cursor-pointer inline-flex items-center gap-2 px-4 py-2 border border-slate-300 dark:border-slate-600 rounded text-sm text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <i class="fa-solid fa-upload"></i> Cargar CSR existente
              <input type="file" accept=".csr,.pem,.txt" class="hidden" @change="cargarCsrDesdeArchivo" />
            </label>
          </div>
        </div>

        <div v-if="csrGenerado">
          <div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded p-3 mb-3">
            <p class="text-xs text-red-700 dark:text-red-300">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>
              <strong>Antes de continuar, bajá la clave privada (.key)</strong> — sin ella no vas a poder facturar.
            </p>
          </div>
          <div class="flex gap-2 mb-4">
            <BaseButton variant="danger" @click="descargarKey">
              <i class="fa-solid fa-key"></i> Descargar .key
            </BaseButton>
          </div>

          <div class="flex items-start justify-between mb-2">
            <p class="text-xs font-semibold text-slate-700 dark:text-slate-300">CSR</p>
            <button class="text-[10px] text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 underline" @click="csrGenerado = false">
              Generar nuevo
            </button>
          </div>
          <p class="text-[11px] text-slate-500 dark:text-slate-400 mb-2">
            Subí este CSR a ARCA. Cuando te devuelvan el certificado .crt, cargalo abajo.
          </p>
          <div class="bg-slate-100 dark:bg-slate-800 rounded p-3 mb-3">
            <pre class="text-[10px] text-slate-600 dark:text-slate-300 whitespace-pre-wrap break-all font-mono">{{ displayCsr() }}</pre>
          </div>
          <div class="flex gap-2 mb-4">
            <BaseButton variant="secondary" @click="copiarCsr">
              <i class="fa-regular fa-copy"></i> Copiar
            </BaseButton>
            <BaseButton variant="secondary" @click="descargarCsr">
              <i class="fa-solid fa-download"></i> Descargar .csr
            </BaseButton>
          </div>

          <hr class="border-slate-200 dark:border-slate-700 mb-4" />

          <p class="text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">Certificado de ARCA</p>
          <div class="flex items-center gap-3 mb-3">
            <label class="cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <i class="fa-solid fa-upload"></i> Cargar .crt
              <input type="file" accept=".crt,.pem,.txt" class="hidden" @change="cargarCertDesdeArchivo" />
            </label>
            <label class="cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <i class="fa-solid fa-key"></i> Cargar .key
              <input type="file" accept=".key,.pem,.txt" class="hidden" @change="cargarKeyDesdeArchivo" />
            </label>
            <label class="cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <i class="fa-solid fa-file-code"></i> Cargar .pem
              <input type="file" accept=".pem,.txt" class="hidden" @change="cargarPemDesdeArchivo" />
            </label>
            <label class="cursor-pointer inline-flex items-center gap-2 px-3 py-1.5 border border-slate-300 dark:border-slate-600 rounded text-xs text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
              <i class="fa-solid fa-file-lines"></i> Cargar .csr
              <input type="file" accept=".csr,.pem,.txt" class="hidden" @change="cargarCsrDesdeArchivo" />
            </label>
          </div>
          <textarea
            v-model="certUpload"
            class="w-full border border-slate-300 dark:border-slate-600 rounded px-3 py-2 text-xs font-mono bg-white dark:bg-slate-800 text-slate-900 dark:text-slate-100 focus:outline-none focus:ring-2 focus:ring-brand-500"
            rows="5"
            placeholder="-----BEGIN CERTIFICATE-----&#10;...&#10;-----END CERTIFICATE-----"
          />
          <div class="mt-3">
            <BaseButton variant="primary" :loading="subiendo" @click="subirCertificado">
              <i class="fa-solid fa-floppy-disk"></i> Guardar Certificado
            </BaseButton>
          </div>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="facturacionExpanded = !facturacionExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-file-invoice text-brand-600"></i>
            Datos de Facturación
          </h3>
          <i :class="['fa-solid fa-chevron-down text-xs transition-transform', facturacionExpanded ? 'rotate-180' : '']"></i>
        </div>
      </button>

      <div v-if="facturacionExpanded" class="mt-4 space-y-4 max-w-lg">
        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3 mb-4">
          <p class="text-xs text-amber-700 dark:text-amber-300">
            <i class="fa-solid fa-triangle-exclamation mr-1"></i>
            <strong>Temporal:</strong> Estos datos se completarán automáticamente desde ARCA en el futuro.
          </p>
        </div>

        <BaseInput v-model="config.empresa_nombre" label="Razón Social" placeholder="Nombre de la empresa" />

        <BaseInput v-model="config.empresa_domicilio" label="Domicilio Comercial" placeholder="Dirección fiscal completa" />

        <BaseSelect
          v-model="config.empresa_condicion_iva"
          label="Condición frente al IVA"
          :options="[
            { value: 'responsable_inscripto', label: 'Responsable Inscripto' },
            { value: 'monotributista', label: 'Monotributista' },
            { value: 'exento', label: 'Exento' }
          ]"
          option-value="value"
          option-label="label"
        />

        <BaseInput v-model="config.empresa_ingresos_brutos" label="Ingresos Brutos" placeholder="1234567 o 'Exento'" />

        <BaseInput v-model="config.empresa_fecha_inicio" label="Fecha de Inicio de Actividades" type="date" />

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig(EMISOR_KEYS)">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="showGuide = !showGuide">
        <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <i class="fa-solid fa-circle-info text-sky-600"></i>
          Guía paso a paso para obtener certificado AFIP / ARCA
          <i :class="['fa-solid fa-chevron-down text-xs transition-transform', showGuide ? 'rotate-180' : '']"></i>
        </h3>
      </button>

      <div v-if="showGuide" class="mt-4 text-xs text-slate-600 dark:text-slate-400 space-y-4">
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 1: Generar CSR</p>
          <p>Expandí la sección <strong>"Factura Electrónica AFIP / ARCA"</strong> arriba, completá CUIT y Pto. Venta, guardá, y click en <strong>"Generar CSR"</strong>. Se descarga automáticamente la clave privada RSA — guardala muy bien.</p>
        </div>
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 2: Subir CSR a ARCA</p>
          <ul class="list-disc list-inside space-y-0.5">
            <li>Ingresá a <a href="https://auth.afip.gob.ar/contribuyente_/login.xhtml" target="_blank" class="text-brand-600 underline">auth.afip.gob.ar</a></li>
            <li>Ir a <strong>Administración de Certificados</strong> (WSASS)</li>
            <li>Crear un nuevo certificado</li>
            <li>Pegar el contenido del archivo <code class="bg-slate-200 dark:bg-slate-700 px-1 rounded">.csr</code> descargado</li>
            <li>Seleccionar servicio: <strong>WSFEV1</strong></li>
            <li>Confirmar y descargar el <code>.crt</code></li>
          </ul>
        </div>
        <div>
          <p class="font-semibold text-slate-700 dark:text-slate-300 mb-1">Paso 3: Volver al sistema</p>
          <p>En la misma sección expandida, cargá o pegá el <code>.crt</code> y guardá. El sistema queda listo para facturar.</p>
        </div>
        <div class="border-t border-slate-200 dark:border-slate-700 pt-2">
          <p class="text-[10px] text-slate-400"><i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i> Guardá la clave privada en un lugar seguro. Sin ella no se puede usar el certificado.</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="bancariosExpanded = !bancariosExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-building-columns text-brand-600"></i>
            Datos Bancarios para Transferencias
          </h3>
          <div class="flex items-center gap-3">
            <span v-if="config.banco_nombre" class="text-xs text-green-600 dark:text-green-400">
              <i class="fa-solid fa-check-circle mr-1"></i>{{ config.banco_nombre }}
            </span>
            <span v-else class="text-xs text-amber-500">
              <i class="fa-solid fa-circle-xmark mr-1"></i>No configurado
            </span>
            <i :class="['fa-solid fa-chevron-down text-xs transition-transform', bancariosExpanded ? 'rotate-180' : '']"></i>
          </div>
        </div>
      </button>

      <div v-if="bancariosExpanded" class="mt-4 space-y-4 max-w-lg">
        <BaseInput v-model="config.banco_nombre" label="Banco" placeholder="Banco Francés, Galicia, etc." />

        <BaseInput v-model="config.banco_titular" label="Titular" placeholder="Nombre completo del titular" />

        <BaseInput v-model="config.banco_alias" label="Alias" placeholder="alias.cbutransferencia" />

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig(BANCOS_KEYS)">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="carritosDefaultExpanded = !carritosDefaultExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-cash-register text-emerald-600"></i>
            Carritos del POS
          </h3>
          <div class="flex items-center gap-3">
            <span v-if="carritosDefault.length" class="text-xs text-slate-500 dark:text-slate-400">{{ carritosDefault.length }} carrito(s)</span>
            <span v-else class="text-xs text-amber-500">
              <i class="fa-solid fa-circle-xmark mr-1"></i>No configurado
            </span>
            <i :class="['fa-solid fa-chevron-down text-xs transition-transform', carritosDefaultExpanded ? 'rotate-180' : '']"></i>
          </div>
        </div>
      </button>

      <div v-if="carritosDefaultExpanded" class="mt-4 space-y-4 max-w-lg">
        <div class="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded p-3 mb-1">
          <p class="text-xs text-emerald-700 dark:text-emerald-300">
            <i class="fa-solid fa-circle-info mr-1"></i>
            Estos carritos quedan <strong>siempre abiertos</strong> en el POS: si alguien los borra o renombra, se vuelven a crear al recargar. Ejemplos: Mostrador, Mesa 1, Mesa 2...
          </p>
        </div>

        <div class="space-y-1.5">
          <div
            v-for="nombre in carritosDefault"
            :key="nombre"
            class="flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50 text-sm text-slate-700 dark:text-slate-200"
          >
            <i class="fa-solid fa-receipt text-emerald-500 text-xs"></i>
            <span class="flex-1 truncate">{{ nombre }}</span>
            <button
              type="button"
              class="shrink-0 w-6 h-6 rounded flex items-center justify-center text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 transition"
              title="Quitar de la lista"
              @click="quitarCarritoDefault(nombre)"
            >
              <i class="fa-solid fa-xmark text-[10px]"></i>
            </button>
          </div>
          <p v-if="!carritosDefault.length" class="text-xs text-slate-400 italic">Sin carritos por defecto. Agregá los que quieras siempre abiertos.</p>
        </div>

        <div class="flex gap-2">
          <input
            v-model="nombreCarritoDefault"
            type="text"
            maxlength="40"
            placeholder="Mostrador, Mesa 1..."
            class="flex-1 min-w-0 text-sm rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-900 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
            @keyup.enter="agregarCarritoDefault"
          />
          <BaseButton variant="secondary" :disabled="!nombreCarritoDefault.trim()" @click="agregarCarritoDefault">
            <i class="fa-solid fa-plus"></i> Agregar
          </BaseButton>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveCarritosDefault">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Se aplican al recargar el POS</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="mercadopagoExpanded = !mercadopagoExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-brands fa-cc-mastercard text-brand-600"></i>
            MercadoPago (QR y Smart Point)
          </h3>
          <div class="flex items-center gap-3">
            <span v-if="config.mercadopago_enabled === 'true' && config.mercadopago_access_token" class="text-xs text-green-600 dark:text-green-400">
              <i class="fa-solid fa-check-circle mr-1"></i>Configurado
            </span>
            <span v-else class="text-xs text-amber-500">
              <i class="fa-solid fa-circle-xmark mr-1"></i>No configurado
            </span>
            <i :class="['fa-solid fa-chevron-down text-xs transition-transform', mercadopagoExpanded ? 'rotate-180' : '']"></i>
          </div>
        </div>
      </button>

      <div v-if="mercadopagoExpanded" class="mt-4 space-y-4 max-w-lg">
        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-3 mb-4">
          <p class="text-xs text-blue-700 dark:text-blue-300">
            <i class="fa-solid fa-circle-info mr-1"></i>
            Configurá tu Access Token y luego usá los botones de abajo para crear automáticamente la sucursal, caja y QR fijo de MercadoPago.
          </p>
        </div>

        <BaseSelect
          v-model="config.mercadopago_enabled"
          label="Habilitar MercadoPago"
          :options="[
            { value: 'false', label: 'Deshabilitado' },
            { value: 'true', label: 'Habilitado' }
          ]"
          option-value="value"
          option-label="label"
        />

        <BaseSelect
          v-model="config.mercadopago_mode"
          label="Entorno"
          :options="[
            { value: 'sandbox', label: 'Sandbox (Pruebas)' },
            { value: 'prod', label: 'Producción' }
          ]"
          option-value="value"
          option-label="label"
        />

        <BaseInput v-model="config.mercadopago_access_token" label="Access Token" type="password" placeholder="APP_USR-..." hint="Lo encontrás en: MercadoPago Dev → Tus integraciones → Credenciales" />

        <hr class="border-slate-200 dark:border-slate-700" />

        <div class="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded p-3">
          <p class="text-xs text-emerald-700 dark:text-emerald-300">
            <i class="fa-solid fa-wand-magic-sparkles mr-1"></i>
            <strong>Crear sucursal y caja automáticamente</strong> — Completá los datos abajo y hacemos todo desde acá.
          </p>
        </div>

        <details class="border border-slate-200 dark:border-slate-700 rounded-lg">
          <summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800">
            <i class="fa-solid fa-store mr-2"></i>Crear Sucursal
          </summary>
          <div class="p-4 space-y-3 border-t border-slate-200 dark:border-slate-700">
            <BaseInput v-model="storeForm.nombre" label="Nombre de la sucursal" placeholder="Ej: Mi Tienda Central" />
            <BaseInput v-model="storeForm.external_id" label="ID Externo" placeholder="Ej: SUC001" hint="Identificador único para tu sistema" />
            <BaseInput v-model="storeForm.street_name" label="Calle" placeholder="Nombre de la calle" />
            <div class="grid grid-cols-2 gap-3">
              <BaseInput v-model="storeForm.street_number" label="Número" placeholder="123" />
              <BaseInput v-model="storeForm.city_name" label="Ciudad" placeholder="Ciudad" />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <BaseSelect
                v-model="storeForm.state_name"
                label="Provincia"
                :options="[
                  { value: 'Buenos Aires', label: 'Buenos Aires' },
                  { value: 'Capital Federal', label: 'Capital Federal' },
                  { value: 'Catamarca', label: 'Catamarca' },
                  { value: 'Chaco', label: 'Chaco' },
                  { value: 'Chubut', label: 'Chubut' },
                  { value: 'Corrientes', label: 'Corrientes' },
                  { value: 'Córdoba', label: 'Córdoba' },
                  { value: 'Entre Ríos', label: 'Entre Ríos' },
                  { value: 'Formosa', label: 'Formosa' },
                  { value: 'Jujuy', label: 'Jujuy' },
                  { value: 'La Pampa', label: 'La Pampa' },
                  { value: 'La Rioja', label: 'La Rioja' },
                  { value: 'Mendoza', label: 'Mendoza' },
                  { value: 'Misiones', label: 'Misiones' },
                  { value: 'Neuquén', label: 'Neuquén' },
                  { value: 'Río Negro', label: 'Río Negro' },
                  { value: 'Salta', label: 'Salta' },
                  { value: 'San Juan', label: 'San Juan' },
                  { value: 'San Luis', label: 'San Luis' },
                  { value: 'Santa Cruz', label: 'Santa Cruz' },
                  { value: 'Santa Fe', label: 'Santa Fe' },
                  { value: 'Santiago del Estero', label: 'Santiago del Estero' },
                  { value: 'Tierra del Fuego', label: 'Tierra del Fuego' },
                  { value: 'Tucumán', label: 'Tucumán' }
                ]"
                option-value="value"
                option-label="label"
              />
              <BaseInput v-model="storeForm.reference" label="Referencia" placeholder="Cerca de..." />
            </div>
            <BaseButton variant="primary" :loading="creandoStore" :disabled="storeCreado" @click="crearSucursalMp">
              <i class="fa-solid fa-plus mr-1"></i> {{ storeCreado ? 'Sucursal Creada' : 'Crear Sucursal' }}
            </BaseButton>
            <div v-if="storeCreado" class="text-xs text-emerald-600 dark:text-emerald-400">
              <i class="fa-solid fa-check-circle mr-1"></i>Sucursal ID: {{ mpStoreId }}
            </div>
          </div>
        </details>

        <details class="border border-slate-200 dark:border-slate-700 rounded-lg" :class="{ 'opacity-50': !storeCreado }">
          <summary class="cursor-pointer px-4 py-3 text-sm font-semibold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800" :class="{ 'pointer-events-none': !storeCreado }">
            <i class="fa-solid fa-desktop mr-2"></i>Crear Caja (POS)
          </summary>
          <div class="p-4 space-y-3 border-t border-slate-200 dark:border-slate-700">
            <BaseInput v-model="cajaForm.nombre" label="Nombre de la caja" placeholder="Ej: Caja Principal" />
            <BaseInput v-model="cajaForm.external_id" label="ID Externo" placeholder="Ej: CAJA001" hint="Identificador único para tu sistema" />
            <div class="bg-slate-100 dark:bg-slate-800 rounded p-2 text-xs text-slate-600 dark:text-slate-400">
              <i class="fa-solid fa-info-circle mr-1"></i>
              La caja se asociará a la sucursal: <strong>{{ storeForm.nombre || 'Sin nombre' }}</strong> (ID: {{ mpStoreId || 'Sin crear' }})
            </div>
            <BaseButton variant="primary" :loading="creandoCaja" :disabled="cajaCreada || !storeCreado" @click="crearCajaMp">
              <i class="fa-solid fa-plus mr-1"></i> {{ cajaCreada ? 'Caja Creada' : 'Crear Caja' }}
            </BaseButton>
            <div v-if="cajaCreada" class="space-y-2">
              <div class="text-xs text-emerald-600 dark:text-emerald-400">
                <i class="fa-solid fa-check-circle mr-1"></i>Caja POS ID: {{ mpCajaId }}
              </div>
              <div v-if="qrFijoUrl" class="bg-white dark:bg-slate-900 rounded p-2 inline-block">
                <p class="text-[10px] text-slate-500 mb-1">QR Fijo:</p>
                <img :src="qrFijoUrl" alt="QR Fijo" class="w-24 h-24" />
              </div>
            </div>
          </div>
        </details>

        <hr class="border-slate-200 dark:border-slate-700" />

        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-3 mb-3">
          <p class="text-xs text-blue-700 dark:text-blue-300">
            <i class="fa-solid fa-info-circle mr-1"></i>
            <strong>Creado desde MercadoPago:</strong> Completá estos datos si ya tenés la caja creada en el portal de MercadoPago.
          </p>
        </div>

        <BaseInput v-model="config.mercadopago_user_id" label="User ID" placeholder="Ej: 3517052704" hint="Tu ID de usuario en MercadoPago (9 dígitos)" />

        <BaseInput v-model="config.mercadopago_external_pos_id" label="External POS ID" placeholder="Ej: CAJA001" hint="El external_id que asignaste a la caja en MercadoPago" />

        <BaseInput v-model="config.mercadopago_pos_id_qr" label="POS ID (QR)" placeholder="Completá manualmente o crealo desde aquí" hint="ID numérico del POS para QR en MercadoPago" />

        <BaseSelect
          v-model="config.mercadopago_qr_fijo_modo"
          label="Modo QR"
          :options="[
            { value: 'dinamico', label: 'Dinámico (QR en pantalla)' },
            { value: 'hibrido', label: 'Híbrido (QR fijo + dinámico)' }
          ]"
          option-value="value"
          option-label="label"
        />

        <div v-if="config.mercadopago_qr_fijo_modo === 'hibrido'" class="space-y-3">
          <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3">
            <p class="text-xs text-amber-700 dark:text-amber-300">
              <i class="fa-solid fa-triangle-exclamation mr-1"></i>
              <strong>Modo Híbrido:</strong> El QR fijo se obtiene al crear la caja (arriba). Imprimilo y pegalo en el mostrador. El QR dinámico se muestra en pantalla al cobrar.
            </p>
          </div>
          <div v-if="qrFijoUrl" class="bg-white dark:bg-slate-900 rounded p-3 inline-block">
            <p class="text-[10px] text-slate-500 mb-2">QR Fijo (descargado de MercadoPago):</p>
            <img :src="qrFijoUrl" alt="QR Fijo" class="w-32 h-32" />
          </div>
          <BaseInput v-model="config.mercadopago_qr_fijo_url" label="QR Fijo (URL)" type="textarea" placeholder="Se completa automáticamente o pegá otra URL" hint="URL de la imagen del QR fijo" />
        </div>

        <BaseInput v-model="config.mercadopago_pos_id_smart" label="POS ID (Smart Point)" placeholder="Para cobrar con dispositivo físico" hint="ID del Smart Point en MercadoPago" />

        <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg p-3">
          <p class="text-xs font-semibold text-slate-600 dark:text-slate-300 mb-2">
            <i class="fa-solid fa-shield-halved mr-1"></i>Seguridad Webhook
          </p>
          <div class="flex items-center gap-2">
            <BaseInput
              v-model="config.mercadopago_webhook_secret"
              label="Webhook Secret"
              type="password"
              placeholder="Clave secreta de MP para validar webhooks"
              hint="Opcional. Encontrás esta clave en el portal de MP Developer > Webhooks"
              class="flex-1"
            />
            <button
              v-if="config.mercadopago_webhook_secret"
              type="button"
              class="mt-6 px-3 py-2 text-red-500 hover:text-red-700 dark:hover:text-red-400 transition-colors"
              title="Borrar clave"
              @click="config.mercadopago_webhook_secret = ''"
            >
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </div>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig(MP_KEYS)">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="qrInteropExpanded = !qrInteropExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-qrcode text-brand-600"></i>
            QR Interoperable (todas las billeteras)
          </h3>
          <div class="flex items-center gap-3">
            <span v-if="config.qr_interop_cuit && config.qr_interop_cuenta" class="text-xs text-green-600 dark:text-green-400">
              <i class="fa-solid fa-check-circle mr-1"></i>Configurado
            </span>
            <span v-else class="text-xs text-amber-500">
              <i class="fa-solid fa-circle-xmark mr-1"></i>No configurado
            </span>
            <i :class="['fa-solid fa-chevron-down text-xs transition-transform', qrInteropExpanded ? 'rotate-180' : '']"></i>
          </div>
        </div>
      </button>

      <div v-if="qrInteropExpanded" class="mt-4 space-y-4 max-w-lg">
        <div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded p-3">
          <p class="text-xs text-blue-700 dark:text-blue-300">
            <i class="fa-solid fa-circle-info mr-1"></i>
            Este QR sigue el estándar EMVCo QRCPS v1.0 (BCRA Com. "A" 6425).
            Cualquier billetera interoperable (Brubank, Personal Pay, MODO, MercadoPago, etc.)
            puede pagarlo: el importe llega por transferencia inmediata a la CBU/CVU que cargués.
            La venta se cierra cuando confirmás manualmente el pago.
          </p>
        </div>

        <BaseInput v-model="config.qr_interop_cuit" label="CUIT/CUIL del comercio *" placeholder="Ej: 20111222333" hint="Debe tener 11 dígitos" />

        <BaseInput v-model="config.qr_interop_cuenta" label="CBU, CVU o alias *" placeholder="Ej: 0000073100000000001234 o maxi@casillas" hint="Cuenta a la que llega el pago. No importa el banco: si la billetera del cliente no es interoperable, no podrá pagarlo." />

        <BaseInput v-model="config.qr_interop_nombre" label="Nombre del comercio *" placeholder="Ej: MI NEGOCIO" hint="Se muestra en el QR. Sin acentos, máx. 25 caracteres" />

        <BaseInput v-model="config.qr_interop_ciudad" label="Ciudad (opcional)" placeholder="Ej: MAR DEL PLATA" hint="Máx. 15 caracteres" />

        <BaseInput v-model="config.qr_interop_mcc" label="MCC (código de categoría) (opcional)" placeholder="Ej: 9700" hint="4 dígitos. Default 9700: comercio sin categoría específica" />

        <div class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded p-3">
          <p class="text-xs text-amber-700 dark:text-amber-300">
            <i class="fa-solid fa-triangle-exclamation mr-1"></i>
            Probá el primer pago con un monto bajo. El QR cobra a través de transferencia
            (sin señalar automáticamente la venta en el sistema: confirmás a mano al ver el ingreso).
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig(QR_INTEROP_KEYS)">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="ventasExpanded = !ventasExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-receipt text-brand-600"></i>
            Factura Electrónica Automática por Medio de Pago
          </h3>
          <i :class="['fa-solid fa-chevron-down text-xs transition-transform', ventasExpanded ? 'rotate-180' : '']"></i>
        </div>
      </button>

      <div v-if="ventasExpanded" class="mt-4 space-y-4 max-w-lg">
        <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
          <p class="text-xs text-slate-600 dark:text-slate-400 mb-4">
            Activá o desactivá la emisión automática de facturas electrónicas para cada medio de pago.
            Cuando está <strong>OFF</strong>, la factura se emite manualmente desde el ticket.
          </p>

          <div class="space-y-4">
            <BaseToggle
              v-model="facturaAuto.efectivo"
              label="Efectivo"
              description="Factura automática al cobrar en efectivo"
              size="sm"
            />
            <BaseToggle
              v-model="facturaAuto.debito"
              label="Débito"
              description="Factura automática al cobrar con tarjeta de débito"
              size="sm"
            />
            <BaseToggle
              v-model="facturaAuto.credito"
              label="Crédito"
              description="Factura automática al cobrar con tarjeta de crédito"
              size="sm"
            />
            <BaseToggle
              v-model="facturaAuto.transferencia"
              label="Transferencia"
              description="Factura automática al cobrar por transferencia bancaria"
              size="sm"
            />
            <BaseToggle
              v-model="facturaAuto.cta_corriente"
              label="Cuenta Corriente"
              description="Factura automática al cobrar a cuenta corriente"
              size="sm"
            />
            <BaseToggle
              v-model="facturaAuto.mercadopago_qr"
              label="MercadoPago QR"
              description="Factura automática al cobrar con QR de MercadoPago"
              size="sm"
            />
            <BaseToggle
              v-model="facturaAuto.mercadopago_pos"
              label="MercadoPago POS"
              description="Factura automática al cobrar con Smart Point de MercadoPago"
              size="sm"
            />
          </div>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="saving" @click="saveConfig(VENTAS_KEYS)">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="recargasExpanded = !recargasExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-mobile-screen-button text-brand-600"></i>
            Servicio de Recargas
          </h3>
          <i :class="['fa-solid fa-chevron-down text-xs transition-transform', recargasExpanded ? 'rotate-180' : '']"></i>
        </div>
      </button>

      <div v-if="recargasExpanded" class="mt-4 space-y-4">
        <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
          <p class="text-xs text-slate-600 dark:text-slate-400">
            Configurá las recargas de saldo (SUBE, etc.): cuánto se carga por unidad, el adicional que cobra el
            negocio y <strong>de qué cuenta sale el dinero</strong>. Al confirmar la venta, el monto cargado se
            registra como <strong>egreso real de caja</strong> de esa cuenta y el adicional queda como ganancia.
          </p>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 max-w-lg">
          <div>
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">
              Monto base por unidad
            </label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400">$</span>
              <input
                v-model.number="recargas.monto_base"
                type="number"
                min="1"
                step="100"
                class="w-full pl-7 pr-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none"
              >
            </div>
            <p class="text-[10px] text-slate-400 mt-1">Solo se admiten múltiplos de este monto.</p>
          </div>

          <div>
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">
              Adicional (%)
            </label>
            <div class="relative">
              <input
                v-model.number="recargas.adicional_pct"
                type="number"
                min="0"
                max="100"
                step="1"
                class="w-full pr-8 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none"
              >
              <span class="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">%</span>
            </div>
            <p class="text-[10px] text-slate-400 mt-1">
              El cliente paga {{ fc(recargaPrecioUnitario) }} por unidad.
            </p>
          </div>
        </div>

        <div class="max-w-lg">
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">
            Cuenta de salida (de dónde sale el dinero para cargar)
          </label>
          <select
            v-model="recargas.medio_pago_carga"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none"
          >
            <option v-for="m in mediosCarga" :key="m.value" :value="m.value">{{ m.label }}</option>
          </select>
          <p class="text-[10px] text-slate-400 mt-1">
            Se registra un egreso de caja por el monto cargado con este medio de pago.
          </p>
        </div>

        <div class="max-w-lg">
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">
            Producto que representa la recarga
          </label>
          <select
            v-model.number="recargas.producto_id"
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none"
          >
            <option :value="null">— Sin configurar —</option>
            <option v-for="p in productosSinStock" :key="p.id" :value="p.id">
              {{ p.nombre }} ({{ fc(p.precio_venta) }})
            </option>
          </select>
          <p class="text-[10px] text-slate-400 mt-1">
            Solo productos sin control de stock. Al elegirlo queda marcado como servicio de recarga.
          </p>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="savingRecargas" @click="saveRecargas">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Los cambios se aplican inmediatamente en el POS</p>
        </div>
      </div>
    </BaseCard>

    <BaseCard v-if="!loading">
      <button class="w-full text-left" @click="denominacionesExpanded = !denominacionesExpanded">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-money-bill-wave text-brand-600"></i>
            Denominaciones de Efectivo
          </h3>
          <i :class="['fa-solid fa-chevron-down text-xs transition-transform', denominacionesExpanded ? 'rotate-180' : '']"></i>
        </div>
      </button>

      <div v-if="denominacionesExpanded" class="mt-4 space-y-4">
        <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-lg p-4">
          <p class="text-xs text-slate-600 dark:text-slate-400">
            Definí las denominaciones que aparecen en el <strong>contador de efectivo</strong> de caja
            (apertura, cierre por método y arqueo). Podés cambiar el valor, el tipo,
            habilitar o deshabilitar, y agregar nuevas.
          </p>
        </div>

        <div v-if="cargandoDenoms" class="flex items-center gap-2 text-xs text-slate-500 py-2">
          <i class="fa-solid fa-spinner fa-spin"></i> Cargando denominaciones...
        </div>

        <div v-else class="space-y-2">
          <div class="hidden sm:grid grid-cols-[1fr_120px_1fr_36px] gap-3 px-3">
            <span class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Valor</span>
            <span class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Tipo</span>
            <span class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Estado</span>
            <span></span>
          </div>

          <div
            v-for="(d, i) in denominaciones"
            :key="d.id ?? 'nuevo' + i"
            class="grid grid-cols-1 sm:grid-cols-[1fr_120px_1fr_36px] gap-3 items-center border border-slate-200 dark:border-slate-700 rounded-lg p-3 bg-white dark:bg-slate-900"
            :class="{ 'opacity-50': !d.activo }"
          >
            <div class="flex items-center gap-2">
              <input
                v-model.number="d.valor"
                type="number"
                min="0"
                step="1"
                inputmode="numeric"
                placeholder="0"
                class="w-[120px] shrink-0 px-2.5 py-1.5 text-sm text-right font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              />
              <span class="text-[11px] text-slate-400 font-mono-data">{{ formatearDenominacion(d.valor) }}</span>
            </div>

            <BaseSelect
              :model-value="d.tipo"
              :options="TIPOS_DENOM"
              :placeholder="''"
              size="sm"
              @update:model-value="cambiarTipoDenominacion(d, $event)"
            />

            <BaseToggle v-model="d.activo" :label="d.activo ? 'Habilitada' : 'Deshabilitada'" size="sm" />

            <BaseButton
              variant="ghost"
              size="xs"
              icon-only
              aria-label="Quitar denominación"
              @click="quitarDenominacion(d)"
            >
              <i class="fa-solid fa-trash text-red-500"></i>
            </BaseButton>
          </div>

          <p v-if="denominaciones.length === 0" class="text-xs text-slate-500 py-2">
            No hay denominaciones cargadas. Agregá al menos una.
          </p>
        </div>

        <div class="flex items-center gap-3">
          <BaseButton variant="secondary" size="sm" :disabled="cargandoDenoms" @click="agregarDenominacion">
            <i class="fa-solid fa-plus"></i> Agregar denominación
          </BaseButton>
          <BaseButton variant="ghost" size="sm" :loading="guardandoDenoms" @click="restaurarDefaultsDenominaciones">
            <i class="fa-solid fa-rotate-left"></i> Restaurar por defecto
          </BaseButton>
        </div>

        <div class="flex items-center gap-3 pt-2">
          <BaseButton variant="primary" :loading="guardandoDenoms" :disabled="cargandoDenoms" @click="guardarDenominaciones">
            <i class="fa-solid fa-floppy-disk"></i> Guardar
          </BaseButton>
          <p class="text-[11px] text-slate-400">Las denominaciones deshabilitadas no aparecen en el contador</p>
        </div>
      </div>
    </BaseCard>
  </div>
</template>
