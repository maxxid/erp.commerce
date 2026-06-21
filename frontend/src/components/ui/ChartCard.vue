<template>
  <div class="bg-white border border-slate-200 p-5 rounded-2xl shadow-sm">
    <h3 class="font-bold text-slate-900 text-sm mb-4">{{ title }}</h3>
    <div class="flex items-end" :class="type === 'thin' ? 'gap-px h-32' : 'gap-1 h-32'">
      <div v-for="(val, idx) in (items?.valores || [])" :key="idx" class="flex-1 flex flex-col items-center gap-1">
        <span v-if="val > 0 && type === 'bars'" class="text-[9px] font-mono-data font-bold text-slate-600">{{ fcShort(val) }}</span>
        <div :class="[color, type === 'thin' && !val ? 'bg-slate-100' : '']" class="w-full rounded-t"
             :style="{ height: (val / maxVal * 100) + '%' }" v-show="type !== 'thin' || maxVal > 0"></div>
        <span class="text-[8px] text-slate-400" v-if="type !== 'thin' || idx % 3 === 0">{{ items?.labels?.[idx] || '' }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({ title: String, items: Object, type: { type: String, default: 'bars' }, color: String })

const maxVal = computed(() => Math.max(...(props.items?.valores || [0]), 1))
function fcShort(v) { if (v == null) return ''; return '$' + Number(v).toLocaleString('es-AR', { maximumFractionDigits: 0 }) }
</script>
