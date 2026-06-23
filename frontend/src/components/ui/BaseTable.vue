<script setup>
import BaseSkeleton from './BaseSkeleton.vue'
import EmptyState from './EmptyState.vue'

const props = defineProps({
  columns: { type: Array, required: true }, // { key, label, align?, width?, sortable? }
  rows: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  skeletonRows: { type: Number, default: 5 },
  emptyTitle: { type: String, default: 'Sin registros' },
  emptyText: { type: String, default: 'No hay datos para mostrar en este momento.' },
  emptyIcon: { type: String, default: 'fa-inbox' },
  striped: { type: Boolean, default: false },
  stickyHeader: { type: Boolean, default: true },
  compact: { type: Boolean, default: false },
  maxHeight: { type: String, default: '' },
  rowClass: { type: Function, default: null }
})

const emit = defineEmits(['sort', 'row-click'])
</script>

<template>
  <div class="w-full">
    <div
      class="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden bg-white dark:bg-slate-900 shadow-sm"
      :class="{ 'overflow-y-auto': maxHeight }"
      :style="maxHeight ? { maxHeight } : {}"
    >
      <table class="w-full text-sm text-left">
        <thead
          class="bg-slate-50/80 dark:bg-slate-800/80 text-xs uppercase text-slate-500 dark:text-slate-400 font-semibold tracking-wide"
          :class="{ 'sticky top-0 z-10 backdrop-blur-sm': stickyHeader }"
        >
          <tr>
            <th
              v-for="col in columns"
              :key="col.key"
              class="px-4 py-3 select-none"
              :class="[
                compact ? 'px-3 py-2' : 'px-4 py-3',
                col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left',
                col.width ? col.width : '',
                col.sortable ? 'cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-700/50 transition-colors' : ''
              ]"
              @click="col.sortable ? emit('sort', col.key) : null"
            >
              <span class="flex items-center gap-1" :class="{ 'justify-end': col.align === 'right', 'justify-center': col.align === 'center' }">
                {{ col.label }}
                <i v-if="col.sortable" class="fa-solid fa-sort text-slate-300 dark:text-slate-600 text-[10px]"></i>
              </span>
            </th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100 dark:divide-slate-800">
          <template v-if="loading">
            <tr v-for="n in skeletonRows" :key="n">
              <td
                v-for="(col, idx) in columns"
                :key="col.key"
                class="px-4"
                :class="compact ? 'py-2.5' : 'py-3.5'"
              >
                <BaseSkeleton class="h-4" :class="idx === 0 ? 'w-3/4' : idx === columns.length - 1 ? 'w-1/2 ml-auto' : 'w-full'" />
              </td>
            </tr>
          </template>
          <template v-else-if="rows.length">
            <tr
              v-for="(row, rIdx) in rows"
              :key="row.id || rIdx"
              class="group transition-colors duration-150"
              :class="[
                striped && rIdx % 2 === 1 ? 'bg-slate-50/50 dark:bg-slate-800/30' : 'bg-white dark:bg-slate-900',
                'hover:bg-slate-50 dark:hover:bg-slate-800/60',
                rowClass ? rowClass(row) : ''
              ]"
              @click="emit('row-click', row)"
            >
              <td
                v-for="col in columns"
                :key="col.key"
                class="px-4 text-slate-700 dark:text-slate-300"
                :class="[
                  compact ? 'py-2.5' : 'py-3.5',
                  col.align === 'right' ? 'text-right' : col.align === 'center' ? 'text-center' : 'text-left'
                ]"
              >
                <slot :name="col.key" :row="row" :value="row[col.key]">
                  {{ row[col.key] }}
                </slot>
              </td>
            </tr>
          </template>
          <template v-else>
            <tr>
              <td :colspan="columns.length" class="py-12">
                <EmptyState
                  :icon="emptyIcon"
                  :title="emptyTitle"
                  :text="emptyText"
                  compact
                />
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
  </div>
</template>
