<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const names = {
  dashboard: 'Dashboard',
  pos: 'POS de Ventas',
  products: 'Productos',
  caja: 'Caja y Arqueos',
  ventas: 'Ventas',
  calendario: 'Calendario',
  compras: 'Compras',
  proveedores: 'Proveedores',
  clientes: 'Clientes',
  reportes: 'Reportes',
  usuarios: 'Usuarios',
  licencias: 'Licencias',
  auditoria: 'Auditoría',
  backups: 'Backups',
}

const items = computed(() => {
  const name = route.name
  if (!name || name === 'login') return []
  return [
    { label: 'Inicio', to: '/dashboard' },
    { label: names[name] || name, to: null }
  ]
})
</script>

<template>
  <nav v-if="items.length" class="flex items-center gap-2 text-sm text-slate-500 dark:text-slate-400">
    <template v-for="(item, idx) in items" :key="idx">
      <i v-if="idx > 0" class="fa-solid fa-chevron-right text-[10px] text-slate-300 dark:text-slate-600"></i>
      <router-link
        v-if="item.to"
        :to="item.to"
        class="hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
      >
        {{ item.label }}
      </router-link>
      <span v-else class="text-slate-900 dark:text-white font-medium">{{ item.label }}</span>
    </template>
  </nav>
</template>
