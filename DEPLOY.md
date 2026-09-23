# Deploy & Mantenimiento

## Cómo funciona (IMPORTANTE - leído con sangre)

- **NO hay Vercel ni Supabase vinculados a este proyecto.** El frontend NO se despliega con git push hacia una plataforma externa.
- El **mismo servidor** (`erp-comercio`, systemd + uvicorn) sirve backend **y** frontend: las rutas `/app/*` se sirven desde `frontend/dist/` (estático). Verificado: `GET /app/sw.js` responde 200 desde uvicorn.
- Flujo: **build en la PC local (Windows) → commit + push → `git pull` en el servidor**. El `dist/` se sube a git y el server lo toma con el pull.
- Conclusión: si el `git log -1` del servidor no tiene el último commit local, el cambio no está en producción.

## Cómo verificar la versión desplegada

```bash
cd /opt/erp-comercio
git log --oneline -3              # ¿está el último commit?
ls frontend/dist/index.html       # ¿existe el build nuevo?
```

## Pull y Restart

Frontend (solo frontend, no reinicia backend):
```bash
cd /opt/erp-comercio && sudo -u erp git pull origin master
```

Backend (Python cambios, requiere restart):
```bash
cd /opt/erp-comercio && sudo -u erp git pull origin master && sudo systemctl restart erp-comercio
```

## Migraciones de Base de Datos (SQLite)

**IMPORTANTE:** La base de datos real está en `/data/erp/erp_comercio.db` (configurado en el servicio systemd).
El `settings.DATABASE_URL` puede mostrar un path relativo que no es el real en producción.

1. Verificar el path real de la DB:
```bash
sudo cat /etc/systemd/system/erp-comercio.service | grep DATABASE_URL
```

2. Crear script de migración (ejemplo para agregar 3 columnas):
```bash
cd /opt/erp-comercio && sudo -u erp bash -c 'cat > /tmp/migrate.py << EOF
import sqlite3
conn = sqlite3.connect("/data/erp/erp_comercio.db")
conn.execute("ALTER TABLE venta_items ADD COLUMN oferta_tipo VARCHAR(20)")
conn.execute("ALTER TABLE venta_items ADD COLUMN oferta_valor FLOAT")
conn.execute("ALTER TABLE venta_items ADD COLUMN oferta_info TEXT")
conn.commit()
conn.close()
print("OK")
EOF
'
```

3. Ejecutar:
```bash
cd /opt/erp-comercio && sudo -u erp bash -c 'source venv/bin/activate && python /tmp/migrate.py'
```

4. Restart:
```bash
sudo systemctl restart erp-comercio
```

## Build Frontend (desde local Windows)

```bash
cd frontend
node scripts/prebuild.cjs
node ./node_modules/vite/bin/vite.js build
```

Luego commit y push - el dist/ se sube a git y el server hace pull.

## Nuevas dependencias npm (frontend)

Si localmente se corrió `npm install <paquete>` (ej: `qrcode`), el `package.json` y `package-lock.json` se suben con el commit. En el server NO hace falta instalar cuando el `dist/` ya está compilado y commiteado (se sirve estático). Solo importaría si se compila en el server.

## Cambios de backend que ya se aplicaron (requieren restart)

- **Auto-cierre de caja por cambio de día** (`app/services/caja_service.py`, commit `700bd6c`): si quedó una caja de ayer sin cierre total, se cierra sola al consultar estado o abrir caja hoy; `cerrar_metodo` ya no tira "ya fue cerrado en esta sesión" por cierres de días previos.

## MercadoPago - URL API Sandbox

**Importante:** MercadoPago ya no usa `api.sandbox.mercadopago.com`. El sandbox ahora usa el mismo dominio `api.mercadopago.com` - el ambiente se determina por el access token: `TEST-...` = pruebas/prueba, `APP_USR-...` = producción (cobros reales).

Si falla `crear-sucursal` o `crear-caja` con error DNS, verificar que `_get_api_base()` en `mercadopago_service.py` use solo `https://api.mercadopago.com`.
