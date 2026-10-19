# Pendientes — ApexERP

> Estado actual del proyecto. **Actualizar al final de cada sesión relevante** (en el commit que cierra la jornada o cuando arranca la siguiente).

---

## 📍 Roadmap: convergencia híbrida mobile

Estrategia: **responsive en las vistas existentes + pantallas dedicadas solo para flujos lineales del piso** (la convención ya existe: `/cobrar`, `/cargar-mercaderia`, `/control-stock` con `meta.bare`). Breakpoint único `md` (768px), CSS para layout y JS solo para features (cámara, sonidos).

### Fase 0 — Hecha ✅
- Shell responsive: sidebar → drawer + bottom-nav (`e2d8c54`)
- Pantallas dedicadas arregladas: escáner, cargar mercadería con `guardar()` real, control stock (`45e8107`)
- PWA base: manifest con shortcuts a Cobrar/Stock, viewport, theme-color

### Fase 1 — Componentes base (mayor ROI: beneficia 12 vistas de una) ✅
- [x] **`BaseTable` con modo cards en <sm**: lista de tarjetas (`sm:hidden`) + tabla (`hidden sm:block`); respeta los slots por columna, `row-click`, `detail`, skeletons y empty state; convenión: primera columna = título de la tarjeta (`primary: true` para elegir otra), `mobile: false` oculta columnas secundarias en la card. Lo usan: Products, Ventas, Clientes, Proveedores, Compras, Caja, Calendario, Usuarios, Auditoría, Licencias, Backups, EtiquetasPrecios
- [x] **`BaseModal` mobile**: `max-h` con `100dvh` (no `100vh` — el URL bar de iOS se comía el footer), paddings compactos `p-4 sm:p-6`
- [x] **Inputs**: `text-[16px] md:text-sm` en BaseInput/BaseSelect (evita el zoom automático de iOS al enfocar), targets ≥44px en BaseButton md/lg e iconOnly md/lg

### Fase 2 — Piso de venta (uso diario del personal)
- [ ] ProductsView — consulta de precios/stock (ya tiene 12 `sm:`, pass corto)
- [ ] POSView — verificar en touch: cantidades, cobro, medios de pago
- [ ] CajaView — apertura/arqueo del cajero en el celular
- [ ] VentasView — historial + detalle de ticket
- [ ] ClientesView

### Fase 3 — Gestión (admin/encargado, uso ocasional)
- [ ] Prioridad real: ReportesView, ComprasView, ProveedoresView, FacturacionView (el dueño las usa fuera del escritorio)
- [ ] Después: DashboardView (ya casi), CalendarioView, PreciosOnlineView, EtiquetasPreciosView, AjustesView, UsuariosView, AuditoriaView, LicenciasView, BackupsView — mínimo: que no se rompan

### Fase 4 — PWA / offline
- [x] Registrar el service worker (se registra en `index.html`: `navigator.serviceWorker.register('/app/sw.js')`) y cachear el app shell — endurecido el 13/10/2026 (network-first shell + versión por deploy, ver sección de fix arriba)
- [x] **Catálogo local para el POS** (nivel 1, 15/10/2026): `GET /api/catalogo/local` + snapshot con fecha en `localStorage` + antigüedad en el aviso. Ver "Nivel 1 del offline del POS" en Completados
- [x] **Eficiencia para que desconectar salga barato** (fase D, 16/10/2026): versión chiquita del catálogo, subida de ventas al abrir CobroMóvil, aviso con monto y poll de caja pausado sin red. Ver "Fase D — eficientizar" en Completados
- [x] **Ciclo completo sin red** (fase E, 16/10/2026): la caja recuerda su estado sin conexión, abrir y cerrar se encolan, y ventas + caja suben juntas **en el orden en que pasaron** y sin duplicar nada. Ver "Fase E — abrir, cobrar y cerrar sin red" en Completados
- [x] **Refresco automático de la pantalla** (16/10/2026): un solo timer de 60 s compartido por POS, CobroMóvil y Caja — sube lo pendiente, refresca la caja y cada 5 min pregunta si cambió el catálogo. CobroMóvil (el celular del cajero) no refrescaba nada
- [x] Extender el patrón de ventas pendientes del POS (`addPendingSale`) a CobroMovil (hecho antes del nivel 1: `crearVenta()` distingue error HTTP de corte de red)
- [ ] Prompt suave de "Agregar a pantalla de inicio"

### Fase 5 — Polish de dispositivo real
- [ ] safe-area en header, `overscroll-behavior`, quirks de teclado virtual
- [ ] Test en mano: iOS Safari + Android Chrome (escáner con BarcodeDetector, `100dvh`, impressión de tickets)

### Definición de done por vista
Usable con el pulgar en 360×740, targets ≥44px, inputs sin zoom, modales full-screen, tablas en cards, y la suite backend en verde si hay contract tests que la parseen.

**Siguiente acción:** Fase 1 arrancando por `BaseTable` (el mayor ROI del plan).

---

## ✅ Completados recientemente

### Fase E — abrir, cobrar y cerrar sin red — 16/10/2026

Con la Fase D la pantalla ya dejaba de morir al desconectar y las ventas ya se encolaban. Lo que faltaba era **el día entero sin conexión**: la caja se abría, se cobraba… y a la hora de cerrar no había forma. Cuatro piezas, todas en el navegador (el backend no cambió):

- **La caja recuerda su estado.** `stores/caja.js` guarda el último estado que pudo ver (`apex-caja-estado`) y lo restaura apenas se arma el store. Sin esto, refrescar la página sin internet mostraba **"CAJA CERRADA"** y el POS/CobroMóvil no dejaba cobrar aunque la caja estuviera abierta en el negocio — era la pieza que hacía imposible el día sin conexión. **Se restaura solo si es del mismo día**: el servidor da por cerrada una apertura de ayer (cambio de día), y restaurarla abierta dejaría el POS cobrando contra una sesión que ya no existe
- **Una sola cola para abrir y cerrar** (`composables/useOfflineCaja.js`, `postear()`): si la red no contesta, la operación queda anotada **y se aplica en el navegador al momento** (la caja queda abierta/cerrada como quedó en el negocio). Si el servidor la rechaza (400/403), el error se propaga y se ve: eso no es "sin conexión". **Solo se encolan tres operaciones** — apertura, arqueo por método y cierre total — porque son las únicas que se pueden **reconciliar contra el estado real**. Ingresos, egresos y extracciones no se encolan: no hay forma de saber si ya se registraron, y **duplicar plata es peor que mostrar el error**
- **Un solo punto de subida** (`composables/useOfflineSync.js`): las ventas y las operaciones de caja se mezclan y se suben **en el orden en que pasaron**, no en dos tandas sueltas. La venta necesita la caja abierta y el cierre necesita las ventas adentro: subirlas por separado dejaba o la venta sin caja, o el cierre sin la venta. Si se corta la red a mitad, **se deja de subir todo** (lo que sigue tampoco entraría, y seguir intentando son pantallas de 30 s); si el servidor rechaza algo puntual, ese queda encolado y se sigue. Al terminar refresca la caja. `syncPendingSales()` dejó de existir: era un segundo punto de subida y en algún caso no iba a respetar el orden
- **No se hace nunca dos veces.** Antes de reintentar se le pregunta al servidor en qué está la caja y se decide: apertura con la caja ya abierta → ya estaba hecha; cierre con la caja ya cerrada → ya estaba hecha; arqueo de un medio ya arqueado → ya estaba hecho. Esa reconciliación existe porque el servidor **no** es idempotente: `abrir_caja()` tira *"Ya hay una caja abierta"* y `cerrar_todo()` *"No hay caja abierta"*, que es un error distinto de "ya estaba hecho" (hay tests que fijan los dos mensajes). Y el estado no se mira una sola vez sino que **va evolucionando**: si se mirara siempre el estado inicial, una cola con apertura y cierre saltaría el cierre ("la caja ya está cerrada") y la jornada quedaría abierta para siempre
- **Se ve.** `OfflineIndicator` ahora cuenta también los movimientos de caja sin subir y los muestra en las tres ramas del aviso; `CajaView` sube lo encolado **antes** de pedir el historial (sino la pantalla mostraba los movimientos sin las aperturas y cierres que faltaban)
- **Pulido posterior al probarlo (16/10/2026): un solo refresco automático.** El dueño probó la venta sin conexión y anduvo, pero notó que **nada se actualizaba solo**. Estaba desparejo: `CajaView` y `POSView` refrescaban la caja cada 60 s con **cada una su timer armado a mano**, y `CobroMovilView` —la pantalla que más mira el cajero en el celular— **no refrescaba nada**: lo único que se actualizaba era lo que se tocaba. Ahora hay un `composables/useRefrescoPeriodico.js` que comparten las tres y que por tick: **(1)** sube lo que quedó sin conexión (si no hay nada pendiente **no hace ni un request**, así que el 99 % de los ticks sale gratis — y es el respaldo del evento `online`, que algunos navegadores no disparan bien con el hotspot), **(2)** refresca el estado de la caja, **(3)** cada 5 ticks pregunta si cambió el catálogo (~100 bytes) y solo baja si cambió. Con la red caída no se reintenta nada (son hasta 30 s de espera cada 60 s): se pausa sola y se reanuda con el evento `online` o cuando alguien pide el estado a mano
- **Prueba 2 del dueño (19/10/2026) — dos bugs y los dos arreglados:**
  1. **Con la caja abierta, refrescar sin internet mostraba "CAJA CERRADA".** Causa: el service worker tenía cacheado el estado de la caja y, sin red, le devolvía la respuesta de **antes de abrir**; `fetchEstado` la tomaba como verdad, **pisaba el estado local** (que sí sabía que la caja se había abierto sin conexión), la volvía a guardar y hasta reactivaba el refresco. Arreglado sacando ese endpoint de la caché del SW —el estado vive en `apex-caja-estado`, que además tiene la fecha— y haciendo que la restauración caiga a `guardadoEn` si la hora del servidor no se puede leer, en vez de quedarse sin caja en silencio
  2. **Desde el celular se cerraba/abría la caja casi sin confirmar nada**: era un `confirm()` de un toque en el chip del header, sin ningún dato. Ahora cerrar abre un modal con **efectivo en cajón, total y desde cuándo está abierta** + botón rojo explícito ("Sí, cerrar la caja"); abrir sigue pidiendo el monto inicial en su modal
- **Tests:** `tests/test_fase_e.py` (30) + `tests/test_refresco_periodico.py` (9) y ajustes en `tests/test_fase_d.py` por el cambio de nombre del punto de subida. Suite: **890 passed**

### Fase D — eficientizar: que desconectar salga barato — 16/10/2026

El negocio trabaja casi siempre con internet por **hotspot limitado**, tiene **un día sin internet**, y el dueño quiere que **si él se va el negocio siga andando** sin que el cajero esté "recargando todo el tiempo". La eficiencia acá no es un fin en sí misma: es lo que hace que desconectar sea un **no-evento** y no un "modo" aparte con sus bugs. Cuatro cosas:

- **Refrescar ya no cuesta bajar el catálogo entero.** Nuevo `GET /api/catalogo/version` (~100 bytes, `catalogo_local.version_local`): cuenta de productos/categorías/ofertas + `max(updated_at)` + **el total de unidades de los lotes**. Ese último es la red de seguridad: una venta mueve un lote **sin tocar `productos.updated_at`**, así que mirando solo productos la versión diría "no cambió nada" y el POS se quedaría con un stock que ya no existe (el error feo, porque no se nota hasta que alguien se queda sin mercadería). `stores/productos.js` ahora: si **no hay señal, no se intenta nada**; si hay, pregunta la versión y **solo baja si cambió** (1 request en vez de 3); si no pudo confirmar, **baja igual** — ante la duda se refresca, nunca se queda viejo por ahorrar bytes. El snapshot guardado lleva su `version` **calculada antes de listar**: si se calculara después, un cambio que llegara mientras se armaba quedaría registrado como "ya está al día" y no se volvería a bajar nunca (hay test que lo vigila con `monkeypatch`). `Categoria` no tiene `updated_at` (solo `created_at`), así que su firma mira las categorías enteras —son 10 y cambian poco—: cualquier alta, baja o renombre se detecta sin hacer una migración
- **El celular sube las ventas al abrir.** `CobroMóvilView` no llamaba `syncPendingSales()`: solo se sincronizaba con el evento `online`, que dispara **solo si antes estuvo desconectado** — quien llega a su casa con el wifi ya encendido no subía nada y la plata quedaba quieta hasta apretar "Sincronizar ahora". Ahora se sube al montar; si no hay pendientes **no hace ni un request**, así que cuesta cero
- **Se ve cuánto hay en juego.** "3 ventas sin subir" no decía si eran $3.000 o $300.000. `useOfflineSales` exporta `totalDeVenta()` (guarda el `total` al encolar y recalcula el de las colas viejas desde los items, menos descuento) y `OfflineIndicator` muestra **"$X sin subir"** en las tres ramas del aviso
- **El poll de caja se pausa cuando la red falló.** `stores/caja.js` marca `sinRed` solo ante **error de red** (un 401 o 500 no significa que no haya red) y expone `refrescarPeriodicamente()`, que es lo que ahora llaman los timers de 60 s de `POSView` y `CajaView`. `fetchEstado()` **a mano sigue pidiendo siempre** — es lo que hace que entrar a una pantalla nunca quede con datos viejos por un corte que ya se superó, y un pedido que sale bien reabilita el poll. El evento `online` también lo reanuda
- **Bonus encontrado al revisar CobroMóvil**: `POST /api/catalogo/descargar` exige `admin`/`encargado`, y CobroMóvil lo llamaba **en cada apertura** sin el rate limit de 1 h que sí tenían `App.vue` y `POSView` — o sea un **403 silencioso para todo cajero**, y como estaba **dentro del `await Promise.all`**, frenaba el momento en que el cajero ve los productos. Ahora es una función aparte con el mismo rate limit de 1 h, solo para quien puede pedirlo, y fuera del await
- **Tests:** `tests/test_fase_d.py` (15) + `tests/test_catalogo_local.py` (30, con la nueva clase `TestVersion`). Suite: **851 passed**

### Nivel 1 del offline del POS: catálogo guardado en el navegador — 15/10/2026

Hasta hoy, cuando se cortaba la internet el navegador se quedaba **sin catálogo**: el service worker cacheaba `/api/productos` solo si esa URL exacta se había pedido antes, y **sin fecha**, así que no había forma de saber si los precios que se estaban cobrando eran los de hoy o de hace dos meses. Entrar sin red ya funcionaba (Fase C2), pero no había con qué vender. Esto es el **nivel 1** del offline completo.

- **Nuevo `GET /api/catalogo/local`**: productos + categorías + ofertas en **una sola respuesta con una sola fecha** (`generado`). Reutiliza los mismos serializadores que los endpoints normales (`producto_service.listar_productos`, `_oferta_to_dict`, `CategoriaOut`), así que **lo que se ve offline es idéntico a lo que se ve online**: si no lo fuera, el catálogo offline sería una segunda verdad que eventualmente contradice a la primera — y a diferencia de un error de precio a la vista, esa contradicción se descubre cobrando mal. Mismos roles que `/api/productos`. Con los 567 productos activos de hoy pesa ~0,4 MB
- **El stock sale de los lotes, no de la columna**: `listar_productos` recalcula `stock_actual` como suma de lotes activos, así que el snapshot no arrastra la columna desfasada (169 de 549 productos la tienen desfasada en producción, ver pendiente de `productos.stock_actual`)
- **`stores/productos.js` persiste y restaura**: el catálogo se guarda en `localStorage` (`apex-catalogo-local`) después de cada carga exitosa, y se restaura (a) apenas se arma el store — para que el POS no arranque con la grilla vacía mientras llegan los datos — y (b) cuando no llegan productos. Si el navegador no deja guardar (cota llena, pestaña privada) no explota: se sigue con lo que hay en memoria. `fetchAll` sigue tolerando que fallen las otras dos llamadas por separado, como antes
- **El aviso superior muestra la antigüedad**: "Modo offline — trabajando con los datos de la última sesión. **Catálogo de hace 3 h**" y, si hay red pero no se pudo actualizar, "No se pudo actualizar el catálogo — se vende con los datos de hace 40 min". Ese es el dato que importa sin red: si el precio que se cobra es el de hoy o el de ayer
- **Tests:** `tests/test_catalogo_local.py` (18), incluidos los de "offline igual que online" que comparan el snapshot carácter por carácter con la salida real de los endpoints normales. Suite: **824 passed**

### Fase C4 de la ronda de 19 bugs: permisos — una sola lista de quién puede qué — 15/10/2026
El **18**. El problema no era "falta una pantalla de permisos": era que la lista de **quién puede qué estaba escrita a mano en tres sitios distintos** —los `require_role(...)` de cada router, los `meta.roles` del router del frontend y el `allowed()` del sidebar— y **ya habían divergido en 14 puntos concretos**:

- el **repositor** ve "Cargar Mercadería" y el backend le devuelve 403 al confirmar
- el **cajero** abre la pantalla de Caja, pero los reportes de caja lo rechazan
- el **sidebar** trataba a un usuario sin datos cargados como **`admin`** y le mostraba todo el menú de administración
- el **encargado** ve el POS en todos lados, pero `POST /api/ventas` es solo admin/cajero

**Lo que quedó:**

**1. Una sola tabla** — `app/auth/permisos.py`, con los 4 roles, las 7 áreas del sistema y los permisos especiales. De ahí sale todo: ya no hay tres listas que se puedan desincronizar.

**2. `GET /api/permisos`** (solo el dueño) devuelve la matriz completa. La pestaña de Usuarios tiene el botón **"Qué puede hacer cada rol"**, que la muestra en modo lectura: área, acción y un ✓ por rol. Las acciones que además se le pueden dar a una persona puntual llevan una llavecita ámbar.

**3. Permisos especiales por persona** — 4 pases sueltos, con checkbox en el modal de "Nuevo/Editar usuario" y con badge en la columna **"Permisos extra"** de la tabla:
- `ver_reportes` → ver la pantalla de Reportes
- `gestionar_clientes` → dar de alta y editar clientes (ver la lista puede cualquiera, porque el POS la necesita para cobrar)
- `ver_caja` → ver el calendario, el día y los movimientos de caja
- `anular_ventas` → anular una venta cobrada

**4. `require_role` acepta permisos** — `require_role("admin", "encargado", permiso="ver_reportes")` deja pasar al rol **o** a quien tenga el pase. El **dueño (admin) siempre entra**, así que no existe forma de que se quede afuera de su propio sistema por un detalle de carga.

**5. Arreglos que salieron del mapeo:**
- el **fallback `'admin'`** del sidebar y del bottom nav pasó a **`'repositor'`** (el rol con menos derechos); antes, mientras el store se hidrataba, se veía todo el menú de administración
- `Usuario.permisos` es una columna nueva (`TEXT NOT NULL DEFAULT '[]'`) con su migración en `_migrate_new_columns`; las filas viejas quedan sin permisos extra, o sea el comportamiento exacto de antes
- un permiso viejo que ya no exista **no cuelga**: se ignora. Y si el dueño manda uno inventado, el backend responde 400 con su nombre
- los permisos se **validan en backend** al crear y al editar

**Ojo con esto:** para que el checkbox signifique algo, 2 endpoints de Reportes y el de anular ventas pasaron de "cualquiera autenticado" a "admin, encargado o el permiso". En la práctica **no cambia para nadie** que hoy lo usaba: esas pantallas ya estaban restringidas en el frontend, así que un cajero o un repositor nunca las vieron.

**Tests:** `tests/test_permisos.py` (29). Suite: **806 passed**

### Fase C2 de la ronda de 19 bugs: modo offline que no corta el trabajo — 15/10/2026
El **19**. La app ya era PWA (service worker cacheando el shell), ya tenía la cola de ventas pendientes y el indicador de "sin conexión" — pero **el arranque la tiraba al piso cada vez que se cortaba el internet**. Los 4 bloqueos:

- **`checkLicense()` sin red** fallaba y la pantalla de login se volvía la de **activación de licencia**, como si el comercio no tuviera licencia
- **`checkAutoLogin()` sin red** fallaba y hacía `clearToken()`: te borraba la sesión. **Cada corte de internet desloguaba a todos**
- **`api.js` no distinguía** "se cortó la red" de "sesión vencida": el `TypeError` de `fetch` salía crudo y sin status, así que no se podía decidir nada en función del motivo
- **`navigator.onLine`** solo sabe si hay tarjeta de red: con el wifi levantado y sin internet no aparecía ningún aviso

**Qué quedó:**
- `api.js` envuelve los errores de red con `status: 0` y exporta `esErrorDeRed()`. Un 401 real sigue echando al usuario igual: eso sí es sesión vencida de verdad
- **Última licencia y última sesión guardadas en `localStorage`** (`apex-licencia-cache`, `apex-sesion-offline`). Si el fallo es de red, se entra con eso y se sigue trabajando con lo cacheado. `logout()` borra la sesión cacheada, porque cerrar sesión es una decisión y no se debe poder volver a entrar a la fuerza
- Sin tarjeta de red no se esperan los 30 s del timeout: se va directo al caché
- **"Modo offline — trabajando con los datos de la última sesión"** en el indicador superior, que ahora también mira `auth.offline` y no solo `navigator.onLine`. Las ventas pendientes se siguen avisando
- Al volver la internet (`window online`), `auth.revalidar()` vuelve a preguntar licencia y token: sale el modo offline y se ve si algo cambió mientras estuvimos caídos
- La pantalla de login avisa que **sin el servidor no se puede confirmar la clave**, en vez de fallar recién al clickear
- **A propósito NO se cacheó `/api/auth/me` ni `/api/licencia/estado` en el service worker**: cachear autenticación hace que la app diga "estás adentro" con datos viejos y sin forma de enterarse de que el servidor ya no lo acepta. La caché vive en `localStorage`, es explícita y solo se usa cuando el fallo es de red
- **Tests:** `tests/test_modo_offline.py` (12). Suite: **777 passed**

### Fase C1 de la ronda de 19 bugs: lo que se le compró a cada proveedor — 15/10/2026
La Fase C traía 4 ítems (15, 16, 18, 19) y se dividió en **C1 = 15**, **C2 = 19 (offline)**, **C4 = 18 (permisos)**. El **16 —beneficio de compra del empleado— quedó pendiente** a pedido del dueño (ver "Pendientes activos").

**15 · Proveedores → ver lo que se le compró**
- Botón 🧺 **"Ver compras"** en cada fila de `ProveedoresView.vue`: abre un modal con **compras realizadas · total comprado · última compra**, la tabla **Fecha · OC · Producto · Cant. · $ Unit. · Subtotal** (la lista aplanada de los ítems de cada orden, de más reciente a más vieja) y el bloque **"Comentarios del proveedor"** con las notas de cada OC, con fecha y autor
- **Sin endpoint nuevo**: todo sale de `GET /api/compras?proveedor_id=`, que ya devolvía items y notas
- Las órdenes **anuladas** no se listan ni suman (queda un aviso con cuántas hay); sus comentarios sí aparecen, marcados como anulados, porque lo que avisó el vendedor sirve aunque después se haya anulado

**3 arreglos que salieron del mapeo**
- **Editar un usuario sin tocar la contraseña fallaba** con 422 y la vista decía "no se pudo guardar" sin motivo: el form manda `password: ""` y el backend exigía 4 caracteres. Ahora clave vacía (o de solo espacios) = "no cambiarla", y la vista solo la manda si se escribió una nueva
- **El toggle activar/desactivar ignoraba el body** que mandaba la vista y simplemente negaba el estado actual: dos clicks rápidos sobre la misma fila terminaban dejando al usuario como estaba. `PATCH /api/usuarios/{id}/toggle` ahora respeta `{activo: ...}` (y si no viene nada, invierte)
- **"Desactivar" en la pestaña de licencias no hacía nada**: llamaba a `PATCH /api/licencia/{id}/toggle`, que **no existía** (estaba documentado en `MAESTRO.md` igual). Se creó el endpoint, y además **no se puede apagar la única licencia vigente de esta máquina**: el login arranca pidiendo licencia válida, así que se quedaría todo el mundo afuera y sin nadie para reactivarla. Una licencia vencida o de otra máquina se puede apagar sin problema
- **Tests:** `tests/test_correcciones_admin.py` (15). Suite: **765 passed**

### Ronda de 19 bugs — Fase A (rápidos) + Fase B (caja/POS) — 15/10/2026
El dueño mandó 19 arreglos y mejoras. Se trabajaron en dos fases y **ambas quedaron cerradas**. Queda abierta la **Fase C (15, 16, 18, 19): hay que sentarse a decidir el diseño antes de tocar código**.

**Fase A — rápidos (6, 7, 10, 11, 12, 13, 14, 17)**

- **6 y 7 · Sidebar:** "Cargar Mercadería" y "Sectores" se mudaron de Gestión a la sección **Vista Móvil**, que es donde viven realmente las pantallas de piso
- **10 · Fecha de los movimientos:** la tabla "Movimientos del Día" mostraba el ISO crudo de la DB en UTC (`2026-10-14T15:32:00Z`). Pasa por `formatFechaHora` (hora Argentina)
- **11 · "Hoy" en el Calendario:** `/dia` comparaba contra la fecha UTC, así que a las 20:00 AR "hoy" seguía siendo ayer y el día se veía vacío. `_OFFSET_LOCAL = +3h` aplicado en **las dos ramas** del endpoint y `formatDate` con `toLocaleDateString('sv')` para que el input reciba `yyyy-mm-dd`
- **12 · "Productos modificados":** el candidato era cualquier `updated_at` movido (también lo que mueve el stock al vender) y la columna de *qué cambió* leía `code`, un campo que el backend no manda, así que salía siempre vacía. Ahora se cruza con la **auditoría** (`producto_actualizado` / `producto_desactivado`): entra si hubo edición real o si no se vendió en el período, se explica con `cambio` y los productos desactivados también cuentan
- **13 · Sectores en Compras:** `fetchSectores()` no se llamaba en `onMounted`, así que los select de sector de cada item arrancaban vacíos
- **14 · Alta rápida de proveedor:** pedía CUIT en un campo de celular. `newProvCelular` reemplaza a `newProvCuit` y guarda `telefono`
- **17 · Desactivar usuarios:** se podía dejar al **admin** (o a uno mismo) sin acceso. `_validar_desactivacion` lo prohíbe, existe `PATCH /{id}/toggle`, la fila mapea `role/active/lastAccess`, el rol se pinta en minúsculas y la acción desaparece sobre el admin protegido

**Fase B — caja y POS (1, 2, 3, 4, 5, 8, 9)**

- **1, 2, 3 · Un solo modal de apertura (`components/caja/AperturaCajaModal.vue`):** el POS tenía su propio modal, desactualizado (sugiere `ultimoCierre.monto`, que **incluye** las cuentas digitales que no están en el cajón, y no tiene "Contar billetes"). Ahora es el mismo componente en Caja y en POS. El aviso aclara que el último cierre es **solo el efectivo del cajón**, y el sugerido usa `saldo_efectivo`. El flujo quedó en lo que el dueño lo pensó: **"Conté en el cajón"** → **"Dejo en caja (fondo)"** → **"Te llevás (retiro)"** calculado solo; "Dejo" arranca igual a lo contado, así que confirmar sin mirar no retira nada. Las cuentas digitales siguen abriendo en 0, con el saldo de ayer al lado como referencia y un clic para copiarlo
- **4 · La doble resta del retiro:** el form mandaba `monto_inicial = contado − retiro` **y además** `monto_retiro`, y el backend creaba el egreso encima → el arqueo nacía esperando el retiro restado dos veces (ningún test lo cubría, porque `monto_retiro > 0` no se probaba). Ahora manda `monto_inicial = max(contado, dejo)` y `monto_retiro = max(0, contado − dejo)`, así que el esperado arranca igual al fondo. Además: NaN en el arqueo cuando el efectivo esperado coincidía con "Dejo", y el `:disabled` de **"Registrar pago" estaba negado** — el botón salía apagado cuando el form estaba completo y encendido cuando no, donde la función lo ignora. Nunca llegó a registrarse
- **5 · Egresos que no afectan a las cajas:** nueva columna `movimientos_caja.afecta_caja` (migración en `_migrate_new_columns`, `DEFAULT 1` = todo lo viejo queda como estaba). En **Nuevo Movimiento → Egreso** aparece "¿Sale de una caja del sistema?". Si la respuesta es "No" (pago particular, paga patronal, giro desde cuenta propia), el movimiento queda en el historial con badge **externo** pero **no baja el esperado de ningún medio**: si lo bajara, el cajero cerraría con una diferencia de plata que nunca estuvo en el cajón. El filtro está en los 4 cálculos de saldos (`_saldos_de_sesion`, `obtener_saldo_por_medio`, `obtener_resumen_por_medio_pago`, `obtener_detalle_medio_sesion`), en los reportes de `/reportes` y `/dia`, y en `egresos_totales` del Calendario
- **8 · Medios de pago en mobile:** el POS mostraba solo siglas ("EFP", "DÉB"). Grid `grid-cols-3 sm:grid-cols-7` con las etiquetas siempre visibles y los números ocultos en pantalla chica
- **9 · Configuración del POS con una sola verdad:** `GET/PUT /api/config/pos` pasó a claves camelCase, se agregó `calculadoraAlcance` / `calculadoraHistorial` y es accesible para el cajero (antes exigía admin, así que el POS no podía leerla). El POS la trae en `onMounted` y la manda a `posPrefs.setEnabledPaymentMethods`; un `watch` sobre `mediosPago` baja del carrito un medio que quedó apagado. El localStorage quedó como **caché**, no como fuente
- **Tests:** 12 nuevos (`tests/test_caja_egresos_externos.py` + las guardas de contrato de ArqueoMedios y del modal de apertura). Suite: **750 passed**

### Historial de Caja: sesiones mal agrupadas y filtro de fechas corrido — 15/10/2026
El dueño reportó el resumen del Historial de Caja con datos imposibles: una sesión con Apertura $0 y Cierre $156.000 (que no le correspondía), otras "Abierta" con Ingresos $0 pese a ventas reales. Causa raíz y fix:

- **`GET /api/caja/reportes` iteraba los movimientos en orden DESC** pero la agrupación (apertura → ingresos/egresos → cierre) asume orden cronológico. Contra los datos reales: el cierre de la sesión de las 09:40 se asignaba a la apertura de las 22:19, los ingresos/egresos de la sesión quedaban huérfanos (`sesion_actual` en `None`) y las sesiones sin cierre aparecían "Abierta" eternamente. Ahora itera en ASC (`created_at, id`) y revierte la lista para mostrar la más reciente arriba
- **Estado "sin_cierre"**: una sesión reemplazada por una apertura posterior sin cierre ya no muestra "Abierta" (que en la práctica nunca se puede cerrar) sino **"Sin cierre"** en rojo — con el auto-cierre desactivado en el server, es la única forma de ver esas jornadas olvidadas
- **Totales para toda sesión**: antes solo se calculaban al momento del cierre; las sesiones abiertas o sin cierre mostraban Ingresos y Egresos en $0
- **Fechas en hora local (AR)**: `/reportes`, `/dia` y `/calendario` convierten los límites de fecha local argentina a UTC con **+3h** (00:00 AR = 03:00 UTC). Los dos últimos **restaban** 3h y su ventana quedaba corrida 6 horas: cortaba las tardes/noches (donde caen los cierres de las 22:00) y el último día del mes en el calendario perdía la noche. En el frontend: `calcularFechasFiltro` manda fechas locales en vez de `toISOString()` (a las 23:59 AR ya era el día siguiente en UTC), y `verDetalleSesion`/el título del modal usan `fechaLocalAR()` en vez de la parte de fecha del ISO en UTC (una sesión abierta 22:19 AR mostraba el día siguiente)
- **Verificado contra la DB real**: la sesión 13/10 09:40 ahora muestra Cerrada con cierre $156.000 = $33.900 + $135.100 − $13.000 ✓; 12/10 y 13/10 22:19 como "Sin cierre"; 14/10 cerrada con $123.550 ✓. De paso quedaron a la vista discrepancias reales que el bug ocultaba (p. ej. 10/10: cierre $50.200 vs. saldo $83.950 — eso es un tema de la operatoria, no del sistema)
- **10 tests nuevos** (`tests/test_caja_reportes_historial.py`, 738 en total): regresión del cierre mal asignado, sesiones sin cierre, totales sin cierre, orden, rango de fechas en hora AR y cierre automático en el historial

### Fix: la app se colgaba tras volver de un rato / deploy nuevo — 13/10/2026
Dos causas raíz del "vuelvo a la app y queda todo colgado hasta hard refresh":

- **Service worker con versión congelada**: `CACHE_VERSION` estaba hardcodeado (`apex-erp-v5`) y nunca se bumpceaba; el `index.html` cacheado seguía referenciando chunks hasheados borrados del server tras cada deploy → el import lazy del router fallaba en silencio y la navegación se trababa. Ahora: **network-first para el shell** (navegaciones + `index.html`), cache-first solo para assets hasheados (inmutables), y `postbuild.cjs` stampa `dist/sw.js` con el commit (`apex-erp-<sha>`) para que cada deploy instale el SW nuevo y limpie los caches viejos
- **Token JWT (20 h) sin manejo global de 401**: `authenticated` quedaba `true` en memoria y todas las llamadas fallaban en silencio. Ahora `api.js` intercepta 401 (excepto `/api/auth/*`) → evento `apex:session-expired` → logout + redirect a `/login` + toast; más revalidación silenciosa del token al volver a la pestaña (`visibilitychange`, throttle 5 min)
- **Timeout de 30 s en todo fetch** (`AbortSignal.timeout`): un fetch colgado tras despertar de sleep ya no deja la vista en loading eterno
- **`router.onError`**: ante un chunk 404 post-deploy recarga una sola vez (flag en `sessionStorage`, sin loops)
- **`controllerchange` del SW** → reload automático cuando se instala una versión nueva (solo si ya había un SW controlando)
- De paso: bug en `PreciosOnlineView` — el PDF de análisis de precios pasaba `{ responseType: 'blob' }` como `params` (el 2do argumento de `api.get`), el botón nunca funcionó. Commit `633589d+1`

### Sectores mobile: ubicar productos escaneando con la cámara — 13/10/2026
Asignar sectores estando en el local seguía siendo de PC (Etiquetas). Ahora se recorre el estante con el celular apuntando a los códigos.

- **`/sectores`** (nueva vista mobile, admin/encargado/repositor): elegir el sector donde estás parado con botones grandes que muestran cuántos productos tiene cada uno, y se abre la cámara de una (iOS exige toque para dar acceso)
- **Escaneo continuo** con el composable `useBarcodeScanner` existente (BarcodeDetector en Android/Chrome, ZXing en iOS/Safari), cámara a pantalla completa con guía, cooldown 1,2 s
- Cada código leído se **asigna al toque** vía el bulk `POST /api/productos/asignar-sector` con un solo id; el lookup es local sobre el store de productos, así que no hay round-trip por escaneo
- **Lista de lo escaneado en la vuelta** con la marca "venía de X" para los que cambiaron de sector; **Deshacer último** (revierte al sector anterior, o a "sin sector") y **Limpiar**
- Feedback para el que está con las manos ocupadas: vibración al acertar, flash verde con el nombre del producto, flash rojo + toast si el código no existe (queda en una lista "no encontrados" de la vuelta)
- **Sector ya asignado** → aviso suave "ya estaba acá", no duplica la lista
- Entrada manual de código por si la cámara no lee algo
- Contadores por sector ajustados en vivo con lo asignado en la sesión
- Entradas de descubrimiento: link **"Sectores (móvil)"** en el sidebar (igual que Cargar Mercadería) y **"Sectores"** en el menú hamburguesa de las 3 vistas mobile
- Sin cambios de backend: reutiliza `GET /api/sectores`, el store de productos y `POST /api/productos/asignar-sector`. Commit `fdd3b03`

### Etiquetas: asignar sector rápido — 13/10/2026
Asignar sectores desde Etiquetas era inviable: había que tildar producto por producto de un listado de hasta 500, con la selección escondida en un card del panel izquierdo.

- **Buscador instantáneo** sobre lo ya cargado (nombre, código, marca o categoría, sin tildes, mismo criterio que Productos) y chip **"Sin sector (N)"** que muestra de una cuántos quedan sin ubicar. El flujo completo quedó en 4 clics: filtrar → "Seleccionar todo lo filtrado" → elegir sector → Asignar
- **Seleccionar todo lo filtrado**: el tilde del header y el botón trabajan sobre lo que se ve, no sobre el listado entero; si el filtro cambia, lo que quedó afuera se deselecciona solo, así "Asignar a N" nunca agarra productos invisibles
- **Sector editable en la fila**: un select compacto por producto que guarda al toque, para arreglos sueltos sin selections ni modales
- **La asignación masiva actualiza en pantalla sin recargar**: si el filtro "sin sector" está activo, los recién asignados se van solos de la lista y ya se agarra el próximo grupo
- **Generar PDF y marcar impreso usan lo que se ve** (selección, o filtrado si no hay selección): nunca imprimen productos escondidos por el filtro
- **`BaseTable`:** slot por encabezado de columna (`header-<key>`), retrocompatible con todas las tablas existentes
- Sin cambios de backend: se reutiliza `POST /api/productos/asignar-sector`. Commit `8c4f895`

### Aviso proactivo por Telegram — 13/10/2026
Además de la campana, el ERP avisa sin que nadie abra el sistema.

- **`avisos_service.py`:** una vez por día, a la hora que se elige en Ajustes → Avisos, manda al canal el mismo listado de la campana (mismas palabras, `mensaje_bajo` compartido). El chequeo corre cada 10 minutos con APScheduler —mismo patrón que los backups— y **lee la config en cada vuelta**: la hora y el token se cambian sin reiniciar, y si el servicio estaba caído a la hora pierde, el aviso sale igual más tarde
- **Cuándo no manda:** si el switch está apagado, si falta el token o el chat ID, si todavía no llegó la hora, o si no hay ningún producto bajo mínimo (y en ese caso no anota el envío, así si algo se cae a cero a la tarde avisa ese mismo día)
- **`POST /api/avisos/probar`** (solo admin) manda un mensaje de prueba ahora, para confirmar que el bot y el canal están bien antes de encender el switch. Todo queda en auditoría (`aviso_stock_telegram`, `aviso_stock_telegram_prueba`)
- **Ajustes → Avisos:** switch, hora (Argentina), token del bot (@BotFather) y chat ID del canal (@userinfobot)
- 13 tests (`tests/test_avisos.py`). Suite: **728 passed**. Commit `e0b062d`
- **Para activarlo:** crear el bot con `@BotFather`, sumarlo al canal del negocio, y pegar token + chat ID en Ajustes. Hasta entonces no manda nada

### Las horas de la DB se ven en hora Argentina — 13/10/2026
La base guarda UTC sin zona, y JavaScript tomaba esos strings como hora local de la máquina de quien mira: un evento de las 09:00 UTC se veía 06:00 en Argentina, y el "hace X min" de Auditoría mentía por 3 horas.

- **`useUtils`:** `parseFechaUTC` pone la `'Z'` a mano a los strings naive y respeta los que ya traen zona; `formatDateShort` / `formatDateTime` / `formatTimeShort` formatean en `America/Argentina/Buenos_Aires`; las fechas **sin hora** (`YYYY-MM-DD`, vencimientos de lotes y CAE) se quedan en UTC para que no se corra un día; `timeAgo` y `esHoy` compartidos
- **Auditoría:** el timestamp de la tabla, el "hace X min" y los minutos del carrito abandonado
- **Caja:** los formateadores de fecha/hora de las sesiones y movimientos, y el "es de hoy"
- **Compras, POS, Calendario, Facturación, Backups, Etiquetas de precios, FacturaDetalleModal y Productos:** mismos helpers en lugar de `new Date()` a secas
- **No se tocaron** los Date armados en el navegador (calendarios, rangos del día del Cierre, tickets del POS): ahí el valor ya es local y no tenía bug. Commit `b63c84f`

### Campana de avisos (stock bajo y novedades) — 13/10/2026
El sistema empieza a avisar en lugar de esperar a que alguien abra el Dashboard.

- **Salen del criterio único:** los avisos usan `filtro_reposicion` (bajo ∪ agotado, el mismo helper del KPI del Dashboard y del chip de Productos), así la campana y la pantalla no pueden contradecirse
- **`stock_service.detalle_reposicion`** arma el mensaje de cada producto: "Stock 2 / mínimo 8 — Proveedor: Carrefour — compra $1,500.00 — venta $2,500.00". El proveedor sale de la última compra no anulada (`CompraItem`→`Compra`→`Proveedor`) y si no hay compras, del proveedor principal en `producto_proveedor`; el precio de venta es el del producto
- **Un aviso por día, no uno por clic:** `Notificacion` lleva una `clave` (tipo + fecha) y `generar` no duplica si el estado sigue igual; a los 30 días se borran solos. La lectura se guarda en `NotificacionLeida`, con `usuario_id` NULL = "leído para todos"
- **Dos switches en Ajustes → Avisos:** `avisos_lectura` (usuario | global) decide si cada uno tiene la campana suya o si lo que lee uno le sirve a todos; `avisos_granularidad` (tipo | producto) decide si el bajo stock llega como un aviso con el listado adentro o como un aviso por producto para ir tildando
- **Tipos que salen:** stock bajo, sin stock, caja abierta, lotes vencidos, lotes por vencer (7 días) y licencia por vencer
- **Frontend:** campana en el header con badge de no leídas, panel con "Marcar todas como leídas", y el click lleva a la vista que corresponde (los de stock abren Productos con `?stock=bajo`, filtro que ya se lee solo)
- 11 tests (`tests/test_notificaciones.py`). Suite: **715 passed**. Commit `87b5de0`

### Un criterio único de "stock bajo" — 13/10/2026
Había tres reglas distintas para lo mismo: el chip de Productos marcaba ~319 productos con `stock_minimo || 5` mientras el Dashboard marcaba 18 con `stock_minimo > 0`.

- **Regla única** (`stock_service.filtro_bajo`): activo + controla stock + mínimo definido (`stock_minimo > 0`) + stock alcanzado o pasado. Con mínimo en 0 no hay aviso: significa "no definí mínimo", no "está al límite". Acompañan `filtro_agotado` (stock ≤ 0) y `filtro_reposicion` (bajo ∪ agotado, que es el alcance de `/productos/stock-bajo`)
- **Backend:** el KPI "Stock Crítico", el detalle de stock crítico, `sin_stock` y `GET /api/dashboard/alertas` pasaron al helper; `/api/productos/stock-bajo` dejó de recalcular lotes producto por producto (549 queries por request) y ahora usa el mismo criterio que el resto
- **Frontend:** `services/stock.js` con `esStockBajo`/`esAgotado` reemplaza el `stock_minimo || 5` en el chip, el filtro, el badge y el KPI del detalle de producto. Los agotados sin mínimo ahora se marcan con badge "Sin stock" en vez de quedar invisibles
- **Borrado:** `LOW_STOCK_THRESHOLD` de `app/config.py`, que se leía y no se usaba en ningún filtro
- 11 tests (`tests/test_stock_bajo.py`) que además verifican que KPI, alertas y endpoint digan lo mismo. Suite: **704 passed**

### IA habilitada en producción (smoke end-to-end) — 12/10/2026
La capa de IA pasó de "código listo" a **andando contra el proveedor real** en el server.

- **Carga de la key:** `EnvironmentFile=-/etc/erp-comercio/ia.env` agregado al unit (`98584ea`/`34fdf30`), archivo `600` de `erp`. El cliente además guardó la key como **BYOK** desde Ajustes (`auditoria: ia_api_key_guardada {"origen":"ajustes"}`), así que manda la de la DB por precedencia `DB > env`. Los dos orígenes apuntan a la misma key de Groq
- **`scripts/smoke_ia.py`**: imprime el snapshot de config, hace el ping y pide un lote con `sugerir_con_ia` (mismo endpoint que el panel). Dos flags que nacieron de problemas reales:
  - `--env-file /etc/erp-comercio/ia.env` — correrlo a mano (ssh/sudo) **no hereda** el entorno que systemd arma para el servicio, así que decía "IA deshabilitada" mientras la app sí la tenía. Se lee **antes** de importar `app.config`, que congela `IA_DEFAULT_API_KEY` en el import
  - `--aplicar` (dry-run por defecto, criterio de `normalizar_productos_titlecase.py`): escribe solo las propuestas cuya categoría destino difiere de la actual — el mismo filtro del panel — y registra auditoría `recategorizacion_producto` con `origen: scripts/smoke_ia.py --aplicar`
- **Modelo:** `llama-3.3-70b-versatile` devuelve **404 model_not_found** en el Free tier (el catálogo del dashboard lo muestra, pero `/v1/models` no lo incluye para esa key). Default en `registro.py` → `openai/gpt-oss-120b`, test y placeholder de Ajustes actualizados; `ia_model` en la DB también (`98584ea`)
- **Resultado:** ping `Conectado con openai/gpt-oss-120b`, lote de 10/556 candidatos → **2 aplicados** (391 "2 por Mil" → Otros, 308 "7 Seven Violet Cherry" → Bebidas), 8 ya estaban en la categoría propuesta, 0 errores, 0 categorías creadas; uso 4/1000. Auditoría `2352`
- Commits: `d64d3ef` (script), `34fdf30` (`--env-file`), `98584ea` (modelo + `--aplicar`), `1d40e41` (auditoría). Suite: **666 passed**
- **Al correr scripts en el server:** siempre `sudo -u erp` + `DATABASE_URL=sqlite:////data/erp/erp_comercio.db` (sin env, el default `sqlite:///erp_comercio.db` es otra DB) y `--env-file` para la key

### Panel de recategorización: selección global, escaneo incremental y colores — 12/10/2026
Los tres arreglos que seguían al criterio de la IA (sección de arriba), en orden.

**2 · "Seleccionar todo" alcanza todas las páginas** (`9ae8896`)
- El problema real: la selección se caía al paginar (`cargar()` filtraba `marcados` contra la página visible) y el botón "Todo" sólo marcaba las filas visibles.
- `GET /api/productos/sugerencias/ids` devuelve todos los ids del filtro; el servicio extrajo `_query_candidatos()` para que la lista paginada y los ids midan exactamente lo mismo.
- `datosPorId` acumula las filas cargadas **y** las que devuelve la IA, así la lista de confirmación puede listar productos que la persona nunca abrió. Para eso `SugerenciaIA` ahora manda `nombre`, `categoria_actual_id` y `categoria_actual`: antes Pydantic los descartaba (el `for item in lote` del router los escribía para nada).
- `confirmarAplicar` manda los cambios de a lotes de **500**, que es el máximo que acepta el backend, y suma todo en un solo toast.
- La selección ahora se limpia al cambiar de filtro (modo o búsqueda), no al paginar.

**3 · Escaneo incremental (`ia_analizado`)** (`faea18e`)
- `sugerir_con_ia` llama a `marcar_analizados()` después de interpretar la respuesta: lo que la IA miró no vuelve a aparecer. Si la respuesta es ilegible o el proveedor falla, no se marca nada.
- Modo **"Nuevos para la IA"** en el panel: filtra `ia_analizado IS NOT true` — `IS NOT` y no `== False` porque las filas previas a la migración quedaron en NULL.
- `scripts/marcar_analizados.py` (dry-run por defecto, `--aplicar`): corrido en prod → **569 marcados**, y el rerun confirma que es idempotente.

**4 · Color por categoría**
- `categorias.color` (`#RRGGBB` o NULL) + migración en `_migrate_new_columns`. Aprovechó para agregar la migración de `productos.ia_analizado`, que **no estaba** (en prod existía sólo por un ALTER manual hecho a mano).
- Los defaults viven en `frontend/src/services/categorias.js`: si la base no tiene color, la pantalla usa el del rubro → **todas las categorías ya se ven con color sin escribir nada**, y las nuevas también.
- Puntito de color en la columna Categoría de **Productos** y junto a la categoría actual en **Recategorizar**. Editor `<input type="color">` por categoría en **Ajustes → Categorías y colores**, que escribe `color` y tapa el default.
- 10 tests (`tests/test_categorias_color.py`). Suite: **693 passed**

**Precisión medida a ciegas — `scripts/precision_ia.py`** (`ad1d4ff`/`32c30d5`)
Clasifica una muestra con seed fijo y `prompt_ia(..., incluir_actual=False)` (el modelo no ve la respuesta), y compara contra la categoría actual.

| muestra | propuestas | aciertos | ≥ 0.8 (lo que preselecciona la UI) | no propuso |
|---|---|---|---|---|
| seed 42 | 38 | 32 = 84,2% | 32/37 = **86,5%** | 2 |
| seed 7 | 34 | 29 = 85,3% | 29/34 = **85,3%** | 6 |
| **total** | **72** | **61 = 84,7%** | **61/71 = 85,9%** | **8** |

- **Las "discrepancias" casi siempre eran la IA teniendo razón**: de las 11, casi todas proponían sacar algo que estaba mal categorizado — desodorante en Almacén → Perfumería, papel higiénico → Limpieza, bebida energizante → Bebidas, té y café → Cafetería, tapa de lasaña y manteca en Frescos → Almacén, pan → Frescos. O sea: 86% es un **piso**, no un techo.
- La cobertura subió al 92%/85% con el prompt nuevo (regla de "no adivinar"): el modelo se anima más porque ahora tiene cómo decir "no sé" sin mandar cualquier cosa.


### Criterio de la IA: más contexto y "no adivinar" — 12/10/2026
El panel mostraba la propuesta de la IA **con el mismo peso para todo**, y con un prompt que le daba poco de qué agarrarse. Se cambió el criterio de punta a punta.

- **Prompt con todas las pistas:** `prompt_ia()` manda `id | nombre | marca | código de barras | categoría actual | descripción[:120]` (antes id/nombre/marca/descripción). El catálogo dejó de ser `id | nombre` solo: cada categoría del nuevo diccionario **`RUBROS`** (golosinas, almacén, bebidas, frescos, limpieza, papelería, cafetería…) lleva `| qué entra: ...`, para que el modelo sepa qué significa el nombre
- **No adivinar:** `SISTEMA_IA` ahora pide **`confianza` entre 0 y 1** por sugerencia y agrega la regla central: si ninguna categoría encaja claramente, devolver `categoria_id` **null** — mejor no proponer que meter mal un producto. Además prohíbe inventar ids fuera del catálogo y desalienta las categorías de relleno (General/Otros/Varios). Cuatro ejemplos few-shot, incluido un caso ambiguo ("2 por Mil") con confianza 0.2
- **Confianza en el flujo:** `interpretar_ia()` la lee con default **0.5** (si el modelo no la manda o manda basura) y la recorta a `[0,1]`; nuevo campo `confianza` en `SugerenciaIA`
- **UI:** `UMBRAL_CONFIANZA = 0.8` en `RecategorizarView.vue`. La propuesta se muestra igual, pero **solo se preselecciona si llega ≥ 0.8** (antes se marcaba todo sin mirar). El % aparece al lado del badge en la columna Sugerencia (verde ≥ 0.8 / ámbar debajo) y el toast resume cuántas se preseleccionaron y cuántas quedaron sin marcar
- **`incluir_actual=False`:** flag en `prompt_ia()` para esconder la categoría actual, que es lo que necesita medir la precisión a ciegas (paso siguiente)
- **Tests:** 8 nuevos (`TestConfianzaIA`, `TestPromptIA`, +1 endpoint que verifica que la confianza llega al JSON de respuesta). Suite: **674 passed**

### Title Case en el modelo (nivel 1) — 12/10/2026
El protocolo de Title Case del catálogo pasó a vivir **en los modelos**, así que lo cumplen también los caminos que no pasan por `producto_service` (seeds, imports de catálogo, scripts, endpoints nuevos).

- `@validates` en `Producto(nombre, marca, descripcion)`, `Categoria(nombre)` y `Sector(nombre)` aplicando `title_case_es`; no-op si el valor no es string. El import va **adentro** del validador: `texto_service` cuelga de `app.services`, cuyo `__init__` importa `producto_service`, que importa los modelos — importarlo arriba rompe en el orden `import app.models` primero (que es el de los tests)
- Ya estaba cubierto a nivel servicio: `normalizar_producto_campos()` se llamaba en `crear_producto`, `actualizar_producto` y `guardar_desde_lookup` (alta manual, alta desde Compras, edición y auto-lookup). Lo que faltaban eran los caminos que se salteaban el servicio
- Bonus: `categorias.nombre` es `unique`, así que dos altas del mismo concepto con distinto casing ahora **chocan** en vez de crear una categoría duplicada silenciosa. Y los nombres guardados pasan a ser los mismos que devuelve `_map_categoria()`, que es lo que compara el `find(c => c.nombre === resp.categoria)` de Products/Compras/QuickCreate
- **Nivel 2 (también hecho):** el chequeo de duplicados comparaba contra el **input crudo**, así que con una variante de casing ("golosinas" con "Golosinas" existiendo) el chequeo no choca y el `INSERT` sí → 500. Normalizado con `title_case_es` antes del chequeo en `categorias.crear` (:42) y en `producto_service._obtener_o_crear_categoria` (:237), y agregado el chequeo que **faltaba en `categorias.actualizar`** (renombrar a una variante de otra categoría tiraba 500; ahora 400, igual que sectores). `categorizacion_service._obtener_o_crear_categoria` ya comparaba con `normalizar()` (sin tildes ni mayúsculas) y no tenía el problema
- **Tests:** 15 nuevos (`tests/test_titlecase_modelos.py`); ajustados 4 que asercionaban el casing crudo del input (2 en `test_recategorizar`, 1 en `test_sectores`). Suite: **666 passed**

### IA con gating por plan — A1+A2+A3+B+C hechos — 12/10/2026
Nuevo eje de trabajo: **IA/LLM con plan de licencia**, **Sectores** para impresión de etiquetas y **panel de recategorización**. Orden decidido: IA → Sectores → Panel.

**A1 — Capa de IA (`app/services/ia/`)**
- `proveedor.py`: ABC `ProveedorIA.completar(sistema, usuario, como_json, ...) → IARespuesta(texto, tokens_in, tokens_out, modelo, reintentos)`; errores tipados `IADeshabilitada`, `LimiteAgotado`, `ErrorProveedor`
- `openai_compat.py`: `ProveedorOpenAICompat` sobre `{base_url}/chat/completions`; retries con backoff acotado + `Retry-After` (statuses {408,409,425,429,500,502,503,504}, `dormir()` único punto mockeable); `extraer_json()` con escaneo balanceado (respeta strings/escapes/anidamiento)
- `limites.py`: contador mensual en `configuraciones` (`ia_uso_YYYY_MM`); `verificar` chequea ANTES de llamar
- `registro.py`: claves `ia_habilitada/ia_provider/ia_api_key/ia_base_url/ia_model/ia_limite_mes`; catálogo `PROVEEDORES` (groq/openai/deepseek/custom); `obtener`, `configuracion` (enmascarado, write-only), `completar` (punto único: gating+límites+registro), `probar`
- Config solo por env: `IA_DEFAULT_API_KEY/BASE_URL/MODELO`, `IA_TIMEOUT`, `IA_MAX_REINTENTOS`. **La key de mi cuenta nunca va a la DB**; el BYOK del cliente sí (precedencia DB > env)
- 57 tests (`tests/test_ia_proveedor.py`): `extraer_json`, reintentos, parseo de usage, enmascarado, precedencia, límites

**A2 — Gating por plan**
- `Licencia.plan` (`trial|basico|pro|enterprise`) + `Licencia.limite_ia_mes` (override por cliente); migración en `main.py` (las existentes quedan `pro` para no romper la instalación actual; inserts nuevos nacen `trial`)
- `app/services/planes_service.py`: catálogo `PLANES` con `features` (`ia` solo en pro/enterprise; `sectores` en todos); `plan_de`, `features_de`, `tiene_feature`, `limite_ia_de` (licencia > config > default)
- `app/auth/dependencies.py`: `requiere_feature(feature)` → **402 Payment Required** si el plan no lo incluye (el frontend distingue "no incluido en tu plan" de un error genérico)
- `GET /api/licencia/estado` ahora expone `plan`, `planes`, `features`, `ia_disponible`, `ia_configurada`, `ia_uso {llamadas, limite}` — la misma respuesta consume `stores/auth.js`
- `crear_licencia(..., plan=...)` y `POST /generar` aceptan plan; historial incluye plan
- 40 tests (`tests/test_planes_licencia.py`)

**A3 — UI de IA**
- `app/routers/ia.py`: `GET/PUT /api/ia/config` (admin/encargado y admin), `POST /api/ia/probar` con `requiere_feature("ia")` → **402 si el plan no incluye IA**. El snapshot trae `plan`, `plan_incluye_ia`, `disponible`, `limite_configurado`, `limite_mes` (efectivo), `uso_mes` — nunca la key cruda
- `registro.guardar(db, cambios)` recibe **solo los campos enviados** (`model_fields_set`), así un campo ausente jamás se pisa con `None`; `api_key: ausente = no tocar, "" = borrar`
- `AjustesView.vue` sección "Inteligencia Artificial": badge de estado en el header (Activa / Sin API key / Deshabilitada / Plan sin IA), banner violeta cuando el plan no incluye IA, medidor de uso del mes con barra (ámbar >80%), toggle, proveedor (al cambiarlo resetea URL/modelo a los del proveedor), API key write-only con máscara+origen y botón de borrar, URL base, modelo, límite mensual, y "Guardar y probar conexión" (guarda antes de probar)
- `LicenciasView.vue`: columna **Plan** con badge, y select de plan en el modal de generación (catálogo desde `GET /api/licencia/estado`). También se arregló `loadLicenses`, que metía el JSON crudo y dejaba la tabla con fechas/estado vacíos
- 17 tests (`tests/test_router_ia.py`). Total suite: **571 passed**

### C — Panel de recategorización con IA — 12/10/2026
Nada se mueve solo. `categorizacion_service.aplicar()` es **el único punto de escritura** y recibe lo que eligió una persona; la IA y las keywords solo proponen.

- `app/services/categorizacion_service.py`
  - `sugerir_local()`: diccionario `SINONIMOS` del rubro argentino (almacén/kiosco) + detección de que el **nombre de una categoría** esté escrito en el producto. Confianza 0.92 si aparece la categoría, 0.75 si la pista está en el nombre, 0.60 si solo en la descripción. Nunca sugiere `General` ni lo que el producto ya tiene
  - `_resolver()`: casa el nombre canónico contra el catálogo real del cliente (igualdad, y contención solo si el canónico tiene ≥4 letras, para que "Pan" no capture "Panadería")
  - `candidatos(modo, q, page, page_size)`: `pendientes` (sin categoría **o** en General), `sin_categoria`, `general`, `todos`; excluye inactivos y ya calcula `destino_id`
  - `prompt_ia()` / `interpretar_ia()`: prompt en español con el catálogo real y JSON estricto; la respuesta se filtra (ids pedidos, `categoria_id` inventado → null, `nueva_categoria` cortada a 60 y descartada si es neutra, basura de tipos ignorada)
  - `TAMANO_LOTE_IA = 20`; `aplicar()` crea/reutiliza categorías (dedup por nombre sin tildes ni mayúsculas), reactiva una inactiva y devuelve `{aplicados, categorias_creadas, errores}`
- `app/routers/recategorizar.py`
  - `GET /api/productos/sugerencias/candidatos` (admin/encargado) → `RespuestaData[CandidatosPage]` con `items/total/page/page_size` **adentro** del payload (si no, `api.js` desenvuelve el `data` y se pierde el total)
  - `POST /api/productos/sugerencias/ia` con `requiere_feature("ia")` → **402** sin IA configurada, **409** límite agotado, **502** proveedor/respuesta ilegible; recorta el lote a 20
  - `POST /api/productos/aplicar-sugerencias` → escribe y registra auditoría `recategorizacion_producto`; máximo 500 por llamada
  - Registrado en `main.py` **antes** que `productos.router`, para que `/sugerencias/*` nunca caiga en un `/{producto_id}` genérico
- `frontend/src/views/RecategorizarView.vue` + ruta `/recategorizar` + entrada en el sidebar (admin/encargado)
  - filtros por modo y búsqueda, contador sin categoría / categorizadas, paginación
  - **"Analizar con IA"** en lotes de 20 con barra de progreso; los resultados se pre-seleccionan para revisión
  - cada fila tiene su select de destino (incluye `Nueva: X` cuando el modelo propuso una categoría inexistente) — elegir algo distinto de lo actual es la confirmación explícita
  - botón "Aplicar N" → **modal de confirmación** con el detalle antes de escribir; los seleccionados sin cambio se descartan y se informan
- 49 tests (`tests/test_recategorizar.py`). Total suite: **651 passed**

**Script one-time ejecutado (12/10/2026):** `scripts/normalizar_productos_titlecase.py --aplicar` contra `/data/erp/erp_comercio.db` → 486 de 569 productos (599 campos: 466 `nombre`, 132 `marca`, 1 `descripcion`), 0 de 9 categorías. Verificado idempotente (segunda corrida: 0 cambios) y diff columna por columna sobre una copia: solo toca `nombre`/`marca`/`descripcion`; códigos de barras, precios e stock intactos (el único efecto colateral es `updated_at`, por el `onupdate` de SQLAlchemy). Backup: `/data/erp/erp_comercio.db.bak-20261012-titlecase`.

El script quedó endurecido en `a39615f`: **dry-run por defecto** y exige `--aplicar`, imprime la DB real que va a usar y se niega a escribir si la URL sigue siendo el default `sqlite:///erp_comercio.db` (relativa al cwd, no es la de producción). `--db` se resuelve antes de importar `app.database`, porque ese módulo arma el engine en el import.

### B — Sectores (ubicación física) para etiquetas y cargas — 12/10/2026
Los sectores son **categorías físicas de ubicación** ("Golosinas", "Bebidas frías", "Estantería 3") y no entran en el módulo de Categorías. El feature `sectores` está en **todos los planes**.

- `app/models/sector.py`: `nombre` (index, **sin unique en DB** — se valida en el router solo contra activos, así un sector borrado no bloquea recrear el nombre), `orden`, `activo`, `created_at`; relationship `productos`
- `app/models/producto.py`: `producto.sector_id` (FK a `sectores`, nullable, index) + `producto.sector`
- `app/routers/sectores.py`: `GET` (activos, un solo query de conteos), `POST` (**upsert**: activo existente → lo devuelve; borrado → lo reactiva), `PUT /{id}`, `DELETE /{id}` → **soft-delete + `sector_id = NULL` en sus productos** (sin estados colgantes; reactivar no restaura productos, devuelve `productos_afectados`)
- `POST /api/productos/asignar-sector`: asignación **bulk** `{productos_ids, sector_id}` (valida sector activo, solo productos activos) — usado por la herramienta de la vista de Etiquetas
- `app/schemas/producto.py` + `producto_service`: `sector_id` en create/update. **`actualizar_producto` ignora `None`** en su loop `updatable`, así que `sector_id` se maneja **fuera** del loop para poder limpiarlo
- `compras.py`: al cargar mercadería, `items[].sector_id` **reubica productos existentes** y se aplica a los nuevos (`null` = no tocar)
- `etiquetas`: filtro `sector_id`, orden `sector` (Sector.orden → Sector.nombre → Producto.nombre con `nullslast()`) y `sector_id`/`sector_nombre` en `EtiquetaProductoOut`
- **UI**
  - `ProductsView`: select **Sector** con botón "+" (quick-create inline) en la fila Categoría | Proveedor | **Sector** (`sm:grid-cols-3`); `form.sector_id` en defaults, en la carga del producto (no debe filtrarse entre productos) y normalizado en `saveProduct`
  - `ComprasView`: fila 2 de cada item con select **Sector** + "+" (quick-create con foco automático); por defecto trae el sector actual del producto y al guardar reubica
  - `EtiquetasPreciosView`: filtro **Sector**, orden **Sector (ubicación)**, columna Sector en la tabla y herramienta **"Asignar sector a la selección"** (bulk)
- 31 tests (`tests/test_sectores.py`). Total suite: **602 passed**

### Rediseño de Etiquetas de Precios — 09/10/2026
- **Layout de dos paneles** (desktop): controles a la izquierda (340px), tabla de preview a la derecha; en mobile se apilan
- **Presets de fecha** (Hoy / 7 días / 30 días / 90 días) como pills clickeables; al cambiar las fechas a mano se marca "Personalizado"
- **Preview visual de la etiqueta**: réplica CSS de cómo se ve la etiqueta real (marca, línea, descripción, código de barras simulado, precio grande, fecha, código) — cambia con el tamaño seleccionado (70×35 o 60×40) y muestra el primer producto seleccionado
- **Badges de motivo** en la tabla: cada producto muestra si es "Nuevo", "Precio" (cambió), o "Nuevo + Precio" — el backend ahora devuelve campo `motivo` en `EtiquetaProductoOut`
- **Historial colapsable**: se movió de card principal a un botón en el header que abre un modal con las últimas 5 impresiones
- **Action bar prominente**: botón "Generar PDF" a todo el ancho con el conteo de selección integrado (`Generar N etiqueta(s)`), Marcar impreso + Seleccionar todo como grid de 2
- **Selectores de formato como cards** con aspect ratio visual, no un dropdown plano
- **Tabla mejorada**: nombre + categoría/código debajo, badge de motivo, descripción inline, stock con color semántico

### Historial de compras vinculado en detalle de producto + modal detalle de compra — 09/10/2026
- **`info-detallada` enriquecido:** el historial de compras ahora incluye `compra_id` y `estado` de cada orden; ahora incluye compras **parciales** (antes solo recibidas); historial de ventas ahora trae `detalle` (últimas 50 filas: venta_id, numero, fecha, cantidad, precio_unitario, subtotal, medio_pago)
- **Modal "Detalle del Producto" rediseñado:** tipografía compacta (text-lg en KPIs, no text-4xl), header con identidad del producto (imagen, marca, código de barras, badges de estado), 4 KPIs compactos (stock/precio/margen/total vendido), historiales de compras y ventas como **tablas lado a lado** (fecha, proveedor/venta, N°, cantidad, $/u, subtotal), proveedores como lista compacta. Compras clickeables → navegan a `/compras?detalle=<id>` con el modal de detalle de compra abierto
- **Modal "Detalle de Compra" (`ComprasView`):** nuevo modal accesible desde el botón ojo en la columna acciones (y por deep-link `?detalle=`). Muestra header (proveedor, fecha, estado, total), tabla completa de items (producto, cant. pedida, recibida con color, precio unitario, subtotal), totales (subtotal/IVA/total) y notas. Usa `GET /api/compras/{id}` (endpoint ya existente pero que nadie llamaba)
- **Deep-link:** al llegar a `/compras?detalle=<id>` abre el modal de esa compra y limpia la query (compartible/bookmarkeable)
- **BaseModal:** size `4xl` agregado (max-w-4xl)

### Modo offline end-to-end (web + celular) — 09/10/2026
- **Fuentes e iconos self-hosted:** el CDN de Google Fonts y Font Awesome es cross-origin y el SW no lo cachea (respuesta opaca) → offline la app quedaba sin un solo icono y con tipografía fallback. Ahora `@fontsource/*` + `@fortawesome/fontawesome-free` se empaquetan en el build (14 woff2 con hash, cacheados por el SW); links CDN borrados de index.html
- **`useOfflineSales` blindado:** flag anti-concurrencia (dos syncs en paralelo = ventas duplicadas), listener `'online'` a nivel de módulo (una sola vez, y sincroniza aunque no abran el POS), id con `crypto.randomUUID()`, y **reanudación**: se persiste `ventaId` + `itemsEnviados` entre pasos — si el sync se corta a mitad de los items, el reintento continúa desde ahí sin crear una venta duplicada
- **Cola completa:** el payload encolado ahora replica el flujo online (oferta_info, importe, medio_pago_carga, efectivo_pagado, comprador_cuit) — antes se perdían kilos, ofertas y pago mixto al sincronizar
- **Cobro Móvil encola offline:** `crearVenta()` diferencia error HTTP (toast) de corte de red (cola + vacía carrito); solo se encolan cortes de red, no rechazos del servidor
- **OfflineIndicator útil:** botón "Sincronizar ahora" + auto-sync al evento `'online'` desde cualquier vista (antes solo al abrir el POS)
- `sw.js` a `apex-erp-v5` (limpia caches viejas al deployear)

### Etiquetas de Precios: 3 bugs + UX — 09/10/2026
- **Nunca mostraba productos (bug principal):** `api.js` desenvuelve `{data: [...]}` y devuelve el array, pero la vista hacía `data.data || []` sobre ese array → siempre vacío. Ahora con unwrap robusto (`Array.isArray`)
- **Día "hasta" excluido (backend):** el servicio comparaba `updated_at`/`created_at` (DateTime con hora) con `between(desde, hasta)` donde `hasta` es medianoche — en SQLite la comparación string dejaba fuera todo lo del día hasta (casi siempre "hoy"). Bound superior ahora es `hasta + 1 día` (exclusivo); 6 tests nuevos en `test_etiquetas_fechas.py`
- **409 STOCK_CERO roto:** el frontend chequeaba `e.data.codigo` pero el detalle venía anidado (y como string crudo en el path blob); además "Generar igual" re-lanzaba el mismo 409 en loop porque el backend no tenía forma de forzar. Nuevo flag `forzar` en `GenerarPDFRequest` + `parsearDetalle409()` que parsea ambos formatos
- **UX:** título con icono (antes no tenía), modal propio para stock cero (antes `confirm()` nativo), EmptyState con acción "Ver todo el catálogo" (desactiva los dos checkboxes de filtro y recarga), carga inicial sin toast, toast de "marcar impreso" con el conteo real, sin `console.error`

### Escáner de cámara en el POS de Ventas — 09/10/2026
- **Botón de cámara** en el suffix del campo Código de Barras (ícono `fa-camera`; al activarse pasa a `fa-camera-rotate` con estado resaltado). Usa el mismo composable `useBarcodeScanner` (BarcodeDetector) que las vistas mobile de piso, en **modo continuo con cooldown de 600ms**: el operador escanea varios códigos seguidos sin reabrir nada y cada lectura dispara el mismo `triggerPOSLookup` del input (alta local, búsqueda externa o alta rápida `*Nombre*Precio`)
- **Vista inline, no modal:** el preview ocupa todo el ancho bajo el input (no tapa el carrito mientras se escanea); se corta con el toggle de cámara del suffix. Si el navegador no soporta BarcodeDetector o niega el permiso, el composable avisa con toast y muestra el error bajo el input

### UX del escáner POS: preview grande, flash verde y sin teclado — 09/10/2026
- **Preview a todo el ancho** (`aspect-[4/3]` en mobile, `aspect-video` en desktop): se quitó el texto explicativo y el botón "Detener" de al lado; se corta con el mismo botón de cámara (toggle) del suffix del input
- **Flash verde al leer:** el composable expone `detectedFlash` (350ms) y el POS lo muestra como overlay emerald sobre el video — feedback claro de que el código se procesó
- **Sin teclado virtual después de cada lectura:** `refocusBarcode()` no enfoca el input si la cámara está abierta, y al detectar se blurrea el `document.activeElement` por si el input ya tenía foco (el foco reenfocado post-lectura era lo que abría el teclado en mobile)
- **Foco/imagen:** constraints de cámara ahora piden 1280×720 ideales + `focusMode: 'continuous'` (mejor nitidez para ZXing y enfoque continuo donde el navegador lo soporta; se ignoran si no)

### Fallback ZXing para escáner de cámara en desktop e iOS — 09/10/2026
- **Problema:** `BarcodeDetector` (Shape Detection API) solo existe en Chrome Android/ChromeOS. Chrome desktop (cualquier versión) y Safari/iOS **nunca** lo implementaron, así que el escáner fallaba con "navegado no soportado" en PC e iPhone
- **Solución:** `useBarcodeScanner` ahora elige motor: `BarcodeDetector` si existe; si no, carga **`@zxing/browser` + `@zxing/library`** bajo demanda (`import()` dinámico → chunk separado de ~458 kB que solo baja quien escanea desde un navegador sin soporte nativo) y decodifica el mismo `MediaStream` con `decodeFromStream`. Sin dep de WASM
- **CobroMovilView migrado al composable:** borradas ~65 líneas de escáner duplicado que tenía el mismo bug del early-return; mantiene su UX single-shot (`continuous: false`: cierra la cámara tras cada lectura y procesa). El POS y las vistas de piso siguen en continuo
- Compila y los 451 tests siguen verdes; pendiente de verificación en Chrome desktop, iPhone Safari (iOS 26) y Chrome Android

### Fase 1 del roadmap mobile: componentes base responsive — 09/10/2026
- **`BaseTable` con modo cards en <640px:** el mismo componente renderiza, según breakpoint, una lista de tarjetas (título = primera columna + `dt/dd` con label/valor por columna) o la tabla de siempre. Sin tocar ninguna de las 12 vistas que lo usan: Products, Ventas, Clientes, Proveedores, Compras, Caja, Calendario, Usuarios, Auditoría, Licencias, Backups y EtiquetasPrecios quedaron con vista mobile de una. Respeta slots por columna, `row-click`, fila `detail` expandible, skeletons y empty state. Columnas secundarias se ocultan con `mobile: false`; título alternativo con `primary: true`
- **`BaseModal`:** `max-h` calculado con `100dvh` (con `100vh` el URL bar de iOS tapaba el footer y los botones quedaban fuera de pantalla), paddings `p-4 sm:p-6` y header/footer compactos en chico
- **`BaseInput` / `BaseSelect`:** `text-[16px] md:text-sm` en los tamaños sm/md — iOS hace zoom automático cuando el input tiene <16px, y el zoom rompía el layout de todos los modales
- **`BaseButton`:** targets táctiles ≥44px en md/lg e iconOnly md/lg (`min-h-[44px] md:min-h-0`)
- Verificado: build OK, 451 tests en verde. Pendiente de la Fase 2: pass por vista (Products, POS, Caja, Ventas, Clientes) para ajustar qué columnas van en la card

### Pantallas mobile exclusivas arregladas (cargar, control stock, cobro) — 09/10/2026
- **El problema:** `/cargar-mercaderia` y `/control-stock` "no andaban como si no estuvieran terminadas" — y literalmente no lo estaban. En ambas el botón **Escanear** tiraba `ReferenceError` (llamaban `abrirScanner`, el composable `useBarcodeScanner` expone `openScanner`). `/cargar-mercadería` montaba con error (`productosStore.fetchCategorias` no existe — `fetchAll` ya trae las categorías), **`guardar()` era una función vacía** ("Guardar y recibir" no hacía nada), la lista de items escaneados **nunca se renderizaba** (solo el header "Items (N)" y los computeds de totales estaban sin usar), y usaba el precio de venta como precio de compra
- **`/cargar-mercaderia` terminada:** lista de items con cantidad −/+, precio de compra editable (default `precio_costo || precio_venta`), quitar/vaciar, totales de und. e importe; `guardar()` valida proveedor + items, `POST /api/compras` con `recibir_directo: true` (mismo payload que ComprasView: producto, codigo_barras, cantidad, precio, precio_venta, categoria_id), limpia el carrito y refresca el catálogo; botón con estado de carga
- **`/control-stock`:** escanear ya no re-sincroniza todo (antes bajaba productos + lotes + catálogo entero en cada lectura, con spinner de por medio); ahora filtra en local y solo refresca productos+lotes si el código no está. Quitado el `overflow-y-auto` anidado que rompía el scroll
- **Ambas:** toasts placeholder `'ok'`/`'err'` reemplazados por mensajes reales, sin re-descarga de catálogo en cada sync (App.vue ya lo hace cada 1h), `tabActivo` correcto en Cargar (`'cargar'`, antes `'cobro'`), `auth.currentUser?.` con optional chaining
- **`/cobrar` (el más completo):** el filtro muerto de medios de pago (`mercadopago_pos` no estaba en la lista) eliminado; los flujos QR ahora chequean caja abierta **antes** de abrir el modal (antes se abrían los dos modales a la vez si la caja estaba cerrada)

### Shell responsive: sidebar-drawer + bottom-nav en mobile — 09/10/2026
- **El problema:** el `aside` del sidebar era fijo (`w-64`, sin hamburguesa) y en un celular comía la pantalla entera — ninguna vista se podía usar en el teléfono aunque sus clases fueran responsive. Arranque del plan "toda la app en mobile" (híbrida: responsive + pantallas dedicadas para flujos de piso como ya son `/cobrar`, `/cargar-mercaderia`, `/control-stock`)
- **`TheSidebar.vue` en mobile (<768px):** se vuelve drawer off-canvas (`fixed`, `-translate-x-full` ↔ `translate-x-0`) con overlay oscuro atrás; se cierra con tap en el overlay, botón ✕, `Escape` o al navegar. En desktop el comportamiento colapsable es idéntico al anterior (`showCollapsed` ignora el colapso en mobile)
- **`TheBottomNav.vue` (nuevo):** barra fija inferior `md:hidden` con las 5 acciones del piso (POS, Cobrar, Cargar, Stock, Caja) filtradas por rol, `pb-[env(safe-area-inset-bottom)]` para el home-indicator de iOS. No aparece en las rutas `bare` (las pantallas mobile dedicadas se quedan full-screen)
- **`TheHeader.vue`:** hamburguesa `md:hidden` a la izquierda (`toggle-menu`), breadcrumb/API-toggle/dot de red ocultos en mobile, padding compacto. **`App.vue`:** estado `menuAbierto`, se cierra al cambiar de ruta, contenido con `pb-24 md:pb-8` para no quedar debajo de la bottom-nav, footer oculto en mobile
- **Verificación:** build OK, 451 tests en verde. Probar en el celular: las vistas desktop quedaron usables (tablas aún apretadas — el paso 2 es el modo cards de `BaseTable`)

### Detalle de un medio en el arqueo + limpieza del commit `6c58510` — 09/10/2026
- **El problema que motivó el revisar:** el cierre mostraba "Efectivo esperado: $30.000" pero no había forma de ver **de qué se componía** ese número. El commit `6c58510` agregó el badge ámbar de métodos pendientes, pero su PENDIENTES.md se commiteó corrupto y el WIP del detalle quedó a medio hacer (el `ArqueoMedios.vue` no compilaba: `function bloqueado()` sin cuerpo, segundo bloque `<template>` raíz y la firma del service mal pasada)
- **Endpoint nuevo `GET /api/caja/medio/{medio_pago}/detalle?cierre_id=`:** devuelve apertura, ingresos, egresos, esperado y cada movimiento de la sesión. **Sale del mismo rango de movimientos con el que se calcula el arqueo** (`_movimientos_de_sesion` / `_movimientos_sesion_abierta`), así que la suma del detalle coincide con el esperado de la fila. Sin `cierre_id` describe la sesión abierta; con él, la de ese cierre — antes el WIP ignoraba el `cierre_id` y en una sesión vieja devolvía las ventas de hoy
- **Permisos:** sin `cierre_id` cualquier autenticado (el cajero lo usa al cerrar); con `cierre_id`, admin/encargado, igual que `GET /cierre/{id}/arqueo`
- **UI en `ArqueoMedios.vue`:** botón de lista junto al Esperado abre un modal (dentro del template raíz, con `BaseModal` y su footer slot) con las 4 mini-cards de resumen y la lista de movimientos: número de ticket + cliente para los ingresos de venta, descripción para el resto, hora argentina (`fecha` se serializa con `Z`: la DB guarda UTC naive) e importe con signo según tipo
- **Sesión correcta por dónde se abre el componente:** la conciliación de una sesión cerrada pasa `:cierre-id="cierreSesionId"`, el cierre de la caja abierta no lo pasa (detalle = sesión actual)
- **Limpieza del commit `6c58510`:** artefacto de lectura `(Showing lines 1-63 of 480...)` que se había commiteado dentro de `PENDIENTES.md` (partía la entrada de carritos en dos) y la sección "Acceso de emergencia" insertada en el medio de esa entrada; eliminados `metodosCompletados`/`metodosCerrados` (sin uso) y los ~10 `console.log` de debug de `confirmarCierreCaja`; el manejo de error volvió a `e?.data?.detail` (`api.js` es fetch puro, no axios — `e.response` no existe)
- **13 tests nuevos** (`tests/test_caja_detalle_medio.py`, 451 en total): totales idénticos a los del arqueo (abierto y cerrado), que el efectivo no se filtre al detalle de otro medio, cuentas digitales con su propia apertura, egresos de otra sesión fuera, cierres parciales ignorados y sesión inexistente como error

### El cierre automático de caja no se podía completar: faltaba arqueo, extracción y conciliación — 01/10/2026
- **El síntoma:** al cambiar el día, `caja_service.caja_abierta()` registra el cierre de la jornada anterior con el monto que calculó el sistema, pero desde el Historial de Caja solo se podía "confirmar" un número suelto. No había forma de contar el cajón, cargar el saldo real de las cuentas digitales ni registrar la plata que se lleva. El operador se quedaba con un cierre sin conciliar y la diferencia de siempre
- **Las tres trabas, todas en el mismo lugar:** `cerrar_metodo()` exigía la caja abierta (imposible para una sesión ya cerrada), `registrar_egreso()` también, y el arqueo se armaba con `obtener_saldo_por_medio()`, que calcula "desde la última apertura" — o sea, de la sesión de hoy, no de la de ayer
- **El arqueo ahora se acota a la sesión:** `obtener_sesion_por_cierre()` camina hacia atrás desde el cierre hasta encontrar su apertura, y `_saldos_de_sesion()` suma solo lo que pasó entre esas dos. Por eso se puede conciliar aunque haya otra caja abierta: el arqueo de ayer no se mezcla con lo que se vendió hoy
- **Los movimientos que se registran para una sesión cerrada quedan "afuera" del rango** (tienen id mayor al del cierre), así que `_movimientos_de_sesion()` los reincorpora por su `referencia_id`. Sin esto, registrar la extracción hacía que el cajón esperado volviera al valor previo a extraerla y el arqueo quedara descuadrado
- **Extracción de efectivo al cerrar:** `POST /api/caja/retiro-cierre` deja el monto como egreso de la sesión (`referencia_tipo="retiro_cierre"`) y recalcula el monto esperado del cierre. Con `cierre_id` pertenece a esa sesión cerrada; sin él, a la sesión abierta. Se puede deshacer con `DELETE /api/caja/retiro-cierre/{id}`. El efecto contable es el que se pidió: extraés $25.000 de un cajón que esperaba $30.000, ahora espera $5.000 y el operador cuenta $5.000 — la diferencia real no cambia, y por eso la cuenta digital sigue cuadrando con lo que muestra la app
- **Conciliación completa desde el Historial:** el botón ✓ de las sesiones con cierre automático abre el arqueo de esa sesión (GET `/api/caja/cierre/{id}/arqueo`), deja precargado lo ya contado, exige todos los medios con saldo (`medios_pendientes`) y al confirmar archiva el resultado. Una vez conciliada la sesión es inmutable: ni arqueos ni extracciones la tocan
- **El modal de arqueo se unificó en `ArqueoMedios.vue`**, que usan tanto el cierre de la caja abierta como la conciliación diferida. Se fue la tarjeta "Cerrar por Método" suelta: cerrar un medio suelto a mitad de jornada se hacía con el arqueo del cierre final, y mantener las dos pantallas hacía que el esperado se mostrara distinto según dónde
- **Bug de UI que destapó esto:** `abrirContadorBilletes(contexto)` ignoraba su segundo argumento, así que el botón "Contar billetes" del efectivo en el arqueo abría el contador pero no escribía el total. El contexto ahora se guarda como `{ contexto, metodo }`
- **La apertura sugiere el efectivo, no el total.** El total del cierre suma las cuentas digitales, que van por su cuenta: sugerirlo como "monto inicial" mandaba al cajón una plata que nunca estuvo ahí. El cierre ahora guarda `saldo_efectivo` (columna nueva con su migración en `app/main.py`, que llenan el cierre manual y el automático)
- **Saldo de la sesión abierta:** las extracciones anotadas con `cierre_id` pertenecen a la sesión de ese cierre, así que `obtener_saldo_por_medio()` las ignora. Sin eso, conciliar la sesión de ayer le restaba esa plata al cajón de hoy
- **Tests:** 23 nuevos en `tests/test_caja_cierre_sesion.py` (250 en total), con el recorrido completo — extraer, contar, conciliar — y la garantía de que la caja de hoy queda intacta


### 502 en producción: reportlab faltaba en el venv del server — 29/09/2026
- **El síntoma:** 502 en toda la app tras el deploy manual (git pull + `systemctl restart`). En el journal: `ModuleNotFoundError: No module named 'reportlab'`, y el servicio en loop de restart (`restart counter is at 40`)
- **La cadena que se caía:** `app.main` → `app.routers.productos` → `analisis_precios_pdf` importan reportlab **duro, a nivel de módulo**. Sin reportlab, ningún import de ese árbol podía cargar, así que uvicorn no arrancaba y nginx respondía 502 en todo
- **No fue culpa del último commit:** el deploy fue frontend-only (`ec64cc3`). El servicio venía corriendo con código viejo en memoria desde antes de que existiera la ficha PDF; el primer restart lo obligó a importar todo de cero y destapó una deuda de muchos commits: `reportlab>=4.0` estaba en `requirements.txt` pero **nunca se instaló en el venv**
- **El fix inmediato** (corrido a mano en el server): `sudo -u erp bash -c 'source venv/bin/activate && pip install "reportlab>=4.0"'` + `systemctl restart erp-comercio`. Se instaló solo reportlab, no el `requirements.txt` entero, para no mover versiones de otras deps
- **El fix estructural (este commit):** una librería de PDF no puede tirar abajo el POS.
  - `analisis_precios_pdf.py` importa reportlab en `try/except ImportError`: la app arranca igual sin ella y solo la ficha PDF falla, con `ReportlabNoDisponible` que dice exactamente qué instalar y cómo reiniciar
  - Los estilos (`C_10`, `ANCHO_UTIL`, etc.) se usan como **default de argumento** en helpers, y los defaults se evalúan al importar → sin reportlab reventaban con `NameError` y la app seguía sin arrancar. Ahora valen `None` cuando falta la librería, y hay guard que lo prueba con `ImportError` simulado
  - El router traduce la falta a **503** con el mensaje accionable, no a un traceback de uvicorn
  - **3 tests nuevos** (`test_arranque_sin_reportlab.py`, 221 en total) que corren en un **subproceso** a propósito: importar `app.main` en el proceso de tests toca la DB y recargar `app.*` resetea el cache global de `lookup_service` que usan otros tests
- **`DEPLOY.md` ahora tiene el paso `pip install -r requirements.txt` obligatorio** tras el pull y antes del restart (antes no existía), más una sección de diagnóstico para 502 (dónde mirar el error real, qué significa `restart counter` y la tabla síntomas/causa/acción)

### Mini-dashboard del POS: "Ventas Hoy" en $0 con ventas en el día — 29/09/2026
- **El síntoma:** en el mini-dash del POS, `Ventas Hoy $0, 0 tickets, Ticket Prom. $0`, pero `Efectivo`, `Cajón` y `Cuentas digitales` con montos reales. El usuario reportó que quedó así "después de algún deploy"
- **El porqué es un síntoma que engaña:** el mini-dash arma 3 KPIs desde `/api/dashboard/resumen` y los 3 restantes desde `/api/caja/*`. Como `fetchPOSStats` atrapa el error **por endpoint** (`.catch(() => null)`), si el endpoint de dashboard devolvía datos "vacíos" solo se veían en cero las ventas; los de caja seguían andando. No era la caja la que estaba mal
- **La causa real (zona horaria, no un crash):** el dashboard cortaba "el día" a medianoche **UTC** (`_inicio_dia()` truncaba `datetime.now(timezone.utc)`), mientras los `fecha` de las ventas se guardan en UTC. En Argentina (UTC-3) el día UTC empieza a las **21:00 local**: a las 22:04 local del 29/09 (que en UTC ya es 30/09 01:04) el "hoy" del dashboard llevaba 1 hora de vida, así que todas las ventas del día quedaban fuera de `ventas_hoy`. Con el 502/health del día siguiente los KPIs de caja sí mostraban el acumulado local. Se reprodujo con un script local contra DB limpia: el endpoint anda bien; el límite de día estaba mal
- **El fix (este commit):** el "día" de negocio ahora es la **zona horaria Argentina (UTC-3)**, igual que el cierre de caja (`caja_service` ya tenía `TZ_AR`). Los 4 helpers `_inicio_dia/_inicio_mes/_inicio_semana/_inicio_trimestre` computan el corte en hora local y convierten a UTC para comparar contra la DB, y `/api/dashboard/trimestral` usa el trimestre local también. Afecta a `ventas_hoy`, tickets, ticket promedio, margen hoy, alertas de "ventas anuladas hoy" y al reporte trimestral
- **6 tests nuevos** (`test_dashboard_dia_local.py`, 227 en total): el caso exacto reportado (22:00 local = día siguiente en UTC cae en el mismo "hoy"), medianoche local arranca día nuevo, mes/trimestre locales, y una integración de `resumen()` con ventas de la mañana y de la noche en DB en memoria

### El carrito del POS se perdia al cambiar de tab, y no habia forma de tener varios carritos a la vez — 29/09/2026
- **El carrito se perdia al navegar.** `cart` era un `reactive()` declarado adentro de `POSView`, sin `keep-alive` en el router. Al ir a la tab de Productos, Vue destruia el componente y el carrito con el. No era un bug de sincronizacion: el carrito nunca existio fuera de esa pantalla. Ahora vive en un store de Pinia y sobrevive al route change y al F5
- **No se podian tener dos carritos abiertos.** El "Hold" que existia guardaba y **vacia**, y recuperar se negaba si el carrito actual no estaba vacio. Servia para liberar la pantalla, no para atender a dos personas
- **Se unifico todo en carritos con nombre.** "Mesa 1", "Mesa 2" y "Mostrador" son carritos con nombre, no una entidad nueva. Apartar y recuperar quedan subsumidos: cambiar de carrito ya guarda el anterior solo
- **Al vaciar un carrito sobrevive el nombre**, que es lo que sirve para una mesa que sigue abierta
- **Al editar una venta** que ya estaba cobrada, si el carrito activo tenia algo sin cobrar se aparta antes con el sufijo "(sin cobrar)", para no pisarlo
- **Al cerrar la caja** ahora se listan los carritos con productos sin cobrar, con nombre, items y total, en vez de un conteo generico de "tickets apartados"
- **Se conserva la migracion de los tickets apartados** de la version anterior: se importan una sola vez como "Apartado 1", "Apartado 2", etc. Quien los use no pierde nada
- **Se conserva la auditoria** en la misma clave, con los eventos `HOLD`, `RENAME`, `CLOSE`, `DELETE_HELD`, `RECALL` y ahora `ORPHAN`

- **Store defensivo:** normaliza lo que lee de localStorage. Un `items` que no es array, un `total` no numerico o un `activoId` colgado se corrigen en vez de romper el POS
- **`useHeldTickets.js` eliminado.** Sus dos consumidores (POSView y CajaView) ahora usan el store, asi que hay una sola fuente de verdad
- **45 verificaciones** del store en Node (credenciales para no perder carritos, persistencia, migracion, datos corruptos, sospechosos, auditoria). No se commitearon porque el frontend no tiene arnes de tests
- **Limite conocido:** los carritos viven en localStorage, no en el servidor. No sobreviven cambiar de terminal. Si alguna vez hace falta que dos terminales compartan carritos, hay que backend + tabla

### Acceso de emergencia sin Oracle Cloud Console: Serial Console (Console Connection) — 08/10/2026
- **Problema:** El servidor se "clava" (freeze), SSH no responde, Oracle Cloud Console inaccesible (credenciales perdidas/soporte no responde). El operador queda ciego sin poder reiniciar ni ver logs.
- **Solución:** **Console Connection (Serial Console)** — acceso directo al kernel via puerto serial (ttyS0), independiente de SSH, systemd, networkd, firewall, Oracle Cloud Console web.
- **Configuración (5 min, una sola vez):**
  1. `ssh-keygen -t ed25519 -f ~/.ssh/oracle-emergency -N ""`
  2. Oracle Console → Instance → Console Connections → Create → SSH Key → pega `~/.ssh/oracle-emergency.pub`
  3. Guarda el comando SSH que te den en `~/emergency-ssh.sh`
- **Uso:** `~/emergency-ssh.sh` → acceso directo al kernel (ttyS0) aunque SSH caiga, kernel panic, etc. Funciona sin password, sin Oracle Console, sin SSH daemon.
- **Fix preventivo:** Watchdog automático (`/etc/watchdog.conf` + health endpoint `/health`) + monitoreo externo (UptimeRobot gratis) + script `~/emergencia.sh` con todas las opciones de recuperación.

### Carrefour Maxi (comerciante.carrefour.com.ar): el sitio es B2B con login, no sirve como fuente — 29/09/2026
- **Se investigo** el portal de compras por volumen de Carrefour, que tiene precios distintos y a veces mejores que el de consumo
- **El catalogo se puede leer por API** (`GET /products?method=productsList&currentUrl=...`): trae EAN, nombre y sector
- **Los precios no.** En los 12 productos que devuelve la búsqueda el atributo viene literalmente como `data-price="private"`, y la página de producto no tiene precio. El sitio lo dice en pantalla: "Te pedimos por favor que ingreses tus datos para poder ver el precio y stock disponible"
- **No se implemento, y no es un bug pendiente:** es un portal B2B con acceso por cuenta, no un obstáculo técnico. Agregarlo exigiría una cuenta de comercio mayorista y guardar credenciales, que es otra decisión
- **De paso se arreglo un bug general que ese sitio destapo:** el scraper pedía `Accept-Encoding: br` y `brotli` no esta instalado, asi que cuando un servidor responde brotli `requests` NO lo descomprime ni tira error, devuelve los bytes crudos. Cualquier sitio que respondiera brotli nos daba basura en silencio, con un error de parseo que no decia nada del Encoding. Ahora se pide `gzip, deflate`
- **3 tests nuevos** (218 en total) para que ninguna fuente vuelva a pedir brotli

### Las promos por cantidad de MasOnline no se detectaban: no estan en el HTML — 29/09/2026
- **Por qué:** el codigo esta hecho para detectar promociones, ofertas y descuentos, y en MasOnline seguia reportando el precio de lista. La Coca Zero de la URL de arriba devolvia $5.899 cuando en 3x2 sale $3.932,86
- **Causa raíz:** no es un bug de parseo, es que la promo **no esta en ningun lado del HTML**. El precio se arma por JS (`priceBehavior: "async"`), el HTML no lo renderiza, y en el estado de VTEX el offer llega con `teasers: []` y `discountHighlights: []` vacios, con `price == priceWithoutDiscount`. No hay nada que parsear
- **La unica fuente es la simulacion de carrito** (`GET /api/checkout/pub/orderForms/simulation`), que devuelve el precio por unidad ya con la promo aplicada segun la cantidad. Ahi se ve que baja recien en 3
- **A diferencia de Vea**, que ya publica el precio descontado en el JSON-LD. Mismo grupo, distinta implementacion
- **El precio de una unidad no baja:** 3932.86 es lo que se paga comprando 3. Por eso va `cantidad_minima` en la respuesta y la card y el PDF lo dicen. Sin eso, un 3x2 se lee como una bajada de precio que no existe para quien compra una
- **Se usa el precio que devuelve la simulacion, no `lista * 2/3`**: la cuenta da 3932.67 y VTEX devuelve 3932.86
- **No se consulta el carrito para todo.** Solo si el producto no tiene ya descuento del JSON-LD y esta en un cluster con multi-compra explicito (`3x2- Bebidas`, no `Oferta` ni `- OP`). Medido: bebidas 7/8 pasan el filtro, pero limpieza, panaderia y alimentos dan 0/5, o sea el gasto extra se concentra donde estan las promos
- **43 tests nuevos** (215 en total), con la pagina real como fixture
- **Pendiente:** solo se simulan cantidades 2 y 3, asi que un 6x5 se escapa. Si aparece alguna, se suman en `_CANTIDADES_MASCULINAS`

### Las promos de Vea/MasOnline nunca se detectaron: se leia el precio de lista — 29/09/2026
- **Por qué:** el código de barras está pensado para detectar promociones, ofertas y descuentos, pero en la práctica no lo hacía. Reportaba el precio **sin** promo y encima marcaba `activo: True` con los dos precios en `None`, o sea un badge de oferta con los números vacíos
- **Causa raíz:** Vea/MasOnline emiten **dos bloques JSON-LD del mismo producto**. El primero trae `offers.lowPrice` = precio **de lista**. El de `id="structured-data-schema"` trae `offers.price` = lo que se paga por unidad **con la promo aplicada**, más `priceSpecification.price` (lista) y `priceValidUntil` (vigencia). `_extract_json_ld` devolvía el primer bloque que parseaba, así que nunca veía el bueno
- **Verificado contra la página real** (Coca Cola Zero 2,25 L): `offers.price` = **3926.67**, `priceSpecification.price` = 5890. $5.890 × 2/3 = $3.926,67 → es una **3x2**, tal cual se ve en el artículo
- **Arreglo:** `_extract_json_ld` puntúa los bloques y gana el correcto (`_puntaje_json_ld`), así que el orden en la página deja de importar. El descuento sale de `_descuento_de_json_ld` (JSON-LD), y el estado de VTEX queda solo como fallback
- **La etiqueta de multi-compra se deduce del ratio exacto**: 2x1, 3x2 y 4x3. Un descuento común (5890 → 5000) no matchea ninguna proporción y queda sin etiqueta, que es lo correcto
- **Corregido también el estado imposible:** un descuento sin los dos precios ya no se marca como activo, y la card muestra la lista tachada, el ahorro en pesos y la vigencia ("hasta el 01/10")
- **Comprobado con red sobre 6 productos reales de la sección bebidas: 4 tienen promo**, detectadas las cuatro (2 de ellas con etiqueta de multi-compra)
- **26 tests nuevos** (167 en total), con la página real guardada como fixture en `tests/fixtures/vea_promo_real.html` (solo los bloques ld+json, no los 3 MB de HTML)
- **Pendiente:** el mismo análisis para **Carrefour** y **MasOnline**, que pueden tener la estructura de oferta distinta a la de Vea. Y sigue abierta la pregunta de si el barcode matchea siempre el mismo producto entre fuentes

### Validación con red real: 3 de 4 fuentes andan, Supercoco marcada experimental — 29/09/2026

- **Por qué:** los tests corren con `sin_red`, o sea que el scraping llevaba commits entero sin verificarse contra los sitios reales. Con red se probaron 6 EAN-13 extraídos de la home de Vea
- **`vea`, `masonline` y `carrefour` funcionan**: devuelven precios, ordenan y detectan ofertas. 2-3 resultados por código, ~9 s por búsqueda
- **Supercoco devuelve 0 siempre, y no es un bug de parseo**: la página de búsqueda renderiza por JavaScript y devuelve el mismo HTML (~393 KB) para cualquier consulta, sin los productos adentro. El parser busca algo que el documento nunca va a traer. La API estilo VTEX da 404 y no hay `__PRELOADED` / `__NEXT_DATA__` / `__NUXT__`
- **Quedó activa, marcada `(experimental)`**, no apagada: apagarla esconde el síntoma en vez de documentarlo. El nombre en pantalla, en el PDF y en el payload (`nombre_fuente`) avisa que el precio no es confiable, y la card suma un aviso "el precio puede no corresponder al mismo producto"
- **`FUENTES` pasó de lista a registro** con nombre canónico y flag `experimental`. El nombre vive en el backend: antes estaba duplicado en el frontend y el PDF hacía `str(fuente).upper()` → "SUPERCOO"
- **Nuevo `SCRAPER_FUENTES_OFF`**: apagar una fuente que rompió no obliga a tocar código ni redeploy. Hay tests de que una fuente apagada no genera ni un request
- **Pendiente para cuando haya tiempo:** el fetch de Supercoco contra la llamada real (pide DevTools), y **el desajuste de precios y nombres entre fuentes** — para `7797750980852`, Vea y Carrefour dan $999.999 pero MasOnline $679.999, y los títulos difieren bastante para el mismo código. Si dos fuentes matchean productos distintos, "el más barato online" compara cosas distintas

### Análisis de Compra: lo que pagaste, a quién y cuándo salió más barato — 29/09/2026
- **Por que:** `/precios-online` decía "acá está más barato" online, pero no contestaba la pregunta que de verdad importa al comprar: **¿cuánto pagué yo la última vez, a quién, y cuándo fue que más barato?** El dato existía (compras + `producto_proveedor`), nunca se había mostrado junto a los precios online
- **`app/services/analisis_precios_service.py`**: historial de compras del producto, costo de lista actual por proveedor, último precio pagado a cada uno, mejor costo histórico **con proveedor y fecha**, ahorro contra la referencia y margen con el precio online más bajo
- **Sin tabla nueva.** El historial sale de `compras` + `compra_items`. Migración: ninguna
- **Las compras anuladas quedan excluidas** (`ESTADOS_VALIDOS = ("recibida", "parcial")`): si no, una compra cancelada figuraría como "el precio más bajo que jamás conseguiste" y la pantalla perdería credibilidad al primer dato raro. Las `pendiente` se ignoran porque todavía no se pagó nada
- **Ficha PDF** (`analisis_precios_pdf.py`, ReportLab, A4 horizontal) con la fila más barata resaltada en cada tabla. Landscape porque en vertical el historial se parte en 3 páginas. Empieza con una frase de recomendación, que es lo primero que se lee
- **38 tests nuevos** (125 en total): orden del historial, exclusión de anuladas, que una anulada no pueda ser el "mejor precio", proveedor/fecha del mínimo, productos sin historial, y que el PDF renderice con y sin datos, escapando `&`/`<`/`>`
- **Bug encontrado al escribir los tests:** `db.query(Entidad, tabla_core)` **aplana la tabla Core a sus columnas**: la fila devolvía 11 valores en vez de 2 y el `for proveedor, vinculo in filas` tiraba `ValueError: too many values to unpack`. Resuelto con `select()` de columnas explícitas

### Tests de los 4 scrapers + 3 bugs que rompian en silencio — 29/09/2026
- **Por que:** el scraping es la unica parte del ERP que puede fallar **sin fallar visiblemente**. Si Carrefour cambia su markup, `comparar_precios` devuelve `[]` y la pantalla dice "no lo encontramos", indistinguible de "el producto no esta en esa tienda". El resto del ERP es SQL CRUD donde un error se ve al instante. El repo no tenia **ningun** test
- **Refactor fetch/parse** en `lookup_service.py`, sin cambiar comportamiento: `_lookup_supercoco` / `_lookup_carrefour_api` / `_scrape_fuente` hacen red; `_parse_supercoco` / `_parse_carrefour` / `_parse_vea` parsean y son testeables
- **81 tests** en `tests/`: parseo de las 4 fuentes, cableado fetch->parse con `requests.get` simulado, TTL de caché, orden de precios, y casos límite
- **Fixture autouse `sin_red`** que bloquea cualquier socket: la suite corre en 0.47s y por construcción no puede pegarle a Carrefour/Vea — si lo hiciera, quemaría el rate limit de las fuentes a las que les scrapeamos todos los días
- `requirements-dev.txt` separado para que **pytest no entre al deploy** del servidor

**Bugs reales que aparecieron al escribir los tests:**

1. **Llaves dentro de strings JSON desbalanceaban el parser.** `_extract_state` contaba `{` y `}` a ciegas. Una descripción de producto con `{}` adentro (ej. "envase de 1 kg {sellado}") cerraba el objeto antes de tiempo, `json.loads` fallaba y **el scrape entero devolvía `None`**. Reemplazado por `_scan_json_object`, que ignora llaves dentro de strings y respeta escapes
2. **El regex de Super Coco cortaba en la primera `}...)`.** Con `(\{.*?\})\s*\)` no-greedy, cualquier `})` dentro de un string del payload (ej. "pack de 2 })") truncaba el JSON y la fuente devolvía `None` para siempre. Ahora usa el mismo scanner balanceado
3. **El botón "Ver en Super Coco" llevaba a la página de búsqueda, no al producto.** `url` era la `search_url`; ahora se arma con el `slug` del payload

Además, dos guards defensivos: `_clean_name` y `_map_categoria` reventaban con `AttributeError` si VTEX cambiaba `categories` de lista de strings a lista de dicts (mismo error, dos funciones).

- **Pendiente:** la tabla de `_map_categoria` no cubre segmentos compuestos como "Café molido", así que el café cae en una categoría propia en vez de "Almacén". Documentado en `test_categoria_usa_el_ultimo_segmento`, pero decidirlo es вопрос de producto

### Gatear el scraping + single-flight — 29/09/2026
- **Mi propuesta original era incorrecta y la corregí antes de tocar código.** Iba a gatear los 2 endpoints que disparan scraping con `require_role`. Al implementarlo encontré que `POST /api/productos/lookup` lo llaman **POS, Compras, Cobro Móvil y Productos**, y que las ventas son `require_role("admin", "cajero")` → gateearlo sin cajero **rompía el POS**, que es la caja. Además el sistema tiene exactamente 4 roles, así que un `require_role` con los 4 es idéntico a `get_current_user`: cero valor de seguridad
- **Lo que sí quedó:** `GET /api/productos/precios-online/{barcode}` gateado a `admin, encargado, repositor`, los mismos roles que la tab en `TheSidebar` y en el `meta` del router. El cajero no tiene UI para esa pantalla
- **La defensa real es mecánica, no por roles:** `threading.Semaphore(SCRAPER_MAX_CONCURRENT=8)` para acotar el scraping saliente
- **Single-flight por `(fuente, barcode)`:** la caché sola no cubría el *stampede* — N requests del mismo barcode al mismo tiempo fallaban la caché a la vez y **los N salían a scrapear**. Con lock por clave, 6 requests simultáneos hacen **1** scrape y los otros 5 leen la caché. Hay test de concurrencia con threads reales que lo verifica
- Los locks se liberan en `finally` (no se acumulan si el scrape revienta) y hay test de que el dict queda vacío tras 50 barcodes

### Precios Online: la pantalla no mostraba precios + caché de scraping — 29/09/2026
- **Bug crítico:** la vista leía `r.precio_referencia || r.precio_venta`, pero `comparar_precios` devuelve el campo `precio` → **todos los precios online salían como "—"** y el bloque "Precio más bajo" nunca se renderizaba (su computed siempre daba `null`)
- **Bug crítico:** las 3 llamadas iban dentro de un solo `try`. El 404 de `POST /api/productos/lookup` (cuando el producto no está en la BD local) cortaba la cadena **antes** de `GET /precios-online` → no se comparaba nada, que es justamente el caso de uso principal. Ahora cada paso tiene su propio `try` y el 404 se trata como información ("no está en tu catálogo"), no como error
- **Datos que ya se scrapeaban y se descartaban:** `comparar_precios` sacaba `marca` e `imagen_url` de los resultados aunque `_scrape_producto` ya las tenía → ahora se incluyen
- **Caché de scraping** (`lookup_service.py`): se cachea por `(fuente, barcode)` porque una búsqueda disparaba hasta 3 rondas completas de scraping (`/lookup` compara precios internamente y la vista además llama a `/precios-online`). 4 fuentes secuenciales con timeout de 20 s podían tardar ~135 s
  - Aciertos: 15 min · **fracasos: 120 s** (si no, un timeout de red quedaba cacheado como "no encontrado" 15 minutos)
  - `threading.Lock`, purga al superar 500 entradas, TTL configurable con `SCRAPER_CACHE_TTL`
  - El timeout ahora sale de `settings.SCRAPER_TIMEOUT` en vez de estar hardcodeado (15/20) en cada scraper
- **Orden y highlights:** resultados ordenados de menor a mayor; la fila más barata con fondo verde + badge "Más barato"
- **KPIs de decisión de compra** (solo si el producto está en el catálogo local y hay resultados): precio de venta local, mejor precio online y **ganancia por unidad** (`precio_local - mejor_precio`). El backend ahora manda `diferencia_vs_local` y `porcentaje_vs_local` por resultado
- **Fix de badges:** `BaseBadge` recibía clases Tailwind (`bg-blue-500`) en `variant` en vez de un variant válido → los badges de fuente salían sin color. Ahora cada fuente tiene su variant (`info`/`danger`/`success`/`brand`)
- **Fix de clave de fuente:** el mapa tenía `masonline` pero el backend devuelve `masonline` → caía al fallback y mostraba el nombre crudo sin icono ni color
- **UX:** modo dark completo (58 clases `dark:`), skeletons en vez de spinners manuales, guard de reentrada (doble clic ya no dispara dos búsquedas), `window.open` con `noopener,noreferrer`, reuso de `formatDateShort` en vez de `formatFecha` duplicado, key por fuente en vez de por índice, handlers en línea extraídos a funciones
- **Convención:** 0 `console.error`, 0 comentarios HTML, toasts con el `detail` real del backend (`e?.data?.detail || e.message`) en vez de mensajes genéricos
- **Backend:** imports function-local redundantes eliminados; `GET /api/proveedores/{id}/productos` ahora usa `_suma_lotes_activos()` — antes devolvía la columna legacy y el modal mostraba un stock distinto al de la card "Stock Bajo" de la misma pantalla
- **Verificado:** caché (0 scrapes extra en la 2ª llamada), TTL positivo/negativo, orden por precio, `marca`/`imagen_url` presentes, `diferencia_vs_local` / `porcentaje_vs_local` / URL de fallback, y que sin producto local no se inventen diferencias
- **Pendiente:** ninguno de esta feature

### Control de stock opcional + reporte de vendido por peso — 29/09/2026
- **Nuevo campo `controla_stock` en productos** (default `True`, así nada cambia para los productos existentes):
  - Desactivado → vender **no** descuenta lotes, **no** genera `MovimientoStock` y **no** marca déficit; `anular_venta()` tampoco reingresa
  - Ideal para fraccionados (panadería, fiambre): el stock en kg se desincroniza solo, lo que interesa es lo vendido
  - Sigue guardando `peso` y `subtotal` de cada venta, así el análisis no se pierde
- **Migración:** `ALTER TABLE productos ADD COLUMN controla_stock BOOLEAN NOT NULL DEFAULT 1` + índice, en `_migrate_new_columns()` (`app/main.py`)
- **Backend:** campo en `ProductoBase`/`ProductoUpdate`/`ProductoOut`/`ProductoLookupResponse`, editable en `actualizar_producto()`; `GET /api/productos/stock-bajo` excluye los productos sin control
- **UI:** toggle "Controlar stock" en el modal de producto; badge `s/ctrl` en la tabla de Productos y en la grilla del POS; el POS no avisa "stock insuficiente" ni marca `_revision` en estos productos; los filtros y contadores "Stock bajo"/"Sin stock" los excluyen
- **Reporte nuevo "Vendido por Peso"** en `ReportesView.vue` (full width, antes de Stock por Lote): rango de fechas (últimos 30 días por defecto), KPIs de $ / kg / operaciones / productos, tabla por producto con kg, rango min–max, precio promedio por kg, operaciones e importe, y pie con totales
- **Endpoint nuevo** `GET /api/reportes/vendido-por-peso?desde=&hasta=&producto_id=` (`app/routers/reportes.py`, primer router de reportes, registrado en `app/main.py`). Cualquier usuario autenticado; solo ítems `por_kilo` de ventas **confirmadas** (anuladas y pendientes fuera)
- **Tests:** migración sobre base vieja (productos existentes quedan en 1), venta por kg sin control no mueve stock ni marca déficit, con control descuenta bien, anulación no reingresa de más, reporte agrega solo confirmadas y rechaza fechas inválidas
- **Pendiente:** replicar el campo Importe en `CobroMovilView.vue`; el flujo offline (`useOfflineSales.js`) sigue sin persistir items (ver abajo)

### Cobro por importe en productos fraccionados (panadería) — 29/09/2026
- **Problema:** en productos por kilo solo se podía cargar el peso, y con 2 decimales el subtotal redondeaba (0,333 kg × $3.000 = $999 en vez de $1.000)
- **Nuevo campo "Importe" ($)** en cada item por kilo del carrito del POS: se tipea lo que se cobra y el peso se calcula solo (`importe / precio_por_kilo`, 3 decimales)
  - Los dos campos quedan sincronizados: escribir el peso deriva el importe, escribir el importe recalcula el peso
  - El subtotal de la línea usa el importe tipeado, así el total y el ticket cuadran con lo cobrado
- **Backend:** `POST /api/ventas/{id}/items` acepta `importe`; si viene, el `subtotal` es ese importe exacto y el `peso` se recalcula. `precio_unitario` sigue siendo el precio de lista por kg (no se distorsiona el análisis)
- **Análisis:** `_venta_to_dict` ahora devuelve `por_kilo` y `peso` en cada ítem (antes no venían), y el ticket muestra los kg en la columna Cant
- **Pendiente:** replicar el campo Importe en `CobroMovilView.vue` (misma lógica de kg, hoy solo peso)

### Denominaciones de efectivo configurables desde Ajustes — 29/09/2026
- Las denominaciones del contador de caja dejan de estar hardcodeadas: ahora se administran en **Ajustes → Denominaciones de Efectivo**
- **Nueva tabla `denominaciones`** (`valor` único, `tipo` = billete/moneda, `activo`) + `app/services/denominacion_service.py` con la lista por defecto de Argentina
  - Siembra automática: `_seed_denominaciones()` en `app/main.py` (la tabla la crea `create_all`, no hace falta migración manual)
- **Endpoints nuevos** en `app/routers/denominaciones.py`:
  - `GET /api/denominaciones?incluir_inactivas=` — cualquier usuario autenticado (lo consume el contador, que también usan los cajeros)
  - `POST`, `PUT /{id}`, `DELETE /{id}` y `POST /restaurar-defaults` — solo `admin`
  - Validaciones: valor > 0, sin denominaciones duplicadas, tipo válido
- **UI en `AjustesView.vue`:** tarjeta colapsable con una fila por denominación (valor editable, select Billete/Moneda, toggle habilitar/deshabilitar, quitar), botón "Agregar denominación", "Restaurar por defecto" y "Guardar" (borrados +actualizados +nuevos en una sola acción)
- **`ContadorBilletesModal.vue`:** carga las habilitadas al abrir, separa billetes/monedas, y si no cubren todo el monto avisa cuánto quedó sin asignar; fallback a la lista por defecto si la API falla
- Deshabilitar una denominación la saca del contador sin borrarla de la configuración

### Contador de billetes por denominación (efectivo) — 29/09/2026
- Nuevo componente `frontend/src/components/caja/ContadorBilletesModal.vue`: conteo por denominación con auto-suma
- Denominaciones AR: billetes $100.000 / $50.000 / $20.000 / $10.000 / $5.000 / $2.000 / $1.000 y monedas $500 / $200 / $100 / $50 / $20 / $10 / $5 / $1
- Botón "Contar billetes" en los 3 puntos de carga de efectivo de `CajaView.vue`:
  - Modal **Apertura de Caja** → escribe en `monto_inicial`
  - **Cerrar por Método** (cuando el método es efectivo) → escribe en `monto_real`
  - Modal **Cierre de Caja (Arqueo)** → escribe en el Monto Real del método efectivo
- UX: precarga greedy del monto ya cargado, subtotales por fila, total con piezas + total billetes + total monedas, botón "Limpiar", `Esc` cierra solo el modal de conteo
- **Solo frontend**: el total se escribe en los campos existentes, sin cambios de API ni migraciones
- **Pendiente opcional:** replicar el botón en el modal de Apertura del POS (`POSView.vue`) y en el de CobroMovil (`CobroMovilView.vue`)

### Fix Arqueo de Caja — 14/09/2026
- **Bug:** al cerrar caja daba error "método ya fue cerrado en esta sesión" cuando en realidad no había cierre previo (tomaba `cierre_parcial` de sesiones anteriores como de la sesión actual)
- **Fix backend (`caja_service.py`):**
  - `cerrar_metodo()`: el chequeo de sesión ahora camina desde el `cierre_parcial` hacia registros más viejos (apertura/cierre total) en vez de desde el más nuevo
  - `obtener_resumen_por_medio_pago()`: ahora cuenta solo la sesión actual (antes sumaba ventas de todas las sesiones) y `total_egresos` ya no devolvía siempre 0
- **Fix frontend (`CajaView.vue`):** confirmación explícita al cerrar sin montos en ningún método + `fetchEstado()` al cerrar o ante error para no quedar con estado desactualizado

### Precarga de Código de Barras en Nuevo Producto — 11/08/2026
- Mejora en el flujo de creación de productos:
  - Al escanear un código en el buscador de productos y no encontrar resultados, al hacer clic en "Nuevo Producto" se precarga automáticamente el código escaneado en el modal
  - El botón "Nuevo Producto" ahora pasa el código buscado (si existe) al modal de creación
  - Facilita el flujo de trabajo con lector de código de barras: escanear → no encontrado → nuevo producto → código ya cargado

### SmartPoint como Medio de Pago — 11/08/2026
- Agregado "SmartPoint" como nuevo medio de pago en el POS de ventas
- Seleccionable en la grilla de medios de pago (ahora 6 opciones en lugar de 5)
- Funciona como medio de pago directo sin integración con API (para dispositivos físicos prestados)
- Atajo de teclado actualizado: tecla 6 para seleccionar SmartPoint
- Las ventas con SmartPoint se registran normalmente en el sistema sin flujo especial de pago

### Precios Online con Info de Proveedores — 10/08/2026
- **Mejora en vista "Precios Online":**
  - Al buscar un producto local, ahora muestra info detallada:
    - **Última fecha de compra** (con número de orden)
    - **Lista de proveedores** con costo y badge "Principal"
    - Al hacer clic en un proveedor → modal con todos sus productos asociados
  - Backend: nuevo endpoint `GET /api/productos/{id}/info-detallada`
  - Backend: nuevo endpoint `GET /api/proveedores/{id}/productos`
  - Al hacer clic en un producto del modal del proveedor, busca precios online automáticamente

### Precios Online con Stock Bajo — 10/08/2026
- **Mejora en vista "Precios Online":**
  - Nuevo botón "Stock Bajo" que muestra productos sin stock o con stock mínimo
  - Lista de productos con stock bajo con imagen, nombre, marca, código de barras, stock actual/mínimo y precio local
  - Al hacer clic en un producto de la lista, busca automáticamente los precios online
  - Backend: nuevo endpoint `GET /api/productos/stock-bajo` que devuelve productos con stock <= stock_minimo o sin stock
  - Ordenados por stock ascendente (los más urgentes primero)

### Precios Online — 10/08/2026
- **Nueva vista "Precios Online"** para comparar precios en supermercados online
- **Backend:**
  - Nuevo endpoint `GET /api/productos/precios-online/{barcode}` que busca en todas las fuentes externas (Carrefour, Vea, Mas Online, Super Coco)
  - Devuelve precios, nombres, imágenes y URLs directas a cada fuente
- **Frontend:**
  - Nueva vista `PreciosOnlineView.vue` con búsqueda por código de barras
  - Muestra info del producto local si existe (nombre, marca, precio, stock)
  - Lista de precios online con imágenes, precios y badges de fuente
  - Destaca el precio más bajo en verde
  - Botón "Ver en [fuente]" que abre la URL directa del producto en el supermercado
  - Soporte para descuentos/ofertas visibles
- **Sidebar:** nuevo tab "Precios Online" entre Compras y Proveedores

### Reportes de Caja (Historial de Sesiones) — 10/08/2026
- **Backend:**
  - Nuevo endpoint `GET /api/caja/reportes` con filtros por fecha (fecha_inicio, fecha_fin)
  - Agrupa movimientos en sesiones (apertura → cierre)
  - Calcula totales de ingresos/egresos por sesión
  - Detecta discrepancias en cierres por método (esperado vs real)
  - Incluye información de cierres automáticos
- **Frontend:**
  - Nueva sección "Historial de Caja" en CajaView
  - Filtros rápidos: Hoy, Semana, Mes, Personalizado
  - Tabla con sesiones: fecha, usuario, apertura, cierre, ingresos, egresos, estado, discrepancias
  - Badges para cierres automáticos y sesiones con discrepancias
  - Modal de detalle con:
    - Info de apertura y cierre (fechas, usuarios, montos, descripciones)
    - Resumen: total ingresos, egresos, saldo final
    - Cierres por método con expected vs real vs diferencia
    - Lista de movimientos (ingresos y egresos) con descripciones

### Mejoras de Caja (Apertura/Cierre) — 10/08/2026
- **Cierre automático con saldo real:**
  - Backend calcula saldo actual antes de cerrar automáticamente
  - Usa zona horaria Argentina (UTC-3) para determinar el "día"
  - Descripción incluye fecha del día que corresponde
- **Nuevo endpoint `/api/caja/ultimo-cierre`:**
  - Devuelve monto, fecha (UTC y local), si fue automático
- **Apertura mejorada:**
  - Modal con monto inicial sugerido (del último cierre)
  - Campo opcional para retiro de efectivo
  - Campo para motivo del retiro
  - Cálculo reactivo: monto final = inicial - retiro
  - Si hay retiro, crea egreso automáticamente vinculado a la apertura
- **Fix botón login bloqueado:**
  - `loggingIn` se reseteaba solo en error, no en éxito
  - Ahora se resetea en ambos casos

### Sincronización entre POS y Products — 10/08/2026
- **Store Pinia de productos:**
  - Nuevo store `productos.js` con `productos`, `categorias`, `ofertas`
  - Funciones: `fetchAll`, `refreshProductos`, `refreshOfertas`
- **POSView y ProductsView usan el store compartido:**
  - Después de confirmar venta en POS → `productosStore.refreshProductos()`
  - Después de guardar/eliminar producto → refresh del store
  - Ambas vistas ven los cambios inmediatamente
- **Fix reactividad:**
  - Cambiado de `storeToRefs` a `computed` properties para mejor reactividad después de logout/login

### POS: buscador de texto null-safe — 10/08/2026
- El buscador de texto en POS fallaba silenciosamente con campos null (marca/codigo_barras)
- Fix: usar `(p.marca || '').toLowerCase()` en lugar de `p.marca.toLowerCase()`

### POS: lookup de barcode devolvía precio en blanco — 10/08/2026
- `POST /api/productos/lookup` omitía `precio_venta` y `stock_actual` cuando encontraba producto local
- El POS interpretaba `precio_referencia` (null/0) como precio_venta=0 y mostraba panel de carga manual
- Fix: schema `ProductoLookupResponse` ahora expone `id`, `precio_venta`, `stock_actual`
- Frontend: si el lookup devuelve `id` (producto real en DB), auto-agrega al carrito
- POS `onMounted` ahora pide `page_size=200` para que la mayoría de productos queden en caché local

### BaseModal scroll fix — 10/08/2026
- `frontend/src/components/ui/BaseModal.vue`:
  - `max-height: calc(100vh - 3rem)` en el contenedor (deja margen para el `py-6` del wrapper)
  - `flex flex-col` con header `shrink-0` y body `overflow-y-auto flex-1 min-h-0` (el `min-h-0` es clave para que flex children puedan shrinkear y permitir scroll)
  - Nuevo `<slot name="footer">` con border-top y bg distinto para botones fijos abajo
- `frontend/src/views/ProductsView.vue`: movidos los botones Cancelar/Crear al footer slot del modal de producto y del modal de oferta (siempre visibles al scrollear). Submit pasa a `@click.prevent` (botón fuera del form).

### ProductsView bug fix + UX — 10/08/2026
- **Bug real del buscador:** cuando la API devolvía campos con tipo raro (BigInt/Number/Object), `(p.nombre || '').toLowerCase()` tiraba TypeError. Vue 3 en computeds que lanzan excepción mantiene el valor anterior sin re-renderizar → parecía que el filtro "no aplicaba".
- Fix: helper `safeStr(v)` que convierte cualquier tipo a string limpio, `Number(v)` para campos numéricos, todos los filtros blindados con `if (!p) return false`. Wrap de `filteredProducts` y `tableRows` en try/catch que loggea y devuelve fallback sensato. Cambiados `} catch {}` por `} catch (err) { console.error(...) }` en `fetchProductsData` y `syncProducts`.
- UX: debounce 200ms en searchInput → searchQuery, botón X para limpiar, búsqueda ahora en 5 campos (nombre, marca, código, **categoría**, **observaciones**), filtros independientes (sin exclusión mutua), botón "Limpiar filtros" con badge de cantidad + "N filtros activos" en el contador.

### Lotes + FEFO (MVP + UI rica) — 09/08/2026
**Decisiones de diseño cerradas:** todos los productos usan lotes · 1 lote por item en recepción · FEFO automático en ventas/ajustes/anulación · `fecha_vencimiento` vive solo en lote (se elimina del producto).

**Backend:**
- Modelos: `Lote` (producto_id, codigo_lote, fecha_fabricacion, fecha_vencimiento, cantidad_inicial/actual, costo, activo, notas, compra_id, compra_item_id) y `VentaItemLote` (trazabilidad por item — un item puede consumir de varios lotes)
- `MovimientoStock.lote_id` para vincular movimientos a lote específico
- Migración auto al arrancar: cada producto con `stock_actual > 0` recibe un "Lote inicial" (sin vencimiento, costo=precio_costo) para preservar el stock preexistente
- `lote_service.py`: CRUD, FEFO (`descontar_fefo`, `reingresar_en_lote`), alertas (`lotes_por_vencer`, `lotes_vencidos`), resumen por producto
- `stock_service.ajustar_stock_por_lote()`: entradas crean lote "AJUSTE", salidas aplican FEFO
- `venta_service.confirmar_venta()`: usa FEFO y registra `VentaItemLote` por item
- `venta_service.anular_venta()`: revierte consumo lote por lote
- `compra_service.recibir_compra()`: crea lote con `fecha_vencimiento` informada, acepta `vencimientos` por item
- `PUT /api/productos/{id}/ajustar-stock` ahora usa FEFO via `ajustar_stock_por_lote`
- Endpoints: `GET /api/lotes`, `GET /api/lotes/alertas`, `GET /api/lotes/{id}`, `POST /api/lotes`, `PUT /api/lotes/{id}`, `POST /api/lotes/{id}/desactivar`, `GET /api/lotes/producto/{id}/resumen`, `GET /api/lotes/reporte/stock-por-lote`, `GET /api/dashboard/alertas-lotes`
- `PUT /api/compras/{id}/recibir` ahora acepta `vencimientos: {item_id: iso_date}` opcional

**Frontend:**
- `ProductoLotesManager.vue` integrado en el modal de edición de producto: lista de lotes con badges de vencimiento (vencido/Xd), resumen (vencidos + por vencer 30d), botones editar/desactivar (con confirmación), sub-modales de edición y creación manual de lote (mermas, ajustes)
- `ComprasView.vue`: nueva columna "Vencimiento" (date input) en el modal de Recepción con hint visible sobre FEFO
- `DashboardView.vue`: alertas arriba (vencidos y por vencer 7d en rojo, 15d en amarillo)
- `ReportesView.vue`: nueva card "Stock por Lote" con buscador + KPIs (productos con stock, lotes activos, valorización total) + lista con chips coloreados

**Pendiente refinar (no bloqueante):** bloquear venta de lotes vencidos en POS · edición inline de codigo_proveedor por lote · exportar reporte stock-por-lote a CSV · deshabilitar lotes en el POS al confirmar venta vencida.

### Producto ↔ Proveedor (UI rica) — 09/08/2026
- Componente `ProductoProveedoresManager.vue` (`frontend/src/components/products/ProductoProveedoresManager.vue`)
  - Lista de proveedores asignados al producto con badge "Principal" e "Inactivo"
  - Inline: toggle de principal (estrella), toggle de activo, botones editar/quitar
  - Sub-modal de edición con `codigo_proveedor`, `costo`, `plazo_entrega_dias`, `es_principal`, `activo`, `notas`
  - Sub-modal de confirmación para quitar
  - Select inline de "Agregar proveedor" filtrado por disponibles
- `ProductsView.vue`: en modo edición, el `<select>` simple se reemplaza por el manager (full-width debajo del grid)
- En modo creación se mantiene el `<select>` simple + quick-create (post-save el manager se ocupa)
- `codigo_proveedor`, `costo`, `plazo`, CUIT y notas se muestran en cada item

### Producto ↔ Proveedor (backend, relación rica) — 08/08/2026
- Migración: tabla puente `producto_proveedor` extendida con `codigo_proveedor`, `costo`, `plazo_entrega_dias`, `es_principal`, `activo`, `notas`, `created_at`, `updated_at` (`app/main.py:246-259`)
- Endpoint `PUT /api/productos/{id}/proveedores/{pid}` para editar la relación (`app/routers/productos.py:400-447`)
  - Marcar `es_principal=true` desmarca los demás del mismo producto (transaccional)
- `GET /api/productos/{id}/proveedores` ahora devuelve los metadatos de la relación (`app/routers/productos.py:344-374`)
- `ProductsView`: buscador con null-safety y persistencia de proveedor al editar (`frontend/src/views/ProductsView.vue:163, 320-336`)
- **Falta UI** para gestionar múltiples proveedores por producto y editar los nuevos campos (ver "Pendientes" abajo)

### Facturación Electrónica ARCA / AFIP — julio 2026
- `AjustesView`: sección colapsable "Datos de Facturación" con campos del emisor (Razón Social, Domicilio, Condición IVA, Ingresos Brutos, Fecha Inicio)
- Toggle `facturacion_provider` s360 / afip en Ajustes (`app/services/s360_service.py` + `afip_service.py`)
- Generación de clave RSA + CSR desde el ERP (`app/services/afip_csr_service.py`)
- Upload de archivos `.key` / `.crt` / `.csr` / `.pem` en Ajustes con endpoints `/subir-key` y `/subir-pem`
- WSFE vía `curl` (sin zeep, sin WSDL dinámico) — fix de múltiples problemas SSL con servers legacy ARCA
- Tipo de comprobante 11 (Factura C) para no-RI; Factura A con array Iva
- Campos según spec ARCA: `ImpIVA`, `ImpOpEx`, `CondicionIVAReceptorId`
- Generador de QR para facturas electrónicas (`app/services/factura_pdf.py`)
- Modal de factura electrónica con PDF, impresión y WhatsApp (`FacturaDetalleModal.vue`)
- Toggle de factura automática por medio de pago (7 medios, default QR MP / POS MP ON) — `app/services/config_service.py:get_factura_auto_por_medio()`
- `venta_service.confirmar_venta()` consulta el toggle antes de emitir FE
- UI: CAE en una línea, box factura 8mm, vencimiento en una línea
- Impresión en ventana nueva con `qr.drawOn` (no `drawAt`)
- Botón "Re-emitir facturas rechazadas"
- Botón "Descargar `.key`" para guardar clave privada AFIP localmente

### MercadoPago — julio 2026
- API `v1/orders` (`app/services/mercadopago_service.py`)
- Creación de store / POS desde Ajustes
- Modo QR híbrido: fijo + dinámico, con QR fijo colapsable por defecto
- Smart Point (POS MP) integrado
- Webhooks con validación HMAC-SHA256 + `webhook_secret` configurable
- Eventos correctos según docs MP (`order.processed`)
- Procesa webhook aunque la orden no esté en MP, usando `external_reference` directo
- Botón borrar clave webhook en Ajustes
- Sandbox URL = `api.mercadopago.com` (no `sandbox.mercadopago.com`)
- Provincia como select con 24 valores válidos para MP; default Jujuy / San Salvador
- `mercadopago_user_id`, `store_id`, `external_store_id` en `get_mercadopago_config`
- Auto-guardado de store y caja en config al crearse
- `caja` usa `external_id` de store (no store_id numérico)
- Polling consulta estado de venta en DB, no en API de MP
- `unit_measure` faltante agregado a items de orden MP
- Mapping español → inglés de modo QR (`dinamico` → `dynamic`)
- `MERCADOPAGO.md` con info de integración y troubleshooting

### Sesión 30/06/2026 (previo, ya documentado)
- WhatsApp en Clientes con mensaje prellenado de deuda
- WhatsApp en Compras (proveedores)
- Estado "parcial" en Compras
- Modal de arqueo en Cierre de Caja
- Logout automático tras cierre-total de caja
- Validación de token con `/api/auth/me` en auto-login
- Columnas Compras: Total brand-600, Canti., Pendiente, icono Comentarios
- Comentarios en Compras con fecha/hora y autor
- Fix: items se guardan al crear OC
- Endpoints `POST /api/compras/{id}/comentario` y `POST /api/clientes/{id}/abonar`

---

## ✅ Completados recientemente

### Entrada manual `*Nombre*Precio` del POS + 3 bugs POS/Productos + Carritos por defecto — 01/10/2026
- **Commits:** `50df07f` (entrada manual), `eac78f6` (3 bugs: menú carritos cortado, vida carrito heredada, 500 al convertir producto), `c9fb3d0` (flechas para recorrer carritos abiertos)
- **Entrada manual `*Nombre*Precio`:** el alta se confirma al pausar 700ms (no al escribir el 2do `*`); input no se borra a medias; aviso solo en Enter explícito conservando texto; códigos `GEN-` derivados de timestamp (no secuencia filtrada)
- **Bug 1 - Menú carritos cortado:** `BaseCard` recibe prop `overflow` (default true); card del POS usa `:overflow="false"` para que el panel absolute se vea completo
- **Bug 2 - Vida carrito heredada:** `/api/caja/estado` expone `sesion_id` y `sesion_inicio` (UTC con Z); `cajaStore.fetchEstado()` llama `carritoStore.sincronizarSesion()`: al abrir caja nueva, carritos abiertos reinician reloj con ella; sesión vigente en `localStorage` (`apex-pos-carritos.sesionId`) sobrevive a reload
- **Bug 3 - 500 al convertir a sin stock:** modal no toca código de producto existente; `_generar_codigo_barras()` asigna `MAN-XXXXXXXXXX` si campo vacío; IntegrityError → 409 con mensaje legible
- **Carritos por defecto:** botón `+` del header del POS → chevrons para recorrer carritos abiertos (anterior/siguiente, circular); crear carrito nuevo sigue en panel del chevron inferior
- **Tests:** 258 tests (5 nuevos código barras, 3 identidad sesión) + build OK

### Precios Online + Control Stock + Lotes FEFO + ProductsView + BaseModal — 29/09/2026 (validación completada)
- **Precios Online:** precios con cifras reales, imagen/marca, badge "Más barato" verde, 3 KPIs (precio local, mejor online, ganancia/unidad), diff vs local con color, caché 15 min noticeably más rápido 2da búsqueda, aviso "no en catálogo" sin error rojo, Stock Bajo → click → busca y cierra, chip proveedor → modal con stock correcto, modo oscuro legible, doble clic no dispara 2 búsquedas
- **Control stock + Vendido por Peso:** toggle "Controlar stock" persiste, badge `s/ctrl` en tabla, no suma en "Stock bajo/Sin stock", POS sin aviso stock insuficiente ni marca revisión, venta con control y stock 0 sigue avisando déficit, reporte "Vendido por Peso" calcula kg/$ correcto vs tickets, venta anulada desaparece del reporte
- **Lotes + FEFO:** "Lote inicial" creado en primer arranque para stock preexistente, recepción OC con columna Vencimiento crea lote, venta POS consume por FEFO (lote más próximo a vencer), anulación revierte al mismo lote, lote vencido con borde rojo en manager + alerta Dashboard, reporte "Stock por Lote" con KPIs y chips coloreados
- **ProductsView buscador:** debounce 200ms (no re-render por tecla), botón X limpia, búsqueda parcial (ej: `coca`, `779`), búsqueda en categoría, filtros combinables (sin exclusión mutua), botón "Limpiar filtros" resetea todo
- **BaseModal scroll:** modal Nuevo/Editar Producto scrollea en pantalla chica, botones Cancelar/Crear fijos abajo (footer slot), funciona en modal Oferta y Eliminar

**Control de stock por producto + Vendido por Peso** (29/09/2026):
- [ ] Editar un producto fraccionado (panadería) → desactivar "Controlar stock" → guardar y recargar: el flag persiste
- [ ] En `/products`, el producto aparece con badge `s/ctrl` en la columna Stock y no suma en "Stock bajo" / "Sin stock"
- [ ] En el POS, vender por kilo ese producto: no aparece el aviso de "Stock insuficiente" ni queda marcado en revisión
- [ ] Vender un producto **con** control y stock 0 → debe seguir apareciendo el aviso y la bandera de déficit (comportamiento viejo intacto)
- [ ] En `/reportes` → card "Vendido por Peso": cambiar el rango, "Calcular", y contrastar los kg/$ con el ticket de las ventas del período
### Lotes + FEFO — Refinamientos
- Bloquear venta de lotes vencidos en POS (validación backend al confirmar)
- Edición inline de `codigo_proveedor` por lote (en ProductoLotesManager)
- Exportar reporte stock-por-lote a CSV
- Deshabilitar lotes inactivos en UI de recepción
- Auditoría: registrar eventos `lote_creado`, `lote_desactivado`, `lote_modificado`

---

## 📋 Pendientes activos

### Alta prioridad
- **Ronda de 19 bugs — ítem 16: beneficio de compra del empleado** (diseño ya acordado con el dueño el 15/10/2026, **falta implementar**): cuando un **cajero atiende su propia compra** en el POS puede aplicar un beneficio. El dueño le otorga en la ficha del usuario: **% máximo por compra + tope mensual en $**, y elige si es **general o solo para rubros** marcados (el árbol de `Categoria` ya tiene jerarquía padre/hijo). Dos botones en el POS: el descuento (limitado al %) y **"Al costo"** con `Producto.precio_costo` (los productos sin costo cargado no se pueden vender al costo, hay que avisar y no cobrar 0). **Se valida en backend** al confirmar la venta, no solo ocultando el input: hoy `PUT /api/ventas/{id}/confirmar` acepta cualquier descuento y `agregar_item` acepta cualquier precio. Ojo: la lógica del carrito está **duplicada** en `POSView.vue` y `CobroMovilView.vue`, hay que tocar las dos. Migración de columnas en `usuarios` (hoy no hay ningún campo de permisos ni de descuento). **Dato que apareció al hacer el nivel 1 del offline:** `precio_costo` **ya viaja** en `GET /api/productos` (y ahora también en `GET /api/catalogo/local`), así que cualquier usuario logueado puede leerlo hoy — **decisión de trabajo (16/10/2026): que no le llegue al celular**: el servidor no lo manda a quien no lo usa, y si el cajero aprieta "Al costo" bajan solo los rubros habilitados de ese usuario. Falta confirmar si el dueño quiere algo distinto. **Los ítems 15, 18 y 19 de esa ronda quedaron cerrados el 15/10/2026** (ver "Completados recientemente": Fase C1, C2 y C4)
- **Modo offline completo del POS** — **fases D (eficiencia) y E (ciclo sin red) hechas y desplegadas el 16/10/2026**, ver "Fase D — eficientizar" y "Fase E — abrir, cobrar y cerrar sin red" en Completados. Plan acordado con el dueño en 3 fases: **D = eficientizar (hecha)**, **E = ciclo sin red (hecha)**, **F = APK**. Nivel 1 (catálogo en el navegador) hecho y desplegado el 15/10/2026; **nivel 2** (cobrar sin red) y **nivel 3** (abrir y cerrar caja sin red) cerrados con la Fase E, incluida la reconciliación al volver **sin duplicar**. **Decisión del dueño (16/10/2026): ese día no se factura**, así que **no** hay emisión diferida de comprobantes: los que requieren red (ARCA, MercadoPago, Telegram, backups, precios online) quedan marcados "necesita red" y se resuelven después con conexión. Quedan:
  - **Pasar el día sin internet en mano (último paso de E)**: con el wifi apagado, abrir caja, vender y cerrar en un dispositivo real, y ver que al reconectar sube todo solo y sin duplicar. Los caminos están cubiertos por `tests/test_fase_e.py`, pero es la prueba que le importa al dueño
  - **APK para tablets/mostrador (Fase F): sigue en pendiente** — vía Capacitor, empaqueta el mismo build de Vue, no hay que reescribir nada. Conviene recién cuando se pida instalar en un dispositivo sin navegador. **Escritorio descartado**: agrega mantenimiento y cero funcionalidad (salvo driver de hardware puntual). Falta saber si en los mostradores usan tablets o PCs
  - Si el catálogo crece y el JSON deja de caber en `localStorage` (~5 MB compartidos; hoy 0,4 MB con 567 productos), moverlo a **IndexedDB**
- **MercadoPago: select de ciudad por provincia** — `app/services/mercadopago_service.py` ya tiene provincia como select (24 valores válidos); falta el segundo select de ciudad/localidad que dependa de la provincia elegida, porque MP rechaza si el `city_name` no es válido
- **Seguridad clave privada AFIP** — la clave se guarda encriptada en la DB con una key hardcodeada (`"erp-afip-key-encryption-v1"`). Si alguien accede a DB + código fuente puede descifrarla. **Solución propuesta:** no guardar clave privada en DB — solo descargar (botón "Descargar .key" ya existe) y que el usuario la guarde localmente. Alternativa: secrets manager (AWS Secrets Manager, etc.). Requiere re-flujo de setup de AFIP.

### Media prioridad
- **Impresión de tickets** — `TicketModal.vue` ya tiene preview 80/58mm; falta:
  - PDF descargable (no solo ventana de impresión)
  - Impresora térmica (ESC/POS o similar)
  - Formato fiscal simplificado
- **Reportes exportables (CSV/PDF)** — los reportes en `/reportes` se ven en pantalla pero no se exportan
- **Notificaciones (campana)** — lista y desplegada (`87b5de0`): avisos de stock bajo con el proveedor de la última compra y los precios de compra y venta, sin stock, caja abierta, lotes vencidos/por vencer y licencia por vencer. Dedup diario, lectura por usuario o global y granularidad "un aviso por día" | "uno por producto", las dos elegibles en Ajustes → Avisos
- **Aviso por Telegram** — `avisos_service.py` desplegado (`e0b062d`): una vez por día, a la hora elegida en Ajustes → Avisos, manda al canal el mismo listado de la campana (producto, stock/mínimo, proveedor de la última compra, precios). Chequeo cada 10 minutos con APScheduler, reintentos si falla, y botón "Probar envío". **Falta la config del usuario**: crear un bot con `@BotFather`, sumarlo al canal del negocio y pegar en Ajustes el token y el chat ID (lo da `@userinfobot`). Sin eso el switch queda apagado y no manda nada
- **Agrupar el bajo stock por lugar de compra** — en la campana y en el detalle del Dashboard, juntar los productos bajo mínimo por el proveedor de su última compra ("Carrefour: 7 productos") para salir a comprar o armar la compra online de una
- **`productos.stock_actual` desincronizado de los lotes** — en producción 169 de 549 productos que controlan stock tienen `stock_actual` distinto de la suma de sus lotes activos (167 con la columna **por encima**, máximo 22 unidades; 2 al revés). Como la columna es la que ven el Dashboard, el POS y el chip de Productos, esos 167 se ven con más stock del que dice FEFO; entre los 18 bajo mínimo, 1 ("Pipas Gigantes 50G": columna 0, lotes 10) está marcado por eso. **Solución propuesta:** `scripts/sincronizar_stock.py` con dry-run por defecto y `--aplicar`, recalculando sólo los productos que tienen lotes (los 10 que no tienen ninguno ya están en 0)
- **Compras: producto similar o discontinuo** — al recibir, poder reemplazar un producto pedido por otro similar; marcar ítems como "no enviado / discontinuo"; registrar qué se recibió en lugar de qué se pidió

### Baja prioridad
- **Multi-sucursal** — modelos `Sucursal` ya existen; falta que cada caja/usuario vea solo su sucursal
- **Migración PostgreSQL + Alembic** — para cuando haya >5 usuarios concurrentes o acceso remoto multi-sucursal
- **Instalador Windows (.exe)** — NSIS o Inno Setup, empaqueta Python + deps + app
- **Dashboard multi-negocio (admin central)** — dueño con varios `machine_id` necesita vista global. Dos opciones:
  - **A)** App separada que lee backups de R2 de todos los machine_id
  - **B)** El admin del ERP actual puede "importar" backups de otros (endpoint `GET /api/admin/backups/todos` + drill-down)

---

## 💡 Backlog (ideas sin priorizar)

- Auditoría de carritos sospechosos (> 2h) — ya hay banner, falta reporte histórico en vista Auditoría
- Catálogo central cross-tenant (compartir entre sucursales)
- Integración con balanza / lector de código de barras por USB
- App mobile companion para el dueño (consultar ventas en vivo)
- Exportar productos a Excel/CSV desde Productos
- Importar productos desde Excel (masivo)

---

## 🗒️ Cómo mantener este archivo

1. Al **cerrar una sesión relevante** (no cada commit chico), agregar entrada a "Completados recientemente" con la fecha
2. Si algo queda a medias, mover a "En curso" con bullets claros de qué falta
3. Si aparece algo nuevo, agregar a "Pendientes activos" en la prioridad que corresponda
4. Si se descarta o se vuelve irrelevante, **borrarlo** (no acumular) — el historial está en `git log`
