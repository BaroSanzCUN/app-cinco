import { z } from "zod";

// {
//   "ot": "string",
//   "responsable_id": 9223372036854776000,
//   "fecha_inicio": "2026-02-12T15:04:13.119Z",
//   "fecha_fin_estimado": "2026-02-12T15:04:13.119Z",
//   "fecha_fin_real": "",
//   "detalle": {
//     "tipo_trabajo": "string",
//     "descripcion": "string",
//     "extra": "string"
//   },
//   "ubicacion": {
//     "direccion": "string",
//     "coordenada_x": "string",
//     "coordenada_y": "string",
//     "zona": "string",
//     "nodo": "string"
//   }
// }

export const ActividadSchema = z.object({
  id: z.number().optional(),
  ot: z.string().min(1, "La OT es requerida"),
  responsable_id: z.number().int().positive("El ID del responsable debe ser un número entero positivo"),
  
  fecha_actividad: z
    .string()
    .min(1, "La fecha es requerida")
    .refine((v) => !isNaN(Date.parse(v)), {
      message: "Fecha inválida",
    }),

  descripcion: z.string().min(1, "La descripción es requerida"),

  tipo_actividad: z.string().min(1, "El tipo de actividad es requerido"),

  fecha_inicio: z
    .string()
    .min(1, "La fecha de inicio es requerida")
    .refine((v) => !isNaN(Date.parse(v)), {
      message: "Fecha de inicio inválida",
    }),
});

export type ActividadFormData = z.infer<typeof ActividadSchema>;
