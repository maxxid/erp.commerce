# Estrategia Multi-Tenant para ERP-Commerce

> Arquitectura decided on: **Docker multi-instance** (short-term) → **PostgreSQL schema-per-client** (long-term)
> Date: 2026-07-01

---

## Resumen Ejecutivo

El objetivo es vender el ERP a **+50 clientes** sin rewrite del código existente.

**Plan de implementación:**
1. **Fase 1 (corto plazo):** Docker multi-instance para probar con 2-3 clientes
2. **Fase 2 (mediano plazo):** PostgreSQL schema-per-client cuando haya 10+ clientes pagando

**No se considera multi-tenant real** (tenant_id en todas las tablas) porque requiere rewrite significativo y no lo vale.

---

## Recursos Oracle Cloud Free Tier Disponibles

| Recurso | Límite | Uso en ERP |
|---------|--------|------------|
| VMs A1.Flex | 2 OCPUs + 12GB RAM total | VMs de producción |
| VMs E2.1.Micro | 1/8 OCPU + 1GB | No，推荐 A1 |
| Block Storage | 200 GB total | Datos de clientes |
| MySQL HeatWave | 50 GB storage **GRATIS** | Potential DB para schema-per-client |
| Oracle Autonomous DB | 20 GB storage **GRATIS** | No recomendado para esto |
| Load Balancer | 1x Flexible (10 Mbps) | Routing para múltiples clientes |
| Object Storage | 10 GB Standard + 10 GB Infrequent | Backups |

---

## Fase 1: Docker Multi-Instance (Corto Plazo)

### Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│  VM Oracle A1.Flex (2 OCPU, 12GB RAM)                      │
│                                                             │
│  Docker + Docker Compose                                    │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Nginx (reverse proxy, puerto 80)                    │    │
│  └──────┬────────┬────────┬────────┬───────────────────┘    │
│         │        │        │        │                        │
│     :5000    :5001    :5002    :5003                       │
│  ┌────────┐┌────────┐┌────────┐┌────────┐                 │
│  │ERP     ││ERP     ││ERP     ││ERP     │                 │
│  │Client1 ││Client2 ││Client3 ││Client4 │                 │
│  │        ││        ││        ││        │                 │
│  │/data/  ││/data/  ││/data/  ││/data/  │                 │
│  │cli1/   ││cli2/   ││cli3/   ││cli4/   │                 │
│  └────────┘└────────┘└────────┘└────────┘                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Configuración

- **Clientes soportados:** 4-6 por VM (basado en RAM)
- **Aislamiento:** Cada cliente tiene su propio directorio `/data/erp/clienteN/` y base de datos SQLite
- **DNS:** Un subdominio por cliente (`cliente1.erp.com`, `cliente2.erp.com`)
- **Costo:** $0 mientras no excedan los recursos free tier

### Pasos de implementación

1. Crear Dockerfile para el ERP
2. Crear docker-compose.yml con servicios por cliente
3. Configurar Nginx como reverse proxy
4. Configurar DNS wildcard o subdominios por cliente
5. Script para agregar nuevos clientes

### Comandos clave

```bash
# Agregar nuevo cliente
mkdir -p /data/erp/cliente5
docker-compose up -d erp-cliente5

# Ver estado
docker ps
docker-compose ps

# Logs
docker-compose logs -f erp-cliente1
```

---

## Fase 2: PostgreSQL Schema-per-Client (Mediano Plazo)

### Por qué PostgreSQL schema-per-client

- **Código minimal change:** Solo cambiar connection string, queries no cambian
- **Aislamiento total:** Cada cliente tiene su propio schema PostgreSQL
- **Escalabilidad:** 50-500 clientes en una sola DB
- **PostgreSQL en OCI:**

| Opción | Costo | Storage | Notas |
|--------|-------|---------|-------|
| MySQL HeatWave | **Gratis** (Always Free) | 50 GB | No es PostgreSQL pero compatible |
| PostgreSQL VM | ~$0.021/hora (ARM) | SSD local | Bare PostgreSQL |
| PostgreSQL Exadata | Desde ~$0.03/hora | 100GB+ | Exagerado para esto |

### Arquitectura PostgreSQL Schema-per-Client

```
PostgreSQL (MySQL HeatWave o VM con PostgreSQL)
│
├── Schema: cliente_1
│   ├── productos
│   ├── ventas
│   ├── clientes
│   └── ...
│
├── Schema: cliente_2
│   ├── productos
│   ├── ventas
│   ├── clientes
│   └── ...
│
└── Schema: cliente_3
    └── ...
```

### Cómo funciona

1. **JWT contiene `cliente_id`** además de `usuario_id` y `rol`
2. **Middleware de conexión** setea `search_path = cliente_{id}` antes de cada query
3. **Todas las queries** que usan `SELECT * FROM productos` automáticamente van al schema correcto
4. **SQLAlchemy** puede usar `schema` parameter en el engine

### Cambio en código

```python
# Antes (SQLite)
DATABASE_URL = "sqlite:////data/erp/erp_comercio.db"

# Después (PostgreSQL schema-per-client)
# En cada request, después de authenticate:
cursor.execute(f"SET search_path TO cliente_{cliente_id}")
```

### Migración de datos (cuando llegue el momento)

1. Exportar data de SQLite por cliente
2. Importar en su schema PostgreSQL correspondiente
3. Validar integridad
4. Cortar tráfico al nuevo PostgreSQL

---

## Integraciones Pendientes

### ARCA - Facturas Electrónicas

- **Estado:** Implementado, faltan credenciales para testear
- **Significado:** Los clientes podrán emitir facturas electrónicas合法的 (Argentina)

### SmartPoint MercadoLibre - Cobro con QR

- **Estado:** En desarrollo (~1 semana para tener disponible)
- **Significado:** Cobro vía QR desde el POS, integración con MercadoPago
- **Potencial:** Atractivo para clientes nuevos, genera revenue adicional

---

## Costos Estimados

### Escenario 1: Docker Multi-Instance (Fase 1)

| Recurso | Costo Mensual |
|---------|---------------|
| 1x VM A1.Flex (2 OCPU, 12GB) | $0 (Always Free) |
| DNS + SSL | $0-5 (Cloudflare free) |
| Backup (R2 Object Storage) | $0 (10GB free tier) |
| **Total** | **$0-5/mes** |

### Escenario 2: PostgreSQL Schema-per-Client (Fase 2)

| Recurso | Costo Mensual |
|---------|---------------|
| MySQL HeatWave (50GB) | **$0 (Always Free)** |
| O PostgreSQL VM (1 OCPU, 6GB) | ~$15/mes |
| Backup | $0 (10GB free) |
| **Total** | **$0-15/mes** para 50+ clientes |

### Cuántos clientes para cubrir costos

| DB Option | Costo/mes | Clientes necesarios para cover |
|-----------|-----------|-------------------------------|
| MySQL HeatWave | $0 | 0 - ya está cubierto |
| PostgreSQL VM | $15 | ~3-5 clientes a $5/cliente/mes |
| PostgreSQL más grande | $30 | ~6-10 clientes a $5/cliente/mes |

**Recomendación:** Empezar con MySQL HeatWave gratis, escalar a VM PostgreSQL cuando sea necesario.

---

## Decisiones Tomadas

| Decisión | Rationale |
|----------|-----------|
| No multi-tenant real (tenant_id) | Rewrite muy significativo, no vale la pena para +50 clientes |
| Schema-per-client en PostgreSQL | Mínimo cambio de código, máximo aislamiento |
| MySQL HeatWave como DB inicial | 50GB gratis, zero costo para empezar |
| Docker multi-instance como paso intermedio | Prueba con clientes reales antes de commitment a PostgreSQL |
| Mantener SQLite para clientes individuales | Si un cliente quiere su propio deploy, sigue funcionando |

---

## Próximos Pasos

### Inmediato (esta semana)
- [ ] Crear Dockerfile del ERP
- [ ] Crear docker-compose.yml
- [ ] Configurar Nginx reverse proxy
- [ ] Testear con 2 clientes en staging

### Corto Plazo (1-4 semanas)
- [ ] Implementar conexión SmartPoint ML (QR payments)
- [ ] Testear credenciales ARCA en producción
- [ ] Primer cliente real en Docker

### Mediano Plazo (1-3 meses)
- [ ] Evaluar migración a MySQL HeatWave o PostgreSQL
- [ ] Implementar schema-per-client si hay 10+ clientes
- [ ] Dashboard de monitoreo por cliente

---

## Glosario

| Término | Definición |
|---------|------------|
| Multi-tenant | Múltiples clientes comparten la misma DB y código, datos aislados por `tenant_id` |
| Schema-per-client | Cada cliente tiene su propio schema PostgreSQL (aislamiento total) |
| Docker multi-instance | Múltiples contenedores Docker, cada uno con su propia DB, en una VM |
| Always Free | Recursos que nunca expiran en Oracle Cloud Free Tier |
| HeatWave | MySQL managed database de Oracle, 50GB gratis |
| ARCA | Administración Federal de Ingresos Públicos, emite facturas electrónicas |
| MercadoLibre QR | Método de cobro vía QR integrado con MercadoPago |

---

## Contactos y Recursos

- **Oracle Cloud Free Tier:** https://oracle.com/cloud/free
- **Documentación Docker:** https://docs.docker.com
- **PostgreSQL Schema-per-Client Pattern:** https://www.postgresql.org/docs/current/ddl-schemas.html
