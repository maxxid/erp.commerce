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
      <div class="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
        <h3 class="font-bold text-slate-900 text-sm">Historial de Caja</h3>
        <div class="flex items-center gap-2">
          <div class="flex gap-1">
            <button
              v-for="filtro in filtrosHistorial"
              :key="filtro.valor"
              @click="cambiarFiltroHistorial(filtro.valor)"
              class="px-3 py-1 text-xs font-semibold rounded-lg transition"
              :class="filtroHistorial === filtro.valor
                ? 'bg-brand-500 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'"
            >
              {{ filtro.label }}
            </button>
          </div>
          <BaseButton v-if="filtroHistorial === 'personalizado'" variant="secondary" size="xs" @click="showFechasPersonalizadas = !showFechasPersonalizadas">
            <i class="fa-solid fa-calendar"></i> Fechas
          </BaseButton>
        </div>
      </div>

      <!-- Filtro de fechas personalizadas -->
      <div v-if="showFechasPersonalizadas && filtroHistorial === 'personalizado'" class="px-5 py-3 bg-slate-50 border-b border-slate-100 flex items-center gap-3">
        <div class="flex items-center gap-2">
          <label class="text-xs font-semibold text-slate-600">Desde:</label>
          <input
            v-model="fechaInicio"
            type="date"
            class="px-2 py-1 text-xs border border-slate-200 rounded-lg"
          />
        </div>
        <div class="flex items-center gap-2">
          <label class="text-xs font-semibold text-slate-600">Hasta:</label>
          <input
            v-model="fechaFin"
            type="date"
            class="px-2 py-1 text-xs border border-slate-200 rounded-lg"
          />
        </div>
        <BaseButton variant="primary" size="xs" @click="fetchReportes">
          <i class="fa-solid fa-search"></i> Buscar
        </BaseButton>
      </div>

      <!-- Tabla de sesiones -->
      <div class="overflow-x-auto">
        <table v-if="sesionesCaja.length" class="w-full text-sm">
          <thead class="bg-slate-50 border-b border-slate-100">
            <tr>
              <th class="px-4 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Fecha</th>
              <th class="px-4 py-2 text-left text-xs font-semibold text-slate-500 uppercase">Usuario</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Apertura</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Cierre</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Ingresos</th>
              <th class="px-4 py-2 text-right text-xs font-semibold text-slate-500 uppercase">Egresos</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase">Estado</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase">Discrepancias</th>
              <th class="px-4 py-2 text-center text-xs font-semibold text-slate-500 uppercase">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sesion in sesionesCaja" :key="sesion.apertura_id" class="border-b border-slate-50 hover:bg-slate-50">
              <td class="px-4 py-3">
                <div class="text-xs font-medium text-slate-900">{{ formatFecha(sesion.apertura_fecha) }}</div>
                <div class="text-[10px] text-slate-400">{{ formatHora(sesion.apertura_fecha) }}</div>
              </td>
              <td class="px-4 py-3 text-xs text-slate-600">{{ sesion.apertura_usuario }}</td>
              <td class="px-4 py-3 text-right font-mono-data text-xs text-slate-700">{{ fc(sesion.apertura_monto) }}</td>
              <td class="px-4 py-3 text-right font-mono-data text-xs" :class="sesion.cierre_monto ? 'text-slate-700' : 'text-slate-400'">
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
                <BaseButton variant="ghost" size="xs" @click="verDetalleSesion(sesion)">
                  <i class="fa-solid fa-eye"></i>
                </BaseButton>
              </td>
            </tr>
          </tbody>
        </table>
        <EmptyState v-else icon="fa-clock-rotate-left" title="Sin sesiones" text="No hay sesiones de caja en este período." />
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

const movements = ref([
  { id: 1, fecha: '2026-06-20 09:15', tipo: 'Ingreso', monto: 5000, metodo: 'Efectivo', comentario: 'Venta ticket #1024' },
  { id: 2, fecha: '2026-06-20 10:30', tipo: 'Ingreso', monto: 3200, metodo: 'Transferencia', comentario: 'Venta ticket #1025' },
  { id: 3, fecha: '2026-06-20 11:45', tipo: 'Egreso', monto: 1500, metodo: 'Efectivo', comentario: 'Pago a proveedor' },
  { id: 4, fecha: '2026-06-20 12:00', tipo: 'Ingreso', monto: 8000, metodo: 'Efectivo', comentario: 'Venta ticket #1026' },
  { id: 5, fecha: '2026-06-20 13:30', tipo: 'Egreso', monto: 700, metodo: 'Transferencia', comentario: 'Gastos varios' },
])

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

const ingresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Ingreso').reduce((sum, m) => sum + m.monto, 0))
const egresosHoy = computed(() => movements.value.filter(m => m.tipo === 'Egreso').reduce((sum, m) => sum + m.monto, 0))
const movimientosIngresos = computed(() => movements.value.filter(m => m.tipo === 'Ingreso').length)
const movimientosEgresos = computed(() => movements.value.filter(m => m.tipo === 'Egreso').length)

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

const filtrosHistorial = [
  { valor: 'hoy', label: 'Hoy' },
  { valor: 'semana', label: 'Semana' },
  { valor: 'mes', label: 'Mes' },
  { valor: 'personalizado', label: 'Personalizado' },
]

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
    if (data && data.length) movements.value = data
  } catch { /* fallback to mock */ }
}

async function fetchResumen() {
  try {
    const data = await api.get('/api/caja/resumen')
    if (data) {
      cajaStore.saldo_actual = data.saldo_actual ?? cajaStore.saldo_actual
      cajaResumen.metodos_cerrados = data.metodos_cerrados || []
    }
  } catch { /* fallback to mock */ }
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
    showCierreModal.value = false
    toast.success('Jornada finalizada. Hasta luego.')
    playCloseCash()
    auth.logout()
    router.push('/login')
  } catch (e) {
    toast.error('Error al cerrar caja: ' + (e?.data?.detail || e?.message || ''))
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
    const now = new Date()
    const fecha = now.toISOString().slice(0, 16).replace('T', ' ')
    movements.value.push({
      id: Date.now(),
      fecha,
      tipo: nuevoMovimiento.tipo,
      monto: nuevoMovimiento.monto,
      metodo: nuevoMovimiento.metodo,
      comentario: nuevoMovimiento.comentario || 'Sin comentario',
    })
    if (nuevoMovimiento.tipo === 'Ingreso') {
      cajaStore.saldo_actual += nuevoMovimiento.monto
    } else {
      cajaStore.saldo_actual -= nuevoMovimiento.monto
    }
    nuevoMovimiento.monto = 0
    nuevoMovimiento.comentario = ''
    showNuevoMovimiento.value = false
    toast.success('Movimiento registrado')
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
