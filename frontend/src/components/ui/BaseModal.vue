<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  size: { type: String, default: 'md' }, // sm, md, lg, xl, 2xl, full
  showClose: { type: Boolean, default: true },
  closeOnOverlay: { type: Boolean, default: true },
  closeOnEsc: { type: Boolean, default: true },
  persistent: { type: Boolean, default: false },
  padding: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue', 'close', 'open'])

const modalRef = ref(null)
const overlayRef = ref(null)
const isOpen = ref(false)

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-lg',
  xl: 'max-w-xl',
  '2xl': 'max-w-2xl',
  '3xl': 'max-w-3xl',
  full: 'max-w-full mx-4'
}[props.size]

function close() {
  if (props.persistent) return
  emit('update:modelValue', false)
  emit('close')
}

function onOverlayClick(e) {
  if (props.closeOnOverlay && e.target === overlayRef.value) close()
}

function onKeydown(e) {
  if (props.closeOnEsc && e.key === 'Escape' && isOpen.value) {
    e.stopPropagation()
    close()
  }
  if (e.key === 'Tab' && isOpen.value && modalRef.value) {
    trapFocus(e)
  }
}

function trapFocus(e) {
  const focusable = modalRef.value.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  )
  if (!focusable.length) return
  const first = focusable[0]
  const last = focusable[focusable.length - 1]
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault()
    last.focus()
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault()
    first.focus()
  }
}

watch(() => props.modelValue, async (val) => {
  if (val) {
    document.body.classList.add('overflow-hidden')
    isOpen.value = true
    emit('open')
    await nextTick()
    const focusable = modalRef.value?.querySelector(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )
    focusable?.focus()
  } else {
    document.body.classList.remove('overflow-hidden')
    isOpen.value = false
  }
})

onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.classList.remove('overflow-hidden')
})
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200 ease-out-expo"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition duration-150 ease-in"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="modelValue"
        ref="overlayRef"
        class="fixed inset-0 z-[90] bg-slate-950/40 dark:bg-black/60 backdrop-blur-sm"
        aria-modal="true"
        role="dialog"
        @click="onOverlayClick"
      >
        <div class="min-h-screen px-4 py-6 flex items-center justify-center">
          <Transition
            enter-active-class="transition duration-300 ease-out-expo"
            enter-from-class="opacity-0 scale-[0.96] translate-y-3"
            enter-to-class="opacity-100 scale-100 translate-y-0"
            leave-active-class="transition duration-200 ease-in"
            leave-from-class="opacity-100 scale-100 translate-y-0"
            leave-to-class="opacity-0 scale-[0.96] translate-y-3"
          >
            <div
              v-if="modelValue"
              ref="modalRef"
              class="w-full bg-white dark:bg-slate-900 rounded-2xl shadow-2xl border border-slate-200/80 dark:border-slate-700/80 outline-none"
              :class="[sizeClasses]"
              @click.stop
            >
              <div
                v-if="title || showClose"
                class="flex items-center justify-between px-6 py-4 border-b border-slate-100 dark:border-slate-800"
              >
                <h3
                  v-if="title"
                  class="text-lg font-semibold text-slate-900 dark:text-white"
                >
                  {{ title }}
                </h3>
                <button
                  v-if="showClose"
                  type="button"
                  aria-label="Cerrar"
                  class="ml-auto w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                  @click="close"
                >
                  <i class="fa-solid fa-xmark"></i>
                </button>
              </div>
              <div :class="padding ? 'p-6' : ''">
                <slot />
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
