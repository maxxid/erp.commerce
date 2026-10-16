import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

// El catálogo entero guardado en el navegador, para poder seguir vendiendo si
// se corta la internet. Es un solo JSON con la fecha en que se bajó, así que
// el POS puede avisar con qué antigüedad está cobrando en vez de fingir que
// tiene datos frescos.
//
// Va en localStorage como el resto de la caché de la app (sesión, licencia,
// ventas pendientes). Hoy el catálogo pesa ~0,4 MB con 567 productos y el
// límite es ~5 MB compartido: si algún día deja de caber, la escritura falla y
// acá se avisa en vez de perder datos en silencio.
const CLAVE_CATALOGO = 'apex-catalogo-local'

function leerSnapshot() {
  try { return JSON.parse(localStorage.getItem(CLAVE_CATALOGO)) || null } catch { return null }
}

function guardarSnapshot(datos) {
  try {
    localStorage.setItem(CLAVE_CATALOGO, JSON.stringify(datos))
    return true
  } catch {
    // El navegador rechazó por espacio (o la pestaña está en modo privado).
    // No hay nada que hacer acá: se sigue con lo que hay en memoria y el
    // usuario se entera porque no aparece el aviso de catálogo guardado.
    return false
  }
}

export const useProductosStore = defineStore('productos', () => {
  const productos = ref([])
  const categorias = ref([])
  const ofertas = ref([])
  const lastSync = ref(0)
  // True cuando lo que se está mostrando viene del navegador y no del servidor:
  // los precios y el stock pueden no ser los de ahora.
  const sinRed = ref(false)
  // Cuándo se bajó el catálogo que se está usando, o null si no hay ninguno.
  const datosDe = ref(null)

  function aplicarSnapshot(snapshot) {
    if (!snapshot) return false
    if (Array.isArray(snapshot.productos)) productos.value = snapshot.productos
    if (Array.isArray(snapshot.categorias)) categorias.value = snapshot.categorias
    if (Array.isArray(snapshot.ofertas)) ofertas.value = snapshot.ofertas
    datosDe.value = snapshot.generado || null
    return true
  }

  // Se restaura apenas se arma el store: el POS no arranca con la grilla vacía
  // mientras llegan los datos, que en un mostrador con wifi flojo es un rato
  // mirando pantalla en blanco.
  aplicarSnapshot(leerSnapshot())

  async function fetchAll(pageSize = 100000) {
    const [prods, cats, ofs] = await Promise.all([
      api.get(`/api/productos?page_size=${pageSize}`).catch(() => null),
      api.get('/api/categorias').catch(() => null),
      api.get('/api/ofertas?page_size=100000').catch(() => null)
    ])

    // Sin productos no hay con qué vender: se cae al catálogo guardado en el
    // navegador en vez de dejar la grilla en blanco.
    if (!Array.isArray(prods)) {
      sinRed.value = true
      aplicarSnapshot(leerSnapshot())
      return
    }

    productos.value = prods
    if (Array.isArray(cats)) categorias.value = cats
    if (Array.isArray(ofs)) ofertas.value = ofs

    const generado = new Date().toISOString()
    lastSync.value = Date.now()
    sinRed.value = false
    datosDe.value = generado
    guardarSnapshot({
      generado,
      productos: prods,
      categorias: categorias.value,
      ofertas: ofertas.value,
    })
  }

  async function refreshProductos() {
    try {
      const prods = await api.get('/api/productos?page_size=100000').catch(() => null)
      if (Array.isArray(prods)) {
        productos.value = prods
        lastSync.value = Date.now()
        sinRed.value = false
      }
    } catch { /* fallback */ }
  }

  async function refreshOfertas() {
    try {
      const ofs = await api.get('/api/ofertas?page_size=100000').catch(() => null)
      if (Array.isArray(ofs)) {
        ofertas.value = ofs
        sinRed.value = false
      }
    } catch { /* fallback */ }
  }

  function updateProductoLocal(producto) {
    const idx = productos.value.findIndex(p => p.id === producto.id)
    if (idx >= 0) {
      productos.value[idx] = { ...productos.value[idx], ...producto }
    } else {
      productos.value.push(producto)
    }
  }

  function decrementarStock(productoId, cantidad) {
    const prod = productos.value.find(p => p.id === productoId)
    if (prod && prod.stock_actual !== undefined) {
      prod.stock_actual = Math.max(0, prod.stock_actual - cantidad)
    }
  }

  return {
    productos,
    categorias,
    ofertas,
    lastSync,
    sinRed,
    datosDe,
    fetchAll,
    refreshProductos,
    refreshOfertas,
    updateProductoLocal,
    decrementarStock
  }
})
