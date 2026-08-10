import { defineStore } from 'pinia'
import { ref } from 'vue'
import api from '@/services/api'

export const useProductosStore = defineStore('productos', () => {
  const productos = ref([])
  const categorias = ref([])
  const ofertas = ref([])
  const lastSync = ref(0)

  async function fetchAll(pageSize = 200) {
    try {
      const [prods, cats, ofs] = await Promise.all([
        api.get(`/api/productos?page_size=${pageSize}`).catch(() => null),
        api.get('/api/categorias').catch(() => null),
        api.get('/api/ofertas?page_size=200').catch(() => null)
      ])
      if (Array.isArray(prods)) productos.value = prods
      if (Array.isArray(cats)) categorias.value = cats
      if (Array.isArray(ofs)) ofertas.value = ofs
      lastSync.value = Date.now()
    } catch { /* fallback */ }
  }

  async function refreshProductos() {
    try {
      const prods = await api.get('/api/productos?page_size=200').catch(() => null)
      if (Array.isArray(prods)) productos.value = prods
      lastSync.value = Date.now()
    } catch { /* fallback */ }
  }

  async function refreshOfertas() {
    try {
      const ofs = await api.get('/api/ofertas?page_size=200').catch(() => null)
      if (Array.isArray(ofs)) ofertas.value = ofs
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
    fetchAll,
    refreshProductos,
    refreshOfertas,
    updateProductoLocal,
    decrementarStock
  }
})
