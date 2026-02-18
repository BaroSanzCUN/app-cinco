// src/store/menu.store.ts
import { create } from "zustand";
import { getActividades } from "@/services/actividades.service";
import { ActividadSchema } from "@/schemas/actividades.schema";

export const useActividadStore = create<any>((set) => ({
  actividades: ActividadSchema.array().parse([]),

  loadActividades: async () => {
    const actividades = await getActividades();
    set({ actividades });
  },

  setNuevaActividad: (actividad: any) => {
    set((state: any) => ({
      actividades: [...state.actividades, actividad],
    }));
  }

}));
