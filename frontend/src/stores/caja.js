import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api, { esErrorDeRed } from '@/services/api'
import { useCarritoStore } from '@/stores/carrito'

// El estado de la caja tal como lo vio la última vez que pudo preguntarle al
// servidor. Sin esto, refrescar la página sin internet dejaba "CAJA CERRADA"
// y el POS no dejaba cobrar aunque la caja estuviera abierta en el negocio:
// era la pieza que hacía imposible el día sin conexión.
const CLAVE_ESTADO = 'apex-caja-estado'

function leerEstado() {
  try { return JSON.parse(localStorage.getItem(CLAVE_ESTADO)) || null } catch { return null }
}

function guardarEstado(estado) {
  try { localStorage.setItem(CLAVE_ESTADO, JSON.stringify(estado)) } catch { /* storage lleno */ }
}

function esDeHoy(iso) {
  if (!iso) return false
  const guardado = new Date(iso)
  if (Number.isNaN(guardado.getTime())) return false
  const hoy = new Date()
  return guardado.getFullYear() === hoy.getFullYear()
    && guardado.getMonth() === hoy.getMonth()
    && guardado.getDate() === hoy.getDate()
}

export const useCajaStore = defineStore('caja', () => {
  const abierta = ref(false)
  const saldo_actual = ref(0)
  const saldos_cuentas = ref({})
  const saldo_cuenta_total = ref(0)
  const saldo_total = ref(0)
  const metodos_cerrados = ref([])
  const ultimoCierre = ref(null)
  const sesion_id = ref(null)
  const sesion_inicio = ref(null)
  // Cuando la red dejó de contestar, el refresco periódico no sirve para nada:
  // solo gasta batería e intentos. Se pausa y se reanuda solo (evento online)
  // o cuando un pedido a mano vuelve a salir bien.
  const sinRed = ref(false)
  // Había una caja abierta guardada, pero de **otro día**: no se restaura (el
  // servidor la da por cerrada con el cambio de fecha), pero que no quede en
  // silencio. El dueño la dejó abierta y la pantalla decía "CAJA CERRADA" sin
  // explicar por qué.
  const cerroDeOtroDia = ref(false)

  function aplicarEstado(state) {
    abierta.value = Boolean(state.abierta)
    if (state.abierta) cerroDeOtroDia.value = false
    // saldo_actual = solo el cajón; las cuentas digitales van aparte para
    // que el efectivo y el saldo de la app se cuadren por separado.
    saldo_actual.value = state.saldo_efectivo ?? state.saldo_actual ?? 0
    saldos_cuentas.value = state.saldos_cuentas || {}
    saldo_cuenta_total.value = state.saldo_cuenta_total || 0
    saldo_total.value = state.saldo_total ?? (saldo_actual.value + saldo_cuenta_total.value)
    metodos_cerrados.value = state.metodos_cerrados || []
    sesion_id.value = state.sesion_id ?? null
    sesion_inicio.value = state.sesion_inicio ?? null
  }

  function persistir() {
    guardarEstado({
      abierta: abierta.value,
      saldo_actual: saldo_actual.value,
      saldo_efectivo: saldo_actual.value,
      saldos_cuentas: saldos_cuentas.value,
      saldo_cuenta_total: saldo_cuenta_total.value,
      saldo_total: saldo_total.value,
      metodos_cerrados: metodos_cerrados.value,
      sesion_id: sesion_id.value,
      sesion_inicio: sesion_inicio.value,
      guardadoEn: new Date().toISOString(),
    })
  }

  // Se restaura apenas se arma el store, para que abrir la página sin internet
  // muestre la caja en el estado en que quedó. Salvo una: una caja de otro día,
  // porque el servidor la da por cerrada con el cambio de día — restaurarla
  // abierta dejaría el POS cobrando contra una sesión que ya no existe.
  //
  // La fecha se mira en dos pasos: primero la del servidor (`sesion_inicio`) y
  // si esa no sirve, la que escribió el propio navegador (`guardadoEn`). Antes
  // un solo `||` sobre `sesion_inicio` bastaba para quedarse sin caja en
  // silencio: si la hora del servidor no se podía leer, no se restauraba nada y
  // la pantalla decía "CAJA CERRADA" aunque la caja estuviera abierta.
  const guardado = leerEstado()
  const deOtroDia = Boolean(
    guardado && guardado.abierta
    && !esDeHoy(guardado.sesion_inicio)
    && !esDeHoy(guardado.guardadoEn)
  )
  if (guardado && !deOtroDia) {
    aplicarEstado(guardado)
  } else if (deOtroDia) {
    cerroDeOtroDia.value = true
  }

  // "hoy 08:15" / "el 19/10 18:20": lo que hay que mirar para saber si la caja
  // que dice abierta es la de hoy o la que quedó de otro día.
  const desdeTexto = computed(() => {
    const iso = sesion_inicio.value
    if (!iso) return ''
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return ''
    const hora = d.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
    if (d.toDateString() === new Date().toDateString()) return `hoy ${hora}`
    return `el ${d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' })} ${hora}`
  })

  async function fetchEstado() {
    try {
      const state = await api.get('/api/caja/estado')
      // Si el pedido salió, la red volvió: esto desbloquea el refresco
      // periódico aunque el navegador no llegue a disparar el evento online.
      sinRed.value = false
      if (state) {
        aplicarEstado(state)
        persistir()
        // Los carritos abiertos son de esta sesion: si la caja arranco de nuevo,
        // su reloj arranca de cero tambien.
        useCarritoStore().sincronizarSesion(state.sesion_id, state.sesion_inicio)
      }
    } catch (e) {
      // Un error HTTP (401, 500) no significa que no haya red: eso se sigue
      // reintentando. Se pausa solo cuando el servidor dejó de contestar.
      if (esErrorDeRed(e)) sinRed.value = true
    }
  }

  // Es lo que llaman los timers de60 s. A mano (`fetchEstado`) se pide igual,
  // para que entrar a una pantalla nunca quede con datos viejos por un corte
  // anterior que ya se superó.
  async function refrescarPeriodicamente() {
    if (sinRed.value) return
    await fetchEstado()
  }

  // Lo que hace la cola offline cuando no pudo abrirle la caja al servidor:
  // el negocio ya está trabajando con la caja abierta, así que el navegador
  // tiene que decir lo mismo aunque nadie le haya contestado todavía.
  function aplicarAperturaLocal(data) {
    const ahora = new Date().toISOString()
    const cuentas = { ...(data?.saldos_cuentas || {}) }
    aplicarEstado({
      abierta: true,
      saldo_efectivo: Number(data?.monto_inicial || 0),
      saldo_cuenta_total: Object.values(cuentas).reduce((s, v) => s + (Number(v) || 0), 0),
      saldos_cuentas: cuentas,
      metodos_cerrados: [],
      sesion_id: null, // el id real llega cuando la apertura se suba
      sesion_inicio: ahora,
      guardadoEn: ahora,
    })
    persistir()
  }

  function aplicarCierreLocal() {
    aplicarEstado({ abierta: false, guardadoEn: new Date().toISOString() })
    persistir()
  }

  async function fetchUltimoCierre() {
    try {
      const resp = await api.get('/api/caja/ultimo-cierre')
      if (resp) {
        ultimoCierre.value = resp
      }
    } catch { /* fallback */ }
  }

  // Al volver la red, el refresco periódico se habilita de nuevo; a los60 s
  // (o al entrar a una pantalla) el estado ya queda al día.
  if (typeof window !== 'undefined') {
    window.addEventListener('online', () => { sinRed.value = false })
  }

  return { abierta, saldo_actual, saldos_cuentas, saldo_cuenta_total, saldo_total, metodos_cerrados, ultimoCierre, sesion_id, sesion_inicio, sinRed, cerroDeOtroDia, desdeTexto, fetchEstado, refrescarPeriodicamente, fetchUltimoCierre, aplicarAperturaLocal, aplicarCierreLocal }
})
