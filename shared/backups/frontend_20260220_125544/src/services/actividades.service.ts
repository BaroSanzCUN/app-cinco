// src/services/actividades.service.ts
import api from "@/lib/api";

export const getActividades = async () => {
  const res = await api.get("/operaciones/actividades/");
  return res.data;
};
