<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseToggle from '@/components/ui/BaseToggle.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import SyncIndicator from '@/components/layout/SyncIndicator.vue'
import { useSounds } from '@/composables/useSounds'

const props = defineProps({
  apiMode: { type: String, default: 'real' },
  time: { type: String, default: '' },
  networkActive: { type: Boolean, default: false }
})

const emit = defineEmits(['toggleApiMode', 'openCommandPalette'])

const route = useRoute()
const showSettings = ref(false)
const justSaved = ref(false)
const soundsEnabled = ref(false)
const { toggleEnabled } = useSounds()

soundsEnabled.value = localStorage.getItem('apex-sounds-enabled') === 'true'

function toggleSounds() {
  soundsEnabled.value = toggleEnabled()
}

const sources = [
  { key: 'carrefour', label: 'Carrefour', desc: 'API VTEX' },
  { key: 'vea', label: 'Vea', desc: 'Scraping HTML' },
  { key: 'masonline', label: 'Masonline', desc: 'Scraping HTML' },
  { key: 'supercoco', label: 'Super Coco', desc: 'Scraping HTML' }
]

const settings = reactive({
  sources: { carrefour: true, vea: true, masonline: true, supercoco: true },
  timeout: 15,
  autoDownloadCatalogo: false,
  ticketWidth: 80
})

onMounted(() => {
  const saved = localStorage.getItem('apex_lookup_settings')
  if (saved) {
    try { Object.assign(settings, JSON.parse(saved)) } catch {}
  }
})

function toggleApiMode(mode) {
  emit('toggleApiMode', mode)
}

function saveSettings() {
  localStorage.setItem('apex_lookup_settings', JSON.stringify({
    sources: { ...settings.sources },
    timeout: settings.timeout,
    autoDownloadCatalogo: settings.autoDownloadCatalogo,
    ticketWidth: settings.ticketWidth
  }))
  justSaved.value = true
  setTimeout(() => { justSaved.value = false }, 1500)
}
</script>

<template>
  <header class="bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 h-16 shrink-0 flex items-center justify-between px-6 lg:px-8 z-10 sticky top-0">
    <div class="flex items-center gap-3 min-w-0">
      <nav class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
        <span class="font-medium">ApexERP</span>
        <i class="fa-solid fa-chevron-right text-[10px] text-slate-300 dark:text-slate-600"></i>
      </nav>
      <h1 class="text-slate-900 dark:text-white font-semibold text-sm uppercase tracking-wider font-display truncate">
        {{ route.name || 'Panel' }}
      </h1>
    </div>

    <div class="flex items-center gap-2 sm:gap-4">
      <button
        type="button"
        class="hidden md:flex items-center gap-2 pl-3 pr-2 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors text-xs"
        @click="emit('openCommandPalette')"
      >
        <i class="fa-solid fa-magnifying-glass"></i>
        <span>Buscar</span>
        <kbd class="ml-1 px-1.5 py-0.5 rounded bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 text-[10px] font-medium">Ctrl K</kbd>
      </button>

      <div class="flex items-center bg-slate-100 dark:bg-slate-800 rounded-lg p-0.5 border border-slate-200 dark:border-slate-700">
        <button
          type="button"
          :class="apiMode === 'mock'
            ? 'bg-white dark:bg-slate-700 text-slate-800 dark:text-white shadow-sm'
            : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
          class="px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide transition-all duration-200"
          @click="toggleApiMode('mock')"
        >
          Simulador
        </button>
        <button
          type="button"
          :class="apiMode === 'real'
            ? 'bg-brand-600 text-white shadow-sm shadow-brand-500/25'
            : 'text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200'"
          class="px-2.5 py-1 rounded-md text-[11px] font-semibold uppercase tracking-wide transition-all duration-200"
          @click="toggleApiMode('real')"
        >
          API Real
        </button>
      </div>

      <div
        class="w-2 h-2 rounded-full transition-all duration-200"
        :class="networkActive ? 'bg-brand-500 animate-ping' : 'bg-emerald-500'"
        :title="networkActive ? 'Red activa' : 'Conectado'"
      ></div>

      <SyncIndicator />

      <button
        type="button"
        :aria-label="soundsEnabled ? 'Desactivar sonidos' : 'Activar sonidos'"
        :title="soundsEnabled ? 'Sonidos activados' : 'Sonidos desactivados'"
        class="w-9 h-9 rounded-lg flex items-center justify-center transition-colors outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
        :class="soundsEnabled ? 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20' : 'text-slate-400 dark:text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800'"
        @click="toggleSounds"
      >
        <i :class="soundsEnabled ? 'fa-solid fa-volume-high' : 'fa-solid fa-volume-xmark'"></i>
      </button>

      <button
        type="button"
        aria-label="Ajustes"
        class="w-9 h-9 rounded-lg flex items-center justify-center text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 hover:text-slate-800 dark:hover:text-white transition-colors outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
        @click="showSettings = true"
      >
        <i class="fa-solid fa-gear"></i>
      </button>

      <span class="hidden sm:inline-block text-xs font-mono-data text-slate-400 dark:text-slate-500">{{ time }}</span>
    </div>

    <BaseModal
      v-model="showSettings"
      title="Ajustes de Búsqueda"
      size="md"
      @close="saveSettings"
    >
      <div class="space-y-6">
        <div>
          <label class="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide block mb-3">Timeout (segundos)</label>
          <div class="flex items-center gap-3">
            <input
              v-model.number="settings.timeout"
              type="range"
              min="3"
              max="30"
              class="flex-1 accent-brand-600 h-1.5 bg-slate-200 dark:bg-slate-700 rounded-lg appearance-none cursor-pointer"
              @change="saveSettings"
            >
            <span class="text-sm font-mono-data font-bold text-slate-700 dark:text-slate-200 w-8 text-center">{{ settings.timeout }}</span>
          </div>
        </div>

        <div>
          <label class="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wide block mb-3">Fuentes de búsqueda</label>
          <div class="space-y-2">
            <div
              v-for="src in sources"
              :key="src.key"
              class="flex items-center justify-between py-2.5 px-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50"
            >
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold text-slate-800 dark:text-slate-100">{{ src.label }}</span>
                <span class="text-[10px] text-slate-400 dark:text-slate-500">{{ src.desc }}</span>
              </div>
              <BaseToggle
                :model-value="settings.sources[src.key]"
                size="sm"
                @update:model-value="settings.sources[src.key] = $event; saveSettings()"
              />
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div class="flex items-center justify-between py-2.5 px-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
            <div>
              <span class="text-sm font-semibold text-slate-800 dark:text-slate-100 block">Ancho de ticket</span>
              <span class="text-[10px] text-slate-400 dark:text-slate-500">{{ settings.ticketWidth }}mm</span>
            </div>
            <BaseToggle
              :model-value="settings.ticketWidth === 80"
              size="sm"
              @update:model-value="settings.ticketWidth = $event ? 80 : 58; saveSettings()"
            />
          </div>
          <div class="flex items-center justify-between py-2.5 px-3 rounded-xl border border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-800/50">
            <span class="text-sm font-semibold text-slate-800 dark:text-slate-100">Auto-descargar catálogo</span>
            <BaseToggle
              :model-value="settings.autoDownloadCatalogo"
              size="sm"
              @update:model-value="settings.autoDownloadCatalogo = $event; saveSettings()"
            />
          </div>
        </div>

        <div class="flex items-center justify-between pt-2">
          <Transition name="fade">
            <span v-if="justSaved" class="text-xs font-medium text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <i class="fa-solid fa-check"></i> Guardado
            </span>
          </Transition>
          <button type="button" class="btn-primary text-sm" @click="showSettings = false">Listo</button>
        </div>
      </div>
    </BaseModal>
  </header>
</template>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 200ms ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
