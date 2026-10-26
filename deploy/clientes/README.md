# Clientes en Docker (multi-instance)

Un contenedor + una SQLite + un subdominio + una licencia **por cliente**, en una
**VM dedicada a clientes**. La VM actual del ERP es una `E2.1.Micro` de 1 GB y
**no alcanza** para producción; el ERP del dueño sigue en systemd (`:8000`) y
**no** se toca.

El diseño completo, las decisiones y los límites están en **`MULTITENANT.md`**.
Acá está sólo el uso de los scripts.

## Requisitos en el servidor

- Docker + Compose v2 (`docker compose version`).
- nginx y certbot (los instala `setup-oracle.sh`).
- Imagen construida: `docker build -t erp-comercio:<git-sha> /opt/erp-comercio`.
- DNS: `A clienteN.erp.imprenta.store` → IP de la VM.
- Root para el alta (crea usuarios de archivos, nginx y certificados).

## Alta

```bash
python3 deploy/clientes/alta_cliente.py \
  --slug cliente1 \
  --nombre "Almacén Don José" \
  --dominio cliente1.erp.imprenta.store \
  --plan trial --dias 30 \
  --imagen erp-comercio:<git-sha> \
  --certbot-email dueno@imprenta.store
```

Opcionales útiles:

- `--memoria 256m`: límite de RAM del contenedor (default `512m`).
- `--sin-nginx`: no toca nginx (para probar el contenedor solo).
- `--root /srv/erp-clientes`: cambia la carpeta base.
- `--licencia-secret`: si no se pasa, se lee `LICENCIA_SECRET` del entorno o se
  genera y guarda en `/srv/erp-clientes/.licencia_secret` (600). **Ese archivo
  es la llave maestra de las licencias: no se borra ni se commitea.**
- `--admin-password`: si no se pasa, se genera uno aleatorio y se imprime una
  sola vez.

Genera:

```
/srv/erp-clientes/<slug>/
├── .env                 # 600: JWT, licencia maestra, admin inicial, R2
├── docker-compose.yml   # hostname y MACHINE_ID = slug (no cambiar)
└── data/
    ├── erp_comercio.db
    └── backups/
```

## Renovar / cambiar de plan

```bash
python3 deploy/clientes/renovar_licencia.py --slug cliente1 --dias 365 --plan pro
```

Usa el `LICENCIA_SECRET` del `.env` del cliente, reemplaza la licencia vigente y
verifica que la instancia la vea válida. No hace falta reiniciar.

## Actualizar la imagen de todos

```bash
./actualizar_clientes.sh erp-comercio:<git-sha>
```

Actualiza el `IMAGEN=` de cada `.env`, guarda `.env.bak` y hace `docker compose
up -d` por cliente. Para volver atrás, correr lo mismo con la imagen anterior.

## Suspender / reactivar

```bash
./suspender_cliente.sh cliente1
cd /srv/erp-clientes/cliente1 && docker compose start
```

Suspender no borra datos. La licencia sigue en la base.

## Respaldos

Cada instancia respalda sola: local cada 15 minutos en `data/backups/` y a R2
cada hora en `backups/<slug>/`. La restauración paso a paso está en
`MULTITENANT.md` §6.

## Reglas que no se rompen

- `MACHINE_ID` y `hostname` son el slug: cambiarlos invalida la licencia.
- `LICENCIA_AUTO=false` y `LICENCIA_GESTION_LOCAL=false` en clientes: el cliente
  no puede auto-emitirse ni renovar licencias.
- El ERP del dueño y Litestream no se tocan desde acá.
