<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-slate-500 dark:text-slate-400">Órdenes de compra y stock</p>
      </div>
      <div class="flex items-center gap-2">
        <BaseButton variant="secondary" size="sm" :disabled="syncing" @click="syncData">
          <i :class="syncing ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-arrows-rotate'"></i>
          {{ syncing ? 'Sincronizando...' : 'Sincronizar' }}
        </BaseButton>
        <BaseButton variant="primary" size="sm" @click="abrirModalNuevaCompra">
          <i class="fa-solid fa-plus"></i> Cargar Mercadería
        </BaseButton>
      </div>
    </div>

    <BaseCard padding="none">
      <BaseTable
        :columns="[
          { key: 'numero_orden', label: 'N° Orden' },
          { key: 'proveedor', label: 'Proveedor' },
          { key: 'total', label: 'Total', align: 'right' },
          { key: 'cantidad', label: 'Canti.', align: 'right' },
          { key: 'pendiente', label: 'Pendiente', align: 'right' },
          { key: 'estado', label: 'Estado', align: 'center' },
          { key: 'fecha', label: 'Fecha' },
          { key: 'comentarios', label: '', align: 'center', skeleton: false },
          { key: 'acciones', label: 'Acciones', align: 'center' }
        ]"
        :rows="compras"
        empty-title="Sin órdenes de compra"
        empty-text="No hay órdenes de compra registradas."
        empty-icon="fa-inbox"
      >
        <template #numero_orden="{ row }">
          <span class="text-xs font-bold text-slate-700">{{ row.numero_orden }}</span>
        </template>
        <template #proveedor="{ row }">
          <span class="text-xs text-slate-600">{{ row.proveedor }}</span>
        </template>
        <template #total="{ row }">
          <span class="text-xs font-mono-data font-bold text-brand-600">{{ fc(row.total) }}</span>
        </template>
        <template #cantidad="{ row }">
          <span class="text-xs font-mono-data text-slate-700">{{ row.total_cantidad || 0 }}</span>
        </template>
        <template #pendiente="{ row }">
          <span class="text-xs font-mono-data font-bold" :class="row.total_pendiente > 0 ? 'text-amber-600' : 'text-slate-400'">
            {{ row.total_pendiente || 0 }}
          </span>
        </template>
        <template #estado="{ row }">
          <BaseBadge :variant="estadoBadgeVariant(row.estado)" size="xs">{{ row.estado }}</BaseBadge>
        </template>
        <template #fecha="{ row }">
          <span class="text-xs text-slate-600">{{ row.fecha_hora }}</span>
        </template>
        <template #comentarios="{ row }">
          <button
            v-if="row.notas"
            class="text-brand-500 hover:text-brand-700 transition-colors p-1"
            title="Ver comentarios"
            @click="openVerComentario(row)"
          >
            <i class="fa-solid fa-comment-dots text-sm"></i>
          </button>
        </template>
        <template #acciones="{ row }">
          <div class="flex items-center justify-center gap-1">
            <button
              class="w-7 h-7 rounded-lg text-blue-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950/30 transition-colors flex items-center justify-center"
              title="Ver detalle de la compra"
              @click="openDetailModal(row)"
            >
              <i class="fa-solid fa-eye text-[10px]"></i>
            </button>
            <a
              v-if="row.proveedor_telefono"
              :href="`https://wa.me/${row.proveedor_telefono.replace(/\D/g,'')}`"
              target="_blank"
              rel="noopener"
              class="inline-flex items-center justify-center w-7 h-7 rounded-full bg-emerald-500 hover:bg-emerald-600 text-white transition-colors"
              title="WhatsApp"
            >
              <i class="fa-brands fa-whatsapp text-sm"></i>
            </a>
            <BaseButton
              v-if="row.estado === 'pendiente' || row.estado === 'parcial'"
              variant="primary"
              size="xs"
              :disabled="receiving"
              @click="openReceiveModal(row)"
            >
              <i class="fa-solid fa-boxes-packing"></i> Recibir
            </BaseButton>
            <BaseButton
              v-else-if="row.estado === 'anulada'"
              variant="ghost"
              size="xs"
              disabled
            >
              <i class="fa-solid fa-ban"></i>
            </BaseButton>
            <span v-else class="text-[10px] text-emerald-600 font-medium">Recibida</span>
          </div>
        </template>
      </BaseTable>
    </BaseCard>

    <BaseModal
      v-model="showModalCompra"
      title="Cargar Mercadería"
      size="3xl"
      :closeOnOverlay="false"
      :closeOnEsc="false"
    >
      <!-- Proveedor + Notas -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
        <BaseSelect
          label="Proveedor"
          required
          :error="errorProveedor"
          :model-value="nuevaCompra.proveedor_id"
          :options="proveedores"
          option-value="id"
          option-label="nombre"
          placeholder="Seleccionar proveedor"
          @update:modelValue="onProveedorChange"
        />
        <div class="md:col-span-2">
          <BaseInput
            v-model="nuevaCompra.notas"
            label="Notas"
            placeholder="Notas u observaciones (opcional)"
          />
        </div>
      </div>

      <!-- Barra de búsqueda + escáner -->
      <div class="relative mt-4">
        <div class="flex gap-2">
          <div class="relative flex-1">
            <i class="fa-solid fa-magnifying-glass absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm"></i>
            <input
              ref="busquedaInputRef"
              v-model="busqueda"
              type="text"
              placeholder="Escaneá un código o buscá por nombre..."
              class="w-full pl-9 pr-3 py-2.5 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none transition"
              @input="onBusquedaInput"
              @keydown="onBusquedaKeydown"
              @focus="onBusquedaFocus"
              @blur="onBusquedaBlur"
            >
          </div>
          <BaseButton variant="secondary" @click="openScanner">
            <i class="fa-solid fa-camera"></i>
            <span class="hidden sm:inline ml-1">Escanear</span>
          </BaseButton>
        </div>

        <!-- Dropdown de resultados -->
        <div
          v-if="dropdownAbierto && resultados.length"
          class="absolute z-20 mt-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl overflow-hidden"
        >
          <button
            v-for="(r, i) in resultados"
            :key="r.id"
            type="button"
            class="w-full px-4 py-2.5 text-left flex items-center justify-between gap-3 transition-colors"
            :class="i === indiceResaltado ? 'bg-brand-50 dark:bg-brand-900/30' : 'hover:bg-slate-50 dark:hover:bg-slate-800'"
            @mousedown.prevent="seleccionarResultado(r)"
            @mouseenter="indiceResaltado = i"
          >
            <div class="min-w-0">
              <p class="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{{ r.nombre }}</p>
              <p class="text-[11px] text-slate-400 font-mono-data truncate">
                {{ r.codigo_barras }}<span v-if="r.marca"> · {{ r.marca }}</span>
              </p>
            </div>
            <div class="text-right shrink-0">
              <p class="text-xs font-mono-data font-bold text-slate-700 dark:text-slate-300">{{ fc(r.precio_venta || 0) }}</p>
              <p v-if="r.precio_costo" class="text-[10px] font-mono-data text-slate-400">Costo {{ fc(r.precio_costo) }}</p>
            </div>
          </button>
        </div>

        <!-- Sin resultados -->
        <div
          v-else-if="dropdownAbierto && busqueda.trim().length >= 2 && !resultados.length"
          class="absolute z-20 mt-1 w-full bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl shadow-xl p-4 text-center"
        >
          <p class="text-xs text-slate-400">Sin resultados para "<strong>{{ busqueda }}</strong>"</p>
          <p class="text-[11px] text-slate-400 mt-1">
            Presioná <kbd class="px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 rounded text-[10px] font-mono border border-slate-200 dark:border-slate-700">Enter</kbd>
            para crearlo como producto nuevo
          </p>
        </div>
      </div>

      <!-- Lista de ítems -->
      <div class="mt-4">
        <div class="flex items-center justify-between mb-2">
          <p class="text-[10px] font-bold text-slate-400 uppercase tracking-wide">
            Ítems <span v-if="nuevaCompra.items.length">({{ nuevaCompra.items.length }})</span>
          </p>
          <span v-if="nuevaCompra.items.length" class="text-sm font-mono-data font-bold text-slate-800 dark:text-slate-200">
            Total: {{ fc(totalCompra) }}
          </span>
        </div>

        <div v-if="nuevaCompra.items.length" class="space-y-2 max-h-[340px] overflow-y-auto overscroll-contain pr-1">
          <TransitionGroup
            name="item-row"
            tag="div"
            enter-active-class="transition duration-200 ease-out-expo"
            enter-from-class="opacity-0 -translate-y-1"
            enter-to-class="opacity-100 translate-y-0"
            leave-active-class="transition duration-150 ease-in"
            leave-from-class="opacity-100"
            leave-to-class="opacity-0"
            move-class="transition duration-200 ease-out-expo"
          >
            <div
              v-for="(item, idx) in nuevaCompra.items"
              :key="item._key"
              class="bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden"
            >
              <!-- Fila principal: nombre + stepper + precio + subtotal + delete -->
              <div class="flex items-center gap-2 px-3 py-2">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-slate-800 dark:text-slate-200 truncate">{{ item.producto }}</p>
                  <p class="text-[10px] text-slate-400 font-mono-data truncate">{{ item.codigo_barras || '—' }}</p>
                </div>

                <!-- Stepper cantidad -->
                <div class="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    class="w-7 h-7 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                    @click="cambiarCantidad(idx, -1)"
                  >−</button>
                  <input
                    v-model.number="item.cantidad"
                    type="number"
                    min="1"
                    class="w-14 text-center text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg py-1 outline-none focus:border-brand-500 transition"
                    @keydown.enter.prevent="onCantidadEnter(idx)"
                  >
                  <button
                    type="button"
                    class="w-7 h-7 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 flex items-center justify-center text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 transition-colors"
                    @click="cambiarCantidad(idx, 1)"
                  >+</button>
                </div>

                <!-- Precio -->
                <div class="w-24 shrink-0">
                  <input
                    v-model.number="item.precio"
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                    class="w-full text-right text-sm font-mono-data bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg px-2 py-1.5 outline-none focus:border-brand-500 transition"
                    :data-precio-idx="idx"
                    @keydown.enter.prevent="onPrecioEnter(idx)"
                  >
                </div>

                <!-- Subtotal -->
                <span class="w-20 text-right text-sm font-mono-data font-bold text-slate-700 dark:text-slate-300 shrink-0">
                  {{ fc(item.cantidad * item.precio || 0) }}
                </span>

                <!-- Expandir / colapsar detalle -->
                <button
                  type="button"
                  :aria-label="item._expanded ? 'Colapsar detalle' : 'Expandir detalle'"
                  class="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center justify-center transition shrink-0"
                  @click="toggleExpandir(idx)"
                >
                  <i :class="['fa-solid fa-chevron-down text-[10px] transition-transform', item._expanded ? 'rotate-180' : '']"></i>
                </button>

                <!-- Delete -->
                <button
                  type="button"
                  aria-label="Quitar ítem"
                  class="w-7 h-7 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/20 flex items-center justify-center transition shrink-0"
                  @click="quitarItem(idx)"
                >
                  <i class="fa-solid fa-trash text-[10px]"></i>
                </button>
              </div>

              <!-- Fila 2: detalle expandible (vencimiento, precio venta, datos de producto nuevo) -->
              <div
                v-if="item._expanded || esNuevoProducto(item)"
                class="px-3 pb-2 pt-2 border-t border-slate-200/60 dark:border-slate-700/50"
              >
                <!-- Fila 2: vencimiento + precio venta (todos) + hint última compra (existentes) + campos nuevos -->
                <div class="flex flex-wrap items-center gap-3">
                  <div class="flex items-center gap-1.5">
                    <label class="text-[9px] uppercase font-bold text-slate-400">Venc.</label>
                    <input
                      v-model="item.vencimiento"
                      type="date"
                      class="px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg outline-none focus:border-brand-500 transition"
                    >
                  </div>

                  <div class="flex items-center gap-1.5">
                    <label class="text-[9px] uppercase font-bold" :class="esNuevoProducto(item) ? 'text-amber-500' : 'text-slate-400'">P. Venta</label>
                    <input
                      v-model.number="item.precio_venta"
                      type="number"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      class="w-20 px-2 py-1 text-[11px] font-mono-data bg-white dark:bg-slate-900 border rounded-lg outline-none focus:border-brand-500 transition"
                      :class="esNuevoProducto(item) ? 'border-amber-300 dark:border-amber-700 focus:border-amber-500' : 'border-slate-200 dark:border-slate-700'"
                    >
                  </div>

                  <template v-if="esNuevoProducto(item)">
                    <div class="w-full flex items-center gap-1.5">
                      <label class="text-[9px] uppercase font-bold text-amber-500 shrink-0">Nombre</label>
                      <input
                        v-model="item.producto"
                        type="text"
                        placeholder="Nombre del producto nuevo"
                        class="flex-1 min-w-0 px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-700 rounded-lg outline-none focus:border-amber-500 transition"
                      >
                    </div>
                    <div class="flex items-center gap-1.5">
                      <label class="text-[9px] uppercase font-bold text-amber-500">Marca</label>
                      <input
                        v-model="item.marca"
                        type="text"
                        placeholder="Opcional"
                        class="w-24 px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-700 rounded-lg outline-none focus:border-amber-500 transition"
                      >
                    </div>
                    <div class="flex items-center gap-1.5">
                      <label class="text-[9px] uppercase font-bold text-amber-500">Cat.</label>
                      <select
                        v-model="item.categoria_id"
                        class="px-2 py-1 text-[11px] bg-white dark:bg-slate-900 border border-amber-300 dark:border-amber-700 rounded-lg outline-none focus:border-amber-500 transition"
                      >
                        <option :value="null">General</option>
                        <option v-for="cat in categorias" :key="cat.id" :value="cat.id">{{ cat.nombre }}</option>
                      </select>
                      <BaseBadge variant="warning" size="xs">Nuevo</BaseBadge>
                    </div>
                  </template>
                </div>

                <!-- Hint: última compra (solo productos existentes, bajo demanda) -->
                <div
                  v-if="!esNuevoProducto(item) && item._productoId"
                  class="mt-1.5 text-[10px] text-slate-400"
                >
                  <template v-if="ultimoCompraCache[item._productoId] !== undefined">
                    <template v-if="ultimoCompraCache[item._productoId]">
                      <i class="fa-solid fa-truck-field mr-1"></i>
                      Últ. compra: <span class="font-mono-data font-semibold">{{ fc(ultimoCompraCache[item._productoId].precio_unitario) }}</span>
                      <span v-if="ultimoCompraCache[item._productoId].proveedor"> · {{ ultimoCompraCache[item._productoId].proveedor }}</span>
                    </template>
                    <span v-else class="text-slate-400/60">Sin compras registradas</span>
                  </template>
                  <span v-else><i class="fa-solid fa-circle-notch fa-spin mr-1"></i>Buscando última compra...</span>
                </div>
              </div>
            </div>
          </TransitionGroup>
        </div>

        <!-- Empty state -->
        <div v-else class="p-8 text-center border border-dashed border-slate-200 dark:border-slate-700 rounded-xl">
          <i class="fa-solid fa-box-open text-2xl text-slate-300 dark:text-slate-600 mb-2"></i>
          <p class="text-xs text-slate-400">Escaneá un código o buscá un producto para empezar</p>
        </div>
      </div>

      <!-- Escáner de cámara -->
      <BaseModal v-model="scannerOpen" title="Escáner de código de barras" size="md" :closeOnOverlay="false">
        <div class="space-y-3">
          <video
            ref="videoEl"
            class="w-full rounded-xl bg-black aspect-video"
            autoplay
            playsinline
            muted
          ></video>
          <p v-if="scannerError" class="text-xs text-red-500 flex items-center gap-1.5">
            <i class="fa-solid fa-circle-exclamation"></i>{{ scannerError }}
          </p>
          <p v-else class="text-xs text-slate-400 text-center">Apuntá al código de barras</p>
          <BaseButton variant="secondary" block @click="closeCamera">Cancelar</BaseButton>
        </div>
      </BaseModal>

      <template #footer>
        <div class="flex gap-2">
          <BaseButton variant="secondary" class="flex-1" @click="showModalCompra = false">
            Cancelar
          </BaseButton>
          <BaseButton
            variant="primary"
            class="flex-1"
            :disabled="saving || !nuevaCompra.items.length"
            @click="guardarCompra"
          >
            <i :class="saving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-boxes-packing'"></i>
            {{ saving ? 'Guardando...' : 'Guardar y Recibir' }}
          </BaseButton>
        </div>
      </template>
    </BaseModal>

    <BaseModal v-model="showReceiveModal" :title="'Recibir Mercadería — ' + receiveTarget?.numero_orden" size="2xl">
      <div class="space-y-5">
        <div class="p-3 bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800/40 rounded-xl text-xs text-brand-700 dark:text-brand-300 flex items-start gap-2">
          <i class="fa-solid fa-circle-info mt-0.5"></i>
          <span>Cada producto se ingresa como un <strong>lote</strong>. Si tiene vencimiento, completalo para que se aplique el despacho FEFO (los más viejos primero).</span>
        </div>

        <BaseTable
          :columns="[
            { key: 'producto', label: 'Producto' },
            { key: 'cantidad', label: 'Pedido', align: 'center', width: 'w-20' },
            { key: 'cantidad_recibida', label: 'Recibido', align: 'center', width: 'w-20' },
            { key: 'pendiente', label: 'Pendiente', align: 'center', width: 'w-20' },
            { key: 'recibir', label: 'Recibir ahora', align: 'center', width: 'w-28' },
            { key: 'vencimiento', label: 'Vencimiento', align: 'center', width: 'w-44' }
          ]"
          :rows="receiveTarget?.items || []"
          compact
        >
          <template #producto="{ row }">
            <span class="text-xs text-slate-700 font-medium">{{ row.producto }}</span>
          </template>
          <template #cantidad="{ row }">
            <span class="text-xs font-mono-data text-slate-700">{{ row.cantidad }}</span>
          </template>
          <template #cantidad_recibida="{ row }">
            <span class="text-xs font-mono-data text-slate-700">{{ row.cantidad_recibida || 0 }}</span>
          </template>
          <template #pendiente="{ row }">
            <span class="text-xs font-mono-data font-bold text-slate-700">{{ row.cantidad - (row.cantidad_recibida || 0) }}</span>
          </template>
          <template #recibir="{ row }">
            <BaseInput
              :model-value="receiveCantidades[row.id]"
              type="number"
              placeholder="0"
              size="sm"
              input-class="w-20 text-center font-mono-data"
              @update:modelValue="receiveCantidades[row.id] = Number($event)"
            />
          </template>
          <template #vencimiento="{ row }">
            <BaseInput
              :model-value="receiveVencimientos[row.id] || ''"
              type="date"
              size="sm"
              input-class="text-center"
              @update:modelValue="receiveVencimientos[row.id] = $event"
            />
          </template>
        </BaseTable>

        <div class="flex gap-2 pt-2">
          <BaseButton variant="secondary" class="flex-1" @click="showReceiveModal = false">
            Cancelar
          </BaseButton>
          <BaseButton variant="primary" class="flex-1" :disabled="receiving" @click="confirmarRecepcion">
            <i :class="receiving ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-check'"></i>
            {{ receiving ? 'Confirmando...' : 'Confirmar Recepción' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal Ver/Agregar Comentarios -->
    <BaseModal v-model="showVerComentario" :title="`Comentarios — ${verComentarioTarget?.numero_orden || ''}`" size="md">
      <div class="space-y-4">
        <div v-if="verComentarioTarget?.notas" class="bg-slate-50 dark:bg-slate-800 rounded-lg p-3 text-xs text-slate-700 dark:text-slate-300 whitespace-pre-wrap max-h-48 overflow-y-auto border border-slate-200 dark:border-slate-700">
          {{ verComentarioTarget.notas }}
        </div>
        <p v-else class="text-sm text-slate-400 text-center py-4">Sin comentarios</p>
        <hr class="border-slate-200 dark:border-slate-700" />
        <div class="space-y-2">
          <label class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold block">Agregar comentario</label>
          <textarea
            v-model="comentarioTexto"
            rows="3"
            placeholder="Escribí un comentario..."
            class="w-full px-3 py-2 text-sm bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 outline-none resize-none transition"
          ></textarea>
        </div>
        <div class="flex gap-2">
          <BaseButton variant="secondary" class="flex-1" @click="showVerComentario = false">Cerrar</BaseButton>
          <BaseButton variant="primary" class="flex-1" :disabled="savingComentario || !comentarioTexto.trim()" @click="guardarComentario">
            <i :class="savingComentario ? 'fa-solid fa-circle-notch animate-spin' : 'fa-solid fa-paper-plane'"></i>
            {{ savingComentario ? 'Guardando...' : 'Agregar' }}
          </BaseButton>
        </div>
      </div>
    </BaseModal>

    <!-- Modal Detalle de Compra -->
    <BaseModal v-model="showDetailModal" :title="`Detalle — ${detailCompra?.numero || ''}`" size="3xl">
      <div v-if="loadingDetail" class="flex items-center justify-center py-16">
        <i class="fa-solid fa-circle-notch animate-spin text-2xl text-brand-500"></i>
      </div>
      <div v-else-if="detailCompra" class="space-y-5">
        <!-- Header info -->
        <div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Proveedor</div>
            <div class="text-sm font-medium text-slate-900 dark:text-white truncate">{{ detailCompra.proveedor_nombre || '—' }}</div>
          </div>
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Fecha</div>
            <div class="text-sm font-mono-data text-slate-700 dark:text-slate-300">{{ formatFecha(detailCompra.fecha) }}</div>
          </div>
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Estado</div>
            <BaseBadge :variant="estadoBadgeVariant(detailCompra.estado)" size="sm">{{ detailCompra.estado }}</BaseBadge>
          </div>
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-3 border border-slate-100 dark:border-slate-800">
            <div class="text-[10px] uppercase tracking-wider text-slate-400 font-semibold mb-1">Total</div>
            <div class="text-sm font-mono-data font-bold text-brand-600">{{ fc(detailCompra.total) }}</div>
          </div>
        </div>

        <!-- Items -->
        <div>
          <h4 class="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            Productos ({{ detailCompra.items?.length || 0 }})
          </h4>
          <div class="overflow-x-auto -mx-5 px-5">
            <table class="w-full text-sm">
              <thead>
                <tr class="text-left text-xs border-b border-slate-200 dark:border-slate-700 text-slate-400">
                  <th class="py-2 pr-3 font-medium">Producto</th>
                  <th class="py-2 px-3 font-medium text-center">Ped.</th>
                  <th class="py-2 px-3 font-medium text-center">Rec.</th>
                  <th class="py-2 px-3 font-medium text-right">$ Unit.</th>
                  <th class="py-2 pl-3 font-medium text-right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in detailCompra.items" :key="item.id"
                    class="border-b border-slate-100 dark:border-slate-800 last:border-0">
                  <td class="py-2 pr-3 text-slate-900 dark:text-white">{{ item.producto_nombre }}</td>
                  <td class="py-2 px-3 text-center font-mono-data text-slate-600 dark:text-slate-400">{{ item.cantidad }}</td>
                  <td class="py-2 px-3 text-center font-mono-data font-semibold"
                      :class="(item.cantidad_recibida || 0) >= item.cantidad ? 'text-emerald-600' : 'text-amber-600'">
                    {{ item.cantidad_recibida || 0 }}
                  </td>
                  <td class="py-2 px-3 text-right font-mono-data text-slate-600 dark:text-slate-400">{{ fc(item.precio_unitario) }}</td>
                  <td class="py-2 pl-3 text-right font-mono-data font-semibold text-slate-900 dark:text-white">{{ fc(item.subtotal) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Totales -->
        <div class="flex justify-end">
          <div class="bg-slate-50 dark:bg-slate-800/50 rounded-xl p-4 border border-slate-100 dark:border-slate-800 space-y-1.5 min-w-[220px]">
            <div class="flex justify-between text-sm text-slate-500 dark:text-slate-400">
              <span>Subtotal</span>
              <span class="font-mono-data">{{ fc(detailCompra.subtotal) }}</span>
            </div>
            <div class="flex justify-between text-sm text-slate-500 dark:text-slate-400">
              <span>IVA</span>
              <span class="font-mono-data">{{ fc(detailCompra.iva) }}</span>
            </div>
            <div class="flex justify-between text-sm font-bold text-slate-900 dark:text-white pt-1.5 border-t border-slate-200 dark:border-slate-700">
              <span>Total</span>
              <span class="font-mono-data text-brand-600">{{ fc(detailCompra.total) }}</span>
            </div>
          </div>
        </div>

        <!-- Notas -->
        <div v-if="detailCompra.notas" class="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/40 rounded-xl p-3">
          <div class="text-[10px] uppercase tracking-wider text-amber-600 dark:text-amber-400 font-semibold mb-1">Notas</div>
          <div class="text-xs text-amber-800 dark:text-amber-300 whitespace-pre-wrap">{{ detailCompra.notas }}</div>
        </div>
      </div>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick, watch, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toasts'
import api from '@/services/api'
import { formatCurrency as fc } from '@/composables/useUtils'
import { useBarcodeScanner } from '@/composables/useBarcodeScanner'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseCard from '@/components/ui/BaseCard.vue'
import BaseTable from '@/components/ui/BaseTable.vue'
import BaseBadge from '@/components/ui/BaseBadge.vue'

const auth = useAuthStore()
const toast = useToastStore()
const route = useRoute()
const router = useRouter()

const proveedores = ref([])
const productosCatalogo = ref([])
const categorias = ref([])
let _itemCounter = 0

const compras = ref([])

const showModalCompra = ref(false)
const showReceiveModal = ref(false)
const syncing = ref(false)
const receiving = ref(false)
const saving = ref(false)
const receiveTarget = ref(null)
const receiveCantidades = reactive({})
const receiveVencimientos = reactive({})
const showVerComentario = ref(false)
const verComentarioTarget = ref(null)
const comentarioTexto = ref('')
const savingComentario = ref(false)

const showDetailModal = ref(false)
const detailCompra = ref(null)
const loadingDetail = ref(false)

const nuevaCompra = reactive({
  proveedor_id: null,
  notas: '',
  items: [],
})
const errorProveedor = ref('')

// --- Búsqueda de productos ---
const busqueda = ref('')
const resultados = ref([])
const dropdownAbierto = ref(false)
const indiceResaltado = ref(0)
const busquedaInputRef = ref(null)
let _debounceTimer = null

// --- Escáner de cámara ---
const { scannerOpen, scannerError, videoEl, openScanner, closeCamera } = useBarcodeScanner({
  continuous: false,
  onDetect: async (raw) => {
    const local = productosCatalogo.value.find(p => p.codigo_barras === raw)
    if (local) {
      agregarItemDesdeProducto(local)
      toast.success(`Agregado: ${local.nombre}`)
    } else {
      busqueda.value = raw
      buscarProductos(raw)
      if (!resultados.value.length) {
        crearProductoNuevoDesdeBusqueda()
        toast.warning('Código no encontrado. Completá los datos del producto nuevo.')
      }
    }
    nextTick(() => busquedaInputRef.value?.focus())
  },
})

function _nuevoItem(producto = '', codigo_barras = '', cantidad = 1, precio = 0) {
  _itemCounter++
  return {
    _key: `item-${_itemCounter}-${Date.now()}`,
    _productoId: null,
    _expanded: false,
    producto,
    codigo_barras,
    cantidad,
    precio,
    marca: '',
    precio_venta: 0,
    vencimiento: '',
    categoria_id: null,
  }
}

function esNuevoProducto(item) {
  if (!item) return false
  const nombre = (item.producto || '').trim().toLowerCase()
  const code = (item.codigo_barras || '').trim()
  const existe = productosCatalogo.value.some(p =>
    (code && p.codigo_barras === code) ||
    (nombre && p.nombre && p.nombre.toLowerCase() === nombre)
  )
  return !existe && (!!nombre || !!code)
}

const totalCompra = computed(() =>
  nuevaCompra.items.reduce((sum, i) => sum + ((Number(i.cantidad) || 0) * (Number(i.precio) || 0)), 0)
)

onMounted(async () => {
  await Promise.all([fetchCompras(), fetchProveedores(), fetchProductosCatalogo(), fetchCategorias()])
  const detalleId = route.query.detalle
  if (detalleId) {
    const compra = compras.value.find(c => c.id === Number(detalleId))
    if (compra) openDetailModal(compra)
    router.replace({ query: {} })
  }
})

onUnmounted(() => {
  clearTimeout(_debounceTimer)
  closeCamera()
})

async function fetchCompras() {
  try {
    const data = await api.get('/api/compras')
    if (data && data.length) {
      compras.value = data.map(c => {
        const items = (c.items || []).map(i => ({
          id: i.id,
          producto: i.producto_nombre || '',
          cantidad: i.cantidad || 0,
          cantidad_recibida: i.cantidad_recibida || 0,
          precio: i.precio_unitario || 0,
          subtotal: i.subtotal || 0,
        }))
        const total_cantidad = items.reduce((s, i) => s + i.cantidad, 0)
        const total_pendiente = items.reduce((s, i) => s + Math.max(0, i.cantidad - (i.cantidad_recibida || 0)), 0)
        return {
          id: c.id,
          numero_orden: c.numero,
          proveedor: c.proveedor_nombre || '',
          proveedor_telefono: c.proveedor_telefono || '',
          total: c.total || 0,
          estado: c.estado || '',
          fecha: c.fecha ? new Date(c.fecha).toLocaleDateString('es-AR') : '',
          fecha_hora: c.fecha ? new Date(c.fecha).toLocaleString('es-AR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' }) : '',
          notas: c.notas || '',
          total_cantidad,
          total_pendiente,
          items,
        }
      })
    }
  } catch { /* fallback to mock */ }
}

async function fetchProveedores() {
  try {
    const data = await api.get('/api/proveedores?page_size=200')
    if (data && data.length) proveedores.value = data
  } catch { /* fallback to mock */ }
}

async function fetchProductosCatalogo() {
  try {
    const data = await api.get('/api/productos?page_size=100000')
    if (data && data.length) productosCatalogo.value = data
  } catch { /* fallback to mock */ }
}

async function fetchCategorias() {
  try {
    const data = await api.get('/api/categorias')
    if (data && data.length) categorias.value = data
  } catch { /* fallback to mock */ }
}

async function syncData() {
  syncing.value = true
  try {
    await Promise.all([fetchCompras(), fetchProveedores(), fetchProductosCatalogo(), fetchCategorias()])
    toast.success('Datos sincronizados')
  } catch {
    toast.warning('Error al sincronizar')
  } finally {
    syncing.value = false
  }
}

function estadoCompraClass(estado) {
  const map = {
    'pendiente': 'bg-amber-50 text-amber-700',
    'parcial': 'bg-blue-50 text-blue-700',
    'recibida': 'bg-emerald-50 text-emerald-700',
    'anulada': 'bg-rose-50 text-rose-700',
  }
  return map[estado] || 'bg-slate-50 text-slate-600'
}

function estadoBadgeVariant(estado) {
  const map = {
    'pendiente': 'warning',
    'parcial': 'info',
    'recibida': 'success',
    'anulada': 'danger',
  }
  return map[estado] || 'default'
}

function formatFecha(fechaStr) {
  if (!fechaStr) return '—'
  const d = new Date(fechaStr)
  return d.toLocaleDateString('es-AR', { day: '2-digit', month: '2-digit', year: 'numeric' })
}

async function openDetailModal(compra) {
  loadingDetail.value = true
  detailCompra.value = null
  showDetailModal.value = true
  try {
    const data = await api.get(`/api/compras/${compra.id}`)
    if (data) detailCompra.value = data
  } catch (e) {
    toast.error('Error al cargar el detalle: ' + (e?.message || ''))
    showDetailModal.value = false
  } finally {
    loadingDetail.value = false
  }
}

function abrirModalNuevaCompra() {
  nuevaCompra.proveedor_id = null
  nuevaCompra.notas = ''
  nuevaCompra.items = []
  errorProveedor.value = ''
  busqueda.value = ''
  resultados.value = []
  dropdownAbierto.value = false
  showModalCompra.value = true
  nextTick(() => busquedaInputRef.value?.focus())
}

function onProveedorChange(val) {
  nuevaCompra.proveedor_id = Number(val)
  if (nuevaCompra.proveedor_id) errorProveedor.value = ''
}

// --- Búsqueda de productos ---
function onBusquedaInput() {
  clearTimeout(_debounceTimer)
  if (busqueda.value.trim().length < 2) {
    resultados.value = []
    dropdownAbierto.value = false
    return
  }
  _debounceTimer = setTimeout(() => buscarProductos(busqueda.value), 150)
}

function buscarProductos(q) {
  const query = q.trim().toLowerCase()
  if (!query) { resultados.value = []; dropdownAbierto.value = false; return }
  const scored = []
  for (const p of productosCatalogo.value) {
    const nombre = (p.nombre || '').toLowerCase()
    const barcode = (p.codigo_barras || '').toLowerCase()
    let score = -1
    if (barcode === query) score = 0
    else if (nombre === query) score = 1
    else if (nombre.startsWith(query)) score = 2
    else if (nombre.includes(query) || barcode.includes(query)) score = 3
    if (score >= 0) scored.push({ p, score })
  }
  scored.sort((a, b) => a.score - b.score || a.p.nombre.localeCompare(b.p.nombre))
  resultados.value = scored.slice(0, 8).map(s => s.p)
  indiceResaltado.value = 0
  dropdownAbierto.value = true
}

function onBusquedaFocus() {
  if (busqueda.value.trim().length >= 2) buscarProductos(busqueda.value)
}

function onBusquedaBlur() {
  setTimeout(() => { dropdownAbierto.value = false }, 150)
}

function onBusquedaKeydown(e) {
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    indiceResaltado.value = Math.min(indiceResaltado.value + 1, resultados.value.length - 1)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    indiceResaltado.value = Math.max(indiceResaltado.value - 1, 0)
  } else if (e.key === 'Enter') {
    e.preventDefault()
    if (dropdownAbierto.value && resultados.value.length) {
      seleccionarResultado(resultados.value[indiceResaltado.value])
    } else if (busqueda.value.trim()) {
      crearProductoNuevoDesdeBusqueda()
    }
  } else if (e.key === 'Escape') {
    dropdownAbierto.value = false
  }
}

function seleccionarResultado(prod) {
  agregarItemDesdeProducto(prod)
  busqueda.value = ''
  resultados.value = []
  dropdownAbierto.value = false
  nextTick(() => busquedaInputRef.value?.focus())
}

function crearProductoNuevoDesdeBusqueda() {
  const texto = busqueda.value.trim()
  if (!texto) return
  const esCodigo = /^\d{8,14}$/.test(texto)
  const item = _nuevoItem(esCodigo ? texto : texto, esCodigo ? texto : '')
  item._expanded = true
  nuevaCompra.items.push(item)
  busqueda.value = ''
  resultados.value = []
  dropdownAbierto.value = false
  nextTick(() => busquedaInputRef.value?.focus())
}

// --- Items ---
function agregarItemDesdeProducto(prod) {
  const existente = nuevaCompra.items.find(i => i.codigo_barras && i.codigo_barras === prod.codigo_barras)
  if (existente) {
    existente.cantidad = (Number(existente.cantidad) || 0) + 1
    return
  }
  const item = _nuevoItem(prod.nombre, prod.codigo_barras || '')
  item._productoId = prod.id || null
  item.precio = prod.precio_costo || prod.precio_referencia || 0
  item.precio_venta = prod.precio_venta || 0
  item.marca = prod.marca || ''
  nuevaCompra.items.push(item)
}

function cambiarCantidad(idx, delta) {
  const item = nuevaCompra.items[idx]
  if (!item) return
  item.cantidad = Math.max(1, (Number(item.cantidad) || 0) + delta)
}

// --- Última compra (bajo demanda al expandir fila) ---
const ultimoCompraCache = reactive({})

async function fetchUltimoCompra(item) {
  if (!item._productoId || ultimoCompraCache[item._productoId] !== undefined) return
  ultimoCompraCache[item._productoId] = null
  try {
    const data = await api.get(`/api/productos/${item._productoId}/info-detallada`)
    if (data) {
      const ult = data.historial_compras?.[0] || null
      ultimoCompraCache[item._productoId] = ult
        ? { precio_unitario: ult.precio_unitario, proveedor: ult.proveedor, fecha: ult.fecha }
        : null
    }
  } catch { /* se queda en null */ }
}

function toggleExpandir(idx) {
  const item = nuevaCompra.items[idx]
  if (!item) return
  item._expanded = !item._expanded
  if (item._expanded && item._productoId) fetchUltimoCompra(item)
}

function onCantidadEnter(idx) {
  nextTick(() => {
    const el = document.querySelector(`[data-precio-idx="${idx}"]`)
    el?.focus()
  })
}

function onPrecioEnter() {
  busqueda.value = ''
  resultados.value = []
  dropdownAbierto.value = false
  nextTick(() => busquedaInputRef.value?.focus())
}

function quitarItem(idx) {
  nuevaCompra.items.splice(idx, 1)
}

async function guardarCompra() {
  errorProveedor.value = ''
  if (!nuevaCompra.proveedor_id) {
    errorProveedor.value = 'Seleccioná un proveedor'
    return
  }
  if (!nuevaCompra.items.length) {
    toast.warning('Agregá al menos un ítem')
    return
  }
  const sinPrecio = nuevaCompra.items.filter(i => !i.precio)
  if (sinPrecio.length) {
    toast.warning(`Ítems sin precio: ${sinPrecio.map(i => i.producto).join(', ')}`)
  }
  saving.value = true
  try {
    const payload = {
      proveedor_id: nuevaCompra.proveedor_id,
      notas: nuevaCompra.notas,
      recibir_directo: true,
      items: nuevaCompra.items.map(i => ({
        producto: i.producto,
        codigo_barras: i.codigo_barras || '',
        cantidad: i.cantidad || 1,
        precio: i.precio || 0,
        marca: i.marca || '',
        precio_venta: i.precio_venta || 0,
        categoria_id: i.categoria_id || null,
        vencimiento: i.vencimiento || null,
      })),
    }
    const resp = await api.post('/api/compras', payload)
    if (resp && resp.id) {
      toast.success(resp.message || `Compra ${resp.numero || ''} recibida`)
    } else {
      toast.success('Mercadería cargada y recibida')
    }
    showModalCompra.value = false
    await fetchCompras()
    await fetchProductosCatalogo()
  } catch (e) {
    toast.error(e.message || 'Error al guardar compra')
  } finally {
    saving.value = false
  }
}

function openReceiveModal(compra) {
  receiveTarget.value = compra
  Object.keys(receiveCantidades).forEach(k => delete receiveCantidades[k])
  Object.keys(receiveVencimientos).forEach(k => delete receiveVencimientos[k])
  compra.items.forEach(item => {
    receiveCantidades[item.id] = item.cantidad - (item.cantidad_recibida || 0)
  })
  showReceiveModal.value = true
}

async function confirmarRecepcion() {
  if (!receiveTarget.value) return
  const tieneCantidad = Object.values(receiveCantidades).some(v => v > 0)
  if (!tieneCantidad) {
    toast.warning('Ingresá al menos una cantidad a recibir')
    return
  }
  receiving.value = true
  try {
    const payload = {
      cantidades: { ...receiveCantidades },
      vencimientos: { ...receiveVencimientos },
    }
    await api.put(`/api/compras/${receiveTarget.value.id}/recibir`, payload)

    const totalRecibido = Object.values(payload.cantidades).reduce((sum, v) => sum + (Number(v) || 0), 0)
    const totalPedido = receiveTarget.value.items.reduce((sum, i) => sum + i.cantidad, 0)
    let totalPrevio = 0
    receiveTarget.value.items.forEach(item => {
      const recibidoAhora = Number(receiveCantidades[item.id]) || 0
      const recibidoPrevio = item.cantidad_recibida || 0
      totalPrevio += recibidoPrevio
      item.cantidad_recibida = (recibidoPrevio + recibidoAhora)
    })
    const totalAcumulado = totalPrevio + totalRecibido

    if (totalAcumulado >= totalPedido) {
      receiveTarget.value.estado = 'recibida'
      toast.success(`${receiveTarget.value.numero_orden} recibida completamente`)
    } else {
      receiveTarget.value.estado = 'parcial'
      toast.success(`Recepción parcial de ${receiveTarget.value.numero_orden} registrada`)
    }

    showReceiveModal.value = false
    await fetchCompras()
  } catch {
    toast.error('Error al confirmar recepción')
  } finally {
    receiving.value = false
  }
}

function openVerComentario(row) {
  verComentarioTarget.value = row
  comentarioTexto.value = ''
  showVerComentario.value = true
}

async function guardarComentario() {
  if (!comentarioTexto.value.trim() || !verComentarioTarget.value) return
  savingComentario.value = true
  try {
    const resp = await api.post(`/api/compras/${verComentarioTarget.value.id}/comentario`, { texto: comentarioTexto.value.trim() })
    if (resp && resp.notas) {
      verComentarioTarget.value.notas = resp.notas
      const compra = compras.value.find(c => c.id === verComentarioTarget.value.id)
      if (compra) compra.notas = resp.notas
    }
    comentarioTexto.value = ''
    toast.success('Comentario agregado')
  } catch {
    toast.error('Error al guardar comentario')
  } finally {
    savingComentario.value = false
  }
}
</script>
