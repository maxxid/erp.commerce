// Única definición de "stock bajo" en el frontend.
//
// Espejo de app/services/stock_service.py: producto activo que controla stock,
// con mínimo definido (minimo > 0) y stock alcanzado o por debajo. Un mínimo
// en 0 significa "no definí mínimo para este producto", no "está al límite":
// antes el chip de Productos usaba un 5 por defecto y marcaba ~319 productos
// mientras el Dashboard marcaba 18.

export function esStockBajo(p) {
  if (!p || p.activo === false || p.controla_stock === false) return false
  const minimo = Number(p.stock_minimo)
  if (!(minimo > 0)) return false
  const stock = Number(p.stock_actual)
  return stock >= 0 && stock <= minimo
}

// Agotado: controla stock y quedó en cero o menos. Es otra alerta que la de
// bajo mínimo (filtro_agotado del backend) y conviene marcarlo igual, porque
// un producto sin mínimo definido pero sin stock tampoco conviene dejar de
// mostrar en rojo.
export function esAgotado(p) {
  if (!p || p.activo === false || p.controla_stock === false) return false
  return Number(p.stock_actual) <= 0
}
