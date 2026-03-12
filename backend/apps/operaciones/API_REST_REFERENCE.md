# API REST - Actividades/Solicitudes

## 📋 Resumen General

La API permite gestionar **solicitudes de actividades** con filtrado avanzado por perfil del usuario.

### Características Principales:

✅ **Filtrado Automático por Perfil:** Solo ves tus solicitudes (creadas o asignadas)  
✅ **10+ Parámetros de Filtro:** OT, estado, área, carpeta, zona, nodo, fechas  
✅ **Búsqueda General:** En descripción, tipo de trabajo, OT, nombre  
✅ **Soft Delete:** Las actividades no se elimian realmente  
✅ **Snapshot del Responsable:** Los datos se congelan en el momento de creación  

---

## 🔗 Rutas de la API

### Base URL
```
http://127.0.0.1:8000/api/operaciones/actividades/
```

### Documentación Interactiva
```
http://127.0.0.1:8000/api/docs/        # Swagger UI
http://127.0.0.1:8000/api/redoc/       # ReDoc
http://127.0.0.1:8000/api/schema/      # OpenAPI 3.0 Schema JSON
```

---

## 📡 Métodos HTTP Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `GET` | `/api/operaciones/actividades/` | Listar actividades |
| `POST` | `/api/operaciones/actividades/` | Crear actividad |
| `GET` | `/api/operaciones/actividades/{id}/` | Obtener detalles |
| `PUT` | `/api/operaciones/actividades/{id}/` | Actualizar completamente |
| `PATCH` | `/api/operaciones/actividades/{id}/` | Actualizar parcialmente |
| `DELETE` | `/api/operaciones/actividades/{id}/` | Eliminar |

---

## 🔒 Autenticación

Todos los endpoints requieren autenticación. Usa uno de estos métodos:

### 1. Bearer Token
```bash
Authorization: Bearer <your_access_token>
```

### 2. API Key (si aplica)
```bash
Authorization: ApiKey <your_api_key>
```

---

## 📥 Request / Response Schemas

### Actividad - Respuesta (GET/PUT/PATCH/POST)

```json
{
  "id": 1,
  "ot": "OT-2024-001",
  "estado": "en_progreso",
  "responsable_id": 123,
  "fecha_inicio": "2024-01-15",
  "fecha_fin_estimado": "2024-01-20",
  "fecha_fin_real": null,
  "created_at": "2024-01-10T10:00:00Z",
  "created_by": 456,
  "updated_at": "2024-01-15T14:30:00Z",
  "updated_by": 456,
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "detalle": {
    "id": 1,
    "tipo_trabajo": "Instalación",
    "descripcion": "Instalación de fibra óptica",
    "extra": null
  },
  "ubicacion": {
    "id": 1,
    "direccion": "Calle Principal 123",
    "coordenada_x": "-75.5000",
    "coordenada_y": "10.4000",
    "zona": "norte",
    "nodo": "nodo-centro"
  },
  "responsable_snapshot": {
    "nombre": "Juan Pérez",
    "area": "Soporte Técnico",
    "carpeta": "Carpeta A",
    "cargo": "Técnico Senior",
    "movil": "3001234567"
  }
}
```

### Parámetros de Query (GET /api/operaciones/actividades/)

```
?ot=OT-2024&estado=pendiente&area=Soporte&responsable_id=123&buscar=instalación&zona=norte&nodo=nodo-centro&fecha_inicio_desde=2024-01-15&fecha_inicio_hasta=2024-02-15
```

---

## 🎯 Casos de Uso Comunes

### Caso 1: Ver mis actividades
```bash
GET /api/operaciones/actividades/
Authorization: Bearer <token>
```
Retorna solo tus solicitudes.

---

### Caso 2: Ver actividades en progreso en mi área
```bash
GET /api/operaciones/actividades/?estado=en_progreso&area=Soporte
Authorization: Bearer <token>
```

---

### Caso 3: Buscar por OT
```bash
GET /api/operaciones/actividades/?ot=OT-2024-001
Authorization: Bearer <token>
```

---

### Caso 4: Filtrar por responsable específico y zona
```bash
GET /api/operaciones/actividades/?responsable_id=123&zona=norte
Authorization: Bearer <token>
```

---

### Caso 5: Búsqueda general
```bash
GET /api/operaciones/actividades/?buscar=instalación
Authorization: Bearer <token>
```
Busca en:
- descripción
- tipo_trabajo
- ot
- nombre del responsable

---

### Caso 6: Actividades en rango de fechas
```bash
GET /api/operaciones/actividades/?fecha_inicio_desde=2024-01-15&fecha_inicio_hasta=2024-02-15
Authorization: Bearer <token>
```

---

### Caso 7: Crear una actividad
```bash
POST /api/operaciones/actividades/
Authorization: Bearer <token>
Content-Type: application/json

{
  "ot": "OT-2024-002",
  "responsable_id": 123,
  "fecha_inicio": "2024-01-20",
  "fecha_fin_estimado": "2024-01-25",
  "detalle": {
    "tipo_trabajo": "Reparación",
    "descripcion": "Reparación de línea dañada",
    "extra": {}
  },
  "ubicacion": {
    "direccion": "Calle Secundaria 456",
    "coordenada_x": "-75.4500",
    "coordenada_y": "10.5000",
    "zona": "sur",
    "nodo": "nodo-sur"
  }
}
```

---

### Caso 8: Actualizar estado
```bash
PATCH /api/operaciones/actividades/1/
Authorization: Bearer <token>
Content-Type: application/json

{
  "estado": "completada",
  "fecha_fin_real": "2024-01-20"
}
```

---

## ⚙️ Parámetros de Filtrado Detallados

### `ot` (Orden de Trabajo)
- **Tipo:** String
- **Búsqueda:** Parcial/insensible a mayúsculas
- **Ejemplo:** `?ot=OT-2024-001` o `?ot=OT-2024`

### `estado` (Estado de Actividad)
- **Tipo:** String (enum)
- **Valores válidos:**
  - `pendiente` - No iniciada
  - `en_progreso` - En ejecución
  - `completada` - Finalizada
  - `cancelada` - Cancelada
  - `pausada` - En pausa
  - `reprogramada` - Reprogramada
- **Ejemplo:** `?estado=en_progreso`

### `area` (Área del Responsable)
- **Tipo:** String
- **Búsqueda:** Parcial/insensible a mayúsculas
- **Ejemplo:** `?area=Soporte%20Técnico` o `?area=Soporte`

### `carpeta` (Carpeta del Responsable)
- **Tipo:** String
- **Búsqueda:** Parcial/insensible a mayúsculas
- **Ejemplo:** `?carpeta=Carpeta%20A`

### `responsable_id` (ID del Empleado Responsable)
- **Tipo:** Integer
- **Ejemplo:** `?responsable_id=123`

### `buscar` (Búsqueda General)
- **Tipo:** String
- **Campos que busca:**
  - detalle.descripcion
  - detalle.tipo_trabajo
  - ot
  - responsable_snapshot.nombre
- **Búsqueda:** Parcial/insensible a mayúsculas
- **Ejemplo:** `?buscar=instalación`

### `zona` (Zona de Ubicación)
- **Tipo:** String
- **Búsqueda:** Parcial/insensible a mayúsculas
- **Ejemplo:** `?zona=norte` o `?zona=sur`

### `nodo` (Nodo de Ubicación)
- **Tipo:** String
- **Búsqueda:** Parcial/insensible a mayúsculas
- **Ejemplo:** `?nodo=nodo-centro`

### `fecha_inicio_desde` (Fecha Inicio Mínima)
- **Tipo:** Date (YYYY-MM-DD)
- **Ejemplo:** `?fecha_inicio_desde=2024-01-15`

### `fecha_inicio_hasta` (Fecha Inicio Máxima)
- **Tipo:** Date (YYYY-MM-DD)
- **Ejemplo:** `?fecha_inicio_hasta=2024-02-15`

---

## 🔄 Filtrado por Perfil (Automático)

Por defecto, el sistema filtra automáticamente según tu usuario:

**Se muestran:**
- ✅ Actividades que TÚ creaste (`created_by = tu_id`)
- ✅ Actividades donde ERES responsable (`responsable_snapshot.empleado_id = tu_empleado_id`)

**Comportamiento:**
```javascript
if (usuario_id) {
  queryset = queryset.filter(
    (created_by == usuario_id) OR (empleado_id == usuario_id)
  )
}
```

---

## 📊 Códigos de Respuesta HTTP

| Código | Descripción |
|--------|-------------|
| `200` | OK - Solicitud exitosa |
| `201` | Created - Recurso creado |
| `204` | No Content - Eliminado exitosamente |
| `400` | Bad Request - Datos inválidos |
| `401` | Unauthorized - No autenticado |
| `403` | Forbidden - Sin permisos |
| `404` | Not Found - Recurso no existe |
| `409` | Conflict - OT duplicada |
| `500` | Internal Server Error - Error del servidor |

---

## 🧪 Herramientas para Testing

### Postman / Insomnia
1. Importa la URL: `http://127.0.0.1:8000/api/schema/`
2. Define tu token Bearer
3. Prueba los endpoints

### Swagger UI
1. Accede a: `http://127.0.0.1:8000/api/docs/`
2. Click "Authorize"
3. Pega tu token
4. Click "Try it out" en cualquier endpoint

### cURL
```bash
curl -X GET "http://127.0.0.1:8000/api/operaciones/actividades/" \
  -H "Authorization: Bearer <token>"
```

### Python Requests
```python
import requests

headers = {
    "Authorization": "Bearer <token>"
}
params = {
    "estado": "en_progreso",
    "area": "Soporte"
}

response = requests.get(
    "http://127.0.0.1:8000/api/operaciones/actividades/",
    headers=headers,
    params=params
)
print(response.json())
```

### JavaScript Fetch
```javascript
const token = '<your_token>';
const params = new URLSearchParams({
    estado: 'en_progreso',
    area: 'Soporte'
});

fetch(`http://127.0.0.1:8000/api/operaciones/actividades/?${params}`, {
    headers: {
        'Authorization': `Bearer ${token}`
    }
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## 📝 Notas Importantes

1. **Búsqueda Sensible al Contexto:** Todos los filtros de texto son insensibles a mayúsculas
2. **Soft Delete:** Al eliminar una actividad, se marca `is_deleted=true` pero no se borra realmente
3. **Snapshot Inmutable:** Los datos del responsable (nombre, área, etc.) se congelan en la creación y no se actualizan
4. **Relaciones:** Las actividades siempre cargan detalles, ubicación y snapshot del responsable
5. **Ordenamiento:** Por defecto ordena por `-id` (más recientes primero)
