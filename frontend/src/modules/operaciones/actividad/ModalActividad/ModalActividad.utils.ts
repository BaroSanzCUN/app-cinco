import {
  actividadCreateDefaultValues,
  actividadEditDefaultValues,
} from "../actividad.defaults";
import { Actividad } from "../types";

/**
 * Retorna los valores por defecto basados en el modo
 * @param mode - Si crear o editar
 * @param actividad - Datos de actividad para editar
 */
export const getDefaultValues = (
  mode: "create" | "edit",
  actividad?: Actividad,
) => {
  if (mode === "edit" && actividad) {
    return actividadEditDefaultValues(actividad);
  }
  return actividadCreateDefaultValues;
};

/**
 * Obtiene el título del modal según el modo
 * @param mode - Si crear o editar
 */
export const getModalTitle = (mode: "create" | "edit"): string => {
  return mode === "create" ? "Crear Nueva Actividad" : "Editar Actividad";
};

/**
 * Configuración del modal de actividad
 */
export const MODAL_ACTIVIDAD_CONFIG = {
  maxWidth: "max-w-150",
  padding: "p-5",
  scrollable: true,
} as const;
