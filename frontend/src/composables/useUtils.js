export function formatCurrency(v) {
  if (v == null) return '\u2014'
  return '$ ' + Number(v).toLocaleString('es-AR', { minimumFractionDigits: 2 })
}

export function formatDateShort(dateStr) {
  if (!dateStr) return '\u2014'
  const d = new Date(dateStr)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
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

export function buildArcaQrUrl(factura, emisor) {
  if (!factura?.cae) return null

  const tipoDocMap = { 96: 96, 80: 80, 86: 86, 99: 99 }
  let tipoDoc = factura.tipo_doc_comprador || 99
  let nroDoc = factura.nro_doc_comprador || '0'

  if (tipoDoc === 99 || !nroDoc || nroDoc === '0' || nroDoc === '') {
    tipoDoc = 99
    nroDoc = '0'
  }

  const fechaStr = factura.fecha_emision
    ? factura.fecha_emision.substring(0, 10)
    : new Date().toISOString().substring(0, 10)

  const payload = {
    ver: 1,
    fecha: fechaStr,
    cuit: parseInt((emisor.cuit || '').replace(/-/g, ''), 10) || 0,
    ptoVta: parseInt(factura.punto_venta, 10) || 1,
    tipoCmp: parseInt(factura.tipo, 10) || 11,
    nroCmp: parseInt(factura.numero_fiscal, 10) || 0,
    importe: parseFloat(factura.total || 0),
    moneda: 'PES',
    ctz: 1.0,
    tipoDocRec: tipoDoc,
    nroDocRec: String(nroDoc).replace(/-/g, ''),
    tipoAut: 'E',
    codAut: parseInt(factura.cae, 10) || 0,
  }

  try {
    const jsonStr = JSON.stringify(payload)
    const b64 = btoa(jsonStr)
    return `https://www.afip.gob.ar/fe/qr/?p=${b64}`
  } catch {
    return null
  }
}

export function generarQrDataUrl(qrUrl, size = 150) {
  if (!qrUrl) return null
  return `https://api.qrserver.com/v1/create-qr-code/?size=${size}x${size}&data=${encodeURIComponent(qrUrl)}`
}
