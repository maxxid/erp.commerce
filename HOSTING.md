# ERP Comercio — Deploy en Oracle Cloud Free Tier

> **Instrucción para el Agente:** Setup inicial de la VM Oracle Cloud. Leer solo si se aprovisiona o migra de hosting. No leer por defecto.

## Resumen
La instancia **actual** (`erp-comercio`, región Santiago) es una **`VM.Standard.E2.1.Micro`**: x86_64, 2 vCPU, **1 GB de RAM**, 45 GB de disco y **sin swap** (se le agregaron 2 GB el 26/10/2026). Alcanza para el ERP solo; **no para clientes multi-instance** (ver `MULTITENANT.md` §9).

> El plan de abajo describe cómo crear una **VM nueva**. Oracle Cloud ofrece una A1.Flex ARM gratis de 4 OCPU/24 GB **en total por cuenta**, pero esta cuenta hoy tiene una E2.1.Micro. Antes de sumar clientes, verificar en la consola de OCI qué shape es la instancia real y cuánta capacidad A1 queda libre.

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
ls -lh /data/erp/                # DB está en /data/erp/
```

## Actualizar desde GitHub
```bash
cd /opt/erp-comercio
git pull
systemctl restart erp-comercio
```

---

## Docker para clientes (multi-cliente)

> **Ojo:** la VM actual es de **1 GB** y comparte RAM con el POS. El 26/10/2026 se
> hizo un ensayo con **un** `cliente-demo` de 256 MB y se detuvo; Docker quedó
> instalado pero **deshabilitado**. Para clientes reales hace falta una VM aparte
> (A1.Flex free o paga, ver `MULTITENANT.md` §9).

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
