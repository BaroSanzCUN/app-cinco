import { z } from "zod";

export const loginSchema = z.object({
  username: z
    .string()
    .trim()
    .min(1, "El numero de documento es obligatorio")
    .regex(/^\d+$/, "El numero de documento debe ser solo numerico"),
  password: z
    .string()
    .trim()
    .min(1, "La contrasena es obligatoria")
    .regex(
      /^[A-Za-z0-9!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]+$/,
      "La contrasena contiene caracteres no validos"
    ),
});

export type LoginFormValues = z.infer<typeof loginSchema>;
