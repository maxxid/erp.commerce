<script setup>
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const items = [
  { to: '/pos', icon: 'fa-cash-register', label: 'POS' },
  { to: '/cobrar', icon: 'fa-mobile-screen', label: 'Cobrar' },
  { to: '/cargar-mercaderia', icon: 'fa-box-open', label: 'Cargar', roles: ['admin', 'encargado', 'repositor'] },
  { to: '/control-stock', icon: 'fa-clipboard-list', label: 'Stock', roles: ['admin', 'encargado', 'repositor'] },
  { to: '/caja', icon: 'fa-vault', label: 'Caja', roles: ['admin', 'cajero'] }
]

function allowed(item) {
  if (!item.roles) return true
  const r = (auth.currentUser?.rol || 'admin').toLowerCase()
  return item.roles.includes(r)
}
</script>

<template>
  <nav class="md:hidden fixed bottom-0 inset-x-0 z-40 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-t border-slate-200 dark:border-slate-800 pb-[env(safe-area-inset-bottom)]">
    <div class="flex items-stretch justify-around h-16">
      <router-link
        v-for="item in items.filter(allowed)"
        :key="item.to"
        :to="item.to"
        custom
        v-slot="{ navigate, isActive }"
      >
        <a
          :aria-current="isActive ? 'page' : undefined"
          class="flex-1 min-w-0 flex flex-col items-center justify-center gap-1 px-1 py-2 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand-500/50"
          :class="isActive ? 'text-brand-600 dark:text-brand-400' : 'text-slate-500 dark:text-slate-400'"
          @click.prevent="navigate()"
        >
          <i :class="`fa-solid ${item.icon} text-xl`"></i>
          <span class="text-[10px] font-semibold truncate max-w-full">{{ item.label }}</span>
        </a>
      </router-link>
    </div>
  </nav>
</template>
