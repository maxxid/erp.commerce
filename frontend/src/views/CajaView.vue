<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 font-display">Arqueos y Caja</h2>
        <p class="text-sm text-slate-500 mt-1">Gestión de caja registradora</p>
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

    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <BaseCard padding="md" class="text-center">
        <div class="text-[10px] font-bold text-slate-400 uppercase">Saldo Actual</div>
        <div class="text-xl font-bold font-mono-data text-brand-600 mt-1">{{ fc(cajaStore.saldo_actual) }}</div>
        <div class="text-[10px] text-slate-400 mt-0.5">en caja</div>
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

    <!-- Cierre Parcial por Método -->
    <BaseCard v-if="cajaStore.abierta" padding="md" class="space-y-4">
      <h3 class="font-bold text-slate-900 text-sm">Cerrar por Método</h3>
      <div class="flex flex-wrap gap-2">
        <BaseButton v-for="metodo in metodosPago" :key="metodo.valor"
                    :variant="cierreParcial.activo && cierreParcial.metodo === metodo.valor ? 'primary' : 'secondary'"
                    :disabled="cerrandoMetodo || cajaResumen.metodos_cerrados?.includes(metodo.valor)"
                    size="sm"
                    @click="cierreParcial.activo = true; cierreParcial.metodo = metodo.valor; cierreParcial.monto_real = 0; cierreParcial.comentario = ''">
          <i v-if="cajaResumen.metodos_cerrados?.includes(metodo.valor)" class="fa-solid fa-check text-xs"></i>
          {{ metodo.label }}
        </BaseButton>
      </div>

      <div v-if="cierreParcial.activo" class="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-3">
        <div class="flex items-center justify-between">
          <span class="text-xs font-bold text-slate-600">
            Cerrando: <span class="text-brand-600">{{ cierreParcial.metodo }}</span>
          </span>
          <BaseButton variant="ghost" size="xs" iconOnly @click="cancelarCierre">
            <i class="fa-solid fa-xmark"></i>
          </BaseButton>
        </div>
        <BaseInput v-model.number="cierreParcial.monto_real" label="Monto Real" type="number" placeholder="0.00" input-class="font-mono-data" />
        <BaseInput v-model="cierreParcial.comentario" label="Comentario (opcional)" placeholder="Nota del cierre" />
        <div class="flex gap-2 pt-1">
          <BaseButton variant="secondary" size="sm" block @click="cancelarCierre">Cancelar</BaseButton>
          <BaseButton :loading="cerrandoMetodo" :disabled="cerrandoMetodo" variant="primary" size="sm" block @click="cerrarMetodo">
            <i :class="cerrandoMetodo ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i>
            {{ cerrandoMetodo ? 'Cerrando...' : 'Cerrar Método' }}
          </BaseButton>
        </div>
      </div>
    </BaseCard>

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
                  <BaseButton variant="ghost" size="xs" @click="verDetalleSesion(sesion)">
                    <i class="fa-solid fa-eye"></i>
                  </BaseButton>
                  <BaseButton
                    v-if="esCierreConfirmable(sesion)"
                    variant="primary"
                    size="xs"
                    @click="abrirConfirmarCierreDeSesion(sesion)"
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
    <BaseModal v-model="showDetalleSesion" title="Detalle de Sesión de Caja" size="lg">
      <div v-if="sesionSeleccionada" class="space-y-4">
        <!-- Info general -->
        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-50 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Apertura</div>
            <div class="text-sm font-medium text-slate-900">{{ formatFechaHora(sesionSeleccionada.apertura_fecha) }}</div>
            <div class="text-xs text-slate-600">{{ sesionSeleccionada.apertura_usuario }}</div>
            <div class="font-mono-data font-bold text-brand-600 mt-1">{{ fc(sesionSeleccionada.apertura_monto) }}</div>
            <div v-if="sesionSeleccionada.apertura_descripcion" class="text-[10px] text-slate-500 mt-1">{{ sesionSeleccionada.apertura_descripcion }}</div>
          </div>
          <div class="bg-slate-50 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Cierre</div>
            <div v-if="sesionSeleccionada.cierre_fecha" class="text-sm font-medium text-slate-900">{{ formatFechaHora(sesionSeleccionada.cierre_fecha) }}</div>
            <div v-else class="text-sm text-slate-400 italic">Sin cerrar</div>
            <div v-if="sesionSeleccionada.cierre_usuario" class="text-xs text-slate-600">{{ sesionSeleccionada.cierre_usuario }}</div>
            <div v-if="sesionSeleccionada.cierre_monto" class="font-mono-data font-bold text-brand-600 mt-1">{{ fc(sesionSeleccionada.cierre_monto) }}</div>
            <div v-if="sesionSeleccionada.cierre_descripcion" class="text-[10px] text-slate-500 mt-1">{{ sesionSeleccionada.cierre_descripcion }}</div>
            <BaseBadge v-if="sesionSeleccionada.fue_automatico" variant="info" size="xs" class="mt-1">Cierre automático</BaseBadge>
            <div v-if="sesionSeleccionada.cierre_monto_confirmado != null" class="mt-2 bg-emerald-50 rounded-xl p-2">
              <div class="text-[10px] uppercase tracking-wider text-emerald-600 font-semibold">Conciliado</div>
              <div class="font-mono-data font-bold text-sm text-emerald-700">{{ fc(sesionSeleccionada.cierre_monto_confirmado) }}</div>
              <div class="text-[10px] text-emerald-600">por {{ sesionSeleccionada.cierre_confirmado_por || '—' }} · {{ formatFechaHora(sesionSeleccionada.cierre_confirmado_at) }}</div>
            </div>
            <div v-else-if="sesionSeleccionada.fue_automatico" class="mt-2">
              <BaseButton variant="primary" size="xs" :loading="confirming" @click="abrirConfirmarCierreDeSesion(sesionSeleccionada)">
                <i class="fa-solid fa-check mr-1"></i>Confirmar cierre
              </BaseButton>
            </div>
          </div>
        </div>

        <!-- Resumen -->
        <div class="grid grid-cols-3 gap-3">
          <div class="bg-emerald-50 rounded-xl p-3 text-center">
            <div class="text-[10px] uppercase tracking-wider text-emerald-600 font-semibold">Ingresos</div>
            <div class="font-mono-data font-bold text-lg text-emerald-700">{{ fc(sesionSeleccionada.total_ingresos) }}</div>
          </div>
          <div class="bg-rose-50 rounded-xl p-3 text-center">
            <div class="text-[10px] uppercase tracking-wider text-rose-600 font-semibold">Egresos</div>
            <div class="font-mono-data font-bold text-lg text-rose-700">{{ fc(sesionSeleccionada.total_egresos) }}</div>
          </div>
          <div class="bg-brand-50 rounded-xl p-3 text-center">
            <div class="text-[10px] uppercase tracking-wider text-brand-600 font-semibold">Saldo Final</div>
            <div class="font-mono-data font-bold text-lg text-brand-700">{{ fc(sesionSeleccionada.saldo_final) }}</div>
          </div>
        </div>

        <!-- Cierres por método -->
        <div v-if="sesionSeleccionada.cierres_metodo && sesionSeleccionada.cierres_metodo.length">
          <h4 class="text-sm font-bold text-slate-900 mb-2">Cierres por Método</h4>
          <div class="space-y-2">
            <div v-for="cierre in sesionSeleccionada.cierres_metodo" :key="cierre.medio_pago" class="bg-slate-50 rounded-xl p-3">
              <div class="flex items-center justify-between mb-2">
                <span class="text-sm font-semibold text-slate-700 capitalize">{{ cierre.medio_pago }}</span>
                <BaseBadge :variant="Math.abs(cierre.diferencia) > 0.01 ? 'danger' : 'success'" size="xs">
                  {{ Math.abs(cierre.diferencia) > 0.01 ? 'Discrepancia' : 'OK' }}
                </BaseBadge>
              </div>
              <div class="grid grid-cols-3 gap-2 text-xs">
                <div>
                  <span class="text-slate-500">Esperado:</span>
                  <span class="font-mono-data font-semibold ml-1">{{ fc(cierre.esperado) }}</span>
                </div>
                <div>
                  <span class="text-slate-500">Real:</span>
                  <span class="font-mono-data font-semibold ml-1">{{ fc(cierre.monto_real) }}</span>
                </div>
                <div>
                  <span class="text-slate-500">Diferencia:</span>
                  <span class="font-mono-data font-semibold ml-1" :class="cierre.diferencia >= 0 ? 'text-emerald-600' : 'text-rose-600'">
                    {{ cierre.diferencia >= 0 ? '+' : '' }}{{ fc(cierre.diferencia) }}
                  </span>
                </div>
              </div>
              <div v-if="cierre.descripcion" class="text-[10px] text-slate-500 mt-2 italic">{{ cierre.descripcion }}</div>
            </div>
          </div>
        </div>

        <!-- Movimientos -->
        <div v-if="sesionSeleccionada.ingresos.length || sesionSeleccionada.egresos.length">
          <h4 class="text-sm font-bold text-slate-900 mb-2">Movimientos</h4>
          <div class="max-h-48 overflow-y-auto space-y-1">
            <div v-for="ing in sesionSeleccionada.ingresos" :key="'ing-'+ing.id" class="flex items-center justify-between bg-emerald-50 rounded-lg px-3 py-2">
              <div class="flex-1">
                <div class="text-xs font-medium text-slate-700">{{ ing.descripcion || 'Ingreso' }}</div>
                <div class="text-[10px] text-slate-500">{{ formatHora(ing.fecha) }} · {{ ing.medio_pago }}</div>
              </div>
              <span class="font-mono-data font-bold text-xs text-emerald-600">+{{ fc(ing.monto) }}</span>
            </div>
            <div v-for="egr in sesionSeleccionada.egresos" :key="'egr-'+egr.id" class="flex items-center justify-between bg-rose-50 rounded-lg px-3 py-2">
              <div class="flex-1">
                <div class="text-xs font-medium text-slate-700">{{ egr.descripcion || 'Egreso' }}</div>
                <div class="text-[10px] text-slate-500">{{ formatHora(egr.fecha) }}</div>
              </div>
              <span class="font-mono-data font-bold text-xs text-rose-600">-{{ fc(egr.monto) }}</span>
            </div>
          </div>
        </div>
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
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">{{ metodo }}</div>
            <div class="font-mono-data font-bold text-lg text-slate-900 dark:text-white">{{ fc(monto) }}</div>
          </div>
          <div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-brand-600 font-semibold">Apertura</div>
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
                <BaseButton v-if="cierre.monto_confirmado == null" :loading="confirming" variant="primary" size="xs"
                  @click="abrirConfirmarCierreDeDia(cierre)">
                  <i class="fa-solid fa-check mr-1"></i>Confirmar
                </BaseButton>
                <BaseBadge v-else variant="success" size="xs">
                  <i class="fa-solid fa-circle-check mr-1"></i>Confirmado {{ fc(cierre.monto_confirmado) }}
                  <span v-if="cierre.confirmado_por" class="ml-1">por {{ cierre.confirmado_por }}</span>
                </BaseBadge>
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

    <!-- Modal Confirmar Cierre -->
    <BaseModal v-model="showConfirmarCierre" title="Confirmar Cierre de Caja" size="md" :hide-footer="true">
      <div v-if="cierreAConfirmar" class="space-y-4">
        <div v-if="cierreAConfirmar.fue_automatico" class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3 text-xs">
          <i class="fa-solid fa-triangle-exclamation text-amber-500 mr-1"></i>
          Este cierre fue generado <b>automáticamente</b> por cambio de día con el monto calculado por el sistema. Confirmá el monto real contado.
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Monto del sistema (esperado)</div>
            <div class="font-mono-data font-bold text-lg text-slate-900 dark:text-white">{{ fc(cierreAConfirmar.monto_esperado) }}</div>
          </div>
          <div class="bg-brand-50 dark:bg-brand-900/20 rounded-xl p-3">
            <div class="text-[10px] uppercase tracking-wider text-brand-600 font-semibold">Diferencia</div>
            <div class="font-mono-data font-bold text-lg" :class="Math.abs(Number(confirmarCierreForm.monto) - Number(cierreAConfirmar.monto_esperado)) > 0.01 ? 'text-amber-600' : 'text-brand-700'">
              {{ diferenciaPreviewText }}
            </div>
          </div>
        </div>

        <BaseInput
          v-model.number="confirmarCierreForm.monto"
          label="Monto real confirmado"
          type="number"
          min="0"
          step="0.01"
          placeholder="0.00"
          input-class="font-mono-data"
        />
        <BaseInput
          v-model="confirmarCierreForm.comentario"
          label="Comentario de conciliación (opcional)"
          placeholder="Ej: el efectivo contado dio distinto al sistema..."
          input-class="text-sm"
        />

        <div v-if="confirmarCierreForm.monto != null && Math.abs(Number(confirmarCierreForm.monto) - Number(cierreAConfirmar.monto_esperado)) > 0.01" class="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-3 text-xs text-amber-700 dark:text-amber-300">
          <i class="fa-solid fa-circle-info mr-1"></i>Al confirmar este monto quedará la diferencia registrada y el día pasará a <b>amarillo</b> (corrección). Podés seguir vendiendo normalmente.
        </div>

        <div class="flex gap-3 pt-2">
          <BaseButton variant="secondary" class="flex-1" :disabled="confirming" @click="showConfirmarCierre = false">Cancelar</BaseButton>
          <BaseButton variant="primary" class="flex-1" :loading="confirming" :disabled="confirming || !confirmarCierreForm.monto" @click="confirmarCierreFinal">
            <i :class="confirming ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ confirming ? 'Guardando...' : 'Confirmar monto' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal Nuevo Movimiento -->
    <BaseModal v-model="showNuevoMovimiento" title="Nuevo Movimiento" size="md">
      <div class="space-y-4">
        <BaseSelect v-model="nuevoMovimiento.tipo" label="Tipo" :options="[{ value: 'Ingreso', label: 'Ingreso' }, { value: 'Egreso', label: 'Egreso' }]" />
        <BaseInput v-model.number="nuevoMovimiento.monto" label="Monto" type="number" placeholder="0.00" input-class="font-mono-data" />
        <BaseSelect v-model="nuevoMovimiento.metodo" label="Método" :options="['Efectivo', 'Transferencia', 'Tarjeta']" />
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
            <p class="text-[10px] text-slate-400 mt-1">Monto con el que inicia la caja (efectivo)</p>
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

          <div class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <div class="flex items-center justify-between">
              <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Monto final de apertura</span>
              <span class="font-mono-data font-bold text-2xl text-brand-600 dark:text-brand-400">{{ fc(montoFinalApertura) }}</span>
            </div>
            <p v-if="aperturaForm.monto_retiro > 0" class="text-[10px] text-slate-400 mt-1 text-right">
              {{ fc(aperturaForm.monto_inicial) }} - {{ fc(aperturaForm.monto_retiro) }} = {{ fc(montoFinalApertura) }}
            </p>
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
        <div class="bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800 rounded-xl p-4">
          <div class="flex items-center gap-2 mb-2">
            <i class="fa-solid fa-triangle-exclamation text-brand-500"></i>
            <span class="font-semibold text-brand-700 dark:text-brand-300 text-sm">Confrontá los montos</span>
          </div>
          <p class="text-xs text-brand-600 dark:text-brand-400">
            Ingresá el monto real contado en cada método de pago. El sistema calculará la diferencia automáticamente.
          </p>
        </div>

        <div class="space-y-3">
          <div v-for="metodo in metodosArqueo" :key="metodo.valor" class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl p-4">
            <div class="flex items-center justify-between mb-3">
              <div class="flex items-center gap-2">
                <span class="w-2 h-2 rounded-full" :class="metodo.colorClass"></span>
                <span class="font-semibold text-slate-900 dark:text-white text-sm">{{ metodo.label }}</span>
                <span v-if="metodo.cerrado" class="text-[10px] px-1.5 py-0.5 rounded bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 font-bold">CERRADO</span>
              </div>
              <div class="text-right">
                <p class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">Esperado</p>
                <p class="font-mono-data font-bold text-slate-900 dark:text-white">{{ fc(metodo.esperado) }}</p>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Monto Real Contado</label>
                <input
                  v-model.number="metodo.montoReal"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="0.00"
                  class="w-full px-3 py-2 text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
                  :disabled="metodo.cerrado || closing"
                />
              </div>
              <div>
                <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block mb-1">Diferencia</label>
                <div class="h-[38px] px-3 py-2 flex items-center rounded-lg border border-slate-200 dark:border-slate-700"
                  :class="{
                    'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800': (metodo.montoReal || 0) - metodo.esperado > 0,
                    'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800': (metodo.montoReal || 0) - metodo.esperado < 0,
                    'bg-slate-50 dark:bg-slate-800': (metodo.montoReal || 0) - metodo.esperado === 0 || !metodo.montoReal
                  }"
                >
                  <span v-if="!metodo.montoReal" class="text-xs text-slate-400">—</span>
                  <span v-else-if="(metodo.montoReal || 0) - metodo.esperado > 0" class="font-mono-data font-bold text-emerald-600 dark:text-emerald-400">+{{ fc((metodo.montoReal || 0) - metodo.esperado) }}</span>
                  <span v-else-if="(metodo.montoReal || 0) - metodo.esperado < 0" class="font-mono-data font-bold text-red-600 dark:text-red-400">{{ fc((metodo.montoReal || 0) - metodo.esperado) }}</span>
                  <span v-else class="font-mono-data font-bold text-slate-500">OK</span>
                </div>
              </div>
            </div>

            <div v-if="metodo.montoReal && (metodo.montoReal || 0) - metodo.esperado !== 0" class="mt-2">
              <input
                v-model="metodo.comentario"
                type="text"
                placeholder="Comentario por diferencia (ej: faltante por robo, sobrante por error de precio)"
                class="w-full px-3 py-1.5 text-xs bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20 outline-none transition"
                :disabled="closing"
              />
            </div>
          </div>
        </div>

        <!-- Resumen Total -->
        <div class="bg-slate-100 dark:bg-slate-800 rounded-xl p-4">
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Total Ingresos Esperado</span>
            <span class="font-mono-data font-bold text-lg text-slate-900 dark:text-white">{{ fc(totalEsperado) }}</span>
          </div>
          <div class="flex items-center justify-between mt-2">
            <span class="text-sm font-semibold text-slate-700 dark:text-slate-300">Total Real Contado</span>
            <span class="font-mono-data font-bold text-lg" :class="totalReal === totalEsperado ? 'text-emerald-600 dark:text-emerald-400' : 'text-amber-600 dark:text-amber-400'">{{ fc(totalReal) }}</span>
          </div>
          <div v-if="totalReal !== totalEsperado" class="flex items-center justify-between mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
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
          <BaseButton variant="secondary" class="flex-1" :disabled="closing" @click="showCierreModal = false">
            Cancelar
          </BaseButton>
          <BaseButton variant="danger" class="flex-1" :loading="closing" :disabled="closing" @click="confirmarCierreCaja">
            <i :class="closing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-lock'"></i>
            {{ closing ? 'Cerrando...' : 'Confirmar Cierre de Caja' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { useCajaStore } from '@/stores/caja'
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
import { useSounds } from '@/composables/useSounds'
import { useHeldTickets } from '@/composables/useHeldTickets'

const auth = useAuthStore()
const toast = useToastStore()
const cajaStore = useCajaStore()
const { playOpenCash, playCloseCash } = useSounds()
const cajaResumen = reactive({ metodos_cerrados: [] })
const cierreParcial = reactive({ activo: false, metodo: '', monto_real: 0, comentario: '' })

const movements = ref([])

const syncing = ref(false)
const opening = ref(false)
const closing = ref(false)
const saving = ref(false)
const cerrandoMetodo = ref(false)

const showNuevoMovimiento = ref(false)
const showCierreModal = ref(false)
const showAperturaModal = ref(false)
const cierreComentario = ref('')

const aperturaForm = reactive({
  monto_inicial: 0,
  monto_retiro: 0,
  motivo_retiro: '',
})

const montoFinalApertura = computed(() => {
  return Math.max(0, aperturaForm.monto_inicial - aperturaForm.monto_retiro)
})

const metodosArqueo = reactive([
  { label: 'Efectivo', valor: 'efectivo', esperado: 0, montoReal: 0, comentario: '', cerrado: false, colorClass: 'bg-emerald-500' },
  { label: 'Débito', valor: 'debito', esperado: 0, montoReal: 0, comentario: '', cerrado: false, colorClass: 'bg-blue-500' },
  { label: 'Crédito', valor: 'credito', esperado: 0, montoReal: 0, comentario: '', cerrado: false, colorClass: 'bg-purple-500' },
  { label: 'Transferencia', valor: 'transferencia', esperado: 0, montoReal: 0, comentario: '', cerrado: false, colorClass: 'bg-amber-500' },
])

const nuevoMovimiento = reactive({ tipo: 'Ingreso', monto: 0, metodo: 'Efectivo', comentario: '' })

const totalEsperado = computed(() => metodosArqueo.reduce((sum, m) => sum + m.esperado, 0))
const totalReal = computed(() => metodosArqueo.reduce((sum, m) => sum + (m.montoReal || 0), 0))
const diferenciaTotal = computed(() => totalReal.value - totalEsperado.value)

const ingresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Ingreso' && esDeHoy(m)).reduce((sum, m) => sum + m.monto, 0))
const egresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Egreso' && esDeHoy(m)).reduce((sum, m) => sum + m.monto, 0))
const movimientosIngresos = computed(() => movements.value.filter(m => m.tipo === 'Ingreso' && esDeHoy(m)).length)
const movimientosEgresos = computed(() => movements.value.filter(m => m.tipo === 'Egreso' && esDeHoy(m)).length)

const metodosPago = [
  { label: 'Efectivo', valor: 'efectivo' },
  { label: 'Débito', valor: 'debito' },
  { label: 'Crédito', valor: 'credito' },
  { label: 'Transferencia', valor: 'transferencia' },
]

const movementColumns = [
  { key: 'fecha', label: 'Fecha' },
  { key: 'tipo', label: 'Tipo' },
  { key: 'monto', label: 'Monto' },
  { key: 'metodo', label: 'Método' },
  { key: 'comentario', label: 'Comentario' },
]

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

// Confirmar cierre
const showConfirmarCierre = ref(false)
const confirmando = ref(false)
const cierreAConfirmar = ref(null)
const confirmarCierreForm = reactive({ monto: 0, comentario: '' })

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

function abrirConfirmarCierreDeSesion(sesion) {
  cierreAConfirmar.value = {
    id: sesion.cierre_id,
    monto_esperado: sesion.cierre_monto_esperado || sesion.cierre_monto || 0,
    monto_confirmado_form: null,
    fue_automatico: sesion.fue_automatico,
    origen: 'sesion',
    sesion: sesion,
  }
  confirmarCierreForm.monto = cierreAConfirmar.value.monto_esperado
  confirmarCierreForm.comentario = ''
  showDetalleSesion.value = false
  showConfirmarCierre.value = true
}

function abrirConfirmarCierreDeDia(cierre) {
  cierreAConfirmar.value = {
    id: cierre.id,
    monto_esperado: cierre.monto_esperado || cierre.monto || 0,
    monto_confirmado_form: null,
    fue_automatico: cierre.fue_automatico,
    origen: 'dia',
  }
  confirmarCierreForm.monto = cierreAConfirmar.value.monto_esperado
  confirmarCierreForm.comentario = ''
  showConfirmarCierre.value = true
}

const diferenciaPreviewText = computed(() => {
  if (!cierreAConfirmar.value || confirmarCierreForm.monto == null) return '—'
  const diff = Number(confirmarCierreForm.monto) - Number(cierreAConfirmar.value.monto_esperado)
  return `${diff > 0 ? '+' : ''}${fc(diff)}`
})

async function confirmarCierreFinal() {
  if (!cierreAConfirmar.value) return
  confirmando.value = true
  try {
    const payload = {
      monto_confirmado: Number(confirmarCierreForm.monto),
      comentario: confirmarCierreForm.comentario || '',
    }
    await api.put(`/api/caja/cierre/${cierreAConfirmar.value.id}/confirmar`, payload)
    toast.success('Cierre conciliado correctamente')
    showConfirmarCierre.value = false
    // Recargar vistas
    const fecha = detalleDia.value?.fecha
    if (fecha) {
      const resp = await api.get(`/api/caja/dia?fecha=${fecha}`)
      detalleDia.value = resp
    }
    await fetchCalendario()
    await fetchReportes()
    if (cierreAConfirmar.value.origen === 'sesion') {
      const sesion = cierreAConfirmar.value.sesion
      sesion.cierre_monto_confirmado = Number(confirmarCierreForm.monto)
      sesion.cierre_confirmado_por = auth.currentUser?.nombre || 'Yo'
      sesion.cierre_confirmado_at = new Date().toISOString()
      verDetalleSesion(sesion)
    }
  } catch (e) {
    toast.error('Error al confirmar el cierre: ' + (e?.data?.detail || e?.message || ''))
  } finally {
    confirmando.value = false
  }
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

function verDetalleSesion(sesion) {
  sesionSeleccionada.value = sesion
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
})

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
        metodo: m.medio_pago || '',
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
      if (data.desglose) {
        cajaStore.saldo_actual = (data.desglose.efectivo || 0) +
          (data.desglose.debito || 0) + (data.desglose.credito || 0) +
          (data.desglose.transferencia || 0)
      }
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
  
  const ultimo = cajaStore.ultimoCierre
  if (ultimo && ultimo.monto > 0) {
    aperturaForm.monto_inicial = ultimo.monto
    aperturaForm.monto_retiro = 0
    aperturaForm.motivo_retiro = ''
    showAperturaModal.value = true
  } else {
    aperturaForm.monto_inicial = 0
    aperturaForm.monto_retiro = 0
    aperturaForm.motivo_retiro = ''
    showAperturaModal.value = true
  }
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
  
  opening.value = true
  try {
    await api.post('/api/caja/apertura', {
      monto_inicial: montoFinalApertura.value,
      monto_retiro: aperturaForm.monto_retiro,
      motivo_retiro: aperturaForm.motivo_retiro,
    })
    await cajaStore.fetchEstado()
    await fetchMovimientos()
    showAperturaModal.value = false
    
    let msg = `Caja abierta con $${montoFinalApertura.value.toLocaleString()}`
    if (aperturaForm.monto_retiro > 0) {
      msg += ` (retiro: $${aperturaForm.monto_retiro.toLocaleString()})`
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
  const { heldCount } = useHeldTickets()
  if (heldCount.value > 0) {
    if (!confirm(`Hay ${heldCount.value} ticket(s) apartados en POS. Si cerrás la caja sin recuperarlos se marcarán como huérfanos en la auditoría. ¿Cerrar de todas formas?`)) return
    const held = JSON.parse(localStorage.getItem('apex-pos-held') || '[]')
    held.forEach(t => { t._orphaned = true })
    localStorage.setItem('apex-pos-held', JSON.stringify(held))
  }

  try {
    const data = await api.get('/api/caja/resumen')
    if (data) {
      const desglose = data.desglose || {}
      const apertura = data.apertura || 0
      metodosArqueo.forEach(m => {
        if (m.valor === 'efectivo') {
          m.esperado = (desglose[m.valor] || 0) + apertura
        } else {
          m.esperado = desglose[m.valor] || 0
        }
        m.montoReal = 0
        m.comentario = ''
        m.cerrado = data.metodos_cerrados?.includes(m.valor)
      })
    }
    cierreComentario.value = ''
    showCierreModal.value = true
  } catch (e) {
    toast.error('Error al obtener resumen de caja')
  }
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
    const medioMap = {
      'Efectivo': 'efectivo',
      'Transferencia': 'transferencia',
      'Débito': 'debito',
      'Tarjeta': 'credito',
    }
    const esIngreso = nuevoMovimiento.tipo === 'Ingreso'
    const body = {
      monto: nuevoMovimiento.monto,
      descripcion: nuevoMovimiento.comentario || (esIngreso ? 'Ingreso manual' : 'Egreso manual'),
    }
    if (esIngreso) body.medio_pago = medioMap[nuevoMovimiento.metodo] || 'efectivo'
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

function cancelarCierre() {
  cierreParcial.activo = false
  cierreParcial.metodo = ''
  cierreParcial.monto_real = 0
  cierreParcial.comentario = ''
}

async function cerrarMetodo() {
  if (!cierreParcial.monto_real || cierreParcial.monto_real <= 0) {
    toast.warning('Ingresá un monto real válido')
    return
  }
  cerrandoMetodo.value = true
  try {
    await api.post('/api/caja/cierre-metodo', {
      medio_pago: cierreParcial.metodo,
      monto_real: cierreParcial.monto_real,
      comentario: cierreParcial.comentario || '',
    })
    toast.success(`Método ${cierreParcial.metodo} cerrado correctamente`)
    cierreParcial.activo = false
    cierreParcial.metodo = ''
    cierreParcial.monto_real = 0
    cierreParcial.comentario = ''
    await fetchMovimientos()
    await fetchResumen()
  } catch {
    toast.error('Error al cerrar el método')
  } finally {
    cerrandoMetodo.value = false
  }
}
</script>
