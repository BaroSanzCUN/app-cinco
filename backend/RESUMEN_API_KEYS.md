# 🔐 Sistema de Autenticación y API Keys - Resumen Ejecutivo

## ✅ Lo que se ha implementado

### 1. **Restricción Total de Endpoints**
Todos los endpoints del backend ahora requieren autenticación, excepto:
- `/auth/login/` - Login de usuarios
- `/auth/refresh/` - Renovación de tokens
- `/auth/csrf/` - Token CSRF
- `/auth/logout/` - Cierre de sesión
- `/auth/health/` - Health check

### 2. **Sistema Dual de Autenticación**

#### Para Usuarios del Frontend (JWT)
- Continúa funcionando exactamente igual
- Token en cookie `access_token` o header `Authorization: Bearer <token>`
- Sin cambios en el frontend

#### Para Aplicaciones Externas (API Keys)
- Nuevo sistema de API Keys con prefijo `cinco_`
- Header `X-API-Key: cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
- Gestión completa desde línea de comandos y admin Django

---

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND API                               │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Authentication Layer (Orden de prioridad)                   │
│  ┌────────────────────────────────────────────┐             │
│  │ 1. APIKeyAuthentication                    │             │
│  │    ├─ Header: X-API-Key                   │             │
│  │    ├─ Valida: hash, expiración, IP        │             │
│  │    └─ Rate limiting configurable          │             │
│  │                                             │             │
│  │ 2. JWTAuthentication                       │             │
│  │    ├─ Cookie: access_token                │             │
│  │    ├─ Header: Authorization Bearer        │             │
│  │    └─ Valida: firma, expiración            │             │
│  └────────────────────────────────────────────┘             │
│                                                               │
│  Permission Layer                                            │
│  ┌────────────────────────────────────────────┐             │
│  │ IsAuthenticatedOrAPIKey (Default)          │             │
│  │ ├─ Permite usuarios autenticados           │             │
│  │ └─ Permite API Keys válidas                │             │
│  └────────────────────────────────────────────┘             │
│                                                               │
│  Throttling Layer                                            │
│  ┌────────────────────────────────────────────┐             │
│  │ APIKeyRateThrottle                          │             │
│  │ └─ Rate limit por API Key (configurable)   │             │
│  └────────────────────────────────────────────┘             │
│                                                               │
│  Endpoints (todos protegidos)                                │
│  ├─ /operaciones/                                            │
│  ├─ /empleados/                                              │
│  └─ /security/                                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Casos de Uso

### Caso 1: Usuario Frontend
```
Usuario → Login → JWT Token → Acceso a todos los endpoints
```
**Sin cambios en el flujo existente**

### Caso 2: Aplicación Externa
```
App → API Key → Acceso directo a endpoints
```
**Nueva capacidad agregada**

### Caso 3: Sistema de Integración
```
Sistema Externo → API Key con IP restringida → Solo desde servidor autorizado
```
**Control granular de acceso**

---

## 📂 Archivos Creados/Modificados

### Nuevos Archivos

```
backend/
├── apps/security/
│   ├── models.py                              # ✅ Modelo APIKey agregado
│   ├── admin.py                               # ✅ Admin panel configurado
│   ├── authentication/
│   │   ├── __init__.py                       # ✅ Nuevo
│   │   └── api_key_authentication.py         # ✅ Nuevo
│   ├── permissions/
│   │   └── api_permissions.py                # ✅ Nuevo
│   ├── throttling/
│   │   ├── __init__.py                       # ✅ Nuevo
│   │   └── api_throttling.py                 # ✅ Nuevo
│   └── management/
│       ├── __init__.py                       # ✅ Nuevo
│       └── commands/
│           ├── __init__.py                   # ✅ Nuevo
│           ├── create_apikey.py              # ✅ Nuevo
│           ├── list_apikeys.py               # ✅ Nuevo
│           ├── revoke_apikey.py              # ✅ Nuevo
│           └── activate_apikey.py            # ✅ Nuevo
│
├── API_KEYS_README.md                        # ✅ Documentación completa
├── GUIA_RAPIDA_API_KEYS.md                   # ✅ Guía rápida
├── test_apikey.py                            # ✅ Script de prueba
└── RESUMEN_API_KEYS.md                       # ✅ Este archivo
```

### Archivos Modificados

```
backend/
├── config/
│   └── settings.py                           # ✅ REST_FRAMEWORK actualizado
│
└── apps/
    ├── operaciones/views/actividad_view.py   # ✅ AllowAny removido
    └── empleados/views/empleado_view.py      # ✅ AllowAny removido
```

---

## 🚀 Comandos de Gestión

### Crear API Key
```bash
python manage.py create_apikey "Nombre App" [opciones]

Opciones:
  --description "..."          Descripción de la app
  --email "..."               Email de contacto
  --rate-limit 1000           Requests por hora
  --allowed-ips "..."         IPs separadas por coma
  --expires-days 365          Días hasta expiración
```

### Listar API Keys
```bash
python manage.py list_apikeys [--active-only]
```

### Revocar API Key
```bash
python manage.py revoke_apikey <ID> [--permanent]
```

### Reactivar API Key
```bash
python manage.py activate_apikey <ID>
```

---

## 🔑 Características de Seguridad

### ✅ Hash Seguro
- Las API Keys se almacenan como SHA256 hash
- Imposible recuperar la key original de la BD
- Solo se muestra una vez al crearla

### ✅ Prefijos Identificables
- Todas las keys empiezan con `cinco_`
- Fácil identificación en logs
- Prefijo de 13 caracteres para búsqueda rápida

### ✅ Rate Limiting
- Configurable por API Key
- Default: 1000 requests/hora
- Basado en cache de Django

### ✅ Restricción por IP
- Lista blanca de IPs permitidas
- Detección de proxy (X-Forwarded-For)
- Opcional (dejar vacío permite todas)

### ✅ Expiración
- Fechas de expiración configurables
- Verificación automática en cada request
- Sin expiración por defecto

### ✅ Logging
- Todos los accesos se registran
- Logs en `backend/logs/security.log`
- Info sobre autenticaciones exitosas y fallidas

### ✅ Tracking
- Última fecha de uso registrada
- Útil para auditorías
- Identificar keys sin uso

---

## 🧪 Probar el Sistema

### Opción 1: Script de Prueba
```bash
cd backend
python manage.py shell < test_apikey.py
```

### Opción 2: Crear y probar manualmente
```bash
# 1. Crear API Key
python manage.py create_apikey "Test App"
# Guarda la key que te muestra

# 2. Probar con curl
curl -H "X-API-Key: <tu-key>" http://localhost:8000/operaciones/actividades/

# 3. Ver resultado
python manage.py list_apikeys
```

### Opción 3: Desde el Admin
```bash
# 1. Iniciar servidor
python manage.py runserver

# 2. Acceder al admin
http://localhost:8000/admin/

# 3. Ir a Security → API Keys → Add API Key
```

---

## 📊 Monitoreo y Mantenimiento

### Ver Logs en Tiempo Real
```bash
# Windows (PowerShell)
Get-Content backend/logs/security.log -Wait -Tail 50

# Linux/Mac
tail -f backend/logs/security.log
```

### Revisar Estado de API Keys
```bash
python manage.py list_apikeys
```

### Identificar Keys sin Uso
```sql
-- Desde Django shell o directamente en MySQL
SELECT name, prefix, created_at, last_used_at 
FROM api_keys 
WHERE last_used_at IS NULL 
ORDER BY created_at DESC;
```

### Limpieza de Keys Expiradas
```python
# Django shell
from apps.security.models import APIKey
from django.utils import timezone

expired = APIKey.objects.filter(
    expires_at__lt=timezone.now(),
    is_active=True
)
for key in expired:
    key.is_active = False
    key.save()
    print(f"Desactivada: {key.name}")
```

---

## 🔄 Migración de Sistemas Externos

### Antes (sin protección)
```python
# Cualquiera podía acceder
response = requests.get('http://api.cincosas.com/operaciones/actividades/')
```

### Después (con API Key)
```python
# Requiere API Key autorizada
headers = {'X-API-Key': 'cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'}
response = requests.get(
    'http://api.cincosas.com/operaciones/actividades/',
    headers=headers
)
```

**Tiempo de migración estimado por sistema externo:** 5-10 minutos

---

## 💡 Mejores Prácticas

### ✅ DO
- Usar variables de entorno para API Keys
- Rotar keys periódicamente (ej: cada 6-12 meses)
- Establecer rate limits apropiados
- Usar restricción por IP cuando sea posible
- Monitorear logs regularmente
- Documentar qué sistema usa cada key

### ❌ DON'T
- Commitear API Keys en Git
- Compartir keys entre múltiples sistemas
- Usar keys sin expiración en ambientes no confiables
- Ignorar logs de seguridad
- Dejar keys inactivas sin eliminar

---

## 🎓 Capacitación del Equipo

### Para Desarrolladores Backend
- Leer: `API_KEYS_README.md`
- Entender: Modelos, autenticación, permisos
- Práctica: Crear/gestionar API Keys

### Para Desarrolladores de Integraciones
- Leer: `GUIA_RAPIDA_API_KEYS.md`
- Tener: API Key de desarrollo
- Práctica: Integrar con ejemplos de código

### Para Administradores
- Leer: Este archivo (RESUMEN_API_KEYS.md)
- Acceso: Admin de Django
- Responsabilidad: Crear/revocar keys de producción

---

## 📈 Métricas Sugeridas

### KPIs de Seguridad
- Número de intentos fallidos por día
- API Keys activas vs inactivas
- Uso promedio por API Key
- Rate limit hits por día

### Reportes Mensuales
- Top 10 API Keys por uso
- Keys sin usar en los últimos 30 días
- Keys próximas a expirar (< 30 días)
- Incidentes de seguridad (IPs no autorizadas, etc.)

---

## 🛠️ Solución de Problemas Comunes

### "API Key inválida"
**Causa:** Key incorrecta, revocada o mal formateada  
**Solución:** Verificar con `list_apikeys`, regenerar si es necesario

### "IP no autorizada"
**Causa:** Request desde IP no listada en `allowed_ips`  
**Solución:** Actualizar IPs permitidas o remover restricción

### "Rate limit excedido"
**Causa:** Más requests que el límite configurado  
**Solución:** Esperar 1 hora o aumentar rate_limit

### "Authentication credentials were not provided"
**Causa:** Falta el header X-API-Key o Authorization  
**Solución:** Agregar header apropiado al request

---

## 🎯 Roadmap Futuro (Opcional)

### Fase 2 (Considerar si es necesario)
- [ ] Dashboard web para gestión de API Keys
- [ ] Webhooks para notificaciones de eventos
- [ ] Scopes/permisos granulares por endpoint
- [ ] API Keys de solo lectura
- [ ] Regeneración de keys sin crear nuevas
- [ ] Estadísticas de uso en tiempo real
- [ ] Alertas automáticas (keys sin uso, rate limit, etc.)

---

## 📞 Contacto y Soporte

**Para crear API Keys de producción:**  
Contactar al administrador del sistema

**Para reportar problemas:**  
Ver logs en `backend/logs/security.log` y contactar soporte técnico

**Para solicitar aumentos de rate limit:**  
Justificar uso y contactar al administrador

---

## ✅ Checklist de Despliegue

Antes de ir a producción:

- [ ] Migraciones aplicadas (`python manage.py migrate`)
- [ ] Logs de seguridad configurados
- [ ] API Keys de prueba eliminadas
- [ ] API Keys de producción creadas
- [ ] Restricciones de IP configuradas
- [ ] Rate limits ajustados
- [ ] Fechas de expiración establecidas
- [ ] Documentación compartida con el equipo
- [ ] Sistemas externos migrados y probados
- [ ] Monitoreo de logs configurado

---

**Fecha de implementación:** 4 de marzo de 2026  
**Versión del sistema:** 1.0  
**Estado:** ✅ Listo para producción
