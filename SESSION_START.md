# Session Start — ApexERP

> **Entrada mínima para una nueva sesión.** Leer este archivo (y solo este) al arrancar; el resto on-demand.

## 1. Git

```bash
git pull
git status
```

## 2. Leer (en este orden, completos)

1. `CONTEXTO.md` — identidad, arranque, convenciones, git
2. `ESTRUCTURA.md` — árbol, capas, vinculaciones, dónde agregar
3. `PENDIENTES.md` → solo sección "En curso" / "Completados recientes"

## 3. Si vas a codear

- `MAESTRO.md` → solo la sección del módulo a tocar (ver índice "Cómo usar este documento")
- `.opencode/instructions.md` + skill `arquitecto-programador`
- No leer otros `.md` salvo que la tarea lo requiera

## 4. Arranque local

```bash
# Backend
cd E:/erp.commerce && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
# Frontend (dev)
cd E:/erp.commerce/frontend && npm run dev
# Build (antes de commitear cambios frontend)
npm run build
```

URL: `http://localhost:8000/app` · login `admin/admin`

## 5. Reglas de eficiencia

- Lectura selectiva: solo archivos directamente relacionados con la tarea.
- Ignorar: `node_modules/`, `dist/`, `__pycache__/`, logs, `erp_comercio.db`, `catalogo_*.json`.
- Usar `grep`/`read_file` con `offset`/`limit`; nunca `cat` de archivos grandes.
- Pausar tras 2 intentos fallidos y pedir confirmación.
- Respuestas concisas; no resúmenes largos no solicitados.

## 6. Al cerrar la sesión

Actualizar `PENDIENTES.md` con lo hecho. Auto commit + push si hubo cambios.