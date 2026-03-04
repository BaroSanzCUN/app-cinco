# Sistema de API Keys para Aplicaciones Externas

## Descripción

Este sistema permite que aplicaciones externas autorizadas accedan al backend mediante API Keys, manteniendo todos los endpoints protegidos. Soporta autenticación dual:

- **JWT (Usuarios)**: Para usuarios autenticados del frontend
- **API Keys (Apps Externas)**: Para aplicaciones externas con autorización previa

## Características

✅ Autenticación dual (JWT + API Keys)  
✅ Rate limiting configurable por API Key  
✅ Restricción por IP  
✅ Fechas de expiración  
✅ Logs de uso y seguridad  
✅ Comandos de gestión integrados  

---

## Configuración Realizada

### 1. Modelo APIKey
- Almacena API Keys de forma segura (solo se guarda el hash SHA256)
- Configuración individual de rate limits
- Restricción por IPs permitidas
- Fechas de expiración opcionales
- Tracking de último uso

### 2. Autenticación
- `APIKeyAuthentication`: Verifica el header `X-API-Key`
- `JWTAuthentication`: Mantiene la autenticación JWT existente
- Orden de prioridad: API Key → JWT

### 3. Permisos
- `IsAuthenticatedOrAPIKey`: Permite usuarios o API Keys
- `IsUserOnly`: Solo usuarios autenticados (no API Keys)
- `IsAPIKeyOnly`: Solo API Keys (no usuarios)
- `IsAuthenticatedUser`: Solo usuarios autenticados (estricto)

### 4. Rate Limiting
- `APIKeyRateThrottle`: Limita requests según configuración de cada API Key

---

## Uso de API Keys

### Crear una API Key

```bash
# Básico
python manage.py create_apikey "Mi Aplicación"

# Con todas las opciones
python manage.py create_apikey "Mi Aplicación" \
    --description "Integración con sistema externo" \
    --email "admin@ejemplo.com" \
    --rate-limit 5000 \
    --allowed-ips "192.168.1.100, 10.0.0.50" \
    --expires-days 365
```

**Salida:**
```
======================================================================
✓ API Key creada exitosamente
======================================================================

Nombre:       Mi Aplicación
ID:           1
Rate Limit:   5000 requests/hora
IPs Permitidas: 192.168.1.100, 10.0.0.50
Expira:       2027-03-04 10:30

⚠ IMPORTANTE: Guarda esta API Key de forma segura.
No podrás verla de nuevo.

API Key:
cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Uso en requests:
  Header: X-API-Key: cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Listar API Keys

```bash
# Todas las API Keys
python manage.py list_apikeys

# Solo las activas
python manage.py list_apikeys --active-only
```

### Revocar una API Key

```bash
# Desactivar (reversible)
python manage.py revoke_apikey 1

# Eliminar permanentemente
python manage.py revoke_apikey 1 --permanent
```

### Reactivar una API Key

```bash
python manage.py activate_apikey 1
```

---

## Usar API Keys en Requests

### cURL
```bash
curl -H "X-API-Key: cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
     https://api.cincosas.com/operaciones/actividades/
```

### Python (requests)
```python
import requests

headers = {
    'X-API-Key': 'cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'Content-Type': 'application/json'
}

response = requests.get(
    'https://api.cincosas.com/operaciones/actividades/',
    headers=headers
)
```

### JavaScript (fetch)
```javascript
fetch('https://api.cincosas.com/operaciones/actividades/', {
  headers: {
    'X-API-Key': 'cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx',
    'Content-Type': 'application/json'
  }
})
```

### Axios
```javascript
axios.get('https://api.cincosas.com/operaciones/actividades/', {
  headers: {
    'X-API-Key': 'cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  }
})
```

---

## Endpoints Protegidos

### Todos los endpoints requieren autenticación

Excepto:
- `/auth/login/` - Login de usuarios
- `/auth/refresh/` - Refresh de tokens JWT
- `/auth/csrf/` - Obtener CSRF token
- `/auth/logout/` - Logout de usuarios
- `/auth/health/` - Health check

Todos los demás endpoints aceptan:
- **JWT**: Header `Authorization: Bearer <token>` o cookie `access_token`
- **API Key**: Header `X-API-Key: cinco_xxxxx...`

---

## Configuración Avanzada

### Personalizar permisos por endpoint

```python
# apps/miapp/views.py
from rest_framework.viewsets import ModelViewSet
from apps.security.permissions.api_permissions import IsUserOnly

class MiViewSet(ModelViewSet):
    # Solo usuarios, no API Keys
    permission_classes = [IsUserOnly]
```

### Crear endpoints específicos para API Keys

```python
from apps.security.permissions.api_permissions import IsAPIKeyOnly

class IntegrationViewSet(ModelViewSet):
    # Solo API Keys, no usuarios
    permission_classes = [IsAPIKeyOnly]
```

### Verificar el tipo de autenticación

```python
from apps.security.models import APIKey

def my_view(request):
    if isinstance(request.auth, APIKey):
        # Request desde API Key
        print(f"App externa: {request.auth.name}")
    elif request.user.is_authenticated:
        # Request desde usuario
        print(f"Usuario: {request.user.username}")
```

---

## Monitoreo y Seguridad

### Logs
Los intentos de acceso con API Keys se registran en:
- `backend/logs/security.log`

### Eventos registrados:
- ✅ Autenticación exitosa
- ⚠️ API Key inválida
- ⚠️ API Key expirada
- ⚠️ IP no autorizada
- ⚠️ Rate limit excedido

### Consultar uso

```python
from apps.security.models import APIKey

# Ver último uso de una API Key
api_key = APIKey.objects.get(id=1)
print(f"Último uso: {api_key.last_used_at}")
```

---

## Migración

Ejecutar migraciones para crear la tabla:

```bash
python manage.py makemigrations security
python manage.py migrate security
```

---

## Troubleshooting

### "API Key inválida"
- Verifica que la API Key sea correcta (empieza con `cinco_`)
- Verifica que la API Key esté activa: `list_apikeys`

### "IP no autorizada"
- La IP del cliente no está en la lista de IPs permitidas
- Actualiza las IPs permitidas desde el admin o creando una nueva key

### "Rate limit excedido"
- La aplicación superó el límite de requests/hora
- Espera a que pase la hora o aumenta el rate_limit

### "API Key expirada"
- La API Key llegó a su fecha de expiración
- Crea una nueva API Key o actualiza la fecha de expiración

---

## Seguridad

### ⚠️ Mejores Prácticas

1. **Nunca** compartas API Keys públicamente
2. **Nunca** commites API Keys en el código
3. Usa variables de entorno para almacenar API Keys
4. Rota API Keys periódicamente
5. Usa rate limits apropiados
6. Restringe por IP cuando sea posible
7. Establece fechas de expiración
8. Monitorea los logs de seguridad

### Ejemplo .env
```bash
# .env (en la app externa)
API_KEY=cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
API_BASE_URL=https://api.cincosas.com
```

---

## Ejemplos de Integración

### App Django Externa
```python
# settings.py
API_KEY = os.environ.get('API_KEY')
API_BASE_URL = os.environ.get('API_BASE_URL')

# services.py
import requests
from django.conf import settings

def get_actividades():
    response = requests.get(
        f'{settings.API_BASE_URL}/operaciones/actividades/',
        headers={'X-API-Key': settings.API_KEY}
    )
    return response.json()
```

### App Node.js Externa
```javascript
// config.js
require('dotenv').config();

module.exports = {
  apiKey: process.env.API_KEY,
  apiBaseUrl: process.env.API_BASE_URL
};

// services/api.js
const axios = require('axios');
const config = require('./config');

const api = axios.create({
  baseURL: config.apiBaseUrl,
  headers: {
    'X-API-Key': config.apiKey
  }
});

async function getActividades() {
  const response = await api.get('/operaciones/actividades/');
  return response.data;
}
```

---

## Soporte

Para crear, revocar o gestionar API Keys, contacta al administrador del sistema.

Para reportar problemas de seguridad, usa el email configurado en la API Key o contacta directamente.
