# Guía de Filtrado de Actividades

## Descripción General

El módulo de actividades ahora soporta filtrado avanzado basado en:
- **Perfil del usuario**: Muestra solicitudes creadas o donde es responsable
- **OT (Orden de Trabajo)**
- **Estado** de la actividad
- **Área** del responsable
- **Carpeta** del responsable
- **Responsable** específico
- **Zona y Nodo** de ubicación
- **Búsqueda general** en descripción, tipo de trabajo, OT y nombre
- **Rango de fechas**

## Endpoints y Ejemplos

### 1. Listar actividades según perfil del usuario (SIN filtros adicionales)
Por defecto, si el usuario está autenticado, solo verá:
- Solicitudes que creó (`created_by`)
- Solicitudes donde es responsable

```bash
GET /api/operaciones/actividades/
Authorization: Bearer <token>
```

### 2. Filtrar por OT
```bash
GET /api/operaciones/actividades/?ot=OT-2024-001
Authorization: Bearer <token>
```

### 3. Filtrar por Estado
Estados disponibles: `pendiente`, `en_progreso`, `completada`, `cancelada`, `pausada`, `reprogramada`

```bash
GET /api/operaciones/actividades/?estado=en_progreso
Authorization: Bearer <token>
```

### 4. Filtrar por Área
```bash
GET /api/operaciones/actividades/?area=Soporte%20Técnico
Authorization: Bearer <token>
```

### 5. Filtrar por Carpeta
```bash
GET /api/operaciones/actividades/?carpeta=Carpeta%20A
Authorization: Bearer <token>
```

### 6. Filtrar por Responsable específico (empleado_id)
```bash
GET /api/operaciones/actividades/?responsable_id=123
Authorization: Bearer <token>
```

### 7. Búsqueda general
Busca en descripción, tipo de trabajo, OT y nombre del responsable:

```bash
GET /api/operaciones/actividades/?buscar=instalación
Authorization: Bearer <token>
```

### 8. Filtrar por Zona
```bash
GET /api/operaciones/actividades/?zona=norte
Authorization: Bearer <token>
```

### 9. Filtrar por Nodo
```bash
GET /api/operaciones/actividades/?nodo=nodo-centro
Authorization: Bearer <token>
```

### 10. Filtrar por Rango de Fechas
```bash
GET /api/operaciones/actividades/?fecha_inicio_desde=2024-01-15&fecha_inicio_hasta=2024-02-15
Authorization: Bearer <token>
```

### 11. Combinaciones de Filtros
Puedes combinar múltiples filtros:

```bash
GET /api/operaciones/actividades/?estado=en_progreso&area=Soporte&buscar=instalación
Authorization: Bearer <token>
```

```bash
GET /api/operaciones/actividades/?ot=OT-2024&estado=pendiente&responsable_id=123&zona=norte
Authorization: Bearer <token>
```

## Estructura de Respuesta

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
        "descripcion": "Instalación de fibra óptica en sector norte",
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

## Notas Importantes

1. **Búsqueda sin Distinción de Mayúsculas/Minúsculas**: Todos los filtros de texto usan `icontains`, por lo que son insensibles a mayúsculas/minúsculas.

2. **Filtros de Perfil**: Cuando se autentica, automáticamente solo verá actividades donde:
   - Es el creador (`created_by = usuario_id`)
   - O es el responsable (`responsable_snapshot.empleado_id = usuario_id`)

3. **Combinación de Filtros**: Los filtros se combinan con lógica AND. Si especificas múltiples filtros, todos deben cumplirse.

4. **Búsqueda General**: El filtro `buscar` busca en 4 campos:
   - `detalle.descripcion`
   - `detalle.tipo_trabajo`
   - `ot`
   - `responsable_snapshot.nombre`

## Validación de Estado

Estados válidos:
- `pendiente` - Actividad no iniciada
- `en_progreso` - Actividad en ejecución
- `completada` - Actividad finalizada
- `cancelada` - Actividad cancelada
- `pausada` - Actividad en pausa
- `reprogramada` - Actividad reprogramada
