# ✅ Compatibilidad con Frontend Existente

## 🎯 Importante: Tu Frontend NO requiere cambios

El sistema de API Keys se diseñó para ser **100% compatible con el frontend existente**.

---

## Cómo Funciona

### Frontend (Sin cambios)
```javascript
// Tu código actual sigue funcionando igual
const response = await fetch('/operaciones/actividades/', {
  headers: {
    'Authorization': `Bearer ${token}`, // JWT funciona igual
    // o usa cookies automáticamente
  }
});
```

### Aplicaciones Externas (Nuevo)
```javascript
// Solo para apps externas
const response = await fetch('/operaciones/actividades/', {
  headers: {
    'X-API-Key': 'cinco_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
  }
});
```

---

## Orden de Autenticación

El backend verifica en este orden:

1. **¿Hay header `X-API-Key`?**  
   → SÍ: Usar autenticación por API Key  
   → NO: Continuar al paso 2

2. **¿Hay cookie `access_token`?**  
   → SÍ: Usar autenticación JWT  
   → NO: Continuar al paso 3

3. **¿Hay header `Authorization: Bearer`?**  
   → SÍ: Usar autenticación JWT  
   → NO: Denegar acceso (401 Unauthorized)

---

## Escenarios

### ✅ Usuario del Frontend
- Envía: JWT (cookie o header)
- Backend: Autentica con JWT
- Resultado: ✓ Acceso permitido
- **Sin cambios requeridos**

### ✅ Aplicación Externa
- Envía: API Key (header)
- Backend: Autentica con API Key
- Resultado: ✓ Acceso permitido
- **Nueva funcionalidad**

### ✅ Endpoint Público (login, health)
- Envía: Nada
- Backend: Permite sin autenticación
- Resultado: ✓ Acceso permitido
- **Sin cambios**

### ❌ Request sin autenticación
- Envía: Nada
- Backend: Rechaza
- Resultado: ✗ 401 Unauthorized
- **Nueva restricción** (antes algunos endpoints permitían AllowAny)

---

## Diferencias Claves

### Usuarios (JWT)
- Tienen **contexto de usuario** (`request.user` disponible)
- Pueden acceder a endpoints que requieren usuario específico
- Afectados por permisos de usuario (admin, roles, etc.)

### API Keys
- **No tienen usuario** (`request.user` es None)
- No pueden acceder a endpoints que requieren contexto de usuario
- Identificados por `request.auth` (objeto APIKey)
- Útiles para integraciones sistema-a-sistema

---

## Endpoints que Requieren Usuario

Si necesitas que un endpoint sea **solo para usuarios** (no API Keys):

```python
from apps.security.permissions.api_permissions import IsUserOnly

class MiViewSet(ModelViewSet):
    permission_classes = [IsUserOnly]  # Solo usuarios, no API Keys
```

Ejemplos de endpoints que deberían ser solo para usuarios:
- Perfil de usuario
- Cambio de contraseña
- Preferencias personales
- Notificaciones de usuario

---

## Verificar Tipo de Autenticación en el Código

```python
from apps.security.models import APIKey

def my_view(request):
    if isinstance(request.auth, APIKey):
        # Es una aplicación externa
        app_name = request.auth.name
        print(f"Acceso desde app: {app_name}")
        
    elif request.user.is_authenticated:
        # Es un usuario del frontend
        username = request.user.username
        print(f"Acceso desde usuario: {username}")
        
    else:
        # No autenticado (no debería llegar aquí si el endpoint está protegido)
        pass
```

---

## Respuestas de Error

### Sin autenticación
```json
{
  "detail": "Authentication credentials were not provided."
}
```

### Token JWT expirado
```json
{
  "detail": "Token expirado"
}
```

### API Key inválida
```json
{
  "detail": "API Key inválida"
}
```

### API Key con IP no autorizada
```json
{
  "detail": "IP no autorizada"
}
```

### Rate limit excedido
```json
{
  "detail": "Rate limit excedido. Límite: 1000 requests/hora",
  "available_in": 3456  // segundos hasta que se resetee
}
```

---

## Testing del Frontend

### Verificar que el frontend sigue funcionando:

1. **Login**
   ```bash
   POST /auth/login/
   Body: { username, password }
   Resultado esperado: Cookie access_token
   ```

2. **Acceder a endpoints protegidos**
   ```bash
   GET /operaciones/actividades/
   Cookie: access_token=...
   Resultado esperado: 200 OK con datos
   ```

3. **Refresh token**
   ```bash
   POST /auth/refresh/
   Cookie: refresh_token=...
   Resultado esperado: Nuevo access_token
   ```

4. **Logout**
   ```bash
   POST /auth/logout/
   Resultado esperado: Cookies eliminadas
   ```

### Si algo no funciona:

1. Verificar que las cookies se estén enviando
2. Revisar la configuración de CORS
3. Verificar que no haya errores en `config/settings.py`
4. Revisar logs: `backend/logs/security.log`

---

## FAQ

### ¿El frontend necesita cambios?
**No.** El frontend sigue usando JWT exactamente igual.

### ¿Los usuarios del frontend pueden seguir usando la app?
**Sí.** Sin ningún cambio en su experiencia.

### ¿Qué endpoints cambiaron?
Solo se restringieron algunos que antes tenían `AllowAny`:
- `/operaciones/actividades/` - Ahora requiere autenticación
- `/empleados/` - Ahora requiere autenticación

Pero el frontend ya enviaba JWT, así que no hay problema.

### ¿Las API Keys reemplazan JWT?
**No.** Son complementarias:
- JWT: Para usuarios del frontend
- API Keys: Para aplicaciones externas

### ¿Puedo usar ambos?
Sí, pero no tiene sentido. Si envías ambos, se usará la API Key (tiene prioridad).

### ¿Cómo sé si mi request usó JWT o API Key?
Revisa los logs en `backend/logs/security.log` o en el response del servidor.

---

## Migración del Frontend (si es necesario)

Si por alguna razón quieres actualizar el frontend para manejar errores específicos:

```javascript
// frontend/src/utils/api.js
async function fetchWithAuth(url, options = {}) {
  const token = getCookie('access_token');
  
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      'Authorization': `Bearer ${token}`
    }
  });

  if (response.status === 401) {
    const error = await response.json();
    
    if (error.detail === 'Token expirado') {
      // Intentar refresh
      await refreshToken();
      // Reintentar request
      return fetchWithAuth(url, options);
    }
    
    // Otro error de autenticación
    redirectToLogin();
  }

  return response;
}
```

Pero esto es **opcional** - tu código actual debería funcionar sin cambios.

---

## Resumen

🟢 **Frontend actual:** Funciona sin cambios  
🟢 **Usuarios:** Sin impacto  
🟢 **JWT:** Sigue funcionando igual  
🟢 **Cookies:** Siguen funcionando igual  
🟡 **Apps externas:** Ahora pueden usar API Keys  
🟡 **Endpoints públicos:** Ahora restringidos (pero frontend ya autenticaba)  

**Conclusión:** El sistema es retrocompatible y no requiere cambios en el frontend.
