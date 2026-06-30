# ERP Comercio — Documento Maestro Funcional

> Documento organizado por pantallas (tabs del sidebar), botones y flujos funcionales.
> Versión actual del sistema con todas las funcionalidades desarrolladas.

---

## Índice

1. [Estructura General](#1-estructura-general)
2. [Login / Activación de Licencia](#2-login--activación-de-licencia)
3. [Dashboard](#3-dashboard)
4. [POS — Punto de Venta](#4-pos--punto-de-venta)
5. [Productos](#5-productos)
6. [Caja](#6-caja)
7. [Ventas](#7-ventas)
8. [Clientes](#8-clientes)
9. [Proveedores](#9-proveedores)
10. [Compras](#10-compras)
11. [Calendario](#11-calendario)
12. [Reportes](#12-reportes)
13. [Usuarios](#13-usuarios)
14. [Licencias](#14-licencias)
15. [Auditoría](#15-auditoría)
16. [Backups](#16-backups)
17. [Elementos Globales](#17-elementos-globales)
18. [Flujos Funcionales Críticos](#18-flujos-funcionales-críticos)
19. [Reglas de Negocio](#19-reglas-de-negocio)
20. [Atajos de Teclado](#20-atajos-de-teclado)

---

## 1. Estructura General

### Layout de la Aplicación

```
┌─────────────────────────────────────────────────┐
│ TheHeader: ruta actual | modo API | sync | red  │
├──────────┬──────────────────────────────────────┤
│          │ TheBreadcrumbs                       │
│ Sidebar  │                                      │
│ (colap-  │ Router View (contenido principal)    │
│ sable)   │  con transición de página            │
│          │                                      │
│          │ TheFooter: modo API, URL base        │
├──────────┴──────────────────────────────────────┤
│ ToastContainer (notificaciones bottom-right)    │
└─────────────────────────────────────────────────┘
```

### Elementos Persistentes

| Elemento | Descripción |
|----------|-------------|
| **TheSidebar** | Navegación principal colapsable. Muestra usuario, badges de stock crítico, caja status, ofertas activas. Toggle dark mode, botón ayuda, logout. |
| **TheHeader** | Barra superior: breadcrumb, botón búsqueda global (Ctrl+K), toggle simulador/real, indicador de red, indicador de sync, toggle sonidos. |
| **TheFooter** | Barra inferior: modo API, URL base, logs mínimos. |
| **ToastContainer** | Notificaciones auto-dismissables con barra de progreso. Tipos: success, error, warning, info. |
| **CommandPalette** | Ctrl+K: búsqueda global de comandos y productos/clientes. 24 comandos + búsqueda dinámica con 300ms debounce. |
| **KeyboardShortcutsModal** | Modal de atajos de teclado (F2, Ctrl+K, ?, Esc). |
| **HelpModal** | Guía rápida: escaneo POS, atajos, flujo de compras, fuentes de búsqueda. |
| **OfflineIndicator** | Indicador de conexión offline/online. |
| **SyncIndicator** | Última sincronización con color según tiempo: verde (<5min), amarillo (<30min), rojo (>=30min). |
| **TicketModal** | Preview de ticket térmico (80/58mm) con datos de tienda, items, totales, medio de pago. |

### Roles del Sistema

| Rol | Acceso |
|-----|--------|
| **admin** | Todo el sistema |
| **encargado** | Dashboard, POS, Productos, Caja, Ventas, Compras, Proveedores, Clientes, Reportes, Backups |
| **cajero** | POS, Caja, Ventas |
| **repositor** | Compras, Proveedores |

---

## 2. Login / Activación de Licencia

**Ruta:** `/login` — **Componente:** `LoginView.vue`

### Pantalla 1: Activación de Licencia
*(visible si no hay licencia o no es válida)*

| Elemento | Tipo | Acción |
|----------|------|--------|
| **Machine ID** | Texto clickeable | `copyMachineId()` — copia al portapapeles, muestra badge "Copiado" 1.5s |
| **Clave de Licencia** | Input text | `v-model="auth.licenseKey"`, Enter → `auth.activateLicense()` |
| **Mensaje error/success** | Alerta | Muestra resultado de activación |
| **Botón Activar Licencia** | Botón primary | `auth.activateLicense()` → POST `/api/licencia/activar` |

### Pantalla 2: Login
*(visible cuando la licencia es válida)*

| Elemento | Tipo | Acción |
|----------|------|--------|
| **Usuario** | Input text | `v-model="auth.loginForm.username"`, Enter → foco a password |
| **Contraseña** | Input password | `v-model="auth.loginForm.password"`, Enter → `doLogin()` |
| **Toggle ver contraseña** | Icono ojo | `showPassword = !showPassword` |
| **Error de login** | Alerta roja | Mensaje de error de autenticación |
| **Botón Conectar** | Botón primary | `doLogin()` → POST `/api/auth/login` → guarda token → navega a `/dashboard` |

### Flujo de Login
1. App carga → `auth.checkLicense()` → GET `/api/licencia/estado` + `/api/licencia/machine-id`
2. Si no hay licencia válida → muestra pantalla de activación
3. Si hay licencia válida → muestra formulario de login
4. Login exitoso → guarda JWT en localStorage → redirige a `/dashboard`

### Auto-Login y Validación de Sesión
- `checkAutoLogin()` es **async** y valida el token contra `GET /api/auth/me`
- Si el token es inválido/expirado → limpia localStorage y no loguea
- Si la caja está cerrada y se ejecuta cierre-total → logout automático y redirige a `/login`
- El usuario se desloggea automáticamente al cerrar la jornada

---

## 3. Dashboard

**Ruta:** `/dashboard` — **Componente:** `DashboardView.vue` — **Roles:** todos

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Dashboard"** | — |
| **Toggle "Vista simple/completa"** | `simple = !simple` — cambia cantidad de KPIs visibles (solo admin/encargado) |
| **Botón "Sincronizar"** | `load()` — recarga todos los datos del dashboard |

### KPIs — Vista Completa (6 cards)

| KPI | Descripción |
|-----|-------------|
| **Ventas Hoy** | Total vendido hoy ($) |
| **Efectivo Hoy** | Total cobrado en efectivo ($) |
| **Transferencia** | Total cobrado por transferencia ($) |
| **Stock Crítico** | Cantidad de productos con stock <= stock_minimo |
| **Ventas Mes** | Total del mes actual (solo en modo simple: 4 cards) |
| **Ticket Promedio** | Promedio por ticket (solo en modo simple: 4 cards) |
| **Stock Total** | Unidades en stock (solo en modo simple) |
| **Tendencia** | Variación vs período anterior (solo en modo simple) |

### Gráficos

| Sección | Tipo | Descripción |
|---------|------|-------------|
| **Ventas — Últimos 7 Días** | Barras | 7 barras con tooltip al hover |
| **Picos por Hora (Hoy)** | Barras | Horas 8-20 con badge "24hs" |

### Listas

| Sección | Descripción |
|---------|-------------|
| **Top Productos del Mes** | Lista numerada rankeada por cantidad vendida |
| **Alertas de Stock** | Dos sub-secciones: críticos + sin stock |

### API
- `GET /api/dashboard/resumen` → KPIs, márgenes, tendencia semanal, ventas diarias, picos por hora, top productos, stock crítico
- Fallback a `mockData` si la API falla

---

## 4. POS — Punto de Venta

**Ruta:** `/pos` — **Componente:** `POSView.vue` — **Roles:** admin, cajero

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "POS — Punto de Venta"** | — |
| **Toggle panel de estadísticas** | `showStatsPanel = !showStatsPanel` — icono chevron-left/right |
| **Badge usuario actual** | Muestra nombre del operador |
| **Badge estado caja** | Verde "Caja abierta" / Rojo "Caja cerrada" |
| **Botón tickets apartados** | `v-if="heldCount"` — icono reloj con badge contador. Abre dropdown de recall |
| **Banner tickets sospechosos** | Alerta ámbar cuando hay tickets apartados > 2h. Botón X para descartar |

### Banner Caja Cerrada
*(visible cuando `!cajaStore.abierta`)*

| Elemento | Acción |
|----------|--------|
| **Mensaje "Caja cerrada"** | Alerta amarilla |
| **Botón "Abrir caja"** | `$router.push('/caja')` |

### Banner Tickets Sospechosos
*(visible cuando `hasSuspicious && showSusWarning`)*

| Elemento | Acción |
|----------|--------|
| **Mensaje** | "X ticket(s) apartados hace más de 2 horas — Posible fraude" |
| **Botón X** | `showSusWarning = false` — descarta banner (persiste en sesión) |

### Columna 1: Catálogo de Productos (5-8 columnas)

#### Buscador por Código de Barras

| Elemento | Acción |
|----------|--------|
| **Input de código de barras** | `v-model="posLookupCode"`, `@input="handlePOSInput"`, Enter → `triggerPOSLookup()` |
| **Contenedor de resultado** | Muestra según estado: |

**Estados del lookup:**

| Estado | UI | Descripción |
|--------|----|-------------|
| **Cargando local** | Spinner + "Buscando en base local..." | Primero busca en la DB local |
| **Buscando externo** | Borde animado naranja + ícono planeta + badges "Carrefour", "Vea", "Disco" | Busca en fuentes externas |
| **Encontrado (local)** | Se agrega directo al carrito con `addToCart(local)` | Producto existente en DB local — auto-add, no muestra card |
| **Encontrado (externo)** | Card producto: nombre, marca, precio, cantidad input + precio input + botón "Agregar" | Producto de fuente externa (no está en DB local) |
| **No encontrado** | Borde rojo + formulario manual: nombre, precio, cantidad + botón "Agregar al carrito" | Entrada manual (se guarda como `*MANUAL*`) |
| **Error** | Mensaje de error | Producto no encontrado |

#### Buscador por Texto

| Elemento | Acción |
|----------|--------|
| **Input de búsqueda textual** | `v-model="posTextSearch"`, filtra grilla de productos en vivo. `ref="textSearchRef"` — auto-focus al montar la vista |
| **Enter sin resultados** | `handleTextSearchEnter()` — abre diálogo "Producto no registrado, ¿desea crearlo?" |

#### Filtros por Categoría

| Elemento | Acción |
|----------|--------|
| **Chips de categorías** | "Todos" + categorías desde API. `@click="selectedPOSCategory = ..."` |

#### Grilla de Productos

| Elemento | Acción |
|----------|--------|
| **Botón de producto** | `@click="addToCart(p)"` — agrega al carrito. Muestra nombre, marca, precio, badge de stock. |

### Columna 2: Carrito de Ventas (4 columnas)

#### Lista del Carrito (TransitionGroup)

| Elemento | Acción |
|----------|--------|
| **Cada item del carrito** | Muestra nombre, cantidad, precio, subtotal |
| **Botón `-`** | `updateCartQty(idx, -1)` — decrementa cantidad |
| **Botón `+`** | `updateCartQty(idx, +1)` — incrementa cantidad |
| **Botón eliminar** | `removeFromCart(idx, silent=false)` — quita item con confirmación (`confirm()`). Si `silent=true` (usado desde qty=0), omite confirmación |

#### Resumen

| Elemento | Acción |
|----------|--------|
| **Subtotal** | Cálculo automático |
| **Input Descuento** | `v-model="cart.descuento"`, `@input="recalcCart"` |
| **Total** | Subtotal - descuento |
| **Medio de Pago** | Botones segmentados: Efectivo | Débito | Crédito | Transferencia | Cta.Cte. Atajos teclado: 1-5, flechas, Enter |
| **Select Cliente** | Dropdown de clientes + "Consumidor Final" |
| **Botón "Confirmar Venta"** | `confirmarVenta()` — flujo completo de confirmación |
| **Link "Vaciar carrito"** | `vaciarCarrito()` — limpia carrito |
| **Link "Hold"** | `holdTicket()` — aparta el carrito en localStorage, vacía el carrito. Muestra toast con ID del ticket |
| **Dropdown recall** | `showRecallDropdown` — lista tickets apartados con items, total, tiempo transcurrido. Tickets >2h destacados en ámbar |
| **Botón recall por ticket** | `recallTicket(id)` — restaura items, subtotal, descuento, cliente, medio de pago |
| **Botón descartar** | `deleteHeldTicket(id)` — elimina ticket (registra en auditoría local) |

### Columna 3: Estadísticas e Historial (3 columnas, toggleable)

| Elemento | Descripción |
|----------|-------------|
| **4 KPIs** | Ventas Hoy, Ticket Promedio, Efectivo, Caja |
| **Últimas Transacciones** | Lista de últimas 5 ventas |
| **Escaneos Recientes** | Badges de productos buscados recientemente |

### Flujo de Venta en POS

1. Escanear código de barras → Enter → `triggerPOSLookup()`
2. Búsqueda local → externa → manual (si no encuentra)
3. Definir cantidad y precio → "Agregar" → se añade al carrito
4. Repetir hasta completar la compra
5. Seleccionar medio de pago (teclas 1-5)
6. Opcional: seleccionar cliente, aplicar descuento
7. "Confirmar Venta" → POST `/api/ventas` → POST items → PUT confirmar
8. Suena efecto sonoro (si activado) + confeti (si es primera venta del día)
9. Muestra TicketModal
10. Carrito se vacía, focus vuelve al escáner

### Flujo de Apartado (Hold) / Recall

1. "Hold" → `holdTicket()` guarda carrito en `localStorage('apex-pos-held')` con timestamp, items, total
2. Carrito se vacía, toast informa ID del ticket
3. Badge contador en header del POS muestra cantidad de tickets apartados
4. "Recall" → dropdown lista tickets con items, total y tiempo transcurrido
5. Click en ticket → `recallTicket(id)` restaura carrito completo
6. Tickets > 2h se muestran con fondo ámbar y se marcan como sospechosos
7. Botón X → `deleteHeldTicket(id)` elimina ticket, queda registrado en auditoría local

### Flujo de Búsqueda por Texto + Creación Rápida

1. El buscador de texto tiene auto-focus al montar POS
2. Escribir nombre/marca/código → grilla filtra en vivo
3. Presionar Enter sin resultados → diálogo "Producto no registrado, ¿desea crearlo?"
4. Sí → abre QuickCreateModal con código pre-cargado (si el texto son 8+ dígitos)
5. En el modal: botón 🔍 busca en fuentes externas (deshabilita Nombre/Marca mientras busca)
6. Si código de barras vacío al guardar → se asigna `GEN-XXXXXXXX` secuencial
7. Guardar → POST `/api/productos` → producto se agrega a la grilla local
8. No → cierra diálogo, focus vuelve al buscador

### Modal: Creación Rápida de Producto (QuickCreateModal)

| Campo | Tipo | Detalle |
|-------|------|---------|
| **Código de Barras** | Input + botón 🔍 suffix | `lookupBarcode()` — busca en fuentes externas. Si vacío al guardar, auto-asigna `GEN-XXXXXXXX` |
| **Nombre del Producto** | Input text | Requerido, deshabilitado durante búsqueda externa |
| **Marca** | Input text | Deshabilitado durante búsqueda externa |
| **Precio Venta** | Input number | Requerido |
| **Categoría** | BaseSelect | Lista de categorías |
| **Botón "Crear Producto"** | Primary | `save()` → POST `/api/productos` → emite `created(product)` |
| **Botón "Cancelar"** | Ghost | Cierra modal |

**Origen:** Se abre desde el diálogo "Producto no registrado" al presionar Enter en el buscador de texto sin resultados.
**Props:** `show`, `barcode` (pre-cargado), `categories`, `nextGenCode`.

### API Calls en POS
- `GET /api/productos` — catálogo completo
- `GET /api/categorias` — categorías
- `GET /api/clientes` — lista de clientes
- `GET /api/dashboard/resumen` — stats panel
- `GET /api/caja/resumen` — resumen caja
- `GET /api/caja/estado` — estado caja
- `GET /api/ventas?page_size=5` — últimas transacciones
- `POST /api/productos/lookup` — búsqueda externa de código
- `POST /api/productos` — crear producto manual
- `POST /api/ventas` — crear venta
- `POST /api/ventas/{id}/items` — agregar item
- `PUT /api/ventas/{id}/confirmar` — confirmar venta

---

## 5. Productos

**Ruta:** `/products` — **Componente:** `ProductsView.vue` — **Roles:** admin, encargado (CRUD), todos (ver)

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Productos"** | — |
| **Botón "Sincronizar"** | `syncProducts()` — recarga productos y ofertas |
| **Botón "Nuevo Producto"** | `openCreateModal()` — abre modal de creación |
| **Botón "Nueva Oferta"** | `openCreateOfertaModal()` — abre modal de oferta |

### Filtros

| Elemento | Acción |
|----------|--------|
| **Input de búsqueda** | Filtra por nombre, código de barras, marca |
| **Select de categoría** | Filtra por categoría |
| **Toggle "Bajo stock"** | `filterStockBajo = !filterStockBajo` — mutuamente excluyente con precio |
| **Toggle "Precio <= costo"** | `filterPrecioDefasado = !filterPrecioDefasado` — mutuamente excluyente con stock |
| **Toggle "En oferta"** | `filterEnOferta = !filterEnOferta` — independiente |

### Tabla de Productos

| Columna | Descripción |
|---------|-------------|
| Imagen | Thumbnail del producto (40x40) |
| Nombre | Nombre + código de barras |
| Marca | Marca del producto |
| Costo | Precio de costo |
| Precio | Precio de venta |
| Stock | Cantidad actual + badge color según nivel |
| Categoría | Nombre de la categoría |
| Oferta | Badge color-coded: verde (2x1), azul (%), naranja ($) con detalle |
| Acciones | Editar 🖊, Eliminar 🗑 |

**Contador:** "X de Y productos"

### Modal: Crear/Editar Producto

| Campo | Tipo | Detalle |
|-------|------|---------|
| Código de barras | Input text | Enter → `lookupBarcode()` busca en fuentes externas |
| Marca | Input text | — |
| Nombre | Input text | Requerido |
| Precio costo | Input number | — |
| Precio venta | Input number | — |
| Stock inicial | Input number | Solo en creación |
| Stock mínimo | Input number | 0 = alerta deshabilitada, con hint text |
| Categoría | BaseSelect + botón `+` | Quick-create inline: nombre + botón Crear |
| Proveedor | Combobox + botón `+` | Quick-create inline: nombre + CUIT |
| Fecha vencimiento | Input date | Opcional |
| Observaciones | Textarea | Opcional |
| **Botón "Guardar"** | Primary | `saveProduct()` |
| **Botón "Cancelar"** | Ghost | `closeModal()` |

### Modal: Crear/Editar Oferta

| Campo | Tipo | Detalle |
|-------|------|---------|
| Producto | Select | Lista de productos |
| Tipo | Select | porcentaje / monto_fijo / 2x1 |
| Valor | Input number | % o monto según tipo |
| Cantidad Mínima | Input number | Requerida para 2x1 |
| Fecha Inicio | Input date | — |
| Fecha Fin | Input date | Opcional |
| Máx Unidades | Input number | Opcional (límite de uso) |
| Descripción | Textarea | Opcional |
| **Botón "Guardar"** | Primary | `saveOferta()` |
| **Botón "Cancelar"** | Ghost | `closeOfertaModal()` |

### Modal: Confirmar Eliminación

| Elemento | Acción |
|----------|--------|
| Mensaje de advertencia | "¿Eliminar producto X?" |
| **Botón "Cancelar"** | `deleteTarget = null` |
| **Botón "Eliminar"** | `executeDelete()` → DELETE `/api/productos/{id}` |

### API Calls
- `GET /api/productos?page_size=200` — listar productos
- `GET /api/categorias` — listar categorías
- `GET /api/ofertas?page_size=200` — listar ofertas
- `GET /api/proveedores` — listar proveedores
- `POST /api/productos/lookup` — lookup externo
- `POST /api/productos` — crear producto
- `PUT /api/productos/{id}` — actualizar producto
- `DELETE /api/productos/{id}` — eliminar producto
- `POST /api/productos/{id}/proveedores` — asignar proveedor
- `POST /api/ofertas` — crear oferta
- `PUT /api/ofertas/{id}` — actualizar oferta
- `DELETE /api/ofertas/{id}` — eliminar oferta
- `POST /api/categorias` — quick-create categoría
- `POST /api/proveedores` — quick-create proveedor

---

## 6. Caja

**Ruta:** `/caja` — **Componente:** `CajaView.vue` — **Roles:** admin, cajero

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Caja / Arqueo"** | — |
| **Botón "Sincronizar"** | `syncData()` — recarga movimientos y resumen |
| **Badge estado caja** | Verde "Abierta" / Rojo "Cerrada" |
| **Botón "Abrir Caja"** | `abrirCaja()` — prompt por monto inicial, POST `/api/caja/apertura` |
| **Botón "Cerrar Caja"** | `initCierreCaja()` — verifica tickets apartados, luego abre modal de arqueo |

### Resumen

| KPI | Descripción |
|-----|-------------|
| **Saldo Actual** | Balance desde última apertura |
| **Ingresos del Día** | Suma de ingresos |
| **Egresos del Día** | Suma de egresos |

### Cierre por Método de Pago
*(visible cuando caja abierta)*

| Elemento | Acción |
|----------|--------|
| **Botones de método** | Efectivo \| Débito \| Crédito \| Transferencia. `@click` activa formulario de cierre |
| **Badge "Cerrado"** | Métodos ya cerrados muestran check verde |
| **Formulario activo** | Monto Real + Comentario + Cancelar/Cerrar |

### Modal: Cierre de Caja (Arqueo)
*(visible al hacer "Cerrar Caja")*

| Elemento | Descripción |
|----------|-------------|
| **Métodos de pago** | Lista con: Esperado (calculado), Monto Real (input), Diferencia (color verde/rojo) |
| **Comentario general** | Campo opcional para nota al cierre |
| **Alerta tickets apartados** | Si hay tickets en hold: confirmación antes de continuar |
| **Botón "Confirmar Cierre"** | `confirmarCierreCaja()` — cierra cada método + cierre-total + logout automático |
| **Botón "Cancelar"** | Cierra el modal sin cerrar la caja |

### Movimientos del Día

| Columna | Descripción |
|---------|-------------|
| Fecha | Timestamp del movimiento |
| Tipo | Apertura / Ingreso / Egreso / Cierre |
| Monto | Formateado $ |
| Método | Efectivo / Débito / Crédito / Transferencia |
| Comentario | Descripción |

| Elemento | Acción |
|----------|--------|
| **Botón "Nuevo Movimiento"** | `showNuevoMovimiento = true` — abre modal (solo si caja abierta) |

### Modal: Nuevo Movimiento

| Campo | Acción |
|-------|--------|
| Tipo | Ingreso / Egreso |
| Monto | Input number |
| Método de Pago | Select |
| Comentario | Input text |
| **Botón "Registrar"** | `registrarMovimiento()` |
| **Botón "Cancelar"** | `showNuevoMovimiento = false` |

### Flujo de Cierre de Caja
1. "Cerrar Caja" → `initCierreCaja()` → GET `/api/caja/resumen` → obtiene desglose por método
2. Si hay tickets apartados → confirmación de huérfanos
3. Modal muestra montos esperados vs reales por método de pago
4. Cajero ingresa monto real contado en cada método
5. Diferencia se calcula y muestra en verde (sobrante) o rojo (faltante)
6. "Confirmar Cierre" → POST `/api/caja/cierre-metodo` por cada método + POST `/api/caja/cierre-total`
7. Logout automático → redirige a `/login`

### API Calls
- `GET /api/caja/movimientos` — listar movimientos
- `GET /api/caja/resumen` — resumen por método (para modal de cierre)
- `GET /api/caja/estado` — estado actual
- `POST /api/caja/apertura` — abrir caja
- `POST /api/caja/cierre-total` — cerrar caja + logout automático
- `POST /api/caja/cierre-metodo` — cerrar método con monto real y comentario
- `POST /api/caja/ingreso` — ingreso manual
- `POST /api/caja/egreso` — egreso manual

### Auto-cierre por Cambio de Día
- En `caja_service.caja_abierta()` compara fecha de apertura vs fecha actual
- Si es otro día, crea automáticamente `MovimientoCaja` tipo "cierre" y retorna `False`
- Previene vender con caja del día anterior

---

## 7. Ventas

**Ruta:** `/ventas` — **Componente:** `VentasView.vue` — **Roles:** todos

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Ventas"** | — |
| **Filtro por fecha** | Input date, filtra por prefijo de fecha |
| **Botón "Sincronizar"** | `syncData()` — recarga ventas |

### Tabla de Ventas (expandible)

| Columna | Descripción |
|---------|-------------|
| Ticket | Número de venta (V-XXXXX) |
| Fecha | Fecha y hora |
| Cliente | Nombre del cliente o "Consumidor Final" |
| Medio de Pago | Badge del método |
| Total | Monto formateado |
| Estado | Badge: Completada (verde), Pendiente (amarillo), Anulada (rojo) |
| Acciones | Expandir 🔽, Ver 👁, Anular 🚫 (solo en "Completada") |

### Detalle Expandido (por fila)

| Elemento | Descripción |
|----------|-------------|
| **Tabla de productos** | Producto, Cantidad, Precio Unitario, Subtotal |
| **Resumen** | Total, Descuento, Medio de Pago |

| Elemento | Acción |
|----------|--------|
| **Botón 🔽** | `toggleRow(id)` — expande/colapsa detalle |
| **Botón "Ver"** | `toggleRow(id)` — mismo comportamiento |
| **Botón "Anular"** | `confirmAnular(row)` — abre modal de confirmación |

### Modal: Anular Venta

| Elemento | Acción |
|----------|--------|
| Mensaje de advertencia | "¿Anular venta N° XXXX?" |
| **Botón "Cancelar"** | `anularTarget = null` |
| **Botón "Anular"** | `executeAnular()` → PUT `/api/ventas/{id}/anular` |

### API
- `GET /api/ventas` — listar ventas (filtro: estado, cliente_id)

---

## 8. Clientes

**Ruta:** `/clientes` — **Componente:** `ClientesView.vue` — **Roles:** admin, encargado

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Clientes"** | — |
| **Botón "Sincronizar"** | `syncClients()` |
| **Botón "Nuevo cliente"** | `openCreateModal()` |

### Tabla de Clientes

| Columna | Descripción |
|---------|-------------|
| Nombre | Nombre del cliente |
| Doc. Tipo | DNI / CUIT / CUIL |
| Doc. Número | Número de documento |
| Teléfono | — |
| Límite crédito | Monto límite disponible |
| Saldo | Monto actual. Color rojo cuando >80% usado |
| Acciones | WhatsApp 💬 (si tiene teléfono), Editar 🖊, Ver Tickets 🎫, Cobrar 💰 (si tiene deuda) |

### Modal: Crear/Editar Cliente

| Campo | Detalle |
|-------|---------|
| Nombre | Requerido |
| Tipo documento | DNI / CUIT / CUIL |
| Número documento | Único en sistema |
| Teléfono | Opcional |
| Email | Opcional |
| Dirección | Opcional |
| Límite de crédito | Para cuenta corriente |
| Notas | Opcional |
| **Botón "Guardar"** | `saveClient()` |
| **Botón "Cancelar"** | `showModal = false` |

### Modal: Historial de Tickets

| Elemento | Descripción |
|----------|-------------|
| **Header cliente** | Nombre + Deuda total |
| **Lista de tickets** | Expandibles con detalle de productos |
| **Footer** | Total deuda + Botón "Imprimir resumen" |

| Elemento | Acción |
|----------|--------|
| **Badge 🔽** | `toggleTicket(id)` — expande detalle del ticket |
| **Botón "Imprimir resumen"** | `imprimirResumen()` — abre ventana de impresión |

### Modal: Cobrar Deuda

| Elemento | Descripción |
|----------|-------------|
| **Deuda actual** | Monto total en rojo |
| **Monto a cobrar** | Input numérico (0.01 a deuda total) |
| **Preview diferencia** | Muestra deuda restante tras el cobro |
| **Botón "Confirmar Cobro"** | `confirmarCobro()` → POST `/api/clientes/{id}/abonar` |
| **Botón "Cancelar"** | Cierra modal |

### Botón WhatsApp en Clientes
- Solo visible si el cliente tiene teléfono
- Enlace `https://wa.me/{numero}?text={mensaje}`
- Mensaje prellenado:
  - Con deuda: `"Hola {nombre}, tu saldo actual es ${monto}. ¿Podemos coordinar el pago?"`
  - Al día: `"Hola {nombre}, tu saldo actual es ${monto}. Todo al día. ¡Gracias!"`

### API
- `GET /api/clientes` — listar clientes
- `GET /api/ventas?cliente_id=X` — tickets del cliente
- `POST /api/clientes/{id}/abonar` — registrar pago parcial o total de deuda

---

## 9. Proveedores

**Ruta:** `/proveedores` — **Componente:** `ProveedoresView.vue` — **Roles:** admin, encargado, repositor

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Proveedores"** | — |
| **Botón "Sincronizar"** | `syncProveedores()` |
| **Botón "Nuevo proveedor"** | `openCreateModal()` |

### KPIs

| KPI | Descripción |
|-----|-------------|
| Total proveedores | Cantidad |
| Activos | Con estado activo |
| Inactivos | Con estado inactivo |
| Último agregado | Nombre del último |

### Tabla de Proveedores

| Columna | Descripción |
|---------|-------------|
| Nombre | — |
| CUIT | — |
| Teléfono | — |
| Email | — |
| Contacto | Persona de contacto |
| Estado | Badge Activo/Inactivo |
| Acciones | Editar 🖊, Toggle activo 🔄 |

### Modal: Crear/Editar Proveedor

| Campo | Detalle |
|-------|---------|
| Nombre | Requerido |
| CUIT | Único |
| Teléfono | Opcional |
| Email | Opcional |
| Persona de contacto | Opcional |
| **Botón "Guardar"** | `saveSupplier()` |
| **Botón "Cancelar"** | `showModal = false` |

### API
- `GET /api/proveedores` — listar
- `POST /api/proveedores` — crear
- `PUT /api/proveedores/{id}` — actualizar

---

## 10. Compras

**Ruta:** `/compras` — **Componente:** `ComprasView.vue` — **Roles:** admin, encargado, repositor

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Compras"** | — |
| **Botón "Sincronizar"** | `syncData()` |
| **Botón "Nueva Compra"** | `abrirModalNuevaCompra()` |

### Tabla de Órdenes de Compra

| Columna | Descripción |
|---------|-------------|
| N° Orden | Número (C-XXXXX) |
| Proveedor | Nombre del proveedor |
| Total | Monto formateado (color brand-600) |
| Canti. | Total de artículos pedidos |
| Pendiente | Artículos pendientes de recibir |
| Estado | Badge: Pendiente (amarillo), Parcial (azul), Recibida (verde), Anulada (rojo) |
| Fecha | dd/mm/yy HH:mm (fecha y hora) |
| Comentarios | Icono 💬 solo si hay notas |
| Acciones | WhatsApp 💬 (si tiene teléfono), Recibir 📦 (Pendiente/Parcial) |

### Modal: Nueva Compra

| Sección | Elemento | Acción |
|---------|----------|--------|
| **Datos** | Select Proveedor | Lista de proveedores |
| **Datos** | Notas | Textarea opcional |
| **Items** | Grilla dinámica | Filas agregables automáticamente |

#### Grilla de Items (dinámica)

| Columna | Tipo | Comportamiento |
|---------|------|----------------|
| Producto | Input text + datalist | Enter/Tab → completa desde catálogo |
| Código de Barras | Input text | Enter → busca en catálogo local + externo |
| Cantidad | Input number | Enter → nueva fila |
| Precio | Input number | — |
| Eliminar | Botón 🗑 | `quitarItem(idx)` |

**Comportamiento:** Siempre hay una fila vacía activa al final. Al completar una fila, se crea automáticamente la siguiente.

| Elemento | Acción |
|----------|--------|
| **Total calculado** | Suma de cantidad × precio de todos los items |
| **Botón "Guardar"** | `guardarCompra()` → POST `/api/compras` (con items incluidos) |
| **Botón "Cancelar"** | `showModalCompra = false` |

### Modal: Recibir Mercadería

| Columna | Descripción |
|---------|-------------|
| Producto | Nombre |
| Pedido | Cantidad ordenada |
| Recibido | Cantidad ya recibida |
| Pendiente | Cantidad pendiente |
| Recibir ahora | Input numérico (default: pendiente) |

| Elemento | Acción |
|----------|--------|
| **Botón "Confirmar"** | `confirmarRecepcion()` → PUT `/api/compras/{id}/recibir` |
| **Botón "Cancelar"** | `showReceiveModal = false` |

### Modal: Ver/Agregar Comentarios

| Elemento | Descripción |
|----------|-------------|
| **Historial** | Muestra todos los comentarios previos con fecha/hora y autor |
| **Agregar comentario** | Textarea + botón "Agregar" |
| **Botón "Cerrar"** | Cierra modal |

### Flujo de Compra
1. "Nueva Compra" → seleccionar proveedor
2. Agregar items: escanear código o escribir nombre (datalist con catálogo)
3. Completar cantidades y precios
4. "Guardar" → POST `/api/compras` con items (estado "pendiente")
5. Cuando llega la mercadería: "Recibir" → ajustar cantidades recibidas → "Confirmar"
6. El stock se actualiza: baja stock_transito, sube stock_actual, actualiza precio_costo
7. Si recepción parcial → estado "parcial"; si completa → "recibida"

### API
- `GET /api/compras` — listar
- `GET /api/proveedores` — listar proveedores
- `GET /api/productos?page_size=200` — catálogo
- `POST /api/productos/lookup` — lookup por código
- `POST /api/compras` — crear orden (con items incluidos)
- `PUT /api/compras/{id}/recibir` — recibir mercadería
- `POST /api/compras/{id}/comentario` — agregar comentario con fecha/hora

---

## 11. Calendario

**Ruta:** `/calendario` — **Componente:** `CalendarioView.vue` — **Roles:** todos

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Calendario"** | — |
| **Selector de fecha** | Input date, controla qué día ver |
| **Botón "Actualizar"** | `syncCalendario()` |

### Tabs (Filtros de Actividad)

| Tab | Muestra |
|-----|---------|
| **Todo** | Todas las secciones |
| **Ventas** | Solo ventas |
| **Caja** | Solo movimientos de caja |
| **Compras** | Solo compras recibidas |
| **Productos** | Solo productos nuevos/modificados |
| **Clientes** | Solo nuevos clientes |

### Secciones por Tab

#### Ventas del Día

| Elemento | Descripción |
|----------|-------------|
| **KPIs** | Total vendido, Tickets emitidos, Promedio por ticket, Productos vendidos |
| **Detalle expandible** | Tabla de ventas con items |

#### Movimientos de Caja

| Elemento | Descripción |
|----------|-------------|
| **KPIs** | Balance, Ingresos, Egresos |
| **Detalle expandible** | Tabla de movimientos |

#### Compras Recibidas

| Elemento | Descripción |
|----------|-------------|
| **KPIs** | Total comprado, Recepciones, Items recibidos |
| **Detalle expandible** | Tabla de compras con items |

#### Productos Nuevos / Modificados

| Elemento | Descripción |
|----------|-------------|
| **Nuevos** | Tabla de productos creados hoy |
| **Modificados** | Tabla de productos actualizados hoy |

#### Nuevos Clientes

| Elemento | Descripción |
|----------|-------------|
| **Tabla** | Clientes registrados hoy |

### API
- `GET /api/calendario/dia?fecha=YYYY-MM-DD` — actividad del día

---

## 12. Reportes

**Ruta:** `/reportes` — **Componente:** `ReportesView.vue` — **Roles:** admin, encargado

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Reportes"** | — |
| **Botón "Sincronizar todo"** | `syncAll()` — recarga los 3 reportes |
| **Botón "Exportar todo"** | Sin handler asignado |

### Cards de Reportes (grid de 3)

#### Reporte Semanal

| Elemento | Descripción |
|----------|-------------|
| **Total Ventas** | Suma de la semana |
| **Vs. Semana Anterior** | Badge con % de cambio |
| **Gráfico de barras** | 7 días |
| **Top 5 Productos** | Lista rankeada |
| **Botón sync propio** | `syncWeekly()` |

#### Reporte Mensual

| Elemento | Descripción |
|----------|-------------|
| **Total Ventas** | Suma del mes |
| **Vs. Mes Anterior** | Badge con % de cambio |
| **Gráfico de barras** | 4 semanas |
| **Por Categoría** | Badges con total por categoría |
| **Top 5 Productos** | Lista rankeada |
| **Botón sync propio** | `syncMonthly()` |

#### Reporte Trimestral

| Elemento | Descripción |
|----------|-------------|
| **Total Ventas** | Suma del trimestre |
| **Vs. Trim. Anterior** | Badge con % de cambio |
| **Gráfico de barras** | 3 meses |
| **Top 5 Productos** | Lista rankeada |
| **Botón sync propio** | `syncQuarterly()` |

### API
- `GET /api/dashboard/semanal` — reporte semanal vs semana anterior
- `GET /api/dashboard/mensual` — reporte mensual vs mes anterior, por semana, por categoría
- `GET /api/dashboard/trimestral` — reporte trimestral vs trimestre anterior, por mes

---

## 13. Usuarios

**Ruta:** `/usuarios` — **Componente:** `UsuariosView.vue` — **Roles:** admin

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Usuarios"** | — |
| **Botón "Nuevo usuario"** | `openCreateModal()` |

### Tabla de Usuarios

| Columna | Descripción |
|---------|-------------|
| Usuario | Nombre de usuario + avatar |
| Nombre | Nombre completo |
| Rol | Badge con icono: Admin 🔑, Encargado ⭐, Cajero 💰, Repositor 📦 |
| Estado | Activo (verde pulse) / Inactivo (gris) |
| Último acceso | Fecha y hora |
| Acciones | Editar 🖊, Activar/Desactivar 🔄 |

### Modal: Crear/Editar Usuario

| Campo | Detalle |
|-------|---------|
| Usuario | Requerido, único |
| Nombre completo | Requerido |
| Contraseña | Requerido en creación, opcional en edición |
| Rol | Select: Admin, Encargado, Cajero, Repositor |
| **Botón "Guardar"** | `saveUser()` |
| **Botón "Cancelar"** | `showModal = false` |

### API
- `GET /api/usuarios` — listar
- `POST /api/usuarios` — crear
- `PUT /api/usuarios/{id}` — actualizar (incluye toggle activo)

---

## 14. Licencias

**Ruta:** `/licencias` — **Componente:** `LicenciasView.vue` — **Roles:** admin

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Licencias"** | — |
| **Botón "Generar licencia"** | `openGenerateModal()` |

### KPIs

| KPI | Descripción |
|-----|-------------|
| Licencias totales | Cantidad |
| Activas | Con estado activa |
| Próximas a vencer (30d) | Cuántas vencen en 30 días |

### Tabla de Licencias

| Columna | Descripción |
|---------|-------------|
| Clave | Código APX-XXXX-XXXX-XXXX |
| Cliente | Nombre del cliente |
| ID Máquina | Hostname + hash de disco |
| Vencimiento | Fecha | | 
| Días restantes | Color-coded: verde (>30), amarillo (7-30), rojo (<7) |
| Estado | Activa (verde) / Inactiva (gris) |
| Acciones | Activar ✅ / Desactivar 🚫 |

### Modal: Generar Licencia

| Campo | Detalle |
|-------|---------|
| Cliente | Nombre del cliente |
| Machine ID | ID de máquina destino |
| Duración | Select: 30, 90, 180, 365, 730 días |
| Clave generada | Texto clickeable para copiar |
| **Botón "Generar"** | `generateLicense()` → POST `/api/licencia/generar` |
| **Botón "Listo"** | Cierra modal |

### API
- `GET /api/licencia/historial` — historial de licencias
- `POST /api/licencia/generar` — generar nueva
- `POST /api/licencia/activar` — activar licencia
- PATCH `/api/licencia/{id}/toggle` — desactivar

---

## 15. Auditoría

**Ruta:** `/auditoria` — **Componente:** `AuditoriaView.vue` — **Roles:** admin

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Auditoría"** | — |
| **Badge "Sospechosos"** | Contador de eventos sospechosos |
| **Botón "Auto-refrescar"** | `toggleAutoRefresh()` — toggle refresco cada 30s |
| **Botón "Refrescar"** | `refreshLogs()` |

### Barra de Filtros

| Elemento | Acción |
|----------|--------|
| **Filtros por tipo** | Todo | Ventas | Caja | Compras | Productos | Clientes |
| **Toggle "Solo sospechosos"** | `soloSospechosos = !soloSospechosos` |

### Tabla de Logs

| Columna | Descripción |
|---------|-------------|
| Timestamp | Fecha + hora relativa |
| Usuario | Avatar + nombre |
| Evento | Emoji + badge según tipo |
| Acción | Descripción textual |
| Detalle | Renderizado variable según evento |
| Alerta | Badge "Sospechoso" si aplica |

**Colores de fila por tipo de evento:**
- Carrito creado → azul claro
- Venta confirmada → verde
- Venta anulada → rosado
- Item quitado → ámbar
- Carrito abandonado → rosado
- Stock sospechoso → rojo claro

### API
- `GET /api/auditoria` — logs de auditoría con detección de carritos abandonados

---

## 16. Backups

**Ruta:** `/backups` — **Componente:** `BackupsView.vue` — **Roles:** admin, encargado

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Título "Backups"** | — |
| **Botón "Configurar R2"** | `openR2Config()` — abre modal de configuración Cloudflare R2 |
| **Botón "Crear backup"** | `createBackup()` → POST `/api/backups/crear` |

### KPIs

| KPI | Descripción |
|-----|-------------|
| Último backup local | Fecha del último |
| Tamaño último backup | En KB/MB |
| Sincronización R2 | Conectado / Desconectado |
| Próximo backup automático | Countdown |

### Panel: Backups Locales

| Columna | Descripción |
|---------|-------------|
| Nombre | Archivo .gz |
| Tamaño | Formateado |
| Fecha | Timestamp |
| Acciones | Descargar ⬇, Subir a R2 ☁, Eliminar 🗑 |

### Panel: Backups en R2 Cloud

| Columna | Descripción |
|---------|-------------|
| Nombre | Archivo .gz |
| Tamaño | Formateado |
| Fecha | Timestamp |
| Sincronización | Badge de estado |
| Acciones | Descargar de R2 ⬇ |

### Card: Catálogo

| Elemento | Acción |
|----------|--------|
| **KPIs** | Productos exportables, Última exportación, Catálogo cargado en memoria |
| **Botón "Exportar y Subir Catálogo"** | `exportarCatalogo()` |
| **Botón "Descargar Catálogo Central"** | `descargarCatalogoCentral()` |
| **Botón "Recargar Catálogo"** | `recargarCatalogo()` |

### Modal: Configuración R2

| Campo | Detalle |
|-------|---------|
| Endpoint | URL del bucket R2 |
| Access Key | Clave de acceso |
| Secret Key | Clave secreta |
| Bucket | Nombre del bucket |
| **Botón "Probar conexión"** | `testConnection()` — muestra resultado |
| **Botón "Guardar"** | `saveR2Config()` |
| **Botón "Cancelar"** | `showR2Config = false` |

### API
- `GET /api/backups/local` — listar locales
- `GET /api/backups/r2` — listar en R2
- `POST /api/backups/crear` — crear backup
- `POST /api/backups/subir` — subir a R2
- `POST /api/backups/descargar` — descargar de R2
- `DELETE /api/backups/local/{filename}` — eliminar local
- `GET /api/backups/estado` — estado del sistema
- `GET /api/catalogo/estado` — estado del catálogo
- `POST /api/catalogo/exportar` — exportar catálogo
- `POST /api/catalogo/descargar` — descargar catálogo central
- `POST /api/catalogo/recargar` — recargar catálogo en memoria

---

## 17. Elementos Globales

### Command Palette (Ctrl+K / F2)

| Sección | Comandos |
|---------|----------|
| **Navegación** | Ir a Dashboard, POS, Productos, Caja, Ventas, Calendario, Compras, Proveedores, Clientes, Reportes, Usuarios, Licencias, Auditoría, Backups |
| **Acciones** | Alternar modo oscuro, Alternar sonidos, Abrir ayuda, Cerrar sesión |
| **Búsqueda dinámica** | Productos y clientes con 300ms debounce |

### Toggle Modo Oscuro
- Sidebar → toggle sol/luna
- Persiste en localStorage (`apex-dark-mode`)
- Script anti-flash en `<head>` de `index.html`

### Toggle Sonidos
- Header → toggle de sonido
- Web Audio API (sine/triangle waves, sin archivos mp3)
- Efectos: venta confirmada, abrir caja, cerrar caja
- Persiste en localStorage (`apex-sounds-enabled`)

### Toggle Modo Simulador/Real
- Header → cambia `apiMode` entre mock y API real
- Muestra datos mock si la API no responde

### Indicador de Red
- Header → destello en cada request
- Muestra actividad de red

### Sync Indicator
- Header → última sincronización con color según antigüedad
- Timestamp actualizado por `api.js` en cada request exitoso

### Atajos Globales de Teclado
- `Ctrl+K` / `Cmd+K` → Command Palette
- `F2` → POS
- `?` → Modal de atajos
- `Esc` → Cerrar modales / búsqueda

---

## 18. Flujos Funcionales Críticos

### Flujo 1: Venta Completa (POS)
```
[Escáner] → Enter → triggerPOSLookup()
  ├─ Buscar en DB local → encontrado → mostrar card
  ├─ Buscar en fuentes externas → encontrado → mostrar card + badge fuente
  └─ No encontrado → formulario manual (*MANUAL*)
[Agregar al carrito] → item en carrito
[Repetir escaneo hasta completar]
[Seleccionar medio de pago] (1-5)
[Seleccionar cliente opcional]
[Aplicar descuento opcional]
[Confirmar Venta]
  ├─ ¿Caja abierta? Sí → continuar
  ├─ ¿Caja abierta? No → mostrar banner "Abrir caja"
  ├─ POST /api/ventas → crear venta pendiente
  ├─ POST /api/ventas/{id}/items (por cada item)
  ├─ PUT /api/ventas/{id}/confirmar
  │   ├─ Verificar stock suficiente
  │   ├─ Descontar stock (MovimientoStock)
  │   ├─ Registrar ingreso en caja (MovimientoCaja)
  │   ├─ Si cta_corriente: actualizar saldo cliente
  │   ├─ Si oferta: incrementar unidades_vendidas
  │   └─ Verificar auto-desactivación de ofertas
  ├─ Efecto sonido (si activado)
  ├─ Confeti (primera venta del día)
  └─ Mostrar TicketModal
[Vaciar carrito] → focus al escáner
```

### Flujo 2: Apertura y Cierre de Caja
```
[ABRIR]
Cajero → /caja → "Abrir Caja"
  ├─ Prompt: "Monto inicial $X"
  └─ POST /api/caja/apertura → caja abierta

[OPERAR DÍA]
Cada venta confirmada → MovimientoCaja ingreso
Puede haber ingresos/egresos manuales

[CIERRE POR MÉTODO]
Por cada método de pago:
  "Cerrar Método" → input monto real → POST /api/caja/cierre-metodo
  Sistema calcula diferencia vs esperado

[CIERRE TOTAL]
"Cerrar Caja" → initCierreCaja() → GET /api/caja/resumen
  ├─ Modal muestra montos esperados vs reales por método
  ├─ Cajero ingresa monto real de cada método
  └─ "Confirmar Cierre" → POST /api/caja/cierre-metodo (por método)
  └─ POST /api/caja/cierre-total → logout automático → /login

[CIERRE AUTOMÁTICO]
Al iniciar día siguiente: `caja_abierta()` detecta cambio de fecha
  └─ Crea cierre automático → obliga a nueva apertura
```

### Flujo 3: Compra y Recepción
```
[CREAR OC]
Encargado → /compras → "Nueva Compra"
  ├─ Seleccionar proveedor
  ├─ Escanear/escribir productos (grilla dinámica)
  ├─ Completar cantidades y precios
  └─ "Guardar" → POST /api/compras → estado "pendiente"
      └─ stock_transito += cantidades

[RECIBIR MERCADERÍA]
Cuando llega → "Recibir" en la OC
  ├─ Ingresar cantidades recibidas (parcial o total)
  └─ "Confirmar" → PUT /api/compras/{id}/recibir
      ├─ stock_transito -= recibido
      ├─ stock_actual += recibido
      ├─ precio_costo se actualiza
      └─ estado: "Recibido" (100%) o "Parcial" (<100%)

[ANULAR]
"Anular" → PUT /api/compras/{id}/anular
  └─ stock_transito revierte
```

### Flujo 4: Búsqueda por Código de Barras
```
Input código → Enter
  1. DB local (SQLite) → ¿existe?
     ├─ Sí → retorna producto
     └─ No → ¿código en catálogo central (JSON en memoria)?
       ├─ Sí → retorna producto
       └─ No → busca en fuentes externas (paralelo)
         ├─ Carrefour (API) → ¿responde?
         ├─ Vea (scraping) → ¿responde?
         ├─ MasOnline (scraping) → ¿responde?
         └─ Super Coco (scraping) → ¿responde?
           ├─ Alguna encontró → retorna producto + badge fuente
           └─ Ninguna → "Producto no encontrado" → formulario manual
```

### Flujo 5: Anulación de Venta
```
[Admin/Encargado] → /ventas → "Anular" en venta completada
  ├─ Confirmación modal
  └─ PUT /api/ventas/{id}/anular
      ├─ Revertir stock (MovimientoStock: venta_anulada)
      ├─ Revertir caja (MovimientoCaja: venta_anulada)
      ├─ Si cta_corriente: revertir saldo cliente
      └─ estado → "anulada"
```

### Flujo 6: Edición de Producto con Cambio de Stock
```
[Admin/Encargado] → /products → Editar producto
  ├─ Cambiar stock_actual
  └─ Guardar → PUT /api/productos/{id}
      ├─ Stock diferente → stock_service.ajustar_stock(diferencia)
      ├─ Si usuario no es admin → auditoria: "stock_sospechoso"
      └─ Actualizar demás campos
```

### Flujo 7: Ofertas — Ciclo de Vida
```
[CREAR]
Admin/Encargado → /products → "Nueva Oferta"
  ├─ Seleccionar producto, tipo (%, $, 2x1), valor, fechas, límites
  └─ POST /api/ofertas → oferta activa

[APLICAR EN VENTA]
Al confirmar venta:
  └─ venta_service.confirmar_venta()
      └─ oferta_service.incrementar_vendidas(producto_id, cantidad)
          └─ Si max_unidades alcanzado → desactivar automáticamente

[AUTO-DESACTIVAR]
  └─ verificar_y_desactivar() en cada incrementar_vendidas()
      ├─ ¿fecha_fin pasada? → activo = false
      └─ ¿unidades_vendidas >= max_unidades? → activo = false
```

### Flujo 8: Apartado (Hold) y Recuperación de Tickets
```
[HOLD — APARTAR CARRITO]
Cajero → POS → "Hold"
  ├─ Guarda carrito completo en localStorage('apex-pos-held'):
  │   ├─ items, subtotal, descuento, total, medio_pago, cliente_id
  │   ├─ timestamp creado (createdAt)
  │   └─ itemCount
  ├─ Registra auditoría local: evento 'HOLD'
  ├─ Carrito se vacía
  └─ Badge contador en POS se actualiza

[RECALL — RECUPERAR]
Dropdown de tickets apartados:
  ├─ Muestra items, total, tiempo transcurrido
  ├─ Tickets >2h resaltados en ámbar (sospechosos)
  └─ Click → recallTicket(id):
      ├─ Restaura items, subtotal, descuento, cliente, medio_pago
      ├─ Elimina ticket de localStorage
      ├─ Registra auditoría local: evento 'RECALL'
      └─ Badge contador decrementa

[DESCARTAR]
Botón X en ticket del dropdown:
  ├─ Marca _deleted = true + timestamp
  ├─ Registra auditoría local: evento 'DELETE_HELD'
  └─ Elimina del array

[ORPHANED — CIERRE DE CAJA]
Si hay tickets apartados al cerrar caja:
  ├─ Advertencia: "Se marcarán como huérfanos"
  ├─ Marca _orphaned = true en cada ticket
  └─ Visibles en getHeldAuditLog()

[SOSPECHOSOS]
Tickets con createdAt > 2hs:
  ├─ Banner ámbar en POS: "X ticket(s) apartados hace más de 2 horas — Posible fraude"
  ├─ Dropdown los resalta con fondo ámbar
  └─ No se eliminan automáticamente, requieren acción manual
```

### Flujo 9: Creación Rápida de Producto desde Búsqueda POS
```
[BUSCAR SIN RESULTADOS]
Cajero escribe en buscador de texto → Enter
  └─ filteredPOSProducts está vacío → diálogo "Producto no registrado, ¿desea crearlo?"
      ├─ Sí (Enter) → abre QuickCreateModal
      │   ├─ Si texto son 8+ dígitos → pre-carga como código de barras
      │   ├─ Si vacío → auto-asigna GEN-XXXXXXXX secuencial
      │   ├─ Botón 🔍 → POST /api/productos/lookup → deshabilita Nombre/Marca
      │   ├─ Guardar → POST /api/productos → agrega a grilla local
      │   └─ Cierra modal, focus a grilla
      └─ No (Esc) → cierra diálogo, focus al buscador
```

---

## 19. Reglas de Negocio

1. **Stock**: No se puede vender más de lo que hay en stock disponible.
2. **Precio histórico**: VentaItem guarda el precio al momento de la venta, no el precio actual del producto.
3. **Anulación**: Anular una venta revierte el stock automáticamente (MovimientoStock tipo "venta_anulada").
4. **Caja**: No se puede vender si la caja no está abierta.
5. **Auto-cierre caja**: Si cambia el día, la caja se cierra automáticamente.
6. **Cta. Corriente**: Pago con "cta_corriente" incrementa saldo del cliente. No excede límite de crédito.
7. **Soft delete**: Productos, clientes, proveedores no se borran físicamente, se desactivan (activo=False).
8. **Lookup orden**: DB local → catálogo central (JSON en memoria) → 4 fuentes externas en paralelo.
9. **Carga manual POS**: Formato `*Nombre*Precio` escaneado crea producto al vuelo (stock=10, costo=0).
10. **Stock en tránsito**: Al crear OC pendiente, stock_transito se acumula. Al recibir, baja tránsito y sube stock real.
11. **Ofertas**: Se desactivan automáticamente por fecha o por alcanzar max_unidades.
12. **Stock sospechoso**: Si un no-admin cambia stock, se registra en auditoría como "stock_sospechoso".
13. **Stock mínimo**: Si stock_actual <= stock_minimo, se marca como "bajo stock" (alerta visual).
14. **Barcode lookup en POS**: Auto-trigger a los 13+ caracteres escaneados vía `@input`. Si se dispara `triggerPOSLookup()`, `handlePOSInput()` hace `return` inmediato para no pisar `_searched` / `id` con `false`/`null`.
15. **Producto local encontrado en POS**: Se agrega directo al carrito con `addToCart()`, se limpia el input y se re-enfoca el `barcodeInput` vía `nextTick`. No se muestra card ni se require click en "Agregar".
16. **Focus del escáner POS**: Siempre retorna al `barcodeInput` después de: agregar item, finalizar venta, o cerrar TicketModal. `defineExpose({ focus })` en BaseInput.vue expone la función para ser llamada por ref.
15. **Confirmación de venta**: Si hay ofertas, se incrementa unidades_vendidas y se verifica desactivación.
16. **Hold/Recall**: Los tickets apartados se guardan en localStorage y no tienen respaldo en servidor. Si se pierde localStorage, se pierden.
17. **Sospechosos**: Tickets apartados > 2h se consideran sospechosos (posible fraude) y se destacan visualmente.
18. **Huérfanos**: Tickets apartados al momento de cerrar caja se marcan como `_orphaned` para auditoría.
19. **Auto-generación de código de barras**: Si se deja vacío al crear producto, se asigna `GEN-XXXXXXXX` secuencial.

---

## 20. Atajos de Teclado

### Globales (App.vue)

| Tecla | Acción |
|-------|--------|
| `Ctrl+K` / `Cmd+K` | Abrir Command Palette |
| `F2` | Ir al POS |
| `?` | Abrir modal de atajos |
| `Esc` | Cerrar modales / command palette |

### POS (teclas rápidas)

| Tecla | Acción |
|-------|--------|
| `1` | Efectivo |
| `2` | Débito |
| `3` | Crédito |
| `4` | Transferencia |
| `5` | Cta. Corriente |
| `←` / `→` | Navegar entre medios de pago |
| `Enter` | Confirmar venta (en sección pago) |
| `Enter` | Disparar búsqueda por código de barras |
| `Enter` (en buscador texto sin resultados) | Abrir diálogo "Producto no registrado" → crear producto |
| `Enter` (en diálogo "crear producto") | Confirmar creación |
| `Esc` (en diálogo "crear producto") | Cancelar creación |

### Compras (grilla de items)

| Tecla | Acción |
|-------|--------|
| `Enter` en producto | Completa desde catálogo, crea nueva fila |
| `Tab` en producto | Completa desde catálogo |
| `Enter` en cantidad | Crea nueva fila |
| `Enter` en código barras | Dispara lookup externo |

### Login

| Tecla | Acción |
|-------|--------|
| `Enter` en usuario | Foco a password |
| `Enter` en password | Ejecuta login |

---

*Documento actualizado el 30/06/2026 — Refleja el estado actual del sistema con todas las funcionalidades desarrolladas.*
