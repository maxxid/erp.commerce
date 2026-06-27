import { ref, computed } from 'vue'

const STORAGE_KEY = 'apex-pos-held'
const AUDIT_KEY = 'apex-pos-held-audit'

const heldTickets = ref(load())

function load() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]') }
  catch { return [] }
}

function save() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(heldTickets.value))
}

function audit(evento, detalle) {
  const log = JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]')
  log.push({
    ts: new Date().toISOString(),
    evento,
    detalle,
    usuario: JSON.parse(localStorage.getItem('apex_user') || '{}').nombre || 'desconocido',
  })
  if (log.length > 200) log.splice(0, log.length - 200)
  localStorage.setItem(AUDIT_KEY, JSON.stringify(log))
}

export function useHeldTickets() {
  const heldCount = computed(() => heldTickets.value.length)
  const orphanedCount = computed(() => heldTickets.value.filter(t => t._orphaned).length)

  // Tickets apartados hace más de 2 horas = sospechosos
  const suspiciousTickets = computed(() =>
    heldTickets.value.filter(t => {
      if (!t.createdAt) return false
      const age = Date.now() - new Date(t.createdAt).getTime()
      return age > 2 * 60 * 60 * 1000
    })
  )

  function holdTicket(cart) {
    if (!cart.items?.length) return null
    const now = new Date()
    const ticket = {
      id: Date.now(),
      createdAt: now.toISOString(),
      createdAtDisplay: now.toLocaleString('es-AR'),
      items: cart.items.map(i => ({ ...i })),
      cliente_id: cart.cliente_id,
      subtotal: cart.subtotal,
      descuento: cart.descuento,
      total: cart.total,
      medio_pago: cart.medio_pago || 'efectivo',
      itemCount: cart.items.reduce((s, i) => s + i.cantidad, 0),
      _deleted: false,
    }
    heldTickets.value.push(ticket)
    save()
    audit('HOLD', { ticketId: ticket.id, items: ticket.itemCount, total: ticket.total })
    return ticket
  }

  function recallTicket(id) {
    const idx = heldTickets.value.findIndex(t => t.id === id)
    if (idx === -1) return null
    const ticket = heldTickets.value[idx]
    heldTickets.value.splice(idx, 1)
    save()
    audit('RECALL', { ticketId: id, items: ticket.itemCount, total: ticket.total })
    return ticket
  }

  function deleteHeldTicket(id) {
    const ticket = heldTickets.value.find(t => t.id === id)
    if (ticket) {
      ticket._deleted = true
      ticket._deletedAt = new Date().toISOString()
      audit('DELETE_HELD', { ticketId: id, items: ticket.itemCount, total: ticket.total })
    }
    heldTickets.value = heldTickets.value.filter(t => t.id !== id)
    save()
  }

  function clearOrphanedFlag() {
    heldTickets.value = heldTickets.value.map(t => ({ ...t, _orphaned: false }))
    save()
  }

  function reload() {
    heldTickets.value = load()
  }

  function getHeldAuditLog() {
    try { return JSON.parse(localStorage.getItem(AUDIT_KEY) || '[]') }
    catch { return [] }
  }

  return {
    heldTickets,
    heldCount,
    orphanedCount,
    suspiciousTickets,
    holdTicket,
    recallTicket,
    deleteHeldTicket,
    clearOrphanedFlag,
    reload,
    getHeldAuditLog,
  }
}
