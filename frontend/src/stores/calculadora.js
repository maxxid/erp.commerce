import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useCalculadoraStore = defineStore('calculadora', () => {
  // Estado de la expresión actual
  const expresion = ref('')
  const resultado = ref(null)
  const minimizada = ref(true)
  const posicion = ref({ x: 20, y: 80 })
  const historial = ref([])
  const maximoHistorial = ref(5)

  // Configuración (se carga de localStorage y se sincroniza con backend)
  const alcance = ref('pos-productos') // 'global' | 'pos-productos'
  const maxHistorial = ref(5)

  // Computed
  const hayExpresion = computed(() => expresion.value.length > 0)
  const tieneResultado = computed(() => resultado.value !== null)
  const mostrarDisplay = computed(() => expresion.value || (resultado.value !== null ? String(resultado.value) : '0'))

  // Cargar configuración desde localStorage
  function cargarConfig() {
    try {
      const guardado = localStorage.getItem('calculadora-config')
      if (guardado) {
        const config = JSON.parse(guardado)
        alcance.value = config.alcance || 'pos-productos'
        maximoHistorial.value = config.maxHistorial || 5
        minimizada.value = config.minimizada !== undefined ? config.minimizada : true
        posicion.value = config.posicion || { x: 20, y: 80 }
      }
    } catch { }
  }

  function guardarConfig() {
    try {
      localStorage.setItem('calculadora-config', JSON.stringify({
        alcance: alcance.value,
        maxHistorial: maximoHistorial.value,
        minimizada: minimizada.value,
        posicion: posicion.value
      }))
    } catch { }
  }

  // Historial
  function agregarAlHistorial(expr, res) {
    if (res === null) return
    const entrada = {
      id: Date.now(),
      expresion: expr,
      resultado: res,
      fecha: new Date().toISOString()
    }
    historial.value.unshift(entrada)
    if (historial.value.length > maximoHistorial.value) {
      historial.value = historial.value.slice(0, maximoHistorial.value)
    }
  }

  function limpiarHistorial() {
    historial.value = []
  }

  // Lógica de cálculo
  function agregarOperador(op) {
    if (!expresion.value && ['+', '-', '×', '÷'].includes(op)) return
    const ultimo = expresion.value.slice(-1)
    if (['+', '-', '×', '÷', '.'].includes(ultimo) && ['+', '-', '×', '÷', '.'].includes(op)) {
      expresion.value = expresion.value.slice(0, -1) + op
      return
    }
    if (op === '.' && expresion.value.split(/[\+\-×÷]/).pop().includes('.')) return
    expresion.value += op
  }

  function calcular() {
    if (!expresion.value) return
    try {
      // Reemplazar operadores visuales por JS
      const expr = expresion.value
        .replace(/×/g, '*')
        .replace(/÷/g, '/')
      const res = Function('"use strict"; return (' + expr + ')')()
      if (!Number.isFinite(res)) throw new Error('Resultado inválido')
      const resRedondeado = Math.round(res * 100000000) / 100000000
      resultado.value = resRedondeado
      agregarAlHistorial(expresion.value, resRedondeado)
      expresion.value = String(resRedondeado)
      resultado.value = null
    } catch {
      expresion.value = 'Error'
      setTimeout(() => { expresion.value = '' }, 1500)
    }
  }

  function limpiar() {
    expresion.value = ''
    resultado.value = null
  }

  function limpiarTodo() {
    expresion.value = ''
    resultado.value = null
  }

  function toggleMinimizar() {
    minimizada.value = !minimizada.value
    guardarConfig()
  }

  function setPosicion(x, y) {
    posicion.value = { x, y }
    guardarConfig()
  }

  // Cargar config al iniciar
  cargarConfig()

  return {
    expresion,
    resultado,
    minimizada,
    posicion,
    historial,
    maximoHistorial,
    alcance,
    maxHistorial,
    hayExpresion,
    tieneResultado,
    mostrarDisplay,
    agregarOperador,
    calcular,
    limpiar,
    limpiarTodo,
    toggleMinimizar,
    setPosicion,
    agregarAlHistorial,
    limpiarHistorial,
    alcance,
    maxHistorial,
    cargarConfig,
    guardarConfig,
    maximoHistorial
  }
})