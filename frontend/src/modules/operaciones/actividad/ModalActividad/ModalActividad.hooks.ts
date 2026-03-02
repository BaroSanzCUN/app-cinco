import { useCallback } from "react";
import { useActividadSubmit } from "../useActividadSubmit";
import { Actividad } from "../types";

/**
 * Hook integrado para toda la lógica del modal de actividad
 * Combina: hook de submit, handlers de formulario
 *
 * @param mode - Si crear o editar
 * @param actividad - Datos de actividad (solo para modo edit)
 * @param onClose - Callback cuando se cierra el modal
 */
export const useModalActividadLogic = (
  mode: "create" | "edit",
  actividad: Actividad | undefined,
  onClose: () => void,
) => {
  const { handleSubmit: submitActividad, isLoading, error } =
    useActividadSubmit();

  // Handler seguro que cierra el modal después de successful submit
  const handleSubmit = useCallback(
    async (data: unknown) => {
      try {
        await submitActividad(
          data as any,
          mode,
          actividad?.id,
          onClose,
        );
      } catch (err) {
        // Error es manejado por el hook
        console.error("Error al guardar actividad:", err);
      }
    },
    [submitActividad, mode, actividad, onClose],
  );

  return {
    handleSubmit,
    isLoading,
    error,
  };
};
