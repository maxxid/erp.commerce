import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useToastStore = defineStore('toasts', () => {
  const toasts = ref([])
  let idCounter = 1

  function add(type, message, options = {}) {
    const id = idCounter++
    const duration = options.duration ?? 5000
    const toast = {
      id,
      type,
      message,
      duration,
      progress: 100,
      paused: false,
      persistent: options.persistent || false
    }
    toasts.value.push(toast)
    if (!toast.persistent) {
      setTimeout(() => remove(id), duration)
    }
    return id
  }

  function remove(id) {
    const idx = toasts.value.findIndex(t => t.id === id)
    if (idx > -1) toasts.value.splice(idx, 1)
  }

  function success(message, options) { return add('success', message, options) }
  function error(message, options) { return add('error', message, { ...options, duration: options?.duration || 7000 }) }
  function warning(message, options) { return add('warning', message, options) }
  function info(message, options) { return add('info', message, options) }
  function clear() { toasts.value = [] }

  return { toasts, add, remove, success, error, warning, info, clear }
})
