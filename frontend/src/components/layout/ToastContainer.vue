<template>
  <div class="fixed top-4 right-4 z-[100] space-y-2 pointer-events-none max-w-sm w-full">
    <div v-for="toast in toasts" :key="toast.id"
         class="p-4 rounded-xl shadow-lg border text-xs font-semibold flex items-center justify-between gap-3 pointer-events-auto transition-all"
         :class="{
           'bg-emerald-50 border-emerald-200 text-emerald-850': toast.type === 'success',
           'bg-rose-50 border-rose-200 text-rose-850': toast.type === 'error',
           'bg-amber-50 border-amber-200 text-amber-850': toast.type === 'warning',
           'bg-blue-50 border-blue-200 text-blue-850': toast.type === 'info'
         }">
      <div class="flex items-center gap-2">
        <i class="fa-solid" :class="{
          'fa-circle-check text-emerald-600': toast.type === 'success',
          'fa-circle-xmark text-rose-600': toast.type === 'error',
          'fa-circle-exclamation text-amber-600': toast.type === 'warning',
          'fa-circle-info text-blue-600': toast.type === 'info'
        }"></i>
        <span>{{ toast.message }}</span>
      </div>
      <button @click="toastStore.remove(toast.id)" class="text-slate-400 hover:text-slate-600">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { useToastStore } from '@/stores/toasts'
import { storeToRefs } from 'pinia'

const toastStore = useToastStore()
const { toasts } = storeToRefs(toastStore)
</script>
