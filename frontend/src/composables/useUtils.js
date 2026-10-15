export function formatCurrency(v) {
  if (v == null) return '\u2014'
  return '$ ' + Number(v).toLocaleString('es-AR', { minimumFractionDigits: 2 })
}

// Versión corta para los números que van arriba de una barra del dashboard:
// con "$ 123.456,00" los rótulos se pisan entre sí. Sin decimales porque en
// una barra la precisión al centavo no dice nada.
export function formatCurrencyShort(v) {
  const n = Number(v) || 0
  const abs = Math.abs(n)
  const signo = n < 0 ? '-' : ''
  if (abs >= 1000000) return signo + '$ ' + (abs / 1000000).toLocaleString('es-AR', { maximumFractionDigits: 1 }) + 'M'
  if (abs >= 1000) return signo + '$ ' + (abs / 1000).toLocaleString('es-AR', { maximumFractionDigits: 1 }) + 'k'
  return signo + '$ ' + abs.toLocaleString('es-AR', { maximumFractionDigits: 0 })
}

// La base guarda UTC sin zona horaria (naive). Si el string llega así,
// JavaScript lo toma como hora local de quien mira: un evento de las 09:00 UTC
// se veía 06:00 en Argentina. Acá se le pone la 'Z' a mano para que todos
// vean lo mismo, y las fechas sin hora (YYYY-MM-DD) se quedan en UTC para
// que no se corra un día.
const TZ_AR = 'America/Argentina/Buenos_Aires'
const SOLO_FECHA = /^\d{4}-\d{2}-\d{2}$/
const CON_HORA = /^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}/
const YA_CON_ZONA = /[zZ]|[+-]\d{2}:?\d{2}$/

export function parseFechaUTC(v) {
  if (v instanceof Date) return v
  let s = String(v ?? '').trim()
  if (!s) return new Date(NaN)
  if (SOLO_FECHA.test(s)) return new Date(s + 'T00:00:00Z')
  if (YA_CON_ZONA.test(s)) return new Date(s)
  if (CON_HORA.test(s)) return new Date(s.replace(' ', 'T') + 'Z')
  return new Date(v)
}

function esSoloFecha(v) {
  return SOLO_FECHA.test(String(v ?? '').trim())
}

export function formatDateShort(v) {
  if (!v) return '\u2014'
  const d = parseFechaUTC(v)
  if (isNaN(d)) return '\u2014'
  return d.toLocaleDateString('es-AR', {
    timeZone: esSoloFecha(v) ? 'UTC' : TZ_AR,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function formatDateTime(v) {
  if (!v) return '\u2014'
  const d = parseFechaUTC(v)
  if (isNaN(d)) return '\u2014'
  return d.toLocaleString('es-AR', {
    timeZone: esSoloFecha(v) ? 'UTC' : TZ_AR,
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

export function formatTimeShort(v) {
  if (!v || esSoloFecha(v)) return ''
  const d = parseFechaUTC(v)
  if (isNaN(d)) return ''
  return d.toLocaleTimeString('es-AR', {
    timeZone: TZ_AR,
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}

// ¿La fecha pasó hoy, según la hora del negocio (Argentina)?
export function esHoy(v) {
  const d = parseFechaUTC(v)
  if (isNaN(d)) return true
  const mismoDia = (x) => x.toLocaleDateString('sv', { timeZone: TZ_AR })
  return mismoDia(d) === mismoDia(new Date())
}

// Fecha local (YYYY-MM-DD) en hora del negocio. Para los endpoints de caja
// que agrupan por día argentino: la parte de fecha de un ISO en UTC puede
// ser el día siguiente (una sesión abierta 22:19 AR es 01:19 UTC).
export function fechaLocalAR(v) {
  const d = parseFechaUTC(v)
  if (isNaN(d)) return ''
  return d.toLocaleDateString('sv', { timeZone: TZ_AR })
}

// "hace 5 min" / "hace 2h" / "hace 3d", para las listas de eventos.
export function timeAgo(v) {
  if (!v) return ''
  const diff = Date.now() - parseFechaUTC(v).getTime()
  if (isNaN(diff)) return ''
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `hace ${mins} min`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `hace ${hours}h`
  const days = Math.floor(hours / 24)
  return `hace ${days}d`
}

export function formatFileSize(bytes) {
  if (!bytes) return '0 B'
  const u = ['B', 'KB', 'MB', 'GB']
  let i = 0, s = bytes
  while (s >= 1024 && i < u.length - 1) { s /= 1024; i++ }
  return s.toFixed(i > 0 ? 1 : 0) + ' ' + u[i]
}

export function esc(s) {
  if (!s) return ''
  return String(s).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
