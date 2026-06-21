<template>
  <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col justify-between border-r border-slate-800 shrink-0 z-20">
    <div>
      <div class="p-6 flex items-center gap-3 border-b border-slate-800">
        <div class="w-10 h-10 rounded-xl bg-brand-600 flex items-center justify-center text-white shadow-lg shadow-brand-600/30">
          <i class="fa-solid fa-cubes-stacked text-xl"></i>
        </div>
        <div>
          <h1 class="text-white font-bold text-base leading-none">ApexERP</h1>
          <span class="text-[10px] text-brand-200/50 font-bold tracking-widest uppercase">DeepSeek Engine</span>
        </div>
      </div>

      <nav class="p-4 space-y-1">
        <SidebarLink to="/dashboard" icon="fa-chart-pie" label="Dashboard" @navigate="emit('navigate')" />
        <SidebarLink to="/pos" icon="fa-cash-register" label="POS de Ventas">
          <span :class="cajaAbierta ? 'bg-emerald-500/20 text-accent-success border-emerald-500/30' : 'bg-rose-500/20 text-accent-danger border-rose-500/30'"
                class="text-[9px] font-bold px-2 py-0.5 rounded-full border">
            {{ cajaAbierta ? 'ABIERTA' : 'CERRADA' }}
          </span>
        </SidebarLink>
        <SidebarLink to="/products" icon="fa-boxes-stacked" label="Productos" @navigate="emit('navigate')" />
        <SidebarLink v-if="auth.isAdmin || auth.isCajero" to="/caja" icon="fa-vault" label="Arqueos y Caja" @navigate="emit('navigate')" />
        <SidebarLink to="/ventas" icon="fa-receipt" label="Ventas" @navigate="emit('navigate')" />
        <SidebarLink to="/calendario" icon="fa-calendar" label="Calendario" @navigate="emit('navigate')" />
        <SidebarLink v-if="auth.isAdmin || auth.isEncargado || auth.isRepositor" to="/compras" icon="fa-truck-ramp-box" label="Compras / Stock" @navigate="emit('navigate')" />
        <SidebarLink v-if="auth.isAdmin || auth.isEncargado || auth.isRepositor" to="/proveedores" icon="fa-industry" label="Proveedores" @navigate="emit('navigate')" />
        <SidebarLink v-if="auth.isAdmin || auth.isEncargado" to="/clientes" icon="fa-address-book" label="Clientes y Ctas. Ctes" @navigate="emit('navigate')" />

        <hr class="border-slate-800 my-2">

        <SidebarLink to="/backups" icon="fa-cloud-arrow-up" label="Respaldos" v-if="auth.isAdmin || auth.isEncargado" muted @navigate="emit('navigate')" />
        <SidebarLink to="/usuarios" icon="fa-users-gear" label="Usuarios" v-if="auth.isAdmin" muted @navigate="emit('navigate')" />
        <SidebarLink to="/reportes" icon="fa-chart-line" label="Reportes" v-if="auth.isAdmin || auth.isEncargado" muted @navigate="emit('navigate')" />
        <SidebarLink to="/licencias" icon="fa-key" label="Licencias" v-if="auth.isAdmin" muted @navigate="emit('navigate')" />
        <SidebarLink to="/auditoria" icon="fa-shield-halved" label="Auditoría" v-if="auth.isAdmin" muted @navigate="emit('navigate')" />
      </nav>
    </div>

    <div class="p-4 border-t border-slate-800">
      <div class="flex items-center gap-3 p-2.5 bg-slate-950/40 rounded-2xl border border-slate-800">
        <div class="w-8 h-8 rounded-xl bg-brand-500 flex items-center justify-center font-bold text-xs text-white uppercase">
          {{ auth.currentUser?.username?.slice(0, 2) || 'AD' }}
        </div>
        <div class="overflow-hidden flex-1">
          <h4 class="text-xs font-semibold text-white truncate">{{ auth.currentUser.nombre || 'Administrador' }}</h4>
          <p class="text-[9px] text-slate-500 uppercase tracking-wider truncate font-semibold">{{ auth.currentUser.rol || 'admin' }}</p>
        </div>
        <button @click="doLogout" title="Cerrar Sesión" class="text-slate-500 hover:text-rose-400 transition ml-2">
          <i class="fa-solid fa-power-off"></i>
        </button>
      </div>
    </div>
  </aside>
</template>

<script setup>
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import SidebarLink from './SidebarLink.vue'

const auth = useAuthStore()
const router = useRouter()
const emit = defineEmits(['navigate'])
defineProps({ cajaAbierta: { type: Boolean, default: false } })

function doLogout() {
  auth.logout()
  router.push('/login')
}
</script>
