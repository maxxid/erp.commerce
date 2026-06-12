API ERP Comercio — Documentación para Frontend
================================================

URL Base: http://localhost:8000
Swagger interactivo: http://localhost:8000/docs
Autenticación: JWT Bearer Token


═══════════════════════════════════════════════════════════════
1. FORMATO GENERAL DE RESPUESTA
═══════════════════════════════════════════════════════════════

Todas las respuestas exitosas siguen este formato:

  Éxito (single):
  {
    "ok": true,
    "message": "Mensaje descriptivo",
    "data": { ... }
  }

  Éxito (lista):
  {
    "ok": true,
    "message": "N producto(s)",
    "data": [ ... ],
    "total": 150,
    "page": 1,
    "page_size": 50
  }

  Error:
  {
    "detail": "Mensaje de error"
  }
  (HTTP status code != 200)


═══════════════════════════════════════════════════════════════
2. AUTENTICACIÓN
═══════════════════════════════════════════════════════════════

2.1 POST /api/auth/login
─────────────────────────
Request:
  {
    "username": "admin",
    "password": "admin"
  }

Response (200):
  {
    "ok": true,
    "message": "Login exitoso",
    "data": {
      "access_token": "eyJhbGciOi...",
      "token_type": "bearer",
      "username": "admin",
      "rol": "admin",
      "nombre": "Administrador"
    }
  }

Response (401):
  { "detail": "Usuario o contraseña incorrectos" }

► Todas las demás peticiones requieren header:
  Authorization: Bearer {access_token}

2.2 GET /api/auth/me
─────────────────────
Response (200):
  {
    "ok": true,
    "data": {
      "id": 1,
      "username": "admin",
      "nombre": "Administrador",
      "rol": "admin",
      "ultimo_login": "2026-06-12T02:00:00"
    }
  }

Roles disponibles: "admin", "cajero", "encargado", "repositor"


═══════════════════════════════════════════════════════════════
3. PRODUCTOS
═══════════════════════════════════════════════════════════════

3.1 GET /api/productos
───────────────────────
Query params (todos opcionales):
  search        string   Búsqueda en nombre, código, marca
  categoria_id  int      Filtrar por categoría
  solo_activos  bool     default true
  page          int      default 1
  page_size     int      default 50, max 200

Response (200):
  {
    "ok": true,
    "message": "1 producto(s)",
    "data": [
      {
        "id": 1,
        "codigo_barras": "7790895000997",
        "nombre": "Gaseosa cola - Coca Cola sabor original 2,25 lts",
        "marca": "Coca Cola",
        "descripcion": "Gaseosa Coca-cola Sabor Original 2.25 L",
        "precio_referencia": 5650.0,
        "precio_costo": 900.0,
        "precio_venta": 7500.0,
        "imagen_url": "https://...vtexassets.com/.../783070/...",
        "sku": "00246613",
        "propiedades": { "Ingredientes": "...", "Tabla Nutricional": "...", "Sellos": "..." },
        "fuente": "carrefour",
        "categoria_id": 1,
        "categoria_nombre": "Bebidas",
        "stock_actual": 50.0,
        "stock_minimo": 5.0,
        "activo": true,
        "ia_analizado": false,
        "created_at": "2026-06-12T02:00:00",
        "updated_at": "2026-06-12T02:00:00"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50
  }


3.2 GET /api/productos/{id}
────────────────────────────
Response (200): Igual estructura que el item de la lista, dentro de "data".

Response (404):
  { "detail": "Producto no encontrado" }


3.3 POST /api/productos
────────────────────────
Crea un producto manualmente. Requiere rol: admin, encargado.

Request:
  {
    "codigo_barras": "7790000000001",
    "nombre": "Producto Nuevo",
    "marca": "Marca X",
    "descripcion": "Opcional",
    "precio_referencia": 1500.0,
    "precio_costo": 900.0,
    "precio_venta": 2200.0,
    "imagen_url": "https://...",
    "sku": "ABC123",
    "propiedades": { "Tipo": "Almacén", "Peso": "500g" },
    "fuente": "manual",
    "categoria_id": 1,
    "stock_minimo": 10.0,
    "cantidad_inicial": 20.0
  }

Campos requeridos: codigo_barras, nombre
Campos opcionales: todos los demás
cantidad_inicial: stock con el que arranca (default 0)

Response (200):
  {
    "ok": true,
    "message": "Producto creado",
    "data": { ...producto completo... }
  }

Response (400):
  { "detail": "Ya existe un producto con código 7790000000001" }


3.4 PUT /api/productos/{id}
────────────────────────────
Actualiza un producto. Requiere rol: admin, encargado.
Todos los campos son opcionales (solo se actualiza lo enviado).

Request:
  {
    "nombre": "Nuevo Nombre",
    "precio_venta": 2500.0,
    "stock_minimo": 15.0,
    "activo": false
  }

Response (200):
  { "ok": true, "message": "Producto actualizado", "data": { ... } }


3.5 POST /api/productos/lookup  (¡IMPORTANTE!)
────────────────────────────────────────────────
Busca producto por código de barras en fuentes externas.
Primero busca en BD local. Si no existe, busca en:
Carrefour → Vea → Masonline.

Request:
  {
    "barcode": "7790895000997",
    "fuente": null,
    "ia_mode": false
  }

  barcode: obligatorio
  fuente:  opcional ("carrefour"|"vea"|"masonline"). null = busca en las 3 en orden.
  ia_mode: booleano, para futuro análisis con IA.

Response — Producto nuevo (200):
  {
    "ok": true,
    "message": "Producto encontrado",
    "data": {
      "codigo_barras": "7790895000997",
      "nombre": "Gaseosa cola - Coca Cola sabor original 2,25 lts",
      "marca": "Coca Cola",
      "descripcion": "Gaseosa Coca-cola Sabor Original 2.25 L",
      "precio_referencia": 5650.0,
      "imagen_url": "https://...",
      "sku": "00246613",
      "propiedades": { "Ingredientes": "...", ... },
      "fuente": "carrefour",
      "url": "https://www.carrefour.com.ar/gaseosa-cola-.../p",
      "descuento": {
        "activo": true,
        "precio_original": null,
        "precio_oferta": null,
        "promocion": "PROMO-2do al 50%..."
      },
      "categoria": "Bebidas",
      "ia_mode": false,
      "_cached": false,
      "comparacion": [
        {
          "fuente": "carrefour",
          "precio": 5650.0,
          "nombre": "Gaseosa cola - ...",
          "url": "https://www.carrefour.com.ar/.../p",
          "descuento": { "activo": true, "promocion": "PROMO-2do al 50%..." }
        },
        {
          "fuente": "vea",
          "precio": 5647.0,
          "nombre": "Gaseosa - Coca-cola...",
          "url": "https://www.vea.com.ar/.../p",
          "descuento": { "activo": true, "promocion": "2do al 50%" }
        },
        {
          "fuente": "masonline",
          "precio": 5649.0,
          "nombre": "Gaseosa - Coca Cola...",
          "url": "https://www.masonline.com.ar/.../p",
          "descuento": null
        }
      ]
    }
  }

Response — Producto ya guardado (200):
  Igual al de arriba pero con:
    "_cached": true,
    "precio_venta": 7500.0,
    "cantidad": 10.0,
    "categoria_id": 1,
    "stock_actual": 10.0,
    ...
    (tiene todos los campos de un producto guardado)
    (NO incluye "comparacion" — hay que llamar al lookup con fuente específica)

Response — No encontrado (404):
  { "detail": "Producto no encontrado" }

► FLUJO RECOMENDADO PARA FRONTEND:
  1. POST /api/productos/lookup { barcode } → obtiene datos primarios
  2. Mostrar tarjeta con 3 badges en carga (⟳ CARREFOUR, ⟳ VEA, ⟳ MASONLINE)
  3. En paralelo, hacer 3 POST /api/productos/lookup { barcode, fuente: "carrefour"|"vea"|"masonline" }
  4. Actualizar cada badge cuando llegue su respuesta (precio, url, descuento)
  5. Cada badge es un <a href="url"> al producto en esa fuente


═══════════════════════════════════════════════════════════════
4. CATEGORÍAS
═══════════════════════════════════════════════════════════════

4.1 GET /api/categorias
────────────────────────
Response (200):
  {
    "ok": true,
    "data": [
      { "id": 1, "nombre": "Bebidas", "padre_id": null, "activo": true,
        "cantidad_productos": 5, "created_at": "..." },
      { "id": 2, "nombre": "Almacén", "padre_id": null, "activo": true,
        "cantidad_productos": 3, "created_at": "..." }
    ],
    "total": 7
  }


4.2 POST /api/categorias
─────────────────────────
Request:  { "nombre": "Nueva Categoría", "padre_id": null }
Response: { "ok": true, "data": { ...categoria... } }


4.3 PUT /api/categorias/{id}
─────────────────────────────
Request:  { "nombre": "Renombrada", "activo": false }
Response: { "ok": true, "data": { ... } }


═══════════════════════════════════════════════════════════════
5. CAJA
═══════════════════════════════════════════════════════════════

► REGLA: No se puede vender sin caja abierta.

5.1 GET /api/caja/estado
─────────────────────────
Response (200):
  {
    "ok": true,
    "data": {
      "abierta": true,
      "saldo_actual": 72000.0
    }
  }

  abierta: true si la caja está abierta (hubo apertura sin cierre)
  saldo_actual: suma de ingresos - egresos desde la última apertura


5.2 POST /api/caja/apertura
────────────────────────────
Request:
  {
    "monto_inicial": 50000.0,
    "sucursal_id": 1
  }

Response (200):
  {
    "ok": true,
    "message": "Caja abierta",
    "data": {
      "id": 1,
      "monto": 50000.0,
      "tipo": "apertura"
    }
  }

Error (400):
  { "detail": "Ya hay una caja abierta. Ciérrela primero." }


5.3 POST /api/caja/cierre
──────────────────────────
Request:
  {
    "monto_real": 72000.0,
    "sucursal_id": 1
  }

  monto_real: el dinero contado físicamente

Response (200):
  {
    "ok": true,
    "message": "Caja cerrada. Diferencia: $0.00",
    "data": {
      "id": 1,
      "monto_real": 72000.0,
      "saldo_esperado": 72000.0,
      "diferencia": 0.0
    }
  }

  diferencia: negativo = faltante, positivo = sobrante, 0 = arqueo perfecto


5.4 POST /api/caja/ingreso
───────────────────────────
Registra un ingreso extra (no asociado a venta). Requiere caja abierta.

Request:
  {
    "monto": 5000.0,
    "descripcion": "Depósito bancario",
    "sucursal_id": 1
  }

5.5 POST /api/caja/egreso
──────────────────────────
Registra un egreso/retiro. Requiere caja abierta.

Request:
  {
    "monto": 2000.0,
    "descripcion": "Pago proveedor",
    "sucursal_id": 1
  }

5.6 GET /api/caja/movimientos
──────────────────────────────
Query: page, page_size
Response: Lista de movimientos (apertura, cierre, ingresos, egresos).


═══════════════════════════════════════════════════════════════
6. VENTAS
═══════════════════════════════════════════════════════════════

► REGLAS:
  - La caja debe estar abierta para confirmar una venta.
  - Stock se descuenta automáticamente al confirmar.
  - Si el medio de pago es "cta_corriente", se actualiza el saldo del cliente.
  - Solo admin/encargado puede anular una venta ya confirmada.

6.1 GET /api/ventas
────────────────────
Query (opcionales):
  estado     string   "pendiente" | "confirmada" | "anulada"
  cliente_id int
  page, page_size

Response (200):
  {
    "ok": true,
    "data": [
      {
        "id": 1,
        "numero": "V-00000001",
        "cliente_id": null,
        "usuario_id": 1,
        "sucursal_id": 1,
        "fecha": "2026-06-12T02:29:45",
        "subtotal": 22500.0,
        "descuento": 500.0,
        "total": 22000.0,
        "medio_pago": "efectivo",
        "estado": "confirmada",
        "notas": null,
        "items": [
          {
            "id": 1,
            "producto_id": 1,
            "producto_nombre": "Coca Cola 2.25L",
            "cantidad": 3.0,
            "precio_unitario": 7500.0,
            "precio_costo": 900.0,
            "subtotal": 22500.0
          }
        ],
        "created_at": "2026-06-12T02:29:45"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50
  }


6.2 GET /api/ventas/{id}
─────────────────────────
Response (200): Igual estructura que un item de la lista.


6.3 POST /api/ventas
─────────────────────
Crea una venta vacía en estado "pendiente".
Requiere rol: admin, cajero.

Request:
  {
    "cliente_id": null,
    "sucursal_id": 1,
    "notas": "Venta mostrador"
  }

  Todos los campos son opcionales (default: cliente_id=null, sucursal_id=1)

Response (200):
  {
    "ok": true,
    "message": "Venta V-00000001 creada",
    "data": {
      "id": 1,
      "numero": "V-00000001",
      "cliente_id": null,
      "usuario_id": 1,
      "sucursal_id": 1,
      "fecha": "2026-06-12T02:29:45",
      "subtotal": 0.0,
      "descuento": 0.0,
      "total": 0.0,
      "medio_pago": "efectivo",
      "estado": "pendiente",
      "notas": null,
      "items": [],
      "created_at": "2026-06-12T02:29:45"
    }
  }


6.4 POST /api/ventas/{venta_id}/items
──────────────────────────────────────
Agrega un producto a la venta pendiente.
Requiere rol: admin, cajero.

Request:
  {
    "producto_id": 1,
    "cantidad": 3.0,
    "precio_unitario": 7500.0
  }

  precio_unitario: opcional. Si no se envía, usa el precio_venta del producto.

Response (200):
  {
    "ok": true,
    "message": "Ítem agregado",
    "data": {
      "item_id": 1,
      "subtotal": 22500.0,
      "venta_subtotal": 22500.0
    }
  }

Error (400):
  { "detail": "Stock insuficiente para 'Coca Cola': disponible=50, requerido=100" }
  { "detail": "Solo se pueden modificar ventas pendientes" }


6.5 DELETE /api/ventas/{venta_id}/items/{item_id}
───────────────────────────────────────────────────
Quita un ítem de la venta pendiente.

Response (200):
  {
    "ok": true,
    "message": "Ítem quitado",
    "data": { "venta_subtotal": 0.0 }
  }


6.6 PUT /api/ventas/{venta_id}/confirmar
─────────────────────────────────────────
Confirma la venta: descuenta stock, registra en caja.
Requiere rol: admin, cajero.

Request:
  {
    "medio_pago": "efectivo",
    "descuento": 500.0
  }

  medio_pago: "efectivo" | "debito" | "credito" | "transferencia" | "cta_corriente"
  descuento: monto a descontar del total (default 0)

Response (200):
  {
    "ok": true,
    "message": "Venta V-00000001 confirmada. Total: $22,000.00",
    "data": {
      "id": 1,
      "numero": "V-00000001",
      "subtotal": 22500.0,
      "descuento": 500.0,
      "total": 22000.0,
      "medio_pago": "efectivo",
      "estado": "confirmada",
      "items": [...],
      ...
    }
  }

Errores (400):
  { "detail": "Stock insuficiente para 'Coca Cola': disponible=2, requerido=3" }
  { "detail": "La caja no está abierta. Ábrala para poder vender." }
  { "detail": "Excede límite de crédito de Juan: límite=$50,000, adeudaría=$72,000" }
  { "detail": "La venta ya fue procesada" }


6.7 PUT /api/ventas/{venta_id}/anular
──────────────────────────────────────
Anula una venta confirmada. Revierte stock y caja.
SOLO admin o encargado.

Response (200):
  {
    "ok": true,
    "message": "Venta V-00000001 anulada",
    "data": { ...venta con estado "anulada"... }
  }

Error (400):
  { "detail": "Solo se pueden anular ventas confirmadas" }


► FLUJO COMPLETO DE VENTA:
  1. GET  /api/caja/estado           → verificar que caja esté abierta
  2. POST /api/ventas                → crear venta (estado: "pendiente")
  3. POST /api/ventas/{id}/items     → agregar cada producto escaneado
     (repetir paso 3 por cada producto)
  4. PUT  /api/ventas/{id}/confirmar → confirmar con medio_pago
  5. GET  /api/caja/estado           → verificar nuevo saldo


═══════════════════════════════════════════════════════════════
7. COMPRAS
═══════════════════════════════════════════════════════════════

7.1 GET /api/compras
─────────────────────
Query (opcionales): estado, proveedor_id, page, page_size

Response (200):
  {
    "ok": true,
    "data": [
      {
        "id": 1,
        "numero": "C-00000001",
        "proveedor_id": 1,
        "proveedor_nombre": "Distribuidora SA",
        "usuario_id": 1,
        "sucursal_id": 1,
        "fecha": "2026-06-12T02:40:36",
        "subtotal": 12500.0,
        "iva": 0.0,
        "total": 12500.0,
        "estado": "recibida",
        "notas": null,
        "items": [
          {
            "id": 1,
            "producto_id": 2,
            "producto_nombre": "Prod ABC1",
            "cantidad": 10.0,
            "precio_unitario": 800.0,
            "subtotal": 8000.0
          },
          {
            "id": 2,
            "producto_id": 2,
            "producto_nombre": "Prod ABC1",
            "cantidad": 5.0,
            "precio_unitario": 900.0,
            "subtotal": 4500.0
          }
        ],
        "created_at": "2026-06-12T02:40:36"
      }
    ],
    "total": 1,
    "page": 1,
    "page_size": 50
  }


7.2 GET /api/compras/{id}
──────────────────────────
Response (200): Igual estructura que item de la lista.


7.3 POST /api/compras
──────────────────────
Crea una compra vacía en estado "pendiente".
Requiere rol: admin, encargado.

Request:
  {
    "proveedor_id": 1,
    "sucursal_id": 1,
    "notas": "Compra semanal"
  }

Response (200):
  {
    "ok": true,
    "message": "Compra C-00000001 creada",
    "data": { ...compra con estado "pendiente", items: []... }
  }


7.4 POST /api/compras/{compra_id}/items
────────────────────────────────────────
Agrega un producto a la compra.

Request:
  {
    "producto_id": 2,
    "cantidad": 10.0,
    "precio_unitario": 800.0
  }

  Todos los campos obligatorios.

Response (200):
  {
    "ok": true,
    "message": "Ítem agregado",
    "data": {
      "item_id": 1,
      "subtotal": 8000.0,
      "compra_subtotal": 8000.0
    }
  }


7.5 DELETE /api/compras/{compra_id}/items/{item_id}
────────────────────────────────────────────────────
Quita un ítem de la compra pendiente.

Response (200):
  { "ok": true, "data": { "compra_subtotal": 0.0 } }


7.6 PUT /api/compras/{compra_id}/recibir
─────────────────────────────────────────
Recibe la mercadería: ingresa stock, actualiza precio_costo del producto.

Response (200):
  {
    "ok": true,
    "message": "Compra C-00000001 recibida. Stock actualizado.",
    "data": { ...compra con estado "recibida"... }
  }


7.7 PUT /api/compras/{compra_id}/anular
────────────────────────────────────────
Anula una compra pendiente. No revierte stock (nunca se recibió).

Response (200):
  { "ok": true, "data": { ...compra con estado "anulada"... } }


► FLUJO COMPLETO DE COMPRA:
  1. POST /api/proveedores          → crear proveedor (si no existe)
  2. POST /api/compras              → crear compra (estado: "pendiente")
  3. POST /api/compras/{id}/items   → agregar cada producto
     (repetir paso 3 por cada producto)
  4. PUT  /api/compras/{id}/recibir → confirmar recepción (actualiza stock)


═══════════════════════════════════════════════════════════════
8. PROVEEDORES
═══════════════════════════════════════════════════════════════

8.1 GET /api/proveedores
─────────────────────────
Query: search, page, page_size

Response (200):
  {
    "ok": true,
    "data": [
      {
        "id": 1,
        "nombre": "Distribuidora SA",
        "cuit": "30-99999999-9",
        "telefono": "1144445555",
        "email": null,
        "direccion": null,
        "nombre_contacto": "Juan",
        "notas": null,
        "activo": true,
        "created_at": "2026-06-12T02:40:02"
      }
    ],
    "total": 1
  }


8.2 GET /api/proveedores/{id}
──────────────────────────────
Response (200): { "ok": true, "data": { ...proveedor... } }


8.3 POST /api/proveedores
──────────────────────────
Request:
  {
    "nombre": "Distribuidora SA",
    "cuit": "30-99999999-9",
    "telefono": "1144445555",
    "nombre_contacto": "Juan"
  }

Response (200): { "ok": true, "message": "Proveedor creado", "data": { ... } }


8.4 PUT /api/proveedores/{id}
──────────────────────────────
Request: { "telefono": "1155556666", "activo": true }


═══════════════════════════════════════════════════════════════
9. CLIENTES
═══════════════════════════════════════════════════════════════

9.1 GET /api/clientes
──────────────────────
Query: search, page, page_size

Response (200):
  {
    "ok": true,
    "data": [
      {
        "id": 1,
        "nombre": "Juan Pérez",
        "tipo_documento": "DNI",
        "numero_documento": "30123456",
        "telefono": "1166667777",
        "email": null,
        "direccion": null,
        "saldo_cta_corriente": 22000.0,
        "limite_credito": 50000.0,
        "notas": null,
        "activo": true,
        "created_at": "...",
        "updated_at": "..."
      }
    ]
  }

9.2 POST /api/clientes
───────────────────────
Request:
  {
    "nombre": "Juan Pérez",
    "tipo_documento": "DNI",
    "numero_documento": "30123456",
    "telefono": "1166667777",
    "limite_credito": 50000.0
  }

9.3 PUT /api/clientes/{id}
───────────────────────────
Request: { "limite_credito": 100000.0 }


═══════════════════════════════════════════════════════════════
10. DASHBOARD
═══════════════════════════════════════════════════════════════

10.1 GET /api/dashboard/resumen
────────────────────────────────
Response (200):
  {
    "ok": true,
    "data": {
      "total_productos": 15,
      "valor_stock": 375000.0,
      "total_clientes": 3,
      "stock_bajo": 2,
      "ventas_hoy": 22000.0,
      "ventas_mes": 22000.0,
      "ultimo_producto": {
        "nombre": "Coca Cola 2.25L",
        "codigo_barras": "7790895000997",
        "fecha": "2026-06-12T02:29:45"
      }
    }
  }

  valor_stock: suma de (precio_venta × stock_actual) de productos activos
  stock_bajo: productos con stock_actual ≤ stock_minimo
  ventas_hoy: total de ventas confirmadas del día
  ventas_mes: total de ventas confirmadas del mes


═══════════════════════════════════════════════════════════════
11. RESUMEN DE FLUJOS PRINCIPALES
═══════════════════════════════════════════════════════════════

► INICIO DE JORNADA:
  POST /api/auth/login
  POST /api/caja/apertura  { monto_inicial: 50000 }

► VENDER UN PRODUCTO (con lector de código de barras):
  POST /api/productos/lookup { barcode: "7790895000997" }
  → Si no está en BD local, lo busca en fuentes externas.
  → Si no existe, mostrarlo con opción de guardar primero.

  POST /api/ventas              → crear venta
  POST /api/ventas/{id}/items   → agregar producto (repetir por cada uno)
  PUT  /api/ventas/{id}/confirmar → confirmar

► RECIBIR MERCADERÍA:
  POST /api/compras                 → crear compra
  POST /api/compras/{id}/items      → agregar producto (repetir)
  PUT  /api/compras/{id}/recibir    → confirmar recepción

► CIERRE DE JORNADA:
  GET  /api/caja/estado              → ver saldo esperado
  POST /api/caja/cierre { monto_real: 72000 } → cerrar con arqueo


═══════════════════════════════════════════════════════════════
12. NOTAS PARA EL FRONTEND
═══════════════════════════════════════════════════════════════

- Todos los precios están en ARS (pesos argentinos), como float.
- Formatear: $ 1.500,00 (es-AR).
- Los estados de venta son: "pendiente" → "confirmada" → (opcional "anulada").
- Los estados de compra son: "pendiente" → "recibida" → (opcional "anulada").
- Una venta pendiente se puede modificar (agregar/quitar items).
  Una vez confirmada o anulada, es inmutable.
- Al confirmar venta con "cta_corriente", el saldo del cliente aumenta.
  Al anular, se revierte.
- propiedad "categoria" en lookup viene como string ("Bebidas"), no como ID.
- propiedad "descuento" puede ser null o { activo: true, promocion: "..." }.
  Si activo es true y hay precio_oferta, mostrar OFERTA.
  Si activo es true y no hay precio pero sí promocion, mostrar PROMO.
- Los badges de comparación de precios deben cargarse en paralelo para
  mejor UX (uno por fuente, no esperar a los 3).
- La caja debe estar abierta para confirmar ventas.
  Mostrar alerta si se intenta confirmar sin caja abierta.
