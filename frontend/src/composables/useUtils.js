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

export function formatDateShort(dateStr) {
  if (!dateStr) return '\u2014'
  const d = new Date(dateStr)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
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

export function formatDateTime(isoStr) {
  if (!isoStr) return '\u2014'
  const d = new Date(isoStr)
  return d.toLocaleString('es-AR', {
    timeZone: 'America/Argentina/Buenos_Aires',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  })
}
