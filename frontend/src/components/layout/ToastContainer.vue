<script setup>
import { useToastStore } from '@/stores/toasts'
import { storeToRefs } from 'pinia'

const toastStore = useToastStore()
const { toasts } = storeToRefs(toastStore)

const icons = {
  success: 'fa-circle-check',
  error: 'fa-circle-xmark',
  warning: 'fa-triangle-exclamation',
  info: 'fa-circle-info'
}

const styles = {
  success: 'bg-white dark:bg-slate-900 border-emerald-200 dark:border-emerald-800/50 shadow-emerald-500/10',
  error: 'bg-white dark:bg-slate-900 border-rose-200 dark:border-rose-800/50 shadow-rose-500/10',
  warning: 'bg-white dark:bg-slate-900 border-amber-200 dark:border-amber-800/50 shadow-amber-500/10',
  info: 'bg-white dark:bg-slate-900 border-blue-200 dark:border-blue-800/50 shadow-blue-500/10'
}

const iconColors = {
  success: 'text-emerald-500',
  error: 'text-rose-500',
  warning: 'text-amber-500',
  info: 'text-blue-500'
}

const progressColors = {
  success: 'bg-emerald-500',
  error: 'bg-rose-500',
  warning: 'bg-amber-500',
  info: 'bg-blue-500'
}
</script>

<template>
  <div
    class="fixed top-4 right-4 z-[100] flex flex-col gap-3 w-full max-w-sm pointer-events-none"
    role="region"
    aria-live="polite"
    aria-label="Notificaciones"
  >
    <TransitionGroup
      enter-active-class="transition duration-300 ease-out-expo"
      enter-from-class="opacity-0 translate-x-6 scale-[0.96]"
      enter-to-class="opacity-100 translate-x-0 scale-100"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-x-0 scale-100"
      leave-to-class="opacity-0 translate-x-6 scale-[0.96]"
      move-class="transition duration-300 ease-out-expo"
    >
      <div
        v-for="toast in toasts"
        :key="toast.id"
        class="pointer-events-auto relative overflow-hidden rounded-xl border shadow-lg p-4"
        :class="styles[toast.type]"
      >
        <div class="flex items-start gap-3">
          <div class="mt-0.5 shrink-0">
            <i :class="`fa-solid ${icons[toast.type]} ${iconColors[toast.type]} text-lg`"></i>
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-medium text-slate-800 dark:text-slate-100 leading-snug">
              {{ toast.message }}
            </p>
          </div>
          <button
            type="button"
            aria-label="Cerrar notificación"
            class="shrink-0 w-6 h-6 flex items-center justify-center rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            @click="toastStore.remove(toast.id)"
          >
            <i class="fa-solid fa-xmark text-sm"></i>
          </button>
        </div>
        <div
          v-if="!toast.persistent && toast.duration"
          class="absolute bottom-0 left-0 h-0.5 transition-all linear"
          :class="progressColors[toast.type]"
          :style="{ width: `${toast.progress}%`, transitionDuration: `${toast.duration}ms` }"
        ></div>
      </div>
    </TransitionGroup>
  </div>
</template>
