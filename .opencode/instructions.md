# ERP Comercio — Instrucciones Base

## Antes de todo

1. **LEÉ MAESTRO.md** — contiene todas las features, flujos, reglas y atajos del sistema. Cualquier cambio debe preservar lo que ya funciona.
2. **NUNCA** elimines o modifiques comportamiento documentado sin permiso explícito del usuario.

## Stack

- **Frontend:** Vue 3 (Composition API, `<script setup>`) + Vite 5 + Tailwind CSS
- **Backend:** Python FastAPI + SQLAlchemy ORM + SQLite
- **Estado:** Pinia stores (`useAuthStore`, `useCajaStore`)
- **Notificaciones:** `useToastStore` (success, error, warning, info)
- **API:** `import api from '@/services/api'` — get/post/put/delete, wrapper `RespuestaData { data, message }`
- **Componentes base:** `BaseModal`, `BaseInput`, `BaseButton`, `BaseSelect`, `BaseBadge`, `BaseCard`, `BaseTable`, `KpiCard`, `EmptyState`

## Convenciones de código

- **Sin comentarios** en código nuevo a menos que el usuario los pida
- **Sin exportaciones no utilizadas**, imports sin usar, logs de debug
- **Componentes modales:** usar `<BaseModal :model-value="show" @update:model-value="emit('close')">` (NUNCA `v-model` con props)
- **Eventos:** `emit('close')` y `emit('created', data)` como convención
- **V-model en inputs:** `v-model="refName"` en refs, `:model-value` + `@update:model-value` en props
- **Nomenclatura:** camelCase para variables/funciones, PascalCase para componentes, kebab-case en archivos .vue
- **Formateo monetario:** `formatCurrency as fc` de `@/composables/useUtils`
- **Iconos:** FontAwesome vía clases `fa-solid fa-xxx`

## Archivos críticos

| Archivo | Propósito |
|---------|-----------|
| `MAESTRO.md` | Documento maestro funcional — LEER SIEMPRE |
| `frontend/src/views/POSView.vue` | Punto de Venta (lógica más densa del frontend) |
| `frontend/src/views/CajaView.vue` | Arqueo y Caja |
| `frontend/src/views/ProductsView.vue` | Gestión de productos |
| `frontend/src/composables/useHeldTickets.js` | Tickets apartados (localStorage) |
| `app/services/producto_service.py` | Lógica de productos (backend) |
| `app/routers/productos.py` | Endpoints de productos |

## Reglas estrictas

1. **No romper features existentes** — verificar contra MAESTRO.md antes de cambiar
2. **Actualizar MAESTRO.md** después de cambios significativos (nuevas features, flujos, atajos, reglas)
3. **Build sin errores** — siempre ejecutar `npm run build` antes de finalizar
4. **Commit solo cuando el usuario lo pida**
5. **Backend async** — `crear_producto`, `actualizar_producto` son sync (SQLAlchemy), los endpoints son async
6. **Errores HTTP** — el backend levanta `HTTPException` con código y detail; el frontend muestra `toast.error(e?.response?.data?.detail || e.message)`
