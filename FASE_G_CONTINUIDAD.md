# Fase G — Continuidad automática (principal → secundaria → retorno)

> **Instrucción para el Agente:** Plan de continuidad (failover). Leer solo si se trabaja en Fase G o en réplica/backup. No leer por defecto.

> **Para qué está este archivo**: para arrancar la Fase G en un chat nuevo sin perder el contexto.
> Todo lo que sigue ya está **diseñado y acordado con el dueño** (24/10/2026), pero **todavía no se implementó nada**.
> El estado real del proyecto (qué está hecho, qué no) está en `PENDIENTES.md`; el flujo de deploy está en `DEPLOY.md`.
>
> **Resumen en una frase**: si el servidor de Oracle Cloud se cae, en unos minutos otra máquina toma el
> trabajo sola y le avisa al dueño por Telegram; a las 06:00 AR, cuando no hay ventas, todo vuelve a la
> máquina principal solo. El dueño no tiene que estar mirando: **automático + un aviso de Telegram**.

---

## 1. Por qué (el problema, en criollo)

- El negocio tiene **un día sin internet** y otros días con **hotspot limitado**. Eso ya está resuelto del
  lado del celular (fases D y E: cola offline que sube sola al volver la red).
- Lo que **no** está resuelto es que **la base vive en una sola máquina de Oracle Cloud free tier**. Si Oracle
  apaga la instancia, o se cae la región, o se vence la cuenta, **el negocio no cobra** hasta que alguien lo
  arregle.
- El dueño quiere que sea **comercial**: que el sistema siga andando solo y que a él **sólo le llegue un
  aviso** por Telegram. No quiere estar "pendiente" del servidor.

Lo que ya está hecho (anteriores, ver `PENDIENTES.md` → Completados):

- **Respaldos automáticos**: locales cada 15 min (snapshot de SQLite, rotación 5) + subida a R2 cada hora (144 objetos al 24/10/2026).
- **Salud y alertas por Telegram**: cada 30 min verifica que haya respaldo de <24 h, que el `.gz` abra
  (`PRAGMA integrity_check`) y que R2 tenga los frescos; avisa con guarda de 12 h por tipo + resumen diario 21:00.
- **Cola offline (Fase E)**: si la red se corta, caja y ventas se guardan localmente y suben en orden al volver.
  **Es el salvavidas**: si un traspaso de servidor falla, las ventas del día no se pierden, suben después.

Lo que falta es justo lo que describe este documento.

---

## 2. Decisiones ya tomadas (no volver a discutir)

| Tema | Decisión |
|---|---|
| Dos cuentas de Oracle | **Descartado**: riesgo de ToS y cierre en cascada de las dos. |
| Segunda máquina gratis | **Segunda VM e2.micro "always free" en la misma región (Santiago) y la misma cuenta** de Oracle. Las 2 micros gratis sólo existen en la *home region*, por eso se queda todo en Santiago. |
| Región | **Quedarse en Santiago**: 70 ms no molesta, todo el stack ya está armado ahí. |
| DNS | Mover el DNS a **Cloudflare free** (TTL de 5 min). Hoy el TTL de Hostinger es **4 h**, lo que anula cualquier cambio de servidor: con 4 h de TTL, un salto automático tarda 4 h en propagarse. |
| Detección | **Vigilante en la secundaria**: si la principal no responde 3 minutos → salto automático. |
| Retorno | **Programado a las 06:00 AR** (ventana sin ventas): la secundaria saca una "foto" de su base, la principal la restaura por encima de la suya, verifica, vuelve el DNS y avisa. |
| Invariante | **Una sola base a la vez.** Nunca hay dos servidores cobrando en paralelo. |
| Mecanismo de replicación | **Litestream** (réplica continua del SQLite hacia R2). La secundaria restaura desde esa réplica. |
| Rol del servidor | Variable de entorno **`ROL_SERVIDOR=principal|secundaria`**. **Si no es principal, no cobra** (el POS queda en "mantenimiento programado"). |
| Sin internet ese día | La cola offline de la Fase E sigue siendo el respaldo; no se factura (decisión del dueño 16/10/2026). |

---

## 3. Cómo funciona (arquitectura)

```
   [PC del dueño / cajeros]
            │  HTTPS
            ▼
   Cloudflare free  ── TTL 5 min ──►  DNS de erp.imprenta.store
            │
            ▼
   PRINCIPAL (Oracle, Santiago)              SECUNDARIA (Oracle, Santiago, 2da micro gratis)
   ─ servicio erp-comercio                   ─ servicio erp-comercio (ROL_SERVIDOR=secundaria)
   ─ base real: /data/erp/erp_comercio.db    ─ base restaurada desde la réplica
   ─ escribe normalmente                     ─ no cobra (banner "mantenimiento")
   ─ Litestream replica cada pocos seg ───►  (R2: réplica continua)
                                                │
                                                ─ vigilante: ping a la principal
                                                  3 min sin respuesta → SALTO:
                                                  1) la secundaria restaura la réplica
                                                  2) Cloudflare API: DNS → secundaria (segundos)
                                                  3) Telegram: "pasé a secundaria"
                                                  4) ROL_SERVIDOR=principal en la secundaria
             ◀──── 06:00 AR: RETORNO ────  (al revés, con verificación antes de devolver)
```

**Puntos clave:**

1. **Réplica continua (Litestream)**: mantiene el SQLite de la principal copiado en R2 con un desfase de
   segundos. La secundaria no lee en vivo de la principal (si la principal está muerta no puede leer de ella),
   lee **la última réplica guardada**.
2. **Vigilante (watchdog)**: proceso corriendo **en la secundaria** que le pregunta a la principal cada 30 s.
   180 s seguidos sin respuesta ⇒ **salto automático**. No depende de que el dueño esté mirando.
3. **Cambio de DNS por API (Cloudflare)**: es lo que hace que el salto dure **segundos** y no 4 horas.
4. **Banner "mantenimiento programado"** en el POS: mientras un servidor no es principal, la pantalla de venta
   muestra eso en vez de cobrar. Evita que alguien cobre en la máquina equivocada.
5. **Retorno a las 06:00 AR**: sólo en horario sin ventas. Primero se **verifica** que la principal vuelva
   antes de devolverle el DNS; si algo falla, **se queda en la secundaria** y avisa.

---

## 4. Plan de trabajo (G1 … G7)

Cada paso = un commit + deploy con la suite en verde (regla del proyecto). Orden recomendado.

### G1 — Cloudflare free: DNS con TTL corto + página de mantenimiento
- Crear cuenta Cloudflare (free) y pasar el DNS de `erp.imprenta.store` (A record → la IP de la principal).
- TTL de 5 min en el registro que importa.
- **Worker de mantenimiento** (free tier, 100.000 req/día: sobra) que responde el banner cuando
  `ROL_SERVIDOR=secundaria` o durante la ventana de retorno.
- *Validación*: el sitio sigue andando igual; `dig` muestra TTL 300.
- *Nota*: antes de tocar el DNS, dejar **UptimeRobot** (free) mirando `https://erp.imprenta.store/app/` como
  segunda red de alerta, por si el vigilante automático no llega a existir todavía.

### G2 — Litestream: réplica continua principal → R2 ✅ **HECHO (25/10/2026)**
- **Hecho**: `litestream 0.5.17` instalado en `/usr/local/bin/litestream` (binario verificado contra `checksums.txt` de GitHub), **`/etc/litestream.yml`** generado leyendo las credenciales R2 de la base (queda `root:erp` 640, sin secretos en el repo) y **`litestream.service`** (systemd, corre como `erp`, `Restart=always`) replicando `/data/erp/erp_comercio.db` → `s3://<bucket>/replica/<machine_id>/`.
- **Base en WAL**: era `delete`; se pasó a `wal` y `app/database.py` lo fija en cada conexión (si no, una base nueva no podría replicarse). Verificado: `PRAGMA journal_mode` → `wal`, `/docs` 200 después del cambio.
- **Snapshots cada 15 min con retención de 24 h**: Litestream sube un archivo aunque nadie venda, así que el chequeo de salud no miente de noche. Ocupa ~200 MB en el bucket (R2 free: 10 GB).
- **Chequeo de salud**: `salud_service.problemas_de_replica()` mira que haya archivos en `replica/<machine_id>/` y que el último no tenga más de 45 min (`MAX_MIN_SIN_REPLICA`); entra en el mismo aviso de Telegram de los respaldos y se muestra en el resumen diario ("Réplica en vivo: al día, hace X min"). Se prende por servidor con **`LITESTREAM_HABILITADO=true`** en el unit file de `erp-comercio`, así una máquina sin litestream no manda alertas falsas.
- Verificación en prod: `litestream status` → `ok`, objetos en R2 con segundos de antigüedad. Tests: `tests/test_replica_salud.py` (10).
- Quedan G1, G3, G4, G5, G6, G7.

### G3 — La secundaria: rol, restauración y banner
- Provisionar la **2da micro e2.micro always free en Santiago** (misma cuenta), con el mismo repo y servicio.
- Variable **`ROL_SERVIDOR=secundaria`** en su unit file (y `principal` en la real).
- Script de **restauración desde la réplica de Litestream** (`litestream restore -o /data/erp/erp_comercio.db`).
- **Banner "mantenimiento programado"** en el POS cuando `ROL_SERVIDOR != principal`: middleware en backend
  (los POST de cobro devuelven 503 con ese mensaje) + aviso visible en `POSView`/`CobroMóvil`.
- La secundaria queda **apagada de servicio o en modo sólo lectura** hasta que se la necesite (no gastar RAM).
- *Validación*: con la secundaria en `secundaria`, el POS no cobra y muestra el banner; con `principal`, cobra.

### G4 — Vigilante + salto automático (el corazón)
- Proceso (script Python o systemd timer cada 30 s) **corriendo en la secundaria**:
  1. `GET http://<principal>/health` (o `:8000/docs`) con timeout de 5 s.
  2. Si **3 minutos seguidos** no responde → dispara el salto.
  3. Salto: restaurar réplica → `ROL_SERVIDOR=principal` → levantar servicio → **Cloudflare API** (cambiar el
     A record a la IP de la secundaria) → **Telegram**: "⚠️ La principal no responde. Estoy sirviendo desde la
     secundaria desde las HH:MM."
  4. Guarda de alarma (no repetir el mismo salto cada 30 s) y **registro en la auditoría**.
- El usuario de Cloudflare sólo puede editar **ese** registro (token con permiso mínimo).
- *Validación (ensayo de laboratorio)*: apagar el servicio en la principal y cronometrar el salto; debe ser
  ~3 min + segundos. Ver el aviso en el celular.

### G5 — Retorno programado a las 06:00 AR
- En la secundaria, un timer diario a las 06:00 AR (poner la zona horaria en el servidor; **AR = UTC-3**):
  1. Aviso Telegram: "↩️ Retorno a la principal en 2 min".
  2. La secundaria **saca la foto de su base** (backup consistente con el API de SQLite, igual que
     `crear_backup_local`) y la deja lista para descargar.
  3. La **principal la restaura por encima de la suya** (importante: lo que se vendió durante la falla vive en
     la secundaria y **no se puede perder**).
  4. **Verificación**: `PRAGMA integrity_check` + conteo de ventas del día en ambos lados.
  5. Si todo OK → Cloudflare API vuelve el DNS a la principal → aviso Telegram "↩️ Todo volvió a la principal".
     Si algo **no** OK → **no devuelve el DNS**, se queda en la secundaria y manda alerta.
  6. La secundaria vuelve a `ROL_SERVIDOR=secundaria`.
- *Ojo*: durante el retorno el POS queda "mantenimiento" unos minutos (por eso es a las 06:00).

### G6 — Ensayo real con la principal apagada
- Avisar al dueño con anticipación, elegir un horario sin ventas, y **apagar la principal de verdad**:
  - que el salto ocurra solo,
  - que se pueda cobrar desde la secundaria,
  - que al volver el día siguiente el retorno pase solo,
  - y que **ninguna venta se pierda ni se duplique**.
- Este es el paso que le importa al dueño: **es la prueba del todo**.

### G7 — Pulir y documentar
- Agregar los tiempos y el costo real a `PENDIENTES.md`.
- Considerar **UptimeRobot** como segunda red de alerta (gratis) por si el vigilante automático falla.
- Borrar lo que quedó a medias.

---

## 5. Criterios de aceptación de la fase

1. **Cae la principal → en ≤4 minutos** la app responde desde la secundaria y el dueño recibe un aviso de Telegram.
2. Durante la falla se puede **cobrar** (la secundaria asume el rol) y la cola offline de Fase E sigue funcionando si hay red sospechosa.
3. A las **06:00 AR** el retorno pasa **solo**, con verificación previa, y **ninguna venta se pierde ni se duplica**.
4. Si la verificación falla, **no** devuelve el DNS y manda alerta.
5. **Jamás** hay dos servidores cobrando a la vez (invariante de una sola base).
6. La suite sigue en verde y hay tests para: detección (3 min), salto (DNS + rol + aviso), retorno (éxito y falla) y banner.
7. Todo el estado se puede reconstruir leyendo este archivo + `PENDIENTES.md` + `git log`.

---

## 6. Datos del entorno (no adivinar)

| Dato | Valor |
|---|---|
| Repositorio | `https://github.com/maxxid/erp.commerce` (rama `master`) |
| Servidor principal | `ubuntu@136.248.245.145`, región **Santiago** (home region) de Oracle Cloud |
| SSH | `ssh -i "C:\Users\maxib\Documents\Oracle-Cloud-Ubuntu\ssh-key-2026-06-20.key" ubuntu@136.248.245.145 '<comando>'` |
| Repo en el servidor | `/opt/erp-comercio` (**el pull hay que hacerlo con `cd /opt/erp-comercio && sudo -u erp git pull origin master`**; sin el `cd` falla con "not a git repository") |
| Base de datos | `/data/erp/erp_comercio.db` (`DATABASE_URL=sqlite:////data/erp/erp_comercio.db` está en el unit file) |
| Servicio | `systemctl restart erp-comercio` → uvicorn en `127.0.0.1:8000` |
| Sitio | `https://erp.imprenta.store/app/` (reverse proxy; `/docs` responde 200 = backend OK) |
| DNS | Hoy en **Hostinger con TTL 4 h** → mover a **Cloudflare free** (G1) |
| Backups | locales c/15 min (rotación 5) + **R2** c/1 h, bucket con prefijo `backups/<machine_id>/` (144 objetos al 24/10/2026, sin rotación → baja prioridad) |
| Réplica (a crear) | Litestream → el mismo bucket de R2 |
| Telegram | **Funcionando**: el dueño configuró su bot y su `/start` responde; avisos de salud y resumen diario activos |
| Zona horaria | Servidor en UTC probablemente; **hora de negocio = UTC-3 (AR)** → la ventana de retorno 06:00 AR = 09:00 UTC |
| Suite | `python -m pytest -p no:cacheprovider` → **980 passed** (red bloqueada por `tests/conftest.py`) |
| Health | `GET /health` (público, sin auth) — implementado en la Fase 1 multi-cliente (`MULTITENANT.md`) |
| Build | `npm run build` en `frontend/` **antes** de commitear (el `sw.js` queda un commit atrás por diseño del stamp) |
| Deploy | `DEPLOY.md` (pull + `pip install -r requirements.txt` + restart) |
| ssh desde PowerShell | Las comillas dobles **se borran**: no usarlas. Para SQL o Python remoto: **base64** (`$b64=[Convert]::ToBase64String(...)`, `echo $b64 | base64 -d > /tmp/q.sql`, y ejecutar leyendo de archivo: `sqlite3 db < /tmp/q.sql`) |
| git | `git add -A ; git reset -- "=" ; git commit -F <archivo> ; git push` (el push avisa `NativeCommandError` pero funciona) |

---

## 7. Preguntas abiertas (consultarle al dueño antes de arrancar)

1. **¿Autoriza arrancar la Fase G?** El paso 1 (mover el DNS a Cloudflare) cambia cómo resuelve el dominio:
   se hace de día y con el sitio andando; si algo sale mal se vuelve atrás cambiando el nameserver.
2. **¿La ventana de retorno a las 06:00 AR le sirve?** (¿abre antes? ¿hay deliveries temprano?)
3. **¿Creó la cuenta UptimeRobot?** sirve como segunda red de alerta, gratis.
4. **¿Las dos micros gratis de Oracle en Santiago están disponibles en su cuenta?** (si una ya está usada, la
   secundaria tendría que ser e2-micro *paid* ≈ USD 7,5/mes — aviso de costo real).
5. ¿Conviene ensayar el salto (G6) en un horario con el negocio cerrado de una vez, o primero en un día hábil?

---

## 8. Cómo continuar (checklist para el chat nuevo)

1. Leer `PENDIENTES.md` (estado real) y `DEPLOY.md` (cómo se despliega) y este archivo.
2. Confirmar con el dueño las preguntas de la sección 7.
3. Empezar por **G1 (Cloudflare)**, porque sin TTL corto no sirve ningún salto automático.
4. Seguir G2 → G7, **un commit + deploy por paso**, suite en verde, sin `console.log` ni código muerto,
   y actualizar `PENDIENTES.md` al cerrar cada paso.
5. Si aparece un bug del día a día (como la Fase H del `7790895000997`), se atiende primero y vuelve este plan.
