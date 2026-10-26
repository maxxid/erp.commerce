# Deploy & Mantenimiento

> **Instrucción para el Agente:** Guía de deploy, migraciones y troubleshooting del servidor. Leer solo cuando se despliega, se migra la DB o se diagnostica un 502. No leer por defecto.

## Deploy & Mantenimiento

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

Backend (cambios en Python, requiere instalar dependencias y reiniciar):
```bash
cd /opt/erp-comercio
sudo -u erp git pull origin master
sudo -u erp bash -c 'source venv/bin/activate && pip install -r requirements.txt'
sudo systemctl restart erp-comercio
sudo systemctl status erp-comercio --no-pager
```

**El `pip install` no es opcional.** Si se omite y el commit nuevo toca imports o
suma una dependencia a `requirements.txt`, el restart tira la app abajo. Paso el
30/09/2026
se instaló en el server, y el `systemctl restart` del deploy tumbó la app entera
(502 en todo, `restart counter is at 40`). El servicio venía corriendo con código
viejo en memoria desde antes de que ese módulo existiera; el restart lo obligó a
importar todo de cero.

Los cambios de frontend (solo `frontend/dist`) no necesitan el `pip install`,
pero correrlo no hace daño.

## Si el servicio no levanta (502 en toda la app)

Un 502 significa que nginx no encuentra el backend. Casi siempre es que uvicorn
no arrancó. El error real está en el journal, no en el status:

```bash
sudo systemctl status erp-comercio --no-pager -l
sudo journalctl -u erp-comercio -n 80 --no-pager
```

El dato útil es la última línea del traceback. Si el status dice
`activating (auto-restart)` con `restart counter is at N`, está en loop: paralo
mientras se arregla, porque quema CPU y llena el journal.

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `ModuleNotFoundError: No module named 'X'` con `X` de librería (reportlab, pandas, etc.) | Falta una dependencia en el venv | `pip install -r requirements.txt` y reiniciar |
| `ModuleNotFoundError` en un módulo propio (`app.*`) | Pull a medias o archivo faltante | `git status`, `git log --oneline -1` |
| `NameError` al importar | Código a medias en el working tree | `git status`, `git log --oneline -1` |

Si el traceback termina en un import de terceros, casi siempre falta el
`pip install`. `requirements.txt` es la fuente de verdad: si la librería no está
ahí, el primer error será un `ModuleNotFoundError` en tiempo de import. Y aunque
esté ahi, hay que correr el install en el venv del server (`/opt/erp-comercio/venv`).

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

## Litestream — réplica en vivo (Fase G)

Corre **aparte** de la app: es un servicio de systemd propio que va subiendo la
base a R2 en vivo para que la secundaria pueda restaurarla (ver
`FASE_G_CONTINUIDAD.md`).

```bash
sudo systemctl status litestream --no-pager      # tiene que decir "active (running)"
sudo /usr/local/bin/litestream status -config /etc/litestream.yml
sudo journalctl -u litestream -n 30 --no-pager
sudo systemctl restart litestream
```

- Config en `/etc/litestream.yml` (generada desde las credenciales R2 que viven
  en la base; `root:erp` 640 — **no commitearla ni volcarla en el chat**).
- La app sólo monitorea la réplica si el unit file de `erp-comercio` tiene
  `Environment=LITESTREAM_HABILITADO=true`. Si alguien lo saca, el chequeo de
  salud deja de mirarla en silencio (los respaldos siguen igual).
- **Ojo con `git pull`**: no toca `/etc/` ni los services, un deploy normal no
  lo apaga.
- La base está en **WAL** por ahora; `app/database.py` la mantiene así. No
  cambiarla a `delete`: Litestream sólo puede replicar en WAL.

## Clientes en Docker (multi-cliente — Fase 1)

> **La VM actual es `VM.Standard.E2.1.Micro` (2 vCPU, 1 GB)** y comparte RAM con
> el POS. El 26/10/2026 se ensayó con **un** `cliente-demo` de 256 MB y se detuvo;
> Docker quedó instalado pero **deshabilitado**. Para clientes reales hace falta
> una VM aparte (A1.Flex free o paga, ver `MULTITENANT.md` §9).
>
> Para repetir el ensayo: `sudo systemctl start docker` y después
> `cd /srv/erp-clientes/cliente-demo && sudo docker compose up -d`.

El ERP del dueño sigue en systemd como siempre. Los clientes son **contenedores
aparte**, cada uno con su SQLite, su subdominio y su licencia. El diseño completo
y los runbooks están en **`MULTITENANT.md`**; acá va sólo lo operativo.

### Construir la imagen

```bash
cd /opt/erp-comercio
git pull origin master
docker build -t erp-comercio:$(git rev-parse --short HEAD) .
```

`frontend/dist` viaja commiteado: no hay que compilar en el servidor. La imagen
lleva `curl` y `openssl` porque AFIP los usa por subprocess.

### Alta de un cliente

```bash
python3 deploy/clientes/alta_cliente.py \
  --slug cliente1 \
  --nombre "Almacén Don José" \
  --dominio cliente1.erp.imprenta.store \
  --plan trial --dias 30
```

El script crea `/srv/erp-clientes/<slug>/`, genera los secretos, siembra la
licencia, levanta el contenedor, arma el vhost de nginx y hace smoke test. El
registro queda en `/srv/erp-clientes/clientes.json`.

### Actualizar todos los clientes

```bash
deploy/clientes/actualizar_clientes.sh <git-sha>
```

### Comandos por cliente

```bash
cd /srv/erp-clientes/cliente1
docker compose ps
docker compose logs -f --tail=100
docker compose restart
docker compose stop     # no borra datos
```

### Reglas que no se rompen

- **No tocar** el unit `erp-comercio` ni `litestream` desde acá: son del ERP del
  dueño y de la Fase G.
- El `MACHINE_ID` del cliente **es su slug** y no se cambia: la licencia está
  atada a él. Tampoco cambiar el `hostname` del contenedor.
- Los respaldos del cliente van a `backups/<slug>/` en R2, no se mezclan.
- La restauración es manual y está en `MULTITENANT.md` §6.
