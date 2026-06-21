import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useToastStore = defineStore('toasts', () => {
  const toasts = ref([])

  function add(type, message) {
    const id = Date.now()
    toasts.value.push({ id, type, message })
    setTimeout(() => remove(id), 5000)
  }

  function remove(id) {
    toasts.value = toasts.value.filter(t => t.id !== id)
  }

  return { toasts, add, remove }
})
