# 📚 Índice de Documentación - Backend

## 📖 Documentación Principal

### [README_API.md](./README_API.md) ⭐ **EMPEZAR AQUÍ**
Guía completa de la API con:
- Todos los endpoints disponibles
- Flujos comunes de uso
- Ejemplos de requests/responses
- Códigos de error
- Herramientas para testing

---

## 🔑 Documentación por Módulo

### **Autenticación** (`/auth/`)
- Endpoints de login, logout, refresh, csrf, health
- Ya documentado en Swagger

### **Empleados** (`/empleados/empleados/`)
- CRUD completo de empleados
- Búsqueda por cédula, nombre, apellido, cargo, móvil
- **Documentación Swagger:** ✅ Completada

### **Operaciones - Actividades** (`/operaciones/actividades/`)
- CRUD completo de actividades/solicitudes
- Filtrado avanzado por 10+ parámetros
- Búsqueda general
- **Documentación específica:**
  - [SWAGGER_DOCUMENTATION.md](./apps/operaciones/SWAGGER_DOCUMENTATION.md)
  - [FILTRADO_ACTIVIDADES.md](./apps/operaciones/FILTRADO_ACTIVIDADES.md)
  - [API_REST_REFERENCE.md](./apps/operaciones/API_REST_REFERENCE.md)

### **Security** (`/security/`)
- Menú dinámico según permisos del usuario
- Ya documentado en Swagger

---

## 🔗 Acceso a Documentación Interactiva

### **Swagger UI** (Interfaz Visual) 🎯
```
http://127.0.0.1:8000/api/docs/
```
- Prueba endpoints directamente
- Autorización integrada (Bearer Token)
- Esquemas de request/response

### **ReDoc** (Documentación Formal)
```
http://127.0.0.1:8000/api/redoc/
```
- Visualización limpia y estructurada
- Lectura únicamente

### **OpenAPI JSON** (Para Herramientas)
```
http://127.0.0.1:8000/api/schema/
```
- Importa en Postman, Insomnia, etc.

---

## 📋 Resumen de Endpoints Documentados

| Módulo | Path | Métodos | Estado |
|--------|------|---------|--------|
| **Auth** | `/auth/login/` | POST | ✅ |
| **Auth** | `/auth/logout/` | POST | ✅ |
| **Auth** | `/auth/refresh/` | POST | ✅ |
| **Auth** | `/auth/csrf/` | GET | ✅ |
| **Auth** | `/auth/health/` | GET | ✅ |
| **Security** | `/security/menu/` | GET | ✅ |
| **Empleados** | `/empleados/empleados/` | GET,POST,PUT,PATCH,DELETE | ✅ |
| **Operaciones** | `/operaciones/actividades/` | GET,POST,PUT,PATCH,DELETE | ✅ |

---

## 🚀 Inicio Rápido

### 1. Inicia el servidor
```bash
cd backend
python manage.py runserver
```

### 2. Abre Swagger UI
```
http://127.0.0.1:8000/api/docs/
```

### 3. Obtén un token
```bash
POST /auth/login/
{
  "username": "tu_usuario",
  "password": "tu_contraseña"
}
```

### 4. Prueba endpoints
- Click "Authorize"
- Pega `Bearer <token>`
- Click en cualquier endpoint
- Click "Try it out"
- Envía request

---

## 📚 Archivos de Documentación

### En la raíz (`backend/`)
```
README_API.md                    ← Guía completa de API
README_DOCS.md (índice)          ← Este archivo
requirements.txt                 ← Dependencias Python
manage.py                        ← Comando de Django
```

### En `apps/operaciones/`
```
SWAGGER_DOCUMENTATION.md         ← Detalles de Swagger
FILTRADO_ACTIVIDADES.md          ← Parámetros de filtro
API_REST_REFERENCE.md            ← Referencia técnica
README_DOCS.md                   ← Índice local
example.http                     ← Ejemplos HTTP
```

---

## 🔐 Flujo de Autenticación

```
1. POST /auth/login/
   → Obtener access_token + refresh_token

2. GET /auth/csrf/
   → Obtener CSRF cookie (para frontend)

3. Usar access_token en requests:
   Authorization: Bearer <access_token>

4. Si token expira:
   POST /auth/refresh/
   → Obtener nuevo access_token

5. Para logout:
   POST /auth/logout/
   → Revocar tokens
```

---

## 🧪 Herramientas de Testing

### **Swagger UI** (Recomendado)
- Sin instalación, directo en navegador
- URL: `http://127.0.0.1:8000/api/docs/`

### **Postman**
```
1. File → Import
2. Pega: http://127.0.0.1:8000/api/schema/
3. Configura Bearer Token
4. Prueba endpoints
```

### **Insomnia**
```
1. Create → Request
2. Importar desde: http://127.0.0.1:8000/api/schema/
3. Autorización Bearer Token
4. Enviar
```

### **cURL**
```bash
curl -X GET "http://127.0.0.1:8000/operaciones/actividades/" \
  -H "Authorization: Bearer <token>"
```

### **VS Code REST Client**
```
Ver archivo: backend/example.http
Instala extensión "REST Client"
Ejecuta requests directamente
```

---

## 📊 Características Principales

### ✅ Autenticación
- Login/Logout
- JWT con refresh token rotation
- CSRF protection
- Device fingerprinting

### ✅ Gestión de Empleados
- CRUD completo
- Búsqueda avanzada
- Filtrado por estado (ACTIVO/INACTIVO/LICENCIA)

### ✅ Gestión de Actividades
- CRUD completo
- Filtrado automático por perfil (tu creadas + asignadas)
- 10+ parámetros de filtrado
- Búsqueda general
- Snapshot de responsable
- Soft delete

### ✅ Seguridad
- Menú dinámico basado en permisos
- API Key support
- Logging de seguridad
- Health checks

### ✅ Documentación
- OpenAPI 3.0 completo
- Swagger UI interactivo
- ReDoc formal
- Markdown detallado

---

## ⚙️ Configuración

### Variables de Entorno
Ver `.env` o `config/settings.py`

### Base de Datos
- **Default:** MySQL (Creencia)
- **Secundaria:** MySQL (Azul) para empleados

### Permisos
- `IsAuthenticatedOrAPIKey` por defecto
- `HasMenuPermission` para menú

---

## 🐛 Troubleshooting

### "Failed to load API definition"
- Reinicia servidor: `Ctrl+C` y `python manage.py runserver`
- Verifica sintaxis en archivo de vistas
- Ver logs en terminal

### "Unauthorized"
- Verifica que el token sea válido
- Obtén nuevo token: `POST /auth/login/`
- Formato correcto: `Authorization: Bearer <token>`

### "Permission Denied"
- El usuario no tiene permisos
- Verifica rol en base de datos
- Consulta `/security/menu/` para permisos disponibles

### "404 Not Found"
- URL incorrecta
- Recurso no existe (ID inválido)
- Verifica endpoints en README_API.md

---

## 📞 Soporte

**¿Dónde empiezo?**
1. Lee [README_API.md](./README_API.md)
2. Accede a Swagger UI: `http://127.0.0.1:8000/api/docs/`
3. Prueba login y algunos endpoints

**¿Cómo filtro actividades?**
- Ver [FILTRADO_ACTIVIDADES.md](./apps/operaciones/FILTRADO_ACTIVIDADES.md)
- Parámetro `?estado=en_progreso&area=Soporte`

**¿Cómo creo una actividad?**
- Ver [API_REST_REFERENCE.md](./apps/operaciones/API_REST_REFERENCE.md)
- POST `/operaciones/actividades/` con datos requeridos

**¿Cómo obtengo el token?**
- POST `/auth/login/` con username/password
- Usar token en header: `Authorization: Bearer <token>`

---

## ✅ Documentación Completa

- ✅ README_API.md - Guía general
- ✅ SWAGGER en `/api/docs/` - Interactivo
- ✅ Swagger Docs en `/apps/operaciones/` - Detallado
- ✅ Ejemplos en `example.http` - REST Client
- ✅ Filtros en FILTRADO_ACTIVIDADES.md
- ✅ Referencia en API_REST_REFERENCE.md
- ✅ Health checks documentado
- ✅ Auth endpoints documentados
- ✅ Employee CRUD documentado
- ✅ Activity CRUD documentado

---

**Última actualización:** 4 de marzo de 2026  
**API Version:** 1.0.0

