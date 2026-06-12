# ERP Comercio — Documento Maestro de Arquitectura

## 1. PROPÓSITO
ERP modular para comercios minoristas (kioscos, almacenes, autoservicios).
Backend robusto con API REST documentada, preparado para escalar a
multi-sucursal y multi-usuario.

## 2. STACK TECNOLÓGICO
- **Lenguaje**: Python 3.11+
- **Framework**: FastAPI (async, OpenAPI/Swagger automático)
- **ORM**: SQLAlchemy 2.0 (async opcional, sincrónico para MVP)
- **Validación**: Pydantic v2
- **Base de datos**: SQLite (dev) → PostgreSQL (prod)
- **Migraciones**: Alembic
- **Auth**: JWT (python-jose) + passlib (bcrypt)
- **Scraping**: requests + BeautifulSoup4 (heredado del MVP)
- **Frontend**: Vue.js 3 + Vite (futuro, no en MVP backend-first)

## 3. ENTIDADES DEL DOMINIO

### 3.1 Producto
Representa un artículo vendible en el comercio.
```
Producto
├── id: int (PK)
├── codigo_barras: str (UNIQUE, NOT NULL)
├── nombre: str (NOT NULL)
├── marca: str (nullable)
├── descripcion: str (nullable)
├── precio_referencia: Decimal  -- precio de góndola en fuente externa
├── precio_costo: Decimal       -- precio de compra al proveedor
├── precio_venta: Decimal       -- precio de venta al público
├── imagen_url: str (nullable)
├── sku: str (nullable)
├── propiedades: JSON           -- ingredientes, nutrición, sellos, etc.
├── fuente: str                 -- "carrefour" | "vea" | "masonline" | "manual"
├── categoria_id: int (FK → Categoria)
├── stock_actual: Decimal (default 0)
├── stock_minimo: Decimal (default 0)
├── activo: bool (default True)
├── ia_analizado: bool (default False)
├── created_at: datetime
├── updated_at: datetime
```
Relaciones:
- Producto *--1 Categoria
- Producto 1--* VentaItem
- Producto 1--* CompraItem
- Producto 1--* MovimientoStock
- Producto 1--* PrecioListItem

### 3.2 Categoría
Clasificación jerárquica de productos.
```
Categoria
├── id: int (PK)
├── nombre: str (UNIQUE, NOT NULL)
├── padre_id: int (FK → Categoria, nullable)  -- subcategorías
├── activo: bool (default True)
├── created_at: datetime
```
Relaciones:
- Categoria 1--* Producto
- Categoria *--1 Categoria (self-referential, padre)

### 3.3 Cliente
Persona o empresa que compra. Opcional en venta (venta al público).
```
Cliente
├── id: int (PK)
├── nombre: str (NOT NULL)
├── tipo_documento: str         -- "DNI", "CUIT", "CUIL"
├── numero_documento: str (UNIQUE, nullable)
├── telefono: str (nullable)
├── email: str (nullable)
├── direccion: str (nullable)
├── saldo_cta_corriente: Decimal (default 0)  -- positivo = nos debe
├── limite_credito: Decimal (default 0)
├── notas: str (nullable)
├── activo: bool (default True)
├── created_at: datetime
├── updated_at: datetime
```
Relaciones:
- Cliente 1--* Venta

### 3.4 Proveedor
Empresa o persona que nos abastece de productos.
```
Proveedor
├── id: int (PK)
├── nombre: str (NOT NULL)
├── cuit: str (UNIQUE, nullable)
├── telefono: str (nullable)
├── email: str (nullable)
├── direccion: str (nullable)
├── nombre_contacto: str (nullable)
├── notas: str (nullable)
├── activo: bool (default True)
├── created_at: datetime
├── updated_at: datetime
```
Relaciones:
- Proveedor 1--* Compra

### 3.5 Venta (Transacción de salida)
Registro de una venta completa. Puede ser con o sin cliente.
```
Venta
├── id: int (PK)
├── numero: str (UNIQUE)        -- "V-00000001" autoincremental
├── cliente_id: int (FK → Cliente, nullable)
├── usuario_id: int (FK → Usuario, NOT NULL)
├── sucursal_id: int (FK → Sucursal, default 1)
├── fecha: datetime (default now)
├── subtotal: Decimal (NOT NULL)
├── descuento: Decimal (default 0)
├── total: Decimal (NOT NULL)
├── medio_pago: str             -- "efectivo", "debito", "credito", "transferencia", "cta_corriente"
├── estado: str                 -- "completada", "anulada"
├── notas: str (nullable)
├── created_at: datetime
```
Relaciones:
- Venta *--1 Cliente (nullable)
- Venta *--1 Usuario
- Venta 1--* VentaItem
- Venta 1--* MovimientoCaja (opcional)

### 3.6 VentaItem (Línea de venta)
Cada producto dentro de una venta. Aquí se registra el precio al momento
de la venta para mantener integridad histórica.
```
VentaItem
├── id: int (PK)
├── venta_id: int (FK → Venta, NOT NULL)
├── producto_id: int (FK → Producto, NOT NULL)
├── cantidad: Decimal (NOT NULL)
├── precio_unitario: Decimal (NOT NULL)  -- precio al momento de la venta
├── precio_costo: Decimal (nullable)     -- costo al momento de la venta
├── subtotal: Decimal (NOT NULL)
```
Relaciones:
- VentaItem *--1 Venta
- VentaItem *--1 Producto

### 3.7 Compra (Transacción de entrada)
Registro de compra a un proveedor.
```
Compra
├── id: int (PK)
├── numero: str (UNIQUE)        -- "C-00000001"
├── proveedor_id: int (FK → Proveedor, NOT NULL)
├── usuario_id: int (FK → Usuario, NOT NULL)
├── sucursal_id: int (FK → Sucursal, default 1)
├── fecha: datetime (default now)
├── subtotal: Decimal (NOT NULL)
├── iva: Decimal (default 0)
├── total: Decimal (NOT NULL)
├── estado: str                 -- "pendiente", "recibida", "anulada"
├── notas: str (nullable)
├── created_at: datetime
```
Relaciones:
- Compra *--1 Proveedor
- Compra *--1 Usuario
- Compra 1--* CompraItem
- Compra 1--* MovimientoCaja (opcional)

### 3.8 CompraItem (Línea de compra)
```
CompraItem
├── id: int (PK)
├── compra_id: int (FK → Compra, NOT NULL)
├── producto_id: int (FK → Producto, NOT NULL)
├── cantidad: Decimal (NOT NULL)
├── precio_unitario: Decimal (NOT NULL)
├── subtotal: Decimal (NOT NULL)
```
Relaciones:
- CompraItem *--1 Compra
- CompraItem *--1 Producto

### 3.9 MovimientoStock
Bitácora de cada cambio en el stock. Generado automáticamente por ventas,
compras, ajustes manuales.
```
MovimientoStock
├── id: int (PK)
├── producto_id: int (FK → Producto, NOT NULL)
├── tipo: str                   -- "entrada" | "salida" | "ajuste"
├── cantidad: Decimal (NOT NULL)
├── stock_anterior: Decimal
├── stock_resultante: Decimal
├── referencia_tipo: str        -- "venta" | "compra" | "ajuste_manual"
├── referencia_id: int          -- ID de la entidad relacionada
├── usuario_id: int (FK → Usuario, NOT NULL)
├── notas: str (nullable)
├── created_at: datetime
```
Relaciones:
- MovimientoStock *--1 Producto
- MovimientoStock *--1 Usuario

### 3.10 MovimientoCaja (Arqueo / Flujo de fondos)
```
MovimientoCaja
├── id: int (PK)
├── tipo: str                   -- "apertura" | "cierre" | "ingreso" | "egreso"
├── monto: Decimal (NOT NULL)
├── descripcion: str
├── referencia_tipo: str (nullable)  -- "venta", "compra", etc.
├── referencia_id: int (nullable)
├── usuario_id: int (FK → Usuario, NOT NULL)
├── sucursal_id: int (FK → Sucursal, default 1)
├── created_at: datetime
```
Relaciones:
- MovimientoCaja *--1 Usuario
- MovimientoCaja *--1 Sucursal

### 3.11 Usuario
Persona que opera el sistema. Autenticación con JWT.
```
Usuario
├── id: int (PK)
├── username: str (UNIQUE, NOT NULL)
├── password_hash: str (NOT NULL)
├── nombre: str (NOT NULL)
├── rol: str                    -- "admin" | "cajero" | "repositor" | "encargado"
├── activo: bool (default True)
├── ultimo_login: datetime (nullable)
├── created_at: datetime
```
Relaciones:
- Usuario 1--* Venta
- Usuario 1--* Compra
- Usuario 1--* MovimientoStock
- Usuario 1--* MovimientoCaja

### 3.12 Sucursal
Punto de venta físico. Prepara para multi-sucursal.
```
Sucursal
├── id: int (PK)
├── nombre: str (NOT NULL)
├── direccion: str (nullable)
├── telefono: str (nullable)
├── activo: bool (default True)
├── created_at: datetime
```
Relaciones:
- Sucursal 1--* Venta
- Sucursal 1--* Compra
- Sucursal 1--* MovimientoCaja

### 3.13 Configuracion
Clave-valor para configuraciones del sistema.
```
Configuracion
├── id: int (PK)
├── clave: str (UNIQUE, NOT NULL)
├── valor: str (NOT NULL)
├── descripcion: str (nullable)
```

## 4. DIAGRAMA DE RELACIONES (TEXTO)

```
Usuario ──┬── Venta ──┬── VentaItem ── Producto ── Categoria
           │            │                    │
           │            │                    ├── MovimientoStock
           │            │                    │
           │            └── MovimientoCaja    └── PrecioListItem (futuro)
           │
           ├── Compra ──┬── CompraItem ──┘
           │            │
           │            └── MovimientoCaja
           │
           ├── MovimientoStock
           └── MovimientoCaja

Cliente ── Venta
Proveedor ── Compra
Sucursal ── Venta, Compra, MovimientoCaja
Categoria (self-referencing: padre)
```

## 5. CICLO DE VIDA DE UNA VENTA (FLUJO PRINCIPAL)

1. Cajero abre sesión (JWT)
2. Cajero inicia venta: POST /api/ventas (estado="pendiente")
3. Escanea productos: POST /api/ventas/{id}/items
   - Cada item descuenta stock → genera MovimientoStock
4. Cajero selecciona medio de pago, aplica descuento si corresponde
5. Cajero confirma venta: PUT /api/ventas/{id}/confirmar
   - Si es "cta_corriente": actualiza saldo del cliente
   - Genera MovimientoCaja (ingreso)
6. Ticket/Factura (futuro)

## 6. ESTRUCTURA DE CARPETAS

```
erp-comercio/
├── MAESTRO.md                   # Este documento
├── requirements.txt
├── alembic.ini                  # Configuración de migraciones
├── .gitignore
├── app/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app, CORS, lifespan
│   ├── config.py                # Settings (DB URL, JWT secret, etc.)
│   ├── database.py              # Engine, SessionLocal, Base
│   ├── models/
│   │   ├── __init__.py          # Importa todos los modelos
│   │   ├── producto.py
│   │   ├── categoria.py
│   │   ├── cliente.py
│   │   ├── proveedor.py
│   │   ├── venta.py             # Venta + VentaItem
│   │   ├── compra.py            # Compra + CompraItem
│   │   ├── movimiento_stock.py
│   │   ├── movimiento_caja.py
│   │   ├── usuario.py
│   │   └── sucursal.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── producto.py
│   │   ├── categoria.py
│   │   ├── cliente.py
│   │   ├── proveedor.py
│   │   ├── venta.py
│   │   ├── compra.py
│   │   ├── caja.py
│   │   ├── usuario.py
│   │   └── common.py            # Paginación, respuestas estándar
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── productos.py
│   │   ├── categorias.py
│   │   ├── clientes.py
│   │   ├── proveedores.py
│   │   ├── ventas.py
│   │   ├── compras.py
│   │   ├── caja.py
│   │   ├── usuarios.py
│   │   ├── dashboard.py
│   │   └── lookup.py            # Búsqueda por código de barras
│   ├── services/
│   │   ├── __init__.py
│   │   ├── producto_service.py  # CRUD + lógica de negocio
│   │   ├── venta_service.py     # Crear, confirmar, anular venta
│   │   ├── stock_service.py     # Movimientos de stock
│   │   ├── caja_service.py      # Apertura/cierre de caja
│   │   └── lookup_service.py    # Scraping adaptado del MVP
│   └── auth/
│       ├── __init__.py
│       ├── security.py          # hash_password, verify_password, create_token
│       └── dependencies.py      # get_current_user, require_role
├── scrapers/
│   ├── __init__.py
│   └── vtex_scraper.py          # Lógica de scraping reutilizable
└── frontend/                    # (futuro Vue.js)
```

## 7. API ENDPOINTS

### Productos
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/productos | Listar (filtro: search, categoria_id, activo) | todos |
| GET | /api/productos/{id} | Detalle | todos |
| POST | /api/productos | Crear manual | admin, encargado |
| PUT | /api/productos/{id} | Actualizar | admin, encargado |
| DELETE | /api/productos/{id} | Desactivar (soft delete) | admin |
| POST | /api/productos/lookup | Buscar por código de barras | todos |

### Categorías
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/categorias | Listar | todos |
| POST | /api/categorias | Crear | admin, encargado |
| PUT | /api/categorias/{id} | Actualizar | admin, encargado |

### Clientes
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/clientes | Listar (filtro: search) | todos |
| GET | /api/clientes/{id} | Detalle + saldo | admin, encargado |
| POST | /api/clientes | Crear | admin, encargado |
| PUT | /api/clientes/{id} | Actualizar | admin, encargado |

### Proveedores
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/proveedores | Listar | admin, encargado |
| POST | /api/proveedores | Crear | admin, encargado |
| PUT | /api/proveedores/{id} | Actualizar | admin, encargado |

### Ventas
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/ventas | Listar (filtro: fecha, estado, cliente) | todos |
| GET | /api/ventas/{id} | Detalle con items | todos |
| POST | /api/ventas | Crear venta | cajero, admin |
| POST | /api/ventas/{id}/items | Agregar ítem | cajero, admin |
| DELETE | /api/ventas/{id}/items/{item_id} | Quitar ítem | cajero, admin |
| PUT | /api/ventas/{id}/confirmar | Confirmar (descarga stock, caja) | cajero, admin |
| PUT | /api/ventas/{id}/anular | Anular (revierte stock) | admin, encargado |

### Compras
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/compras | Listar | admin, encargado |
| POST | /api/compras | Crear compra | admin, encargado |
| POST | /api/compras/{id}/items | Agregar ítem | admin, encargado |
| PUT | /api/compras/{id}/recibir | Recibir (ingresa stock) | admin, encargado |

### Caja
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/caja/estado | Estado actual (abierta/cerrada, saldo) | todos |
| POST | /api/caja/apertura | Abrir caja con monto inicial | cajero, admin |
| POST | /api/caja/cierre | Cerrar caja con arqueo | cajero, admin |
| GET | /api/caja/movimientos | Historial de movimientos | admin, encargado |
| POST | /api/caja/ingreso | Registrar ingreso extra | cajero, admin |
| POST | /api/caja/egreso | Registrar egreso extra | cajero, admin |

### Dashboard
| Método | Ruta | Descripción | Rol |
|--------|------|-------------|-----|
| GET | /api/dashboard/ventas | Ventas del día, del mes | todos |
| GET | /api/dashboard/stock | Productos con stock bajo | admin, encargado |
| GET | /api/dashboard/resumen | KPIs generales | admin, encargado |

### Auth
| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | /api/auth/login | Login (devuelve JWT) |
| POST | /api/auth/register | Registro (solo admin puede) |
| GET | /api/auth/me | Datos del usuario autenticado |

## 8. REGLAS DE NEGOCIO CLAVE

1. **Stock**: No se puede vender más de lo que hay en stock.
2. **Precio histórico**: VentaItem guarda el precio al momento de la venta,
   no el precio actual del producto (si cambia después, la venta ya hecha
   mantiene su valor).
3. **Anulación**: Anular una venta revierte el stock automáticamente.
4. **Caja**: No se puede vender si la caja no está abierta. No se puede
   abrir una caja si ya hay una abierta.
5. **Cta. Corriente**: Si un cliente paga con "cta_corriente", se incrementa
   su saldo. El límite de crédito no se puede exceder.
6. **Soft delete**: Productos y clientes no se borran físicamente, se
   desactivan (activo=False).
7. **Lookup**: La búsqueda por código de barras busca primero en BD local,
   luego en fuentes externas (Carrefour → Vea → Masonline).

## 9. FORMATO DE RESPUESTA ESTÁNDAR

```json
// Éxito
{
  "ok": true,
  "data": { ... },
  "message": "Operación exitosa"
}

// Lista con paginación
{
  "ok": true,
  "data": [ ... ],
  "total": 150,
  "page": 1,
  "page_size": 50
}

// Error
{
  "ok": false,
  "error": "Mensaje descriptivo",
  "detail": "Información adicional (opcional)"
}
```

## 10. PRÓXIMOS PASOS (ROADMAP)

### Fase 1 — Core (ESTA)
- [ ] Modelos SQLAlchemy completos
- [ ] Schemas Pydantic
- [ ] Servicios CRUD básicos
- [ ] Autenticación JWT + roles
- [ ] Endpoints de Productos, Categorías, Lookup
- [ ] Scraper integrado

### Fase 2 — Ventas
- [ ] Módulo de Ventas completo
- [ ] Módulo de Caja (apertura/cierre)
- [ ] Movimientos de Stock automáticos
- [ ] Clientes

### Fase 3 — Compras y Proveedores
- [ ] Módulo de Compras
- [ ] Proveedores
- [ ] Ingreso de stock por compra

### Fase 4 — Frontend
- [ ] Vue.js + Vite
- [ ] Pantalla de ventas (POS)
- [ ] Pantalla de productos
- [ ] Dashboard

### Fase 5 — Reportes y Multi-sucursal
- [ ] Reportes exportables
- [ ] Multi-sucursal
- [ ] Sincronización entre sucursales
