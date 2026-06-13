# Ideas Pendientes — ApexERP

## Dashboard multi-negocio (admin central)
**Estado:** Idea — para más adelante

Un dueño con varios negocios (cada uno con su machine_id) necesita ver todo centralizado.

### Opción A: App separada para el dueño
- Nueva app que lee los backups de R2 de todos los machine_id
- Muestra dashboard global + drill-down por negocio
- No interfiere con el ERP de cada negocio
- Stack: mismo Python/FastAPI + SQLite (lee los .db descargados)

### Opción B: El admin del ERP actual puede "importar" backups de otros
- Endpoint `GET /api/admin/backups/todos` — lista todos los backups de todos los clientes en R2
- Botón "Ver negocio X" que descarga, restaura temporalmente, y muestra dashboard
- Más simple pero menos elegante

### Datos que interesan al dueño (por negocio y global)
- Ventas hoy / semana / mes
- Margen bruto
- Ticket promedio
- Productos más vendidos
- Alertas (stock bajo, caja sin cerrar)
- Comparativas entre negocios (ranking)
- Auditoría (ventas anuladas, carritos abandonados)

---

## Otras ideas pendientes

### Impresión de tickets
- PDF o impresora térmica
- Formato de ticket fiscal simplificado

### Reportes exportables (CSV/PDF)
- Ventas por período
- Stock actual
- Movimientos de caja

### Notificaciones
- Stock bajo
- Licencia por vencer
- Caja sin cerrar al final del día

### Multi-sucursal
- Modelos ya existen (Sucursal)
- Misma DB, diferente sucursal_id
- Cada caja ve solo su sucursal

### Migración PostgreSQL + Alembic
- Para cuando haya >5 usuarios concurrentes
- O cuando se necesite acceso remoto multi-sucursal

### Instalador Windows (.exe)
- NSIS o Inno Setup
- Empaqueta Python + dependencias + la app
- Un solo .exe, siguiente-siguiente-instalar
