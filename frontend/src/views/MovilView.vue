<template>
  <div class="min-h-screen bg-slate-50 p-4">
    <div class="max-w-md mx-auto">
      <div class="text-center mb-6">
        <div class="w-12 h-12 rounded-xl bg-brand-600 text-white flex items-center justify-center text-xl mx-auto">
          <i class="fa-solid fa-cubes-stacked"></i>
        </div>
        <h1 class="text-xl font-bold text-slate-900 mt-3 font-display">ApexERP Móvil</h1>
      </div>
      <div class="grid grid-cols-2 gap-3">
        <div class="bg-white p-4 rounded-2xl shadow-sm text-center" v-for="item in menu" :key="item.label" @click="$router.push(item.to)">
          <i :class="item.icon" class="text-2xl text-brand-600 mb-2"></i>
          <div class="text-xs font-semibold">{{ item.label }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const menu = [
  { to: '/dashboard', icon: 'fa-solid fa-chart-pie', label: 'Dashboard' },
  { to: '/pos', icon: 'fa-solid fa-cash-register', label: 'POS' },
  { to: '/products', icon: 'fa-solid fa-boxes-stacked', label: 'Productos' },
  { to: '/ventas', icon: 'fa-solid fa-receipt', label: 'Ventas' },
]
</script>
