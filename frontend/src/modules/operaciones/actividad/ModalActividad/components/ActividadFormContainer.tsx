import ActividadForm from "../../ActividadForm";
import { ActividadFormData } from "@/schemas/actividades.schema";

interface ActividadFormContainerProps {
  mode: "create" | "edit";
  defaultValues: ActividadFormData;
  onSubmit: (data: ActividadFormData) => void;
  isLoading: boolean;
  backendErrors?: Record<string, any> | null;
}

/**
 * Contenedor que renderiza el formulario de actividad
 * Aísla la lógica del formulario del modal
 */
export const ActividadFormContainer = ({
  mode,
  defaultValues,
  onSubmit,
  isLoading,
  backendErrors,
}: ActividadFormContainerProps) => {
  return (
    <ActividadForm
      defaultValues={defaultValues}
      isLoading={isLoading}
      onSubmit={onSubmit}
      backendErrors={backendErrors}
      mode={mode}
    />
  );
};
