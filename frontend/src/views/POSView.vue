<template>
  <div class="space-y-5">
    <!-- Header -->
    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
      <div>
        <h2 class="text-2xl font-bold text-slate-950 dark:text-white font-display">POS de Ventas</h2>
        <p class="text-sm text-slate-500 dark:text-slate-400 mt-1">Punto de Venta rápido</p>
      </div>
      <div class="flex items-center gap-3">
        <button
          type="button"
          class="w-9 h-9 rounded-xl flex items-center justify-center border border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          :title="showStatsPanel ? 'Ocultar panel lateral' : 'Mostrar panel lateral'"
          @click="showStatsPanel = !showStatsPanel"
        >
          <i :class="showStatsPanel ? 'fa-solid fa-chevron-right' : 'fa-solid fa-chevron-left'" class="text-sm"></i>
        </button>
        <BaseBadge variant="default" size="sm">
          <i class="fa-solid fa-user mr-1"></i>
          {{ auth.currentUser?.nombre || auth.currentUser?.username }}
        </BaseBadge>
        <BaseBadge :variant="cajaStore.abierta ? 'success' : 'danger'" size="sm" :dot="true">
          {{ cajaStore.abierta ? 'CAJA ABIERTA' : 'CAJA CERRADA' }}
        </BaseBadge>
        <button
          v-if="heldCount"
          type="button"
          class="relative w-9 h-9 rounded-xl flex items-center justify-center border border-slate-200 dark:border-slate-700 text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition-colors"
          title="Tickets apartados"
          @click="showRecallDropdown = !showRecallDropdown"
        >
          <i class="fa-solid fa-clock-rotate-left text-sm"></i>
          <span class="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-amber-500 text-white text-[8px] font-bold flex items-center justify-center">{{ heldCount }}</span>
        </button>
      </div>
    </div>

    <!-- Tickets sospechosos banner -->
    <Transition
      enter-active-class="transition duration-300 ease-out-expo"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="hasSuspicious && showSusWarning"
        class="p-3 rounded-2xl border bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800/50 flex items-center gap-3"
      >
        <div class="w-10 h-10 rounded-xl bg-amber-100 dark:bg-amber-800/40 flex items-center justify-center text-amber-600 dark:text-amber-300 shrink-0">
          <i class="fa-solid fa-clock-rotate-left text-lg"></i>
        </div>
        <div class="flex-1">
          <p class="text-sm font-bold text-amber-800 dark:text-amber-200">{{ suspiciousTickets.length }} ticket(s) apartados hace más de 2 horas</p>
          <p class="text-xs text-amber-600 dark:text-amber-300">Posible fraude. Revisar y confirmar/descartar en el panel de tickets apartados.</p>
        </div>
        <button type="button" class="shrink-0 w-7 h-7 rounded-lg flex items-center justify-center text-amber-400 hover:text-amber-600 hover:bg-amber-100 dark:hover:bg-amber-800/40 transition" @click="showSusWarning = false">
          <i class="fa-solid fa-xmark"></i>
        </button>
      </div>
    </Transition>

    <!-- Caja cerrada banner -->
    <Transition
      enter-active-class="transition duration-300 ease-out-expo"
      enter-from-class="opacity-0 -translate-y-2"
      enter-to-class="opacity-100 translate-y-0"
      leave-active-class="transition duration-200 ease-in"
      leave-from-class="opacity-100 translate-y-0"
      leave-to-class="opacity-0 -translate-y-2"
    >
      <div
        v-if="!cajaStore.abierta"
        class="p-4 rounded-2xl border bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800/50 flex items-center gap-4"
      >
        <div class="w-12 h-12 rounded-xl bg-red-100 dark:bg-red-800/40 flex items-center justify-center text-red-600 dark:text-red-300 shrink-0">
          <i class="fa-solid fa-lock text-xl"></i>
        </div>
        <div class="flex-1">
          <p class="text-sm font-bold text-red-800 dark:text-red-200">La caja está cerrada</p>
          <p class="text-xs text-red-600 dark:text-red-300">Abrí la caja en <strong>Arqueos y Caja</strong> para poder confirmar ventas.</p>
        </div>
        <BaseButton variant="primary" size="sm" @click="$router.push('/caja')">Abrir caja</BaseButton>
      </div>
    </Transition>

    <div class="grid grid-cols-1 xl:grid-cols-12 gap-6">
      <!-- COLUMN 1: Product Catalog (5 cols) -->
      <div :class="showStatsPanel ? 'xl:col-span-5' : 'xl:col-span-8'" class="space-y-4">
        <BaseCard padding="md">
          <BaseInput
            ref="barcodeInput"
            v-model="posLookupCode"
            label="Código de Barras"
            placeholder="Escanear o escribir código..."
            input-class="font-mono-data"
            size="lg"
          @input="handlePOSInput"
          @enter="triggerPOSLookup"
          >
            <template #prefix>
              <i class="fa-solid fa-barcode text-slate-400"></i>
            </template>
          </BaseInput>

          <!-- Lookup result -->
          <Transition
            enter-active-class="transition duration-200 ease-out-expo"
            enter-from-class="opacity-0 translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-150 ease-in"
            leave-from-class="opacity-100 translate-y-0"
            leave-to-class="opacity-0 translate-y-1"
          >
            <div v-if="lookupProduct._loading || lookupProduct._searchingExternal || lookupProduct.id || lookupProduct._searched || lookupProduct._manualEntry" class="mt-3">
              <!-- Loading local -->
              <div v-if="lookupProduct._loading" class="flex items-center justify-center py-6">
                <i class="fa-solid fa-circle-notch fa-spin text-brand-500 text-xl"></i>
                <span class="ml-2 text-sm text-slate-500 dark:text-slate-400">Buscando en base local...</span>
              </div>
              <!-- Searching external with spinning border -->
              <div v-else-if="lookupProduct._searchingExternal" class="lookup-external-searching relative p-[2px] rounded-xl overflow-hidden">
                <div class="absolute inset-0 bg-gradient-to-r from-orange-500 via-amber-400 to-orange-600 animate-spin-slow"></div>
                <div class="relative bg-slate-900 rounded-[10px] p-4">
                  <div class="flex items-center gap-3 mb-3">
                    <div class="w-10 h-10 rounded-lg bg-orange-500/20 flex items-center justify-center text-orange-400 shrink-0">
                      <i class="fa-solid fa-globe text-lg animate-pulse"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-bold text-white truncate">Buscando en fuentes externas...</p>
                      <p class="text-xs text-slate-400">{{ lookupProduct._barcode || '' }}</p>
                    </div>
                    <i class="fa-solid fa-circle-notch fa-spin text-orange-400 text-xl"></i>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <BaseBadge variant="warning" size="xs">
                      <i class="fa-solid fa-magnifying-glass mr-1"></i> Carrefour
                    </BaseBadge>
                    <BaseBadge variant="warning" size="xs">
                      <i class="fa-solid fa-magnifying-glass mr-1"></i> Vea
                    </BaseBadge>
                    <BaseBadge variant="warning" size="xs">
                      <i class="fa-solid fa-magnifying-glass mr-1"></i> Disco
                    </BaseBadge>
                  </div>
                  <p class="text-[10px] text-slate-500 mt-2">Podés seguir escaneando mientras tanto</p>
                </div>
              </div>
              <!-- Found externally or locally -->
              <div v-else-if="lookupProduct.id" class="p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-100 dark:border-brand-800/40 rounded-xl">
                <div class="flex items-start justify-between">
                  <div class="flex items-start gap-3">
                    <div class="w-12 h-12 rounded-xl bg-brand-100 dark:bg-brand-800/40 flex items-center justify-center text-brand-600 dark:text-brand-300 shrink-0">
                      <i class="fa-solid fa-box text-lg"></i>
                    </div>
                    <div class="flex-1 min-w-0">
                      <p class="text-sm font-bold text-slate-900 dark:text-white truncate">{{ lookupProduct.nombre }}</p>
                      <p class="text-xs text-slate-500 dark:text-slate-400">{{ lookupProduct.marca }}</p>
                      <div class="flex items-center gap-3 mt-1.5">
                        <span class="text-sm font-bold font-mono-data text-brand-600 dark:text-brand-400">{{ fc(lookupProduct.precio_venta) }}</span>
                        <BaseBadge variant="default" size="xs">Stock: {{ lookupProduct.stock_actual }}</BaseBadge>
                      </div>
                    </div>
                  </div>
                  <button type="button" class="w-7 h-7 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 hover:bg-slate-100 dark:hover:bg-slate-800 transition" @click="closeLookupPanel">
                    <i class="fa-solid fa-xmark text-sm"></i>
                  </button>
                </div>
                <div class="flex items-center gap-2 mt-3">
                  <div class="relative">
                    <input
                      v-model.number="lookupProduct._qty"
                      type="number"
                      min="1"
                      placeholder="1"
                      class="w-16 pl-6 pr-2 py-1.5 text-sm text-center font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                    >
                    <span class="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400">u.</span>
                  </div>
                  <div class="relative flex-1">
                    <span class="absolute left-2 top-1/2 -translate-y-1/2 text-sm text-slate-400">$</span>
                    <input
                      v-model.number="lookupProduct._price"
                      type="number"
                      step="0.01"
                      placeholder="0.00"
                      class="w-full pl-6 pr-2 py-1.5 text-sm text-center font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                    >
                  </div>
                  <BaseButton size="sm" @click="addFoundToCart">
                    <i class="fa-solid fa-plus mr-1"></i> {{ lookupProduct.codigo_barras }}
                  </BaseButton>
                </div>
              </div>
              <!-- Manual entry (not found externally) -->
              <div v-else-if="lookupProduct._manualEntry" class="p-3 bg-red-50 dark:bg-red-900/20 border-2 border-red-400 dark:border-red-600 rounded-xl">
                <div class="flex items-center justify-between mb-3">
                  <div class="flex items-center gap-2">
                    <i class="fa-solid fa-circle-xmark text-red-500"></i>
                    <p class="text-xs font-bold text-red-700 dark:text-red-300">No encontrado en fuentes externas</p>
                  </div>
                  <button type="button" class="w-7 h-7 rounded-lg flex items-center justify-center text-red-400 hover:text-red-600 hover:bg-red-100 dark:hover:bg-red-900/40 transition" @click="closeLookupPanel">
                    <i class="fa-solid fa-xmark text-sm"></i>
                  </button>
                </div>
                <p class="text-[10px] text-red-600 dark:text-red-400 mb-3">Ingresá los datos manualmente. Se guardará como <strong>*MANUAL*</strong> para revisión posterior.</p>
                <div class="space-y-2">
                  <BaseInput
                    v-model="lookupProduct._manualNombre"
                    placeholder="Nombre del producto"
                    size="sm"
                    input-class="text-sm"
                  />
                  <div class="grid grid-cols-2 gap-2">
                    <div class="relative">
                      <span class="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 z-10">$</span>
                      <BaseInput
                        v-model.number="lookupProduct._manualPrecio"
                        type="number"
                        step="0.01"
                        min="0"
                        placeholder="Precio"
                        size="sm"
                        input-class="text-sm font-mono-data text-right pl-6"
                      />
                    </div>
                    <div class="relative">
                      <span class="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-slate-400 z-10">u.</span>
                      <BaseInput
                        v-model.number="lookupProduct._manualQty"
                        type="number"
                        min="1"
                        placeholder="Cantidad"
                        size="sm"
                        input-class="text-sm font-mono-data text-right pl-6"
                      />
                    </div>
                  </div>
                  <BaseButton size="sm" block @click="addManualToCart">
                    <i class="fa-solid fa-plus mr-1"></i> Agregar al carrito
                  </BaseButton>
                </div>
              </div>
              <!-- Not found (simple error) -->
              <div v-else-if="lookupProduct._searched" class="p-3 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/40 rounded-xl text-xs text-red-600 dark:text-red-300 font-medium text-center flex items-center justify-center gap-2">
                <i class="fa-solid fa-circle-xmark"></i>
                Producto no encontrado
              </div>
            </div>
          </Transition>
        </BaseCard>

        <BaseInput
          ref="textSearchRef"
          v-model="posTextSearch"
          placeholder="Buscar producto por nombre, marca o código..."
          size="md"
          @enter="handleTextSearchEnter"
        >
          <template #prefix>
            <i class="fa-solid fa-magnifying-glass text-slate-400"></i>
          </template>
        </BaseInput>

        <!-- Category chips -->
        <div class="flex flex-wrap gap-2">
          <button
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border"
            :class="!selectedPOSCategory
              ? 'bg-brand-600 text-white border-brand-600 shadow-sm shadow-brand-500/20'
              : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
            @click="selectedPOSCategory = null"
          >
            Todos
          </button>
          <button
            v-for="cat in categories"
            :key="cat.id"
            type="button"
            class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border"
            :class="selectedPOSCategory === cat.id
              ? 'bg-brand-600 text-white border-brand-600 shadow-sm shadow-brand-500/20'
              : 'bg-white dark:bg-slate-900 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'"
            @click="selectedPOSCategory = cat.id"
          >
            {{ cat.nombre }}
          </button>
        </div>

        <!-- Product grid -->
        <div class="grid grid-cols-2 sm:grid-cols-3 gap-3 max-h-[520px] overflow-y-auto pr-1">
          <TransitionGroup
            enter-active-class="transition duration-200 ease-out-expo"
            enter-from-class="opacity-0 scale-95"
            enter-to-class="opacity-100 scale-100"
            leave-active-class="transition duration-150 ease-in"
            leave-from-class="opacity-100 scale-100"
            leave-to-class="opacity-0 scale-95"
            move-class="transition duration-200 ease-out-expo"
          >
            <button
              v-for="p in filteredPOSProducts"
              :key="p.id"
              type="button"
              class="group relative text-left bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 p-3 rounded-xl shadow-sm transition-all duration-200 ease-out-expo hover:shadow-md hover:border-brand-300 dark:hover:border-brand-700 hover:-translate-y-0.5 active:scale-[0.98] focus-visible:ring-2 focus-visible:ring-brand-500/40"
              @click="addToCart(p)"
            >
              <div class="flex items-center gap-2 mb-2">
                <div class="w-9 h-9 rounded-lg bg-brand-50 dark:bg-brand-900/30 flex items-center justify-center text-brand-600 dark:text-brand-400 shrink-0 group-hover:scale-105 transition-transform">
                  <i class="fa-solid fa-box text-xs"></i>
                </div>
                <p class="text-xs font-bold text-slate-900 dark:text-white truncate leading-tight">{{ p.nombre }}</p>
              </div>
              <p class="text-[10px] text-slate-400 dark:text-slate-500 truncate">{{ p.marca }}</p>
              <div class="flex items-center justify-between mt-2">
                <span class="text-sm font-bold font-mono-data text-brand-600 dark:text-brand-400">{{ fc(p.precio_venta) }}</span>
                <BaseBadge
                  :variant="p.stock_actual <= 5 ? 'danger' : 'default'"
                  size="xs"
                >
                  {{ p.stock_actual }} u
                </BaseBadge>
              </div>
            </button>
          </TransitionGroup>
          <div v-if="!filteredPOSProducts.length" class="col-span-full">
            <EmptyState icon="fa-box-open" title="Sin productos" text="No hay productos que coincidan con tu búsqueda." compact />
          </div>
        </div>
      </div>

      <!-- COLUMN 2: Cart (4 cols) -->
      <div class="xl:col-span-4 space-y-4">
        <BaseCard padding="none" class="overflow-hidden">
          <div class="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center gap-2">
            <i class="fa-solid fa-cash-register text-brand-500"></i>
            <span class="text-sm font-bold text-slate-900 dark:text-white">Carrito</span>
            <BaseBadge variant="default" size="xs" class="ml-auto">{{ cart.items.length }} productos</BaseBadge>
          </div>

          <div class="max-h-[340px] overflow-y-auto">
            <TransitionGroup
              tag="div"
              class="divide-y divide-slate-50 dark:divide-slate-800/70"
              enter-active-class="transition duration-250 ease-out-expo"
              enter-from-class="opacity-0 -translate-x-3"
              enter-to-class="opacity-100 translate-x-0"
              leave-active-class="transition duration-200 ease-in"
              leave-from-class="opacity-100 translate-x-0"
              leave-to-class="opacity-0 translate-x-3"
              move-class="transition duration-200 ease-out-expo"
            >
              <div
                v-for="(item, idx) in cart.items"
                :key="`${item.producto_id}-${item.precio_unitario}`"
                class="p-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                <div class="w-10 h-10 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-500 dark:text-slate-400 shrink-0">
                  <i class="fa-solid fa-box text-xs"></i>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-bold text-slate-900 dark:text-white truncate">{{ item.nombre }}</p>
                  <p class="text-[10px] text-slate-400 dark:text-slate-500 font-mono-data">{{ item.codigo_barras }}</p>
                  <div class="flex items-center gap-2 mt-1.5">
                    <button
                      type="button"
                      aria-label="Disminuir cantidad"
                      class="w-6 h-6 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs flex items-center justify-center transition active:scale-95"
                      @click="updateCartQty(idx, item.cantidad - 1)"
                    >&minus;</button>
                    <span class="text-xs font-mono-data font-bold text-slate-700 dark:text-slate-200 w-6 text-center">{{ item.cantidad }}</span>
                    <button
                      type="button"
                      aria-label="Aumentar cantidad"
                      class="w-6 h-6 rounded-md bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs flex items-center justify-center transition active:scale-95"
                      @click="updateCartQty(idx, item.cantidad + 1)"
                    >+</button>
                    <span class="text-xs font-mono-data font-bold text-brand-600 dark:text-brand-400 ml-auto">{{ fc((item._precio_neto || item.precio_unitario) * item.cantidad) }}</span>
                    <BaseBadge v-if="item.oferta" size="xs" variant="warning" class="ml-1">{{ item.oferta.tipo === 'porcentaje' ? item.oferta.valor + '%' : item.oferta.tipo === 'monto_fijo' ? '$' + item.oferta.valor : '2x1' }}</BaseBadge>
                  </div>
                </div>
                <button
                  type="button"
                  aria-label="Eliminar producto"
                  class="w-7 h-7 rounded-lg text-rose-400 hover:text-rose-600 dark:hover:text-rose-300 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex items-center justify-center transition flex-shrink-0"
                  @click="removeFromCart(idx)"
                >
                  <i class="fa-solid fa-trash text-[10px]"></i>
                </button>
              </div>
            </TransitionGroup>

            <div v-if="!cart.items.length" class="p-8 text-center">
              <div class="w-16 h-16 rounded-2xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center mx-auto mb-3">
                <i class="fa-solid fa-basket-shopping text-slate-300 dark:text-slate-600 text-2xl"></i>
              </div>
              <p class="text-sm text-slate-500 dark:text-slate-400 font-semibold">Carrito vacío</p>
              <p class="text-xs text-slate-400 dark:text-slate-500 mt-1">Escaneá o seleccioná productos</p>
            </div>
          </div>
        </BaseCard>

        <!-- Summary -->
        <BaseCard padding="md" class="space-y-4">
          <div class="flex justify-between text-sm">
            <span class="text-slate-500 dark:text-slate-400">Subtotal</span>
            <span class="font-mono-data font-bold text-slate-800 dark:text-slate-200">{{ fc(cart.subtotal) }}</span>
          </div>

          <div class="flex items-center justify-between">
            <span class="text-xs font-bold text-slate-500 dark:text-slate-400 uppercase">Descuento</span>
            <div class="flex items-center gap-2">
              <input
                v-model.number="cart.descuento"
                type="number"
                step="0.01"
                min="0"
                placeholder="0"
                class="w-24 px-2 py-1.5 text-xs text-right font-mono-data bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
                @input="recalcCart"
              >
              <span class="text-[10px] text-slate-400 dark:text-slate-500">$</span>
            </div>
          </div>

          <hr class="border-slate-100 dark:border-slate-800">

          <div class="flex justify-between items-end">
            <span class="text-sm font-bold text-slate-900 dark:text-white">Total</span>
            <span class="text-2xl font-bold font-mono-data text-brand-600 dark:text-brand-400">{{ fc(cart.total) }}</span>
          </div>

          <!-- Payment method segmented -->
          <div ref="pagoSection" tabindex="0" @keydown="handlePagoKeydown">
            <label class="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase block mb-2">
              Medio de Pago
              <span class="text-slate-300 dark:text-slate-600 ml-2 font-normal">Atajos: 1-5, ←→, Enter</span>
            </label>
            <div class="grid grid-cols-5 gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl">
              <button
                v-for="(medio, idx) in mediosPago"
                :key="medio.value"
                type="button"
                class="flex flex-col items-center gap-1 py-2 rounded-lg text-[10px] font-semibold transition-all duration-200 outline-none focus-visible:ring-2 focus-visible:ring-brand-500/40"
                :class="cart.medio_pago === medio.value
                  ? 'bg-white dark:bg-slate-700 text-brand-600 dark:text-brand-400 shadow-sm'
                  : 'text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-700/50'"
                @click="cart.medio_pago = medio.value"
              >
                <i :class="`fa-solid ${medio.icon}`"></i>
                <span class="hidden sm:inline">{{ medio.label }}</span>
                <span class="sm:hidden">{{ idx + 1 }}</span>
              </button>
            </div>
          </div>

          <div v-if="cart.medio_pago === 'transferencia' && (bankConfig.banco_nombre || bankConfig.banco_alias)" class="p-3 bg-sky-50 dark:bg-sky-900/20 border border-sky-200 dark:border-sky-800 rounded-xl">
            <p class="text-[10px] font-bold text-sky-700 dark:text-sky-300 mb-2">
              <i class="fa-solid fa-building-columns mr-1"></i>Datos para Transferencia
            </p>
            <div class="space-y-1 text-[10px] text-slate-600 dark:text-slate-300">
              <p v-if="bankConfig.banco_nombre"><span class="font-semibold">Banco:</span> {{ bankConfig.banco_nombre }}</p>
              <p v-if="bankConfig.banco_titular"><span class="font-semibold">Titular:</span> {{ bankConfig.banco_titular }}</p>
              <p v-if="bankConfig.banco_alias"><span class="font-semibold">Alias:</span> {{ bankConfig.banco_alias }}</p>
            </div>
          </div>

          <BaseSelect
            v-model="cart.cliente_id"
            label="Cliente"
            placeholder=""
            :options="[{ value: '', label: 'Consumidor Final' }, ...clientes.map(c => ({ value: c.id, label: c.nombre }))]"
            option-value="value"
            option-label="label"
            size="sm"
          />

          <BaseButton
            variant="primary"
            block
            size="lg"
            :loading="confirmando"
            :disabled="!cart.items.length"
            class="!bg-emerald-600 hover:!bg-emerald-700 !shadow-emerald-500/20"
            @click="confirmarVenta"
          >
            <i :class="confirmando ? 'fa-solid fa-circle-notch fa-spin' : 'fa-solid fa-check-circle'"></i>
            {{ confirmando ? 'Procesando...' : 'Confirmar Venta' }}
          </BaseButton>

          <div class="flex items-center gap-2 pt-1">
            <button
              v-if="cart.items.length"
              type="button"
              class="flex-1 text-amber-600 dark:text-amber-400 hover:text-amber-700 dark:hover:text-amber-300 text-xs font-semibold transition text-center py-1.5 rounded-lg hover:bg-amber-50 dark:hover:bg-amber-900/10"
              @click="holdTicket"
            >
              <i class="fa-solid fa-clock-rotate-left mr-1"></i> Hold
            </button>
            <button
              v-if="cart.items.length"
              type="button"
              class="flex-1 text-rose-500 hover:text-rose-600 dark:hover:text-rose-400 text-xs font-semibold transition text-center py-1.5 rounded-lg hover:bg-rose-50 dark:hover:bg-rose-900/10"
              @click="vaciarCarrito"
            >
              <i class="fa-solid fa-trash mr-1"></i> Vaciar
            </button>
          </div>

          <!-- Recall Dropdown -->
          <div v-if="showRecallDropdown && heldTickets.length" class="border-t border-slate-100 dark:border-slate-700 pt-2 mt-1">
            <p class="text-[10px] font-bold text-slate-400 uppercase mb-1.5 px-1">Tickets apartados</p>
            <div class="space-y-1 max-h-40 overflow-y-auto">
              <div
                v-for="t in heldTickets"
                :key="t.id"
                class="flex items-center gap-2 px-2 py-1.5 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 group transition text-[11px]"
                :class="t.createdAt && Date.now() - new Date(t.createdAt).getTime() > 2 * 60 * 60 * 1000 ? 'bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800/30' : ''"
              >
                <button
                  class="flex-1 flex items-center gap-2 text-left min-w-0"
                  @click="recallTicket(t.id)"
                >
                  <i class="fa-solid fa-rotate-left text-amber-500 shrink-0 text-[10px]"></i>
                  <span class="text-slate-600 dark:text-slate-400 font-medium truncate">{{ t.itemCount }} items</span>
                  <span class="text-[9px] text-slate-400 ml-1 hidden sm:inline">{{ formatHeldTime(t.createdAt) }}</span>
                  <span class="text-slate-800 dark:text-slate-200 font-bold font-mono-data ml-auto">{{ fc(t.total) }}</span>
                </button>
                <button
                  class="shrink-0 w-5 h-5 rounded flex items-center justify-center text-slate-300 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 opacity-0 group-hover:opacity-100 transition"
                  title="Descartar (quedará registrado en auditoría)"
                  @click.stop="deleteHeldTicket(t.id)"
                >
                  <i class="fa-solid fa-xmark text-[10px]"></i>
                </button>
              </div>
            </div>
          </div>
          <div v-else-if="showRecallDropdown && !heldTickets.length" class="border-t border-slate-100 dark:border-slate-700 pt-2 mt-1">
            <p class="text-[10px] text-slate-400 text-center py-2">No hay tickets apartados</p>
          </div>
        </BaseCard>
      </div>

      <!-- COLUMN 3: Stats & history (3 cols) -->
      <div v-show="showStatsPanel" class="xl:col-span-3 space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <KpiCard label="Ventas Hoy" :value="stats.ventas_hoy" prefix="$" icon="fa-sack-dollar" icon-color="success" :sublabel="`${stats.tickets_hoy} tickets`" />
          <KpiCard label="Ticket Prom." :value="stats.ticket_promedio" prefix="$" icon="fa-receipt" icon-color="brand" />
          <KpiCard label="Efectivo" :value="stats.efectivo" prefix="$" icon="fa-money-bill-wave" icon-color="info" />
          <KpiCard label="Caja" :value="stats.saldo_caja" prefix="$" icon="fa-vault" icon-color="success" />
        </div>

        <BaseCard padding="none">
          <div class="p-4 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
            <h3 class="text-sm font-bold text-slate-900 dark:text-white">Últimas Transacciones</h3>
            <BaseBadge variant="default" size="xs">Hoy</BaseBadge>
          </div>
          <div class="max-h-[300px] overflow-y-auto divide-y divide-slate-50 dark:divide-slate-800/70">
            <TransitionGroup
              enter-active-class="transition duration-250 ease-out-expo"
              enter-from-class="opacity-0 -translate-x-2"
              enter-to-class="opacity-100 translate-x-0"
              leave-active-class="transition duration-150 ease-in"
              leave-from-class="opacity-100 translate-x-0"
              leave-to-class="opacity-0 translate-x-2"
            >
              <div
                v-for="t in recentTransactions"
                :key="t.id"
                class="p-3 flex items-center gap-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                <div
                  class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
                  :class="t.medio_pago === 'efectivo' ? 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400' : 'bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400'"
                >
                  <i :class="t.medio_pago === 'efectivo' ? 'fa-solid fa-money-bill-wave' : 'fa-solid fa-credit-card'" class="text-xs"></i>
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-xs font-bold text-slate-800 dark:text-slate-100 truncate">{{ t.cliente || 'Consumidor Final' }}</p>
                  <p class="text-[10px] text-slate-400 dark:text-slate-500">{{ t.hora }} · {{ t.itemCount || t.items?.length || 0 }} productos</p>
                </div>
                <span class="text-xs font-bold font-mono-data text-slate-800 dark:text-slate-200">{{ fc(t.total) }}</span>
                <div class="flex items-center gap-1">
                  <button
                    class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition"
                    title="Ver detalle"
                    @click="viewSaleInfo(t)"
                  >
                    <i class="fa-solid fa-eye text-[10px]"></i>
                  </button>
                  <button
                    class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition"
                    title="Reabrir ticket"
                    @click="reopenTicket(t)"
                  >
                    <i class="fa-solid fa-receipt text-[10px]"></i>
                  </button>
                  <button
                    v-if="Date.now() - t.createdAt < 60000"
                    class="w-6 h-6 rounded flex items-center justify-center text-slate-400 hover:text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-900/20 transition"
                    title="Editar venta"
                    @click="editSale(t)"
                  >
                    <i class="fa-solid fa-pen text-[10px]"></i>
                  </button>
                </div>
              </div>
            </TransitionGroup>
            <p v-if="!recentTransactions.length" class="text-xs text-slate-400 dark:text-slate-500 text-center py-6">Sin transacciones hoy</p>
          </div>
        </BaseCard>

        <BaseCard v-if="lookupBadges.length" padding="md">
          <p class="text-[10px] font-bold text-slate-500 dark:text-slate-400 uppercase mb-2">Escaneos Recientes</p>
          <div class="flex flex-wrap gap-1.5">
            <span
              v-for="(b, bi) in lookupBadges"
              :key="bi"
              class="px-2 py-1 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-[10px] font-mono-data font-bold text-slate-600 dark:text-slate-300"
            >{{ b }}</span>
          </div>
        </BaseCard>
      </div>
    </div>
  </div>
  <!-- Missing product dialog -->
  <BaseModal v-model="showMissingDialog" title="Producto no encontrado" size="sm" :close-on-esc="true" @close="showMissingDialog = false">
    <div class="text-center">
      <div class="w-12 h-12 rounded-2xl bg-amber-50 dark:bg-amber-900/20 flex items-center justify-center mx-auto mb-3">
        <i class="fa-solid fa-circle-question text-amber-500 text-xl"></i>
      </div>
      <p class="text-sm font-semibold text-slate-800 dark:text-slate-200 mb-1">Producto no registrado</p>
      <p class="text-xs text-slate-500 dark:text-slate-400 mb-4">¿Desea crearlo?</p>
      <div class="flex items-center gap-3">
        <BaseButton variant="secondary" class="flex-1" @click="showMissingDialog = false">
          <i class="fa-solid fa-xmark mr-1"></i> No <span class="text-[10px] text-slate-400 ml-1">(Esc)</span>
        </BaseButton>
        <BaseButton variant="primary" class="flex-1" @click="confirmCreateFromSearch">
          <i class="fa-solid fa-check mr-1"></i> Sí <span class="text-[10px] text-brand-300 ml-1">(Enter)</span>
        </BaseButton>
      </div>
    </div>
  </BaseModal>

  <!-- Quick-create product modal -->
  <QuickCreateModal
    :show="showCreateModal"
    :barcode="createBarcode"
    :categories="categories"
    :next-gen-code="nextGenCode"
    @close="showCreateModal = false"
    @created="onProductCreated"
  />

  <TicketModal :show="showTicket" :ticket="ticketData" @close="showTicket = false; nextTick(() => barcodeInput.value?.focus())" />

  <BaseModal v-model="showSaleInfoModal" title="Detalle de venta" size="sm">
    <div v-if="saleInfoTarget" class="space-y-3">
      <div class="flex justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>Ticket #{{ saleInfoTarget.ventaNumero || saleInfoTarget.id }}</span>
        <span>{{ saleInfoTarget.hora }}</span>
      </div>
      <div class="space-y-1">
        <div v-for="(item, i) in saleInfoTarget.items" :key="i" class="flex justify-between text-xs text-slate-700 dark:text-slate-300">
          <span class="flex-1 truncate">{{ item.nombre }}</span>
          <span class="w-16 text-right">{{ item.cantidad }} x {{ fc(item.precio_unitario) }}</span>
          <span class="w-20 text-right font-bold">{{ fc(item.cantidad * item.precio_unitario) }}</span>
        </div>
      </div>
      <div class="border-t border-slate-200 dark:border-slate-700 pt-2 space-y-1 text-xs">
        <div v-if="saleInfoTarget.descuento" class="flex justify-between text-slate-500">
          <span>Descuento</span>
          <span>- {{ fc(saleInfoTarget.descuento) }}</span>
        </div>
        <div class="flex justify-between font-bold text-slate-900 dark:text-white">
          <span>TOTAL</span>
          <span>{{ fc(saleInfoTarget.total) }}</span>
        </div>
        <div class="flex justify-between text-slate-500">
          <span>Medio de pago</span>
          <span class="capitalize">{{ saleInfoTarget.medio_pago }}</span>
        </div>
        <div class="flex justify-between text-slate-500">
          <span>Cliente</span>
          <span>{{ saleInfoTarget.cliente || 'Consumidor Final' }}</span>
        </div>
      </div>
    </div>
  </BaseModal>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import { formatCurrency as fc } from '@/composables/useUtils'
import api from '@/services/api'
import { useCajaStore } from '@/stores/caja'
import TicketModal from '@/components/layout/TicketModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import KpiCard from '@/components/ui/KpiCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import QuickCreateModal from '@/components/pos/QuickCreateModal.vue'
import { useSounds } from '@/composables/useSounds'
import { useConfetti } from '@/composables/useConfetti'
import { useHeldTickets } from '@/composables/useHeldTickets'

const auth = useAuthStore()
const toast = useToastStore()
const cajaStore = useCajaStore()
const route = useRoute()
const router = useRouter()
const { playSale } = useSounds()
const { firstSaleOfDay } = useConfetti()

const posLookupCode = ref('')
const posTextSearch = ref('')
const selectedPOSCategory = ref(null)
const confirmando = ref(false)
const showTicket = ref(false)
const showStatsPanel = ref(true)
const showRecallDropdown = ref(false)
const ticketData = reactive({ items: [], numero: '', fecha: '', total: 0, descuento: 0, medio_pago: '', cliente: '', sucursal: '' })

const {
  heldTickets, heldCount, suspiciousTickets,
  holdTicket: _holdTicket, recallTicket: _recallTicket, deleteHeldTicket: _deleteHeldTicket,
} = useHeldTickets()

const hasSuspicious = computed(() => suspiciousTickets.value.length > 0)
const showSusWarning = ref(true)

const textSearchRef = ref(null)
const barcodeInput = ref(null)

// Missing product dialog states
const showMissingDialog = ref(false)
const showCreateModal = ref(false)
const createBarcode = ref('')

const nextGenCode = computed(() => {
  const codes = products.value
    .filter(p => p.codigo_barras?.startsWith('GEN-'))
    .map(p => parseInt(p.codigo_barras.replace('GEN-', ''), 10))
    .filter(n => !isNaN(n))
  const maxSeq = codes.length ? Math.max(...codes) : 0
  return `GEN-${String(maxSeq + 1).padStart(8, '0')}`
})

function handleTextSearchEnter() {
  const q = posTextSearch.value.trim()
  if (!q || filteredPOSProducts.value.length > 0) return
  // Check if query looks like a barcode (mostly digits)
  createBarcode.value = /^\d{8,}$/.test(q) ? q : ''
  showMissingDialog.value = true
}

function confirmCreateFromSearch() {
  showMissingDialog.value = false
  showCreateModal.value = true
}

function onProductCreated(product) {
  // Add to local products list so it appears immediately
  products.value.push(product)
  // Clear search and select the new product
  posTextSearch.value = ''
  selectedPOSCategory.value = product.categoria_id || null
  toast.success(`${product.nombre} creado. Podés agregarlo al carrito desde la grilla.`)
  showCreateModal.value = false
}

function holdTicket() {
  const t = _holdTicket(cart)
  if (!t) { toast.warning('El carrito está vacío'); return }
  vaciarCarrito()
  toast.info(`Ticket #${t.id.toString().slice(-6)} apartado (${t.itemCount} items, ${fc(t.total)})`)
  showRecallDropdown.value = false
}

function recallTicket(id) {
  if (cart.items.length) {
    toast.warning('El carrito actual no está vacío. Vacialo o confirmalo primero.')
    return
  }
  const ticket = _recallTicket(id)
  if (!ticket) return
  cart.items = ticket.items.map(i => ({ ...i }))
  cart.subtotal = ticket.subtotal
  cart.total = ticket.total
  cart.descuento = ticket.descuento || 0
  cart.cliente_id = ticket.cliente_id || ''
  cart.medio_pago = ticket.medio_pago || 'efectivo'
  showRecallDropdown.value = false
  toast.info(`Ticket recuperado — ${ticket.itemCount} items`)
}

function deleteHeldTicket(id) {
  _deleteHeldTicket(id)
  if (!heldTickets.value.length) showRecallDropdown.value = false
}

function formatHeldTime(iso) {
  if (!iso) return ''
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diff / 60000)
    if (mins < 1) return 'ahora'
    if (mins < 60) return `hace ${mins}min`
    const hrs = Math.floor(mins / 60)
    return `hace ${hrs}h${mins % 60 > 0 ? mins % 60 + 'm' : ''}`
  } catch { return iso }
}

const lookupProduct = reactive({
  id: null,
  codigo_barras: '',
  nombre: '',
  marca: '',
  precio_venta: 0,
  precio_costo: 0,
  categoria_id: null,
  stock_actual: 0,
  _loading: false,
  _searched: false,
  _searchingExternal: false,
  _manualEntry: false,
  _manualNombre: '',
  _manualPrecio: 0,
  _manualQty: 1,
  _barcode: '',
  _qty: 1,
  _price: 0
})

const lookupBadges = ref([])

const pendingLookups = ref([])

const mediosPago = [
  { value: 'efectivo', label: 'Efectivo', icon: 'fa-money-bill-wave' },
  { value: 'debito', label: 'Débito', icon: 'fa-credit-card' },
  { value: 'credito', label: 'Crédito', icon: 'fa-credit-card' },
  { value: 'transferencia', label: 'Transf.', icon: 'fa-mobile-screen-button' },
  { value: 'cta_corriente', label: 'Cta. Cte.', icon: 'fa-file-invoice-dollar' }
]

const cart = reactive({
  items: [],
  subtotal: 0,
  total: 0,
  descuento: 0,
  medio_pago: 'efectivo',
  cliente_id: ''
})

const stats = reactive({
  ventas_hoy: 84500,
  tickets_hoy: 12,
  ticket_promedio: 7041,
  efectivo: 52000,
  saldo_caja: 72000
})

const products = ref([])

const categories = ref([])

const clientes = ref([])

const ofertas = ref([])

const recentTransactions = ref([])
const editingVentaId = ref(null)
const showSaleInfoModal = ref(false)
const saleInfoTarget = ref(null)

const bankConfig = reactive({ banco_nombre: '', banco_titular: '', banco_alias: '' })

const filteredPOSProducts = computed(() => {
  let list = products.value
  if (selectedPOSCategory.value) {
    list = list.filter(p => p.categoria_id === selectedPOSCategory.value)
  }
  if (posTextSearch.value.trim()) {
    const q = posTextSearch.value.toLowerCase()
    list = list.filter(p =>
      p.nombre.toLowerCase().includes(q) ||
      p.marca.toLowerCase().includes(q) ||
      p.codigo_barras.includes(q)
    )
  }
  return list
})

onMounted(async () => {
  localStorage.setItem('apex_user', JSON.stringify({ nombre: auth.currentUser?.nombre || auth.currentUser?.username || '' }))
  try {
    const [prods, cats, clis, ofs, cfg] = await Promise.all([
      api.get('/api/productos').catch(() => null),
      api.get('/api/categorias').catch(() => null),
      api.get('/api/clientes').catch(() => null),
      api.get('/api/ofertas?page_size=200').catch(() => null),
      api.get('/api/config/ajustes').catch(() => null)
    ])
    const prodItems = prods?.data || prods || []
    if (Array.isArray(prodItems)) products.value = prodItems
    const catItems = cats?.data || cats || []
    if (Array.isArray(catItems)) categories.value = catItems
    const cliItems = clis?.data || clis || []
    if (Array.isArray(cliItems)) clientes.value = cliItems
    const ofsItems = ofs?.data || ofs || []
    if (Array.isArray(ofsItems)) ofertas.value = ofsItems
    if (cfg) {
      for (const item of cfg) {
        if (item.clave === 'banco_nombre') bankConfig.banco_nombre = item.valor || ''
        if (item.clave === 'banco_titular') bankConfig.banco_titular = item.valor || ''
        if (item.clave === 'banco_alias') bankConfig.banco_alias = item.valor || ''
      }
    }
  } catch { /* sin datos */ }

  fetchPOSStats()
  fetchRecentTransactions()
  cajaStore.fetchEstado()
  // Auto-sync catálogo si pasó >1h desde última descarga
  const lastSync = localStorage.getItem('catalogo_last_sync')
  const hour = 60 * 60 * 1000
  if (!lastSync || Date.now() - Number(lastSync) > hour) {
    api.post('/api/catalogo/descargar').then(() => {
      localStorage.setItem('catalogo_last_sync', String(Date.now()))
    }).catch(() => {})
  }
  await nextTick()
  barcodeInput.value?.focus()
  if (route.query.editVentaId) {
    loadSaleForEditing(Number(route.query.editVentaId))
    router.replace({ query: {} })
  }
})

async function fetchPOSStats() {
  try {
    const [dash, cajaRes, cajaEst] = await Promise.all([
      api.get('/api/dashboard/resumen').catch(() => null),
      api.get('/api/caja/resumen').catch(() => null),
      api.get('/api/caja/estado').catch(() => null)
    ])
    if (dash) {
      stats.ventas_hoy = dash.ventas_hoy || 0
      stats.tickets_hoy = dash.cant_ventas_hoy || 0
      stats.ticket_promedio = dash.ticket_promedio || 0
    }
    if (cajaRes && cajaRes.desglose) {
      stats.efectivo = cajaRes.desglose.efectivo || 0
    }
    if (cajaEst) {
      stats.saldo_caja = cajaEst.saldo_actual || 0
    }
  } catch { /* fallback to mock */ }
}

async function fetchRecentTransactions() {
  try {
    const ventas = await api.get('/api/ventas?page_size=5&estado=completada').catch(() => null)
    const items = ventas?.data || ventas || []
    if (Array.isArray(items)) {
      recentTransactions.value = items.map(v => ({
        id: v.id,
        ventaNumero: v.numero,
        cliente: v.cliente_nombre || null,
        total: v.total,
        subtotal: v.subtotal,
        descuento: v.descuento || 0,
        medio_pago: v.medio_pago,
        items: (v.items || []).map(i => ({
          producto_id: i.producto_id,
          nombre: i.producto_nombre,
          cantidad: i.cantidad,
          precio_unitario: i.precio_unitario
        })),
        itemCount: v.items ? v.items.length : 0,
        hora: v.fecha ? new Date(v.fecha).toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }) : '',
        createdAt: v.created_at ? new Date(v.created_at).getTime() : Date.now()
      }))
    }
  } catch { /* sin datos */ }
}

function selectProductForLookup(product) {
  Object.assign(lookupProduct, {
    id: product.id,
    codigo_barras: product.codigo_barras,
    nombre: product.nombre,
    marca: product.marca,
    precio_venta: product.precio_venta,
    precio_costo: product.precio_costo,
    categoria_id: product.categoria_id,
    stock_actual: product.stock_actual,
    _loading: false,
    _searched: true,
    _qty: 1,
    _price: product.precio_venta
  })
}

async function triggerPOSLookup() {
  const raw = posLookupCode.value.trim()
  if (!raw) return

  if (raw.startsWith('*')) {
    posLookupCode.value = ''
    const parts = raw.split('*')
    const nombre = (parts[1] || '').trim()
    const precio = parseFloat(parts[2] || '0')
    if (!nombre || precio <= 0) {
      toast.warning('Formato: *Nombre*Precio. Ej: *COCA 1.5L*1500')
      return
    }
    const seq = products.value.filter(p => p.codigo_barras && (p.codigo_barras.startsWith('GEN-') || p.codigo_barras.startsWith('*MANUAL*'))).length + 1
    const cleanCode = `GEN-${String(seq).padStart(8, '0')}`
    const tempProd = {
      id: Date.now() + Math.random(),
      codigo_barras: cleanCode,
      nombre, marca: '', precio_venta: precio, precio_costo: 0,
      stock_actual: 0, categoria_id: categories.value[0]?.id || 1,
      _pending: true, _nombre: nombre, _precio: precio
    }
    products.value.push(tempProd)
    addToCart(tempProd, 1, precio)
    toast.info(`${nombre} → ${cleanCode}. Se creará al confirmar la venta.`)
    nextTick(() => barcodeInput.value?.focus())
    return
  }

  // 1. Buscar en base local primero
  const local = products.value.find(p => p.codigo_barras === raw)
  if (local) {
    addToCart(local)
    posLookupCode.value = ''
    if (!lookupBadges.value.some(b => b.includes(raw))) {
      lookupBadges.value.unshift(raw)
      if (lookupBadges.value.length > 10) lookupBadges.value.pop()
    }
    nextTick(() => barcodeInput.value?.focus())
    return
  }

  // 2. No está en local, buscar en API - mostrar panel con animación
  posLookupCode.value = ''
  const lookupId = Date.now()
  lookupProduct._searchingExternal = true
  lookupProduct._barcode = raw
  lookupProduct._manualEntry = false
  lookupProduct.id = null
  lookupProduct._searched = false

  try {
    const resp = await api.post('/api/productos/lookup', { barcode: raw }).catch(() => null)
    if (resp && resp.nombre) {
      // Encontrado en fuentes externas - mostrar en panel
      lookupProduct._searchingExternal = false
      lookupProduct.id = lookupId
      lookupProduct.codigo_barras = raw
      lookupProduct.nombre = resp.nombre
      lookupProduct.marca = resp.marca || ''
      lookupProduct.precio_venta = resp.precio_referencia || resp.precio_venta || 0
      lookupProduct.precio_costo = resp.precio_costo || 0
      lookupProduct.stock_actual = resp.stock_actual || 0
      lookupProduct.categoria_id = resp.categoria_id
      lookupProduct._qty = 1
      lookupProduct._price = lookupProduct.precio_venta
      lookupProduct._searched = true
      if (resp.comparacion) {
        lookupBadges.value = resp.comparacion.map(c => `${c.fuente}: ${fc(c.precio)}`)
      }
      // Guardar en pendientes por si el usuario sigue escaneando
      pendingLookups.value.push({
        id: lookupId,
        barcode: raw,
        nombre: resp.nombre,
        marca: resp.marca || '',
        precio: lookupProduct.precio_venta,
        fuente: resp.fuente,
        type: 'found'
      })
      if (pendingLookups.value.length > 10) pendingLookups.value.shift()
    } else {
      // No encontrado - mostrar manual entry en panel
      lookupProduct._searchingExternal = false
      lookupProduct._manualEntry = true
      lookupProduct._manualNombre = ''
      lookupProduct._manualPrecio = 0
      lookupProduct._manualQty = 1
      lookupProduct._barcode = raw
      // Guardar en pendientes
      pendingLookups.value.push({
        id: lookupId,
        barcode: raw,
        nombre: '',
        marca: '',
        precio: 0,
        fuente: null,
        type: 'manual'
      })
      if (pendingLookups.value.length > 10) pendingLookups.value.shift()
    }
  } catch {
    lookupProduct._searchingExternal = false
    lookupProduct._manualEntry = true
    lookupProduct._manualNombre = ''
    lookupProduct._manualPrecio = 0
    lookupProduct._manualQty = 1
    lookupProduct._barcode = raw
  }

  nextTick(() => barcodeInput.value?.focus())
}

function addPendingLookupToCart(lookupId) {
  const lookup = pendingLookups.value.find(l => l.id === lookupId)
  if (!lookup) return
  if (!lookup.nombre) {
    showManualEntryForPending(lookupId)
    return
  }
  const tempProd = {
    id: Date.now() + Math.random(),
    codigo_barras: lookup.barcode,
    nombre: lookup.nombre,
    marca: lookup.marca,
    precio_venta: lookup.precio,
    precio_costo: 0,
    stock_actual: 0,
    categoria_id: categories.value[0]?.id || 1,
    _pending: true
  }
  products.value.push(tempProd)
  addToCart(tempProd, 1, lookup.precio)
  pendingLookups.value = pendingLookups.value.filter(l => l.id !== lookupId)
  toast.info(`${lookup.nombre} agregado al carrito.`)
  // Si hay pendientes, mostrar siguiente en panel
  showNextPendingInPanel()
}

function showManualEntryForPending(lookupId) {
  const lookup = pendingLookups.value.find(l => l.id === lookupId)
  if (!lookup) return
  pendingLookups.value = pendingLookups.value.filter(l => l.id !== lookupId)
  lookupProduct._manualEntry = true
  lookupProduct._searchingExternal = false
  lookupProduct._barcode = lookup.barcode
  lookupProduct._manualNombre = ''
  lookupProduct._manualPrecio = lookup.precio || 0
  lookupProduct._manualQty = 1
  lookupProduct.id = null
  lookupProduct._searched = false
  nextTick(() => barcodeInput.value?.focus())
}

function showNextPendingInPanel() {
  if (pendingLookups.value.length === 0) {
    closeLookupPanel()
    return
  }
  const next = pendingLookups.value.shift()
  if (next.type === 'found') {
    lookupProduct._searchingExternal = false
    lookupProduct._manualEntry = false
    lookupProduct.id = next.id
    lookupProduct.codigo_barras = next.barcode
    lookupProduct.nombre = next.nombre
    lookupProduct.marca = next.marca
    lookupProduct.precio_venta = next.precio
    lookupProduct._qty = 1
    lookupProduct._price = next.precio
    lookupProduct._searched = true
  } else {
    lookupProduct._searchingExternal = false
    lookupProduct._manualEntry = true
    lookupProduct._barcode = next.barcode
    lookupProduct._manualNombre = ''
    lookupProduct._manualPrecio = next.precio || 0
    lookupProduct._manualQty = 1
    lookupProduct.id = null
    lookupProduct._searched = false
  }
}

function addFoundToCart() {
  const tempProd = {
    id: Date.now() + Math.random(),
    codigo_barras: lookupProduct.codigo_barras,
    nombre: lookupProduct.nombre,
    marca: lookupProduct.marca,
    precio_venta: lookupProduct._price || lookupProduct.precio_venta,
    precio_costo: 0,
    stock_actual: 0,
    categoria_id: categories.value[0]?.id || 1,
    _pending: true
  }
  products.value.push(tempProd)
  // Remove from pending
  pendingLookups.value = pendingLookups.value.filter(l => l.id !== lookupProduct.id)
  addToCart(tempProd, lookupProduct._qty, lookupProduct._price || lookupProduct.precio_venta)
  showNextPendingInPanel()
}

function closeLookupPanel() {
  lookupProduct._searchingExternal = false
  lookupProduct._manualEntry = false
  lookupProduct.id = null
  lookupProduct._searched = false
  lookupProduct._barcode = ''
}

function handlePOSInput() {
  const val = posLookupCode.value.trim()
  if (val.length >= 13 && !val.startsWith('*')) {
    triggerPOSLookup()
    return
  }
  if (val.startsWith('*') && val.includes('*', 2)) {
    triggerPOSLookup()
    return
  }
  lookupProduct._searched = false
  lookupProduct.id = null
}

function addManualToCart() {
  const nombre = lookupProduct._manualNombre?.trim()
  const precio = lookupProduct._manualPrecio || 0
  const qty = lookupProduct._manualQty || 1

  if (!nombre) {
    toast.error('Ingresá un nombre para el producto')
    return
  }
  if (precio <= 0) {
    toast.error('Ingresá un precio válido')
    return
  }

  const seq = products.value.filter(p => p.codigo_barras && (p.codigo_barras.startsWith('GEN-') || p.codigo_barras.startsWith('*MANUAL*'))).length + 1
  const cleanCode = `*MANUAL*${String(seq).padStart(6, '0')}`
  const tempProd = {
    id: Date.now() + Math.random(),
    codigo_barras: cleanCode,
    nombre, marca: '', precio_venta: precio, precio_costo: 0,
    stock_actual: 0, categoria_id: categories.value[0]?.id || 1,
    _pending: true, _nombre: nombre, _precio: precio
  }
  products.value.push(tempProd)
  addToCart(tempProd, qty, precio)
  toast.info(`${nombre} agregado. Se guardará como *MANUAL* al confirmar venta.`)
  // Remove from pending and show next
  const barcode = lookupProduct._barcode
  pendingLookups.value = pendingLookups.value.filter(l => l.barcode !== barcode)
  showNextPendingInPanel()
}

function addToCart(product, qty = 1, price = null) {
  const isManual = product._pending || (product.codigo_barras && (product.codigo_barras.startsWith('*MANUAL*') || product.codigo_barras.startsWith('GEN-')))

  const oferta = ofertas.value.find(o => o.producto_id === product.id && o.activo)
  const basePrice = price || product.precio_venta

  const existing = cart.items.find(i => i.producto_id === product.id)

  const newQty = (existing ? existing.cantidad : 0) + qty
  if (!isManual && product.stock_actual !== undefined && newQty > product.stock_actual) {
    toast.error(`Stock insuficiente: ${product.stock_actual} disponibles`)
    return
  }

  if (existing) {
    existing.cantidad += qty
    if (oferta && !isManual) existing.oferta = { ...oferta }
  } else {
    cart.items.push({
      producto_id: product.id,
      nombre: product.nombre,
      codigo_barras: product.codigo_barras,
      precio_unitario: basePrice,
      cantidad: qty,
      oferta: oferta && !isManual ? { ...oferta } : null
    })
  }

  posLookupCode.value = ''
  lookupProduct.id = null
  lookupProduct._searched = false
  recalcCart()
  nextTick(() => barcodeInput.value?.focus())
}

function handlePagoKeydown(event) {
  const pagos = mediosPago.map(m => m.value)
  const key = event.key
  if (key >= '1' && key <= '5') {
    event.preventDefault()
    cart.medio_pago = pagos[parseInt(key) - 1]
  } else if (key === 'ArrowLeft') {
    event.preventDefault()
    const idx = pagos.indexOf(cart.medio_pago)
    cart.medio_pago = pagos[Math.max(0, idx - 1)]
  } else if (key === 'ArrowRight') {
    event.preventDefault()
    const idx = pagos.indexOf(cart.medio_pago)
    cart.medio_pago = pagos[Math.min(pagos.length - 1, idx + 1)]
  } else if (key === 'Enter') {
    event.preventDefault()
    confirmarVenta()
  }
}

function recalcCart() {
  cart.subtotal = cart.items.reduce((sum, i) => {
    const qty = i.cantidad || 0
    const unitPrice = i.precio_unitario || 0
    let lineTotal = unitPrice * qty

    if (i.oferta) {
      const req = i.oferta.requiere_cantidad || 2
      if (qty >= req) {
        if (i.oferta.tipo === 'porcentaje') {
          const desc = lineTotal * (i.oferta.valor / 100)
          lineTotal = Math.max(0, lineTotal - desc)
        } else if (i.oferta.tipo === 'monto_fijo') {
          const mult = Math.floor(qty / req)
          const desc = i.oferta.valor * mult
          lineTotal = Math.max(0, lineTotal - desc)
        } else if (i.oferta.tipo === '2x1') {
          const mult = Math.floor(qty / req)
          lineTotal = unitPrice * (qty - mult)
        }
      }
    }

    i._precio_neto = qty > 0 ? lineTotal / qty : unitPrice

    return sum + lineTotal
  }, 0)
  cart.total = Math.max(0, cart.subtotal - (cart.descuento || 0))
}

function vaciarCarrito() {
  cart.items.splice(0, cart.items.length)
  recalcCart()
  cart.descuento = 0
  cart.cliente_id = ''
}

function updateCartQty(idx, qty) {
  if (qty <= 0) {
    removeFromCart(idx)
    return
  }
  const item = cart.items[idx]
  const prod = products.value.find(p => p.id === item.producto_id)
  const isManual = prod?._pending || (prod?.codigo_barras && (prod.codigo_barras.startsWith('*MANUAL*') || prod.codigo_barras.startsWith('GEN-')))
  if (!isManual && prod && prod.stock_actual !== undefined && qty > prod.stock_actual) {
    toast.error(`Stock insuficiente: ${prod.stock_actual} disponibles`)
    return
  }
  item.cantidad = qty
  recalcCart()
}

function removeFromCart(idx) {
  const item = cart.items[idx]
  if (item && !confirm(`¿Eliminar "${item.nombre || item.producto_nombre || 'producto'}" (${fc(item.precio_venta * item.cantidad)}) del carrito?`)) return
  cart.items.splice(idx, 1)
  recalcCart()
}

async function confirmarVenta() {
  if (!cart.items.length || cart.total <= 0) {
    if (!cart.items.length) toast.warning('El carrito está vacío')
    return
  }
  if (!cajaStore.abierta) {
    toast.error('La caja está cerrada. Andá a Arqueos y Caja para abrirla.')
    return
  }

  confirmando.value = true
  let ventaNumero = ''
  let ventaTotal = cart.total
  let ventaResp = null

  try {
    for (const item of cart.items) {
      const prod = products.value.find(p => p.id === item.producto_id)
      if (prod && prod._pending) {
        try {
          const resp = await api.post('/api/productos', {
            codigo_barras: prod.codigo_barras,
            nombre: prod._nombre || prod.nombre,
            precio_venta: prod._precio || prod.precio_venta,
            precio_costo: 0, fuente: 'manual',
            cantidad_inicial: item.cantidad,
            categoria_id: prod.categoria_id || 1
          })
          if (resp && resp.id) {
            item.producto_id = resp.id
            prod.id = resp.id
            prod.stock_actual = item.cantidad
            prod._pending = false
            toast.info(`${prod.nombre} creado con stock=${item.cantidad}. Tras la venta quedará en 0.`)
          }
        } catch {
          prod._pending = false
          prod.stock_actual = item.cantidad
        }
      }
    }

    ventaResp = await api.post('/api/ventas', { cliente_id: cart.cliente_id || undefined })
    if (ventaResp && ventaResp.id) {
      const ventaId = ventaResp.id
      ventaNumero = ventaResp.numero || `#${ventaId}`

      for (const item of cart.items) {
        await api.post(`/api/ventas/${ventaId}/items`, {
          producto_id: item.producto_id,
          cantidad: item.cantidad,
          precio_unitario: item._precio_neto || item.precio_unitario,
          oferta_tipo: item.oferta?.tipo || null,
          oferta_valor: item.oferta?.valor || null,
          oferta_info: item.oferta ? `${item.oferta.tipo === 'porcentaje' ? item.oferta.valor + '% OFF' : item.oferta.tipo === 'monto_fijo' ? '$' + item.oferta.valor + ' OFF' : '2x1'}` : null
        })
      }

      const confirmResp = await api.put(`/api/ventas/${ventaId}/confirmar`, {
        medio_pago: cart.medio_pago,
        descuento: cart.descuento || 0,
        cliente_id: cart.cliente_id || undefined
      })
      if (confirmResp && confirmResp.total) {
        ventaTotal = confirmResp.total
      }
      toast.success(`Venta ${ventaNumero} confirmada. Total: ${fc(ventaTotal)}`)
      playSale()
      firstSaleOfDay()
      try {
        const fe = await api.get(`/api/facturacion/facturas/${ventaId}`)
        if (fe && fe.cae) ticketData.factura = `CAE: ${fe.cae}`
        else if (fe && fe.estado) ticketData.factura = `FE: ${fe.estado}`
      } catch { /* sin factura */ }
    } else {
      throw new Error('No se pudo crear la venta')
    }
  } catch (e) {
    if (!ventaResp) {
      toast.success('Venta registrada (modo local)')
      for (const item of cart.items) {
        const prod = products.value.find(p => p.id === item.producto_id)
        if (prod && !prod._pending) {
          prod.stock_actual = Math.max(0, prod.stock_actual - item.cantidad)
        }
      }
    } else {
      toast.warning('Venta creada pero no confirmada en backend. Revisá en Ventas.')
    }
  }

  stats.ventas_hoy += ventaTotal
  stats.tickets_hoy += 1
  stats.ticket_promedio = Math.round(stats.ventas_hoy / stats.tickets_hoy)
  if (cart.medio_pago === 'efectivo') {
    stats.efectivo += ventaTotal
  }
  stats.saldo_caja += ventaTotal

  recentTransactions.value.unshift({
    id: ventaResp?.id || Date.now(),
    ventaNumero: ventaNumero || `#${Date.now().toString().slice(-6)}`,
    cliente: clientes.value.find(c => c.id === cart.cliente_id)?.nombre || null,
    total: ventaTotal,
    subtotal: cart.subtotal,
    descuento: cart.descuento || 0,
    medio_pago: cart.medio_pago,
    items: cart.items.map(i => ({ ...i })),
    itemCount: cart.items.length,
    hora: new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }),
    createdAt: Date.now()
  })
  if (recentTransactions.value.length > 20) recentTransactions.value.pop()

  ticketData.numero = ventaNumero || `#${Date.now().toString().slice(-6)}`
  ticketData.fecha = new Date().toLocaleString('es-AR')
  ticketData.items = cart.items.map(i => ({ ...i }))
  ticketData.total = ventaTotal
  ticketData.descuento = cart.descuento
  ticketData.medio_pago = cart.medio_pago
  ticketData.cliente = clientes.value.find(c => c.id === cart.cliente_id)?.nombre || ''
  showTicket.value = true

  vaciarCarrito()
  confirmando.value = false
  nextTick(() => barcodeInput.value?.focus())
}

function viewSaleInfo(t) {
  saleInfoTarget.value = t
  showSaleInfoModal.value = true
}

function reopenTicket(t) {
  ticketData.numero = t.ventaNumero || `#${t.id}`
  ticketData.fecha = t.hora || ''
  ticketData.items = t.items || []
  ticketData.total = t.total
  ticketData.descuento = t.descuento || 0
  ticketData.medio_pago = t.medio_pago
  ticketData.cliente = t.cliente || ''
  showTicket.value = true
}

async function editSale(t) {
  if (Date.now() - t.createdAt > 60000) {
    toast.warning('Ya pasó el minuto para editar')
    return
  }
  editingVentaId.value = t.id
  try {
    await api.put(`/api/ventas/${t.id}/anular?edit=true`, {})
    toast.info('Venta original anulada. Editá el carrito y confirmá.')
  } catch {
    toast.error('No se pudo anular la venta original')
    editingVentaId.value = null
    return
  }
  cart.items = (t.items || []).map(i => ({ ...i }))
  cart.descuento = t.descuento || 0
  cart.medio_pago = t.medio_pago || 'efectivo'
  cart.cliente_id = ''
  recalcCart()
  toast.info(`Productos cargados. Editá y confirmá la venta.`)
  nextTick(() => barcodeInput.value?.focus())
}

async function loadSaleForEditing(ventaId) {
  try {
    const res = await api.get(`/api/ventas/${ventaId}`)
    const v = res?.data || res
    if (!v || !v.items) return
    await api.put(`/api/ventas/${ventaId}/anular?edit=true`, {})
    toast.info('Venta original anulada. Editá el carrito y confirmá.')
    cart.items = (v.items || []).map(i => ({
      producto_id: i.producto_id,
      nombre: i.producto_nombre,
      codigo_barras: '',
      precio_unitario: i.precio_unitario,
      cantidad: i.cantidad
    }))
    cart.descuento = v.descuento || 0
    cart.medio_pago = v.medio_pago || 'efectivo'
    cart.cliente_id = v.cliente_id || ''
    editingVentaId.value = ventaId
    recalcCart()
    toast.success(`Productos cargados. Editá y confirmá la venta.`)
    nextTick(() => barcodeInput.value?.focus())
  } catch {
    toast.error('No se pudo cargar la venta para edición')
  }
}
</script>

<style scoped>
@keyframes spin-slow {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.animate-spin-slow {
  animation: spin-slow 3s linear infinite;
}

.lookup-external-searching {
  background: linear-gradient(90deg, #f97316, #fbbf24, #ea580c, #f97316);
  background-size: 200% 200%;
  animation: gradient-shift 2s ease infinite;
}

@keyframes gradient-shift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}
</style>
