import { defineStore } from 'pinia'
import { ref } from 'vue'

export const usePosPreferencesStore = defineStore('posPreferences', () => {
  const STORAGE_KEY = 'apex-pos-preferences'

  const defaults = {
    showStatsPanel: true,
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
    setProductViewMode,
    setEnabledPaymentMethods,
    togglePaymentMethod,
    isPaymentMethodEnabled
  }
})