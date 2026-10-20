import { ref } from 'vue'
import api, { esErrorDeRed } from '@/services/api'
import { useCajaStore } from '@/stores/caja'

// Apertura y cierre hechos sin conexión, para subirlos cuando vuelva la red.
//
// Solo se encolan estas tres operaciones porque son las que se pueden
// **reconciliar contra el estado real**: antes de reintentar se le pregunta al
// servidor en qué está la caja, y si la operación ya estaba hecha no se vuelve
// a hacer. Así nunca queda una apertura ni un cierre contados dos veces.
//
// Los movimientos sueltos (ingreso, egreso, extracción, pago a proveedor) no se
// encolan: no hay forma de saber si ya se registraron, y duplicar plata es peor
// que mostrar el error. Esos siguen avisando en rojo como hasta ahora.
const CLAVE = 'apex-offline-caja'
const OPERACIONES = ['/api/caja/apertura', '/api/caja/cierre-metodo', '/api/caja/cierre-total']

const cola = ref([])
let cargada = false

function nuevoId() {
  return (typeof crypto !== 'undefined' && crypto.randomUUID)
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`
}

function notificar() {
  if (typeof window !== 'undefined') window.dispatchEvent(new Event('apex-pending-caja-updated'))
}

export function useOfflineCaja() {
  function cargarCola() {
    try {
      const guardada = localStorage.getItem(CLAVE)
      cola.value = guardada ? JSON.parse(guardada) : []
    } catch {
      cola.value = []
    }
    cargada = true
  }

  function guardarCola() {
    try { localStorage.setItem(CLAVE, JSON.stringify(cola.value)) } catch { /* storage lleno */ }
  }

  function pendientes() {
    if (!cargada) cargarCola()
    return cola.value.filter((op) => !op.subida)
  }

  // Mismo criterio en los dos caminos (con red y sin ella): la pantalla tiene
  // que quedar como quedó la caja en el negocio. Antes esto solo pasaba al
  // encolar, así que con red la apertura quedaba guardada en el navegador
  // recién cuando salía el pedido siguiente (`fetchEstado`): si ese no salía,
  // la pantalla seguía viendo la caja abierta y **al refrescar aparecía
  // "CAJA CERRADA" con la caja abierta en el negocio** (Prueba 2, 20/10).
  function aplicarLocal(endpoint, data) {
    const caja = useCajaStore()
    if (endpoint === '/api/caja/apertura') caja.aplicarAperturaLocal(data)
    if (endpoint === '/api/caja/cierre-total') caja.aplicarCierreLocal()
  }

  function encolar(endpoint, data, etiqueta) {
    cola.value.push({
      id: nuevoId(),
      createdAt: new Date().toISOString(),
      endpoint,
      data,
      etiqueta: etiqueta || endpoint,
      subida: false,
    })
    guardarCola()
    // El negocio siguió andando: mientras no conteste el servidor, el navegador
    // tiene que mostrar la caja como quedó (abierta al abrir, cerrada al cerrar).
    aplicarLocal(endpoint, data)
    notificar()
  }

  /**
   * El único camino para escribir en la caja: si la red no contesta, la
   * operación queda anotada y se avisa que quedó sin subir. Si la rechaza el
   * servidor (400, 403), el error se propaga: eso no es "sin conexión", es un
   * problema que alguien tiene que ver.
   */
  async function postear(endpoint, data, etiqueta) {
    if (!OPERACIONES.includes(endpoint)) {
      throw new Error(`Operación de caja no encolable: ${endpoint}`)
    }
    try {
      const resp = await api.post(endpoint, data)
      // El servidor ya lo registró: se deja anotado en el navegador acá mismo,
      // sin depender del pedido que sigue (`fetchEstado`).
      aplicarLocal(endpoint, data)
      return { resp, encolada: false }
    } catch (e) {
      if (!esErrorDeRed(e)) throw e
      encolar(endpoint, data, etiqueta)
      return { resp: null, encolada: true }
    }
  }

  // No avisa: quien sincroniza avisa una sola vez al terminar.
  function marcarSubida(id) {
    const op = cola.value.find((o) => o.id === id)
    if (op) op.subida = true
    cola.value = cola.value.filter((o) => !o.subida)
    guardarCola()
  }

  /** El estado real de la caja con el que se decide qué aplicar dos veces. */
  async function traerEstado() {
    return api.get('/api/caja/estado')
  }

  /**
   * Sube una operación teniendo en cuenta el estado que lleva la réplica.
   *
   * `estado` se arranca con lo que dijo el servidor y va evolucionando con cada
   * operación que se aplica: si se mirara siempre el estado inicial, una cola
   * con apertura y cierre saltaría el cierre ("la caja ya está cerrada") y la
   * jornada quedaría abierta para siempre en el servidor.
   *
   * - `true` → ya estaba hecha o recién se hizo: se saca de la cola.
   * - `false` → el servidor la rechazó: se queda encolada para mirarla.
   * - lanza si se cortó la red: lo que sigue no puede subir igual.
   */
  async function subirOperacion(op, estado) {
    const data = op.data || {}
    const yaHecha = (
      (op.endpoint === '/api/caja/apertura' && estado.abierta) ||
      (op.endpoint === '/api/caja/cierre-total' && !estado.abierta) ||
      (op.endpoint === '/api/caja/cierre-metodo' && (estado.metodos_cerrados || []).includes(data.medio_pago))
    )
    if (yaHecha) return true

    try {
      await api.post(op.endpoint, data)
    } catch (e) {
      if (esErrorDeRed(e)) throw e
      return false
    }

    if (op.endpoint === '/api/caja/apertura') {
      estado.abierta = true
      estado.metodos_cerrados = []
    } else if (op.endpoint === '/api/caja/cierre-total') {
      estado.abierta = false
      estado.metodos_cerrados = []
    } else {
      estado.metodos_cerrados = [...(estado.metodos_cerrados || []), data.medio_pago]
    }
    return true
  }

  return {
    cargarCola,
    pendientes,
    postear,
    marcarSubida,
    traerEstado,
    subirOperacion,
  }
}
