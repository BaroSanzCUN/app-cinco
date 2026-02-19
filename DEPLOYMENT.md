# 🚀 Guía Rápida de Deployment

## Deploy Manual

### Backend (Django)
```bash
ssh deployer@cincosas.com
bash /home/admcinco/deployment/deploy_backend.sh
```

### Frontend (Next.js)
```bash
ssh deployer@cincosas.com
bash /home/admcinco/deployment/deploy_frontend.sh
```

## Rollback

### Listar backups disponibles
```bash
ls -lh /home/admcinco/app_cinco/shared/backups/
```

### Ejecutar rollback
```bash
# Backend
bash /home/admcinco/deployment/rollback.sh backend 20260219_143022

# Frontend
bash /home/admcinco/deployment/rollback.sh frontend 20260219_143022
```

## Ver Logs

### Apache (Backend)
```bash
sudo tail -f /var/log/apache2/api.cincosas.com-error.log
```

### PM2 (Frontend)
```bash
pm2 logs app-cinco-frontend
pm2 logs app-cinco-frontend --lines 100
```

### Monitoreo
```bash
tail -f /home/admcinco/app_cinco/shared/logs/monitor.log
```

## Health Checks

```bash
# Backend
curl https://api.cincosas.com/auth/health/

# Frontend
curl https://frontend.cincosas.com/
```

## Comandos Útiles

### Apache
```bash
sudo systemctl status apache2
sudo systemctl reload apache2
sudo apache2ctl configtest
```

### PM2
```bash
pm2 status
pm2 restart app-cinco-frontend
pm2 monit
```

### Django
```bash
cd /home/admcinco/app_cinco
source env/bin/activate
cd backend
python manage.py check
python manage.py migrate
```

## Deploy Automático (GitHub Actions)

1. Hacer commit de cambios
2. Push a `main` branch
3. GitHub Actions ejecutará tests y deploy automáticamente
4. Verificar en: https://github.com/[tu-repo]/actions

## Troubleshooting Rápido

### Apache no inicia
```bash
sudo apache2ctl configtest
sudo tail -100 /var/log/apache2/error.log
sudo systemctl restart apache2
```

### PM2 no mantiene proceso
```bash
pm2 logs app-cinco-frontend --err
cd /home/admcinco/app_cinco/frontend
npm run build
pm2 restart app-cinco-frontend
```

### Base de datos
```bash
mysql -u root -p db_cincosas
python manage.py showmigrations
python manage.py migrate
```

## Contactos de Emergencia

- Logs: `/var/log/apache2/` y `pm2 logs`
- Backups: `/home/admcinco/app_cinco/shared/backups/`
- Documentación completa: Ver README.md en raíz del proyecto
