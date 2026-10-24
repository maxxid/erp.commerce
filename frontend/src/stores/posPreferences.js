import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePosPreferencesStore = defineStore('posPreferences', () => {
  const STORAGE_KEY = 'apex-pos-preferences'

  const defaults = {
    // El panel lateral (mini dashboard) arranca **cerrado**: es donde se ven
    // los KPIs del día y las últimas transacciones, y un dato vacío o viejo en
    // esa pantalla se lee como "algo se rompió" — el dueño pidió que por
    // defecto esté minimizado. `showStatsPanelTocado` deja constancia de si el
    // usuario lo abrió/cerró a mano, para que el default de Ajustes no le pise
    // la elección en cada carga.
    showStatsPanel: false,
    showStatsPanelTocado: false,
    productViewMode: 'grilla',
    enabledPaymentMethods: [
      'efectivo',
      'transferencia',
      'mercadopago_qr',
      'qr_interop',
      'mercadopago_pos',
      'smartpoint',
      'cta_corriente'
    ]
  }

  function load() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const parsed = JSON.parse(stored)
        return { ...defaults, ...parsed }
      }
    } catch { }
    return { ...defaults }
  }

  const prefs = ref(load())

  function save() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs.value))
    } catch { }
  }

  function setShowStatsPanel(value) {
    prefs.value.showStatsPanel = value
    prefs.value.showStatsPanelTocado = true   // lo mandó el usuario, no el default
    save()
  }

  // Default que manda Ajustes (lo elige el dueño): sólo se aplica si el
  // usuario nunca abrió ni cerró el panel a mano.
  function aplicarDefaultPanel(valor) {
    if (typeof valor !== 'boolean' || prefs.value.showStatsPanelTocado) return
    prefs.value.showStatsPanel = valor
    save()
  }

  function setProductViewMode(value) {
    prefs.value.productViewMode = value
    save()
  }

  function setEnabledPaymentMethods(methods) {
    prefs.value.enabledPaymentMethods = methods
    save()
  }

  function togglePaymentMethod(method) {
    const idx = prefs.value.enabledPaymentMethods.indexOf(method)
    if (idx >= 0) {
      prefs.value.enabledPaymentMethods.splice(idx, 1)
    } else {
      prefs.value.enabledPaymentMethods.push(method)
    }
    save()
  }

  function isPaymentMethodEnabled(method) {
    return prefs.value.enabledPaymentMethods.includes(method)
  }

  return {
    prefs,
    defaults,
    load,
    save,
    setShowStatsPanel,
    aplicarDefaultPanel,
    setProductViewMode,
    setEnabledPaymentMethods,
    togglePaymentMethod,
    isPaymentMethodEnabled
  }
})