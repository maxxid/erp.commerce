import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useSyncStore = defineStore('sync', () => {
  const lastSyncAt = ref(parseInt(localStorage.getItem('apex-last-sync') || '0', 10) || Date.now())

  function touch() {
    lastSyncAt.value = Date.now()
    try { localStorage.setItem('apex-last-sync', String(lastSyncAt.value)) } catch {}
  }

  const timeAgoLabel = computed(() => {
    const diff = Math.floor((Date.now() - lastSyncAt.value) / 1000)
    if (diff < 5) return 'ahora'
    if (diff < 60) return `hace ${diff}s`
    const mins = Math.floor(diff / 60)
    if (mins < 60) return `hace ${mins}m`
    const hrs = Math.floor(mins / 60)
    return `hace ${hrs}h`
  })

  const statusColor = computed(() => {
    const diff = Math.floor((Date.now() - lastSyncAt.value) / 1000)
    if (diff < 300) return 'emerald'
    if (diff < 1800) return 'amber'
    return 'red'
  })

  return { lastSyncAt, touch, timeAgoLabel, statusColor }
})
