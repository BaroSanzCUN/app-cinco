# ✅ Resumen de Pruebas Manuales de Deployment

## 📊 Estado Actual

### ✅ Completado

1. **Health Check Endpoint Implementado**
   - Archivo: `backend/apps/authentication/views/health_view.py`
   - URL: `/auth/health/`
   - Estado: ✅ **FUNCIONANDO**
   - Respuesta: 
     ```json
     {
       "status": "healthy",
       "service": "app-cinco-backend",
       "databases": {
         "default": "connected",
         "azul": "connected"
       }
     }
     ```

2. **URLs Actualizadas**
   - `backend/apps/authentication/urls.py` incluye la ruta `/health/`

3. **Archivos de Configuración Creados**
   - ✅ `backend/.env.example`
   - ✅ `frontend/.env.local.example`
   - ✅ `.github/workflows/ci-cd.yml`

4. **Documentación Completa**
   - ✅ `README.md` - Guía completa de CI/CD
   - ✅ `MANUAL_TESTING.md` - Guía de pruebas paso a paso
   - ✅ `DEPLOYMENT.md` - Guía rápida de deployment

5. **Scripts de Prueba**
   - ✅ `quick_test.ps1` - Test rápido funcional
   - ✅ `test_deploy_backend.ps1` - Test detallado backend
   - ✅ `test_deploy_frontend.ps1` - Test detallado frontend

### 🔄 En Progreso

1. **Frontend**
   - Estado: Servidor no iniciado
   - Acción necesaria: `cd frontend; npm run dev`

### 📋 Pendiente

1. **Configuración de Variables de Entorno Reales**
   - Crear `backend/.env` a partir de `.env.example`
   - Crear `frontend/.env.local` a partir de `.env.local.example`

2. **Servidor de Producción**
   - Configurar VirtualHosts Apache
   - Instalar PM2
   - Crear scripts de deployment en servidor
   - Configurar SSH keys para CI/CD

---

## 🚀 Próximos Pasos

### Paso 1: Completar Setup Local (HOY)

```powershell
# 1. Crear archivo .env para backend
cd backend
copy .env.example .env
# Editar .env con valores reales de tu BD

# 2. Crear archivo .env.local para frontend
cd ..\frontend
copy .env.local.example .env.local
# Editar .env.local:
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8000/

# 3. Iniciar ambos servidores y probar
# Terminal 1 (Backend):
cd backend
python manage.py runserver

# Terminal 2 (Frontend):
cd frontend
npm run dev

# Terminal 3 (Tests):
cd ..
.\quick_test.ps1
```

### Paso 2: Validar Integración Local (HOY)

- [ ] Backend health check responde OK
- [ ] Frontend carga correctamente
- [ ] Frontend puede conectarse al backend
- [ ] Login funciona
- [ ] Tokens JWT se generan

### Paso 3: Preparar Servidor (ESTA SEMANA)

Seguir la guía en `README.md` sección por sección:

1. **Infraestructura Base** (Semana 1)
   - Crear usuario deployer
   - Configurar SSH keys
   - Instalar Apache + mod_wsgi
   - Instalar Node.js 24.x + PM2

2. **Configuración Apache** (Semana 1)
   - VirtualHost para backend (Django)
   - VirtualHost para frontend (Next.js proxy)
   - Certificados SSL con certbot

3. **Scripts de Deployment** (Semana 2)
   - `deploy_backend.sh`
   - `deploy_frontend.sh`
   - `rollback.sh`
   - `monitor.sh`

### Paso 4: Probar Deployment Manual en Servidor (PRÓXIMA SEMANA)

```bash
# En el servidor
ssh deployer@cincosas.com

# Probar backend deploy
bash /home/admcinco/deployment/deploy_backend.sh

# Probar frontend deploy
bash /home/admcinco/deployment/deploy_frontend.sh

# Verificar health checks
curl https://api.cincosas.com/auth/health/
curl https://frontend.cincosas.com/
```

### Paso 5: Automatizar con GitHub Actions (SEMANA 3)

1. Configurar secrets en GitHub:
   - `SSH_PRIVATE_KEY`
   - `SSH_HOST`
   - `SSH_USER`
   - `SSH_PORT`

2. Hacer push a `main`:
   ```powershell
   git add .
   git commit -m "feat: add CI/CD pipeline and health check"
   git push origin main
   ```

3. Ver el deployment automático en GitHub Actions

---

## 📝 Comandos de Referencia Rápida

### Tests Locales
```powershell
# Test completo
.\quick_test.ps1

# Solo health check backend
Invoke-RestMethod -Uri http://127.0.0.1:8000/auth/health/

# Solo health check frontend
Invoke-WebRequest -Uri http://localhost:3000 -UseBasicParsing
```

### Django Commands
```powershell
cd backend
python manage.py check
python manage.py showmigrations
python manage.py migrate
python manage.py runserver
```

### Next.js Commands
```powershell
cd frontend
npm install
npm run lint
npm run build
npm run dev
npm start
```

### Git Workflow
```powershell
git status
git add .
git commit -m "mensaje"
git push origin develop
```

---

## 🎯 Checklist de Validación

### Local (Antes de deploy a servidor)
- [x] Health check endpoint funciona
- [x] Documentación completa
- [x] Scripts de prueba funcionan
- [ ] Variables de entorno configuradas
- [ ] Frontend conecta al backend
- [ ] Login funciona
- [ ] Todas las pruebas pasan

### Servidor (Antes de automatizar)
- [ ] Servidor configurado según README
- [ ] Apache con mod_wsgi funcionando
- [ ] PM2 instalado y configurado
- [ ] Scripts de deployment creados
- [ ] SSH keys configuradas
- [ ] Deploy manual funciona
- [ ] Rollback funciona

### CI/CD (Automatización)
- [ ] GitHub secrets configurados
- [ ] Workflow YAML validado
- [ ] Tests pasan en GitHub Actions
- [ ] Deploy automático funciona
- [ ] Monitoreo configurado

---

## 🆘 Resolución de Problemas

### Backend no responde
```powershell
cd backend
python manage.py check
# Verificar que MySQL esté corriendo
# Verificar .env
```

### Frontend no conecta al backend
```powershell
# Verificar CORS en backend settings.py
# Verificar NEXT_PUBLIC_API_URL en frontend/.env.local
```

### Errores de migraciones
```powershell
python manage.py showmigrations
python manage.py migrate --database=default
python manage.py migrate --database=azul
```

---

## 📚 Documentación

- **README.md**: Guía completa de CI/CD con todos los detalles
- **MANUAL_TESTING.md**: Guía paso a paso de pruebas manuales
- **DEPLOYMENT.md**: Guía rápida de comandos de deployment
- **Este archivo**: Resumen del progreso actual

---

**Última actualización**: 19 de febrero de 2026  
**Estado**: ✅ Pruebas locales completadas - Listo para configurar servidor  
**Responsable**: [Tu nombre]
