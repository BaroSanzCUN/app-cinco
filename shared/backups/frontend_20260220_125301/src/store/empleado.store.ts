// src/store/menu.store.ts
import { create } from "zustand";
import { getEmpleados } from "@/services/empleado.service";

export const useEmpleadoStore = create<any>((set) => ({
  empleados: [],
  loadEmpleados: async () => {
    const empleados = await getEmpleados();
    set({ empleados });
  },
}));
