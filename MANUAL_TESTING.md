# 🧪 Guía de Pruebas Manuales de Deployment

Esta guía te ayudará a validar el proceso de deployment paso a paso antes de automatizarlo con GitHub Actions.

## ✅ Pre-requisitos

Antes de comenzar, asegúrate de tener:

- [ ] Python 3.11.9 instalado
- [ ] Node.js 24.x instalado
- [ ] Entorno virtual activado (env)
- [ ] Base de datos MySQL configurada
- [ ] Variables de entorno configuradas

---

## 📋 Fase 1: Pruebas Locales (Windows)

### 1.1 Probar Backend

#### Opción A: Script Automatizado
```powershell
# Ejecutar script de prueba
.\test_deploy_backend.ps1
```

#### Opción B: Paso a paso manual
```powershell
# 1. Activar entorno virtual
cd C:\Users\Admin\Documents\PPP\app_cinco
.\env\Scripts\Activate.ps1

# 2. Ir al directorio backend
cd backend

# 3. Verificar configuración
python manage.py check

# 4. Ver migraciones pendientes
python manage.py showmigrations

# 5. Aplicar migraciones (si es necesario)
python manage.py migrate --database=default
python manage.py migrate --database=azul

# 6. Collectstatic
python manage.py collectstatic --no-input

# 7. Iniciar servidor
python manage.py runserver
```

#### Verificar Endpoints:
```powershell
# Health Check (en otra terminal)
curl http://127.0.0.1:8000/auth/health/

# Debe retornar:
# {
#   "status": "healthy",
#   "service": "app-cinco-backend",
#   "databases": {
#     "default": "connected",
#     "azul": "connected"
#   }
# }

# Swagger UI
# Abrir en navegador: http://127.0.0.1:8000/api/docs/

# Admin
# Abrir en navegador: http://127.0.0.1:8000/
```

---

### 1.2 Probar Frontend

#### Opción A: Script Automatizado
```powershell
# Ejecutar script de prueba
.\test_deploy_frontend.ps1
```

#### Opción B: Paso a paso manual
```powershell
# 1. Ir al directorio frontend
cd C:\Users\Admin\Documents\PPP\app_cinco\frontend

# 2. Verificar/instalar dependencias
npm install

# 3. Crear .env.local si no existe
cp .env.local.example .env.local
# Editar .env.local con:
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/

# 4. Ejecutar linting
npm run lint

# 5. Build de producción
npm run build

# 6. Iniciar en modo producción
npm start
# O en modo desarrollo:
npm run dev
```

#### Verificar Frontend:
```powershell
# Abrir en navegador
# http://localhost:3000

# Verificar que se conecta al backend
# Revisar Network tab en DevTools
```

---

## 📋 Fase 2: Simulación de Deployment Completo

### 2.1 Backup Simulado

```powershell
# Crear directorio de backups
mkdir C:\Users\Admin\Documents\PPP\app_cinco\shared\backups

# Simular backup
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
Copy-Item -Recurse backend "shared\backups\backend_$timestamp"
Copy-Item -Recurse frontend "shared\backups\frontend_$timestamp"

Write-Host "Backup creado: backend_$timestamp"
```

### 2.2 Simular Pull de Cambios

```powershell
# Ver estado de Git
git status

# Ver diferencias con remoto
git fetch
git log HEAD..origin/main --oneline

# Hacer pull (simulación)
# git pull origin main
```

### 2.3 Reinstalar Dependencias

```powershell
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ..\frontend
npm ci
```

### 2.4 Ejecutar Migraciones

```powershell
cd ..\backend
python manage.py migrate --database=default
python manage.py migrate --database=azul
```

### 2.5 Rebuild Frontend

```powershell
cd ..\frontend
npm run build
```

### 2.6 Health Checks

```powershell
# Backend (debe estar corriendo)
curl http://127.0.0.1:8000/auth/health/

# Frontend (debe estar corriendo)
curl http://localhost:3000
```

---

## 📋 Fase 3: Checklist de Validación

### Backend
- [ ] `python manage.py check` sin errores
- [ ] Todas las migraciones aplicadas
- [ ] Health check responde 200
- [ ] Swagger UI accesible
- [ ] CORS configurado correctamente
- [ ] Conexión a ambas BDs funciona

### Frontend
- [ ] `npm run lint` sin errores
- [ ] Build exitoso sin warnings críticos
- [ ] Página principal carga correctamente
- [ ] Conexión al backend funciona
- [ ] Variables de entorno correctas
- [ ] API calls funcionan

### Integración
- [ ] Frontend puede hacer login
- [ ] Tokens JWT se generan correctamente
- [ ] Refresh token funciona
- [ ] CORS permite peticiones desde frontend
- [ ] Health check accesible sin autenticación

---

## 📋 Fase 4: Preparación para Servidor

Una vez que todo funcione localmente, prepara estos archivos para el servidor:

### 4.1 Scripts de Deployment (Linux/Bash)

Los scripts ya están documentados en `README.md` sección 3:
- `deploy_backend.sh`
- `deploy_frontend.sh`
- `rollback.sh`
- `monitor.sh`

### 4.2 Variables de Entorno

Asegúrate de tener configurados:

**Backend** (.env):
```env
DJANGO_SECRET_KEY=tu-secret-key-real
DJANGO_DEBUG=False
BD_NAME=db_cincosas
BD_USER=tu_usuario
BD_PASSWORD=tu_password
# ... resto de variables
```

**Frontend** (.env.local):
```env
NEXT_PUBLIC_API_URL=https://api.cincosas.com/
NEXT_PUBLIC_APP_NAME=App Cinco
```

### 4.3 Configuración Apache

Los archivos de configuración están en `README.md` sección 2:
- `api.cincosas.com.conf`
- `frontend.cincosas.com.conf`

---

## 📋 Fase 5: Pruebas de Rollback

### 5.1 Simular Rollback

```powershell
# Ver backups disponibles
Get-ChildItem shared\backups

# Simular rollback backend
$timestamp = "20260219_143022"  # Usar timestamp real
Remove-Item -Recurse backend
Copy-Item -Recurse "shared\backups\backend_$timestamp" backend

# Verificar
cd backend
python manage.py check
```

---

## 🐛 Troubleshooting

### Error: ModuleNotFoundError
```powershell
# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: CORS
```powershell
# Verificar CORS_ALLOWED_ORIGINS en settings.py
# Debe incluir: http://localhost:3000
```

### Error: Database connection
```powershell
# Verificar variables de entorno
# Verificar que MySQL esté corriendo
# Verificar credenciales
```

### Error: npm build fails
```powershell
# Limpiar node_modules y reinstalar
Remove-Item -Recurse node_modules
Remove-Item package-lock.json
npm install
```

---

## ✅ Checklist Final

Antes de proceder a automatizar con GitHub Actions:

- [ ] Backend funciona localmente
- [ ] Frontend funciona localmente
- [ ] Health check endpoint funciona
- [ ] Integración frontend-backend funciona
- [ ] Variables de entorno documentadas
- [ ] Scripts de deployment revisados
- [ ] Proceso de rollback probado
- [ ] Documentación actualizada
- [ ] Equipo capacitado en el proceso

---

## 🚀 Siguiente Paso

Una vez completadas todas las pruebas:

1. Commit de cambios:
```powershell
git add .
git commit -m "feat: add health check endpoint and deployment scripts"
git push origin develop
```

2. Configurar servidor según `README.md`
3. Probar deploy manual en servidor
4. Configurar GitHub Actions
5. Primer deploy automático

---

**Fecha de pruebas**: _____________
**Responsable**: _____________
**Estado**: [ ] En proceso [ ] Completado [ ] Bloqueado
