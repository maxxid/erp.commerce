# Estrategia multi-cliente (multitenant) — ApexERP

> **Instrucción para el Agente:** Estrategia de multi-cliente, aislamiento, licencias y runbooks de alta/baja/actualización. Leer solo si la tarea toca multi-cliente, Docker, onboarding de clientes o licencias. No leer por defecto.

> **Estado:** diseño aprobado el **26/10/2026**. La Fase 1 está **en implementación** (ver checklist al final). El ERP del dueño **no** se migra a Docker en esta fase.

---

## 1. Resumen en una frase

Un **contenedor por cliente** en la misma VM Oracle, con **su propia base SQLite**, **su subdominio** y **su licencia**. Sin `tenant_id` y sin reescribir el código.

Para el cliente es "su ERP en `clienteN.erp.imprenta.store`". Para nosotros es un servicio de Docker Compose más, con su carpeta de datos y su backup.

---

## 2. Decisiones cerradas

| Tema | Decisión | Por qué |
|---|---|---|
| Estrategia | **Docker multi-instance** (una instancia + una SQLite por cliente) | Mínimo cambio de código; aislamiento real; se puede empezar con 2-3 clientes |
| Multi-tenant real (`tenant_id` en todas las tablas) | **Descartado** | Rewrite grande y riesgo de filtrar datos entre clientes |
| Base de datos | **SQLite por cliente**, en un volumen propio | Es lo que el ERP ya usa y alcanza para 1-3 cajas |
| Hosting | **Misma VM Oracle A1** del ERP propio | Sin costo extra; el ERP del dueño sigue en systemd `:8000` |
| Acceso | **Subdominios** `clienteN.erp.imprenta.store` | Un certificado wildcard cubre a todos; DNS simple |
| Licencia | **Una por cliente**, `machine_id = slug` | Cada cliente tiene su plan y su vencimiento |
| Imagen | **Una sola** `erp-comercio:<git-sha>` para todos | Un build, muchos contenedores |
| Fase 2 (PostgreSQL) | **Solo si se dispara** (ver §10) | Hoy sería optimización prematura |

---

## 3. Arquitectura

```
                         Internet
                            │
                    Cloudflare / DNS
                            │
                        nginx :443
             ┌──────────────┼───────────────────┐
             │              │                   │
   erp.imprenta.store   cliente1.…        cliente2.…
   127.0.0.1:8000     127.0.0.1:5101     127.0.0.1:5102
        │                   │                   │
  systemd (dueño)      contenedor          contenedor
  /data/erp/           erp-cliente1        erp-cliente2
  Litestream (G2)      /srv/erp-clientes/  /srv/erp-clientes/
                       cliente1/data/      cliente2/data/
```

- El **ERP del dueño queda fuera de Docker** en la Fase 1: así no se toca el unit `erp-comercio`, ni Litestream, ni la continuidad de `FASE_G_CONTINUIDAD.md`.
- Cada cliente escucha **solo en loopback** (`127.0.0.1:51xx`). Nginx es la única puerta.
- Todos los contenedores usan la **misma imagen**; cambia el `.env`, no el código. (Si algún día un cliente necesita una versión distinta, se le cambia el tag.)

### Layout en el servidor

```
/srv/erp-clientes/
├── clientes.json              # registro: slug, dominio, puerto, plan, vence, imagen, estado
├── cliente1/
│   ├── docker-compose.yml
│   ├── .env                   # 600: secretos del cliente
│   └── data/
│       ├── erp_comercio.db
│       ├── erp_comercio.db-wal
│       └── backups/           # respaldos locales (.db.gz)
└── cliente2/
    └── ...
```

### Qué hay dentro de cada contenedor

- FastAPI + frontend compilado (`frontend/dist`, servido en `/app`).
- Su base SQLite y sus respaldos (volumen `./data:/data`).
- Sus schedulers: backup, avisos, salud, bot de Telegram y alertas.
- Su configuración de AFIP, MercadoPago, IA y Telegram, cargada en su propia base.

---

## 4. Qué NO es esto (para no confundir)

- **No es una base compartida.** Cada cliente tiene su archivo SQLite; una venta de uno no existe en la base del otro.
- **No hay continuidad Fase G para clientes.** Litestream y la segunda máquina son del ERP del dueño. Para clientes, la recuperación es el respaldo local + R2 (ventana máxima de pérdida: 1 hora).
- **No hay panel central de clientes.** El registro es `clientes.json` y los scripts de `deploy/clientes/`.
- **No hay facturación automática del abono.** La licencia tiene vencimiento y se renueva con un script; el cobro se gestiona aparte.
- **No es multi-sucursal.** Eso es otro eje (modelo `Sucursal`), todavía pendiente.

---

## 5. Licencias por cliente

Cada instancia tiene **una licencia propia**, guardada en su base, con:

| Campo | Valor |
|---|---|
| `cliente` | Nombre comercial |
| `machine_id` | **El slug del cliente** (`cliente1`), fijo |
| `plan` | `trial` / `basico` / `pro` / `enterprise` (`app/services/planes_service.py`) |
| `fecha_expiracion` | La define el alta o la renovación |
| `activa` | `true` mientras está vigente |

### Cómo se ata a la instancia

El `machine_id` normal se calcula con hostname + hardware, que **en Docker cambia** al recrear el contenedor. Por eso la instancia acepta un override:

```env
MACHINE_ID=cliente1
```

En el compose también se fija `hostname: cliente1`, para que cualquier herramienta que lea el hostname vea lo mismo.

### Secretos

| Variable | Alcance | Para qué |
|---|---|---|
| `JWT_SECRET` | **Único por cliente** | Firmar los tokens de sesión |
| `LICENCIA_SECRET` | **Maestro, igual en todas las instancias** | Firmar/validar claves de licencia aunque cada cliente tenga otro `JWT_SECRET` |
| `ADMIN_PASSWORD_INICIAL` | **Único por cliente** | Password del usuario `admin` en el primer arranque |

Si `LICENCIA_SECRET` no está definido, se usa `JWT_SECRET` (comportamiento viejo, válido para desarrollo).

### Reglas de negocio

- **`LICENCIA_AUTO=false` en clientes.** Sin esto, el arranque crea una licencia demo `pro` de 30 días cada vez que vence (`app/main.py`), o sea el cliente nunca pagaría.
- **`LICENCIA_GESTION_LOCAL=false` en clientes.** El admin del cliente **no** puede emitir ni renovar claves desde la UI (`/api/licencia/generar` responde 403). La gestión es del dueño del sistema.
- **La licencia se siembra antes del primer arranque** con `scripts/seed_licencia_cliente.py`, porque el login exige licencia válida (`app/routers/auth.py`).
- **Renovación:** `deploy/clientes/renovar_licencia.py` actualiza/inserta la licencia y reinicia el contenedor.
- **Suspensión:** `activa=false` o `docker compose stop`. Detener el contenedor no borra nada.

---

## 6. Respaldos y recuperación

Cada instancia corre su propio `backup_service`:

- **Local cada 15 minutos** en `/data/backups` (volumen del cliente, rotación de 5 archivos).
- **A R2 cada hora** en `backups/<slug>/` del mismo bucket, con las credenciales del `.env`.
- **Verificación de salud** cada 30 minutos por instancia (`salud_service`); el aviso por Telegram es opcional y se configura en la instancia del cliente.

### Restaurar un cliente

```bash
cd /srv/erp-clientes/cliente1
docker compose stop
cp data/erp_comercio.db data/erp_comercio.db.bak-$(date +%Y%m%d%H%M)
gunzip -c data/backups/erp_comercio_YYYYMMDD_HHMMSS.db.gz > data/erp_comercio.db
chown 10001:10001 data/erp_comercio.db
docker compose start
curl -fsS http://127.0.0.1:5101/health
```

> La ventana máxima de pérdida es **1 hora** (la subida a R2). No hay réplica en vivo para clientes.

---

## 7. Alta de un cliente (runbook)

**Requisitos previos:** Docker instalado, imagen `erp-comercio:<sha>` construida, nginx y `certbot` funcionando, y el registro DNS apuntando a la VM.

```bash
python3 deploy/clientes/alta_cliente.py \
  --slug cliente1 \
  --nombre "Almacén Don José" \
  --dominio cliente1.erp.imprenta.store \
  --plan trial \
  --dias 30
```

El script hace todo:

1. Valida el slug (`^[a-z0-9-]{3,30}$`), que no exista y que haya puerto libre.
2. Asigna el siguiente puerto desde `5101` y lo anota en `clientes.json`.
3. Crea `/srv/erp-clientes/<slug>/{data,data/backups}` con dueño `10001:10001`.
4. Genera `.env` (600) con `JWT_SECRET`, `ADMIN_PASSWORD_INICIAL` y el `LICENCIA_SECRET` maestro.
5. Genera el `docker-compose.yml` desde la plantilla (hostname y `MACHINE_ID` fijos).
6. Siembra la licencia con un contenedor efímero (`scripts/seed_licencia_cliente.py`).
7. Levanta el contenedor y espera el healthcheck.
8. Escribe el vhost de nginx, valida y recarga; pide el certificado con `certbot` (o avisa que falta el wildcard).
9. Smoke test: `/health`, `/api/licencia/estado` con `valida=true` y login con el admin inicial.
10. Imprime **una sola vez** la URL, el usuario y la password inicial.

**Después del alta:** entrar y cambiar la password de `admin`; cargar los datos del negocio; configurar AFIP/MercadoPago/Telegram/IA si corresponde (son independientes por cliente).

---

## 8. Operación

### Actualizar la imagen

```bash
cd /opt/erp-comercio
git pull origin master
docker build -t erp-comercio:<git-sha> .
deploy/clientes/actualizar_clientes.sh <git-sha>
```

El script actualiza el tag en cada `.env`, hace `docker compose up -d` por cliente y guarda el tag anterior para rollback. Si algo falla:

```bash
deploy/clientes/actualizar_clientes.sh <tag-anterior>
```

### Comandos por cliente

```bash
cd /srv/erp-clientes/cliente1
docker compose ps
docker compose logs -f --tail=100
docker compose restart
docker compose stop
docker compose up -d
```

### Límites y capacidad

| Recurso | Valor inicial | Nota |
|---|---|---|
| RAM por cliente | `512m` | Medir con `docker stats`; ajustar según uso real |
| CPU por cliente | `0.5` | Suficiente para 1-3 cajas |
| Clientes por VM | 4-6 con holgura | Empezar con 2-3 y medir |

### Monitoreo

- Healthcheck de Docker contra `/health` (público, sin auth).
- `docker stats`, `df -h` y logs de nginx.
- Opcional por cliente: UptimeRobot o su propio bot de Telegram.
- **No hay monitoreo central todavía**: si un cliente se cae, avisa su propia instancia (si tiene Telegram configurado) o lo detecta el dueño al mirar.

### Seguridad

- Contenedor con usuario **no-root** (`uid 10001`).
- `.env` con permisos `600`; secretos **fuera** del repo y de la imagen.
- Base, respaldos y logs **fuera** de la imagen (`.dockerignore`).
- `JWT_SECRET` único por cliente: un token de uno no sirve en otro.
- La gestión de licencias queda deshabilitada en la instancia del cliente.

---

## 9. Costos y capacidad

| Recurso | Costo | Nota |
|---|---|---|
| VM Oracle A1 (misma del dueño) | $0 | Verificar el shape real y la capacidad libre en OCI |
| Almacenamiento | Incluido en el disco de la VM | Cada base arranca en pocos MB |
| R2 | $0 hasta 10 GB | Los respaldos de todos comparten bucket, separados por slug |
| Cloudflare / TLS | $0 | Wildcard cuando G1 mueva el DNS |
| **Total extra** | **$0** | Mientras entren en la misma VM |

> El número de OCPU/RAM de la VM se verifica en la consola de OCI antes de comprometer capacidad. `HOSTING.md` y este documento deben decir lo mismo.

---

## 10. Fase 2 — PostgreSQL (solo si se dispara)

**No se implementa hoy.** Se evalúa cuando pase alguna de estas condiciones:

- Más de ~10 clientes, o backups/actualizaciones manuales inmanejables.
- Necesidad de reportes cross-cliente o de un panel central.
- Un cliente con más concurrencia de la que SQLite soporta cómodamente.

Si llega el momento:

1. **Preferir base por cliente** en PostgreSQL (`cliente1_db`, `cliente2_db`) antes que *schema*-per-client: el aislamiento es más simple y los respaldos son por base.
2. Si se usa *schema*-per-client, **no** hacer `SET search_path` sobre un pool compartido: usar `schema_translate_map` de SQLAlchemy o un engine por tenant, y resetear el `search_path` al devolver la conexión.
3. **MySQL HeatWave es MySQL, no PostgreSQL**: no asumir compatibilidad de SQL ni de driver.
4. **Alembic es prerrequisito.** Hoy las migraciones son `ALTER TABLE` a mano al arrancar (`app/main.py`); con una base compartida eso deja de ser seguro.
5. Migración: exportar cada SQLite, importar a su base PostgreSQL, validar conteos y `integrity_check`, cortar tráfico y volver atrás si falla.

---

## 11. Integraciones por cliente

Cada instancia configura lo suyo; no se comparte nada entre clientes.

| Integración | Estado | Nota por cliente |
|---|---|---|
| **ARCA / AFIP** (factura electrónica) | Implementado; faltan credenciales de producción y revisar el manejo de la clave privada | Certificado, CUIT y punto de venta propios |
| **MercadoPago** (QR / Smart Point) | Implementado | Access token, store y caja propios; webhook por subdominio |
| **SmartPoint** | Implementado como medio de pago | No requiere API propia |
| **IA / LLM** | Implementado con plan y límite mensual | API key y límite por cliente (`planes_service`) |
| **Telegram** | Implementado (avisos + bot interactivo) | **Un bot por cliente** si se quiere; el polling de una instancia no debe compartir token con otra |
| **Precios online (scraping)** | Implementado | Sale a internet desde cada contenedor; respetar timeouts y caché |
| **Respaldos R2** | Implementado | Mismo bucket, prefijo por slug |

> El bot de Telegram hace polling cada 3 segundos **por instancia**. Si un cliente no configura token y chat ID, no hace requests, pero el scheduler existe.

---

## 12. Riesgos conocidos

- **Un solo servidor para todos.** Si la VM se cae, se caen el ERP del dueño y todos los clientes. La red de seguridad son los respaldos (local + R2), no una segunda máquina.
- **Secretos maestros en el servidor.** `LICENCIA_SECRET` y las credenciales de R2 permiten emitir licencias y leer respaldos de todos: tratarlos como llaves maestras.
- **Configuración duplicada.** Cada cliente repite AFIP, MP, Telegram e IA; conviene un checklist de alta y otro de baja.
- **Sin panel central.** El estado se mira en `clientes.json`, `docker ps` y los logs.
- **Fase G no aplica.** No prometer continuidad automática a los clientes hasta que exista un plan específico.
- **Deriva de versiones.** Todos deberían quedar en el mismo tag; si un cliente se atrasa, anotarlo en `clientes.json`.

---

## 13. Estado de implementación (Fase 1)

- [x] Diseño y documento (`MULTITENANT.md`) — 26/10/2026
- [x] Parametrización por entorno: `MACHINE_ID`, `BACKUP_DIR`, `LICENCIA_SECRET`, `LICENCIA_AUTO`, `LICENCIA_GESTION_LOCAL`, `ADMIN_PASSWORD_INICIAL` — 26/10/2026
- [x] `/health` público — 26/10/2026
- [ ] `.dockerignore` + `Dockerfile` endurecido (`curl`, `openssl`, usuario no-root)
- [ ] `scripts/seed_licencia_cliente.py`
- [ ] `deploy/clientes/` (plantillas + alta + renovación + actualización)
- [ ] Ensayo con `cliente-demo`: aislamiento, backup y restauración
- [ ] Primer cliente real

---

## 14. Glosario

| Término | Definición |
|---|---|
| **Multi-instance** | Varios procesos de la app, cada uno con su propia base. Es lo que usa este proyecto |
| **Multi-tenant** | Una sola app y una sola base, con los datos separados por `tenant_id`. **No** es lo que usa este proyecto |
| **Schema-per-client** | Cada cliente tiene su *schema* dentro de un mismo PostgreSQL |
| **`machine_id`** | Identificador que ata una licencia a una instalación. En clientes es el slug |
| **Always Free** | Recursos de Oracle Cloud que no expiran |
| **ARCA** | Administración Federal de Ingresos Públicos (ex AFIP); emite facturas electrónicas |
| **R2** | Cloudflare Object Storage, compatible con S3; guarda los respaldos |
