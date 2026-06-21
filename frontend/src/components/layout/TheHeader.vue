<template>
  <header class="bg-white border-b border-slate-200 h-16 shrink-0 flex items-center justify-between px-8 z-10">
    <div class="flex items-center gap-3">
      <span class="text-slate-400 text-sm">ERP Fase 5 Vue</span>
      <i class="fa-solid fa-chevron-right text-xs text-slate-300"></i>
      <span class="text-brand-600 font-semibold text-sm uppercase tracking-wider font-display">{{ route.name }}</span>
    </div>
    <div class="flex items-center gap-4">
      <button @click="toggleApiMode('mock')" :class="apiMode === 'mock' ? 'bg-white shadow-sm font-bold text-slate-800' : 'text-slate-500'"
              class="px-3 py-1 rounded-lg text-[11px] uppercase tracking-wide bg-slate-100 border border-slate-200 transition duration-150">
        Simulador
      </button>
      <button @click="toggleApiMode('real')" :class="apiMode === 'real' ? 'bg-brand-600 text-white font-bold' : 'text-slate-500'"
              class="px-3 py-1 rounded-lg text-[11px] uppercase tracking-wide bg-slate-100 border border-slate-200 transition duration-150">
        API Real
      </button>
      <span class="text-slate-300">|</span>
      <button @click="showSettings = true" class="text-slate-400 hover:text-slate-600 transition" title="Ajustes">
        <i class="fa-solid fa-gear"></i>
      </button>
      <span class="text-xs font-mono-data text-slate-400">{{ time }}</span>
    </div>

    <!-- Settings Modal -->
    <Teleport to="body">
      <div v-if="showSettings" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="showSettings = false"></div>
        <div class="relative bg-white rounded-2xl shadow-2xl border border-slate-200 w-full max-w-sm">
          <div class="flex items-center justify-between p-5 border-b border-slate-100">
            <h3 class="text-lg font-bold text-slate-950 font-display">Ajustes de Búsqueda</h3>
            <button @click="showSettings = false" class="w-8 h-8 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition">
              <i class="fa-solid fa-xmark"></i>
            </button>
          </div>
          <div class="p-5 space-y-5">
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase block mb-3">Timeout (segundos)</label>
              <div class="flex items-center gap-2">
                <input v-model.number="settings.timeout" type="range" min="3" max="30" class="flex-1 accent-brand-600">
                <span class="text-sm font-mono-data font-bold text-slate-700 w-8 text-center">{{ settings.timeout }}</span>
              </div>
            </div>
            <div>
              <label class="text-[10px] font-bold text-slate-400 uppercase block mb-3">Fuentes de búsqueda</label>
              <div class="space-y-2">
                <label v-for="src in sources" :key="src.key" class="flex items-center justify-between py-2 px-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer transition">
                  <div class="flex items-center gap-2">
                    <span class="text-sm font-semibold text-slate-800">{{ src.label }}</span>
                    <span class="text-[10px] text-slate-400">{{ src.desc }}</span>
                  </div>
                  <button @click="settings.sources[src.key] = !settings.sources[src.key]"
                          :class="settings.sources[src.key] ? 'bg-brand-600' : 'bg-slate-300'"
                          class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0">
                    <span :class="settings.sources[src.key] ? 'translate-x-[18px]' : 'translate-x-[2px]'"
                          class="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200"></span>
                  </button>
                </label>
              </div>
            </div>
            <div>
              <label class="flex items-center justify-between py-2 px-3 rounded-xl border border-slate-200 hover:bg-slate-50 cursor-pointer transition">
                <span class="text-sm font-semibold text-slate-800">Auto-descargar catálogo</span>
                <button @click="settings.autoDownloadCatalogo = !settings.autoDownloadCatalogo"
                        :class="settings.autoDownloadCatalogo ? 'bg-brand-600' : 'bg-slate-300'"
                        class="relative w-9 h-5 rounded-full transition-colors duration-200 flex-shrink-0">
                  <span :class="settings.autoDownloadCatalogo ? 'translate-x-[18px]' : 'translate-x-[2px]'"
                        class="absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200"></span>
                </button>
              </label>
            </div>
          </div>
        </div>
      </div>
    </Teleport>
  </header>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'

defineProps({ apiMode: String, time: String })
const emit = defineEmits(['toggleApiMode'])

const route = useRoute()
const showSettings = ref(false)

const sources = [
  { key: 'carrefour', label: 'Carrefour', desc: 'API VTEX' },
  { key: 'vea', label: 'Vea', desc: 'Scraping HTML' },
  { key: 'masonline', label: 'Masonline', desc: 'Scraping HTML' },
  { key: 'supercoco', label: 'Super Coco', desc: 'Scraping HTML' },
]

const settings = reactive({
  sources: { carrefour: true, vea: true, masonline: true, supercoco: true },
  timeout: 15,
  autoDownloadCatalogo: false
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
    autoDownloadCatalogo: settings.autoDownloadCatalogo
  }))
}
</script>
