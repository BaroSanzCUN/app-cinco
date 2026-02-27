# EmployeeSearchInput - Buscador de Empleados

Componente reutilizable para buscar y seleccionar empleados en formularios.

## 📋 Características

- ✅ Búsqueda en tiempo real con debounce
- ✅ Búsqueda por nombre, apellido, cédula, cargo o móvil
- ✅ Vista previa con foto del empleado
- ✅ **Caché automático** de búsquedas (5 minutos)
- ✅ **Precarga de imágenes** para mejor UX
- ✅ Totalmente tipado con TypeScript
- ✅ Soporte para modo oscuro
- ✅ Reutilizable en múltiples campos del mismo formulario
- ✅ Validación y mensajes de error
- ✅ Accesibilidad (ARIA labels)

## 🚀 Uso Básico

```tsx
import EmployeeSearchInput from "@/components/form/EmployeeSearchInput";
import { Empleado } from "@/types/empleado";
import { useState } from "react";

function MyForm() {
  const [empleado, setEmpleado] = useState<Empleado | null>(null);

  return (
    <EmployeeSearchInput
      label="Empleado"
      placeholder="Buscar empleado..."
      value={empleado}
      onChange={setEmpleado}
    />
  );
}
```

## 📖 Props

| Prop | Tipo | Default | Descripción |
|------|------|---------|-------------|
| `label` | `string` | - | Etiqueta del campo |
| `placeholder` | `string` | `"Buscar empleado..."` | Texto del placeholder |
| `value` | `Empleado \| null` | `null` | Empleado seleccionado |
| `onChange` | `(employee: Empleado \| null) => void` | - | Callback al seleccionar/limpiar |
| `error` | `boolean` | `false` | Muestra el campo con error |
| `hint` | `string` | - | Texto de ayuda debajo del campo |
| `disabled` | `boolean` | `false` | Deshabilita el campo |
| `required` | `boolean` | `false` | Marca el campo como requerido |
| `name` | `string` | - | Nombre del campo para formularios |

## 💡 Ejemplos de Uso

### Ejemplo 1: Múltiples selecciones en un formulario

```tsx
function AsignacionForm() {
  const [empleado, setEmpleado] = useState<Empleado | null>(null);
  const [supervisor, setSupervisor] = useState<Empleado | null>(null);
  const [jefe, setJefe] = useState<Empleado | null>(null);

  return (
    <form>
      <EmployeeSearchInput
        label="Empleado"
        value={empleado}
        onChange={setEmpleado}
        required
      />
      
      <EmployeeSearchInput
        label="Supervisor"
        value={supervisor}
        onChange={setSupervisor}
      />
      
      <EmployeeSearchInput
        label="Jefe de Área"
        value={jefe}
        onChange={setJefe}
      />
    </form>
  );
}
```

### Ejemplo 2: Con validación

```tsx
function FormWithValidation() {
  const [empleado, setEmpleado] = useState<Empleado | null>(null);
  const [error, setError] = useState(false);

  const handleSubmit = () => {
    if (!empleado) {
      setError(true);
      return;
    }
    // Enviar formulario
  };

  return (
    <EmployeeSearchInput
      label="Empleado"
      value={empleado}
      onChange={(emp) => {
        setEmpleado(emp);
        setError(false);
      }}
      error={error}
      hint={error ? "Por favor selecciona un empleado" : undefined}
      required
    />
  );
}
```

### Ejemplo 3: Con React Hook Form

```tsx
import { Controller, useForm } from "react-hook-form";

function FormWithRHF() {
  const { control, handleSubmit } = useForm();

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <Controller
        name="empleado"
        control={control}
        rules={{ required: "El empleado es requerido" }}
        render={({ field, fieldState }) => (
          <EmployeeSearchInput
            label="Empleado"
            value={field.value}
            onChange={field.onChange}
            error={!!fieldState.error}
            hint={fieldState.error?.message}
            required
          />
        )}
      />
    </form>
  );
}
```

## 🎨 Personalización

El componente usa las clases de Tailwind del proyecto y se adapta automáticamente al tema oscuro.

## 🔧 Backend Requirements

El componente requiere que el backend tenga un endpoint de búsqueda:

**Endpoint:** `GET /empleados/empleados/?search={query}`

**Response:**
```json
[
  {
    "id": 1,
    "cedula": "1007115509",
    "nombre": "FRAY SANTIAGO",
    "apellido": "OSPINA OSPINA",
    "cargo": "AUXILIAR",
    "link_foto": "https://..."
  }
]
```

## 📝 Tipo de Datos

```typescript
interface Empleado {
  id: number;
  cedula: string;
  nombre: string;
  apellido: string;
  area?: string;
  carpeta?: string;
  cargo?: string;
  movil?: string;
  supervisor?: string;
  estado: string;
  link_foto?: string;
}
```

## ⚡ Performance

- Búsqueda con debounce de 300ms
- Solo busca cuando hay 2+ caracteres
- **Caché automático:** Búsquedas repetidas se sirven desde memoria (0ms)
- **Precarga de imágenes:** Los avatares se precargan para UX instantánea
- Cierra dropdown automáticamente al hacer clic fuera
- Lazy loading de imágenes con Next.js Image
- **TTL del caché:** 5 minutos para búsquedas, 1 año para imágenes

### Limpiar Caché Manualmente

Si actualizas datos de empleados, puedes limpiar el caché:

```typescript
import { clearEmpleadosCache } from "@/services/empleado.service";

// Después de actualizar un empleado
clearEmpleadosCache();
```

Ver más detalles en [CACHE_SYSTEM.md](/CACHE_SYSTEM.md)

## 🐛 Troubleshooting

**Problema:** No aparecen resultados
- Verifica que el backend esté corriendo
- Verifica que el endpoint `/empleados/empleados/` esté disponible
- Revisa la consola del navegador para errores

**Problema:** Las imágenes no se cargan
- Verifica que `link_foto` tenga una URL válida
- Asegúrate de tener una imagen por defecto en `/images/user/owner.png`

## 📦 Archivos Relacionados

- `src/components/form/EmployeeSearchInput.tsx` - Componente principal
- `src/components/form/EmployeeSearchExample.tsx` - Ejemplo de uso
- `src/types/empleado.ts` - Tipos TypeScript
- `src/services/empleado.service.ts` - Servicio de API
- `backend/apps/empleados/views/empleado_view.py` - Vista del backend
