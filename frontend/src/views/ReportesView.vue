<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-slate-500 dark:text-slate-400">Reportes y análisis del negocio</p>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Análisis de ventas y rendimiento por período</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton
          variant="secondary"
          size="md"
          :loading="syncing"
          :disabled="syncing"
          @click="syncAll"
        >
          <i class="fa-solid fa-arrows-rotate"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar todo' }}
        </BaseButton>
        <BaseButton variant="primary" size="md">
          <i class="fa-solid fa-file-pdf text-sm"></i>
          Exportar todo
        </BaseButton>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">

      <!-- ==================== SEMANAL ==================== -->
      <BaseCard class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-indigo-100 flex items-center justify-center">
              <i class="fa-solid fa-calendar-week text-indigo-600 text-sm"></i>
            </div>
            <h2 class="font-semibold text-slate-900">Semanal</h2>
          </div>
          <BaseButton
            variant="ghost"
            size="xs"
            icon-only
            title="Sincronizar semanal"
            aria-label="Sincronizar semanal"
            :loading="syncingWeekly"
            :disabled="syncingWeekly"
            @click="syncWeekly"
          >
            <i class="fa-solid fa-arrows-rotate text-xs"></i>
          </BaseButton>
        </div>

        <div class="space-y-2">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-slate-900">{{ formatCurrency(weekly.total) }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">vs semana anterior</span>
            <BaseBadge :variant="weekly.change >= 0 ? 'success' : 'danger'" size="sm">
              <i :class="weekly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(weekly.change) }}%
            </BaseBadge>
          </div>
        </div>

        <div v-if="weeklyBars.length" class="flex items-end gap-1" style="height: 130px;">
          <div
            v-for="(item, idx) in weeklyBars" :key="idx"
            class="flex-1 flex flex-col items-center gap-1 min-w-0"
          >
            <span class="text-[10px] font-mono-data text-slate-500 font-medium leading-none text-center">
              {{ item.ventas > 0 ? formatCurrency(item.ventas) : '' }}
            </span>
            <div
              class="w-full bg-brand-500 rounded-t-md transition-all duration-500 ease-out hover:bg-brand-600 cursor-default"
              :style="{ height: weeklyMax > 0 ? Math.max((item.ventas / weeklyMax) * 96, item.ventas > 0 ? 4 : 0) + 'px' : '0px' }"
            ></div>
            <span class="text-[10px] text-slate-500 font-medium">{{ item.dia }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          icon="fa-chart-bar"
          title="Sin datos para esta semana"
          text=""
          compact
        />

        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in weekly.topProducts.slice(0, 5)" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-slate-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-slate-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
          <p v-if="!weekly.topProducts.length" class="text-xs text-slate-400">Sin datos</p>
        </div>
      </BaseCard>

      <!-- ==================== MENSUAL ==================== -->
      <BaseCard class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
              <i class="fa-solid fa-calendar-check text-emerald-600 text-sm"></i>
            </div>
            <h2 class="font-semibold text-slate-900">Mensual</h2>
          </div>
          <BaseButton
            variant="ghost"
            size="xs"
            icon-only
            title="Sincronizar mensual"
            aria-label="Sincronizar mensual"
            :loading="syncingMonthly"
            :disabled="syncingMonthly"
            @click="syncMonthly"
          >
            <i class="fa-solid fa-arrows-rotate text-xs"></i>
          </BaseButton>
        </div>

        <div class="space-y-2">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-slate-900">{{ formatCurrency(monthly.total) }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">vs mes anterior</span>
            <BaseBadge :variant="monthly.change >= 0 ? 'success' : 'danger'" size="sm">
              <i :class="monthly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(monthly.change) }}%
            </BaseBadge>
          </div>
        </div>

        <div v-if="monthlyBars.length" class="flex items-end gap-1" style="height: 130px;">
          <div
            v-for="(item, idx) in monthlyBars" :key="idx"
            class="flex-1 flex flex-col items-center gap-1 min-w-0"
          >
            <span class="text-[10px] font-mono-data text-slate-500 font-medium leading-none text-center">
              {{ item.ventas > 0 ? formatCurrency(item.ventas) : '' }}
            </span>
            <div
              class="w-full bg-brand-500 rounded-t-md transition-all duration-500 ease-out hover:bg-brand-600 cursor-default"
              :style="{ height: monthlyMax > 0 ? Math.max((item.ventas / monthlyMax) * 96, item.ventas > 0 ? 4 : 0) + 'px' : '0px' }"
            ></div>
            <span class="text-[10px] text-slate-500 font-medium">{{ item.semana }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          icon="fa-chart-bar"
          title="Sin datos para este mes"
          text=""
          compact
        />

        <div v-if="monthlyCategories.length">
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Por categoría</p>
          <div class="flex flex-wrap gap-1.5">
            <BaseBadge
              v-for="(cat, idx) in monthlyCategories" :key="idx"
              :variant="['brand', 'success', 'warning', 'danger', 'info', 'default'][idx % 6]"
              size="sm"
            >
              {{ cat.categoria }}: {{ formatCurrency(cat.total) }}
            </BaseBadge>
          </div>
        </div>

        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in monthly.topProducts.slice(0, 5)" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-slate-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-slate-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
          <p v-if="!monthly.topProducts.length" class="text-xs text-slate-400">Sin datos</p>
        </div>
      </BaseCard>

      <!-- ==================== TRIMESTRAL ==================== -->
      <BaseCard class="space-y-4">
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2.5">
            <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
              <i class="fa-solid fa-calendar-alt text-amber-600 text-sm"></i>
            </div>
            <h2 class="font-semibold text-slate-900">Trimestral</h2>
          </div>
          <BaseButton
            variant="ghost"
            size="xs"
            icon-only
            title="Sincronizar trimestral"
            aria-label="Sincronizar trimestral"
            :loading="syncingQuarterly"
            :disabled="syncingQuarterly"
            @click="syncQuarterly"
          >
            <i class="fa-solid fa-arrows-rotate text-xs"></i>
          </BaseButton>
        </div>

        <div class="space-y-2">
          <div>
            <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Ventas totales</p>
            <p class="text-2xl font-mono-data font-bold text-slate-900">{{ formatCurrency(quarterly.total) }}</p>
          </div>
          <div class="flex items-center gap-2">
            <span class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">vs trim. anterior</span>
            <BaseBadge :variant="quarterly.change >= 0 ? 'success' : 'danger'" size="sm">
              <i :class="quarterly.change >= 0 ? 'fa-solid fa-arrow-trend-up' : 'fa-solid fa-arrow-trend-down'"></i>
              {{ Math.abs(quarterly.change) }}%
            </BaseBadge>
          </div>
        </div>

        <div v-if="quarterlyBars.length" class="flex items-end gap-2" style="height: 130px;">
          <div
            v-for="(item, idx) in quarterlyBars" :key="idx"
            class="flex-1 flex flex-col items-center gap-1 min-w-0"
          >
            <span class="text-[10px] font-mono-data text-slate-500 font-medium leading-none text-center">
              {{ item.ventas > 0 ? formatCurrency(item.ventas) : '' }}
            </span>
            <div
              class="w-full bg-brand-500 rounded-t-md transition-all duration-500 ease-out hover:bg-brand-600 cursor-default"
              :style="{ height: quarterlyMax > 0 ? Math.max((item.ventas / quarterlyMax) * 96, item.ventas > 0 ? 4 : 0) + 'px' : '0px' }"
            ></div>
            <span class="text-[10px] text-slate-500 font-medium">{{ item.mes }}</span>
          </div>
        </div>
        <EmptyState
          v-else
          icon="fa-chart-bar"
          title="Sin datos para este trimestre"
          text=""
          compact
        />

        <div>
          <p class="text-[10px] uppercase tracking-wider text-slate-500 font-semibold mb-2">Top 5 productos</p>
          <div class="space-y-1.5">
            <div v-for="(prod, idx) in quarterly.topProducts.slice(0, 5)" :key="idx" class="flex items-center justify-between text-sm">
              <span class="text-slate-700 truncate mr-2">{{ prod.name }}</span>
              <span class="font-mono-data text-slate-500 text-xs">{{ prod.sold }} u.</span>
            </div>
          </div>
          <p v-if="!quarterly.topProducts.length" class="text-xs text-slate-400">Sin datos</p>
        </div>
      </BaseCard>

    </div>

    <!-- ==================== VENDIDO POR PESO ==================== -->
    <BaseCard>
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-brand-100 flex items-center justify-center">
            <i class="fa-solid fa-mobile-screen-button text-brand-600 text-sm"></i>
          </div>
          <div>
            <h2 class="font-semibold text-slate-900">Recargas de saldo</h2>
            <p class="text-xs text-slate-500">Cuánto se cargó, cuánto se cobró y la ganancia (adicional) del período</p>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <BaseInput v-model="recargasDesde" type="date" size="sm" class="w-40" />
          <span class="text-xs text-slate-400">a</span>
          <BaseInput v-model="recargasHasta" type="date" size="sm" class="w-40" />
          <BaseButton variant="primary" size="sm" :loading="loadingRecargas" @click="loadRecargas">
            <i class="fa-solid fa-filter text-xs"></i>
            Calcular
          </BaseButton>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-4">
        <KpiCard
          label="Cargado"
          :value="reporteRecargas.totales.monto_cargado"
          prefix="$ "
          icon="fa-mobile-screen-button"
          icon-color="brand"
          :decimals="2"
          :animate="false"
        />
        <KpiCard
          label="Cobrado"
          :value="reporteRecargas.totales.total_cobrado"
          prefix="$ "
          icon="fa-cash-register"
          icon-color="info"
          :decimals="2"
          :animate="false"
        />
        <KpiCard
          label="Ganancia (adicional)"
          :value="reporteRecargas.totales.ganancia"
          prefix="$ "
          icon="fa-arrow-trend-up"
          icon-color="success"
          :decimals="2"
          :animate="false"
        />
        <KpiCard
          label="Operaciones"
          :value="reporteRecargas.totales.recargas"
          icon="fa-receipt"
          icon-color="warning"
          :animate="false"
        />
      </div>

      <div v-if="loadingRecargas" class="flex items-center justify-center py-12 text-slate-400 text-sm">
        <i class="fa-solid fa-circle-notch fa-spin mr-2"></i>
        Calculando recargas...
      </div>
      <EmptyState
        v-else-if="!reporteRecargas.por_dia.length"
        icon="fa-mobile-screen-button"
        title="Sin recargas en el período"
        text="Vendé recargas desde el POS dentro del rango de fechas para ver el detalle."
        compact
      />
      <div v-else class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Por día</p>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-slate-200 dark:border-slate-700 text-left">
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Fecha</th>
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Cargado</th>
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Cobrado</th>
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Ganancia</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in reporteRecargas.por_dia" :key="row.fecha" class="border-b border-slate-100 dark:border-slate-800/60">
                  <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">{{ row.fecha }}</td>
                  <td class="py-2.5 px-3 text-right font-mono-data text-slate-700 dark:text-slate-300">{{ formatCurrency(row.cargado) }}</td>
                  <td class="py-2.5 px-3 text-right font-mono-data text-slate-700 dark:text-slate-300">{{ formatCurrency(row.cobrado) }}</td>
                  <td class="py-2.5 px-3 text-right font-mono-data font-bold text-emerald-600 dark:text-emerald-400">{{ formatCurrency(row.ganancia) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <p class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">Por medio de pago del cliente</p>
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-slate-200 dark:border-slate-700 text-left">
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Medio</th>
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Operaciones</th>
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Cargado</th>
                  <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Cobrado</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="row in reporteRecargas.por_medio_pago" :key="row.medio_pago" class="border-b border-slate-100 dark:border-slate-800/60">
                  <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">
                    {{ MEDIO_LABELS[row.medio_pago] || row.medio_pago }}
                  </td>
                  <td class="py-2.5 px-3 text-right font-mono-data text-slate-700 dark:text-slate-300">{{ row.recargas }}</td>
                  <td class="py-2.5 px-3 text-right font-mono-data text-slate-700 dark:text-slate-300">{{ formatCurrency(row.cargado) }}</td>
                  <td class="py-2.5 px-3 text-right font-mono-data font-bold text-slate-900 dark:text-white">{{ formatCurrency(row.cobrado) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </BaseCard>

    <BaseCard>
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
            <i class="fa-solid fa-weight-hanging text-emerald-600 text-sm"></i>
          </div>
          <div>
            <h2 class="font-semibold text-slate-900">Vendido por Peso</h2>
            <p class="text-xs text-slate-500">Kg e importe de los productos fraccionados (panadería, fiambre, etc.)</p>
          </div>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <BaseInput
            v-model="pesoDesde"
            type="date"
            size="sm"
            class="w-40"
          />
          <span class="text-xs text-slate-400">a</span>
          <BaseInput
            v-model="pesoHasta"
            type="date"
            size="sm"
            class="w-40"
          />
          <BaseButton
            variant="primary"
            size="sm"
            :loading="loadingPeso"
            @click="loadVendidoPorPeso"
          >
            <i class="fa-solid fa-filter text-xs"></i>
            Calcular
          </BaseButton>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-4 gap-4 mb-4">
        <KpiCard
          label="Total vendido"
          :value="vendidoPeso.totales.importe_total"
          prefix="$ "
          icon="fa-dollar-sign"
          icon-color="success"
          :decimals="2"
          :animate="false"
        />
        <KpiCard
          label="Kilos vendidos"
          :value="vendidoPeso.totales.peso_total"
          suffix=" kg"
          icon="fa-weight-hanging"
          icon-color="brand"
          :decimals="3"
          :animate="false"
        />
        <KpiCard
          label="Operaciones"
          :value="vendidoPeso.totales.ventas"
          icon="fa-receipt"
          icon-color="info"
          :animate="false"
        />
        <KpiCard
          label="Productos"
          :value="vendidoPeso.totales.productos"
          icon="fa-box"
          icon-color="warning"
          :animate="false"
        />
      </div>

      <div v-if="loadingPeso" class="flex items-center justify-center py-12 text-slate-400 text-sm">
        <i class="fa-solid fa-circle-notch fa-spin mr-2"></i>
        Calculando vendido por peso...
      </div>
      <EmptyState
        v-else-if="!vendidoPeso.items.length"
        icon="fa-weight-hanging"
        title="Sin ventas por peso en el período"
        text="Cargá ventas por kilo en el POS dentro del rango de fechas para ver el detalle."
        compact
      />
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-slate-200 dark:border-slate-700 text-left">
              <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Producto</th>
              <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Kilos</th>
              <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Precio prom./kg</th>
              <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Operaciones</th>
              <th class="py-2 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold text-right">Importe</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="row in vendidoPeso.items"
              :key="row.producto_id"
              class="border-b border-slate-100 dark:border-slate-800/60"
            >
              <td class="py-2.5 px-3 font-semibold text-slate-900 dark:text-white">{{ row.producto_nombre }}</td>
              <td class="py-2.5 px-3 text-right font-mono-data text-slate-700 dark:text-slate-300">
                {{ row.peso_total }} kg
                <span class="text-[10px] text-slate-400">({{ row.peso_min }}–{{ row.peso_max }})</span>
              </td>
              <td class="py-2.5 px-3 text-right font-mono-data text-slate-700 dark:text-slate-300">
                {{ formatCurrency(row.peso_total > 0 ? row.importe_total / row.peso_total : 0) }}
              </td>
              <td class="py-2.5 px-3 text-right font-mono-data text-slate-700 dark:text-slate-300">{{ row.ventas }}</td>
              <td class="py-2.5 px-3 text-right font-mono-data font-bold text-slate-900 dark:text-white">{{ formatCurrency(row.importe_total) }}</td>
            </tr>
          </tbody>
          <tfoot>
            <tr class="border-t-2 border-slate-200 dark:border-slate-700">
              <td class="py-2.5 px-3 text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Total</td>
              <td class="py-2.5 px-3 text-right font-mono-data font-bold text-slate-900 dark:text-white">{{ vendidoPeso.totales.peso_total }} kg</td>
              <td class="py-2.5 px-3"></td>
              <td class="py-2.5 px-3 text-right font-mono-data font-bold text-slate-900 dark:text-white">{{ vendidoPeso.totales.ventas }}</td>
              <td class="py-2.5 px-3 text-right font-mono-data font-bold text-brand-600 dark:text-brand-400">{{ formatCurrency(vendidoPeso.totales.importe_total) }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </BaseCard>

    <!-- ==================== STOCK POR LOTE ==================== -->
    <BaseCard>
      <div class="flex items-center justify-between mb-4">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-lg bg-amber-100 flex items-center justify-center">
            <i class="fa-solid fa-boxes-stacked text-amber-600 text-sm"></i>
          </div>
          <div>
            <h2 class="font-semibold text-slate-900">Stock por Lote</h2>
            <p class="text-xs text-slate-500">Desglose por lote con valorización al costo real</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <BaseInput
            v-model="stockLoteSearch"
            placeholder="Buscar producto..."
            size="sm"
            class="w-56"
            @input="loadStockPorLote"
          >
            <template #prefix>
              <i class="fa-solid fa-magnifying-glass text-slate-400 text-xs"></i>
            </template>
          </BaseInput>
          <BaseButton
            variant="ghost"
            size="sm"
            icon-only
            title="Sincronizar"
            :loading="syncingLotes"
            @click="loadStockPorLote(true)"
          >
            <i class="fa-solid fa-arrows-rotate text-xs"></i>
          </BaseButton>
        </div>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
        <KpiCard
          label="Productos con stock"
          :value="stockPorLote.productos.length"
          icon="fa-box"
          icon-color="brand"
          :animate="false"
        />
        <KpiCard
          label="Lotes activos"
          :value="stockPorLote.productos.reduce((s, p) => s + p.lotes.length, 0)"
          icon="fa-layer-group"
          icon-color="info"
          :animate="false"
        />
        <KpiCard
          label="Valorización total"
          :value="formatCurrency(stockPorLote.valor_total_general)"
          icon="fa-coins"
          icon-color="success"
          :animate="false"
        />
      </div>

      <div v-if="loadingLotes" class="flex items-center justify-center py-12 text-slate-400 text-sm">
        <i class="fa-solid fa-circle-notch fa-spin mr-2"></i>
        Cargando stock por lote...
      </div>
      <EmptyState
        v-else-if="!stockPorLote.productos.length"
        icon="fa-boxes-stacked"
        title="Sin stock registrado"
        text="Recibí mercadería o creá lotes manuales para ver el reporte."
        compact
      />
      <div v-else class="space-y-3 max-h-[500px] overflow-y-auto">
        <div
          v-for="prod in stockPorLote.productos"
          :key="prod.producto_id"
          class="p-3 bg-slate-50 dark:bg-slate-800/40 rounded-xl border border-slate-200 dark:border-slate-700"
        >
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2 min-w-0">
              <i class="fa-solid fa-box text-slate-400 text-sm shrink-0"></i>
              <div class="min-w-0">
                <p class="text-sm font-semibold text-slate-900 dark:text-white truncate">{{ prod.producto_nombre }}</p>
                <p class="text-[10px] text-slate-500 font-mono-data">{{ prod.codigo_barras }}</p>
              </div>
            </div>
            <div class="text-right shrink-0 ml-2">
              <p class="text-sm font-bold text-slate-900 dark:text-white font-mono-data">{{ prod.stock_total }} u.</p>
              <p class="text-[10px] text-slate-500 font-mono-data">{{ formatCurrency(prod.valor_total) }}</p>
            </div>
          </div>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="lote in prod.lotes"
              :key="lote.id"
              class="inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-[10px] font-medium border"
              :class="[
                lote.vencido ? 'bg-red-50 text-red-700 border-red-200' :
                lote.dias_para_vencer != null && lote.dias_para_vencer <= 30 ? 'bg-amber-50 text-amber-700 border-amber-200' :
                'bg-white text-slate-600 border-slate-200'
              ]"
            >
              <i class="fa-solid fa-cubes text-[8px]"></i>
              <span class="font-mono-data font-bold">{{ lote.cantidad_actual }}</span>
              <span v-if="lote.codigo_lote" class="text-slate-500">· {{ lote.codigo_lote }}</span>
              <span v-if="lote.fecha_vencimiento">
                · vto {{ new Date(lote.fecha_vencimiento).toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit' }) }}
              </span>
            </span>
          </div>
        </div>
      </div>
    </BaseCard>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/services/api'
import { formatCurrency } from '@/composables/useUtils'
import { useToastStore } from '@/stores/toasts'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import KpiCard from '@/components/ui/KpiCard.vue'

const toast = useToastStore()

const syncing = ref(false)
const syncingWeekly = ref(false)
const syncingMonthly = ref(false)
const syncingQuarterly = ref(false)

// ── Vendido por peso ──────────────────────────────────────────────────

function fechaISO(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

const hoy = new Date()
const hace30 = new Date()
hace30.setDate(hoy.getDate() - 30)

const pesoDesde = ref(fechaISO(hace30))
const pesoHasta = ref(fechaISO(hoy))
const loadingPeso = ref(false)
const vendidoPeso = ref({ items: [], totales: { peso_total: 0, importe_total: 0, ventas: 0, productos: 0 } })

async function loadVendidoPorPeso() {
  if (!pesoDesde.value || !pesoHasta.value) {
    toast.error('Elegí el rango de fechas')
    return
  }
  loadingPeso.value = true
  try {
    const params = new URLSearchParams({ desde: pesoDesde.value, hasta: pesoHasta.value })
    const data = await api.get(`/api/reportes/vendido-por-peso?${params}`)
    vendidoPeso.value = data || { items: [], totales: { peso_total: 0, importe_total: 0, ventas: 0, productos: 0 } }
  } catch (e) {
    toast.error(e?.data?.detail || 'Error al cargar el reporte de ventas por peso')
  } finally {
    loadingPeso.value = false
  }
}

const recargasDesde = ref(fechaISO(hace30))
const recargasHasta = ref(fechaISO(hoy))
const loadingRecargas = ref(false)
const reporteRecargas = ref({ por_dia: [], por_medio_pago: [], totales: { monto_cargado: 0, total_cobrado: 0, ganancia: 0, recargas: 0, unidades: 0 } })

const MEDIO_LABELS = {
  efectivo: 'Efectivo',
  transferencia: 'Transferencia',
  mercadopago_qr: 'QR MP',
  mercadopago_pos: 'POS MP',
  smartpoint: 'SmartPoint',
  qr_interop: 'QR BCRA',
  debito: 'Débito',
  credito: 'Crédito',
  cta_corriente: 'Cta. Cte.',
}

async function loadRecargas() {
  if (!recargasDesde.value || !recargasHasta.value) {
    toast.error('Elegí el rango de fechas')
    return
  }
  loadingRecargas.value = true
  try {
    const params = new URLSearchParams({ desde: recargasDesde.value, hasta: recargasHasta.value })
    const data = await api.get(`/api/reportes/recargas?${params}`)
    reporteRecargas.value = data || { por_dia: [], por_medio_pago: [], totales: { monto_cargado: 0, total_cobrado: 0, ganancia: 0, recargas: 0, unidades: 0 } }
  } catch (e) {
    toast.error(e?.data?.detail || 'Error al cargar el reporte de recargas')
  } finally {
    loadingRecargas.value = false
  }
}

const stockLoteSearch = ref('')
const loadingLotes = ref(false)
const syncingLotes = ref(false)
const stockPorLote = ref({ productos: [], valor_total_general: 0 })

let stockLoteDebounce = null
async function loadStockPorLote(force = false) {
  if (stockLoteDebounce) clearTimeout(stockLoteDebounce)
  stockLoteDebounce = setTimeout(async () => {
    if (force) syncingLotes.value = true
    else loadingLotes.value = true
    try {
      const params = new URLSearchParams()
      if (stockLoteSearch.value.trim()) params.set('search', stockLoteSearch.value.trim())
      params.set('page_size', '50')
      const data = await api.get(`/api/lotes/reporte/stock-por-lote?${params}`)
      stockPorLote.value = data || { productos: [], valor_total_general: 0 }
    } catch {
      stockPorLote.value = { productos: [], valor_total_general: 0 }
    } finally {
      loadingLotes.value = false
      syncingLotes.value = false
    }
  }, 300)
}

// ── Mock / fallback data ──────────────────────────────────────────────

const weekly = ref({
  total: 2456800,
  change: 4.5,
  topProducts: [
    { name: 'Leche entera 1L', sold: 245 },
    { name: 'Pan francés', sold: 198 },
    { name: 'Yerba mate 500g', sold: 156 },
    { name: 'Queso cremoso 1kg', sold: 134 },
    { name: 'Aceite girasol 1.5L', sold: 112 },
  ],
})

const weeklyBars = ref([
  { dia: 'Lun', ventas: 412000 },
  { dia: 'Mar', ventas: 389500 },
  { dia: 'Mié', ventas: 456200 },
  { dia: 'Jue', ventas: 512800 },
  { dia: 'Vie', ventas: 528300 },
  { dia: 'Sáb', ventas: 598000 },
  { dia: 'Dom', ventas: 0 },
])

const monthly = ref({
  total: 9875200,
  change: -2.3,
  topProducts: [
    { name: 'Leche entera 1L', sold: 980 },
    { name: 'Carne picada común', sold: 845 },
    { name: 'Pan francés', sold: 790 },
    { name: 'Yerba mate 500g', sold: 632 },
    { name: 'Huevos x30', sold: 548 },
  ],
})

const monthlyBars = ref([
  { semana: 'Sem 1', ventas: 2340000 },
  { semana: 'Sem 2', ventas: 2567800 },
  { semana: 'Sem 3', ventas: 2456800 },
  { semana: 'Sem 4', ventas: 3154600 },
])

const monthlyCategories = ref([
  { categoria: 'Lácteos', total: 2340000 },
  { categoria: 'Panadería', total: 1890000 },
  { categoria: 'Carnes', total: 3120000 },
  { categoria: 'Almacén', total: 1560000 },
  { categoria: 'Bebidas', total: 965200 },
])

const quarterly = ref({
  total: 29876500,
  change: 8.2,
  topProducts: [
    { name: 'Leche entera 1L', sold: 2980 },
    { name: 'Carne picada común', sold: 2540 },
    { name: 'Pan francés', sold: 2310 },
    { name: 'Yerba mate 500g', sold: 1890 },
    { name: 'Aceite girasol 1.5L', sold: 1720 },
  ],
})

const quarterlyBars = ref([
  { mes: 'Abr', ventas: 9875200 },
  { mes: 'May', ventas: 10234500 },
  { mes: 'Jun', ventas: 12046800 },
])

// ── Computed: max value per dataset for bar scaling ───────────────────

const weeklyMax = computed(() => {
  const vals = weeklyBars.value.map(b => b.ventas || 0)
  return vals.length ? Math.max(...vals) : 0
})

const monthlyMax = computed(() => {
  const vals = monthlyBars.value.map(b => b.ventas || 0)
  return vals.length ? Math.max(...vals) : 0
})

const quarterlyMax = computed(() => {
  const vals = quarterlyBars.value.map(b => b.ventas || 0)
  return vals.length ? Math.max(...vals) : 0
})

// ── Category badge colors ─────────────────────────────────────────────

const catColors = [
  'bg-blue-50 text-blue-700',
  'bg-emerald-50 text-emerald-700',
  'bg-amber-50 text-amber-700',
  'bg-purple-50 text-purple-700',
  'bg-rose-50 text-rose-700',
  'bg-cyan-50 text-cyan-700',
  'bg-indigo-50 text-indigo-700',
  'bg-teal-50 text-teal-700',
]

function catBadgeColor(idx) {
  return catColors[idx % catColors.length]
}

// ── API mapping helpers ───────────────────────────────────────────────

function mapTopProducts(list) {
  return (list || []).map(p => ({
    name: p.nombre,
    sold: p.cantidad,
  }))
}

// ── Sync all ──────────────────────────────────────────────────────────

async function syncAll() {
  syncing.value = true
  try {
    await Promise.all([syncWeekly(true), syncMonthly(true), syncQuarterly(true), loadVendidoPorPeso()])
    toast.success('Datos sincronizados')
  } catch {
    toast.error('No se pudieron sincronizar los datos')
  }
  syncing.value = false
}

// ── Per-period sync ───────────────────────────────────────────────────

async function syncWeekly(silent = false) {
  syncingWeekly.value = true
  try {
    const w = await api.get('/api/dashboard/semanal')
    if (w) {
      weekly.value = {
        total: w.ventas_actual ?? weekly.value.total,
        change: w.diff_ventas_pct ?? weekly.value.change,
        topProducts: mapTopProducts(w.top_productos_semana || w.top_productos).length
          ? mapTopProducts(w.top_productos_semana || w.top_productos)
          : weekly.value.topProducts,
      }
      if (w.dias && w.dias.length) {
        weeklyBars.value = w.dias.map(d => ({ dia: d.dia, ventas: d.ventas }))
      }
    }
    if (!silent) toast.success('Reporte semanal actualizado')
  } catch {
    if (!silent) toast.error('Error al cargar reporte semanal')
  }
  syncingWeekly.value = false
}

async function syncMonthly(silent = false) {
  syncingMonthly.value = true
  try {
    const m = await api.get('/api/dashboard/mensual')
    if (m) {
      monthly.value = {
        total: m.ventas_actual ?? monthly.value.total,
        change: m.diff_ventas_pct ?? monthly.value.change,
        topProducts: mapTopProducts(m.top_productos).length
          ? mapTopProducts(m.top_productos)
          : monthly.value.topProducts,
      }
      if (m.semanas && m.semanas.length) {
        monthlyBars.value = m.semanas.map(s => ({ semana: s.semana, ventas: s.ventas }))
      }
      if (m.por_categoria && m.por_categoria.length) {
        monthlyCategories.value = m.por_categoria
      }
    }
    if (!silent) toast.success('Reporte mensual actualizado')
  } catch {
    if (!silent) toast.error('Error al cargar reporte mensual')
  }
  syncingMonthly.value = false
}

async function syncQuarterly(silent = false) {
  syncingQuarterly.value = true
  try {
    const q = await api.get('/api/dashboard/trimestral')
    if (q) {
      quarterly.value = {
        total: q.ventas_actual ?? quarterly.value.total,
        change: q.diff_ventas_pct ?? quarterly.value.change,
        topProducts: mapTopProducts(q.top_productos).length
          ? mapTopProducts(q.top_productos)
          : quarterly.value.topProducts,
      }
      if (q.meses && q.meses.length) {
        quarterlyBars.value = q.meses.map(m => ({ mes: m.mes, ventas: m.ventas }))
      }
    }
    if (!silent) toast.success('Reporte trimestral actualizado')
  } catch {
    if (!silent) toast.error('Error al cargar reporte trimestral')
  }
  syncingQuarterly.value = false
}

onMounted(() => { syncAll(); loadStockPorLote(); loadVendidoPorPeso(); loadRecargas() })
</script>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.animate-spin {
  animation: spin 1.5s linear infinite;
}
</style>
