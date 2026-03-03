# Ejemplo de Uso: useBackendErrors

Este archivo contiene ejemplos prácticos de cómo implementar el manejo de errores estandarizado en nuevos módulos.

## 📋 Estructura recomendada para un nuevo módulo

```
src/modules/mi-modulo/
├── MiFormulario.tsx              # Componente del formulario
├── MiFormulario.hooks.ts         # Lógica del formulario
├── MiFormulario.types.ts         # Tipos TypeScript
├── useMiFormularioSubmit.ts      # Hook de envío
├── ModalMiFormulario.tsx         # Modal (si aplica)
└── mi-formulario.defaults.ts     # Valores por defecto
```

## 🔧 Paso 1: Definir el Schema (Zod)

\`\`\`typescript
// src/schemas/mi-modulo.schema.ts
import { z } from "zod";

export const MiFormularioSchema = z.object({
  nombre: z.string().min(1, "El nombre es requerido"),
  email: z.string().email("Email inválido"),
  
  // Campos anidados
  detalle: z.object({
    descripcion: z.string().min(1, "La descripción es requerida"),
    categoria: z.string().min(1, "La categoría es requerida"),
  }),
});

export type MiFormularioData = z.infer<typeof MiFormularioSchema>;
\`\`\`

## 🎣 Paso 2: Crear el Hook del Formulario

\`\`\`typescript
// src/modules/mi-modulo/MiFormulario.hooks.ts
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useBackendErrors } from "@/hooks/useBackendErrors";  // ⭐ IMPORTAR
import { MiFormularioSchema, MiFormularioData } from "@/schemas/mi-modulo.schema";

interface UseMiFormularioLogicParams {
  defaultValues: MiFormularioData;
  backendErrors?: Record<string, any> | null;
}

export const useMiFormularioLogic = ({
  defaultValues,
  backendErrors,
}: UseMiFormularioLogicParams) => {
  const {
    control,
    handleSubmit,
    setError,
    formState: { errors },
  } = useForm<MiFormularioData>({
    resolver: zodResolver(MiFormularioSchema),
    defaultValues,
  });

  // ⭐ APLICAR ERRORES DEL BACKEND
  useBackendErrors(backendErrors, setError);

  return {
    control,
    errors,
    handleSubmit,
  };
};
\`\`\`

## 📤 Paso 3: Crear el Hook de Submit

\`\`\`typescript
// src/modules/mi-modulo/useMiFormularioSubmit.ts
import { useFormSubmit } from "@/hooks/useFormSubmit";
import { MiFormularioData } from "@/schemas/mi-modulo.schema";
import { toast } from "sonner";

export const useMiFormularioSubmit = () => {
  const { submit, isLoading, error } = useFormSubmit<MiFormularioData>();

  const handleSubmit = async (
    data: MiFormularioData,
    mode: "create" | "edit",
    id?: number,
    onSuccessCallback?: () => void,
  ) => {
    const endpoint =
      mode === "create"
        ? "/api/mi-recurso/"
        : \`/api/mi-recurso/\${id}/\`;

    const method = mode === "create" ? "POST" : "PATCH";

    await submit(data, {
      endpoint,
      method,
      onSuccess: (response) => {
        toast.success(
          mode === "create"
            ? "Registro creado exitosamente"
            : "Registro actualizado exitosamente"
        );

        onSuccessCallback?.();
      },
      onError: (err) => {
        toast.error(err.message || "Error al procesar la solicitud");
      },
    });
  };

  return {
    handleSubmit,
    isLoading,
    error, // ⭐ Este objeto tiene { type, status, message, errors }
  };
};
\`\`\`

## 🎨 Paso 4: Crear el Componente del Formulario

\`\`\`typescript
// src/modules/mi-modulo/MiFormulario.tsx
import { Controller } from "react-hook-form";
import { useMiFormularioLogic } from "./MiFormulario.hooks";
import { MiFormularioData } from "@/schemas/mi-modulo.schema";
import Input from "@/components/form/input/InputField";
import Label from "@/components/form/Label";

interface MiFormularioProps {
  defaultValues: MiFormularioData;
  onSubmit: (data: MiFormularioData) => void;
  isLoading?: boolean;
  backendErrors?: Record<string, any> | null;  // ⭐ RECIBIR ERRORES
  mode?: "create" | "edit";
}

export const MiFormulario = ({
  defaultValues,
  onSubmit,
  isLoading,
  backendErrors,  // ⭐ RECIBIR ERRORES
  mode = "create",
}: MiFormularioProps) => {
  const { control, errors, handleSubmit } = useMiFormularioLogic({
    defaultValues,
    backendErrors,  // ⭐ PASAR ERRORES AL HOOK
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Campo simple */}
      <div>
        <Label htmlFor="nombre">Nombre *</Label>
        <Controller
          name="nombre"
          control={control}
          render={({ field }) => (
            <Input
              {...field}
              id="nombre"
              error={!!errors.nombre}
              hint={errors.nombre?.message}
            />
          )}
        />
      </div>

      {/* Campo anidado */}
      <div>
        <Label htmlFor="descripcion">Descripción *</Label>
        <Controller
          name="detalle.descripcion"
          control={control}
          render={({ field }) => (
            <Input
              {...field}
              id="descripcion"
              error={!!errors.detalle?.descripcion}
              hint={errors.detalle?.descripcion?.message}
            />
          )}
        />
      </div>

      <button type="submit" disabled={isLoading}>
        {mode === "create" ? "Crear" : "Actualizar"}
      </button>
    </form>
  );
};
\`\`\`

## 🪟 Paso 5: Crear el Modal

\`\`\`typescript
// src/modules/mi-modulo/ModalMiFormulario.tsx
import { useModal } from "@/hooks/useModal";
import { Modal } from "@/components/ui/modal";
import Button from "@/components/ui/button/Button";
import { MiFormulario } from "./MiFormulario";
import { useMiFormularioSubmit } from "./useMiFormularioSubmit";

interface ModalMiFormularioProps {
  mode: "create" | "edit";
  item?: any;
  textButton?: string;
}

export const ModalMiFormulario = ({
  mode,
  item,
  textButton,
}: ModalMiFormularioProps) => {
  const { isOpen, openModal, closeModal } = useModal();
  const { handleSubmit, isLoading, error } = useMiFormularioSubmit();

  const defaultValues = {
    nombre: item?.nombre || "",
    email: item?.email || "",
    detalle: {
      descripcion: item?.detalle?.descripcion || "",
      categoria: item?.detalle?.categoria || "",
    },
  };

  return (
    <>
      <Button onClick={openModal}>{textButton}</Button>

      <Modal isOpen={isOpen} onClose={closeModal}>
        <Modal.Header showCloseButton onClose={closeModal} />
        
        <Modal.Content>
          <MiFormulario
            defaultValues={defaultValues}
            isLoading={isLoading}
            onSubmit={(data) => handleSubmit(data, mode, item?.id, closeModal)}
            backendErrors={error?.errors}  // ⭐ PASAR error.errors (NO error completo)
            mode={mode}
          />
        </Modal.Content>
      </Modal>
    </>
  );
};
\`\`\`

## 🔄 Flujo Completo de Errores

\`\`\`
1. Usuario envía formulario
   ↓
2. useMiFormularioSubmit → useFormSubmit hace POST/PATCH
   ↓
3. Backend responde con 400 (error de validación)
   {
     "ot": ["Ya existe un registro con este valor"],
     "detalle": {
       "descripcion": ["Este campo es requerido"]
     }
   }
   ↓
4. useFormSubmit clasifica el error → error.errors contiene los errores
   ↓
5. Modal pasa error.errors como backendErrors al formulario
   ↓
6. useBackendErrors detecta cambio en backendErrors
   ↓
7. useBackendErrors aplica errores con setError
   - "ot" → errors.ot
   - "detalle.descripcion" → errors.detalle.descripcion
   ↓
8. Los errores se muestran bajo cada campo automáticamente
\`\`\`

## ✅ Checklist para Nuevos Módulos

- [ ] Crear schema con Zod
- [ ] Crear hook del formulario que use `useBackendErrors`
- [ ] Crear hook de submit que use `useFormSubmit`
- [ ] En el formulario, recibir `backendErrors` como prop
- [ ] En el hook del formulario, pasar `backendErrors` a `useBackendErrors`
- [ ] En el modal/padre, pasar `error?.errors` (NO `error` completo)
- [ ] Verificar que los campos muestren los errores correctamente

## 🎯 Puntos Clave

1. **Siempre pasar `error?.errors`**, no `error` completo
2. **Campos anidados** usan notación de punto: `detalle.descripcion`
3. **El hook maneja 3 formatos**: arrays, strings, objetos anidados
4. **Errores con tipo "server"** para distinguirlos de errores cliente
5. **Actualizaciones automáticas** cuando `backendErrors` cambia

## 📚 Referencias

- Hook: \`src/hooks/useBackendErrors.ts\`
- Documentación: \`src/hooks/useBackendErrors.README.md\`
- Ejemplo real: \`src/modules/operaciones/actividad/\`
