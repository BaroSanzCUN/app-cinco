// src/services/empleado.service.ts
import api from "@/lib/api";

export const getEmpleados = async () => {
  const res = await api.get("/empleados/empleados/");
  return res.data;
};
