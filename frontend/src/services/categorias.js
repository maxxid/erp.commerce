// Color por rubro de las categorías.
//
// Si la categoría no tiene `color` cargado en la base, la pantalla usa el de
// acá: así una categoría nueva ya se ve con color sin que nadie la edite, y el
// editor de Ajustes lo precarga con este valor. Guardar desde Ajustes escribe
// `color` y tapa este default.
const POR_RUBRO = {
  golosinas: '#f59e0b',
  almacen: '#3b82f6',
  bebidas: '#06b6d4',
  'bebidas alcoholicas': '#ef4444',
  frescos: '#22c55e',
  lacteos: '#eab308',
  limpieza: '#8b5cf6',
  papeleria: '#64748b',
  cafeteria: '#a16207',
  libreria: '#0ea5e9',
  perfumeria: '#ec4899',
  kiosco: '#f97316',
  panaderia: '#d97706',
  helados: '#14b8a6',
  general: '#94a3b8',
  otros: '#94a3b8',
}

const SIN_COLOR = '#94a3b8'

function clave(nombre) {
  return (nombre || '')
    .toString()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\s+/g, ' ')
    .toLowerCase()
    .trim()
}

export function colorDeCategoria(categoria) {
  if (!categoria) return SIN_COLOR
  if (categoria.color) return categoria.color
  return POR_RUBRO[clave(categoria.nombre)] || SIN_COLOR
}

export { POR_RUBRO as COLORES_POR_RUBRO, SIN_COLOR as COLOR_SIN_CATEGORIA }
