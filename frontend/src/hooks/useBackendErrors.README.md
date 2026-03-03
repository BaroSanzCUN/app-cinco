# useBackendErrors Hook

Hook reutilizable para manejar errores del backend en formularios de React Hook Form de manera consistente en toda la aplicación.

## 📋 Propósito

Estandarizar el manejo de errores de validación que provienen del backend (Django REST Framework) y aplicarlos automáticamente a los campos correspondientes del formulario.

## 🔧 Uso

### Importación

```typescript
import { useBackendErrors } from "@/hooks/useBackendErrors";
```

### Implementación en un formulario

```typescript
import { useForm } from "react-hook-form";
import { useBackendErrors } from "@/hooks/useBackendErrors";

const MyFormHook = ({ backendErrors }) => {
  const {
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(MySchema),
    defaultValues,
  });

  // Aplicar errores del backend automáticamente
  useBackendErrors(backendErrors, setError);

  return {
    control,
    errors,
    handleSubmit,
  };
};
```

## 📦 Formatos de error soportados

El hook maneja automáticamente múltiples formatos de error:

### 1. Array de strings (Django REST Framework estándar)

```json
{
  "ot": ["Ya existe un/a actividad con este/a ot."],
  "email": ["Ingrese una dirección de correo electrónico válida."]
}
```

### 2. String directo

```json
{
  "ot": "Este campo es requerido",
  "nombre": "El nombre es muy corto"
}
```

### 3. Objetos anidados

```json
{
  "detalle": {
    "tipo_trabajo": ["Este campo es requerido"],
    "descripcion": ["La descripción debe tener al menos 10 caracteres"]
  },
  "ubicacion": {
    "direccion": ["Este campo no puede estar en blanco"]
  }
}
```

El hook procesa automáticamente la estructura anidada y aplica los errores a los campos correspondientes usando notación de punto (ej: `detalle.tipo_trabajo`, `ubicacion.direccion`).

## 🎯 Integración con useFormSubmit

Este hook funciona perfectamente con `useFormSubmit`:

```typescript
const MyComponent = () => {
  const { submit, isLoading, error } = useFormSubmit();
  
  const {
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(MySchema),
  });

  // Pasar error.errors (donde están los errores de validación)
  useBackendErrors(error?.errors, setError);

  const onSubmit = async (data) => {
    await submit(data, {
      endpoint: "/api/endpoint/",
      method: "POST",
      onSuccess: (response) => {
        toast.success("Operación exitosa");
      },
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* campos del formulario */}
    </form>
  );
};
```

## ✨ Ventajas

1. **Consistencia**: Todos los formularios manejan errores de la misma manera
2. **Mantenibilidad**: Lógica centralizada en un solo lugar
3. **Flexibilidad**: Soporta múltiples formatos sin configuración adicional
4. **Type-safe**: Totalmente tipado con TypeScript
5. **Recursivo**: Maneja cualquier nivel de anidación

## 🔗 Relación con otros hooks

- **`useFormSubmit`**: Maneja el envío del formulario y clasifica los errores
- **`useBackendErrors`**: Aplica los errores del backend a los campos del formulario
- **React Hook Form**: Proporciona la función `setError` para aplicar los errores

## 📝 Notas importantes

1. Los errores se aplican automáticamente cuando `backendErrors` cambia
2. Los errores se marcan con `type: "server"` para distinguirlos de errores de validación del cliente
3. Para errores anidados, usar la estructura de React Hook Form (ej: `detalle.tipo_trabajo`)
4. Desde el modal/componente padre, pasar `error?.errors` en lugar de `error` completo

## 🚀 Ejemplo completo

Ver implementación real en:
- `src/modules/operaciones/actividad/ActividadForm.hooks.ts`
- `src/modules/operaciones/actividad/ModalActividad.tsx`
