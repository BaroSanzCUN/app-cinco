// /modules/operaciones/actividad/types.ts

import { ActividadFormData } from "@/schemas/actividades.schema";

export interface Actividad extends ActividadFormData {
    id: number;
}
