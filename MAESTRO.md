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
11. [Precios Online](#11-precios-online)
12. [Calendario](#12-calendario)
13. [Reportes](#13-reportes)
14. [Usuarios](#14-usuarios)
15. [Licencias](#15-licencias)
16. [Auditoría](#16-auditoría)
17. [Backups](#17-backups)
18. [Elementos Globales](#18-elementos-globales)
19. [Flujos Funcionales Críticos](#19-flujos-funcionales-críticos)
20. [Reglas de Negocio](#20-reglas-de-negocio)
21. [Atajos de Teclado](#21-atajos-de-teclado)

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
| **Recargas Hoy** | Solo aparece si hubo recargas: monto cargado hoy ($) + cantidad y ganancia del adicional. Viene de `recargas_hoy` en `GET /api/dashboard/resumen` |
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
| **Botón selector de carritos** | Header del POS, solo si hay más de un carrito. Icono capas con badge contador. Abre el panel de carritos (el card va con `:overflow="false"`: con el `overflow-hidden` de `BaseCard` el panel quedaba recortado) |
| **Banner carritos sospechosos** | Alerta ámbar cuando hay un carrito abierto > 2h **dentro de la sesión de caja actual**. Botón X para descartar |

> **La vida de un carrito se cuenta dentro de la sesión de caja.** `/api/caja/estado` devuelve `sesion_id` y `sesion_inicio` (UTC con "Z"); el store de caja llama a `carritoStore.sincronizarSesion()` en cada `fetchEstado()`. Cuando arranca una caja nueva, los carritos que seguían abiertos reinician su reloj con ella (un carrito de ayer ya no dice "hace 38h" al abrir caja hoy). La sesión vigente se guarda en `localStorage` (`apex-pos-carritos.sesionId`), así que recargar el POS no reinicia nada.

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

> **Entrada manual `*Nombre*Precio`.** Al escribir algo que empieza con `*`, el producto se confirma **cuando el operador deja de escribir** (700 ms de pausa), no al escribir el segundo `*`: el precio va después del segundo asterisco, así que dispararlo ahí saltaba el aviso de formato y borraba lo tipeado. A medio escribir no se avisa ni se borra nada; el aviso "Formato: *Nombre*Precio" queda solo para cuando el error fue un **Enter** explícito. El producto entra al carrito como pendiente (`_pending`) y se crea en la BD al confirmar la venta.

| Elemento | Acción |
|----------|--------|
| **Input de código de barras** | `v-model="posLookupCode"`, `@input="handlePOSInput"`, Enter → `triggerPOSLookup()`. Acepta escáner y **entrada manual `*Nombre*Precio`** (ej. `*COCA 1.5L*1500`) |
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
| **Items por kilo (panadería)** | Además del toggle KILO/UNIDAD, muestra dos campos: **Peso** (kg, 3 decimales) e **Importe** ($, lo que realmente se cobra). El importe manda: `updateCartImporte()` recalcula el peso como `importe / precio_por_kilo` redondeado a 3 decimales, así no se pierden centavos por redondeo del peso. Al escribir el peso, el importe se deriva (`peso × precio/kg`) |

#### Venta por peso: importe en lugar de peso
*(productos `tipo_venta = kilo` o `ambos` con precio por kilo — panadería, fiambre, etc.)*

| Elemento | Comportamiento |
|----------|----------------|
| **Importe manda** | El subtotal de la línea es el importe tipeado, no `peso × precio` — el ticket cuadra al peso con lo que se cobró |
| **Backend** | `POST /api/ventas/{id}/items` acepta `importe`: si viene, el `subtotal` es ese importe exacto y el `peso` se recalcula (3 decimales). `precio_unitario` sigue siendo el precio de lista por kg, así el análisis por precio no se distorsiona |
| **API de ventas** | `_venta_to_dict` ahora devuelve `por_kilo` y `peso` en cada ítem (antes no venían) para poder analizar lo vendido por kg |
| **Ticket** | `TicketModal` muestra `peso kg` en la columna Cant y el subtotal real |

#### Resumen

| Elemento | Acción |
|----------|--------|
| **Subtotal** | Cálculo automático |
| **Input Descuento** | `v-model="cart.descuento"`, `@input="recalcCart"` |
| **Total** | Subtotal - descuento |
| **Medio de Pago** | Botones segmentados: Efectivo | Débito | Crédito | Transferencia | Cta.Cte. Atajos teclado: 1-5, flechas, Enter |
| **Select Cliente** | Dropdown de clientes + "Consumidor Final" |
| **Botón "Confirmar Venta"** | `confirmarVenta()` — flujo completo de confirmación |
| **Link "Vaciar carrito"** | `cerrarCarritoActual()` — vacía los items del carrito activo pero conserva su nombre |
| **Botón "Recarga"** | Header del POS — abre el modal de recarga de saldo (ver "Servicio de Recargas") |
| **Nombre del carrito** | Header de la columna del carrito. Clic para renombrar en el lugar (ej. "Mesa 2"). `empezarRenombre()` |
| **Panel de carritos** | Lista todos los carritos con items, total y antigüedad (dentro de la sesión de caja actual). `activarCarrito(id)` cambia de carrito sin perder el anterior. Se renderiza absoluto y **fuera** del `overflow-hidden` del card |
| **Botón cerrar carrito** | Por cada carrito con items: vacía ese carrito conservando el nombre. `cerrarCarrito(id)` |
| **Botón eliminar carrito** | Por cada carrito: lo borra (registra en auditoría local). No permite borrar el último. `eliminarCarrito(id)` |
| **Campo "nuevo carrito"** | Input + botón `+` para abrir un carrito con nombre. `crearCarrito()` |

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

### Flujo de Recarga (POS)

1. Botón "Recarga" en el header → `abrirModalRecarga()`
2. Se carga `GET /api/recargas/config` al montar el POS (monto base, adicional %, cuenta de salida, producto)
3. Elegir monto (input o atajos de $1.000 / $2.000 / $3.000 / $5.000 / $10.000)
4. Se muestra el desglose en vivo: cargado, adicional y total a cobrar
5. "Agregar al carrito" → una línea de venta con `cantidad` = unidades y `precio_unitario` = base + adicional
6. Se cobra como cualquier venta (efectivo / transferencia / etc.)
7. Al confirmar, el backend registra el egreso de caja por el monto cargado desde la cuenta digital

Si el producto de recarga no está configurado, el modal avisa y ofrece ir a Ajustes (solo admin / encargado).

### Carritos con nombre (mesas, mostrador, apartado)

El carrito **no pertenece a la pantalla del POS**: vive en un store de Pinia (`frontend/src/stores/carrito.js`) y se persiste en `localStorage('apex-pos-carritos')`. Hay varios carritos a la vez, cada uno con nombre, y uno de ellos es el activo.

Esto resuelve tres cosas que antes no funcionaban:

- **El carrito ya no se pierde al cambiar de tab.** Antes `cart` era un `reactive()` dentro de `POSView`, así que al ir a Productos Vue destruía el componente y el carrito con él. Ahora sobrevive al route change, y también a un F5.
- **Se pueden tener varios carritos abiertos.** "Mesa 1", "Mesa 2" y "Mostrador" no son una entidad nueva: son carritos con nombre.
- **Apartar y recuperar se subsumen.** Un carrito aparteado es un carrito con nombre. Ya no hace falta guardar y vaciar: se cambia de carrito y el anterior queda guardado solo.

Flujo:

1. El panel del header lista todos los carritos con items, total y antigüedad
2. Click en uno → `activarCarrito(id)` lo vuelve activo. No se pide confirmación porque nada se pierde: el que se deja queda guardado
3. Si hay una venta yendo al backend o un QR esperando confirmación, el cambio se bloquea con un aviso
4. El nombre del carrito activo se edita en el lugar, clic sobre el nombre
5. "Vaciar" / el check verde → `cerrarCarrito(id)` vacía los items pero **conserva el nombre**, que es lo que se quiere para una mesa que sigue abierta
6. La X → `eliminarCarrito(id)` borra el carrito. El último no se puede borrar: el POS siempre necesita uno
7. Todo queda en `localStorage('apex-pos-held-audit')` con los eventos `HOLD`, `RENAME`, `CLOSE`, `DELETE_HELD` y `RECALL`
8. Un carrito abierto hace más de 2h aparece en ámbar y se marca como sospechoso

Máximo 12 carritos simultáneos.

**Al editar una venta** que ya estaba cobrada, sus items se cargan en el carrito activo. Si ese carrito tenía algo sin cobrar, se aparta antes con el sufijo "(sin cobrar)" para no pisarlo.

**Al cerrar la caja**, `initCierreCaja()` en `CajaView` avisa cuántos carritos tienen productos sin cobrar, los lista con su total, y registra un evento `ORPHAN` por cada uno. Los carritos vacíos no cuentan: no son nada pendiente.

#### Cómo evita POSView reescribir sus ~100 referencias a `cart.`

`POSView` ya usaba `cart.items`, `cart.total`, `cart.subtotal`... en ~100 lugares. Para no reescribirlas todas, `cart` es un `Proxy` que resuelve cada acceso contra `carritoStore.activo` en el momento:

```js
const cart = new Proxy({}, {
  get: (_t, k) => carritoStore.activo[k],
  set: (_t, k, v) => { carritoStore.activo[k] = v; return true },
  // ...
})
```

Cambiar de carrito es cambiar `activoId`, y todas las referencias existentes ya ven el carrito nuevo.

#### Migración de los tickets apartados anteriores

Los tickets de la versión vieja (`localStorage('apex-pos-held')`) se importan **una sola vez** como carritos llamados "Apartado 1", "Apartado 2", etc. Se filtran los que no tienen items. Si no hay datos viejos, arranca limpio con un "Carrito 1" vacío.

El store normaliza lo que lee: un `items` que no es array, un `total` no numérico o un `activoId` colgado se corrigen en vez de romper el POS. Si el JSON está corrupto se descarta y arranca de cero.

### Flujo de Búsqueda por Texto + Creación Rápida

1. El buscador de texto tiene auto-focus al montar POS
2. Escribir nombre/marca/código → grilla filtra en vivo
3. Presionar Enter sin resultados → diálogo "Producto no registrado, ¿desea crearlo?"
4. Sí → abre QuickCreateModal con código pre-cargado (si el texto son 8+ dígitos)
5. En el modal: botón 🔍 busca en fuentes externas (deshabilita Nombre/Marca mientras busca)
6. Si código de barras vacío al guardar → se asigna un `GEN-XXXXXXXX` interno, derivado de la hora (`nextGenCode()`, no una secuencia: la grilla del POS viene filtrada y paginada y el número se repetía, chocando con el UNIQUE de `codigo_barras`)
7. Guardar → POST `/api/productos` → producto se agrega a la grilla local
8. No → cierra diálogo, focus vuelve al buscador

### Modal: Creación Rápida de Producto (QuickCreateModal)

| Campo | Tipo | Detalle |
|-------|------|---------|
| **Código de Barras** | Input + botón 🔍 suffix | `lookupBarcode()` — busca en fuentes externas. Si vacío al guardar, auto-asigna un `GEN-XXXXXXXX` (derivado de la hora, `nextGenCode()`) |
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
| Código de barras | Input text | Enter → `lookupBarcode()` busca en fuentes externas. **Al editar, el código de un producto existente no se modifica** (ni `*MANUAL*` ni `GEN-`): antes se regeneraba un `GEN-XXXX` con el número de la lista filtrada, que podía chocar con otro producto y dejar el guardado en 500. Si el campo llega vacío, el backend asigna un `MAN-XXXXXXXXXX` |
| Marca | Input text | — |
| Nombre | Input text | Requerido |
| Precio costo | Input number | — |
| Precio venta | Input number | — |
| Stock inicial | Input number | Solo en creación |
| Stock mínimo | Input number | 0 = alerta deshabilitada, con hint text |
| **Controlar stock** | BaseToggle | Desactivado en fraccionados: vender no descuenta lotes, no genera movimientos ni alertas (solo queda registrado lo vendido) |
| Categoría | BaseSelect + botón `+` | Quick-create inline: nombre + botón Crear |
| Proveedor | Combobox + botón `+` | Quick-create inline: nombre + CUIT |
| Fecha vencimiento | Input date | Opcional |

> `productos.codigo_barras` es NOT NULL y UNIQUE. POST/PUT de productos traducen un `IntegrityError` a un **409 con mensaje legible** ("Ya existe otro producto con el código …"), y `_generar_codigo_barras()` asigna un `MAN-…` cuando el campo viene vacío, para que nunca queden dos productos en blanco.
| Observaciones | Textarea | Opcional |
| **Botón "Guardar"** | Primary | `saveProduct()` |
| **Botón "Cancelar"** | Ghost | `closeModal()` |

#### Control de stock por producto (`controla_stock`)

*(productos fraccionados: panadería, fiambre, etc., donde el stock en kg se desincroniza solo)*

| Elemento | Comportamiento |
|----------|----------------|
| **Default** | `True` — todos los productos existentes siguen controlando stock tal cual |
| **Con control** | Comportamiento actual: FEFO sobre lotes, `MovimientoStock` de salida, `deficit_stock` / `flag_revision_stock` y alertas de stock bajo |
| **Sin control** | `confirmar_venta()` no descuenta lotes ni genera movimientos; `anular_venta()` no reingresa. Se siguen guardando `peso` y `subtotal` de la venta para el análisis |
| **Alertas** | Quedan fuera de `GET /api/productos/stock-bajo`, de los filtros "Stock bajo"/"Sin stock" de Productos y de la grilla del POS (muestran badge `s/ctrl`) |
| **Migración** | `ALTER TABLE productos ADD COLUMN controla_stock BOOLEAN NOT NULL DEFAULT 1` en `_migrate_new_columns()` (`app/main.py`) |

### Servicio de Recargas (SUBE, saldo, etc.)

*(cargar saldo a un cliente cobrando base + adicional, con el dinero saliendo de una cuenta digital)*

| Elemento | Comportamiento |
|----------|----------------|
| **Botón "Recarga"** | Header del POS. Abre el modal de recarga (solo visible si hay un producto de recarga configurado) |
| **Monto a cargar** | Input libre + atajos de $1.000 / $2.000 / $3.000 / $5.000 / $10.000. Solo múltiplos del monto base (por defecto $1.000) |
| **Desglose** | Muestra lo que se carga, el adicional y el total a cobrar en vivo |
| **Al confirmar la venta** | Se cobra el total (efectivo / transferencia / etc.) y sale un **egreso real de caja** por el monto cargado desde la cuenta digital configurada |
| **Ganancia** | El adicional. El costo del ítem se guarda como el monto cargado, así el Dashboard no cuenta los $1.000 cargados como ganancia |
| **Anulación** | Devuelve el dinero cargado a la cuenta digital (movimiento de ingreso compensatorio) y excluye la recarga del reporte |
| **Movimientos** | El egreso queda en el listado de movimientos de caja con `medio_pago` = cuenta de salida |
| **Cierre de caja** | Los egresos de la sesión se informan aparte por medio (no afectan el conteo físico de cada método) |
| **Dashboard** | KPI "Recargas Hoy" (cargado + ganancia) cuando hubo recargas en el día |
| **Reportes** | Card "Recargas de saldo": cargado, cobrado, ganancia y operaciones, por día y por medio de pago del cliente |
| **Semilla** | `_seed_producto_recarga()` crea el producto "Recarga SUBE" (`es_recarga=True`, sin stock) la primera vez que arranca |

**Ajustes → Servicio de Recargas** *(tarjeta colapsable en `/ajustes`)*

| Campo | Detalle |
|-------|---------|
| Monto base por unidad | Default `1000`. Solo se admiten múltiplos de este valor |
| Adicional (%) | Default `10`. El cliente paga `base × (1 + %)` por unidad ($1.100) |
| Cuenta de salida | De dónde sale el dinero para cargar: `smartpoint`, `mercadopago_qr`, `mercadopago_pos`, `qr_interop`, `debito`, `credito`, `transferencia`, `efectivo` |
| Producto que representa la recarga | Solo productos sin control de stock. Al elegirlo queda marcado `es_recarga=True` |

**Backend:**
- Tabla `recargas` (`app/models/recarga.py`): `venta_id`, `unidades`, `monto_cargado`, `adicional_monto`, `total_cobrado`, `medio_pago_cobro`, `medio_pago_carga`, `estado` (`confirmada` / `anulada`)
- `app/services/recarga_service.py`: config en la tabla `configuraciones`, `precio_unidad()`, `calcular()`, `registrar_venta_recarga()` y `anular_recargas()`
- Enganche en `confirmar_venta()` / `anular_venta()` (`app/services/venta_service.py`)
- `registrar_egreso()` ahora acepta `medio_pago`; `obtener_resumen_por_medio_pago()` devuelve `egresos_por_medio`
- **Endpoints:** `GET /api/recargas/config` (cualquier usuario autenticado, lo usa el POS), `PUT /api/recargas/config` (admin / encargado), `GET /api/recargas/calculo?unidades=` (desglose)
- **Migración:** `ALTER TABLE productos ADD COLUMN es_recarga BOOLEAN NOT NULL DEFAULT 0` en `_migrate_new_columns()` (`app/main.py`)

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
| **Botón "Abrir Caja"** | `abrirCaja()` — precarga el último cierre y abre el modal de apertura, POST `/api/caja/apertura` |
| **Botón "Cerrar Caja"** | `initCierreCaja()` — verifica los carritos con productos sin cobrar, luego abre modal de arqueo |

### Modal: Apertura de Caja
*(visible al hacer "Abrir Caja")*

| Elemento | Descripción |
|----------|-------------|
| **Último cierre detectado** | Banner con monto del último cierre + badge si fue automático |
| **Monto inicial sugerido** | Input numérico precargado con el último cierre (`GET /api/caja/saldos-cuentas-sugeridos`). Junto al hint tiene el botón "Contar billetes" |
| **Saldos iniciales de cuentas digitales** | Una fila por cuenta digital (SmartPoint, MercadoPago QR, MercadoPago POS, QR Interoperable) precargada con el último saldo real de esa cuenta. Se envía en `saldos_cuentas` del POST de apertura; los montos en 0 se descartan |
| **Retiro de efectivo (opcional)** | Monto que se aparta al abrir + motivo. Se registra como egreso del cajón |
| **Monto final de apertura** | `monto_inicial - monto_retiro` (reactivo) — es el valor enviado a la API |
| **Aviso "falta saldo inicial"** | Si una cuenta digital tuvo movimientos pero se abrió sin saldo inicial, la Arqueo la marca con warning: sin ese dato el saldo absoluto de la cuenta no es verificable |
| **Botones** | Cancelar / Abrir Caja (`confirmarAperturaCaja()`) |

Cada apertura de cuenta digital se persiste como movimiento `tipo="apertura"` con `medio_pago` = cuenta, `referencia_tipo="apertura_cuenta"` y `referencia_id` = id de la apertura del cajón. No genera una sesión de caja nueva ni altera la lectura del efectivo.

### Resumen

| KPI | Descripción |
|-----|-------------|
| **Cajón** | `saldo_efectivo`: balance de efectivo desde la última apertura |
| **Cuentas digitales** | `saldo_cuenta_total`: suma de los saldos de las cuentas digitales |
| **Total** | `saldo_total` = Cajón + Cuentas digitales. Es el total bajo control del turno |
| **Ingresos del Día** | Suma de ingresos |
| **Egresos del Día** | Suma de egresos (de todos los medios; el detalle por medio sale del arqueo) |

### Arqueo por Medio de Pago
*(componente `ArqueoMedios.vue`, se usa en el cierre de la caja abierta y en la conciliación de una sesión ya cerrada)*

| Columna | Descripción |
|---------|-------------|
| **Método** | Efectivo \| Débito \| Crédito \| Transferencia + las cuentas digitales con movimiento o saldo inicial |
| **Saldo inicial** | Aporte de apertura de ese medio (solo cuentas digitales; el efectivo toma la apertura del cajón) |
| **Ingresos** | Ingresos del medio |
| **Egresos** | Egresos del medio |
| **Esperado** | `apertura + ingresos - egresos` |
| **Monto Real** | Input por medio; en efectivo abre "Contar billetes" |

### Extracción de Efectivo al Cerrar
*(bloque al pie del arqueo, tanto en el cierre de la caja abierta como en la conciliación de una sesión cerrada)*

| Elemento | Descripción |
|----------|-------------|
| **Monto a extraer + Motivo** | Input del monto que sale del cajón y su motivo (opcional) |
| **Botón "Registrar extracción"** | `POST /api/caja/retiro-cierre` — el monto queda como egreso de la sesión y se descuenta del efectivo esperado |
| **Lista de extracciones** | Cada extracción registrada con su monto y motivo, y un botón para deshacerla (`DELETE /api/caja/retiro-cierre/{id}`) |
| **"Queda en el cajón"** | Muestra el efectivo esperado una vez descontadas las extracciones |

- La extracción **neutraliza** la diferencia, no la crea: si el cajón esperaba $30.000 y extraés $25.000, el arqueo espera $5.000 y el operador cuenta $5.000. Por eso la cuenta digital sigue cuadrando con lo que muestra la app
- Queda registrado como `MovimientoCaja` tipo `egreso` con `referencia_tipo="retiro_cierre"`, así que aparece en el detalle de la sesión
- Con `cierre_id` pertenece a esa sesión (y recalcula el monto esperado del cierre); sin `cierre_id` es de la sesión abierta
- Las extracciones de sesiones ya cerradas no cuentan en el saldo de la caja abierta, y las de la sesión abierta no cuentan en el arqueo de una sesión cerrada

### Modal: Conteo de Billetes (Efectivo)
*(componente `ContadorBilletesModal.vue`, se abre desde Apertura y desde el Arqueo)*

| Elemento | Descripción |
|----------|-------------|
| **Columna Billetes** | Denominaciones de tipo `billete` habilitadas en Ajustes (por defecto $100.000 / $50.000 / $20.000 / $10.000 / $5.000 / $2.000 / $1.000) con input de cantidad y subtotal |
| **Columna Monedas** | Denominaciones de tipo `moneda` habilitadas en Ajustes (por defecto $500 / $200 / $100 / $50 / $20 / $10 / $5 / $1) con input de cantidad y subtotal |
| **Total contado** | Auto-suma de todos los subtotales + piezas, total de billetes y total de monedas |
| **Botón "Limpiar"** | Vacía todas las cantidades |
| **Botón "Usar $X"** | Escribe el total en el campo de monto del modal padre y lo cierra (deshabilitado si el total es 0) |
| **Precarga** | Al abrir, descompone greedy el monto ya cargado en el campo destino para partir de una base |
| **Aviso de cobertura** | Si las denominaciones habilitadas no cubren el monto completo, avisa cuánto quedó sin asignar para corregir a mano |

- La suma se aplica al monto real del **efectivo** solamente; débito, crédito y transferencia siguen con carga manual
- `Esc` cierra solo el modal de conteo (no el modal padre)
- Al abrir carga `GET /api/denominaciones`; si falla la API o no hay ninguna habilitada, usa la lista por defecto de Argentina

### Ajustes: Denominaciones de Efectivo
*(tarjeta colapsable en `/ajustes`, define las denominaciones del contador de caja)*

| Elemento | Descripción |
|----------|-------------|
| **Fila por denominación** | Input numérico de valor, select Billete/Moneda, toggle Habilitada/Deshabilitada y botón para quitarla |
| **Botón "Agregar denominación"** | Agrega una fila nueva al final (hereda el tipo de la anterior) |
| **Botón "Restaurar por defecto"** | `POST /api/denominaciones/restaurar-defaults` — vuelve a la lista estándar de Argentina (con confirmación) |
| **Botón "Guardar"** | Valida (valor > 0, sin duplicados) y persiste: borra las quitadas, actualiza las existentes y crea las nuevas |

- **Backend:** tabla `denominaciones` (`valor` único, `tipo`, `activo`) + `app/services/denominacion_service.py` con defaults AR
- **Endpoints:** `GET /api/denominaciones?incluir_inactivas=` (cualquier usuario autenticado, lo usa el contador), `POST` / `PUT /{id}` / `DELETE /{id}` / `POST /restaurar-defaults` (solo `admin`)
- **Siembra:** `_seed_denominaciones()` en `app/main.py` crea la tabla y la lista por defecto la primera vez que arranca
- Las deshabilitadas quedan guardadas pero **no aparecen** en el contador de caja

### Ajustes: Servicio de Recargas
*(tarjeta colapsable en `/ajustes`, define el servicio de carga de saldo — ver "Servicio de Recargas" en Productos)*

| Elemento | Descripción |
|----------|-------------|
| **Monto base por unidad** | Input numérico (default `1000`). Solo se admiten recargas múltiplo de este valor |
| **Adicional (%)** | Input numérico (default `10`). Debajo muestra el precio de venta calculado por unidad ($1.100) |
| **Cuenta de salida** | Select con `smartpoint`, `mercadopago_qr`, `mercadopago_pos`, `qr_interop`, `debito`, `credito`, `transferencia`, `efectivo` |
| **Producto de la recarga** | Select de productos sin control de stock. Al guardarlo se marca `es_recarga=True` |
| **Botón "Guardar"** | `saveRecargas()` → `PUT /api/recargas/config` (admin o encargado) |

- **Backend:** `app/services/recarga_service.py` (config en la tabla `configuraciones`, claves `recarga_*`) + `app/routers/recargas.py`
- **Endpoints:** `GET /api/recargas/config` (cualquier usuario autenticado), `PUT /api/recargas/config` (admin / encargado), `GET /api/recargas/calculo?unidades=`
- **Siembra:** `_seed_producto_recarga()` en `app/main.py` crea el producto "Recarga SUBE" si todavía no hay ningún producto de recarga
- Si el producto no está configurado, el POS muestra un aviso con acceso directo a esta tarjeta (solo para admin / encargado)

### Modal: Cierre de Caja (Arqueo)
*(visible al hacer "Cerrar Caja")*

| Elemento | Descripción |
|----------|-------------|
| **Métodos de pago** | `ArqueoMedios.vue` con: Esperado (calculado), Monto Real (input), Diferencia (color verde/rojo). En **Efectivo** el label "Monto Real Contado" lleva el botón "Contar billetes" |
| **Botón "Contar billetes"** | Solo en Efectivo — abre el modal de conteo por denominación y escribe la auto-suma en el Monto Real |
| **Extracción de efectivo** | Ver "Extracción de Efectivo al Cerrar" |
| **Comentario general** | Campo opcional para nota al cierre |
| **Egresos de la sesión** | Bloque rojo (solo si hay egresos con medio definido) con el detalle por medio y el total. No forman parte del conteo físico de cada método |
| **Alerta tickets apartados** | Si hay carritos con productos sin cobrar: confirmación antes de continuar |
| **Botón "Confirmar Cierre"** | `confirmarCierreCaja()` — cierra cada medio (POST `/api/caja/cierre-metodo`) + cierre-total + logout automático |
| **Botón "Cancelar"** | `cancelarCierreCaja()` — avisa que la extracción registrada queda como egreso y cierra el modal |

Cada medio se concilia por separado: se registra un `cierre_parcial` con `medio_pago`, `monto_esperado`, `monto_confirmado` y la diferencia. El cierre total usa `saldo_total` (cajón + cuentas digitales).

### Conciliación de Sesión (cierre diferido)
*(modal `Conciliar sesión de caja`, desde el botón ✓ del Historial de Caja o de "Detalle del día" en una sesión con cierre automático)*

| Elemento | Descripción |
|----------|-------------|
| **Datos de la sesión** | Apertura, cierre, extracciones y saldo esperado de esa jornada |
| **Arqueo por medio** | `ArqueoMedios.vue` con las filas ya cargadas: lo que ya se contó queda precargado y editable, lo que falta arranca vacío |
| **Total esperado / real / diferencia** | Resumen de la conciliación |
| **Botón "Conciliar sesión"** | `conciliarSesion()` — arquea cada medio con monto cargado (POST `/api/caja/cierre/{id}/metodo`) y confirma (PUT `/api/caja/cierre/{id}/confirmar`) |
| **Botón "Cerrar"** | Cierra el modal sin conciliar; el arqueo queda como estaba |

- Solo aplica a sesiones con **cierre automático** y sin monto confirmado. Una vez conciliada queda inmutable: ni arqueos ni extracciones pueden tocarla
- Se puede conciliar **aunque haya otra caja abierta**: el arqueo se acota entre la apertura y el cierre de esa sesión y no toma los movimientos de la caja nueva
- Exige contar todos los medios con saldo esperado (`medios_pendientes`); si alguno quedó con diferencia pide confirmación
- Los movimientos que se registran para la sesión (arqueo, extracción) se guardan con el `id` del cierre como referencia, así que quedan fuera del rango de la sesión pero el arqueo los sigue contando

### Movimientos del Día

| Columna | Descripción |
|---------|-------------|
| Fecha | Timestamp del movimiento |
| Tipo | Apertura / Apertura de cuenta / Ingreso / Egreso / Cierre |
| Monto | Formateado $ |
| Método | Efectivo / Débito / Crédito / Transferencia / cuenta digital |
| Comentario | Descripción |

| Elemento | Acción |
|----------|--------|
| **Botón "Nuevo Movimiento"** | `showNuevoMovimiento = true` — abre modal (solo si caja abierta) |

### Modal: Nuevo Movimiento

| Campo | Acción |
|-------|--------|
| Tipo | Ingreso / Egreso |
| Monto | Input number |
| Método de Pago | Select (incluye las cuentas digitales) |
| Comentario | Input text |
| **Botón "Registrar"** | `registrarMovimiento()` |
| **Botón "Cancelar"** | `showNuevoMovimiento = false` |

### Flujo de Cierre de Caja
1. "Cerrar Caja" → `initCierreCaja()` → GET `/api/caja/resumen` → obtiene desglose por método
2. Si hay carritos con productos sin cobrar → confirmación listándolos, y evento `ORPHAN` por cada uno
3. Modal muestra montos esperados vs reales por método de pago
4. Cajero ingresa monto real contado en cada método
5. Diferencia se calcula y muestra en verde (sobrante) o rojo (faltante)
6. Si deja plata en el cajón o la lleva a la caja fuerte → la registra como extracción (queda como egreso y baja el esperado del efectivo)
7. "Confirmar Cierre" → POST `/api/caja/cierre-metodo` por cada método + POST `/api/caja/cierre-total`
8. Logout automático → redirige a `/login`

### API Calls
- `GET /api/caja/movimientos` — listar movimientos
- `GET /api/caja/resumen` — resumen por medio (`por_medio` con apertura/ingresos/egresos/esperado por método, más `saldo_efectivo`, `saldo_cuenta_total`, `saldo_total`, `retiros` y `total_retiros` de la sesión abierta)
- `GET /api/caja/estado` — estado actual (cajón y cuentas por separado)
- `GET /api/caja/saldos-cuentas-sugeridos` — últimos saldos reales por cuenta digital para precargar la apertura
- `POST /api/caja/apertura` — abrir caja (cajón + `saldos_cuentas`)
- `POST /api/caja/cierre-total` — cerrar caja + logout automático
- `POST /api/caja/cierre-metodo` — cerrar un medio con monto real y comentario
- `POST /api/caja/retiro-cierre` — registrar extracción de efectivo (`monto`, `motivo`, `cierre_id` opcional)
- `DELETE /api/caja/retiro-cierre/{id}` — dar de baja una extracción mal cargada
- `GET /api/caja/cierre/{cierre_id}/arqueo` — arqueo de una sesión (admin/encargado)
- `POST /api/caja/cierre/{cierre_id}/metodo` — arquear un medio de una sesión ya cerrada (admin/cajero)
- `PUT /api/caja/cierre/{cierre_id}/confirmar` — conciliar la sesión con el monto real total
- `POST /api/caja/ingreso` — ingreso manual
- `POST /api/caja/egreso` — egreso manual

### Cuentas Digitales vs Cajón
- Las cuentas digitales son `smartpoint`, `mercadopago_qr`, `mercadopago_pos` y `qr_interop`. Se configuran en Ajustes.
- Cada cuenta mantiene su propio saldo: apertura + ingresos - egresos.
- Un egreso de cuenta (ej. una recarga de SUBE) **nunca** descuenta el efectivo del cajón.
- `saldo_actual` conserva el nombre histórico pero representa solo el cajón; para el total usar `saldo_total`.
- Sin apertura de la cuenta, el arqueo marca `falta_saldo_inicial` para ese medio.

### Apertura: Cuánto Sugerir
- El monto sugerido es el **efectivo** del último cierre (`saldo_efectivo`), no el total: el total del cierre suma las cuentas digitales, que van por su cuenta
- `MovimientoCaja.saldo_efectivo` guarda el cajón del cierre; los cierres manuales también lo llenan

### Auto-cierre por Cambio de Día
- En `caja_service.caja_abierta()` compara fecha de apertura vs fecha actual
- Si es otro día, crea automáticamente `MovimientoCaja` tipo "cierre" y retorna `False`
- Previene vender con caja del día anterior
- Ese cierre **se puede completar después** desde el Historial: arqueo por medio, extracción y conciliación. Ver "Conciliación de Sesión"

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

## 11. Precios Online

**Ruta:** `/precios-online` — **Componente:** `PreciosOnlineView.vue` — **Roles:** admin, encargado, repositor

Compara el precio de un producto en comercios online contra el precio de venta propio, para decidir si conviene comprar en esa fuente.

### Encabezado

| Elemento | Acción |
|----------|--------|
| **Input "Código de barras"** | `v-model="barcodeInput"`, Enter → `buscarPrecios()` |
| **Botón "Stock Bajo"** | `toggleStockBajo()` — variant dinámico: `primary` si el panel está abierto, `secondary` si está cerrado |
| **Botón "Buscar"** | `buscarPrecios()` — bloqueado mientras `loading` (guard de reentrada) |
| **Hint de espera** | Visible solo durante la búsqueda: "Consultando las fuentes online. Puede tardar unos segundos." |

### Flujo de búsqueda

Tres pasos **independientes**: un error en uno no cancela los otros.

1. `POST /api/productos/lookup { barcode }` — busca en BD local, luego catálogo central, luego fuentes externas
   - Si devuelve `id` → se pide `GET /api/productos/{id}/info-detallada` y se arma la card del producto local
   - Si responde **404** → no es un error: se marca `noEstaEnLocal` y la búsqueda sigue
2. `GET /api/productos/precios-online/{barcode}` — precios de las 4 fuentes, ordenados de menor a mayor
3. Si no hay producto local **ni** resultados → `toast.info` de que no se encontró en ninguna fuente

### KPIs de decisión de compra

Se muestran solo cuando el producto está en el catálogo local **y** hay resultados online.

| KPI | Cálculo |
|-----|---------|
| **Precio de venta local** | `productoInfo.precio_local` |
| **Mejor precio online** | Primer resultado tras ordenar por precio ascendente |
| **Ganancia por unidad** | `precio_local - mejor_precio`. Ícono `arrow-trend-up` en verde si es positiva, `arrow-trend-down` en ámbar si el local está más barato que el online |

### Card: Producto Local

| Elemento | Comportamiento |
|----------|----------------|
| Nombre + marca | Del `info-detallada` |
| Badges | Precio local, costo, stock (`success` / `danger`) |
| Última compra | Fecha con `formatDateShort` + número de orden |
| Chips de proveedores | `es_principal` → badge "Principal". Click → `verProductosProveedor(prov)` abre el modal con los productos del proveedor |
| Botón "No está en tu catálogo" | Solo si `noEstaEnLocal`: avisa que se puede crear desde Productos |

### Card: Precios Online

Resultados ordenados de menor a mayor. La fila más barata se resalta con fondo `emerald-50/50` + badge "Más barato" + precio en verde.

| Elemento | Comportamiento |
|----------|----------------|
| **Badge de fuente** | `variant` según fuente: Carrefour `info`, Vea `danger`, Mas Online `success`, Super Coco `brand`. Fuente desconocida → `default` + ícono `fa-globe` |
| **Precio** | `resultado.precio` (el campo que devuelve `comparar_precios`, no `precio_referencia`) |
| **Diferencia vs precio local** | `diferencia_vs_local` con el signo invertido según convenga: verde si comprar online deja margen, rojo si el local ya es más barato |
| **Oferta** | `descuento.activo` + `precio_oferta` → precio tachado; `descuento.promocion` → badge ámbar con el texto de la promoción |
| **Botón "Ver en {fuente}"** | `window.open(url, '_blank', 'noopener,noreferrer')` |
| **Imagen** | `imagen_url` cuando la fuente la expone; si no, ícono de tienda |

### Panel: Stock Bajo

| Elemento | Comportamiento |
|----------|----------------|
| **Header** | Cantidad de productos + botón de recarga (solo si hay resultados) |
| **Carga** | Skeletons (`BaseSkeleton`), 4 filas |
| **Vacío** | Ícono de check verde: "Todos los productos tienen stock suficiente" |
| **Fila** | Imagen, nombre, marca, código, badge `stock/min` (`danger` si 0, `warning` si bajo) y precio local. Click → `buscarDesdeStockBajo(producto)` |

### Modal: Productos del Proveedor

| Elemento | Comportamiento |
|----------|----------------|
| **Título** | `Productos de {nombre}` |
| **Carga** | Skeletons, 5 filas |
| **Vacío** | "Este proveedor no tiene productos asociados" |
| **Fila** | Imagen, nombre, marca, código, precio y stock. Click → `buscarDesdeProveedor(producto)`: setea el código, cierra el modal y relanza la búsqueda |
| **Stock** | Viene de `_suma_lotes_activos()`, igual que el resto del sistema |

### Reglas

- El estado vacío inicial (`EmptyState`) solo aparece si no hubo búsqueda alguna: `!loading && !productoInfo && !resultados.length && !noEstaEnLocal`
- Un 404 en el lookup **nunca** se muestra como error, solo como aviso informativo
- Todos los errores van por `toast.error(e?.data?.detail || e.message || fallback)` — el wrapper `api.js` ya deja el `detail` del backend en `Error.message`
- Se ignora cualquier resultado sin precio numérico antes de ordenar

### API
- `POST /api/productos/lookup` — producto local / catálogo central / fuentes externas
- `GET /api/productos/precios-online/{barcode}` — precios por fuente, ordenados de menor a mayor, con `diferencia_vs_local` y `porcentaje_vs_local` si el producto está en el catálogo local
- `GET /api/productos/{id}/info-detallada` — producto + proveedores + última compra
- `GET /api/productos/stock-bajo` — productos con stock <= mínimo o sin stock
- `GET /api/proveedores/{id}/productos` — productos asociados a un proveedor

### Scraping: caché y timeout

`app/services/lookup_service.py` cachea por `(fuente, barcode)` porque una sola búsqueda dispara varias rondas de scraping (`/lookup` compara precios por dentro y la vista llama además a `/precios-online`).

| Aspecto | Valor |
|---------|-------|
| **Cache de aciertos** | `SCRAPER_CACHE_TTL` = 900 s (15 min) |
| **Cache de fracasos** | 120 s — evita que un timeout de red quede cacheado como "no encontrado" por 15 minutos |
| **Timeout** | `settings.SCRAPER_TIMEOUT` = 20 s (antes hardcodeado en cada scraper: 15 y 20) |
| **Límite de entradas** | 500, con purga de vencidas al exceder |
| **Scraping simultáneo** | `SCRAPER_MAX_CONCURRENT` = 8, por `threading.Semaphore` |
| **Single-flight** | Lock por `(fuente, barcode)`: N requests del mismo código a la vez → 1 solo scrape, los demás esperan y leen la caché |

**Por qué `/lookup` NO está gateado por rol:** lo llaman `POSView`, `ComprasView`, `CobroMovilView` y `ProductsView`, y las ventas son `require_role("admin", "cajero")`. Gatequearlo sin cajero rompe el POS. Como el sistema solo tiene 4 roles, un `require_role` con los 4 sería idéntico a `get_current_user`. La protección contra abusar del scraping va por el semáforo y el single-flight, no por roles.

`GET /precios-online/{barcode}` sí está gateado a `admin, encargado, repositor`, que son exactamente los roles de la tab en `TheSidebar` y en el `meta` del router.

`comparar_precios` devuelve por fuente: `fuente`, `nombre_fuente`, `experimental`, `precio`, `nombre`, `marca`, `imagen_url`, `url`, `descuento`.

### Por qué los headers no piden brotli

`Accept-Encoding` es `gzip, deflate` y **no** `br`, a propósito. `brotli` no viene instalado, y si el servidor responde igual con `Content-Encoding: br`, `requests` **no lo descomprime y no tira error**: devuelve los bytes comprimidos y los trata como si fueran el HTML. El parseo falla después con un error que no menciona el Encoding, que es la peor forma de fallar porque esconde la causa.

Lo detectó `comerciante.carrefour.com.ar`, que responde con `br`. Ese sitio no se puede usar como fuente (abajo), pero el bug era general: cualquier sitio que decidiera responder brotli nos devolvía basura en silencio.

Supercoco usa un dict de headers propio con solo el User-Agent, así que nunca pidió brotli. `test_scrapers_fetch.py::TestHeadersDeRed` cubre las dos rutas.

### `comerciante.carrefour.com.ar` (Maxi Pedido) — no se puede usar como fuente

Existe y es un sitio distinto del de consumo, con precios por volumen. El listado se puede leer por API (`GET /products?method=productsList&currentUrl=...`) y trae EAN, nombre y sector, así que la parte de catálogo funciona.

**Pero los precios están detrás de un login.** En los 12 productos que devuelve la búsqueda el atributo viene literalmente como `data-price="private"`, y la página de producto no tiene precio alguno. El sitio lo dice en pantalla: *"Te pedimos por favor que ingreses tus datos para poder ver el precio y stock disponible."*

No es un obstáculo a sortear con otra consulta: es el propósito del sitio, un portal B2B con acceso por cuenta. Agregarlo exigiría una cuenta de comercio mayorista y guardar credenciales, que es otra decisión y otra responsabilidad, y no algo que se pueda resolver desde acá.

Aparte: el EAN buscado (`7790895001000`) no existe. La búsqueda lo resuelve por近似 a `7790895000997` (Coca regular 2.25 L), que sí existe.

### Fuentes: registro, nombre canónico y apagado

`FUENTES` dejó de ser una lista y es un dict con los datos de cada fuente:

```python
FUENTES = {
    "carrefour": {"nombre": "Carrefour", "experimental": False},
    "vea": {"nombre": "Vea", "experimental": False},
    "masonline": {"nombre": "MasOnline", "experimental": False},
    "supercoco": {"nombre": "Supercoco (experimental)", "experimental": True},
}
```

**El nombre vive en el backend y viaja en `nombre_fuente`.** Antes el nombre estaba duplicado en `PreciosOnlineView.vue` y el PDF hacia `str(fuente).upper()`, o sea "SUPERcoco". Con el registro, pantalla y PDF muestran lo mismo y no hay dos listas que desincronicen. El frontend conserva su mapa local solo para el color y el icono, que son cosas de presentacion.

**Supercoco está activa y marcada experimental.** La página de búsqueda renderiza por JavaScript: devuelve el mismo HTML (~393 KB) para cualquier consulta, sin los productos adentro, así que el parser nunca va a matchear nada. Se verificó contra el sitio en vivo. No se apagó porque apagarla esconde el síntoma en vez de documentarlo; el nombre y el aviso en pantalla dicen que ese precio no es confiable. La API estilo VTEX devuelve 404 y el documento no trae `__PRELOADED` / `__NEXT_DATA__` / `__NUXT__`, así que arreglarlo pide ver la llamada real desde el navegador.

| Config | Efecto |
|--------|--------|
| `SCRAPER_FUENTES_OFF` | Lista de fuentes a no consultar, separada por coma: `SCRAPER_FUENTES_OFF=supercoco,carrefour` |

`fuentes_activas()` filtra por esa variable, así que apagar una fuente que rompió no obliga a tocar código ni a redeploy. Tolera espacios y mayúsculas, e ignora nombres que no existen. `lookup_producto(barcode, fuente=...)` con fuente explícita **no** se filtra: es un pedido directo, no un barrido.

### Tests de scraping

`lookup_service.py` separa **fetch** de **parse** para que el parseo sea testeable sin red:

| Capa | Funcion | Que hace |
|------|---------|----------|
| Fetch | `_lookup_supercoco`, `_lookup_carrefour_api`, `_scrape_fuente` | `requests.get` + manejo de errores, devuelve HTML/JSON crudo |
| Parse | `_parse_supercoco`, `_parse_carrefour`, `_parse_vea` | Texto/JSON a dict de producto. Sin red |
| Auxiliar | `_scan_json_object` / `_parse_balanced_object` | Extrae el objeto JSON tras un marcador, contando llaves **ignorando las que estan dentro de strings** |

#### La promo se lee del JSON-LD, no del estado de VTEX

Vea y MasOnline emiten **dos bloques ld+json del mismo producto**, y cada uno tiene un precio distinto:

| Bloque | Campo | Qué es |
|--------|-------|--------|
| primero (sin `id`) | `offers.lowPrice` | Precio **de lista**, o sea **sin promo** |
| `id="structured-data-schema"` | `offers.price` | Lo que se paga por unidad **con la promo ya aplicada** |
| | `priceSpecification.price` | El precio de lista, en `priceType: ListPrice` |
| | `priceValidUntil` | Cuándo deja de estar la oferta |

Leer el primero da el precio sin descuento. Por eso `_extract_json_ld` no devuelve "el primer bloque que parsea": puntúa cada bloque y gana el mejor (`_puntaje_json_ld`, con +10 para `structured-data-schema` y +5 por traer `price` explícito). El orden en la página no importa, y hay test de las dos variantes.

Ejemplo real (Coca Cola Zero 2,25 L): `offers.price = 3926.67` y `priceSpecification.price = 5890`. $5.890 × 2/3 = $3.926,67, o sea una **3x2**. La etiqueta sale del ratio exacto (`_etiqueta_multi_compra`): 2x1, 3x2 y 4x3. Un descuento común como 5890 → 5000 no matchea ninguna proporción y queda sin etiqueta, que es lo correcto.

**Un descuento sin los dos precios no se marca como descuento.** El fallback cuando la página no trae JSON-LD devuelve `activo: False` con el nombre de la promo: sin los dos números no se puede calcular el ahorro, y un badge de oferta sin precio hace dudar del resto de los datos. También `_find_promotion_code` barre el estado entero, así que puede(New) agarrar un banner general del sitio ("3x2 en Hamburguesas") que no es de este producto y que además puede estar vencido.

#### En MasOnline las promos no están en ningún lado del HTML

Vea y MasOnline son del mismo grupo, pero la promo se implementa distinto:

| | Dónde está la promo | Precio de referencia |
|---|---|---|
| **Vea** | JSON-LD, ya descontado | 3926.67 (el de oferta) |
| **MasOnline** | Solo en la simulación de carrito | 3932.86 (recién comprando 3) |

En MasOnline el precio se arma por JS (`priceBehavior: "async"`), el HTML no lo renderiza y en el estado el offer llega con `teasers: []` y `discountHighlights: []` vacíos, con `price == priceWithoutDiscount`. No hay nada que parsear. La única fuente es `GET /api/checkout/pub/orderForms/simulation`, que devuelve el precio **por unidad con la promo ya aplicada** según la cantidad:

| cantidad | unidad | total | pagás |
|---|---|---|---|
| 1 | 5899.00 | 5899.00 | 1 |
| 2 | 5899.00 | 11798.00 | 2 |
| **3** | **3932.86** | 11798.58 | 2 |
| 4 | 5899.00 | 23596.00 | 4 |
| **6** | **3932.86** | 23597.16 | 4 |

Tres cosas que salen de esa tabla:

- **El precio de una unidad no baja.** 3932.86 es lo que se paga comprando 3. Por eso la respuesta lleva `cantidad_minima` y la card y el PDF lo dicen, sin eso un 3x2 se lee como una bajada de precio que no existe para quien compra una.
- **El precio se usa el que devuelve la simulación, no una cuenta.** `lista * 2/3` da 3932.67 y VTEX devuelve 3932.86. Calcularlo muestra un precio que el cliente nunca va a ver.
- **La promo es por bloques de 3.** A cantidad 4 y 5 no hay descuento (quirón de VTEX), y a 6 vuelve. `cantidad_minima` es 3, que es lo que importa para comprar.

**Cómo se decide si vale la pena preguntar.** La simulación va a un endpoint de carrito de terceros, así que no se llama para todo. Solo si:

1. el producto no tiene ya un descuento del JSON-LD, y
2. está en un cluster con un multi-compra **explícito** (`3x2- Bebidas`, `Hasta 2x1`, no `Oferta` ni `- OP`).

El filtro importa mucho: `3x2- Bebidas` cuelga de casi todas las bebidas, pero fuera de bebidas casi ningún producto lo cuelga. Medido sobre 5 productos de cada categoría: bebidas 7/8 pasan el filtro, limpieza 0/5, panadería 0/5, alimentos 0/5. Es decir, el gasto extra se concentra justo donde están las promos. Un filtro más laxo (cualquier palabra tipo "Oferta" u "OP") no filtraba nada: recall 2/2 pero precisión 2/8.

Con eso una comparación de 8 bebidas hizo **14 requests al carrito** (2 por producto que pasa el filtro, cortando antes si la promo ya aparece en la primera consulta).

**Carrefour quedó afuera:** el mismo producto no tiene descuento por cantidad ni a 1 ni a 3, así que la simulación no aporta nada ahí.

**Limitación conocida:** solo se simulan cantidades 2 y 3, así que un `6x5` se escapa. Son promos raras y cada cantidad probada es un request a un endpoint de carrito; si alguna vez aparecen, el lugar para sumarlas es `_CANTIDADES_MASCULINAS`.

**Correr los tests**

```
python -m pip install -r requirements-dev.txt
python -m pytest
```

`pytest.ini` fija `testpaths = tests`. `conftest.py` setea `DATABASE_URL` a una BD temporal antes de importar la app (porque `database.py` llama `verificar_db()` a nivel de modulo) y define un fixture autouse `sin_red` que **bloquea cualquier socket**: ningun test puede pegarle a Carrefour/Vea reales, porque serian lentos, flaky y quemarian el rate limit de las fuentes a las que les scrapeas todos los dias.

| Archivo | Cubre |
|---------|-------|
| `test_scrapers.py` | Parseo de las 4 fuentes contra fixtures, orden, ofertas, categoria |
| `test_scrapers_fetch.py` | Cableado fetch -> parse con `requests.get` simulado, timeouts, errores de red, flujo de 1 y 2 pasos |
| `test_scrapers_limites.py` | Casos que rompian en silencio: llaves en strings, `})` dentro de un string, categorias como dicts, precios no numericos |
| `test_lookup_cache.py` | TTL positivo/negativo, purga, cache por fuente+barcode, orden de `comparar_precios` |
| `test_analisis_precios.py` | Historial de compras: orden, exclusion de anuladas/pendientes, ultimo costo, mejor historico con proveedor y fecha |
| `test_analisis_precios_pdf.py` | La ficha PDF renderiza con y sin datos; escapa `&`/`<`/`>`;aguanta precios grandes y fechas invalidas |
| `test_fuentes_registro.py` | Nombre canonico de cada fuente, flag experimental, y que una fuente apagada por config no genere ni un request |
| `test_vea_promos.py` | Que se elija el bloque ld+json con precio de oferta y no el de lista, con una **pagina real** en `fixtures/vea_promo_real.html` |
| `test_masonline_promos.py` | Filtro de clusters, `priceToken`, y la promo por cantidad contra la simulacion de carrito, con la **pagina real** en `fixtures/masonline_promo_real.html` |

Las fixtures viven en `tests/fixtures/` y son HTML/JSON **guardados a mano**, con trampas incluidas a proposito (una descripcion con `{}` adentro, un `})` dentro de un string).

**Cuando cambia el markup de una fuente:** el symptom es que `comparar_precios` devuelve `[]` y la pantalla dice "no lo encontramos", indistinguible de "no esta en esa tienda". Para diagnosticarlo, se reemplaza la fixture por el HTML real que devuelve la fuente y se corre el test: el nombre del test que falla dice que campo se rompio.

### Análisis de Compra

`/precios-online` decia "aca esta mas barato", pero no contestaba la pregunta que importa al comprar: **¿cuanto pago yo la ultima vez, a quien, y cuando fue que mas barato?** Ese analisis vive en `app/services/analisis_precios_service.py` y se muestra en una card abajo de la ficha del producto.

**No hay tabla nueva.** Todo sale de datos que el sistema ya tiene:

| Dato | Origen |
|------|--------|
| Que se pago, cuando y a quien | `compras` + `compra_items` + `proveedores` |
| Costo de lista actual por proveedor | `producto_proveedor.costo` |

| Endpoint | Que hace |
|----------|----------|
| `GET /api/productos/{id}/analisis-precios` | Historial, costo por proveedor, online, ahorro, margen |
| `GET /api/productos/{id}/analisis-precios/pdf` | Ficha A4 horizontal para imprimir o compartir |

Ambos estan gateados a `admin, encargado, repositor` y comparten `_analisis_por_id()`, asi que el PDF nunca puede decir algo distinto a lo que muestra la pantalla.

**Las compras anuladas quedan fuera.** `ESTADOS_VALIDOS = ("recibida", "parcial")`: una compra cancelada figuraria como "el precio mas bajo que jamais conseguiste", que es exactamente el error que hace desconfiar de la pantalla. Por el mismo motivo se ignoran las `pendiente` (todavia no se pago nada).

En la pantalla: la columna mas barata de la tabla de proveedores queda resaltada en verde, y la compra con menor precio unitario en ambar. `ahorro_vs_mejor_historico` compara el precio online de hoy contra el mejor pago historico, no contra el ultimo: comparar contra el ultimo compra "contra vos mismo" y siempre sale que conviene comprar online.

La ficha PDF (`app/services/analisis_precios_pdf.py`, ReportLab) es landscape porque en vertical la tabla de historial no entra sin partirse en 3 paginas. Empieza con una frase de recomendacion ("tu proveedor habitual sigue mejor...") porque es lo primero que se lee al recibirla por mail.

---

## 12. Calendario

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

## 13. Reportes

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

#### Vendido por Peso

*(productos fraccionados: panadería, fiambre, etc. — análisis de kg e importe)*

| Elemento | Descripción |
|----------|-------------|
| **Rango de fechas** | Inputs `desde` / `hasta` (por defecto, últimos 30 días) + botón "Calcular" → `loadVendidoPorPeso()` |
| **KPIs** | Total vendido ($), kilos vendidos, operaciones y cantidad de productos del período |
| **Tabla** | Por producto: kilos totales (con rango min–max), precio promedio por kg, operaciones e importe |
| **Pie de tabla** | Totales del período |
| **Carga** | `onMounted` y `syncAll()` también refrescan este reporte |
| **Solo ventas confirmadas** | Las ventas anuladas y las pendientes quedan fuera del cálculo |

#### Recargas de saldo

*(carga de saldo SUBE y similares — cuánto se cargó, cuánto se cobró y la ganancia)*

| Elemento | Descripción |
|----------|-------------|
| **Rango de fechas** | Inputs `desde` / `hasta` (por defecto, últimos 30 días) + botón "Calcular" → `loadRecargas()` |
| **KPIs** | Cargado ($), cobrado ($), ganancia = adicional y cantidad de operaciones |
| **Tabla por día** | Fecha, cargado, cobrado y ganancia |
| **Tabla por medio de pago** | Medio con el que pagó el cliente: operaciones, cargado y cobrado |
| **Solo recargas confirmadas** | Las anuladas quedan fuera del cálculo |
| **Carga** | `onMounted` también refresca este reporte |

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
- `GET /api/reportes/vendido-por-peso?desde=YYYY-MM-DD&hasta=YYYY-MM-DD&producto_id=` — kg e importe por producto (`router: reportes.py`, cualquier usuario autenticado). Solo ítems con `por_kilo = true` de ventas confirmadas
- `GET /api/reportes/recargas?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` — recargas de saldo por día y por medio de pago (`router: reportes.py`)
- `GET /api/caja/reportes?desde=YYYY-MM-DD&hasta=YYYY-MM-DD` — sesiones agrupadas (apertura → cierre) por día. Cada sesión expone `apertura` (cajón) y `apertura_cuentas` (suma de los saldos iniciales de las cuentas digitales del turno). Las aperturas de cuenta no generan sesiones propias

---

## 14. Usuarios

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

## 15. Licencias

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

## 16. Auditoría

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

## 17. Backups

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

## 18. Elementos Globales

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

## 19. Flujos Funcionales Críticos

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
  ├─ Sugiere el efectivo del último cierre (saldo_efectivo)
  ├─ Opcional: retiro al abrir + saldos iniciales de cuentas digitales
  └─ POST /api/caja/apertura → caja abierta

[OPERAR DÍA]
Cada venta confirmada → MovimientoCaja ingreso
Puede haber ingresos/egresos manuales

[CIERRE TOTAL]
"Cerrar Caja" → initCierreCaja() → GET /api/caja/resumen
  ├─ Modal muestra montos esperados vs reales por método
  ├─ Cajero ingresa monto real de cada medio
  ├─ Extracción de efectivo (opcional) → POST /api/caja/retiro-cierre
  │    └─ Baja el esperado del cajón; queda como egreso de la sesión
  └─ "Confirmar Cierre" → POST /api/caja/cierre-metodo (por medio)
  └─ POST /api/caja/cierre-total → logout automático → /login

[CIERRE AUTOMÁTICO]
Al iniciar día siguiente: `caja_abierta()` detecta cambio de fecha
  └─ Crea cierre automático → obliga a nueva apertura
  └─ Después se completa desde el Historial ("Conciliar sesión"):
       GET /api/caja/cierre/{id}/arqueo →Extacción (POST retiro-cierre)
       → arqueo por medio (POST /cierre/{id}/metodo)
       → PUT /cierre/{id}/confirmar
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

### Flujo 8: Carritos con Nombre (mesas y apartado)
```
[ABRIR UN CARRITO]
Cajero → POS → panel de carritos → input "+"
  ├─ crearCarrito(nombre): agrega el carrito y lo deja activo
  ├─ Persiste en localStorage('apex-pos-carritos')
  └─ Registra auditoría local: evento 'HOLD'

[CAMBIAR DE CARRITO]
Click en un carrito del panel → activarCarrito(id):
  ├─ Cambia carritoStore.activoId
  ├─ NO se pide confirmación: el carrito que se deja queda guardado solo
  ├─ Se bloquea si hay venta en curso o QR esperando confirmación
  └─ Registra auditoría local: evento 'RECALL'

[RENOMBRAR]
Clic sobre el nombre del carrito activo:
  ├─ Se edita en el lugar, Enter o blur confirma, Esc cancela
  └─ Registra auditoría local: evento 'RENAME'

[VACIAR UN CARRITO]
Botón "Vaciar" o el check verde del panel → cerrarCarrito(id):
  ├─ Vacía items, subtotal, total, descuento, recibido, cliente
  ├─ CONSERVA el nombre (la mesa sigue abierta)
  └─ Registra auditoría local: evento 'CLOSE'

[ELIMINAR UN CARRITO]
Botón X del panel → eliminarCarrito(id):
  ├─ Lo borra del array y de localStorage
  ├─ Si era el activo, pasa al siguiente
  ├─ El último carrito no se puede borrar
  └─ Registra auditoría local: evento 'DELETE_HELD'

[ORPHAN — CIERRE DE CAJA]
Si hay carritos con productos sin cobrar al cerrar caja (initCierreCaja en CajaView):
  ├─ Confirmación listando nombre, items y total de cada uno
  ├─ Registra auditoría local: evento 'ORPHAN' por cada carrito
  └─ Los carritos vacíos no cuentan

[SOSPECHOSOS]
Carritos con items y más de 2h de antigüedad:
  ├─ Banner ámbar en POS: "X carrito(s) abierto(s) hace más de 2 horas"
  ├─ El panel los resalta con borde ámbar
  └─ No se eliminan automáticamente, requieren acción manual
```

### Flujo 9: Creación Rápida de Producto desde Búsqueda POS
```
[BUSCAR SIN RESULTADOS]
Cajero escribe en buscador de texto → Enter
  └─ filteredPOSProducts está vacío → diálogo "Producto no registrado, ¿desea crearlo?"
      ├─ Sí (Enter) → abre QuickCreateModal
      │   ├─ Si texto son 8+ dígitos → pre-carga como código de barras
      │   ├─ Si vacío → auto-asigna un GEN-XXXXXXXX (derivado de la hora, `nextGenCode()`)
      │   ├─ Botón 🔍 → POST /api/productos/lookup → deshabilita Nombre/Marca
      │   ├─ Guardar → POST /api/productos → agrega a grilla local
      │   └─ Cierra modal, focus a grilla
      └─ No (Esc) → cierra diálogo, focus al buscador
```

---

## 20. Reglas de Negocio

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
16. **Carritos sin respaldo en servidor**: Viven en localStorage. Si se borra el localStorage del navegador, se pierden. No sobreviven cambiar de terminal.
17. **Sospechosos**: Carritos con items y más de 2h de antigüedad se consideran sospechosos (posible fraude) y se destacan visualmente.
18. **Huérfanos**: Al cerrar caja, cada carrito con productos sin cobrar genera un evento `ORPHAN` en la auditoría local.
19. **Auto-generación de código de barras**: Si se deja vacío al crear producto, se asigna un `GEN-XXXXXXXX` derivado de la hora (`nextGenCode()`). No es una secuencia sobre la grilla: al venir filtrada y paginada se repetía y el UNIQUE de `codigo_barras` rechazaba el alta, dejando la venta sin crear el producto.
20. **Editar venta con carrito ocupado**: Cargar una venta para editar crea un carrito "(sin cobrar)" con lo que hubiera, para no pisarlo.

---

## 21. Atajos de Teclado

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
