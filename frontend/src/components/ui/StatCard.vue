<template>
  <div class="bg-white border border-slate-200 p-4 rounded-2xl shadow-sm text-center">
    <div class="text-[10px] font-bold text-slate-400 uppercase">{{ label }}</div>
    <div :class="colorClass || colorToClass(color)" class="text-xl font-bold font-mono-data mt-1">{{ value }}</div>
    <div v-if="sub" class="text-[10px] text-slate-400 mt-0.5">{{ sub }}</div>
  </div>
</template>

<script setup>
defineProps({
  label: String,
  value: [String, Number],
  color: { type: String, default: 'emerald' },
  colorClass: { type: String, default: '' },
  sub: { type: String, default: '' }
})

function colorToClass(c) {
  const map = { emerald: 'text-emerald-600', indigo: 'text-indigo-600', brand: 'text-brand-600', amber: 'text-amber-600', rose: 'text-rose-600', blue: 'text-blue-600' }
  return map[c] || 'text-emerald-600'
}
</script>
