# Contexto — ApexERP

> **Instrucción para el Agente:** Lee este documento al inicio de cada sesión junto con `ESTRUCTURA.md` para entender el contexto global del proyecto, la ubicación de sus módulos y las restricciones de ejecución. No leas otros archivos de documentación a menos que sea explícitamente necesario para la tarea asignada.

> Snapshot del proyecto para retomar sesiones rápido. **Actualizar al cambiar de contexto o al cerrar un hito importante.**

---

## 🏷️ Identidad

| Campo | Valor |
|-------|-------|
| **Nombre** | ApexERP (también "ERP Comercio") |
| **Repo** | `github.com/maxxid/erp.commerce` · branch `master` |
| **Local** | `E:/erp.commerce` (Windows) |
| **Stack** | Python FastAPI + SQLAlchemy + SQLite · Vue 3 (Composition API) + Vite 5 + Tailwind · Pinia |
| **Última release** | commit `3a494b7` (10/08/2026) |

---

## 📌 TL;DR para empezar una sesión

1. `git pull` y leer `SESSION_START.md` (o este archivo + `ESTRUCTURA.md`)
2. Leer `PENDIENTES.md` → sección "En curso" para saber qué retomar
3. Si vas a codear: leer `MAESTRO.md` + `.opencode/instructions.md` + skill `arquitecto-programador`
4. Al cerrar la sesión, actualizar `PENDIENTES.md` con lo hecho

---

## ⚡ Reglas de eficiencia & consumo de tokens

1. **Lectura selectiva:** consulta únicamente los archivos directamente relacionados con la tarea. Apóyate en el índice de `ESTRUCTURA.md`.
2. **Ignorar archivos pesados:** nunca analices `node_modules/`, `dist/`, `.next/`, `build/`, `package-lock.json`, ni logs masivos.
3. **Pausar tras 2 intentos fallidos:** si un comando de prueba/build/refactor falla 2 veces consecutivas, detente, explica brevemente el bloqueo y pide confirmación antes de reintentar.
4. **Respuestas concisas:** límitate a aplicar los cambios requeridos y dar una explicación breve. Evita resúmenes largos no solicitados.
5. **No leer otros `.md`** (MAESTRO, PENDIENTES, etc.) a menos que la tarea lo requiera explícitamente.
6. **Lectura eficiente:** usar `grep`/`read_file` con `offset`/`limit` sobre archivos grandes; nunca `cat` completo de logs, DB o `dist/`. Preferir rangos específicos.

---

## 📚 Cuándo leer cada doc

| Doc | Cuándo |
|---|---|
| `SESSION_START.md` | Entry point mínimo al arrancar una sesión |
| `CONTEXTO.md` | Siempre (identidad, arranque, convenciones) |
| `ESTRUCTURA.md` | Siempre (árbol, capas, vinculaciones) |
| `PENDIENTES.md` | Al arrancar (solo "En curso"/"Completados recientes") |
| `MAESTRO.md` | Solo la sección del módulo a tocar (ver su índice) |
| `API_DOCUMENTACION.md` | Solo si la tarea toca endpoints/contratos |
| `MERCADOPAGO.md` | Solo si la tarea toca MP |
| `DEPLOY.md`/`HOSTING.md` | Solo si la tarea toca deploy/hosting |
| `MULTITENANT.md` | Solo si la tarea toca multi-tenant |
| `FASE_G_CONTINUIDAD.md` | Solo si la tarea toca continuidad/replica |
| `PROJECT_GUIDELINES.md` | Solo si la tarea toca guidelines generales |

---

## 🚀 Cómo arrancar

```bash
# Backend (con venv activado)
cd E:/erp.commerce
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# o: iniciar.bat

# Frontend (dev con HMR)
cd E:/erp.commerce/frontend && npm run dev

# Build de producción (siempre antes de commitear cambios de frontend)
npm run build
```

- **URL local:** `http://localhost:8000/app` · **Login default:** `admin / admin`
- **Licencia:** 30 días de prueba automática al primer arranque
- **DB:** SQLite local (path por defecto en el dir del proyecto)
- `setup.bat` instala todo desde cero (descarga Python 3.12 si no hay compatible).

---

## 🗂️ Estructura y vinculaciones

Ver **`ESTRUCTURA.md`** (árbol de fuente, capas backend/frontend, vinculaciones padre-hijo, convenciones de ubicación). Ignorar siempre: `frontend/dist/`, `node_modules/`, `__pycache__/`, logs, `erp_comercio.db`.

---

## 📐 Convenciones (resumen)

**Código:** sin comentarios salvo que se pidan; sin imports/exports no usados ni código comentado. Backend sync (`crear_producto`, `actualizar_producto`); endpoints async. Errores HTTP: backend `HTTPException(status_code, detail=...)`; frontend `toast.error(e?.response?.data?.detail || e.message)`.

**Frontend:** Composition API con `<script setup>`; `import api from '@/services/api'` (desenvuelve `RespuestaData { data, message }`); formateo monetario `formatCurrency as fc` desde `useUtils`; iconos FontAwesome `fa-solid fa-xxx`; modales `<BaseModal :model-value="show" @update:model-value="emit('close')">` (nunca `v-model` con props); stores globales solo `useAuthStore` y `useCajaStore`.

**Migraciones:** auto al arrancar (`_migrate_new_columns()` en `app/main.py:243-259`); columnas nuevas con `ALTER TABLE ... ADD COLUMN` + check `PRAGMA table_info(...)`. No hay Alembic.

**Frontend build:** `frontend/dist/` está commiteado (lo sirve FastAPI en `/app`). Siempre `npm run build` antes de commitear cambios de frontend.

---

## 🔧 Git

Política: auto commit + push después de cada cambio relevante. Mensajes en español, lowercase después del scope, descripción clara. Tipos: `feat, fix, refactor, chore, docs, build, ui, debug`. Cada commit debe dejar el sistema funcional. Si algo se rompe: `git revert HEAD` + push.

---

## 🧠 Conocimiento del dominio / gotchas / troubleshooting

Movidos a `PENDIENTES.md` → sección "Contexto de sesión (movido desde CONTEXTO.md)" para no duplicar. Leer ahí cuando la tarea toque facturación ARCA, MercadoPago, caja, stock, migraciones o licencias.