# Pendientes — ApexERP

> Estado actual del proyecto. **Actualizar al final de cada sesión relevante** (en el commit que cierra la jornada o cuando arranca la siguiente).

---

## ✅ Completados recientemente

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

## 🟡 En curso (próximo a retomar)

### 🧪 Pendiente de validación manual en browser

_(Código pusheado, falta probar end-to-end en navegador — sesión 10/08/2026)_

**Precios Online** (29/09/2026):
- [ ] Escanear un código que **sí** esté en el catálogo local → los precios online aparecen con cifras reales (no "—"), con imagen y marca
- [ ] El primer resultado (más barato) sale con fondo verde + badge "Más barato", y el precio en verde
- [ ] Aparecen los 3 KPIs: precio de venta local, mejor precio online y ganancia por unidad
- [ ] En cada resultado aparece la diferencia contra el precio local ("$X vs tu precio") con el color correcto
- [ ] Repetir la **misma** búsqueda: la segunda tiene que ser noticeably más rápida (caché de 15 min)
- [ ] Escanear un código que **no** esté en el catálogo local → igual muestra la comparación online, y sale el aviso "Ese producto no está en tu catálogo" en vez de un error rojo
- [ ] "Stock Bajo" → abrir, ver skeletons, click en un producto → carga su búsqueda y cierra el panel
- [ ] Click en un chip de proveedor → el modal muestra los productos con el stock correcto (verificado contra `/productos`)
- [ ] Revisar en **modo oscuro** que toda la pantalla sea legible
- [ ] Doble clic rápido en "Buscar" → no debe disparar dos búsquedas

**Control de stock por producto + Vendido por Peso** (29/09/2026):
- [ ] Editar un producto fraccionado (panadería) → desactivar "Controlar stock" → guardar y recargar: el flag persiste
- [ ] En `/products`, el producto aparece con badge `s/ctrl` en la columna Stock y no suma en "Stock bajo" / "Sin stock"
- [ ] En el POS, vender por kilo ese producto: no aparece el aviso de "Stock insuficiente" ni queda marcado en revisión
- [ ] Vender un producto **con** control y stock 0 → debe seguir apareciendo el aviso y la bandera de déficit (comportamiento viejo intacto)
- [ ] En `/reportes` → card "Vendido por Peso": cambiar el rango, "Calcular", y contrastar los kg/$ con el ticket de las ventas del período
- [ ] Verificar que una venta anulada del período desaparece del reporte

**Lotes + FEFO** (commits `d9b97f5`, `b9391f7`):
- [ ] Verificar que al primer arranque se creó un "Lote inicial" para cada producto con stock preexistente (ir a `/products` → Editar → sección "Lotes")
- [ ] Crear OC en `/compras`, ir a "Recibir", completar la columna **Vencimiento**, confirmar → ver que el lote aparece en el producto
- [ ] En POS, hacer una venta de un producto con varios lotes → confirmar que el consumo sale del lote más próximo a vencer (FEFO)
- [ ] Anular la venta → verificar que el stock vuelve al mismo lote
- [ ] Verificar que un lote vencido aparece con borde rojo en el manager y como alerta en el Dashboard
- [ ] En `/reportes` → nueva card "Stock por Lote" abajo, verificar KPIs y chips coloreados

**ProductsView buscador** (commits `3834d58`, `0460edf`):
- [ ] Probar typing con debounce (no debe re-renderizar en cada tecla)
- [ ] Botón X limpia la búsqueda
- [ ] Buscar por texto parcial funciona (ej: `coca`, `779`)
- [ ] Buscar en categoría (ej: nombre de la categoría)
- [ ] Filtros combinables (Bajo stock + Sin código, etc.) — la exclusión mutua entre Bajo stock/Precio ≤ costo ya no existe
- [ ] Botón "Limpiar filtros" resetea todos los toggles y la búsqueda

**BaseModal scroll** (commit `3a494b7`):
- [ ] Abrir modal de Nuevo/Editar Producto en pantalla chica (zoom del navegador) → debe scrollear internamente
- [ ] Botones Cancelar/Crear deben quedar fijos abajo (footer slot)
- [ ] Probar también en modal de Oferta y modal de Eliminar

### Lotes + FEFO — Refinamientos
- Bloquear venta de lotes vencidos en POS (validación backend al confirmar)
- Edición inline de `codigo_proveedor` por lote (en ProductoLotesManager)
- Exportar reporte stock-por-lote a CSV
- Deshabilitar lotes inactivos en UI de recepción
- Auditoría: registrar eventos `lote_creado`, `lote_desactivado`, `lote_modificado`

---

## 📋 Pendientes activos

### Alta prioridad
- **MercadoPago: select de ciudad por provincia** — `app/services/mercadopago_service.py` ya tiene provincia como select (24 valores válidos); falta el segundo select de ciudad/localidad que dependa de la provincia elegida, porque MP rechaza si el `city_name` no es válido
- **Seguridad clave privada AFIP** — la clave se guarda encriptada en la DB con una key hardcodeada (`"erp-afip-key-encryption-v1"`). Si alguien accede a DB + código fuente puede descifrarla. **Solución propuesta:** no guardar clave privada en DB — solo descargar (botón "Descargar .key" ya existe) y que el usuario la guarde localmente. Alternativa: secrets manager (AWS Secrets Manager, etc.). Requiere re-flujo de setup de AFIP.

### Media prioridad
- **Impresión de tickets** — `TicketModal.vue` ya tiene preview 80/58mm; falta:
  - PDF descargable (no solo ventana de impresión)
  - Impresora térmica (ESC/POS o similar)
  - Formato fiscal simplificado
- **Reportes exportables (CSV/PDF)** — los reportes en `/reportes` se ven en pantalla pero no se exportan
- **Notificaciones** — stock bajo, licencia por vencer, caja sin cerrar al final del día
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
