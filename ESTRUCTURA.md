# Estructura — ApexERP

> **Instrucción para el Agente:** Lee este archivo (junto con `CONTEXTO.md` o vía `SESSION_START.md`) al inicio de cada sesión para localizar rápidamente archivos y relaciones sin escanear el repo. No leas otros `.md` salvo que la tarea lo requiera.

> Snapshot de la estructura física y de las vinculaciones padre-hijo entre archivos. Actualizar al agregar módulos, vistas o routers.

---

## 1. Árbol de fuente (ignorar `dist/`, `node_modules/`, `__pycache__/`, logs, `.git/`)

```
erp.commerce/
├── app/                          # Backend FastAPI
│   ├── main.py                   # Entry + registro de routers + migraciones + seeds + schedulers
│   ├── database.py               # engine, Base, SessionLocal, verificar_db
│   ├── config.py                 # settings (env)
│   ├── auth/                     # security.py (hash/jwt), dependencies.py (get_current_user), permisos.py
│   ├── models/                   # SQLAlchemy (uno por entidad)
│   ├── routers/                  # Endpoints REST (uno por dominio)
│   ├── schemas/                  # Pydantic (request/response)
│   └── services/                 # Lógica de negocio (uno por dominio)
├── frontend/
│   ├── src/
│   │   ├── main.js               # Bootstrap Vue + Pinia + router
│   │   ├── App.vue               # Layout global (header/sidebar/footer/toasts)
│   │   ├── router/index.js       # Rutas → views + guards por rol
│   │   ├── views/                # Pantallas (una por ruta)
│   │   ├── components/           # ui/, layout/, caja/, pos/, products/, ajustes/
│   │   ├── stores/               # Pinia: auth, caja, carrito, productos, ...
│   │   ├── composables/          # Hooks reutilizables (useUtils, useSounds, ...)
│   │   └── services/             # api.js (wrapper), stock.js, categorias.js
│   └── dist/                     # Build commiteado (lo sirve FastAPI en /app) — NO editar a mano
├── migrations/                   # SQL histórico (referencia; no hay Alembic)
├── tests/                        # pytest (testpaths = tests); conftest bloquea red
├── data/, backups/               # Datos y backups locales
├── CONTEXTO.md, MAESTRO.md, PENDIENTES.md, API_DOCUMENTACION.md, ...
├── requirements.txt, requirements-dev.txt
├── Dockerfile, railway.json, Procfile, iniciar.bat, setup.bat
└── pytest.ini
```

---

## 2. Backend — capas y convención

Cadena de llamada estándar: **router → service → model** (schema valida entrada/salida).

- `app/main.py` registra todos los routers (líneas 48-79) y ejecuta en startup: `create_all`, `_migrate_new_columns`, seeds, schedulers.
- `app/models/__init__.py` importa todos los modelos → `Base.metadata` los registra.
- Para agregar un dominio nuevo: crear `model`, `schema`, `service`, `router`, importar en `main.py` y `include_router`.

### 2.1 Routers (`app/routers/`) — endpoints REST por dominio

| Router | Prefix típico | Responsabilidad |
|---|---|---|
| `auth.py` | `/api/auth` | Login, `/me`, JWT |
| `usuarios.py` | `/api/usuarios` | CRUD usuarios + roles |
| `permisos.py` | `/api/permisos` | Permisos especiales |
| `licencia.py` | `/api/licencia` | Activación/generación licencias |
| `productos.py` | `/api/productos` | CRUD productos, lookup, stock-bajo, info-detallada, analisis-precios, precios-online |
| `categorias.py` | `/api/categorias` | CRUD categorías |
| `sectores.py` | `/api/sectores` | Sectores/ubicaciones |
| `proveedores.py` | `/api/proveedores` | CRUD proveedores + productos por proveedor |
| `compras.py` | `/api/compras` | Órdenes de compra + recepción + comentarios |
| `ventas.py` | `/api/ventas` | CRUD ventas, items, confirmar, anular |
| `caja.py` | `/api/caja` | Apertura/cierre, movimientos, arqueo, conciliación, retiros |
| `clientes.py` | `/api/clientes` | CRUD clientes + abonar deuda + historial |
| `ofertas.py` | `/api/ofertas` | CRUD ofertas |
| `lotes.py` | `/api/lotes` | Lotes/FEFO |
| `etiquetas.py` | `/api/etiquetas` | Etiquetas de precio + PDF + grupos |
| `recargas.py` | `/api/recargas` | Config + cálculo recargas |
| `denominaciones.py` | `/api/denominaciones` | Denominaciones de efectivo |
| `dashboard.py` | `/api/dashboard` | Resumen, semanal, mensual, trimestral |
| `reportes.py` | `/api/reportes` | Vendido-por-peso, recargas |
| `calendario.py` | `/api/calendario` | Actividad por día |
| `facturacion.py` | `/api/facturacion` | FE ARCA/AFIP/s360 |
| `pagos.py` | `/api/pagos` | MercadoPago |
| `configuracion.py` | `/api/configuracion` | Ajustes (AFIP, MP, FE, recargas, denominaciones, etc.) |
| `catalogo.py` | `/api/catalogo` | Exportar/descargar/recargar catálogo central |
| `backups.py` | `/api/backups` | Backups locales/R2 |
| `auditoria.py` | `/api/auditoria` | Logs de auditoría |
| `notificaciones.py` | `/api/notificaciones` | Notificaciones |
| `avisos.py` | `/api/avisos` | Avisos de stock (Telegram) |
| `recategorizar.py` | `/api/recategorizar` | Sugerencias de recategorización IA |
| `ia.py` | `/api/ia` | IA (OpenAI-compat) |

### 2.2 Models (`app/models/`) — entidades SQLAlchemy

| Modelo | Tabla | Relaciones clave |
|---|---|---|
| `producto.py` | `productos` | → categoria, sector; ↔ proveedores (via `producto_proveedor`); ↔ lotes |
| `categoria.py` | `categorias` | ← productos |
| `sector.py` | `sectores` | ← productos |
| `proveedor.py` | `proveedores` | ↔ productos; → deudas/pagos (cta. cte.) |
| `producto_proveedor.py` (schema) | `producto_proveedor` | tabla puente producto↔proveedor con costo, código, principal |
| `compra.py` | `compras`, `compra_items` | → proveedor; → productos |
| `venta.py` | `ventas`, `venta_items` | → cliente, usuario; → productos; → recargas |
| `cliente.py` | `clientes` | ← ventas |
| `usuario.py` | `usuarios` | → sucursal; ← ventas, movimientos |
| `movimiento_caja.py` | `movimientos_caja` | → usuario, sucursal, cierre |
| `movimiento_stock.py` | `movimientos_stock` | → producto, lote |
| `lote.py` | `lotes` | → producto |
| `oferta.py` | `ofertas` | → producto |
| `recarga.py` | `recargas` | → venta |
| `notificacion.py` | `notificaciones` | — |
| `auditoria.py` | `auditoria` | — |
| `licencia.py` | `licencias` | — |
| `configuracion.py` | `configuraciones` | — |
| `factura_electronica.py` | `facturas_electronicas` | → venta |
| `denominacion.py` | `denominaciones` | — |
| `proveedor_pago.py` | `deudas_proveedor`, `pagos_proveedor` | → proveedor |

### 2.3 Services (`app/services/`) — lógica de negocio

Convención: un service por dominio; los routers lo llaman. Servicios "core":
`producto_service`, `venta_service`, `caja_service`, `compra_service`, `stock_service`, `lote_service`, `oferta_service`, `catalogo_local/service`, `lookup_service`, `factura_pdf(_service)`, `afip_service`, `afip_csr_service`, `s360_service`, `mercadopago_service`, `config_service`, `recarga_service`, `analisis_precios_service`, `etiquetas_service`, `etiquetas_pdf`, `auditoria_service`, `backup_service`, `licencia_service`, `usuario_service` (en router), `notificaciones_service`, `avisos_service`, `salud_service`, `telegram_bot_service`, `demo_service`, `categorizacion_service`, `texto_service`, `planes_service`, `qr_interop_service`, `proveedor_pago_service`, `ticket_proveedor_service`, `denominacion_service`.

Integraciones externas: `services/ia/` (openai_compat, proveedor, limites, registro, __init__).

### 2.4 Schemas (`app/schemas/`) — Pydantic

`categoria`, `denominacion`, `etiquetas`, `lote`, `oferta`, `producto`, `producto_proveedor`, `recategorizar`, `sector`, `common`.

### 2.5 Auth (`app/auth/`)

- `security.py`: `hash_password`, `verify_password`, `create_access_token`, `decode_token`.
- `dependencies.py`: `get_current_user`, `require_role(...)`.
- `permisos.py`: permisos especiales por usuario.

---

## 3. Frontend — capas

### 3.1 Router (`frontend/src/router/index.js`)

Rutas → views lazy. Guards: `auth.authenticated`, `to.meta.roles`. Base history `/app/`. Ver tabla completa en el archivo (33 rutas: login, dashboard, pos, cobrar, products, etiquetas-precios, recategorizar, caja, ventas, calendario, compras, cargar-mercaderia, control-stock, sectores, precios-online, proveedores, clientes, reportes, usuarios, licencias, auditoria, backups, facturacion, ajustes).

### 3.2 Views (`frontend/src/views/`) — pantallas

Una por ruta. Principales: `POSView`, `CajaView`, `ProductsView`, `VentasView`, `ComprasView`, `ClientesView`, `ProveedoresView`, `DashboardView`, `ReportesView`, `CalendarioView`, `PreciosOnlineView`, `EtiquetasPreciosView`, `AjustesView`, `FacturacionView`, `BackupsView`, `AuditoriaView`, `UsuariosView`, `LicenciasView`, `LoginView`, y vistas móviles: `CobroMovilView`, `ComprasMovilView`, `ControlStockMovilView`, `SectoresMovilView`, `RecategorizarView`.

### 3.3 Stores (`frontend/src/stores/`) — Pinia

`auth` (JWT, usuario, licencia), `caja` (estado caja, movimientos, resumen), `carrito` (carritos con nombre, persiste localStorage), `productos`, `notificaciones`, `sync`, `toasts`, `calculadora`, `posPreferences`.

### 3.4 Composables (`frontend/src/composables/`)

`useUtils` (formatCurrency, formatDate...), `useSounds`, `useConfetti`, `useKeyboardShortcuts`, `useBarcodeScanner`, `useRefrescoPeriodico`, `useOfflineSync`, `useOfflineSales`, `useOfflineCaja`, `cajaCuentas`.

### 3.5 Services (`frontend/src/services/`)

`api.js` (wrapper axios/fetch, desenvuelve `RespuestaData { data, message }`), `stock.js`, `categorias.js`.

### 3.6 Componentes (`frontend/src/components/`)

- `ui/`: BaseButton, BaseInput, BaseSelect, BaseModal, BaseTable, BaseCard, BaseBadge, BaseSkeleton, BaseToggle, EmptyState, KpiCard, AnimatedNumber, Kbd.
- `layout/`: TheHeader, TheSidebar, TheFooter, TheBreadcrumbs, CommandPalette, HelpModal, KeyboardShortcutsModal, SidebarLink, SyncIndicator, OfflineIndicator, ToastContainer, NotificationBell, TicketModal, FacturaDetalleModal.
- `caja/`: AperturaCajaModal, ArqueoMedios, ContadorBilletesModal, ContadorTransferenciasModal, CalculadoraFlotante.
- `pos/`: QuickCreateModal.
- `products/`: ProductoLotesManager, ProductoProveedoresManager.
- `ajustes/`: LaboratorioQr.

---

## 4. Vinculaciones clave (padre → hijos)

### Backend
- `main.py` → importa todos los `routers/*` y `models/*` (vía `app.models *`).
- `database.py` → `engine`, `Base`, `SessionLocal`; `verificar_db()` al importar.
- `routers/*` → `services/*` → `models/*` + `schemas/*`.
- `auth/dependencies.py` → `auth/security.py` (decode JWT) + `models/usuario.py`.
- Migraciones: `_migrate_new_columns()` en `main.py` (PRAGMA + ALTER). Seeds: `_seed_database`, `_seed_denominaciones`, `_seed_producto_recarga`, `_migrate_lotes_iniciales`.

### Frontend
- `main.js` → monta `App.vue` + router + Pinia.
- `App.vue` → layout + `router-view` + toasts + modales globales.
- `router/index.js` → lazy import de `views/*`.
- `views/*` → `components/*`, `stores/*`, `composables/*`, `services/api.js`.
- `stores/carrito.js` → persiste en `localStorage('apex-pos-carritos')`; sobrevive route change.
- `services/api.js` → único punto de HTTP al backend; desenvuelve `RespuestaData`.

### Dominio Producto (ejemplo de cadena completa)
- Backend: `routers/productos.py` → `services/producto_service.py` (+ `stock_service`, `lote_service`, `oferta_service`) → `models/producto.py`, `models/lote.py`, `models/movimiento_stock.py` + `schemas/producto.py`, `schemas/producto_proveedor.py`.
- Frontend: `views/ProductsView.vue` → `stores/productos.js` → `services/api.js` → `/api/productos`; modales usan `components/products/ProductoLotesManager.vue`, `ProductoProveedoresManager.vue`.

### Caja
- Backend: `routers/caja.py` → `services/caja_service.py` → `models/movimiento_caja.py`.
- Frontend: `views/CajaView.vue` → `stores/caja.js` + `components/caja/*`.

### Ventas/POS
- Backend: `routers/ventas.py` → `services/venta_service.py` → `models/venta.py`, `models/movimiento_stock.py`, `models/movimiento_caja.py`, `models/cliente.py`.
- Frontend: `views/POSView.vue` → `stores/carrito.js` + `stores/caja.js` + `components/pos/QuickCreateModal.vue`.

---

## 5. Dónde agregar cosas (convención de ubicación)

| Tarea | Dónde |
|---|---|
| Nuevo endpoint de dominio existente | `app/routers/<dominio>.py` + service correspondiente |
| Nuevo dominio backend | Crear `models/X.py`, `schemas/X.py`, `services/X_service.py`, `routers/X.py`; importar en `main.py` (import + include_router) y en `models/__init__` si aplica |
| Nueva columna en tabla existente | Agregar al modelo + bloque en `_migrate_new_columns()` (`main.py`) con check `PRAGMA table_info` |
| Nueva vista frontend | `frontend/src/views/XView.vue` + ruta en `router/index.js` + entrada en `TheSidebar` si aplica |
| Nuevo componente reutilizable | `frontend/src/components/ui/` o subcarpeta por dominio |
| Nuevo store global | `frontend/src/stores/X.js` (solo si es global; preferir composable local) |
| Nuevo composable | `frontend/src/composables/useX.js` |
| Migración de datos histórica | `migrations/*.sql` (referencia) + seed en `main.py` si es idempotente |
| Tests | `tests/test_*.py` (conftest bloquea red; fixtures en `tests/fixtures/`) |

---

## 6. Ignorar siempre (no leer/analizar)

`frontend/dist/`, `frontend/node_modules/`, `app/**/__pycache__/`, `*.pyc`, `*.log`, `.git/`, `erp_comercio.db` (binario), `catalogo_*.json` (grandes), `backups/`.

---

## 7. Configuración y arranque

- Backend: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` (o `iniciar.bat`).
- Frontend dev: `cd frontend && npm run dev`; build: `npm run build` (commitear `dist/`).
- URL local: `http://localhost:8000/app`; login default `admin/admin`.
- DB: SQLite (path en `app/database.py`); migraciones auto al arrancar.
- Tests: `python -m pytest` (pytest.ini: `testpaths = tests`).
- Env: `app/config.py` + `.env*`.

---

## 8. Docs de referencia (leer solo si la tarea lo requiere)

| Doc | Cuándo leer |
|---|---|
| `SESSION_START.md` | Entry point mínimo al arrancar |
| `MAESTRO.md` | Solo la sección del módulo (ver su índice "Cómo usar") |
| `PENDIENTES.md` | Solo "En curso"/"Completados recientes" |
| `API_DOCUMENTACION.md` | Si la tarea toca endpoints/contratos |
| `MERCADOPAGO.md` | Si la tarea toca MP |
| `DEPLOY.md`/`HOSTING.md` | Si la tarea toca deploy/hosting |
| `MULTITENANT.md` | Si la tarea toca multi-tenant |
| `FASE_G_CONTINUIDAD.md` | Si la tarea toca continuidad/replica |
| `PROJECT_GUIDELINES.md` | Si la tarea toca guidelines generales |

> `CONTEXTO.md` apunta a este archivo para la estructura. Mantener ambos sincronizados.
