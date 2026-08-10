# Pendientes — ApexERP

> Estado actual del proyecto. **Actualizar al final de cada sesión relevante** (en el commit que cierra la jornada o cuando arranca la siguiente).

---

## ✅ Completados recientemente

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

### Lotes + FEFO — Refinamientos
- Bloquear venta de lotes vencidos en POS (validación backend al confirmar)
- Edición inline de `codigo_proveedor` por lote (en ProductoLotesManager)
- Exportar reporte stock-por-lote a CSV
- Deshabilitar lotes inactivos en UI de recepción
- Auditoría: registrar eventos `lote_creado`, `lote_desactivado`, `lote_modificado`

_(Frontend de Lotes/FEFO MVP+UI rica cerrado y pusheado)_

---

## 📋 Pendientes activos

### Alta prioridad
- _(Vacío — siguiente frente a elegir entre los de media/baja prioridad)_
  - Registrar productos por **lote** al recibir mercadería (en Compras o Productos), con cantidad, fecha de vencimiento y costo por lote
  - El `stock_actual` del producto pasa a ser la **suma de lotes activos** (no un contador global)
  - Política de despacho **FEFO** (First Expired, First Out): al confirmar una venta, el sistema toma automáticamente del lote que vence primero; si no alcanza, sigue con el siguiente
  - Trazabilidad: poder ver de qué lote salió cada item de una venta (y revertir correctamente al anular)
  - Alertas: lotes por vencer (ej. 30/15/7 días) y lotes vencidos (bloqueo de venta + reposición)
  - Reportes: stock desglosado por lote, valorización de stock por costo real de cada lote
  - Decisiones pendientes de diseño:
    - ¿El campo `fecha_vencimiento` actual del producto se mantiene o se elimina? (hoy es a nivel producto, no lote)
    - ¿Productos sin vencimiento también van por lote? (sí, lote sin fecha)
    - ¿El código de barras del producto se mantiene único o cada lote tiene el suyo? (recomendado: único, el lote es interno)
    - ¿FEFO aplica también a la salida por ajuste manual de stock? (sí, pero registrando de qué lote)
  - Impacto grande: modelos `Producto` y `CompraItem` + `VentaItem` + `MovimientoStock` + POS + Compras (recepción) + Reportes + Auditoría
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
