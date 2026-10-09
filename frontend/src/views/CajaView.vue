<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Gestión de caja registradora</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton :loading="syncing" :disabled="syncing" variant="secondary" size="sm" @click="syncData">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
        <BaseBadge :variant="cajaStore.abierta ? 'success' : 'danger'" size="sm" dot>
          {{ cajaStore.abierta ? 'Caja Abierta' : 'Caja Cerrada' }}
        </BaseBadge>
        <BaseButton v-if="cajaStore.abierta" :loading="closing" :disabled="closing" variant="danger" size="sm" @click="initCierreCaja">
          <i :class="closing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i>
          {{ closing ? 'Cerrando...' : 'Cerrar Caja' }}
        </BaseButton>
        <BaseButton v-else :loading="opening" :disabled="opening" variant="primary" size="sm" @click="abrirCaja">
          <i :class="opening ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock-open'"></i>
          {{ opening ? 'Abriendo...' : 'Abrir Caja' }}
        </BaseButton>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Cajón (efectivo)</div>
        <div class="text-xl font-bold font-mono-data text-brand-600 mt-1">{{ fc(cajaStore.saldo_actual) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">conteo físico</div>
      </BaseCard>
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Cuentas digitales</div>
        <div class="text-xl font-bold font-mono-data text-indigo-600 mt-1">{{ fc(cajaStore.saldo_cuenta_total) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">
          {{ cuentasConSaldo.length ? cuentasConSaldo.map(c => `${c.label} ${fc(c.saldo)}`).join(' · ') : 'sin saldos' }}
        </div>
      </BaseCard>
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Ingresos del Día</div>
        <div class="text-xl font-bold font-mono-data text-emerald-600 mt-1">{{ fc(ingresosHoy) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">{{ movimientosIngresos }} movimientos</div>
      </BaseCard>
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Egresos del Día</div>
        <div class="text-xl font-bold font-mono-data text-rose-600 mt-1">{{ fc(egresosHoy) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">{{ movimientosEgresos }} movimientos</div>
      </BaseCard>
    </div>

    <div v-if="!cajaStore.abierta" class="bg-amber-50 border border-amber-200 p-4 rounded-2xl text-sm text-amber-700 font-semibold flex items-center gap-2">
      <i class="fa-solid fa-triangle-exclamation"></i>
      La caja está cerrada. Abrila para registrar operaciones.
    </div>

    <BaseCard padding="none">
      <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-slate-900 text-sm">Movimientos del Día</h3>
        <BaseButton v-if="cajaStore.abierta" variant="primary" size="xs" @click="showNuevoMovimiento = true">
          <i class="fa-solid fa-plus"></i> Nuevo Movimiento
        </BaseButton>
      </div>
      <div class="overflow-x-auto">
        <BaseTable v-if="movements.length" :columns="movementColumns" :rows="movements">
          <template #tipo="{ row }">
            <BaseBadge :variant="row.tipo === 'Ingreso' ? 'success' : 'danger'" size="xs">{{ row.tipo }}</BaseBadge>
          </template>
          <template #monto="{ row }">
            <span class="font-mono-data font-bold" :class="row.tipo === 'Ingreso' ? 'text-emerald-600' : 'text-rose-600'">
              {{ row.tipo === 'Ingreso' ? '+' : '-' }} {{ fc(row.monto) }}
            </span>
          </template>
        </BaseTable>
        <EmptyState v-else icon="fa-receipt" title="Sin movimientos" text="No hay movimientos registrados." />
      </div>
    </BaseCard>

    <!-- Historial de Sesiones de Caja -->
    <BaseCard padding="none">
      <div class="px-5 py-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between flex-wrap gap-2">
        <h3 class="font-bold text-slate-900 dark:text-white text-sm">Historial de Caja</h3>
        <div class="flex items-center gap-2 flex-wrap">
          <div class="flex gap-1">
            <button
              v-for="v in vistasHistorial"
              :key="v.valor"
              @click="cambiarVistaHistorial(v.valor)"
              class="px-3 py-1 text-xs font-semibold rounded-lg transition"
              :class="vistaHistorial === v.valor
                ? 'bg-brand-500 text-white'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
            >
              <i :class="v.icone + ' mr-1'"></i>{{ v.label }}
            </button>
          </div>
          <div v-if="vistaHistorial === 'lista'" class="flex gap-1">
            <button
              v-for="filtro in filtrosHistorial"
              :key="filtro.valor"
              @click="cambiarFiltroHistorial(filtro.valor)"
              class="px-3 py-1 text-xs font-semibold rounded-lg transition"
              :class="filtroHistorial === filtro.valor
                ? 'bg-brand-500 text-white'
                : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'"
            >
              {{ filtro.label }}
            </button>
          </div>
          <BaseButton v-if="vistaHistorial === 'lista' && filtroHistorial === 'personalizado'" variant="secondary" size="xs" @click="showFechasPersonalizadas = !showFechasPersonalizadas">
            <i class="fa-solid fa-calendar"></i> Fechas
          </BaseButton>
        </div>
      </div>

      <!-- Filtro de fechas personalizadas -->
      <div v-if="showFechasPersonalizadas && filtroHistorial === 'personalizado' && vistaHistorial === 'lista'" class="px-5 py-3 bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800 flex items-center gap-3">
        <div class="flex items-center gap-2">
          <label class="text-xs font-semibold text-slate-600 dark:text-slate-300">Desde:</label>
          <input
            v-model="fechaInicio"
            type="date"
            class="px-2 py-1 text-xs border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
        </div>
        <div class="flex items-center gap-2">
          <label class="text-xs font-semibold text-slate-600 dark:text-slate-300">Hasta:</label>
          <input
            v-model="fechaFin"
            type="date"
            class="px-2 py-1 text-xs border border-slate-200 dark:border-slate-700 rounded-lg bg-white dark:bg-slate-900 text-slate-900 dark:text-white"
          />
        </div>
        <BaseButton variant="primary" size="xs" @click="fetchReportes">
          <i class="fa-solid fa-search"></i> Buscar
        </BaseButton>
      </div>

      <!-- Calendario (vista mes con semáforo) -->
      <div v-if="vistaHistorial === 'calendario'" class="p-5">
        <div class="flex items-center justify-between mb-4">
          <BaseButton variant="ghost" size="sm" @click="cambiarMesCalendario(-1)">
            <i class="fa-solid fa-chevron-left"></i>
          </BaseButton>
          <span class="font-bold text-slate-900 dark:text-white">{{ tituloMesCalendario }}</span>
          <BaseButton variant="ghost" size="sm" @click="cambiarMesCalendario(1)">
            <i class="fa-solid fa-chevron-right"></i>
          </BaseButton>
        </div>

        <div class="grid grid-cols-7 gap-1.5 text-center mb-1">
          <div v-for="d in diasSemana" :key="d" class="text-[10px] font-bold uppercase text-slate-400 py-1">{{ d }}</div>
        </div>

        <div class="grid grid-cols-7 gap-1.5">
          <div v-for="(celda, idx) in celdasCalendario" :key="idx">
            <button
              v-if="celda.dia"
              :disabled="!celda.tieneOperacion"
              @click="abrirDiaCalendario(celda.fecha)"
              class="w-full text-center rounded-xl border-2 p-2 transition"
              :class="[
                colorDia(celda),
                celda.tieneOperacion && !celda.esHoy ? 'hover:opacity-80 cursor-pointer' : '',
                celda.esHoy ? 'ring-2 ring-brand-500' : ''
              ]"
            >
              <div class="text-sm font-semibold text-slate-800 dark:text-slate-100">{{ celda.dia }}</div>
              <div v-if="celda.n_ventas" class="text-[9px] text-slate-500 dark:text-slate-400 font-mono-data">
                {{ celda.n_ventas }} venta(s)
              </div>
              <div v-if="celda.ingresos" class="text-[9px] text-slate-700 dark:text-slate-300 font-mono-data">
                ${{ fc(celda.ingresos) }}
              </div>
            </button>
            <div v-else class="h-full min-h-[52px] rounded-xl border-2 border-dashed border-slate-100 dark:border-slate-800"></div>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-4 mt-4 text-[11px] text-slate-500 dark:text-slate-400">
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded border-2 bg-emerald-50 border-emerald-500"></span> OK / conciliado</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded border-2 bg-amber-50 border-amber-500"></span> Con diferencias / corregido</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded border-2 bg-red-50 border-red-500"></span> Sin conciliar / error</span>
          <span class="flex items-center gap-1.5"><span class="w-3 h-3 rounded border-2 bg-slate-50 border-slate-300"></span> Sin operaciones</span>
          <BaseBadge v-if="loadingCalendario" variant="info" size="xs">
            <i class="fa-solid fa-circle-notch animate-spin mr-1"></i>Cargando...
          </BaseBadge>
        </div>
      </div>

      <!-- Tabla de sesiones (vista lista) -->
      <div v-if="vistaHistorial === 'lista'">
      <div class="overflow-x-auto">
        <table v-if="sesionesCaja.length" class="w-full text-sm">
          <thead class="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-100 dark:border-slate-800">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Fecha</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Usuario</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Apertura</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Cierre</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Ingresos</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Egresos</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Estado</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Discrepancias</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Conciliación</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sesion in sesionesCaja" :key="sesion.apertura_id" class="border-b border-slate-50 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800/50">
              <td class="px-4 py-3">
                <div class="text-xs font-medium text-slate-900 dark:text-white">{{ formatFecha(sesion.apertura_fecha) }}</div>
                <div class="text-[10px] text-slate-400">{{ formatHora(sesion.apertura_fecha) }}</div>
              </td>
              <td class="px-4 py-3 text-xs text-slate-600 dark:text-slate-300">{{ sesion.apertura_usuario }}</td>
              <td class="px-4 py-3 text-right font-mono-data text-xs text-slate-700 dark:text-slate-300">{{ fc(sesion.apertura_monto) }}</td>
              <td class="px-4 py-3 text-right font-mono-data text-xs" :class="sesion.cierre_monto ? 'text-slate-700 dark:text-slate-300' : 'text-slate-400'">
                {{ sesion.cierre_monto ? fc(sesion.cierre_monto) : '—' }}
              </td>
              <td class="px-4 py-3 text-right font-mono-data text-xs text-emerald-600">{{ fc(sesion.total_ingresos) }}</td>
              <td class="px-4 py-3 text-right font-mono-data text-xs text-rose-600">{{ fc(sesion.total_egresos) }}</td>
              <td class="px-4 py-3 text-center">
                <BaseBadge :variant="sesion.estado === 'cerrada' ? 'success' : 'warning'" size="xs">
                  {{ sesion.estado === 'cerrada' ? 'Cerrada' : 'Abierta' }}
                </BaseBadge>
                <BaseBadge v-if="sesion.fue_automatico" variant="info" size="xs" class="ml-1">Auto</BaseBadge>
              </td>
              <td class="px-4 py-3 text-center">
                <BaseBadge v-if="sesion.tiene_discrepancias" variant="danger" size="xs">
                  <i class="fa-solid fa-triangle-exclamation mr-1"></i>Sí
                </BaseBadge>
                <BaseBadge v-else-if="sesion.cierres_metodo && sesion.cierres_metodo.length" variant="success" size="xs">No</BaseBadge>
                <span v-else class="text-xs text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-center">
                <BaseBadge v-if="sesion.cierre_monto_confirmado != null" variant="success" size="xs">
                  <i class="fa-solid fa-circle-check mr-1"></i>{{ fc(sesion.cierre_monto_confirmado) }}
                </BaseBadge>
                <BaseBadge v-else-if="sesion.fue_automatico" variant="warning" size="xs">Sin confirmar</BaseBadge>
                <span v-else class="text-xs text-slate-400">—</span>
              </td>
              <td class="px-4 py-3 text-center">
                <div class="flex items-center justify-center gap-1">
                  <BaseButton
                    variant="ghost"
                    size="xs"
                    @click="verDetalleSesion(sesion)"
                    :title="'Ver detalle completo de la sesión'"
                    class="relative"
                  >
                    <i class="fa-solid fa-eye"></i>
                    <span class="sr-only">Ver detalle</span>
                  </BaseButton>
                  <BaseButton
                    v-if="esCierreConfirmable(sesion)"
                    variant="primary"
                    size="xs"
                    :title="'Conciliar sesión'"
                    @click="abrirCierreSesion(sesion.cierre_id)"
                  >
                    <i class="fa-solid fa-check"></i>
                  </BaseButton>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <EmptyState v-else icon="fa-clock-rotate-left" title="Sin sesiones" text="No hay sesiones de caja en este período." />
      </div>
      </div>
    </BaseCard>

    <!-- Modal Detalle de Sesión -->
    <BaseModal v-model="showDetalleSesion" title="Detalle de Sesión de Caja" size="xl">
      <div v-if="sesionSeleccionada" class="space-y-4">
        <!-- Header con estado -->
        <div class="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800/50 rounded-xl">
          <div>
            <div class="text-sm font-bold text-slate-900 dark:text-white">
              Sesión {{ sesionSeleccionada.apertura_id ? '#' + sesionSeleccionada.apertura_id : '' }}
            </div>
            <div class="text-xs text-slate-500 dark:text-slate-400">
              {{ formatFechaDia(sesionSeleccionada.apertura_fecha?.split('T')[0] || '') }}
            </div>
          </div>
          <div class="flex items-center gap-2">
            <BaseBadge v-if="sesionSeleccionada.fue_automatico" variant="info" size="sm">
              <i class="fa-solid fa-robot mr-1"></i>Automático
            </BaseBadge>
            <BaseBadge v-else variant="default" size="sm">Manual</BaseBadge>
            <BaseBadge v-if="sesionSeleccionada.cierre_monto_confirmado != null" variant="success" size="sm">
              <i class="fa-solid fa-circle-check mr-1"></i>Conciliado
            </BaseBadge>
            <BaseBadge v-else-if="sesionSeleccionada.fue_automatico" variant="warning" size="sm">Pendiente</BaseBadge>
          </div>
        </div>

        <!-- Info Apertura / Cierre -->
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">Apertura</div>
            <div class="space-y-1">
              <div class="flex justify-between">
                <span class="text-xs text-slate-500">Fecha</span>
                <span class="text-sm font-medium font-mono-data">{{ formatFechaHora(sesionSeleccionada.apertura_fecha) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-xs text-slate-500">Usuario</span>
                <span class="text-sm">{{ sesionSeleccionada.apertura_usuario || '—' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-xs text-slate-500">Monto inicial (cajón)</span>
                <span class="text-sm font-bold font-mono-data text-brand-600">{{ fc(sesionSeleccionada.apertura_monto) }}</span>
              </div>
              <div v-if="sesionSeleccionada.apertura_cuentas" class="flex justify-between">
                <span class="text-xs text-slate-500">Cuentas digitales</span>
                <span class="text-sm font-bold font-mono-data text-indigo-600">+ {{ fc(sesionSeleccionada.apertura_cuentas) }}</span>
              </div>
              <div v-if="sesionSeleccionada.apertura_descripcion" class="flex justify-between">
                <span class="text-xs text-slate-500">Descripción</span>
                <span class="text-sm text-slate-600">{{ sesionSeleccionada.apertura_descripcion }}</span>
              </div>
            </div>
          </div>
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-2">Cierre</div>
            <div class="space-y-1">
              <div class="flex justify-between">
                <span class="text-xs text-slate-500">Fecha</span>
                <span class="text-sm font-medium font-mono-data">{{ formatFechaHora(sesionSeleccionada.cierre_fecha) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-xs text-slate-500">Usuario</span>
                <span class="text-sm">{{ sesionSeleccionada.cierre_usuario || '—' }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-xs text-slate-500">Monto del sistema</span>
                <span class="text-sm font-bold font-mono-data text-brand-600">{{ fc(sesionSeleccionada.cierre_monto) }}</span>
              </div>
              <div v-if="sesionSeleccionada.cierre_monto_confirmado != null" class="flex justify-between border-t pt-2 mt-2">
                <span class="text-xs text-emerald-600 font-semibold">Conciliado</span>
                <span class="text-sm font-bold font-mono-data text-emerald-700">{{ fc(sesionSeleccionada.cierre_monto_confirmado) }}</span>
              </div>
              <div v-if="sesionSeleccionada.cierre_monto_confirmado != null" class="flex justify-between">
                <span class="text-xs text-slate-500">Confirmado por</span>
                <span class="text-sm">{{ sesionSeleccionada.cierre_confirmado_por || '—' }}</span>
              </div>
              <div v-if="sesionSeleccionada.cierre_monto_confirmado != null" class="flex justify-between">
                <span class="text-xs text-slate-500">Confirmado el</span>
                <span class="text-sm">{{ formatFechaHora(sesionSeleccionada.cierre_confirmado_at) }}</span>
              </div>
              <div v-if="sesionSeleccionada.cierre_comentario" class="flex justify-between">
                <span class="text-xs text-slate-500">Comentario</span>
                <span class="text-sm text-slate-600">{{ sesionSeleccionada.cierre_comentario }}</span>
              </div>
              <div v-else-if="sesionSeleccionada.fue_automatico" class="mt-3 pt-2 border-t">
                <BaseButton variant="primary" size="sm" class="w-full" @click="abrirCierreSesion(sesionSeleccionada.cierre_id)">
                  <i class="fa-solid fa-check mr-1"></i>Conciliar esta sesión
                </BaseButton>
              </div>
            </div>
          </div>
        </div>

        <!-- Resumen financiero -->
        <div class="grid grid-cols-4 gap-3">
          <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-3 text-center">
            <div class="text-[10px] uppercase tracking-wider text-emerald-600 font-semibold">Ingresos</div>
            <div class="font-mono-data font-bold text-lg text-emerald-700">{{ fc(sesionSeleccionada.total_ingresos || sesionSeleccionada.ingresos) }}</div>
          </div>
          <div class="bg-rose-50 dark:bg-rose-900/20 rounded-xl p-3 text-center">
            <div class="text-[10px] uppercase tracking-wider text-rose-600 font-semibold">Egresos</div>
            <div class="font-mono-data font-bold text-lg text-rose-700">{{ fc(sesionSeleccionada.total_egresos || sesionSeleccionada.egresos) }}</div>
          </div>
          <div class="bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-3 text-center">
            <div class="text-[10px] uppercase tracking-wider text-indigo-600 font-semibold">Cuentas digitales</div>
            <div class="font-mono-data font-bold text-lg text-indigo-700">{{ fc(sesionSeleccionada.apertura_cuentas || 0) }}</div>
          </div>
          <div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-3 text-center">
            <div class="text-[10px] uppercase tracking-wider text-brand-600 font-semibold">Saldo Final</div>
            <div class="font-mono-data font-bold text-lg text-brand-700">{{ fc(sesionSeleccionada.saldo_final) }}</div>
          </div>
        </div>

        <!-- Cierres por método (arqueo) -->
        <div v-if="sesionSeleccionada.cierres_metodo && sesionSeleccionada.cierres_metodo.length" class="space-y-2">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-calculator text-brand-600"></i>Arqueo por Método
          </h4>
          <div class="space-y-2">
            <div v-for="cierre in sesionSeleccionada.cierres_metodo" :key="cierre.medio_pago" class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-semibold text-slate-700 dark:text-slate-200 capitalize">{{ cierre.medio_pago }}</span>
                <BaseBadge :variant="Math.abs(cierre.diferencia) > 0.01 ? 'danger' : 'success'" size="sm">
                  {{ Math.abs(cierre.diferencia) > 0.01 ? 'Discrepancia' : 'OK' }}
                </BaseBadge>
              </div>
              <div class="grid grid-cols-4 gap-2 text-xs">
                <div class="bg-white dark:bg-slate-900 p-2 rounded">
                  <span class="text-slate-500">Esperado:</span>
                  <span class="font-mono-data font-semibold ml-1">{{ fc(cierre.esperado) }}</span>
                </div>
                <div class="bg-white dark:bg-slate-900 p-2 rounded">
                  <span class="text-slate-500">Real:</span>
                  <span class="font-mono-data font-semibold ml-1">{{ fc(cierre.monto_real) }}</span>
                </div>
                <div class="bg-white dark:bg-slate-900 p-2 rounded">
                  <span class="text-slate-500">Diferencia:</span>
                  <span class="font-mono-data font-semibold ml-1" :class="cierre.diferencia >= 0 ? 'text-emerald-600' : 'text-rose-600'">
                    {{ cierre.diferencia >= 0 ? '+' : '' }}{{ fc(cierre.diferencia) }}
                  </span>
                </div>
                <div class="bg-white dark:bg-slate-900 p-2 rounded">
                  <span class="text-slate-500">Usuario:</span>
                  <span class="font-mono-data font-semibold ml-1">{{ cierre.usuario || '—' }}</span>
                </div>
              </div>
              <div v-if="cierre.descripcion" class="text-[10px] text-slate-500 mt-2 italic">{{ cierre.descripcion }}</div>
            </div>
          </div>
        </div>

        <!-- Retiros / Extracciones de cierre -->
        <div v-if="sesionSeleccionada.retiros && sesionSeleccionada.retiros.length" class="space-y-2">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-money-bill-wave text-rose-600"></i>Extracciones de cierre
          </h4>
          <div class="space-y-1">
            <div v-for="r in sesionSeleccionada.retiros" :key="r.id" class="bg-rose-50 dark:bg-rose-900/20 rounded-lg p-2">
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <BaseBadge :variant="r.tipo === 'pago_proveedor' ? 'warning' : 'danger'" size="xs">
                    {{ r.tipo === 'pago_proveedor' ? 'Pago proveedor' : 'Extracción' }}
                  </BaseBadge>
                  <span class="text-xs text-slate-600">{{ formatHora(r.fecha) }}</span>
                  <span class="text-xs text-slate-400">{{ r.proveedor_id ? 'Proveedor #' + r.proveedor_id : r.descripcion }}</span>
                </div>
                <span class="font-mono-data font-bold text-rose-600">-{{ fc(r.monto) }}</span>
              </div>
            </div>
            <div class="flex justify-end text-xs">
              <span class="text-rose-600">Total: {{ fc(sesionSeleccionada.retiros.reduce((s, r) => s + (r.monto || 0), 0)) }}</span>
            </div>
          </div>
        </div>

        <!-- Movimientos (ingresos/egresos) -->
        <div v-if="(sesionSeleccionada.ingresos && sesionSeleccionada.ingresos.length) || (sesionSeleccionada.egresos && sesionSeleccionada.egresos.length)" class="space-y-2">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-list text-brand-600"></i>Movimientos
          </h4>
          <div class="max-h-60 overflow-y-auto space-y-1">
            <div v-for="ing in (sesionSeleccionada.ingresos || [])" :key="'ing-'+ing.id" class="flex items-center justify-between bg-emerald-50 dark:bg-emerald-900/20 rounded-lg px-3 py-2">
              <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-slate-700 dark:text-slate-200 truncate">{{ ing.descripcion || 'Ingreso' }}</div>
                <div class="text-[10px] text-slate-500">{{ formatHora(ing.fecha) }} · {{ ing.medio_pago }}</div>
              </div>
              <span class="font-mono-data font-bold text-xs text-emerald-600">+{{ fc(ing.monto) }}</span>
            </div>
            <div v-for="egr in (sesionSeleccionada.egresos || [])" :key="'egr-'+egr.id" class="flex items-center justify-between bg-rose-50 dark:bg-rose-900/20 rounded-lg px-3 py-2">
              <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-slate-700 dark:text-slate-200 truncate">{{ egr.descripcion || 'Egreso' }}</div>
                <div class="text-[10px] text-slate-500">{{ formatHora(egr.fecha) }}</div>
              </div>
              <span class="font-mono-data font-bold text-xs text-rose-600">-{{ fc(egr.monto) }}</span>
            </div>
          </div>
        </div>

        <!-- Ventas / Tickets de la sesión -->
        <div v-if="sesionSeleccionada.tickets && sesionSeleccionada.tickets.length" class="space-y-2">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <i class="fa-solid fa-receipt text-brand-600"></i>Ventas ({{ sesionSeleccionada.tickets.length }})
          </h4>
          <div class="max-h-60 overflow-y-auto space-y-1">
            <button
              v-for="t in sesionSeleccionada.tickets"
              :key="t.id"
              @click="verTicketDetalle(t.id)"
              class="w-full flex items-center justify-between bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 hover:border-brand-400 transition text-left"
            >
              <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">{{ t.numero }} <span class="text-slate-400 font-normal">· {{ t.cliente || 'Cliente ocasional' }}</span></div>
                <div class="text-[10px] text-slate-500">{{ formatFechaHora(t.fecha) }} · {{ t.medio_pago }} · {{ t.vendedor }}</div>
              </div>
              <span class="font-mono-data font-bold text-xs text-slate-900 dark:text-white ml-2">${{ fc(t.total) }}</span>
              <i class="fa-solid fa-chevron-right text-[10px] text-slate-400 ml-2"></i>
            </button>
          </div>
        </div>

        <!-- Estado vacío si no hay datos extendidos -->
        <div v-else class="text-center py-8 text-slate-400">
          <i class="fa-solid fa-info-circle text-xl mb-2"></i>
          <p class="text-sm">No hay datos extendidos para esta sesión.</p>
          <p class="text-[10px] mt-1">Usa el Historial → Calendario → Día para ver el desglose completo.</p>
        </div>
      </div>
      <div v-else class="flex items-center justify-center py-12 text-slate-400">
        <i class="fa-solid fa-circle-notch animate-spin mr-2"></i> Cargando...
      </div>
    </BaseModal>

    <!-- Modal Detalle del Día (vista calendario) -->
    <BaseModal v-model="showDetalleDia" title="Detalle del Día" size="lg">
      <div v-if="detalleDia" class="space-y-4">
        <div class="flex items-center justify-between">
          <div>
            <div class="text-xs text-slate-500 dark:text-slate-400">{{ formatFechaDia(detalleDia.fecha) }}</div>
            <div class="text-sm font-semibold text-slate-900 dark:text-white">
              {{ detalleDia.n_ventas }} venta(s) · <span class="font-mono-data">{{ fc(detalleDia.total_ingresos) }}</span> ingresos
            </div>
          </div>
          <BaseBadge :variant="badgeColorDia(estadoDiaActual() || 'sin_operacion')" size="sm">
            {{ labelColorDia(estadoDiaActual() || 'sin_operacion') }}
          </BaseBadge>
        </div>

        <!-- Mini dashboards por medio de pago -->
        <div class="grid grid-cols-2 md:grid-cols-3 gap-3">
          <div v-for="(monto, metodo) in detalleDia.desglose" :key="metodo" class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">{{ MEDIO_LABELS[metodo] || metodo }}</div>
            <div class="font-mono-data font-bold text-lg text-slate-900 dark:text-white">{{ fc(monto) }}</div>
          </div>
          <div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-brand-600 font-semibold">Apertura cajón</div>
            <div class="font-mono-data font-bold text-lg text-brand-700">{{ fc(detalleDia.apertura) }}</div>
          </div>
          <div v-if="detalleDia.total_egresos" class="bg-rose-50 dark:bg-rose-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-rose-600 font-semibold">Egresos</div>
            <div class="font-mono-data font-bold text-lg text-rose-700">{{ fc(detalleDia.total_egresos) }}</div>
          </div>
          <div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-emerald-600 font-semibold">Saldo Final</div>
            <div class="font-mono-data font-bold text-lg text-emerald-700">{{ fc(detalleDia.saldo_final) }}</div>
          </div>
          <div v-for="(saldo, cuenta) in detalleDia.saldos_cuentas || {}" :key="cuenta" class="bg-indigo-50 dark:bg-indigo-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-indigo-500 font-semibold">{{ MEDIO_LABELS[cuenta] || cuenta }}</div>
            <div class="font-mono-data font-bold text-lg text-indigo-700 dark:text-indigo-300">{{ fc(saldo) }}</div>
            <div class="text-[9px] text-indigo-400">saldo final de la cuenta</div>
          </div>
        </div>

        <!-- Cierres -->
        <div v-if="detalleDia.cierres && detalleDia.cierres.length">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white mb-2">Cierres</h4>
          <div class="space-y-2">
            <div v-for="cierre in detalleDia.cierres" :key="cierre.id" class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
              <div class="flex items-center justify-between flex-wrap gap-2">
                <div class="flex items-center gap-2">
                  <BaseBadge v-if="cierre.fue_automatico" variant="info" size="xs">Automático</BaseBadge>
                  <BaseBadge v-else variant="default" size="xs">Manual</BaseBadge>
                  <span class="text-xs text-slate-500">{{ formatFechaHora(cierre.created_at) }}</span>
                  <span class="text-xs text-slate-400">por {{ cierre.usuario_nombre }}</span>
                </div>
                <BaseButton v-if="cierre.monto_confirmado == null && cierre.fue_automatico" :loading="cargandoArqueoSesion" variant="primary" size="xs"
                  @click="abrirCierreSesion(cierre.id)">
                  <i class="fa-solid fa-check mr-1"></i>Conciliar sesión
                </BaseButton>
                <BaseBadge v-else-if="cierre.monto_confirmado != null" variant="success" size="xs">
                  <i class="fa-solid fa-circle-check mr-1"></i>Confirmado {{ fc(cierre.monto_confirmado) }}
                  <span v-if="cierre.confirmado_por" class="ml-1">por {{ cierre.confirmado_por }}</span>
                </BaseBadge>
                <span v-else class="text-[10px] text-slate-400">cerrada con arqueo</span>
              </div>
              <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs mt-2">
                <div><span class="text-slate-400">Sistema:</span> <span class="font-mono-data font-semibold">{{ fc(cierre.monto_esperado) }}</span></div>
                <div><span class="text-slate-400">Confirmado:</span> <span class="font-mono-data font-semibold">{{ cierre.monto_confirmado != null ? fc(cierre.monto_confirmado) : '—' }}</span></div>
                <div><span class="text-slate-400">Diferencia:</span>
                  <span v-if="cierre.diferencia != null" class="font-mono-data font-semibold" :class="cierre.diferencia === 0 ? 'text-emerald-600' : cierre.diferencia > 0 ? 'text-amber-600' : 'text-rose-600'">
                    {{ cierre.diferencia > 0 ? '+' : '' }}{{ fc(cierre.diferencia) }}
                  </span>
                  <span v-else class="text-slate-400">—</span>
                </div>
                <div v-if="cierre.comentario_concil" class="col-span-2 text-[10px] text-slate-500 italic">{{ cierre.comentario_concil }}</div>
              </div>
              <div class="text-[10px] text-slate-400 mt-1 italic">{{ cierre.descripcion }}</div>
            </div>
          </div>
        </div>

        <!-- Tickets / ventas del día -->
        <div v-if="detalleDia.tickets && detalleDia.tickets.length">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white mb-2">Ventas del día</h4>
          <div class="max-h-64 overflow-y-auto space-y-1">
            <button
              v-for="t in detalleDia.tickets"
              :key="t.id"
              @click="verTicketDetalle(t.id)"
              class="w-full flex items-center justify-between bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg px-3 py-2 hover:border-brand-400 transition text-left"
            >
              <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-slate-800 dark:text-slate-200">{{ t.numero }} <span class="text-slate-400 font-normal">· {{ t.cliente || 'Cliente ocasional' }}</span></div>
                <div class="text-[10px] text-slate-500">{{ formatFechaHora(t.fecha) }} · {{ t.medio_pago }} · {{ t.vendedor }}</div>
              </div>
              <span class="font-mono-data font-bold text-xs text-slate-900 dark:text-white ml-2">${{ fc(t.total) }}</span>
              <i class="fa-solid fa-chevron-right text-[10px] text-slate-400 ml-2"></i>
            </button>
          </div>
        </div>
        <EmptyState v-else icon="fa-receipt" title="Sin ventas" text="No hubo ventas en esta jornada." />
      </div>
    </BaseModal>

    <!-- Modal Detalle de Venta -->
    <BaseModal v-model="showTicketDetalle" title="Detalle de Venta" size="lg">
      <div v-if="ticketSeleccionado" class="space-y-4">
        <div class="flex items-center justify-between flex-wrap gap-2">
          <div>
            <div class="text-lg font-bold text-slate-900 dark:text-white">{{ ticketSeleccionado.numero }}</div>
            <div class="text-xs text-slate-500">{{ formatFechaHora(ticketSeleccionado.fecha || ticketSeleccionado.created_at) }} · {{ ticketSeleccionado.medio_pago }}</div>
            <div class="text-xs text-slate-400">Vendedor: {{ ticketSeleccionado.usuario?.nombre || ticketSeleccionado.vendedor || '—' }} · Cliente: {{ ticketSeleccionado.cliente_nombre || ticketSeleccionado.cliente || 'Ocasional' }}</div>
          </div>
          <div class="text-right">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Total</div>
            <div class="font-mono-data font-bold text-2xl text-brand-600">{{ fc(ticketSeleccionado.total) }}</div>
          </div>
        </div>

        <div v-if="ticketSeleccionado.items && ticketSeleccionado.items.length">
          <h4 class="text-sm font-bold text-slate-900 dark:text-white mb-2">Artículos</h4>
          <div class="space-y-1 max-h-72 overflow-y-auto">
            <div v-for="item in ticketSeleccionado.items" :key="item.id" class="flex items-center justify-between bg-slate-50 dark:bg-slate-800/50 rounded-lg px-3 py-2">
              <div class="flex-1 min-w-0">
                <div class="text-xs font-medium text-slate-800 dark:text-slate-200 truncate">{{ item.producto_nombre || item.producto?.nombre || `Producto #${item.producto_id}` }}</div>
                <div class="text-[10px] text-slate-500">{{ item.por_kilo ? item.peso + ' kg' : item.cantidad + ' u' }} × {{ fc(item.precio_unitario) }}</div>
              </div>
              <span class="font-mono-data font-bold text-xs text-slate-900 dark:text-white">{{ fc(item.subtotal) }}</span>
            </div>
          </div>
        </div>

        <div v-if="ticketSeleccionado.estado" class="flex justify-end">
          <BaseBadge :variant="ticketSeleccionado.estado === 'confirmada' ? 'success' : 'warning'" size="sm">{{ ticketSeleccionado.estado }}</BaseBadge>
        </div>
      </div>
      <div v-else class="flex items-center justify-center py-12 text-slate-400">
        <i class="fa-solid fa-circle-notch animate-spin mr-2"></i> Cargando...
      </div>
    </BaseModal>

    <!-- Modal Arqueo de sesión (cierre diferido de una sesión auto-cerrada) -->
    <BaseModal v-model="showCierreSesion" title="Conciliar sesión de caja" size="lg" :hide-footer="true">
      <div v-if="arqueoSesion" class="space-y-5">
        <div v-if="arqueoSesion.fue_automatico" class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3 text-xs text-amber-700 dark:text-amber-300">
          <i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i>
          Esta sesión se cerró <b>automáticamente</b> por cambio de día con el monto del sistema ({{ fc(arqueoSesion.monto_esperado) }}). Contá el efectivo y las cuentas digitales para dejarla conciliada.
        </div>
        <div v-else-if="arqueoSesion.confirmado" class="bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 rounded-xl p-3 text-xs text-emerald-700 dark:text-emerald-300">
          <i class="fa-solid fa-circle-check text-emerald-500 mr-1"></i>
          Esta sesión ya fue conciliada. Solo se puede consultar.
        </div>

        <div class="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Apertura</div>
            <div class="font-mono-data font-bold text-slate-900 dark:text-white">{{ fc(arqueoSesion.apertura_monto) }}</div>
            <div class="text-[10px] text-slate-400">{{ arqueoSesion.apertura_fecha ? formatFechaHora(arqueoSesion.apertura_fecha) : '—' }}</div>
          </div>
          <div class="bg-rose-50 dark:bg-rose-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-rose-400 font-semibold">Extracciones</div>
            <div class="font-mono-data font-bold text-rose-600 dark:text-rose-300">{{ fc(arqueoSesion.total_retiros) }}</div>
            <div class="text-[10px] text-rose-400">ya descontadas del cajón</div>
          </div>
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Cierre</div>
            <div class="font-mono-data font-bold text-slate-900 dark:text-white">{{ fc(arqueoSesion.confirmado ? arqueoSesion.monto_confirmado : arqueoSesion.monto_esperado) }}</div>
            <div class="text-[10px] text-slate-400">{{ arqueoSesion.cierre_fecha ? formatFechaHora(arqueoSesion.cierre_fecha) : '—' }}</div>
          </div>
          <div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-brand-400 font-semibold">Saldo esperado</div>
            <div class="font-mono-data font-bold text-brand-600 dark:text-brand-300">{{ fc(arqueoSesion.saldo_esperado) }}</div>
            <div class="text-[10px] text-brand-400">cajón + cuentas</div>
          </div>
        </div>

        <div v-if="cargandoArqueoSesion" class="flex items-center justify-center py-10 text-slate-400 text-sm">
          <i class="fa-solid fa-circle-notch animate-spin mr-2"></i> Cargando arqueo...
        </div>

        <template v-else>
          <ArqueoMedios
            :filas="filasCierreSesion"
            :retiros="retirosCierreSesion"
            :disabled="conciliandoSesion || arqueoSesion.confirmado"
            :guardando-retiro="guardandoRetiroSesion"
            :guardando-pago="guardandoPago"
            :proveedores="proveedores"
            :bloquear-cerrados="false"
            :cierre-id="cierreSesionId"
            @contar="abrirContadorBilletes('arqueo', $event)"
            @contar-medio="abrirContadorTransferencias($event)"
            @agregar-retiro="agregarRetiroSesion"
            @borrar-retiro="borrarRetiro($event, true)"
            @pago-proveedor="registrarPagoProveedor($event, cierreSesionId)"
          />

          <div class="bg-slate-100 dark:bg-slate-800 rounded-xl p-4 space-y-2">
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Total esperado</span>
              <span class="font-mono-data font-bold text-slate-900 dark:text-white">{{ fc(totalEsperadoSesion) }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Total real cargado</span>
              <span class="font-mono-data font-bold text-lg" :class="totalRealSesion === totalEsperadoSesion ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'">{{ fc(totalRealSesion) }}</span>
            </div>
            <div v-if="totalRealSesion !== totalEsperadoSesion" class="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
              <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Diferencia</span>
              <span class="font-mono-data font-bold text-lg" :class="diferenciaTotalSesion >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">
                {{ diferenciaTotalSesion >= 0 ? '+' : '' }}{{ fc(diferenciaTotalSesion) }}
              </span>
            </div>
          </div>

          <div>
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Observaciones de la conciliación</label>
            <input
              v-model="comentarioCierreSesion"
              type="text"
              placeholder="Observaciones generales del cierre de la sesión..."
              class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              :disabled="conciliandoSesion"
            />
          </div>
        </template>

        <div class="flex gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" :disabled="conciliandoSesion" @click="cerrarModalCierreSesion">Cerrar</BaseButton>
          <BaseButton v-if="!arqueoSesion.confirmado" variant="primary" class="flex-1" :loading="conciliandoSesion" :disabled="conciliandoSesion || cargandoArqueoSesion" @click="conciliarSesion">
            <i class="fa-solid fa-check"></i> {{ conciliandoSesion ? 'Conciliando...' : 'Conciliar sesión' }}
          </BaseButton>
        </div>
      </div>
      <div v-else-if="cargandoArqueoSesion" class="flex items-center justify-center py-12 text-slate-400">
        <i class="fa-solid fa-circle-notch animate-spin mr-2"></i> Cargando...
      </div>
    </BaseModal>


    <!-- Modal Nuevo Movimiento -->
    <BaseModal v-model="showNuevoMovimiento" title="Nuevo Movimiento" size="md">
      <div class="space-y-4">
        <BaseSelect v-model="nuevoMovimiento.tipo" label="Tipo" :options="[{ value: 'Ingreso', label: 'Ingreso' }, { value: 'Egreso', label: 'Egreso' }]" />
        <BaseInput v-model.number="nuevoMovimiento.monto" label="Monto" type="number" placeholder="0.00" input-class="font-mono-data" />
        <BaseSelect v-model="nuevoMovimiento.metodo" label="Sale de / entra a" :options="metodosMovimiento" />
        <p class="text-[10px] text-slate-400 -mt-2">
          Para un egreso indicá de qué cuenta salió el dinero (ej: una transferencia de MercadoPago al banco).
        </p>
        <BaseInput v-model="nuevoMovimiento.comentario" label="Comentario" placeholder="Descripción del movimiento" />
        <div class="flex gap-2 pt-2">
          <BaseButton variant="secondary" size="sm" block @click="showNuevoMovimiento = false">Cancelar</BaseButton>
          <BaseButton :loading="saving" :disabled="saving" variant="primary" size="sm" block @click="registrarMovimiento">
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ saving ? 'Guardando...' : 'Registrar' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal Apertura de Caja -->
    <BaseModal v-model="showAperturaModal" title="Apertura de Caja" size="md" :hide-footer="true">
      <div class="space-y-5">
        <div v-if="cajaStore.ultimoCierre && cajaStore.ultimoCierre.monto > 0" class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-2">
            <i class="fa-solid fa-info-circle text-amber-500"></i>
            <span class="font-semibold text-amber-700 dark:text-amber-300 text-sm">Último cierre detectado</span>
            <BaseBadge v-if="cajaStore.ultimoCierre.fue_automatico" variant="warning" size="xs">Automático</BaseBadge>
          </div>
          <p class="text-xs text-amber-600 dark:text-amber-400 mb-2">
            Monto del último cierre: <span class="font-mono-data font-bold">{{ fc(cajaStore.ultimoCierre.monto) }}</span>
          </p>
          <p v-if="cajaStore.ultimoCierre.fecha_local_str" class="text-[10px] text-amber-500 dark:text-amber-400">
            Fecha: {{ cajaStore.ultimoCierre.fecha_local_str }}
          </p>
        </div>

        <div class="space-y-4">
          <div>
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Monto inicial sugerido</label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">$</span>
              <input
                v-model.number="aperturaForm.monto_inicial"
                type="number"
                min="0"
                step="100"
                class="w-full pl-7 pr-3 py-2.5 text-lg font-mono-data font-bold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                placeholder="0.00"
              />
            </div>
            <div class="flex items-center justify-between gap-2 mt-1">
              <p class="text-[10px] text-slate-400">Monto con el que inicia la caja (efectivo)</p>
              <BaseButton variant="ghost" size="xs" @click="abrirContadorBilletes('apertura')">
                <i class="fa-solid fa-money-bill-wave"></i> Contar billetes
              </BaseButton>
            </div>
          </div>

          <div class="border-t border-slate-200 dark:border-slate-700 pt-4">
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Retiro de efectivo (opcional)</label>
            <div class="relative">
              <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">$</span>
              <input
                v-model.number="aperturaForm.monto_retiro"
                type="number"
                min="0"
                step="100"
                class="w-full pl-7 pr-3 py-2.5 text-lg font-mono-data font-bold bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                placeholder="0.00"
              />
            </div>
            <p class="text-[10px] text-slate-400 mt-1">Efectivo que se aparta/retira al abrir (ej: fondo para cambio)</p>
          </div>

          <div v-if="aperturaForm.monto_retiro > 0">
            <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Motivo del retiro</label>
            <input
              v-model="aperturaForm.motivo_retiro"
              type="text"
              class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              placeholder="Ej: Fondo para cambio, Retiro de efectivo..."
            />
          </div>

          <div class="border-t border-slate-200 dark:border-slate-700 pt-4">
            <div class="flex items-center gap-2 mb-1">
              <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Saldos iniciales de cuentas digitales</label>
              <BaseButton variant="ghost" size="xs" @click="abrirCuentasDigitales = !abrirCuentasDigitales">
                <i :class="abrirCuentasDigitales ? 'fa-solid fa-chevron-up' : 'fa-solid fa-chevron-down'"></i>
                {{ abrirCuentasDigitales ? 'Ocultar' : 'Mostrar' }}
              </BaseButton>
            </div>
            <p class="text-[10px] text-slate-400 mb-2">
              Cargá el saldo que muestra hoy cada app. Arranca en 0: se anota lo que ves
              ahora, no lo que quedó ayer.
            </p>
            <div v-if="abrirCuentasDigitales" class="space-y-2">
              <div v-for="cuenta in cuentasDigitales" :key="cuenta.valor" class="flex items-center gap-2">
                <div class="flex-1">
                  <div class="flex items-center justify-between gap-2">
                    <label class="text-xs text-slate-600 dark:text-slate-300">{{ cuenta.label }}</label>
                    <!-- El saldo de ayer, a la vista pero no cargado. -->
                    <button
                      v-if="saldosUltimosCuentas[cuenta.valor] > 0"
                      type="button"
                      class="text-[10px] text-slate-400 hover:text-brand-600 dark:hover:text-brand-400 transition shrink-0"
                      title="Cargar el saldo con el que quedó en el último cierre"
                      @click="aperturaForm.saldos_cuentas[cuenta.valor] = saldosUltimosCuentas[cuenta.valor]"
                    >
                      ayer {{ fc(saldosUltimosCuentas[cuenta.valor]) }}
                    </button>
                  </div>
                  <div class="relative mt-0.5">
                    <span class="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 font-semibold">$</span>
                    <input
                      v-model.number="aperturaForm.saldos_cuentas[cuenta.valor]"
                      type="number"
                      min="0"
                      step="0.01"
                      inputmode="decimal"
                      class="w-full pl-7 pr-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                      placeholder="0.00"
                    />
                  </div>
                </div>
              </div>
            </div>
            <p v-else-if="totalSaldosCuentasApertura > 0" class="text-[10px] text-slate-500">
              Cuentas a controlar: {{ cuentasConSaldoApertura }} — total {{ fc(totalSaldosCuentasApertura) }}
            </p>
          </div>

          <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Monto final de apertura (cajón)</span>
              <span class="font-mono-data font-bold text-2xl text-brand-600 dark:text-brand-400">{{ fc(montoFinalApertura) }}</span>
            </div>
            <p v-if="aperturaForm.monto_retiro > 0" class="text-[10px] text-slate-400 mt-1 text-right">
              {{ fc(aperturaForm.monto_inicial) }} - {{ fc(aperturaForm.monto_retiro) }} = {{ fc(montoFinalApertura) }}
            </p>
            <div v-if="totalSaldosCuentasApertura > 0" class="flex items-center justify-between mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
              <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Total a controlar (cajón + cuentas)</span>
              <span class="font-mono-data font-bold text-lg text-indigo-600 dark:text-indigo-400">{{ fc(montoFinalApertura + totalSaldosCuentasApertura) }}</span>
            </div>
          </div>
        </div>

        <div class="flex gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" :disabled="opening" @click="showAperturaModal = false">
            Cancelar
          </BaseButton>
          <BaseButton variant="primary" class="flex-1" :loading="opening" :disabled="opening" @click="confirmarAperturaCaja">
            <i :class="opening ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock-open'"></i>
            {{ opening ? 'Abriendo...' : 'Abrir Caja' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal Cierre de Caja -->
    <BaseModal v-model="showCierreModal" title="Cierre de Caja" size="lg" :hide-footer="true">
      <div class="space-y-5">
        <div v-if="carritoStore.carritosConItems.length" class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3">
          <div class="flex items-center gap-2 mb-1">
            <i class="fa-solid fa-triangle-exclamation text-red-600 dark:text-red-400"></i>
            <span class="font-semibold text-red-700 dark:text-red-300 text-sm">Carritos sin cobrar</span>
          </div>
          <ul class="text-xs text-red-700 dark:text-red-300 space-y-0.5">
            <li v-for="c in carritoStore.carritosConItems" :key="c.id">— {{ c.nombre }}: {{ c.items.length }} producto(s) por {{ fc(c.total) }}</li>
          </ul>
          <p class="text-[10px] text-red-600 dark:text-red-400 mt-1.5">
            Si cerrás la caja sin cobrarlos quedan como huérfanos en la auditoría.
          </p>
        </div>

        <div class="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-2">
            <i class="fa-solid fa-triangle-exclamation text-brand-500"></i>
            <span class="font-semibold text-brand-700 dark:text-brand-300 text-sm">Confrontá los montos</span>
          </div>
          <p class="text-xs text-brand-600 dark:text-brand-400">
            Cargá el monto real de cada medio. El efectivo se cuenta en el cajón y las cuentas digitales con el saldo que muestra la app: cada uno se cuadra por separado, sin compensar uno con otro.
          </p>
        </div>

        <ArqueoMedios
          :filas="metodosArqueo"
          :retiros="retirosCierreActual"
          :disabled="closing"
          :guardando-retiro="guardandoRetiroActual"
          :guardando-pago="guardandoPago"
          :proveedores="proveedores"
          @contar="abrirContadorBilletes('arqueo', $event)"
          @contar-medio="abrirContadorTransferencias($event)"
          @agregar-retiro="agregarRetiroCierreActual"
          @borrar-retiro="borrarRetiro($event, false)"
          @pago-proveedor="registrarPagoProveedor($event)"
        />

        <!-- Advertencia métodos pendientes -->
        <div v-if="hayPendientes" class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3">
          <div class="flex items-center gap-2 mb-2">
            <i class="fa-solid fa-triangle-exclamation text-amber-500"></i>
            <span class="font-semibold text-amber-700 dark:text-amber-300 text-sm">Faltan montos para cerrar</span>
          </div>
          <p class="text-xs text-amber-600 dark:text-amber-400 mb-2">
            Ingresá el monto real en cada método para poder cerrar:
          </p>
          <div class="flex flex-wrap gap-1">
            <span 
              v-for="m in metodosPendientes" 
              :key="m.valor" 
              class="px-2 py-1 text-xs font-medium bg-white dark:bg-slate-800 border border-amber-300 dark:border-amber-700 rounded text-amber-700 dark:text-amber-300"
            >
              {{ m.label }} (esperado: {{ fc(m.esperado) }})
            </span>
          </div>
        </div>

        <!-- Egresos de la sesión: ya están descontados del esperado de cada medio -->
        <div v-if="egresosPorMedio.length" class="bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-2">
            <i class="fa-solid fa-arrow-up-from-bracket text-rose-500"></i>
            <span class="font-semibold text-rose-700 dark:text-rose-300 text-sm">Egresos de la sesión</span>
          </div>
          <p class="text-[10px] text-rose-600 dark:text-rose-400 mb-2">
            Salidas de dinero. Ya están descontadas del saldo esperado de cada medio (por eso el arqueo de la cuenta digital cuadra igual).
          </p>
          <div class="space-y-1">
            <div v-for="e in egresosPorMedio" :key="e.medio" class="flex items-center justify-between text-sm">
              <span class="text-rose-700 dark:text-rose-300">{{ e.label }}</span>
              <span class="font-mono-data font-bold text-rose-600 dark:text-rose-400">-{{ fc(e.monto) }}</span>
            </div>
            <div class="flex items-center justify-between text-sm pt-1 border-t border-rose-200 dark:border-rose-800">
              <span class="font-semibold text-rose-700 dark:text-rose-300">Total egresado</span>
              <span class="font-mono-data font-bold text-rose-600 dark:text-rose-400">-{{ fc(totalEgresos) }}</span>
            </div>
            <p v-if="totalRetirosCierreActual > 0" class="text-[10px] text-rose-500 dark:text-rose-400 text-right">
              Incluye {{ fc(totalRetirosCierreActual) }} de extracción.
            </p>
          </div>
        </div>

        <!-- Resumen Total -->
        <div class="bg-slate-100 dark:bg-slate-800 rounded-xl p-4 space-y-2">
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Cajón esperado</span>
            <span class="font-mono-data font-bold text-slate-900 dark:text-white">{{ fc(esperadoEfectivo) }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Cuentas digitales esperadas</span>
            <span class="font-mono-data font-bold text-indigo-600 dark:text-indigo-400">{{ fc(esperadoCuentas) }}</span>
          </div>
          <div class="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
            <span class="text-sm font-bold text-slate-900 dark:text-white">Total esperado</span>
            <span class="font-mono-data font-bold text-lg text-slate-900 dark:text-white">{{ fc(totalEsperado) }}</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Total real cargado</span>
            <span class="font-mono-data font-bold text-lg" :class="totalReal === totalEsperado ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'">{{ fc(totalReal) }}</span>
          </div>
          <div v-if="totalReal !== totalEsperado" class="flex items-center justify-between pt-2 border-t border-slate-200 dark:border-slate-700">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Diferencia Total</span>
            <span class="font-mono-data font-bold text-lg" :class="diferenciaTotal >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'">
              {{ diferenciaTotal >= 0 ? '+' : '' }}{{ fc(diferenciaTotal) }}
            </span>
          </div>
        </div>

        <!-- Comentario General -->
        <div>
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Observaciones del Cierre</label>
          <input
            v-model="cierreComentario"
            type="text"
            placeholder="Observaciones generales del cierre de caja..."
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
            :disabled="closing"
          />
        </div>

        <div class="flex gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" :disabled="closing" @click="cancelarCierreCaja">
            Cancelar
          </BaseButton>
          <BaseButton variant="danger" class="flex-1" :loading="closing" :disabled="closing" @click="confirmarCierreCaja">
            <i :class="closing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i>
            {{ closing ? 'Cerrando...' : 'Confirmar Cierre de Caja' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <ContadorBilletesModal
      v-model="showContadorBilletes"
      :titulo="tituloContadorBilletes"
      :valor-actual="valorActualContador"
      @aplicar="aplicarConteoBilletes"
    />

    <ContadorTransferenciasModal
      v-model="showContadorTransferencias"
      :titulo="tituloContadorTransferencias"
      :valor-actual="valorActualContador"
      :valor-esperado="valorEsperadoTransferencias"
      :medio-por-defecto="contadorContexto?.metodo?.valor || 'transferencia'"
      @aplicar="aplicarConteoTransferencias"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useCajaStore } from '@/stores/caja'
import { useCarritoStore } from '@/stores/carrito'
import router from '@/router'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ContadorBilletesModal from '@/components/caja/ContadorBilletesModal.vue'
import ContadorTransferenciasModal from '@/components/caja/ContadorTransferenciasModal.vue'
import ArqueoMedios from '@/components/caja/ArqueoMedios.vue'
import { useSounds } from '@/composables/useSounds'

const auth = useAuthStore()
const toast = useToastStore()
const cajaStore = useCajaStore()
const carritoStore = useCarritoStore()
const { playOpenCash, playCloseCash } = useSounds()
const cajaResumen = reactive({ metodos_cerrados: [], egresos_por_medio: {}, retiros: [], total_retiros: 0 })

const movements = ref([])

const syncing = ref(false)
const opening = ref(false)
const closing = ref(false)
const saving = ref(false)
const guardandoRetiroActual = ref(false)

const syncInterval = ref(null)

const showNuevoMovimiento = ref(false)
const showCierreModal = ref(false)
const showAperturaModal = ref(false)
const cierreComentario = ref('')

const aperturaForm = reactive({
  monto_inicial: 0,
  monto_retiro: 0,
  motivo_retiro: '',
  saldos_cuentas: {},
})

const abrirCuentasDigitales = ref(false)
// Saldo con el que quedó cada cuenta en el último cierre. Se muestra como
// referencia al lado del input, pero nunca se precarga: las cuentas abren en 0.
const saldosUltimosCuentas = ref({})

const montoFinalApertura = computed(() => {
  return Math.max(0, aperturaForm.monto_inicial - aperturaForm.monto_retiro)
})

const showContadorBilletes = ref(false)
const showContadorTransferencias = ref(false)
const contadorContexto = ref(null)

const TITULOS_CONTADOR = {
  apertura: 'Contar efectivo — Apertura de caja',
  arqueo: 'Contar efectivo — Cierre de caja',
}

const tituloContadorBilletes = computed(() => TITULOS_CONTADOR[contadorContexto.value] || 'Contar efectivo')

const valorActualContador = computed(() => {
  const ctx = contadorContexto.value
  if (!ctx) return 0
  if (ctx === 'apertura') return Number(aperturaForm.monto_inicial) || 0
  return Number(ctx?.metodo?.montoReal) || 0
})

function abrirContadorBilletes(contexto, metodo = null) {
  contadorContexto.value = metodo ? { contexto, metodo } : contexto
  showContadorBilletes.value = true
}

function aplicarConteoBilletes(total) {
  const ctx = contadorContexto.value
  if (ctx === 'apertura') aperturaForm.monto_inicial = total
  else if (ctx?.metodo) ctx.metodo.montoReal = total
  toast.success(`Total contado: ${fc(total)}`)
}

// El mismo contador pero para transferencias: se abre desde la fila del medio
// que sea, con el esperado de esa fila como referencia del aviso.
const tituloContadorTransferencias = computed(() => {
  const medio = contadorContexto.value?.metodo
  return medio ? `Contar ${medio.label}` : 'Contar transferencias'
})

const valorEsperadoTransferencias = computed(() => {
  const medio = contadorContexto.value?.metodo
  return medio ? Number(medio.esperado) || 0 : 0
})

function aplicarConteoTransferencias(total) {
  const ctx = contadorContexto.value
  if (ctx?.metodo) ctx.metodo.montoReal = total
  toast.success(`Total contado: ${fc(total)}`)
}

// Se abre desde cualquier medio que no sea efectivo: el efectivo tiene su
// contador de billetes y este es para las cuentas.
function abrirContadorTransferencias(metodo) {
  if (metodo?.valor === 'efectivo') {
    abrirContadorBilletes('arqueo', metodo)
    return
  }
  contadorContexto.value = { contexto: 'arqueo', metodo }
  showContadorTransferencias.value = true
}

// --- Proveedores, para el pago del cierre ---
// Se cargan al abrir el cierre y no antes: la lista puede estar larga y hasta
// ese momento no se necesitan.
const proveedores = ref([])

async function cargarProveedores() {
  if (proveedores.value.length) return
  try {
    const data = await api.get('/api/proveedores', { page_size: 100000 })
    proveedores.value = Array.isArray(data) ? data : []
  } catch {
    proveedores.value = []
  }
}

const guardandoPago = ref(false)

async function registrarPagoProveedor({ monto, proveedor_id, proveedor_nombre, descripcion, medio_pago }, cierreId = null) {
  guardandoPago.value = true
  try {
    await api.post('/api/caja/pago-proveedor', {
      monto,
      proveedor_id,
      proveedor_nombre,
      descripcion: descripcion || '',
      medio_pago,
      ...(cierreId ? { cierre_id: cierreId } : {}),
    })
    toast.success(`Pago a ${proveedor_nombre} registrado: ${fc(monto)}`)
    if (cierreId) {
      await cargarArqueoSesion()
    } else {
      await cargarResumenCierreActual()
    }
    await fetchResumen()
    await fetchMovimientos()
  } catch (e) {
    toast.error('Error al registrar el pago: ' + (e?.data?.detail || e?.message || ''))
  } finally {
    guardandoPago.value = false
  }
}

const metodosArqueo = reactive([])

const MEDIO_LABELS = {
  efectivo: 'Efectivo',
  debito: 'Débito',
  credito: 'Crédito',
  transferencia: 'Transferencia',
  mercadopago_qr: 'QR MercadoPago',
  mercadopago_pos: 'POS MercadoPago',
  smartpoint: 'SmartPoint',
  qr_interop: 'QR BCRA',
  cta_corriente: 'Cta. Cte.',
}

// Cuentas digitales: el saldo vive en la app del proveedor, no en el cajón
const MEDIOS_CUENTA = ['smartpoint', 'mercadopago_qr', 'mercadopago_pos', 'qr_interop']

const MEDIO_COLORS = {
  efectivo: 'bg-emerald-500',
  debito: 'bg-blue-500',
  credito: 'bg-purple-500',
  transferencia: 'bg-amber-500',
}

const cuentasDigitales = computed(() => MEDIOS_CUENTA.map(v => ({ valor: v, label: MEDIO_LABELS[v] || v })))

const cuentasConSaldo = computed(() =>
  Object.entries(cajaStore.saldos_cuentas || {})
    .map(([medio, saldo]) => ({ medio, label: MEDIO_LABELS[medio] || medio, saldo }))
    .filter(c => c.saldo)
)

const totalSaldosCuentasApertura = computed(() =>
  Object.values(aperturaForm.saldos_cuentas || {}).reduce((sum, v) => sum + (Number(v) || 0), 0)
)

const cuentasConSaldoApertura = computed(() =>
  cuentasDigitales.value
    .filter(c => (Number(aperturaForm.saldos_cuentas[c.valor]) || 0) > 0)
    .map(c => c.label)
    .join(', ')
)

const nuevoMovimiento = reactive({ tipo: 'Ingreso', monto: 0, metodo: 'Efectivo', comentario: '' })

// Selector de medio del movimiento manual: incluye las cuentas digitales para
// poder registrar, por ejemplo, una transferencia de MP al banco.
const MEDIOS_MOVIMIENTO = {
  Efectivo: 'efectivo',
  'Débito': 'debito',
  Crédito: 'credito',
  Transferencia: 'transferencia',
  SmartPoint: 'smartpoint',
  'QR MercadoPago': 'mercadopago_qr',
  'POS MercadoPago': 'mercadopago_pos',
  'QR BCRA': 'qr_interop',
}
const metodosMovimiento = Object.keys(MEDIOS_MOVIMIENTO)

const totalEsperado = computed(() => metodosArqueo.reduce((sum, m) => sum + m.esperado, 0))
const esperadoEfectivo = computed(() => {
  const m = metodosArqueo.find(x => x.valor === 'efectivo')
  return m ? m.esperado : 0
})
const esperadoCuentas = computed(() => metodosArqueo
  .filter(m => m.es_cuenta_digital)
  .reduce((sum, m) => sum + m.esperado, 0))
const totalReal = computed(() => metodosArqueo.reduce((sum, m) => sum + (m.montoReal || 0), 0))
const diferenciaTotal = computed(() => totalReal.value - totalEsperado.value)

// Egresos por medio de la sesión (ej: recargas que salieron de MercadoPago/SmartPoint).
// No afectan el conteo físico de cada método: se informan aparte para que el cierre
// muestre el egreso real sin romper el arqueo del efectivo.
const egresosPorMedio = computed(() => {
  const porMedio = cajaResumen.egresos_por_medio || {}
  return Object.entries(porMedio)
    .map(([medio, monto]) => ({ medio, label: MEDIO_LABELS[medio] || medio, monto }))
    .filter(e => e.monto > 0)
    .sort((a, b) => b.monto - a.monto)
})
const totalEgresos = computed(() => egresosPorMedio.value.reduce((sum, e) => sum + e.monto, 0))

const ingresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Ingreso' && esDeHoy(m)).reduce((sum, m) => sum + m.monto, 0))
const egresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Egreso' && esDeHoy(m)).reduce((sum, m) => sum + m.monto, 0))
const movimientosIngresos = computed(() => movements.value.filter(m => m.tipo === 'Ingreso' && esDeHoy(m)).length)
const movimientosEgresos = computed(() => movements.value.filter(m => m.tipo === 'Egreso' && esDeHoy(m)).length)

const movementColumns = [
  { key: 'fecha', label: 'Fecha' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'monto', label: 'Monto' },
  { key: 'metodo', label: 'Método' },
  { key: 'comentario', label: 'Comentario' },
]

// Métodos pendientes de montoReal para poder cerrar
const metodosPendientes = computed(() => metodosArqueo.filter(m => 
  !m.cerrado && m.esperado > 0 && (!m.montoReal || m.montoReal <= 0)
))
const hayPendientes = computed(() => metodosPendientes.value.length > 0)

// Historial de sesiones de caja
const filtroHistorial = ref('semana')
const showFechasPersonalizadas = ref(false)
const fechaInicio = ref('')
const fechaFin = ref('')
const sesionesCaja = ref([])
const showDetalleSesion = ref(false)
const sesionSeleccionada = ref(null)
const loadingReportes = ref(false)

// Vista del historial: lista | calendario
const vistaHistorial = ref('lista')
const vistasHistorial = [
  { valor: 'lista', label: 'Lista', icone: 'fa-solid fa-list' },
  { valor: 'calendario', label: 'Calendario', icone: 'fa-solid fa-calendar-days' },
]
const diasSemana = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb']

// Calendario (semáforo por día)
const mesCalendario = ref(new Date())
const calendarioDias = ref([])
const loadingCalendario = ref(false)

// Detalle del día
const showDetalleDia = ref(false)
const detalleDia = ref(null)
const detalleDiaEstado = ref('sin_operacion')

// Arqueo/cierre diferido de una sesión que el sistema ya cerró sola
const showCierreSesion = ref(false)
const cierreSesionId = ref(null)
const arqueoSesion = ref(null)
const filasCierreSesion = ref([])
const retirosCierreSesion = ref([])
const comentarioCierreSesion = ref('')
const cargandoArqueoSesion = ref(false)
const conciliandoSesion = ref(false)
const guardandoRetiroSesion = ref(false)

// Detalle de ticket
const showTicketDetalle = ref(false)
const ticketSeleccionado = ref(null)
const loadingTicket = ref(false)

const filtrosHistorial = [
  { valor: 'hoy', label: 'Hoy' },
  { valor: 'semana', label: 'Semana' },
  { valor: 'mes', label: 'Mes' },
  { valor: 'personalizado', label: 'Personalizado' },
]

function cambiarVistaHistorial(vista) {
  vistaHistorial.value = vista
  if (vista === 'calendario') {
    fetchCalendario()
  } else {
    fetchReportes()
  }
}

const tituloMesCalendario = computed(() => {
  const d = mesCalendario.value
  return d.toLocaleDateString('es-AR', { month: 'long', year: 'numeric' })
})

const celdasCalendario = computed(() => {
  const hoy = new Date()
  const anio = mesCalendario.value.getFullYear()
  const mes = mesCalendario.value.getMonth()
  const primerDia = new Date(anio, mes, 1)
  const offset = primerDia.getDay() // 0 = domingo
  const totalDias = new Date(anio, mes + 1, 0).getDate()

  const celdas = []
  for (let i = 0; i < offset; i++) celdas.push({ dia: 0 })
  for (let d = 1; d <= totalDias; d++) {
    const fechaStr = `${anio}-${String(mes + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    const info = calendarioDias.value.find(x => x.fecha === fechaStr) || null
    celdas.push({
      dia: d,
      fecha: fechaStr,
      estado: info ? info.estado : 'sin_operacion',
      tieneOperacion: !!info && (info.n_cierres > 0 || info.ingresos > 0 || info.n_ventas > 0),
      esHoy: hoy.getFullYear() === anio && hoy.getMonth() === mes && hoy.getDate() === d,
      n_ventas: info ? info.ventas : 0,
      ingresos: info ? info.ingresos : 0,
    })
  }
  return celdas
})

function colorDia(celda) {
  if (celda.estado === 'verde') return 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-500'
  if (celda.estado === 'amarillo') return 'bg-amber-50 dark:bg-amber-900/20 border-amber-500'
  if (celda.estado === 'rojo') return 'bg-red-50 dark:bg-red-900/20 border-red-500'
  if (celda.tieneOperacion) return 'bg-slate-100 dark:bg-slate-700/40 border-slate-300 dark:border-slate-600'
  return 'bg-slate-50 dark:bg-slate-800/40 border-slate-200 dark:border-slate-700'
}

function labelColorDia(estado) {
  if (estado === 'verde') return 'OK'
  if (estado === 'amarillo') return 'Con diferencias'
  if (estado === 'rojo') return 'Sin conciliar'
  if (estado === 'abierta') return 'Caja abierta'
  return 'Sin operaciones'
}

function badgeColorDia(estado) {
  if (estado === 'verde') return 'success'
  if (estado === 'amarillo') return 'warning'
  if (estado === 'rojo') return 'danger'
  return 'secondary'
}

function cambiarMesCalendario(delta) {
  const nuevo = new Date(mesCalendario.value)
  nuevo.setMonth(nuevo.getMonth() + delta)
  mesCalendario.value = nuevo
  fetchCalendario()
}

async function fetchCalendario() {
  loadingCalendario.value = true
  try {
    const mes = `${mesCalendario.value.getFullYear()}-${String(mesCalendario.value.getMonth() + 1).padStart(2, '0')}`
    const resp = await api.get(`/api/caja/calendario?mes=${mes}`)
    calendarioDias.value = (resp && resp.dias) || []
  } catch (e) {
    console.error('Error fetching calendario:', e)
    toast.error('Error al cargar el calendario de caja')
  } finally {
    loadingCalendario.value = false
  }
}

async function abrirDiaCalendario(fecha) {
  try {
    const resp = await api.get(`/api/caja/dia?fecha=${fecha}`)
    detalleDia.value = resp
    const info = calendarioDias.value.find(x => x.fecha === fecha)
    detalleDiaEstado.value = info ? info.estado : 'sin_operacion'
    showDetalleDia.value = true
  } catch (e) {
    toast.error('Error al cargar el detalle del día')
  }
}

function estadoDiaActual() {
  return detalleDiaEstado.value
}

function formatFechaDia(fechaStr) {
  if (!fechaStr) return '—'
  const [y, m, d] = fechaStr.split('-').map(Number)
  const fecha = new Date(y, m - 1, d)
  return fecha.toLocaleDateString('es-AR', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' })
}

function esCierreConfirmable(sesion) {
  return !!sesion.fue_automatico && sesion.cierre_monto_confirmado == null
}

// Arqueo de una sesión que el sistema cerró sola. Se puede hacer aunque haya otra
// caja abierta: el backend acota el arqueo a la sesión del cierre y, si la caja
// abierta es la misma, recalcula el esperado de cada medio con la extracción.
async function abrirCierreSesion(cierreId) {
  if (!cierreId) {
    toast.error('La sesión no tiene cierre asociado')
    return
  }
  cierreSesionId.value = cierreId
  arqueoSesion.value = null
  filasCierreSesion.value = []
  retirosCierreSesion.value = []
  comentarioCierreSesion.value = ''
  showDetalleSesion.value = false
  showDetalleDia.value = false
  showCierreSesion.value = true
  await cargarArqueoSesion()
}

async function cargarArqueoSesion() {
  if (!cierreSesionId.value) return
  cargandoArqueoSesion.value = true
  try {
    const data = await api.get(`/api/caja/cierre/${cierreSesionId.value}/arqueo`)
    arqueoSesion.value = data
    filasCierreSesion.value = construirMetodosArqueo(data, {
      cerrados: (data.por_medio || []).filter(f => f.cerrado).map(f => f.medio_pago),
      prellenar: true,
    })
    retirosCierreSesion.value = data.retiros || []
  } catch (e) {
    toast.error('Error al cargar el arqueo: ' + (e?.data?.detail || e?.message || ''))
    showCierreSesion.value = false
  } finally {
    cargandoArqueoSesion.value = false
  }
}

const totalEsperadoSesion = computed(() => filasCierreSesion.value.reduce((s, f) => s + (f.esperado || 0), 0))
const totalRealSesion = computed(() => filasCierreSesion.value.reduce((s, f) => s + (Number(f.montoReal) || 0), 0))
const diferenciaTotalSesion = computed(() => totalRealSesion.value - totalEsperadoSesion.value)

function cerrarModalCierreSesion() {
  showCierreSesion.value = false
  cierreSesionId.value = null
  arqueoSesion.value = null
}

async function conciliarSesion() {
  if (!arqueoSesion.value || arqueoSesion.value.confirmado) return
  const pendiente = (arqueoSesion.value.medios_pendientes || []).filter(m => {
    const fila = filasCierreSesion.value.find(f => f.valor === m)
    return !fila || fila.montoReal == null || fila.montoReal === ''
  })
  if (pendiente.length) {
    toast.warning('Contá el monto de: ' + pendiente.map(m => MEDIO_LABELS[m] || m).join(', '))
    return
  }
  const conDiferencia = filasCierreSesion.value.filter(f => (Number(f.montoReal) || 0) - (f.esperado || 0) !== 0)
  if (conDiferencia.length && !confirm(
    `Hay ${conDiferencia.length} medio(s) con diferencia:\n\n` +
    conDiferencia.map(f => `  - ${f.label}: esperado ${fc(f.esperado)} · contado ${fc(f.montoReal)}`).join('\n') +
    '\n\nAl conciliar queda registrada la diferencia y el día pasa a amarillo (corrección). ¿Conciliar igual?'
  )) return

  conciliandoSesion.value = true
  try {
    for (const fila of filasCierreSesion.value) {
      if (fila.montoReal == null || fila.montoReal === '') continue
      await api.post(`/api/caja/cierre/${cierreSesionId.value}/metodo`, {
        medio_pago: fila.valor,
        monto_real: Number(fila.montoReal),
        comentario: fila.comentario || comentarioCierreSesion.value || '',
      })
    }
    await api.put(`/api/caja/cierre/${cierreSesionId.value}/confirmar`, {
      monto_confirmado: totalRealSesion.value,
      comentario: comentarioCierreSesion.value || '',
    })
    toast.success('Sesión conciliada')
    cerrarModalCierreSesion()
    await recargarVistasCierre()
  } catch (e) {
    toast.error('Error al conciliar la sesión: ' + (e?.data?.detail || e?.message || ''))
  } finally {
    conciliandoSesion.value = false
  }
}

async function recargarVistasCierre() {
  const fecha = detalleDia.value?.fecha
  if (fecha) {
    try {
      detalleDia.value = await api.get(`/api/caja/dia?fecha=${fecha}`)
    } catch { /* el detalle del día es informativo */ }
  }
  await fetchCalendario()
  await fetchReportes()
}

async function verTicketDetalle(ventaId) {
  try {
    loadingTicket.value = true
    const resp = await api.get(`/api/ventas/${ventaId}`)
    ticketSeleccionado.value = resp
    showTicketDetalle.value = true
  } catch (e) {
    toast.error('Error al cargar el detalle de la venta')
  } finally {
    loadingTicket.value = false
  }
}

function cambiarFiltroHistorial(filtro) {
  filtroHistorial.value = filtro
  if (filtro !== 'personalizado') {
    showFechasPersonalizadas.value = false
    fetchReportes()
  }
}

function calcularFechasFiltro() {
  const hoy = new Date()
  let inicio = new Date()
  let fin = new Date()

  if (filtroHistorial.value === 'hoy') {
    inicio = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate())
    fin = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate(), 23, 59, 59)
  } else if (filtroHistorial.value === 'semana') {
    const diaSemana = hoy.getDay()
    const diff = diaSemana === 0 ? 6 : diaSemana - 1
    inicio = new Date(hoy)
    inicio.setDate(hoy.getDate() - diff)
    inicio.setHours(0, 0, 0, 0)
    fin = new Date(hoy)
    fin.setHours(23, 59, 59, 999)
  } else if (filtroHistorial.value === 'mes') {
    inicio = new Date(hoy.getFullYear(), hoy.getMonth(), 1)
    fin = new Date(hoy.getFullYear(), hoy.getMonth() + 1, 0, 23, 59, 59)
  }

  return {
    inicio: inicio.toISOString().split('T')[0],
    fin: fin.toISOString().split('T')[0]
  }
}

async function fetchReportes() {
  loadingReportes.value = true
  try {
    let fechaIni = ''
    let fechaFinStr = ''

    if (filtroHistorial.value === 'personalizado') {
      fechaIni = fechaInicio.value
      fechaFinStr = fechaFin.value
    } else {
      const fechas = calcularFechasFiltro()
      fechaIni = fechas.inicio
      fechaFinStr = fechas.fin
    }

    const params = new URLSearchParams()
    if (fechaIni) params.append('fecha_inicio', fechaIni)
    if (fechaFinStr) params.append('fecha_fin', fechaFinStr)

    const resp = await api.get(`/api/caja/reportes?${params.toString()}`)
    if (resp && resp.sesiones) {
      sesionesCaja.value = resp.sesiones
    }
  } catch (e) {
    console.error('Error fetching reportes:', e)
    toast.error('Error al cargar historial de caja')
  } finally {
    loadingReportes.value = false
  }
}

async function verDetalleSesion(sesion) {
  // Obtener la fecha de la apertura para usar el endpoint /dia que tiene datos completos
  if (!sesion.apertura_fecha) {
    sesionSeleccionada.value = sesion
    showDetalleSesion.value = true
    return
  }
  const fecha = sesion.apertura_fecha.split('T')[0]
  try {
    const resp = await api.get(`/api/caja/dia?fecha=${fecha}`)
    // Buscar la sesión específica en el día (puede haber varias)
    const sesionCompleta = resp.cierres?.find(c => c.id === sesion.cierre_id) 
      || { ...sesion, ...resp }
    sesionSeleccionada.value = { ...sesion, ...resp, cierres: resp.cierres, tickets: resp.tickets, movimientos: resp.movimientos }
  } catch (e) {
    // Fallback a datos básicos
    sesionSeleccionada.value = sesion
  }
  showDetalleSesion.value = true
}

function formatFecha(fechaStr) {
  if (!fechaStr) return '—'
  const fecha = new Date(fechaStr)
  return fecha.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

function formatHora(fechaStr) {
  if (!fechaStr) return '—'
  const fecha = new Date(fechaStr)
  return fecha.toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' })
}

function formatFechaHora(fechaStr) {
  if (!fechaStr) return '—'
  const fecha = new Date(fechaStr)
  return fecha.toLocaleString('es-AR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(async () => {
  await fetchMovimientos()
  await fetchResumen()
  await cajaStore.fetchUltimoCierre()
  await fetchReportes()
  startPeriodicSync()
})

onUnmounted(() => {
  stopPeriodicSync()
})

function startPeriodicSync() {
  if (syncInterval.value) return
  syncInterval.value = setInterval(async () => {
    try {
      await cajaStore.fetchEstado()
    } catch { /* ignore */ }
  }, 60000)
}

function stopPeriodicSync() {
  if (syncInterval.value) {
    clearInterval(syncInterval.value)
    syncInterval.value = null
  }
}

async function fetchMovimientos() {
  try {
    const data = await api.get('/api/caja/movimientos')
    if (data && data.length) {
      movements.value = data.map(m => ({
        id: m.id,
        fecha: m.created_at,
        tipo: (m.tipo || '').toLowerCase() === 'ingreso' ? 'Ingreso'
            : (m.tipo || '').toLowerCase() === 'egreso' ? 'Egreso' : m.tipo,
        monto: m.monto,
        metodo: MEDIO_LABELS[m.medio_pago] || m.medio_pago || '',
        comentario: m.descripcion || '',
        created_at: m.created_at,
      }))
    }
  } catch { /* fallback to mock */ }
}

function esDeHoy(m) {
  const f = new Date(m.created_at || m.fecha)
  if (isNaN(f.getTime())) return true
  const ahora = new Date()
  return f.getFullYear() === ahora.getFullYear() &&
    f.getMonth() === ahora.getMonth() &&
    f.getDate() === ahora.getDate()
}

async function fetchResumen() {
  try {
    const data = await api.get('/api/caja/resumen')
    if (data) {
      cajaResumen.metodos_cerrados = data.metodos_cerrados || []
      cajaResumen.egresos_por_medio = data.egresos_por_medio || {}
      cajaResumen.retiros = data.retiros || []
      cajaResumen.total_retiros = data.total_retiros || 0
    }
  } catch { /* fallback to mock */ }
  await cajaStore.fetchEstado()
}

async function syncData() {
  syncing.value = true
  try {
    await fetchMovimientos()
    await fetchResumen()
    toast.success('Datos sincronizados')
  } catch {
    toast.warning('Error al sincronizar')
  } finally {
    syncing.value = false
  }
}

async function abrirCaja() {
  await cajaStore.fetchUltimoCierre()
  await cargarSaldosCuentasSugeridos()

  // Se sugiere solo el efectivo que quedó en el cajón: el total del cierre suma
  // también las cuentas digitales, que van por su propia cuenta.
  const ultimo = cajaStore.ultimoCierre
  const efectivo = ultimo ? (ultimo.saldo_efectivo ?? ultimo.monto) : 0
  aperturaForm.monto_inicial = efectivo > 0 ? efectivo : 0
  aperturaForm.monto_retiro = 0
  aperturaForm.motivo_retiro = ''
  showAperturaModal.value = true
}

// Las cuentas digitales abren siempre en 0.
//
// Antes se precargaban con el saldo del último cierre, y el resultado era que
// un clic de más abría la caja con un saldo inventado: si el cajero no miraba
// el campo y confirmaba directo, el arqueo del día ya nacía con una diferencia
// que no se explica. El saldo real de la app se escribe a mano; el de ayer
// queda a la vista como referencia, no como valor.
async function cargarSaldosCuentasSugeridos() {
  const saldos = {}
  MEDIOS_CUENTA.forEach(m => { saldos[m] = 0 })
  try {
    const data = await api.get('/api/caja/saldos-cuentas')
    const sugeridos = data?.saldos || {}
    // Se guarda aparte, solo para mostrarlo al lado del input.
    saldosUltimosCuentas.value = {}
    MEDIOS_CUENTA.forEach(m => {
      if (sugeridos[m] != null) saldosUltimosCuentas.value[m] = Number(sugeridos[m]) || 0
    })
  } catch { /* sin sugeridos: quedan en 0 */ }
  aperturaForm.saldos_cuentas = saldos
}

async function confirmarAperturaCaja() {
  if (aperturaForm.monto_inicial < 0) {
    toast.error('El monto inicial no puede ser negativo')
    return
  }
  if (aperturaForm.monto_retiro < 0) {
    toast.error('El monto de retiro no puede ser negativo')
    return
  }
  if (aperturaForm.monto_retiro > aperturaForm.monto_inicial) {
    toast.error('El monto de retiro no puede ser mayor al monto inicial')
    return
  }
  const saldosCuentas = {}
  for (const m of MEDIOS_CUENTA) {
    const v = Number(aperturaForm.saldos_cuentas[m]) || 0
    if (v < 0) {
      toast.error(`El saldo inicial de ${MEDIO_LABELS[m]} no puede ser negativo`)
      return
    }
    if (v > 0) saldosCuentas[m] = v
  }

  opening.value = true
  try {
    await api.post('/api/caja/apertura', {
      monto_inicial: montoFinalApertura.value,
      monto_retiro: aperturaForm.monto_retiro,
      motivo_retiro: aperturaForm.motivo_retiro,
      saldos_cuentas: saldosCuentas,
    })
    await cajaStore.fetchEstado()
    await fetchMovimientos()
    showAperturaModal.value = false
    
    let msg = `Caja abierta con $${montoFinalApertura.value.toLocaleString()}`
    if (aperturaForm.monto_retiro > 0) {
      msg += ` (retiro: $${aperturaForm.monto_retiro.toLocaleString()})`
    }
    const nCuentas = Object.keys(saldosCuentas).length
    if (nCuentas) {
      msg += ` · ${nCuentas} cuenta${nCuentas > 1 ? 's' : ''} digital${nCuentas > 1 ? 'es' : ''} a controlar`
    }
    toast.success(msg)
    playOpenCash()
  } catch (e) {
    toast.error('Error al abrir caja: ' + (e.message || ''))
  } finally {
    opening.value = false
  }
}

async function initCierreCaja() {
  // Los carritos con productos sin cobrar son los que hay que resolver antes de
  // bajar la caja. Los vacios se ignoran: no son nada pendiente.
  const abiertos = carritoStore.carritosConItems
  if (abiertos.length > 0) {
    const detalle = abiertos.map(c => `  - ${c.nombre}: ${c.items.length} producto(s) por ${fc(c.total)}`).join('\n')
    if (!confirm(`Hay ${abiertos.length} carrito(s) del POS con productos sin cobrar:\n\n${detalle}\n\nSi cerrás la caja sin cobrarlos quedan como huérfanos en la auditoría. ¿Cerrar de todas formas?`)) return
    for (const c of abiertos) {
      carritoStore.auditar('ORPHAN', { carritoId: c.id, nombre: c.nombre, items: c.items.length, total: c.total })
    }
    try { localStorage.setItem('apex-pos-caja-cierre', new Date().toISOString()) } catch { /* storage bloqueado */ }
  }

  try {
    await cargarResumenCierreActual()
    // El bloque de pago a proveedor necesita la lista, y solo se usa acá.
    await cargarProveedores()
    cierreComentario.value = ''
    showCierreModal.value = true
  } catch (e) {
    toast.error('Error al obtener resumen de caja')
  }
}

async function cargarResumenCierreActual() {
  const data = await api.get('/api/caja/resumen')
  if (!data) return
  metodosArqueo.splice(0, metodosArqueo.length, ...construirMetodosArqueo(data))
  retirosCierreActual.value = data.retiros || []
}

// Arma las filas del arqueo a partir del resumen del backend: efectivo y medios
// clásicos siempre, más las cuentas digitales que tengan saldo inicial o
// movimientos en la sesión. `prellenar` es para el arqueo diferido, donde las
// filas arrancan con el monto que ya se había cargado en un intento anterior.
function construirMetodosArqueo(data, { cerrados = null, prellenar = false } = {}) {
  const porMedio = data.por_medio || []
  const listaCerrados = cerrados || data.metodos_cerrados || []
  const previos = new Map(metodosArqueo.map(f => [f.valor, f]))
  const montoDe = (medio, porDefecto) => {
    if (prellenar) return porDefecto ?? null
    const previo = previos.get(medio)
    return previo ? previo.montoReal : 0
  }
  const comentarioDe = (medio) => {
    if (prellenar) return ''
    return previos.get(medio)?.comentario || ''
  }
  if (!porMedio.length) {
    return ['efectivo', 'debito', 'credito', 'transferencia'].map(v => ({
      label: MEDIO_LABELS[v], valor: v, esperado: 0, apertura: 0, ingresos: 0, egresos: 0,
      montoReal: montoDe(v, null), comentario: comentarioDe(v), cerrado: listaCerrados.includes(v),
      es_cuenta_digital: false, falta_saldo_inicial: false,
      colorClass: MEDIO_COLORS[v] || 'bg-slate-400',
    }))
  }
  return porMedio.map(f => ({
    label: f.nombre || MEDIO_LABELS[f.medio_pago] || f.medio_pago,
    valor: f.medio_pago,
    esperado: f.esperado || 0,
    apertura: f.apertura || 0,
    ingresos: f.ingresos || 0,
    egresos: f.egresos || 0,
    montoReal: montoDe(f.medio_pago, f.monto_real),
    comentario: prellenar ? (f.comentario || '') : comentarioDe(f.medio_pago),
    cerrado: listaCerrados.includes(f.medio_pago),
    es_cuenta_digital: !!f.es_cuenta_digital,
    falta_saldo_inicial: !!f.falta_saldo_inicial,
    colorClass: f.es_cuenta_digital ? 'bg-indigo-500' : (MEDIO_COLORS[f.medio_pago] || 'bg-slate-400'),
  }))
}

const retirosCierreActual = ref([])
const totalRetirosCierreActual = computed(() => retirosCierreActual.value.reduce((s, r) => s + (Number(r.monto) || 0), 0))

async function agregarRetiroCierreActual({ monto, motivo, por_dejo, deja }) {
  guardandoRetiroActual.value = true
  try {
    await api.post('/api/caja/retiro-cierre', { monto, motivo: motivo || '' })
    // El mensaje dice las dos mitades porque es lo que hay que saber al
    // cerrar: cuánto salió y cuánto queda adentro.
    toast.success(por_dejo
      ? `Dejaste ${fc(deja)} y te llevaste ${fc(monto)}`
      : 'Extracción registrada')
    await cargarResumenCierreActual()
    await fetchMovimientos()
  } catch (e) {
    toast.error('Error al registrar la extracción: ' + (e?.data?.detail || e?.message || ''))
  } finally {
    guardandoRetiroActual.value = false
  }
}

async function agregarRetiroSesion({ monto, motivo, por_dejo, deja }) {
  guardandoRetiroSesion.value = true
  try {
    await api.post('/api/caja/retiro-cierre', { cierre_id: cierreSesionId.value, monto, motivo: motivo || '' })
    toast.success(por_dejo
      ? `Dejaste ${fc(deja)} y te llevaste ${fc(monto)}`
      : 'Extracción registrada')
    await cargarArqueoSesion()
    await fetchResumen()
  } catch (e) {
    toast.error('Error al registrar la extracción: ' + (e?.data?.detail || e?.message || ''))
  } finally {
    guardandoRetiroSesion.value = false
  }
}

async function borrarRetiro(retiro, deSesion) {
  // La lista mezcla extracciones y pagos a proveedor: cada uno tiene su
  // endpoint porque cada uno valida su propia sesión.
  const esPago = retiro.tipo === 'pago_proveedor'
  const base = esPago ? 'pago-proveedor' : 'retiro-cierre'
  try {
    await api.delete(`/api/caja/${base}/${retiro.id}`)
    if (deSesion) await cargarArqueoSesion()
    else {
      await cargarResumenCierreActual()
      await fetchMovimientos()
    }
    await fetchResumen()
    toast.success(esPago ? 'Pago anulado' : 'Extracción deshecha')
  } catch (e) {
    toast.error(
      (esPago ? 'Error al anular el pago: ' : 'Error al borrar la extracción: ')
      + (e?.data?.detail || e?.message || '')
    )
  }
}

function cancelarCierreCaja() {
  if (totalRetirosCierreActual.value > 0 && !confirm(
    `Registraste una extracción de ${fc(totalRetirosCierreActual.value)} que queda como egreso de caja aunque cierres este modal. ¿Cerrar igual?`
  )) return
  showCierreModal.value = false
}

async function confirmarCierreCaja() {
  const metodosConMonto = metodosArqueo.filter(m => m.montoReal && m.montoReal > 0 && !m.cerrado)
  if (metodosConMonto.length === 0) {
    const confirmar = confirm('No ingresaste montos en ningún método de pago. El cierre se hará sin arqueo por método (solo cierre total). ¿Continuar?')
    if (!confirmar) return
  }

  closing.value = true
  try {
    for (const metodo of metodosArqueo) {
      if (metodo.cerrado) continue
      if (!metodo.montoReal || metodo.montoReal <= 0) continue

      const comentarioFinal = metodo.comentario || cierreComentario.value || ''
      await api.post('/api/caja/cierre-metodo', {
        medio_pago: metodo.valor,
        monto_real: metodo.montoReal,
        comentario: comentarioFinal,
      })
    }

    await api.post('/api/caja/cierre-total', { comentario: cierreComentario.value || '' })
    await cajaStore.fetchEstado()
    showCierreModal.value = false
    toast.success('Jornada finalizada. Hasta luego.')
    playCloseCash()
    auth.logout()
    router.push('/login')
  } catch (e) {
    toast.error('Error al cerrar caja: ' + (e?.data?.detail || e?.message || ''))
    await cajaStore.fetchEstado()
  } finally {
    closing.value = false
  }
}

async function registrarMovimiento() {
  if (!nuevoMovimiento.monto || nuevoMovimiento.monto <= 0) {
    toast.warning('Ingresá un monto válido')
    return
  }
  saving.value = true
  try {
    const esIngreso = nuevoMovimiento.tipo === 'Ingreso'
    const medio = MEDIOS_MOVIMIENTO[nuevoMovimiento.metodo] || 'efectivo'
    const body = {
      monto: nuevoMovimiento.monto,
      descripcion: nuevoMovimiento.comentario
        || (esIngreso ? 'Ingreso manual' : 'Egreso manual'),
      medio_pago: medio,
    }
    await api.post(esIngreso ? '/api/caja/ingreso' : '/api/caja/egreso', body)
    await fetchMovimientos()
    await fetchResumen()
    nuevoMovimiento.monto = 0
    nuevoMovimiento.comentario = ''
    showNuevoMovimiento.value = false
    toast.success('Movimiento registrado')
  } catch (e) {
    toast.error('Error al registrar movimiento: ' + (e?.data?.detail || e?.message || ''))
  } finally {
    saving.value = false
  }
}
</script>
