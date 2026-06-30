# Deploy & Mantenimiento

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
