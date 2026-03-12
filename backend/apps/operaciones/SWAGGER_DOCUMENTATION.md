# Documentación Swagger - Actividades

## Acceso a la Documentación Swagger

Una vez que el servidor Django esté en ejecución, puedes acceder a la documentación interactiva de Swagger en:

```
http://127.0.0.1:8000/api/docs/
```

También está disponible en formato ReDoc:
```
http://127.0.0.1:8000/api/redoc/
```

Esquema OpenAPI JSON:
```
http://127.0.0.1:8000/api/schema/
```

## Endpoints Documentados

### 1. **Listar Actividades** `GET /api/operaciones/actividades/`

**Descripción:** Obtiene un listado de actividades filtradas según el perfil del usuario actual.

**Autenticación:** Requerida (Bearer Token o API Key)

**Parámetros de Query:**

| Parámetro | Tipo | Requerido | Descripción | Ejemplos |
|-----------|------|-----------|-------------|----------|
| `ot` | string | No | Filtra por Orden de Trabajo (búsqueda parcial) | `OT-2024-001`, `OT-2024` |
| `estado` | string (enum) | No | Estado de la actividad | `pendiente`, `en_progreso`, `completada`, `cancelada`, `pausada`, `reprogramada` |
| `area` | string | No | Área del responsable (búsqueda parcial) | `Soporte Técnico`, `Instalación` |
| `carpeta` | string | No | Carpeta del responsable (búsqueda parcial) | `Carpeta A`, `Carpeta B` |
| `responsable_id` | integer | No | ID del empleado responsable | `123`, `456` |
| `buscar` | string | No | Búsqueda general en descripción, OT, nombre | `instalación`, `reparación` |
| `zona` | string | No | Zona de ubicación (búsqueda parcial) | `norte`, `sur`, `oriente` |
| `nodo` | string | No | Nodo de ubicación (búsqueda parcial) | `nodo-centro`, `nodo-norte` |
| `fecha_inicio_desde` | date | No | Fecha de inicio mínima (YYYY-MM-DD) | `2024-01-15` |
| `fecha_inicio_hasta` | date | No | Fecha de inicio máxima (YYYY-MM-DD) | `2024-02-15` |

**Ejemplos de Requests:**

```bash
# Listar mis actividades
curl -X GET "http://127.0.0.1:8000/api/operaciones/actividades/" \
  -H "Authorization: Bearer <token>"

# Actividades en progreso
curl -X GET "http://127.0.0.1:8000/api/operaciones/actividades/?estado=en_progreso" \
  -H "Authorization: Bearer <token>"

# Combinación: Área + Estado
curl -X GET "http://127.0.0.1:8000/api/operaciones/actividades/?area=Soporte&estado=pendiente" \
  -H "Authorization: Bearer <token>"

# Búsqueda general
curl -X GET "http://127.0.0.1:8000/api/operaciones/actividades/?buscar=instalación" \
  -H "Authorization: Bearer <token>"

# Múltiples filtros
curl -X GET "http://127.0.0.1:8000/api/operaciones/actividades/?estado=en_progreso&area=Soporte&zona=norte" \
  -H "Authorization: Bearer <token>"
```

**Respuesta (200 OK):**
```json
{
  "count": 5,
  "next": null,
  "previous": null,
  "results": [
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
  ]
}
```

---

### 2. **Crear Actividad** `POST /api/operaciones/actividades/`

**Descripción:** Crea una nueva actividad/solicitud.

**Autenticación:** Requerida

**Body (JSON):**
```json
{
  "ot": "OT-2024-001",
  "responsable_id": 123,
  "fecha_inicio": "2024-01-15",
  "fecha_fin_estimado": "2024-01-20",
  "fecha_fin_real": null,
  "detalle": {
    "tipo_trabajo": "Instalación",
    "descripcion": "Instalación de fibra óptica",
    "extra": {}
  },
  "ubicacion": {
    "direccion": "Calle Principal 123",
    "coordenada_x": "-75.5000",
    "coordenada_y": "10.4000",
    "zona": "norte",
    "nodo": "nodo-centro"
  }
}
```

**Respuesta (201 Created):**
```json
{
  "id": 1,
  "ot": "OT-2024-001",
  "estado": "pendiente",
  "responsable_id": 123,
  "fecha_inicio": "2024-01-15",
  "fecha_fin_estimado": "2024-01-20",
  "fecha_fin_real": null,
  "created_at": "2024-01-10T10:00:00Z",
  "created_by": 456,
  "updated_at": "2024-01-10T10:00:00Z",
  "updated_by": 456,
  "is_deleted": false,
  "deleted_at": null,
  "deleted_by": null,
  "detalle": {
    "id": 1,
    "tipo_trabajo": "Instalación",
    "descripcion": "Instalación de fibra óptica",
    "extra": {}
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

**Errores Comunes:**

- **400 Bad Request**: Datos inválidos
- **409 Conflict**: OT ya existe (debe ser única)
- **404 Not Found**: Responsable no existe

---

### 3. **Obtener Detalles** `GET /api/operaciones/actividades/{id}/`

**Descripción:** Obtiene la información completa de una actividad específica.

**Respuesta (200 OK):** Similar a la lista, pero un objeto individual.

---

### 4. **Actualizar Completamente** `PUT /api/operaciones/actividades/{id}/`

**Descripción:** Actualiza todos los campos de una actividad.

**Body:** Igual que POST (todos los campos requeridos)

**Respuesta (200 OK):** Actividad actualizada

---

### 5. **Actualizar Parcialmente** `PATCH /api/operaciones/actividades/{id}/`

**Descripción:** Actualiza solo los campos proporcionados.

**Body:** Solo los campos a actualizar
```json
{
  "estado": "completada",
  "fecha_fin_real": "2024-01-20"
}
```

**Respuesta (200 OK):** Actividad actualizada

---

### 6. **Eliminar Actividad** `DELETE /api/operaciones/actividades/{id}/`

**Descripción:** Elimina (soft delete) una actividad.

**Respuesta (204 No Content):** Sin contenido

---

## Comportamiento de Filtrado por Perfil

### Importante:
Por defecto, cuando solicitas actividades **sin especificar ningún filtro adicional**, solo verás:

- ✅ Actividades que TÚ creaste (`created_by = tu_usuario_id`)
- ✅ Actividades donde ERES el responsable (`responsable_snapshot.empleado_id = tu_empleado_id`)

### Ejemplos de lo que verás:

```bash
# Esto filtrará automáticamente por tu perfil
GET /api/operaciones/actividades/
# Solo tus actividades + donde eres responsable
```

```bash
# Esto filtrará por tu perfil Y además por estado
GET /api/operaciones/actividades/?estado=en_progreso
# Tus actividades en progreso (creadas por ti o donde eres responsable)
```

```bash
# Si quieres ver actividades de un responsable específico
GET /api/operaciones/actividades/?responsable_id=123
# Tu perfil + responsable 123
```

---

## Testing con Swagger UI

1. **Abre el navegador:**
   ```
   http://127.0.0.1:8000/api/docs/
   ```

2. **Autorízate:**
   - Click en el botón "Authorize" (arriba a la derecha)
   - Selecciona "bearerAuth"
   - Pega tu token Bearer

3. **Prueba los endpoints:**
   - Expande cada endpoint
   - Click en "Try it out"
   - Llena los parámetros
   - Click en "Execute"

---

## Notas Técnicas

- **Búsqueda insensible a mayúsculas:** Todos los filtros de texto usan `icontains`
- **Fechas:** Formato YYYY-MM-DD
- **Soft Delete:** Las actividades eliminadas se marcan con `is_deleted=true`
- **Snapshot:** Los datos del responsable se congelan en el momento de la creación (snapshot pattern)
