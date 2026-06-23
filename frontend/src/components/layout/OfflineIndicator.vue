<script setup>
import { ref, onMounted, onUnmounted } from 'vue'

const isOffline = ref(!navigator.onLine)

function onOnline() { isOffline.value = false }
function onOffline() { isOffline.value = true }

onMounted(() => {
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
})

onUnmounted(() => {
  window.removeEventListener('online', onOnline)
  window.removeEventListener('offline', onOffline)
})
</script>

<template>
  <Transition
    enter-active-class="transition duration-300 ease-out"
    enter-from-class="opacity-0 -translate-y-1"
    enter-to-class="opacity-100 translate-y-0"
    leave-active-class="transition duration-200 ease-in"
    leave-from-class="opacity-100 translate-y-0"
    leave-to-class="opacity-0 -translate-y-1"
  >
    <div v-if="isOffline" class="fixed top-0 left-0 right-0 z-[200] bg-red-600 text-white text-xs text-center py-1.5 px-4 font-medium">
      <i class="fa-solid fa-wifi mr-1.5"></i>
      Sin conexión. Algunas funciones pueden no estar disponibles.
    </div>
  </Transition>
</template>
