# ERP Comercio — Deploy en Oracle Cloud Free Tier

> **Instrucción para el Agente:** Setup inicial de la VM Oracle Cloud. Leer solo si se aprovisiona o migra de hosting. No leer por defecto.

## Resumen
Oracle Cloud ofrece una VM ARM **gratis de por vida** con:
- 4 cores, 24 GB RAM, 200 GB disco
- IP pública estática
- Sin límite de tráfico

> El total **Always Free** de A1.Flex es 4 OCPU + 24 GB **en toda la cuenta**, repartido entre las instancias A1 que tengas. Antes de sumar clientes, verificá en la consola de OCI el shape real de `erp-comercio` y cuánto queda libre. Los clientes multi-instancia viven en **esta misma VM** (ver `MULTITENANT.md`).

## Paso a paso

### 1. Crear la VM en Oracle Cloud
1. Entrá a [cloud.oracle.com](https://cloud.oracle.com) → registrate (pide tarjeta, no cobran)
2. **Compute → Instances → Create Instance**
3. Nombre: `erp-comercio`
4. Image: **Ubuntu 22.04**
5. Shape: **VM.Standard.A1.Flex** (ARM, Always Free)
   - OCPU: 4, RAM: 24 GB
6. Descargá la **SSH key** (o subí tu pública)
7. **Create**

### 2. Conectarse por SSH
```bash
chmod 600 ~/Descargas/ssh-key-xxx.key
ssh -i ~/Descargas/ssh-key-xxx.key ubuntu@<IP-PUBLICA>
```

### 3. Abrir puertos en Oracle
1. Oracle Console → **Instances** → Click en tu VM
2. **Primary VNIC → Subnet → Default Security List**
3. **Add Ingress Rules:**
   - Source: `0.0.0.0/0`, TCP, Port: `80`
   - Source: `0.0.0.0/0`, TCP, Port: `443`

### 4. Ejecutar el instalador
```bash
# Ya dentro del servidor (SSH)
git clone https://github.com/TU-USUARIO/erp-comercio.git
cd erp-comercio
chmod +x setup-oracle.sh
sudo ./setup-oracle.sh erp.tudominio.com
```

El script instala todo: Python 3.11, dependencias, systemd, nginx.

### 5. SSL con Certbot
```bash
sudo certbot --nginx -d erp.tudominio.com
```

### 6. Configurar dominio
En tu proveedor de DNS agregá un registro:
```
Tipo: A
Nombre: erp
Valor: <IP-PUBLICA-DE-ORACLE>
```

### 7. Listo
```bash
# Verificar que anda
systemctl status erp-comercio
journalctl -u erp-comercio -f  # logs en vivo
```

ERP en: `https://erp.tudominio.com/app`
API Docs: `https://erp.tudominio.com/docs`

## Comandos útiles
```bash
systemctl restart erp-comercio   # Reiniciar
systemctl stop erp-comercio      # Detener
journalctl -u erp-comercio -f    # Ver logs
tail -f /data/erp/erp_comercio.db  # DB está en /data/erp/
```

## Actualizar desde GitHub
```bash
cd /opt/erp-comercio
git pull
systemctl restart erp-comercio
```

---

## Docker para clientes (multi-cliente)

El ERP del dueño sigue en systemd (`:8000`). Docker se usa **solo** para los
clientes, que escuchan en `127.0.0.1:5101+` detrás de nginx. No reemplaza al
servicio `erp-comercio` ni a Litestream.

```bash
# Instalar Docker (Ubuntu 22.04)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # cerrar y volver a entrar

# Verificar
docker --version
docker run --rm hello-world

# Construir la imagen del ERP
cd /opt/erp-comercio
docker build -t erp-comercio:$(git rev-parse --short HEAD) .
```

- Datos de clientes: `/srv/erp-clientes/<slug>/` (fuera del repo).
- Alta, actualización y restauración: `MULTITENANT.md` §6-§8 y `DEPLOY.md`.
- nginx y certbot ya están instalados por `setup-oracle.sh`; cada cliente suma
  un vhost más.
