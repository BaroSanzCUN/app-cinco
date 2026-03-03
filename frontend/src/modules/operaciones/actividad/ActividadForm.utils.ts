import { ActividadFormData } from "@/schemas/actividades.schema";
import { Empleado } from "@/types/empleado";

export const getDateFromPicker = (dates: Date[] | Date): Date | undefined => {
  return Array.isArray(dates) ? dates[0] : dates;
};

export const toIsoDate = (date?: Date): string => {
  return date ? date.toISOString().split("T")[0] : "";
};

export const toDateOrUndefined = (value?: string | null): Date | undefined => {
  return value ? new Date(value) : undefined;
};

export const buildResponsableSnapshot = (empleado: Empleado) => ({
  nombre: `${empleado.nombre} ${empleado.apellido}`,
  area: empleado.area || "",
  carpeta: empleado.carpeta || "",
  cargo: empleado.cargo || "",
  movil: empleado.movil || "",
});

export const getSnapshotEmpleado = (
  defaultValues: ActividadFormData,
): Empleado | null => {
  if (!defaultValues.responsable_snapshot || !defaultValues.responsable_id) {
    return null;
  }

  return {
    id: defaultValues.responsable_id,
    cedula: "",
    nombre: defaultValues.responsable_snapshot.nombre.split(" ")[0] || "",
    apellido:
      defaultValues.responsable_snapshot.nombre.split(" ").slice(1).join(" ") ||
      "",
    area: defaultValues.responsable_snapshot.area,
    carpeta: defaultValues.responsable_snapshot.carpeta,
    cargo: defaultValues.responsable_snapshot.cargo,
    movil: defaultValues.responsable_snapshot.movil,
    estado: "ACTIVO",
    link_foto: undefined,
  };
};
