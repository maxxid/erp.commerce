import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const STORAGE_KEY = 'apex-pos-carritos'
const LEGACY_KEY = 'apex-pos-held'
const AUDIT_KEY = 'apex-pos-held-audit'
const STALE_MS = 2 * 60 * 60 * 1000
const MAX_CARTS = 12

function nuevoId() {
  return `c${Date.now().toString(36)}${Math.random().toString(36).slice(2, 7)}`
}

function carritoVacio(nombre) {
  const ahora = new Date().toISOString()
  return {
    id: nuevoId(),
    nombre,
    creado: ahora,
    actualizado: ahora,
    items: [],
    subtotal: 0,
    total: 0,
    descuento: 0,
    recibido: '',
    efectivo_pagado: '',
    medio_pago: 'efectivo',
    cliente_id: '',
    comprador_cuit: '',
  }
}

// localStorage es del usuario: puede traer carritos viejos, incompletos o
// editados a mano. Normalizar evita que un dato raro rompa el POS.
function normalizar(c, i) {
  const base = carritoVacio(c?.nombre || `Carrito ${i + 1}`)
  const out = { ...base, ...(c || {}) }
  out.id = c?.id || base.id
  out.nombre = String(out.nombre || base.nombre).slice(0, 40)
  out.items = Array.isArray(out.items) ? out.items : []
  out.subtotal = Number(out.subtotal) || 0
  out.total = Number(out.total) || 0
  out.descuento = Number(out.descuento) || 0
  return out
}

// Los tickets apartados de la version anterior ya eran carritos guardados con
// nombre implicito. Se importan una sola vez para que quien los use no pierda
// nada al actualizar.
function migrarLegacy() {
  try {
    const viejos = JSON.parse(localStorage.getItem(LEGACY_KEY) || '[]')
    if (!Array.isArray(viejos)) return null
    const carritos = viejos
      .filter(t => t && Array.isArray(t.items) && t.items.length)
      .map((t, i) => {
        const base = carritoVacio(`Apartado ${i + 1}`)
        return {
          ...base,
          ...t,
          id: nuevoId(),
          nombre: `Apartado ${i + 1}`,
          creado: t.createdAt || base.creado,
          actualizado: t.createdAt || base.creado,
        }
      })
    if (!carritos.length) return null
    return { carritos, activoId: carritos[0].id }
  } catch {
    return null
  }
}

function cargar() {
  try {
    const raw = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null')
    if (raw && Array.isArray(raw.carritos) && raw.carritos.length) {
      const carritos = raw.carritos.slice(0, MAX_CARTS).map(normalizar)
      const activoId = carritos.some(c => c.id === raw.activoId) ? raw.activoId : carritos[0].id
      return { carritos, activoId, sesionId: raw.sesionId || '' }
    }
  } catch {
    // dato corrupto: se descarta y se arranca de cero
  }
  const legacy = migrarLegacy()
  if (legacy) return { ...legacy, sesionId: '' }
  const primero = carritoVacio('Carrito 1')
  return { carritos: [primero], activoId: primero.id, sesionId: '' }
}

function auditar(evento, detalle) {
  try {
    const log = JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]')
    let usuario = 'desconocido'
    try { usuario = JSON.parse(localStorage.getItem('apex_user') || '{}').nombre || 'desconocido' }
    catch { /* sin usuario en localStorage */ }
    log.push({ ts: new Date().toISOString(), evento, detalle, usuario })
    if (log.length > 200) log.splice(0, log.length - 200)
    localStorage.setItem(AUDIT_KEY, JSON.stringify(log))
  } catch {
    // la auditoria nunca debe romper una venta
  }
}

export const useCarritoStore = defineStore('carrito', () => {
  const inicial = cargar()
  const carritos = ref(inicial.carritos)
  const activoId = ref(inicial.activoId)
  const sesionId = ref(inicial.sesionId)

  const activo = computed(() => carritos.value.find(c => c.id === activoId.value) || carritos.value[0])

  const cantidadCarritos = computed(() => carritos.value.length)
  const carritosConItems = computed(() => carritos.value.filter(c => c.items.length > 0))
  const totalItems = computed(() => carritos.value.reduce((s, c) => s + c.items.reduce((n, i) => n + (Number(i.cantidad) || 0), 0), 0))

  // Igual que antes: un carrito abierto hace mas de 2 horas es sospechoso.
  const sospechosos = computed(() =>
    carritos.value.filter(c => {
      if (!c.items.length || !c.creado) return false
      return Date.now() - new Date(c.creado).getTime() > STALE_MS
    })
  )

  function siguienteNombre() {
    const usados = new Set(carritos.value.map(c => c.nombre))
    let n = carritos.value.length + 1
    while (usados.has(`Carrito ${n}`)) n++
    return `Carrito ${n}`
  }

  // Los carritos default se eligen en Ajustes ("Mostrador", "Mesa 1", ...) y
  // son la lista que el local quiere siempre abierta. Se respetan por nombre:
  // si un default falta (porque se borro o renombro), se vuelve a crear en el
  // proximo load. Un renombre manual, entonces, dura solo hasta que se recarga
  // el POS desde la config.
  function asegurarDefaults(nombres) {
    if (!Array.isArray(nombres)) return 0
    let creados = 0
    for (const crudo of nombres) {
      const nombre = String(crudo || '').trim().slice(0, 40)
      if (!nombre || carritos.value.some(c => c.nombre === nombre)) continue
      if (carritos.value.length >= MAX_CARTS) break
      const nuevo = carritoVacio(nombre)
      carritos.value.push(nuevo)
      auditar('HOLD', { carritoId: nuevo.id, nombre: nuevo.nombre, items: 0, total: 0, origen: 'default' })
      creados++
    }
    return creados
  }

  function guardar() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify({
        carritos: carritos.value,
        activoId: activoId.value,
        sesionId: sesionId.value,
      }))
    } catch {
      // cuota llena o storage bloqueado: el carrito sigue en memoria
    }
  }

  // La vida de un carrito se cuenta dentro de la sesion de caja. Un carrito que
  // quedo abierto de ayer seguia marcando sus 38 horas hoy, despues de abrir
  // caja: engaaba y lo marcaba como sospechoso al instante. Cuando arranca una
  // sesion nueva, los carritos que ya estaban abiertos arrancan su reloj con
  // ella; los creados en esta sesion no se tocan.
  function sincronizarSesion(id, inicio) {
    if (!id || id === sesionId.value) return 0
    const arranque = inicio ? new Date(inicio) : new Date()
    const desde = isNaN(arranque.getTime()) || arranque > new Date() ? new Date().toISOString() : arranque.toISOString()
    let reiniciados = 0
    for (const c of carritos.value) {
      const creado = new Date(c.creado || '')
      if (!c.creado || isNaN(creado.getTime()) || creado < arranque) {
        c.creado = desde
        const actualizado = new Date(c.actualizado || '')
        if (!c.actualizado || isNaN(actualizado.getTime()) || actualizado < arranque) {
          c.actualizado = desde
        }
        reiniciados++
      }
    }
    sesionId.value = id
    guardar()
    if (reiniciados) {
      auditar('SESSION', { sesionId: id, carritosReiniciados: reiniciados, desde })
    }
    return reiniciados
  }

  function crear(nombre) {
    if (carritos.value.length >= MAX_CARTS) return null
    const limpio = String(nombre || '').trim().slice(0, 40)
    const nuevo = carritoVacio(limpio || siguienteNombre())
    carritos.value.push(nuevo)
    activar(nuevo.id, true)
    auditar('HOLD', { carritoId: nuevo.id, nombre: nuevo.nombre, items: 0, total: 0 })
    return nuevo
  }

  function activar(id, silencioso = false) {
    if (!carritos.value.some(c => c.id === id)) return false
    if (id === activoId.value) return true
    const destino = carritos.value.find(c => c.id === id)
    const previo = activo.value
    activoId.value = id
    if (!silencioso && destino) {
      auditar('RECALL', {
        carritoId: id,
        nombre: destino.nombre,
        items: destino.items.length,
        total: destino.total,
        desde: previo ? previo.nombre : null,
      })
    }
    return true
  }

  function renombrar(id, nombre) {
    const c = carritos.value.find(x => x.id === id)
    const limpio = String(nombre || '').trim().slice(0, 40)
    if (!c || !limpio || c.nombre === limpio) return false
    c.nombre = limpio
    auditar('RENAME', { carritoId: id, nombre: limpio })
    return true
  }

  function eliminar(id) {
    const idx = carritos.value.findIndex(c => c.id === id)
    if (idx === -1) return false
    // El ultimo carrito no se elimina: el POS siempre necesita uno activo.
    if (carritos.value.length === 1) return false
    const [borrado] = carritos.value.splice(idx, 1)
    if (activoId.value === id) {
      activoId.value = carritos.value[Math.min(idx, carritos.value.length - 1)].id
    }
    auditar('DELETE_HELD', { carritoId: id, nombre: borrado.nombre, items: borrado.items.length, total: borrado.total })
    return true
  }

  // Cierra el carrito: se vacian los items pero el nombre sobrevive, que es
  // justo lo que se quiere para una mesa que sigue abierta.
  function cerrar(id) {
    const c = carritos.value.find(x => x.id === (id || activoId.value))
    if (!c) return false
    auditar('CLOSE', { carritoId: c.id, nombre: c.nombre, items: c.items.length, total: c.total })
    c.items = []
    c.subtotal = 0
    c.total = 0
    c.descuento = 0
    c.recibido = ''
    c.efectivo_pagado = ''
    c.cliente_id = ''
    c.actualizado = new Date().toISOString()
    return true
  }

  function tocar() {
    if (activo.value) activo.value.actualizado = new Date().toISOString()
  }

  function antiguedad(iso) {
    if (!iso) return 'ahora'
    const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
    if (mins < 1) return 'ahora'
    if (mins < 60) return `hace ${mins}min`
    const hrs = Math.floor(mins / 60)
    return `hace ${hrs}h${mins % 60 > 0 ? ` ${mins % 60}m` : ''}`
  }

  watch([carritos, activoId], guardar, { deep: true })

  return {
    carritos,
    activoId,
    sesionId,
    activo,
    cantidadCarritos,
    carritosConItems,
    totalItems,
    sospechosos,
    crear,
    activar,
    renombrar,
    eliminar,
    cerrar,
    asegurarDefaults,
    sincronizarSesion,
    tocar,
    antiguedad,
    auditar,
  }
})
