# ERP Comercio — Deploy en Oracle Cloud Free Tier

## Resumen
Oracle Cloud ofrece una VM ARM **gratis de por vida** con:
- 4 cores, 24 GB RAM, 200 GB disco
- IP pública estática
- Sin límite de tráfico

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
