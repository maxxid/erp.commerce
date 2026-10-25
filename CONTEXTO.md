# Contexto — ApexERP

> **Instrucción para el Agente:** Lee este documento al inicio de cada sesión para entender el contexto global del proyecto, la ubicación de sus módulos y las restricciones de ejecución. No leas otros archivos de documentación a menos que sea explícitamente necesario para la tarea asignada.

> Snapshot del proyecto para retomar sesiones rápido. **Actualizar al cambiar de contexto o al cerrar un hito importante.**

---

## 🏷️ Identidad

| Campo | Valor |
|-------|-------|
| **Nombre** | ApexERP (también llamado "ERP Comercio" en algunos docs) |
| **Repo** | `github.com/maxxid/erp.commerce` |
| **Branch actual** | `master` |
| **Local** | `E:/erp.commerce` (Windows) |
| **Stack** | Python FastAPI + SQLAlchemy + SQLite · Vue 3 (Composition API) + Vite 5 + Tailwind · Pinia |
| **Última release funcional** | commit `3a494b7` (10/08/2026) |

---

## 📌 TL;DR para empezar una sesión

1. `git pull` y leer este archivo
2. Leer `PENDIENTES.md` → sección "En curso" para saber qué retomar
3. Si vas a codear: leer `MAESTRO.md` + `.opencode/instructions.md` + skill `arquitecto-programador`
4. Al cerrar la sesión, actualizar `PENDIENTES.md` con lo hecho

---

## 🗺️ Mapa de arquitectura (Context Index)

Usar este índice para localizar rápidamente el archivo o módulo relevante según la consulta, evitando escaneos completos del repositorio.

| Módulo / Dominio | Archivos Clave | Descripción / Responsabilidad |
| :--- | :--- | :--- |
| **Autenticación** | `app/auth/*` | JWT, dependencias, hashing |
| **API & Rutas** | `app/routers/*`, `app/main.py` | Endpoints REST por dominio |
| **Lógica de Negocio** | `app/services/*` | Reglas de negocio e integraciones de servicios |
| **Base de Datos** | `app/models/*`, `app/database.py` | Modelos SQLAlchemy, engine, Base |
| **Schemas** | `app/schemas/*` | Pydantic (incl. `producto_proveedor.py`) |
| **Configuración** | `app/config.py`, `.env*` | Configs y variables de entorno |
| **Migraciones** | `migrations/*`, `app/main.py:_migrate_new_columns` | SQL histórico + auto-migración al arrancar |
| **UI / Vistas** | `frontend/src/views/*` | Pantallas: POS, Caja, Products, Ajustes, Facturación |
| **UI / Componentes** | `frontend/src/components/*` | BaseButton, BaseModal, layout, etc. |
| **Stores / Composables** | `frontend/src/stores/*`, `frontend/src/composables/*` | Pinia (auth, caja) y hooks |
| **API client** | `frontend/src/services/api.js` | Wrapper axios/fetch con `RespuestaData { data, message }` |
| **Documentación** | `MAESTRO.md`, `PENDIENTES.md`, `API_DOCUMENTACION.md`, `MERCADOPAGO.md`, `DEPLOY.md`, `HOSTING.md`, `MULTITENANT.md`, `FASE_G_CONTINUIDAD.md` | Docs de referencia (leer solo si la tarea lo requiere) |

---

## ⚡ Reglas de eficiencia & consumo de tokens (para el Agente)

Para minimizar el consumo innecesario de créditos y optimizar el tiempo de respuesta:

1. **Lectura selectiva:** consulta únicamente los archivos directamente relacionados con la tarea. Apóyate en el *Mapa de arquitectura* y en *Estructura clave*.
2. **Ignorar archivos pesados:** nunca analices archivos dentro de `node_modules/`, `dist/`, `.next/`, `build/`, `package-lock.json`, ni logs masivos.
3. **Pausar tras 2 intentos fallidos:** si un comando de prueba, build o refactorización falla 2 veces consecutivas, detente, explica brevemente el bloqueo y pide confirmación al usuario antes de reintentar.
4. **Respuestas concisas:** límitate a aplicar los cambios requeridos y dar una explicación breve. Evita resúmenes largos no solicitados.
5. **No leer otros `.md`** (MAESTRO, PENDIENTES, etc.) a menos que la tarea lo requiera explícitamente.

---

## 🚀 Cómo arrancar

```bash
# Backend (con venv activado)
cd E:/erp.commerce
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# O usar el launcher de Windows
iniciar.bat

# Frontend (en otra terminal, solo para desarrollo con HMR)
cd E:/erp.commerce/frontend
npm run dev

# Build de producción (siempre antes de commitear cambios en frontend)
npm run build
```

- **URL local:** `http://localhost:8000/app`
- **Login default:** `admin / admin`
- **Licencia:** 30 días de prueba automática al primer arranque
- **DB:** SQLite local en `app/database.py` (path por defecto en el dir del proyecto)

`setup.bat` instala todo desde cero (descarga Python 3.12 si no hay compatible).

---

## 🗂️ Estructura clave

```
erp.commerce/
├── app/                              # Backend FastAPI
│   ├── main.py                       # Entry point + migraciones de schema
│   ├── database.py                   # SQLAlchemy Base + engine
│   ├── config.py                     # Configs varias
│   ├── auth/                         # JWT, dependencias, hashing
│   ├── models/                       # SQLAlchemy: producto, venta, cliente, etc.
│   ├── routers/                      # Endpoints REST por dominio
│   │   ├── productos.py              # ⭐ incluye PUT /productos/{id}/proveedores/{pid}
│   │   ├── facturacion.py            # FE ARCA/AFIP/s360
│   │   ├── pagos.py                  # MercadoPago
│   │   └── ventas.py
│   ├── schemas/                      # Pydantic — incluye producto_proveedor.py
│   └── services/                     # Lógica de negocio
│       ├── producto_service.py
│       ├── venta_service.py          # confirmar_venta, FE auto, etc.
│       ├── afip_service.py           # WSAA + WSFE via curl
│       ├── afip_csr_service.py       # Genera clave RSA + CSR
│       ├── s360_service.py           # Proveedor alternativo FE
│       ├── mercadopago_service.py    # v1/orders, stores, webhooks
│       ├── factura_pdf.py            # PDF + QR de factura electrónica
│       ├── factura_pdf_service.py
│       └── config_service.py         # Toggles FE por medio de pago
├── frontend/
│   ├── src/
│   │   ├── views/                    # Pantallas — POSView, CajaView, etc.
│   │   │   ├── ProductsView.vue      # ⭐ donde va la UI rica producto-proveedor
│   │   │   ├── AjustesView.vue       # AFIP, MP, FE, Datos de Facturación
│   │   │   ├── FacturacionView.vue
│   │   │   └── POSView.vue
│   │   ├── components/               # BaseButton, BaseModal, layout, etc.
│   │   ├── composables/              # useHeldTickets, useUtils, useSounds
│   │   ├── stores/                   # Pinia: useAuthStore, useCajaStore
│   │   └── services/api.js           # Wrapper axios/fetch con RespuestaData
│   └── dist/                         # Build de producción (commiteado)
├── migrations/                       # SQL de migraciones históricas
├── MAESTRO.md                        # ⭐ Documento funcional maestro — LEER SIEMPRE
├── PENDIENTES.md                     # ⭐ Estado actual de tareas
├── CONTEXTO.md                       # ⭐ Este archivo
├── API_DOCUMENTACION.md              # Endpoints REST
├── MERCADOPAGO.md                    # Setup + troubleshooting MP
├── DEPLOY.md / HOSTING.md            # Deploy Railway / hosting
├── setup.bat / iniciar.bat           # Instalación y arranque Windows
└── requirements.txt
```

---

## 📐 Convenciones (resumen)

**Código:**
- **Sin comentarios** en código nuevo a menos que el usuario los pida
- **Sin exports/imports no usados**, sin logs de debug, sin código comentado
- Backend sync: `crear_producto`, `actualizar_producto` son sync (SQLAlchemy); los endpoints son async
- Errores HTTP: backend levanta `HTTPException(status_code, detail=...)`; frontend muestra `toast.error(e?.response?.data?.detail || e.message)`

**Frontend:**
- Composition API con `<script setup>`
- `import api from '@/services/api'` — wrapper que desenvuelve `RespuestaData { data, message }`
- Formateo monetario: `import { formatCurrency as fc } from '@/composables/useUtils'`
- Iconos: FontAwesome clases `fa-solid fa-xxx`
- Modales: `<BaseModal :model-value="show" @update:model-value="emit('close')">` (nunca `v-model` con props)
- Stores: solo `useAuthStore` y `useCajaStore` son globales; lo demás vive en composables/refs locales

**Migraciones:**
- El backend intenta hacer migraciones de schema al arrancar (`_migrate_new_columns()` en `app/main.py:243-259`)
- Para columnas nuevas usar `ALTER TABLE ... ADD COLUMN` con check de `PRAGMA table_info(...)` para no romper reinicios

**Frontend build:**
- `frontend/dist/` está commiteado (es lo que sirve FastAPI en `/app`)
- **Siempre** correr `npm run build` antes de commitear cambios de frontend

---

## 🔧 Git

**Política: auto commit + push después de cada cambio relevante.** No esperar a que el usuario lo pida. El backend está deployado en otro server, así que push = deploy automático. Si algo falla, se hace `git revert` o un fix commit encima.

```bash
# Estado (consultar, no esperar a que el usuario lo pida)
git status
git log --oneline -20

# Flujo automático después de un cambio
git add <files>
git commit -m "feat(productos): ..."
git push origin master
# Tipos: feat, fix, refactor, chore, docs, build, ui, debug

# Si algo se rompe
git revert HEAD        # deshace el último commit (genera un commit nuevo)
git push origin master # publica el revert
```

- Mensajes en español, lowercase después del scope, descripción clara
- Cada commit debe dejar el sistema funcional (no romper build)
- `npm run build` antes de commitear cambios de frontend (el `dist/` está commiteado)

---

## 🧠 Conocimiento del dominio

- **Tipo de cambio de día:** Si la caja se abrió ayer y hoy es otro día, `caja_service.caja_abierta()` la cierra automáticamente al consultar el estado
- **Stock en tránsito vs real:** al crear OC, sube `stock_transito`; al recibir, baja tránsito y sube `stock_actual`
- **Soft delete:** Productos, clientes, proveedores no se borran físicamente, se desactivan con `activo=False`
- **Anular venta:** revierte stock (`MovimientoStock` tipo `venta_anulada`), revierte caja, revierte saldo cta. cte.
- **Facturación ARCA:** backend usa `curl` directo (no zeep) por issues SSL con servers legacy; se ejecuta vía `/usr/bin/openssl` y `curl -sk` cuando hace falta CMS
- **Webhooks MP:** validan firma HMAC-SHA256 con `webhook_secret` configurable; el secret se borra desde Ajustes
- **Cta. Corriente:** medio de pago propio del ERP (no MP), incrementa saldo cliente sin pasar por pasarela

---

## 🟢 Dónde estamos ahora (sesión 09–10/08/2026 — último commit `3a494b7`)

**Tareas cerradas en esta sesión (en orden):**
1. **Producto ↔ Proveedor (UI rica)** — `ProductoProveedoresManager.vue` integrado en el modal de edición. Backend ya estaba desde el 08/08.
2. **Lotes + FEFO (MVP + UI rica)** — backend completo + frontend (manager en producto, vencimiento en Compras, alertas en Dashboard, reporte en Reportes). Migración auto crea "Lote inicial" para stock preexistente.
3. **ProductsView UX** — buscador con debounce + clear, filtros independientes (sin exclusión mutua), botón "Limpiar filtros" + contador de filtros activos, badges con contraste correcto.
4. **ProductsView bug fix** — el buscador fallaba silenciosamente cuando la API devolvía campos con tipo raro (BigInt/Number/Object). Vue 3 en computeds con excepción mantiene valor anterior sin re-renderizar. Fix: `safeStr()` + `Number()` + try/catch con logging.
5. **BaseModal scroll** — modal crecía sin límite y no se podía scrollear. Fix: max-height + flex-col + overflow-y-auto en body + footer slot para botones fijos.

**Pendiente de validación manual en browser (no testeado aún):**
- Lotes/FEFO end-to-end: migración inicial → recepción con vencimiento → venta consume por FEFO → anulación revierte → alertas Dashboard → reporte valorizado
- ProductsView: buscador con datos reales (especialmente con campos null/tipo raro)
- BaseModal: scroll en modal de producto + edición con varios proveedores y lotes

**Próximo frente sugerido** (a discutir mañana): refinar Lotes (bloqueo de venta de lotes vencidos en POS) o pasar a **MercadoPago: select de ciudad por provincia** o **Reportes exportables CSV**.

**Decisiones de diseño Lotes ya cerradas** (referencia):
- Todos los productos usan lotes · 1 lote por item en recepción · FEFO automático en ventas/ajustes/anulación · `fecha_vencimiento` vive solo en lote.

---

## ⚠️ Gotchas recordados

- **No usar zeep para WSFE** — SSL con ARCA legacy rompe. Usar `curl` directo.
- **TRA de AFIP** necesita timezone `-03:00` (Argentina), no UTC.
- **Cert/key de AFIP** se desencriptan y escriben a temp files antes de usar SSL mutuo.
- **CSR de AFIP** debe tener `serialNumber=CUIT` (requerido por ARCA).
- **Webhooks MP:** `order.processed` es el evento, no `payment`. Y no validar firma en webhooks QR según docs.
- **Sandbox MP:** URL = `api.mercadopago.com` (no `sandbox.mercadopago.com` que ya no existe).
- **MP provincia:** 24 valores válidos; default Jujuy / San Salvador. Ciudad debe matchear.
- **MP `unit_measure`** es obligatorio en items de orden o falla.
- **Auto-emisión FE:** `venta_service.confirmar_venta()` consulta `get_factura_auto_por_medio()` antes de emitir — respetá ese toggle.
- **No romper features existentes** — siempre verificar contra `MAESTRO.md` antes de cambiar algo.
- **Build antes de commitear frontend** — `npm run build` + commitear el `dist/` actualizado.
- **Migraciones SQLite:** usar el patrón `PRAGMA table_info` + `ALTER TABLE ... IF NOT EXISTS` (no hay Alembic todavía).

---

## 🆘 Si algo no anda

1. **Backend no arranca:** ver `iniciar.bat` para stack trace; `app/main.py` es el entry.
2. **Frontend no compila:** `cd frontend && npm run build` para ver error; `dist/` es lo que se sirve.
3. **Endpoint nuevo no aparece:** reiniciar uvicorn (no HMR en backend).
4. **Cambio en schema no se aplica:** `_migrate_new_columns()` en `app/main.py:243-259` — agregar bloque siguiendo el patrón.
5. **Factura rechazada:** revisar `app/services/afip_service.py` y los logs SOAP; el modal muestra el motivo.
6. **Webhook MP no procesa:** ver `MERCADOPAGO.md` troubleshooting + logs en `app/services/mercadopago_service.py`.

---

## 📋 Reglas de código & estilo (Project Taste)

1. **Arquitectura:** mantener separación estricta de responsabilidades entre rutas, controladores y servicios.
2. **Manejo de errores:** retornar errores tipados; evitar bloques `try/catch` vacíos o genéricos sin logging.
3. **Librerías:** no agregar nuevas dependencias externas sin confirmación previa del usuario.
4. **Patrones preferidos:** funciones puras, composición sobre herencia, manejo explícito de tipos.

---

*Generado/actualizado a partir de la estructura de `PROJECT_GUIDELINES.md` para optimizar tokens y navegación.*
