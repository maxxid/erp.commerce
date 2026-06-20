#!/bin/bash
# ============================================================
# SETUP — ERP Comercio en Oracle Cloud Free Tier (Ubuntu 22.04)
# Ejecutar como root o con sudo:
#   chmod +x setup-oracle.sh && sudo ./setup-oracle.sh
# ============================================================
set -e

APP_DIR="/opt/erp-comercio"
APP_USER="erp"
DATA_DIR="/data/erp"
DOMAIN="${1:-erp.tudominio.com}"  # Pasar como argumento o editar

echo "========================================"
echo "  ERP Comercio — Instalador Oracle Cloud"
echo "========================================"

# 1. Actualizar sistema
echo "[1/7] Actualizando sistema..."
apt update && apt upgrade -y

# 2. Instalar Python 3.11 (Ubuntu 22.04 trae 3.10 por defecto)
echo "[2/7] Instalando Python 3.11..."
apt install -y software-properties-common
add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y python3.11 python3.11-venv python3.11-dev \
    python3-pip git nginx certbot python3-certbot-nginx \
    build-essential libssl-dev

# 3. Crear usuario y directorios
echo "[3/7] Creando estructura..."
id -u $APP_USER &>/dev/null || useradd -m -s /bin/bash $APP_USER
mkdir -p $DATA_DIR
mkdir -p $APP_DIR

# 4. Configurar repositorio
echo "[4/7] Configurando repositorio..."
if [ -d "$APP_DIR/.git" ]; then
    echo "  Repositorio ya existe en $APP_DIR"
elif [ -d "$(pwd)/.git" ] && [ "$(pwd)" != "$APP_DIR" ]; then
    echo "  Copiando proyecto actual a $APP_DIR..."
    rsync -a "$(pwd)/" "$APP_DIR/" --exclude venv
elif [ ! -d "$APP_DIR/.git" ]; then
    echo "  Clonando desde GitHub..."
    read -p "  URL del repo GitHub (o Enter para saltar): " REPO_URL
    if [ -n "$REPO_URL" ]; then
        git clone "$REPO_URL" "$APP_DIR"
    else
        echo "  ERROR: Necesito el repo. Clone manualmente en $APP_DIR y vuelva a ejecutar."
        exit 1
    fi
fi

# 5. Instalar dependencias Python
echo "[5/7] Instalando dependencias Python..."
cd $APP_DIR
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
deactivate

# 6. Crear servicio systemd
echo "[6/7] Configurando servicio systemd..."
cat > /etc/systemd/system/erp-comercio.service << SYSTEMD
[Unit]
Description=ERP Comercio API
After=network.target

[Service]
Type=simple
User=$APP_USER
Group=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
Environment="DATABASE_URL=sqlite:///$DATA_DIR/erp_comercio.db"
Environment="JWT_SECRET=$(openssl rand -hex 32)"
ExecStart=$APP_DIR/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
SYSTEMD

# 7. Configurar permisos y arrancar
echo "[7/7] Configurando permisos..."
chown -R $APP_USER:$APP_USER $APP_DIR
chown -R $APP_USER:$APP_USER $DATA_DIR
chmod 755 $DATA_DIR

systemctl daemon-reload
systemctl enable erp-comercio
systemctl start erp-comercio

# Nginx
echo ""
echo "Configurando Nginx..."
cat > /etc/nginx/sites-available/erp-comercio << NGINX
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
    }
}
NGINX

ln -sf /etc/nginx/sites-available/erp-comercio /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

echo ""
echo "========================================"
echo "  INSTALACIÓN COMPLETA"
echo "========================================"
echo ""
echo "Servicio: systemctl status erp-comercio"
echo "Logs:     journalctl -u erp-comercio -f"
echo "DB:       $DATA_DIR/erp_comercio.db"
echo ""
echo "Próximo paso: SSL con Certbot"
echo "  sudo certbot --nginx -d $DOMAIN"
echo ""
echo "Después de SSL, el ERP estará en:"
echo "  https://$DOMAIN/app"
echo "  https://$DOMAIN/docs"
echo ""
echo "Abrir puerto 80 y 443 en Oracle Cloud:"
echo "  Oracle Console → Instancias → Subnet → Security List → Ingress Rules"
echo "  Agregar: 0.0.0.0/0 TCP 80 y 443"
echo "========================================"
