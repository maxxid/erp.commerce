// Cuentas digitales de la caja: el saldo vive en la app de cada proveedor, no
// en el cajón. Se arquean aparte del efectivo porque el "esperado" sale de lo
// que el dueño anota al abrir, no de los movimientos del día.
export const MEDIO_LABELS_CUENTA = {
  smartpoint: 'SmartPoint',
  mercadopago_qr: 'QR MercadoPago',
  mercadopago_pos: 'POS MercadoPago',
  qr_interop: 'QR BCRA',
}

export const MEDIOS_CUENTA = Object.keys(MEDIO_LABELS_CUENTA)

// Objeto con todas las cuentas en 0: los saldos iniciales arrancan vacíos.
export function cuentasEnCero() {
  return MEDIOS_CUENTA.reduce((acc, m) => {
    acc[m] = 0
    return acc
  }, {})
}
