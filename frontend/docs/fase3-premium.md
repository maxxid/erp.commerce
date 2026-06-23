# Fase 3 — Toques Premium

> **Tipo de documento:** Prompt de ejecución para agente de IA.  
> **Proyecto:** ERP Commerce — Frontend Vue 3 (`frontend/`).  
> **Estado:** Pendiente de implementación.  
> **Objetivo:** Agregar micro-interacciones, feedback sensorial, navegación mejorada y capacidad offline/PWA sin alterar la lógica de negocio ni los endpoints existentes.

---

## 1. Contexto del proyecto

- **Stack:** Vue 3 (Composition API `<script setup>`), Vue Router 4, Pinia, Tailwind CSS, Vite 5.
- **Rutas base:** `/app/` (ver `router/index.js`).
- **Base URL backend:** se sirve desde el mismo origen en producción; en desarrollo el proxy apunta a `http://localhost:8000`.
- **Design system:** hay componentes base en `src/components/ui/` (`BaseButton`, `BaseInput`, `BaseSelect`, `BaseModal`, `BaseCard`, `BaseTable`, `BaseBadge`, `BaseToggle`, `BaseSkeleton`, `EmptyState`, `AnimatedNumber`, `KpiCard`).
- **Stores:** `auth.js`, `caja.js`, `toasts.js`.
- **Layout global:** `TheSidebar.vue`, `TheHeader.vue`, `TheFooter.vue`, `ToastContainer.vue`, `HelpModal.vue`, `TicketModal.vue`, `CommandPalette.vue`.
- **Regla de oro:** ningún endpoint, store, flujo de venta/caja/auth ni lógica de negocio puede cambiar. Solo se añaden capas de UX.

---

## 2. Alcance de la Fase 3

Implementar los siguientes 7 toques premium:

1. Breadcrumbs en todas las vistas internas.
2. Indicador global de "Última sincronización hace X segundos".
3. Sonidos opcionales para venta confirmada, apertura de caja y cierre de caja.
4. Confetti en la primera venta del día.
5. PWA básica + indicador de estado offline/online.
6. Spotlight de búsqueda global extendida (`Ctrl+K`).
7. Atajos visuales de teclado por vista + modal de ayuda contextual.

---

## 3. Reglas generales para el agente ejecutor

1. **No modificar lógica de negocio.** Solo tocar templates, estilos, componentes nuevos y helpers de UX.
2. **No cambiar endpoints.** Si necesitas datos nuevos, derivalos del estado existente o usa `localStorage`.
3. **Dark mode obligatorio.** Todo nuevo componente debe tener variantes `dark:`.
4. **Mantener el bundle razonable.** Confetti y sonidos deben cargarse lazy/dinámicamente.
5. **Usar componentes base.** Priorizar `BaseButton`, `BaseModal`, `BaseBadge`, `BaseCard`.
6. **Toast semántico.** Usar `toast.success()` / `toast.error()` / `toast.info()` del store `toasts.js`.
7. **Accesibilidad.** Atajos de teclado deben poder desactivarse; sonidos deben respetar `prefers-reduced-motion` y la preferencia del usuario.
8. **Build verificado.** Después de cada sub-tarea ejecutar `node node_modules/vite/bin/vite.js build` y corregir errores.
9. **Commits atómicos.** Un commit por feature de la lista anterior.

---

## 4. Especificación por feature

### 4.1 Breadcrumbs en todas las vistas internas

#### Comportamiento
- Se muestra debajo del header y sobre el contenido principal, alineado con el padding del layout (`px-6` o el que use el layout).
- Muestra: `Inicio / Nombre de la vista actual`. Si la vista tiene tabs o sub-secciones, mostrar un tercer nivel opcional.
- `Inicio` siempre apunta a `/dashboard`.
- El ítem actual no es clickeable.

#### Implementación sugerida
1. Crear componente `src/components/layout/TheBreadcrumbs.vue`.
2. Usar `$route.name` para determinar la vista actual.
3. Mapa de nombres legibles (ej: `pos → Punto de venta`, `caja → Caja y arqueos`).
4. Insertar el componente en `App.vue` justo debajo de `TheHeader` o dentro del área de contenido, respetando transiciones de ruta.

```vue
<!-- Ejemplo de uso -->
<TheBreadcrumbs />
```

#### Estilo
- Texto `text-sm text-slate-500 dark:text-slate-400`.
- Separador `fa-solid fa-chevron-right text-[10px] text-slate-300 dark:text-slate-600`.
- Link anterior con hover `text-brand-600 dark:text-brand-400`.

---

### 4.2 Indicador global "Última sincronización hace X segundos"

#### Comportamiento
- Aparece en `TheHeader.vue`, al lado derecho del breadcrumb o junto a los controles de modo/red.
- Se actualiza cada 10 segundos.
- Muestra: `Sincronizado hace 25s` / `Sincronizado hace 2m` / `Sincronizado hace 1h`.
- El timestamp se reinicia cada vez que:
  - Se completa una llamada `api.get` o `api.post` exitosa (excepto polling).
  - El usuario presiona manualmente un botón de sincronizar.

#### Implementación sugerida
1. Crear store `src/stores/sync.js` con:
   - `state.lastSyncAt` (timestamp).
   - `actions.touch()` para actualizar el timestamp.
   - `getters.timeAgoLabel` para formatear.
2. Interceptar respuestas exitosas en `src/services/api.js` (donde ya existe el interceptor) y llamar a `syncStore.touch()`.
3. Crear componente `src/components/layout/SyncIndicator.vue` y montarlo en `TheHeader.vue`.

#### Estilo
- Texto `text-xs text-slate-500 dark:text-slate-400`.
- Icono `fa-solid fa-rotate` que gira brevemente al sincronizar.
- Color verde si la sincronización fue hace menos de 5 min; ámbar si fue hace más de 30 min; rojo si está offline.

---

### 4.3 Sonidos opcionales

#### Eventos con sonido
1. **Venta confirmada** (`POSView.vue` → al cerrar ticket exitosamente).
2. **Apertura de caja** (`CajaView.vue` → al abrir caja exitosamente).
3. **Cierre de caja** (`CajaView.vue` → al cerrar caja exitosamente).

#### Comportamiento
- Los sonidos están **desactivados por defecto**.
- El usuario puede activarlos desde:
  - Un toggle en `TheHeader.vue` (icono `fa-solid fa-volume-high` / `fa-solid fa-volume-xmark`).
  - O desde el modal de ayuda/atajos.
- La preferencia se guarda en `localStorage` bajo la key `apex-sounds-enabled`.
- Debe respetar `prefers-reduced-motion: reduce` (no reproducir si está activo).

#### Implementación sugerida
1. Crear `src/composables/useSounds.js`:
   - Cargar archivos de audio lazy con `new Audio()`.
   - Funciones: `playSale()`, `playOpenCash()`, `playCloseCash()`.
   - Verificar `localStorage` y `prefers-reduced-motion` antes de reproducir.
2. Archivos de audio a colocar en `public/sounds/`:
   - `sale-success.mp3`
   - `cash-open.mp3`
   - `cash-close.mp3`
   - Pueden ser generados o descargados; si no existen, dejar placeholders y loguear un warning.
3. Integrar llamadas en `POSView.vue` y `CajaView.vue` **solo en el `.then`/exito de la acción**, sin tocar la lógica de la acción.

---

### 4.4 Confetti en la primera venta del día

#### Comportamiento
- Al confirmar una venta en `POSView.vue`, si es la **primera venta del día actual**, lanzar confetti.
- "Día actual" se determina por la fecha local del navegador (`YYYY-MM-DD`).
- Se debe registrar en `localStorage` bajo `apex-first-sale-YYYY-MM-DD = true` para no repetir.
- El confetti debe ser corto (1.5s) y no bloquear la UI.

#### Implementación sugerida
1. Instalar `canvas-confetti` como dependencia de desarrollo/producción:
   ```bash
   node node_modules/vite/bin/vite.js build  # ya existe
   # instalar con npm si es posible, o dejar indicado al usuario
   ```
   Si npm está bloqueado por Execution Policy, usar `npm install canvas-confetti --save` documentado como paso manual.
2. Crear helper `src/composables/useConfetti.js` que importe `canvas-confetti` dinámicamente:
   ```js
   const confetti = (await import('canvas-confetti')).default
   ```
3. En `POSView.vue`, después de `toast.success('Venta confirmada')`, llamar a `useConfetti().firstSaleOfDay()`.
4. La función `firstSaleOfDay()` verifica `localStorage.getItem('apex-first-sale-' + today)`; si no existe, lanza confetti y guarda la key.

#### Estilo
- Confetti desde el centro de la pantalla, colores brand (`brand-500`, `emerald-500`, `amber-500`).
- Respetar `prefers-reduced-motion: reduce` (no lanzar).

---

### 4.5 PWA básica + indicador offline/online

#### Comportamiento
- El frontend debe ser instalable como PWA.
- Debe funcionar offline mostrando una pantalla de fallback o cacheando el shell.
- Indicador visual en `TheHeader.vue` cuando el navegador pierde conexión.

#### Implementación sugerida
1. **Manifest:** crear `frontend/public/manifest.json`:
   - `name`: "ERP Commerce"
   - `short_name`: "ERP"
   - `start_url`: "/app/"
   - `display`: "standalone"
   - `theme_color`: "#4f46e5" (ajustar al brand)
   - `icons`: usar iconos placeholder o generar desde un logo existente. Si no hay logo, dejar indicado.
2. **Service Worker:**
   - Opción A: usar el plugin `vite-plugin-pwa` (recomendado).
   - Opción B: service worker manual en `public/sw.js` con estrategia Cache-First para el shell y Network-First para API.
   - **Importante:** el backend (`/api/*`) no debe ser cacheado con datos sensibles. Cachear solo assets estáticos.
3. **Indicador offline:**
   - Crear componente `src/components/layout/OfflineIndicator.vue`.
   - Escuchar eventos `window.online` / `window.offline`.
   - Mostrar barra fina en la parte superior del viewport cuando `navigator.onLine === false`.
   - Texto: "Sin conexión. Algunas funciones pueden no estar disponibles."

#### Estilo
- Barra offline: `bg-red-600 text-white text-xs text-center py-1`.
- Transición suave al aparecer/desaparecer.

---

### 4.6 Spotlight de búsqueda global extendida

#### Comportamiento
- Ya existe `CommandPalette.vue` con `Ctrl+K`.
- Extenderlo para que además de comandos estáticos permita:
  - **Buscar productos:** al escribir, si la query tiene 3+ caracteres, llamar a `/api/productos?search={query}` y mostrar resultados en la misma lista.
  - **Buscar clientes:** llamar a `/api/clientes?search={query}`.
  - **Acciones rápidas:** "Nueva venta", "Abrir caja", "Cerrar caja", "Nuevo producto", "Nuevo cliente", "Generar licencia", "Crear backup".
- Los resultados de búsqueda deben distinguirse visualmente de los comandos (icono diferente o sección).
- Al seleccionar un producto/cliente, navegar a la vista correspondiente con el ítem pre-seleccionado o abrir su modal de edición.

#### Implementación sugerida
1. Extender `commands` en `CommandPalette.vue` con acciones rápidas faltantes.
2. Agregar estado: `searchResults` (productos + clientes), `searchLoading`.
3. Usar `watchDebounced` (de `@vueuse/core` si está disponible, o implementar manualmente) sobre `query` para llamar a la API después de 300ms de inactividad.
4. Combinar `commands` + `searchResults` en una lista renderizada, separada por encabezados.

#### Estilo
- Encabezados de sección: `text-[10px] uppercase tracking-wider text-slate-400 dark:text-slate-500 font-semibold px-3 py-1.5`.
- Items de resultado: icono `fa-box` para productos, `fa-user` para clientes.

---

### 4.7 Atajos visuales de teclado por vista + modal de ayuda

#### Comportamiento
- Mostrar atajos de teclado en:
  - `POSView.vue`
  - `CajaView.vue`
  - `VentasView.vue`
  - `ProductsView.vue`
  - `ClientesView.vue`
  - `ComprasView.vue`
  - `ProveedoresView.vue`
- Cada vista debe registrar sus propios atajos.
- Atajos globales:
  - `Ctrl+K` / `Cmd+K` → Spotlight.
  - `F2` → POS.
  - `?` → Abrir modal de ayuda contextual.
  - `Esc` → Cerrar modales/palette.
- Atajos por vista (ejemplos):
  - **POS:** `+` abrir modal de cantidad, `*` activar input de búsqueda manual, `Enter` confirmar venta, `F` foco en búsqueda de producto.
  - **Caja:** `A` abrir caja, `C` cerrar caja, `M` nuevo movimiento.
  - **Ventas:** `A` anular venta seleccionada, `V` ver detalle.

#### Implementación sugerida
1. Crear composable `src/composables/useKeyboardShortcuts.js`:
   - Registrar atajos por vista con `addEventListener('keydown')`.
   - Evitar conflictos con inputs activos (`document.activeElement.tagName`).
   - Devolver `registerShortcuts(viewName, shortcuts)` y `unregisterShortcuts(viewName)`.
2. Crear componente `src/components/layout/KeyboardShortcutsModal.vue`:
   - Recibe prop `shortcuts` (array de `{ key, description }`).
   - Se abre con la tecla `?` o desde el menú de ayuda.
   - Usar `BaseModal`.
3. Crear componente `src/components/ui/Kbd.vue` para mostrar teclas con estilo consistente.
4. Integrar en cada vista:
   - Registrar atajos en `onMounted`.
   - Desregistrar en `onUnmounted`.
   - Pasar la lista de atajos al modal.

#### Estilo
- Tecla `Kbd`: `px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-mono text-slate-600 dark:text-slate-400`.
- Modal de ayuda: lista limpia con tecla a la izquierda y descripción a la derecha.

---

## 5. Componentes y archivos a crear/modificar

### Crear
- `src/components/layout/TheBreadcrumbs.vue`
- `src/components/layout/SyncIndicator.vue`
- `src/components/layout/OfflineIndicator.vue`
- `src/components/layout/KeyboardShortcutsModal.vue`
- `src/components/ui/Kbd.vue`
- `src/composables/useSounds.js`
- `src/composables/useConfetti.js`
- `src/composables/useKeyboardShortcuts.js`
- `src/stores/sync.js`
- `public/manifest.json`
- `public/sw.js` (o configurar `vite-plugin-pwa`)
- `public/sounds/*.mp3` (placeholders)

### Modificar
- `src/App.vue` → añadir breadcrumbs y offline indicator.
- `src/services/api.js` → tocar timestamp de sync en respuestas exitosas.
- `src/components/layout/TheHeader.vue` → añadir sync indicator, sound toggle, PWA install button.
- `src/components/layout/CommandPalette.vue` → extender con búsqueda dinámica.
- `src/views/POSView.vue` → sonido venta, confetti, atajos.
- `src/views/CajaView.vue` → sonidos apertura/cierre, atajos.
- `src/views/VentasView.vue`, `ProductsView.vue`, `ClientesView.vue`, `ComprasView.vue`, `ProveedoresView.vue` → atajos + modal ayuda.
- `index.html` → registrar manifest, theme-color.
- `vite.config.js` → si se usa `vite-plugin-pwa`.

---

## 6. Plan de implementación recomendado

Ordenar las tareas por dependencia y riesgo:

1. **Breadcrumbs** (bajo riesgo, no dependencias).
2. **Sync indicator + store** (bajo riesgo, mejora percepción de frescura).
3. **Offline indicator + PWA manifest** (medio riesgo, verificar service worker).
4. **Keyboard shortcuts + Kbd + modal de ayuda** (medio riesgo, probar conflictos con inputs).
5. **Sonidos opcionales** (bajo riesgo, activar solo en éxito).
6. **Confetti** (bajo riesgo, depende de sonidos/venta).
7. **Spotlight extendido** (medio-alto riesgo, puede generar muchas llamadas API; implementar debounce y límite de resultados).

Después de cada tarea:
- Ejecutar build.
- Revisar visualmente en modo claro y oscuro.
- Verificar que no se rompan flujos críticos (login, POS, caja, ventas).

---

## 7. Criterios de aceptación

- [ ] Breadcrumbs visibles y funcionales en todas las vistas internas.
- [ ] Indicador de sync actualizado en header y reflejando última llamada API exitosa.
- [ ] Toggle de sonidos en header; sonidos reproducidos solo si el usuario activó y no hay `prefers-reduced-motion`.
- [ ] Confetti aparece solo en la primera venta del día; no se repite hasta el día siguiente.
- [ ] El sitio es instalable como PWA (Chrome muestra el ícono de instalar).
- [ ] Indicador offline aparece al desconectar la red y desaparece al reconectar.
- [ ] Spotlight permite buscar productos y clientes con debounce.
- [ ] Cada vista principal tiene atajos documentados y el modal de ayuda se abre con `?`.
- [ ] Build de producción exitoso (`node node_modules/vite/bin/vite.js build`).
- [ ] Sin errores en consola del navegador en flujo básico.

---

## 8. Notas de testing manual

1. **Breadcrumbs:** navegar entre todas las vistas y verificar que el último ítem no sea clickeable.
2. **Sync:** hacer clic en "Actualizar" en cualquier vista; el indicador debe resetear a "hace 0s".
3. **Sonidos:** activar sonidos, vender en POS, abrir/cerrar caja. Verificar que no suenen si el toggle está apagado.
4. **Confetti:** vender por primera vez en un día nuevo (borrar `localStorage` key `apex-first-sale-YYYY-MM-DD` para forzar).
5. **PWA:** en Chrome DevTools → Application → Manifest, verificar datos. En Network → Offline, recargar y verificar shell cacheado.
6. **Spotlight:** presionar `Ctrl+K`, escribir 3 caracteres de un producto/cliente existente, seleccionar y navegar.
7. **Atajos:** en POS presionar `?`, ver modal; probar `F2` desde cualquier vista para ir a POS.

---

## 9. Dependencias opcionales

- `canvas-confetti` para confetti.
- `vite-plugin-pwa` para PWA/service worker.
- `@vueuse/core` para `watchDebounced` (solo si no se quiere implementar manualmente).

Si el entorno tiene npm bloqueado por Execution Policy, documentar el comando alternativo:
```bash
cd C:\Users\Paula\Documents\erp-commerce\frontend
node node_modules\npm\bin\npm-cli.js install <paquete>
```
o dejar la instalación como paso manual del usuario.

---

## 10. Mensaje de commit sugerido

```
feat(ui): fase 3 premium - breadcrumbs, sync, sonidos, confetti, PWA, spotlight y atajos
```

Si se implementa por partes:
- `feat(ui): breadcrumbs en todas las vistas`
- `feat(ui): indicador de ultima sincronizacion`
- `feat(ui): sonidos opcionales para venta y caja`
- `feat(ui): confetti en primera venta del dia`
- `feat(pwa): manifest, service worker e indicador offline`
- `feat(ui): spotlight extendido con busqueda de productos y clientes`
- `feat(ui): atajos de teclado por vista y modal de ayuda`
