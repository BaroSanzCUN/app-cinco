// src/services/menu.service.ts
import api from "@/lib/api";

export const getMenu = async () => {
  const res = await api.get("/security/menu/");
  return res.data;
};
