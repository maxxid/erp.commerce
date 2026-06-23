import { onMounted, onUnmounted } from 'vue'

const registered = new Map()
let listener = null

function isInputActive() {
  const el = document.activeElement
  if (!el) return false
  const tag = el.tagName
  return tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || el.isContentEditable
}

function ensureListener() {
  if (listener) return
  listener = (e) => {
    if (isInputActive()) return
    for (const [, shortcuts] of registered) {
      for (const s of shortcuts) {
        const match =
          s.key && e.key === s.key &&
          !!s.ctrl === (e.ctrlKey || e.metaKey) &&
          !!s.shift === e.shiftKey &&
          !!s.alt === e.altKey
        if (match) {
          e.preventDefault()
          s.handler()
          return
        }
      }
    }
  }
  window.addEventListener('keydown', listener)
}

export function useKeyboardShortcuts(viewName, shortcuts) {
  onMounted(() => {
    registered.set(viewName, shortcuts)
    ensureListener()
  })

  onUnmounted(() => {
    registered.delete(viewName)
    if (registered.size === 0 && listener) {
      window.removeEventListener('keydown', listener)
      listener = null
    }
  })
}
