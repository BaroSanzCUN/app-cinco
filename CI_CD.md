# 🚀 CI/CD y Despliegue en Apache - App Cinco

Este documento describe el paso a paso para implementar CI/CD para este proyecto, desplegado en un servidor Apache dedicado que coexiste con una aplicación legacy en PHP.

## 📦 Stack Tecnológico

- **Backend**: Django 5.2.10 + Django REST Framework + Python 3.11.9
- **Frontend**: Next.js 16.1.6 + React 19 + TypeScript 5.9.3
- **Base de datos**: MySQL 8.0 (2 bases: default y azul)
- **Servidor web**: Apache 2.4 con mod_wsgi
- **Dominios**:
  - API Backend: `api.cincosas.com`
  - Frontend: `frontend.cincosas.com`
  - Legacy PHP: `legacy.cincosas.com` (o dominio existente)

## 1️⃣ Preparación del Entorno

### 1.1 Estructura del servidor

```
/home/admcinco/
├── app_cinco/                    # Nueva app (Django + Next.js)
│   ├── backend/
│   ├── frontend/
│   ├── env/                      # Virtualenv Python 3.11.9
│   └── shared/
│       ├── logs/
│       ├── backups/
│       └── scripts/
├── public_html/                  # App PHP existente
└── deployment/
    ├── deploy_backend.sh
    ├── deploy_frontend.sh
    ├── rollback.sh
    ├── monitor.sh
    └── health_check.sh
```

### 1.2 Usuario de despliegue

```bash
# Crear usuario exclusivo para deployment (NO usar root)
sudo adduser deployer
sudo usermod -aG www-data deployer

# Configurar permisos
sudo chown -R deployer:www-data /home/admcinco/app_cinco
sudo chmod -R 755 /home/admcinco/app_cinco

# Verificar que Python 3.11.9 esté disponible
python3 --version  # Debe mostrar: Python 3.11.9
```

### 1.3 SSH Keys para CI/CD

```bash
# En el servidor
sudo su - deployer
ssh-keygen -t ed25519 -C "ci-cd-deployer-app-cinco" -f ~/.ssh/ci_cd_key

# Agregar a authorized_keys
cat ~/.ssh/ci_cd_key.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys

# Copiar la PRIVATE key (ci_cd_key) para GitHub Secrets
cat ~/.ssh/ci_cd_key
# Guardar el contenido completo (incluyendo BEGIN y END) como SSH_PRIVATE_KEY en GitHub
```

---

## 2️⃣ Configuración de Apache

### 2.1 Instalar módulos requeridos

```bash
# Instalar mod_wsgi para Python 3.11
sudo apt update
sudo apt install apache2 libapache2-mod-wsgi-py3

# Habilitar módulos necesarios
sudo a2enmod ssl rewrite proxy proxy_http wsgi headers

# Verificar instalación
apache2ctl -M | grep wsgi
```

### 2.2 VirtualHost Backend Django (mod_wsgi)

Crear archivo: `/etc/apache2/sites-available/api.cincosas.com.conf`

```apache
<VirtualHost *:80>
    ServerName api.cincosas.com
    ServerAlias www.api.cincosas.com

    # Redirección HTTPS (recomendado para producción)
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</VirtualHost>

<VirtualHost *:443>
    ServerName api.cincosas.com
    ServerAlias www.api.cincosas.com

    # Certificados SSL (usar certbot: sudo certbot --apache -d api.cincosas.com)
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/api.cincosas.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/api.cincosas.com/privkey.pem

    # Django WSGI Configuration
    WSGIDaemonProcess django_app_cinco \
        python-home=/home/admcinco/app_cinco/env \
        python-path=/home/admcinco/app_cinco/backend \
        user=deployer \
        group=www-data \
        processes=2 \
        threads=15 \
        display-name=%{GROUP}

    WSGIProcessGroup django_app_cinco
    WSGIScriptAlias / /home/admcinco/app_cinco/backend/config/wsgi.py

    <Directory /home/admcinco/app_cinco/backend/config>
        <Files wsgi.py>
            Require all granted
        </Files>
    </Directory>

    # Archivos estáticos de Django
    Alias /static /home/admcinco/app_cinco/backend/static
    <Directory /home/admcinco/app_cinco/backend/static>
        Require all granted
        Options -Indexes
    </Directory>

    # Logs
    ErrorLog ${APACHE_LOG_DIR}/api.cincosas.com-error.log
    CustomLog ${APACHE_LOG_DIR}/api.cincosas.com-access.log combined

    # Security headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set X-XSS-Protection "1; mode=block"
</VirtualHost>
```

### 2.3 VirtualHost Frontend Next.js (Proxy Reverso)

Crear archivo: `/etc/apache2/sites-available/frontend.cincosas.com.conf`

```apache
<VirtualHost *:80>
    ServerName frontend.cincosas.com
    RewriteEngine On
    RewriteCond %{HTTPS} off
    RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]
</VirtualHost>

<VirtualHost *:443>
    ServerName frontend.cincosas.com

    # Certificados SSL
    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/frontend.cincosas.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/frontend.cincosas.com/privkey.pem

    # Proxy a Next.js (Node 24.x corriendo en puerto 3000)
    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:3000/
    ProxyPassReverse / http://127.0.0.1:3000/

    # WebSocket support (para Hot Reload en dev)
    RewriteEngine On
    RewriteCond %{HTTP:Upgrade} websocket [NC]
    RewriteCond %{HTTP:Connection} upgrade [NC]
    RewriteRule /(.*) ws://127.0.0.1:3000/$1 [P,L]

    # Timeout para requests largos
    ProxyTimeout 300

    # Logs
    ErrorLog ${APACHE_LOG_DIR}/frontend.cincosas.com-error.log
    CustomLog ${APACHE_LOG_DIR}/frontend.cincosas.com-access.log combined

    # Security headers
    Header always set X-Content-Type-Options "nosniff"
    Header always set X-Frame-Options "SAMEORIGIN"
    Header always set Referrer-Policy "strict-origin-when-cross-origin"
</VirtualHost>
```

### 2.4 Coexistencia con App Legacy PHP

Si tu aplicación PHP legacy está en el mismo servidor:

```apache
# /etc/apache2/sites-available/legacy.cincosas.com.conf
<VirtualHost *:443>
    ServerName legacy.cincosas.com

    DocumentRoot /home/admcinco/app_legacy_php/public

    <Directory /home/admcinco/app_legacy_php/public>
        Options Indexes FollowSymLinks
        AllowOverride All
        Require all granted
    </Directory>

    # PHP-FPM (ajustar versión según tu instalación)
    <FilesMatch \.php$>
        SetHandler "proxy:unix:/var/run/php/php8.1-fpm.sock|fcgi://localhost"
    </FilesMatch>

    SSLEngine on
    SSLCertificateFile /etc/letsencrypt/live/legacy.cincosas.com/fullchain.pem
    SSLCertificateKeyFile /etc/letsencrypt/live/legacy.cincosas.com/privkey.pem

    ErrorLog ${APACHE_LOG_DIR}/legacy.cincosas.com-error.log
    CustomLog ${APACHE_LOG_DIR}/legacy.cincosas.com-access.log combined
</VirtualHost>
```

**Nota**: Las tres aplicaciones pueden coexistir en el mismo Apache sin conflictos.

### 2.5 Activar configuraciones

```bash
# Habilitar sitios
sudo a2ensite api.cincosas.com.conf
sudo a2ensite frontend.cincosas.com.conf

# Verificar configuración (no debe mostrar errores)
sudo apache2ctl configtest

# Si muestra "Syntax OK", reiniciar Apache
sudo systemctl reload apache2

# Verificar que Apache esté corriendo
sudo systemctl status apache2
```

---

## 3️⃣ Scripts de Deployment

Crear directorio y archivos de deployment:

```bash
sudo mkdir -p /home/admcinco/deployment
sudo chown deployer:www-data /home/admcinco/deployment
```

### 3.1 Script de Deploy Backend

Crear archivo: `/home/admcinco/deployment/deploy_backend.sh`

```bash
#!/bin/bash
set -e

echo "=== 🚀 Inicio Deploy Backend - App Cinco ==="

PROJECT_DIR="/home/admcinco/app_cinco"
BACKEND_DIR="$PROJECT_DIR/backend"
ENV_DIR="$PROJECT_DIR/env"
BACKUP_DIR="$PROJECT_DIR/shared/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. Crear backup
echo "📦 Creando backup..."
mkdir -p $BACKUP_DIR
cp -r $BACKEND_DIR $BACKUP_DIR/backend_$TIMESTAMP

# 2. Pull cambios (preservar .env)
echo "⬇️ Descargando cambios desde repositorio..."
cd $PROJECT_DIR
git stash push -- backend/.env backend/config/.env || true
git pull origin main
git stash pop || true

# 3. Activar entorno virtual Python 3.11.9
echo "🐍 Activando entorno virtual..."
source $ENV_DIR/bin/activate

# Verificar Python
python --version

# 4. Instalar/actualizar dependencias
echo "📚 Instalando dependencias..."
cd $BACKEND_DIR
pip install -r requirements.txt --quiet

# 5. Ejecutar migraciones
echo "🗄️ Aplicando migraciones..."
python manage.py migrate --database=default --no-input
python manage.py migrate --database=azul --no-input

# 6. Collectstatic
echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --no-input --clear

# 7. Reiniciar Apache
echo "🔄 Reiniciando Apache..."
sudo systemctl reload apache2

# 8. Health check
echo "🏥 Verificando estado del backend..."
sleep 3
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://api.cincosas.com/auth/health/ || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Deploy exitoso - Backend respondiendo correctamente"
    # Limpiar backups antiguos (>7 días)
    find $BACKUP_DIR -type d -name "backend_*" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    exit 0
else
    echo "❌ Error - Backend no responde (HTTP $HTTP_CODE)"
    echo "🔙 Ejecutando rollback automático..."
    bash /home/admcinco/deployment/rollback.sh backend $TIMESTAMP
    exit 1
fi
```

### 3.2 Script de Deploy Frontend

Crear archivo: `/home/admcinco/deployment/deploy_frontend.sh`

```bash
#!/bin/bash
set -e

echo "=== 🚀 Inicio Deploy Frontend - App Cinco ==="

PROJECT_DIR="/home/admcinco/app_cinco"
FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKUP_DIR="$PROJECT_DIR/shared/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. Crear backup
echo "📦 Creando backup..."
mkdir -p $BACKUP_DIR
cp -r $FRONTEND_DIR $BACKUP_DIR/frontend_$TIMESTAMP

# 2. Pull cambios (preservar .env.local)
echo "⬇️ Descargando cambios desde repositorio..."
cd $PROJECT_DIR
git stash push -- frontend/.env.local || true
git pull origin main
git stash pop || true

# 3. Instalar dependencias (Node 24.x)
echo "📚 Instalando dependencias..."
cd $FRONTEND_DIR

# Verificar Node version
node --version

# Instalar dependencias (ci es más rápido y determinista que install)
npm ci --production=false

# 4. Build de Next.js
echo "🏗️ Construyendo aplicación Next.js..."
npm run build

# 5. Reiniciar PM2
echo "🔄 Reiniciando proceso Next.js con PM2..."
pm2 restart app-cinco-frontend || pm2 start npm --name "app-cinco-frontend" -- start

# 6. Health check
echo "🏥 Verificando estado del frontend..."
sleep 5
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" https://frontend.cincosas.com/ || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo "✅ Deploy exitoso - Frontend respondiendo correctamente"
    # Limpiar backups antiguos (>7 días)
    find $BACKUP_DIR -type d -name "frontend_*" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
    exit 0
else
    echo "❌ Error - Frontend no responde (HTTP $HTTP_CODE)"
    echo "🔙 Ejecutando rollback automático..."
    bash /home/admcinco/deployment/rollback.sh frontend $TIMESTAMP
    exit 1
fi
```

### 3.3 Script de Rollback

Crear archivo: `/home/admcinco/deployment/rollback.sh`

```bash
#!/bin/bash
set -e

APP_TYPE=$1  # backend o frontend
TIMESTAMP=$2

BACKUP_DIR="/home/admcinco/app_cinco/shared/backups"
PROJECT_DIR="/home/admcinco/app_cinco"

if [ -z "$APP_TYPE" ] || [ -z "$TIMESTAMP" ]; then
    echo "❌ Uso: ./rollback.sh [backend|frontend] [timestamp]"
    echo "Ejemplo: ./rollback.sh backend 20260219_143022"
    exit 1
fi

echo "🔙 Iniciando rollback de $APP_TYPE a versión $TIMESTAMP"

if [ "$APP_TYPE" = "backend" ]; then
    echo "Restaurando backend..."
    rm -rf $PROJECT_DIR/backend
    cp -r $BACKUP_DIR/backend_$TIMESTAMP $PROJECT_DIR/backend
    
    echo "Reiniciando Apache..."
    sudo systemctl reload apache2
    
    echo "✅ Rollback de backend completado"
    
elif [ "$APP_TYPE" = "frontend" ]; then
    echo "Restaurando frontend..."
    rm -rf $PROJECT_DIR/frontend
    cp -r $BACKUP_DIR/frontend_$TIMESTAMP $PROJECT_DIR/frontend
    
    echo "Reiniciando PM2..."
    cd $PROJECT_DIR/frontend
    pm2 restart app-cinco-frontend
    
    echo "✅ Rollback de frontend completado"
else
    echo "❌ Tipo de app inválido. Use: backend o frontend"
    exit 1
fi

echo "Verificando servicio restaurado..."
sleep 3

if [ "$APP_TYPE" = "backend" ]; then
    curl -f https://api.cincosas.com/auth/health/ && echo "✅ Backend operativo" || echo "⚠️ Verificar manualmente"
else
    curl -f https://frontend.cincosas.com/ && echo "✅ Frontend operativo" || echo "⚠️ Verificar manualmente"
fi
```

### 3.4 Dar permisos de ejecución

```bash
# Hacer scripts ejecutables
chmod +x /home/admcinco/deployment/*.sh

# Configurar sudo sin password para reload de Apache (solo para deployer)
sudo visudo

# Agregar al final del archivo:
deployer ALL=(ALL) NOPASSWD: /bin/systemctl reload apache2
deployer ALL=(ALL) NOPASSWD: /bin/systemctl status apache2
```

---

## 4️⃣ GitHub Actions CI/CD

### 4.1 Secrets en GitHub

Ir a tu repositorio GitHub → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Agregar los siguientes secrets:

```
Nombre: SSH_PRIVATE_KEY
Valor: [contenido completo de ~/.ssh/ci_cd_key del servidor]

Nombre: SSH_HOST
Valor: [IP del servidor o cincosas.com]

Nombre: SSH_USER
Valor: deployer

Nombre: SSH_PORT
Valor: 22

Nombre: DJANGO_SECRET_KEY (opcional, para tests)
Valor: [tu secret key de Django]
```

### 4.2 Workflow Principal de CI/CD

Crear archivo: `.github/workflows/ci-cd.yml`

```yaml
name: CI/CD Pipeline - App Cinco

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PYTHON_VERSION: '3.11.9'
  NODE_VERSION: '24.x'

jobs:
  # ========== TEST BACKEND ==========
  test-backend:
    name: 🧪 Test Backend (Django 5.2.10)
    runs-on: ubuntu-latest
    
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: test_password
          MYSQL_DATABASE: test_db_default
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Python 3.11.9
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
          cache-dependency-path: 'backend/requirements.txt'
      
      - name: Install dependencies
        working-directory: ./backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-django pytest-cov flake8
      
      - name: Run linting
        working-directory: ./backend
        run: |
          flake8 apps/ config/ --max-line-length=120 --exclude=migrations,__pycache__,*.pyc --count || true
      
      - name: Run Django checks
        working-directory: ./backend
        env:
          DJANGO_SECRET_KEY: test-secret-key-for-ci-cd-pipeline
          BD_NAME: test_db_default
          BD_USER: root
          BD_PASSWORD: test_password
          BD_HOST: 127.0.0.1
          BD_PORT: 3306
          DB_AZUL_NAME: test_db_default
          DB_AZUL_USER: root
          DB_AZUL_PASSWORD: test_password
          DB_AZUL_HOST: 127.0.0.1
          DB_AZUL_PORT: 3306
        run: |
          python manage.py check --deploy
      
      # Descomentar cuando tengas tests
      # - name: Run tests
      #   working-directory: ./backend
      #   env:
      #     DJANGO_SECRET_KEY: test-secret-key-for-ci-cd-pipeline
      #   run: |
      #     pytest --cov=apps --cov-report=xml

  # ========== TEST FRONTEND ==========
  test-frontend:
    name: 🧪 Test Frontend (Next.js 16 + React 19)
    runs-on: ubuntu-latest
    
    steps:
      - name: Checkout code
        uses: actions/checkout@v4
      
      - name: Set up Node.js 24.x
        uses: actions/setup-node@v4
        with:
          node-version: ${{ env.NODE_VERSION }}
          cache: 'npm'
          cache-dependency-path: './frontend/package-lock.json'
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Run linting
        working-directory: ./frontend
        run: npm run lint
      
      - name: Build Next.js
        working-directory: ./frontend
        env:
          NEXT_PUBLIC_API_URL: https://api.cincosas.com/
        run: npm run build
      
      # Descomentar cuando tengas tests
      # - name: Run tests
      #   working-directory: ./frontend
      #   run: npm test

  # ========== DEPLOY A PRODUCCIÓN ==========
  deploy:
    name: 🚀 Deploy to Production (Apache)
    needs: [test-backend, test-frontend]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    
    steps:
      - name: Configure SSH
        run: |
          mkdir -p ~/.ssh/
          echo "${{ secrets.SSH_PRIVATE_KEY }}" > ~/.ssh/deploy_key
          chmod 600 ~/.ssh/deploy_key
          cat >>~/.ssh/config <<END
          Host production
            HostName ${{ secrets.SSH_HOST }}
            User ${{ secrets.SSH_USER }}
            Port ${{ secrets.SSH_PORT }}
            IdentityFile ~/.ssh/deploy_key
            StrictHostKeyChecking no
          END
      
      - name: Deploy Backend (Django + Apache)
        run: |
          echo "🚀 Desplegando backend..."
          ssh production 'bash /home/admcinco/deployment/deploy_backend.sh'
      
      - name: Deploy Frontend (Next.js + PM2)
        run: |
          echo "🚀 Desplegando frontend..."
          ssh production 'bash /home/admcinco/deployment/deploy_frontend.sh'
      
      - name: Verify Deployment
        run: |
          echo "🏥 Verificando endpoints..."
          curl -f https://api.cincosas.com/auth/health/ || exit 1
          curl -f https://frontend.cincosas.com/ || exit 1
          echo "✅ Deployment verificado exitosamente"
      
      - name: Notify Success
        if: success()
        run: |
          echo "✅ Deployment completado exitosamente: $(date)"
          echo "Backend: https://api.cincosas.com/"
          echo "Frontend: https://frontend.cincosas.com/"
      
      - name: Notify Failure
        if: failure()
        run: |
          echo "❌ Deployment falló: $(date)"
          echo "Revisar logs en GitHub Actions"
```

---

## 5️⃣ Servicios del Servidor

### 5.1 Instalar y configurar PM2 para Next.js

PM2 es un gestor de procesos para Node.js que mantiene la aplicación corriendo.

```bash
# Instalar PM2 globalmente (como deployer)
sudo npm install -g pm2

# Configurar PM2 para Next.js
cd /home/admcinco/app_cinco/frontend

# Iniciar aplicación
pm2 start npm --name "app-cinco-frontend" -- start

# Guardar configuración
pm2 save

# Configurar PM2 para iniciar al bootear el servidor
pm2 startup systemd
# Ejecutar el comando que PM2 muestre

# Ver logs en tiempo real
pm2 logs app-cinco-frontend

# Ver estado
pm2 status

# Reiniciar
pm2 restart app-cinco-frontend

# Detener
pm2 stop app-cinco-frontend
```

### 5.2 Implementar Health Check en Backend

Agregar endpoint de health check para monitoreo automatizado.

**Paso 1**: Crear vista - `backend/apps/authentication/views/health_view.py`

```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.db import connection, connections

class HealthCheckView(APIView):
    """
    Health check endpoint para CI/CD y monitoreo
    """
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        try:
            # Verificar conexión a base de datos default
            connections['default'].ensure_connection()
            
            # Verificar conexión a base de datos azul
            connections['azul'].ensure_connection()
            
            return Response({
                "status": "healthy",
                "service": "app-cinco-backend",
                "databases": {
                    "default": "connected",
                    "azul": "connected"
                }
            }, status=status.HTTP_200_OK)
        except Exception as exc:
            return Response({
                "status": "unhealthy",
                "service": "app-cinco-backend",
                "error": str(exc)
            }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
```

**Paso 2**: Agregar ruta - `backend/apps/authentication/urls.py`

```python
from django.urls import path
from .views import login_view, refresh_view, health_view

urlpatterns = [
    path("login/", login_view.LoginView.as_view(), name="login"),
    path("refresh/", refresh_view.RefreshTokenView.as_view(), name="refresh"),
    path("health/", health_view.HealthCheckView.as_view(), name="health"),
]
```

**Paso 3**: Probar endpoint

```bash
# Local
curl http://127.0.0.1:8000/auth/health/

# Producción
curl https://api.cincosas.com/auth/health/
```

---

## 6️⃣ Logs y Monitoreo

### 6.1 Configurar Logrotate

Evitar que los logs crezcan indefinidamente.

Crear archivo: `/etc/logrotate.d/app-cinco`

```
/home/admcinco/app_cinco/shared/logs/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    missingok
    create 0640 deployer www-data
    sharedscripts
    postrotate
        pm2 reloadLogs
    endscript
}
```

Probar configuración:

```bash
sudo logrotate -d /etc/logrotate.d/app-cinco
```

### 6.2 Script de Monitoreo

Crear archivo: `/home/admcinco/deployment/monitor.sh`

```bash
#!/bin/bash

LOG_FILE="/home/admcinco/app_cinco/shared/logs/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$DATE] Iniciando monitoreo..." >> $LOG_FILE

check_service() {
    SERVICE=$1
    URL=$2
    
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 $URL)
    
    if [ "$HTTP_CODE" = "200" ]; then
        echo "[$DATE] ✅ $SERVICE UP (HTTP $HTTP_CODE)" >> $LOG_FILE
        return 0
    else
        echo "[$DATE] ❌ $SERVICE DOWN (HTTP $HTTP_CODE)" >> $LOG_FILE
        # Aquí puedes agregar notificación por email o Slack
        return 1
    fi
}

# Monitorear servicios
check_service "Backend" "https://api.cincosas.com/auth/health/"
check_service "Frontend" "https://frontend.cincosas.com/"

# Verificar PM2
PM2_STATUS=$(pm2 list | grep "app-cinco-frontend" | grep "online" || echo "")

if [ -n "$PM2_STATUS" ]; then
    echo "[$DATE] ✅ PM2 process running" >> $LOG_FILE
else
    echo "[$DATE] ⚠️ PM2 process not running - attempting restart" >> $LOG_FILE
    pm2 restart app-cinco-frontend >> $LOG_FILE 2>&1
fi

# Verificar Apache
APACHE_STATUS=$(systemctl is-active apache2)
if [ "$APACHE_STATUS" = "active" ]; then
    echo "[$DATE] ✅ Apache running" >> $LOG_FILE
else
    echo "[$DATE] ❌ Apache not running" >> $LOG_FILE
fi

echo "[$DATE] Monitoreo completado" >> $LOG_FILE
echo "---" >> $LOG_FILE
```

Hacer ejecutable:

```bash
chmod +x /home/admcinco/deployment/monitor.sh
```

### 6.3 Configurar Cron para Monitoreo Automático

```bash
# Editar crontab del usuario deployer
crontab -e

# Agregar estas líneas:

# Monitoreo cada 5 minutos
*/5 * * * * /home/admcinco/deployment/monitor.sh

# Backup diario de base de datos a las 2 AM
0 2 * * * /home/admcinco/deployment/backup_db.sh
```

### 6.4 Ubicación de Logs Importantes

```bash
# Logs de Apache
/var/log/apache2/api.cincosas.com-error.log
/var/log/apache2/api.cincosas.com-access.log
/var/log/apache2/frontend.cincosas.com-error.log

# Logs de PM2
pm2 logs app-cinco-frontend
pm2 logs app-cinco-frontend --lines 100

# Logs de aplicación personalizada
/home/admcinco/app_cinco/shared/logs/

# Logs del sistema
/var/log/syslog
```

---

## 7️⃣ Variables de Entorno

### 7.1 Archivo .env.example para Backend

Crear archivo en la raíz del proyecto: `backend/.env.example`

```env
# Django Configuration
DJANGO_SECRET_KEY=your-secret-key-here-change-in-production
DJANGO_DEBUG=False

# Database Default
BD_NAME=db_cincosas
BD_USER=db_user
BD_PASSWORD=secure_password_here
BD_HOST=127.0.0.1
BD_PORT=3306

# Database Azul (segunda BD)
DB_AZUL_NAME=cinco-api
DB_AZUL_USER=db_user
DB_AZUL_PASSWORD=secure_password_here
DB_AZUL_HOST=127.0.0.1
DB_AZUL_PORT=3306

# Paths (para producción en Apache)
BASE_PATH=/home/admcinco/app_cinco/backend/

# Hosts permitidos (separados por coma)
ALLOWED_HOSTS=api.cincosas.com,www.api.cincosas.com,192.168.79.11,127.0.0.1,localhost
```

### 7.2 Archivo .env.example para Frontend

Crear archivo en la raíz del proyecto: `frontend/.env.local.example`

```env
# API URL
NEXT_PUBLIC_API_URL=https://api.cincosas.com/

# App Configuration
NEXT_PUBLIC_APP_NAME=App Cinco

# Node Environment
NODE_ENV=production
```

### 7.3 Configurar variables en el servidor

```bash
# Backend
cd /home/admcinco/app_cinco/backend
cp .env.example .env
nano .env  # Editar con valores reales

# Frontend
cd /home/admcinco/app_cinco/frontend
cp .env.local.example .env.local
nano .env.local  # Editar con valores reales
```

**⚠️ IMPORTANTE**: Los archivos `.env` y `.env.local` NO deben incluirse en Git (ya están en `.gitignore`).

---

## 8️⃣ Checklist de Implementación

### Semana 1: Infraestructura Base
- [ ] Crear usuario `deployer` en servidor
- [ ] Configurar SSH keys para CI/CD
- [ ] Instalar Apache con mod_wsgi
- [ ] Configurar VirtualHosts (Backend, Frontend, Legacy)
- [ ] Obtener certificados SSL con certbot
- [ ] Instalar Node.js 24.x y PM2
- [ ] Crear estructura de directorios

### Semana 2: Scripts y Deploy Manual
- [ ] Crear scripts de deployment (`deploy_backend.sh`, `deploy_frontend.sh`)
- [ ] Crear script de rollback
- [ ] Implementar health check endpoint en Django
- [ ] Probar deployment manual (backend y frontend)
- [ ] Configurar PM2 para autostart
- [ ] Configurar logs y logrotate

### Semana 3: Automatización CI/CD
- [ ] Crear archivo `.github/workflows/ci-cd.yml`
- [ ] Configurar secrets en GitHub
- [ ] Primer deployment automático desde GitHub Actions
- [ ] Verificar que tests pasen correctamente
- [ ] Configurar monitoreo con cron
- [ ] Documentar proceso (este README)

### Semana 4: Optimización y Tests
- [ ] Implementar tests unitarios (backend con pytest)
- [ ] Implementar tests unitarios (frontend con vitest/jest)
- [ ] Configurar ambiente staging (opcional)
- [ ] Optimizar tiempos de build
- [ ] Capacitar al equipo en el flujo de trabajo
- [ ] Post-mortem y ajustes finales

### Semana 5: Monitoreo y Mejoras
- [ ] Configurar alertas (email/Slack)
- [ ] Implementar backups automáticos de BD
- [ ] Documentación de troubleshooting
- [ ] Plan de disaster recovery
- [ ] Revisión de seguridad
- [ ] Optimización de performance

---

## 9️⃣ Comandos Útiles del Día a Día

### 9.1 Apache

```bash
# Verificar configuración
sudo apache2ctl configtest

# Reiniciar Apache
sudo systemctl restart apache2

# Recargar configuración (sin downtime)
sudo systemctl reload apache2

# Ver estado
sudo systemctl status apache2

# Ver logs en tiempo real
sudo tail -f /var/log/apache2/api.cincosas.com-error.log
sudo tail -f /var/log/apache2/frontend.cincosas.com-error.log

# Ver todos los VirtualHosts activos
apache2ctl -S
```

### 9.2 PM2 (Next.js)

```bash
# Ver estado de procesos
pm2 status

# Ver logs en tiempo real
pm2 logs app-cinco-frontend

# Ver últimas 100 líneas de logs
pm2 logs app-cinco-frontend --lines 100

# Reiniciar aplicación
pm2 restart app-cinco-frontend

# Detener aplicación
pm2 stop app-cinco-frontend

# Iniciar aplicación
pm2 start app-cinco-frontend

# Ver información detallada
pm2 show app-cinco-frontend

# Monitoreo en tiempo real (CPU, memoria)
pm2 monit

# Limpiar logs viejos
pm2 flush
```

### 9.3 Django (Backend)

```bash
# Activar entorno virtual
cd /home/admcinco/app_cinco
source env/bin/activate

# Ver migraciones pendientes
cd backend
python manage.py showmigrations

# Ejecutar migraciones
python manage.py migrate --database=default
python manage.py migrate --database=azul

# Crear superusuario
python manage.py createsuperuser

# Shell interactivo de Django
python manage.py shell

# Verificar configuración
python manage.py check --deploy

# Collectstatic
python manage.py collectstatic --no-input

# Ver versión de Django
python manage.py version
```

### 9.4 Base de Datos

```bash
# Conectar a MySQL
mysql -u root -p -h 127.0.0.1 db_cincosas

# Backup de base de datos
mysqldump -u root -p db_cincosas > backup_$(date +%Y%m%d).sql
mysqldump -u root -p cinco-api > backup_azul_$(date +%Y%m%d).sql

# Restaurar backup
mysql -u root -p db_cincosas < backup_20260219.sql

# Ver tamaño de bases de datos
mysql -u root -p -e "SELECT table_schema AS 'Database', 
ROUND(SUM(data_length + index_length) / 1024 / 1024, 2) AS 'Size (MB)' 
FROM information_schema.TABLES GROUP BY table_schema;"
```

### 9.5 Git y Deployment

```bash
# Ver estado del repositorio
cd /home/admcinco/app_cinco
git status

# Ver último commit
git log -1

# Ver cambios sin hacer pull
git fetch
git log HEAD..origin/main --oneline

# Deploy manual backend
bash /home/admcinco/deployment/deploy_backend.sh

# Deploy manual frontend
bash /home/admcinco/deployment/deploy_frontend.sh

# Rollback a versión anterior
bash /home/admcinco/deployment/rollback.sh backend 20260219_143022

# Ver backups disponibles
ls -lh /home/admcinco/app_cinco/shared/backups/
```

### 9.6 Monitoreo del Sistema

```bash
# Ver uso de disco
df -h

# Ver uso de memoria
free -h

# Ver procesos que más consumen recursos
htop

# Ver conexiones a MySQL
mysqladmin -u root -p processlist

# Ver puertos en uso
sudo netstat -tulpn | grep LISTEN

# Ver logs del sistema
sudo tail -f /var/log/syslog
```

---

## 🔟 Troubleshooting

### Problema: Apache no inicia

```bash
# Verificar errores de configuración
sudo apache2ctl configtest

# Ver logs de error
sudo tail -100 /var/log/apache2/error.log

# Verificar que el puerto 80/443 no esté ocupado
sudo netstat -tulpn | grep :80
sudo netstat -tulpn | grep :443

# Reiniciar Apache
sudo systemctl restart apache2
```

### Problema: PM2 proceso no se mantiene

```bash
# Ver logs de error
pm2 logs app-cinco-frontend --err

# Verificar que el build sea correcto
cd /home/admcinco/app_cinco/frontend
npm run build

# Reiniciar PM2
pm2 delete app-cinco-frontend
pm2 start npm --name "app-cinco-frontend" -- start
pm2 save

# Verificar startup
pm2 startup
```

### Problema: Deploy falla en SSH

```bash
# Verificar permisos de la key
chmod 600 ~/.ssh/ci_cd_key

# Probar conexión SSH manual
ssh -i ~/.ssh/ci_cd_key deployer@cincosas.com

# Verificar que la key esté en authorized_keys
cat ~/.ssh/authorized_keys
```

### Problema: Migraciones fallan

```bash
# Ver migraciones pendientes
python manage.py showmigrations

# Hacer fake de migración problemática
python manage.py migrate --fake app_name migration_name

# Rollback de última migración
python manage.py migrate app_name previous_migration_name

# Crear backup antes de migrar
mysqldump -u root -p db_cincosas > backup_pre_migration.sql
```

### Problema: 502 Bad Gateway (Frontend)

```bash
# Verificar que Next.js esté corriendo
pm2 status
curl http://127.0.0.1:3000

# Ver logs de PM2
pm2 logs app-cinco-frontend

# Reiniciar proceso
pm2 restart app-cinco-frontend

# Verificar configuración de Apache proxy
sudo apache2ctl -S
```

### Problema: CORS errors

```bash
# Verificar ALLOWED_HOSTS en settings.py
cd /home/admcinco/app_cinco/backend
nano config/settings.py

# Verificar CORS_ALLOWED_ORIGINS
# Debe incluir: https://frontend.cincosas.com

# Reiniciar Apache después de cambios
sudo systemctl reload apache2
```

---

## 📚 Referencias y Recursos

- **Django**: https://docs.djangoproject.com/
- **Next.js**: https://nextjs.org/docs
- **Apache mod_wsgi**: https://modwsgi.readthedocs.io/
- **PM2**: https://pm2.keymetrics.io/
- **GitHub Actions**: https://docs.github.com/actions
- **Let's Encrypt**: https://letsencrypt.org/

---

## 👥 Equipo y Soporte

Para dudas o problemas con el deployment:

1. Revisar los logs en `/var/log/apache2/` y `pm2 logs`
2. Consultar esta documentación
3. Revisar el estado de GitHub Actions
4. Contactar al equipo de DevOps

---

**Última actualización**: Febrero 2026  
**Versiones**: Django 5.2.10 | Next.js 16.1.6 | Python 3.11.9 | Node 24.x
