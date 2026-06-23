<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useSyncStore } from '@/stores/sync'

const sync = useSyncStore()
const now = ref(Date.now())
let interval = null

onMounted(() => {
  sync.touch()
  interval = setInterval(() => { now.value = Date.now() }, 10000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})

const colorClass = {
  emerald: 'text-emerald-600 dark:text-emerald-400',
  amber: 'text-amber-600 dark:text-amber-400',
  red: 'text-red-600 dark:text-red-400'
}
</script>

<template>
  <div class="hidden lg:flex items-center gap-1.5 text-xs" :class="colorClass[sync.statusColor] || 'text-slate-400'">
    <i class="fa-solid fa-rotate text-[10px]"></i>
    <span>{{ sync.timeAgoLabel }}</span>
  </div>
</template>
