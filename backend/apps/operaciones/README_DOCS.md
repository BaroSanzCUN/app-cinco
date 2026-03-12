# 📚 Documentación del Módulo de Actividades

## Resumen de Implementación

Se ha completado la implementación de **filtrado avanzado de actividades** con documentación Swagger/OpenAPI.

---

## 📖 Archivos de Documentación

### 1. **SWAGGER_DOCUMENTATION.md** (Este archivo)
   - Documentación completa de Swagger/OpenAPI
   - Cómo acceder a la interfaz interactiva
   - Esquemas de request/response
   - Ejemplos de uso
   - **Ubicación:** `backend/apps/operaciones/SWAGGER_DOCUMENTATION.md`

### 2. **FILTRADO_ACTIVIDADES.md**
   - Guía de filtrado y búsqueda
   - Parámetros disponibles
   - Ejemplos de combinaciones
   - **Ubicación:** `backend/apps/operaciones/FILTRADO_ACTIVIDADES.md`

### 3. **API_REST_REFERENCE.md**
   - Referencia completa de la API REST
   - Métodos HTTP
   - Parámetros detallados
   - Casos de uso comunes
   - Herramientas para testing
   - **Ubicación:** `backend/apps/operaciones/API_REST_REFERENCE.md`

### 4. **example.http** (Actualizado)
   - Ejemplos de requests HTTP
   - Uso con extensiones VS Code (REST Client)
   - **Ubicación:** `backend/example.http`

---

## 🔗 Acceso a Documentación Interactiva

### Opción 1: Swagger UI (Recomendado)
```
http://127.0.0.1:8000/api/docs/
```
- Interfaz visual amigable
- Autorización integrada
- "Try it out" para probar endpoints

### Opción 2: ReDoc
```
http://127.0.0.1:8000/api/redoc/
```
- Documentación limpia y organizada
- Solo lectura

### Opción 3: OpenAPI JSON
```
http://127.0.0.1:8000/api/schema/
```
- Esquema JSON crudo
- Importable en herramientas como Postman

---

## 🎯 Características Documentadas

### ✅ GET - Listar Actividades
**Endpoint:** `GET /api/operaciones/actividades/`

**Documentación:**
- Descripción detallada
- 10+ parámetros de query documentados
- Ejemplos de uso
- Esquema de respuesta completo

**Parámetros:**
- `ot` - Orden de Trabajo
- `estado` - Estado (enum con opciones)
- `area` - Área del responsable
- `carpeta` - Carpeta del responsable
- `responsable_id` - ID del empleado
- `buscar` - Búsqueda general
- `zona` - Zona de ubicación
- `nodo` - Nodo de ubicación
- `fecha_inicio_desde` - Fecha mínima
- `fecha_inicio_hasta` - Fecha máxima

### ✅ POST - Crear Actividad
**Endpoint:** `POST /api/operaciones/actividades/`

**Documentación:**
- Campos requeridos y opcionales
- Validaciones
- Esquema de request/response
- Errores comunes

### ✅ GET - Obtener Detalles
**Endpoint:** `GET /api/operaciones/actividades/{id}/`

**Documentación:**
- Descripción clara
- Esquema de respuesta

### ✅ PUT - Actualizar Completamente
**Endpoint:** `PUT /api/operaciones/actividades/{id}/`

**Documentación:**
- Requiremientos de campos
- Esquema completo

### ✅ PATCH - Actualizar Parcialmente
**Endpoint:** `PATCH /api/operaciones/actividades/{id}/`

**Documentación:**
- Campos opcionales
- Ejemplos de actualización

### ✅ DELETE - Eliminar Actividad
**Endpoint:** `DELETE /api/operaciones/actividades/{id}/`

**Documentación:**
- Nota sobre soft delete
- Respuesta esperada

---

## 📋 Tipos de Datos Documentados

### Estados (Enum)
```
- pendiente
- en_progreso
- completada
- cancelada
- pausada
- reprogramada
```

### Esquema de Respuesta
```json
{
  "id": integer,
  "ot": string (unique),
  "estado": string (enum),
  "responsable_id": integer,
  "fecha_inicio": date,
  "fecha_fin_estimado": date,
  "fecha_fin_real": date (nullable),
  "created_at": datetime,
  "created_by": integer,
  "updated_at": datetime,
  "updated_by": integer,
  "is_deleted": boolean,
  "deleted_at": datetime (nullable),
  "deleted_by": integer (nullable),
  "detalle": object,
  "ubicacion": object,
  "responsable_snapshot": object
}
```

---

## 🔐 Autenticación

Todos los endpoints están documentados con requisitos de autenticación:

**Métodos soportados:**
- Bearer Token (JWT)
- API Key

**Ejemplo en Swagger UI:**
1. Click "Authorize" (arriba a la derecha)
2. Selecciona "bearerAuth"
3. Pega tu token
4. Click "Authorize"

---

## 🧪 Testing

### En Swagger UI
1. Navega a `http://127.0.0.1:8000/api/docs/`
2. Autorízate con tu token
3. Expande cualquier endpoint
4. Click "Try it out"
5. Llena los parámetros
6. Click "Execute"

### Con REST Client (VS Code)
Usa los ejemplos en [example.http](../example.http)

### Con cURL
```bash
curl -X GET "http://127.0.0.1:8000/api/operaciones/actividades/?estado=en_progreso" \
  -H "Authorization: Bearer <token>"
```

### Con Postman
1. Importa: `http://127.0.0.1:8000/api/schema/`
2. Configura autenticación (Bearer Token)
3. Prueba los endpoints

---

## 📊 Filtrado Automático por Perfil

**Importante:** El sistema filtra automáticamente por perfil del usuario.

```python
# Se muestran SOLO actividades donde:
if usuario_id:
    queryset = queryset.filter(
        Q(created_by=usuario_id) |              # Creadas por ti
        Q(responsable_snapshot__empleado_id=usuario_id)  # Donde eres responsable
    ).distinct()
```

**Esto significa:**
- ✅ Solo ves tus actividades y las que te asignaron
- ✅ Los filtros adicionales se aplican sobre tu perfil
- ✅ No necesitas parámetros especiales

---

## 🔧 Implementación Técnica

### Archivos Modificados:
1. **actividad_view.py** - Decoradores Swagger completos en todas las acciones
2. **actividad_service.py** - Métodos de filtrado reutilizables
3. **actividad_filter.py** - Clase con 10+ métodos de filtro

### Librerías Utilizadas:
- `drf-spectacular` - Documentación OpenAPI 3.0
- `django-rest-framework` - API REST
- `Django ORM` - Queries optimizadas con Q objects

---

## 📌 Próximos Pasos (Opcional)

- [ ] Agregar paginación en la documentación
- [ ] Documentar webhooks (si aplica)
- [ ] Agregar ejemplos de Python/JavaScript
- [ ] Testing automatizado con OpenAPI
- [ ] Versioning de API

---

## 📚 Referencias

- [OpenAPI 3.0 Spec](https://spec.openapis.org/oas/v3.0.3)
- [drf-spectacular Docs](https://drf-spectacular.readthedocs.io/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Swagger UI](https://swagger.io/tools/swagger-ui/)

---

## ✅ Checklist de Documentación

- ✅ GET /api/operaciones/actividades/ - Documentado con 10+ parámetros
- ✅ POST /api/operaciones/actividades/ - Documentado con esquema request/response
- ✅ GET /api/operaciones/actividades/{id}/ - Documentado
- ✅ PUT /api/operaciones/actividades/{id}/ - Documentado
- ✅ PATCH /api/operaciones/actividades/{id}/ - Documentado
- ✅ DELETE /api/operaciones/actividades/{id}/ - Documentado
- ✅ Parámetros de query con tipo, descripción y ejemplos
- ✅ Enum de estados con valores válidos
- ✅ Esquema de respuesta completo
- ✅ Comportamiento de filtrado por perfil explicado
- ✅ Ejemplos de uso (cURL, HTTP, Python, JavaScript)
- ✅ Códigos de error documentados
- ✅ Notas técnicas y comportamiento especial

---

## 📞 Soporte

Si encuentras problemas:
1. Verifica autenticación en Swagger UI
2. Revisa los códigos de error HTTP
3. Consulta SWAGGER_DOCUMENTATION.md para ejemplos
4. Verifica que Django esté ejecutándose: `py manage.py runserver`

