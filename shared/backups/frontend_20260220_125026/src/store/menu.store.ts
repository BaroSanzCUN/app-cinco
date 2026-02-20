// src/store/menu.store.ts
import { create } from "zustand";
import { getMenu } from "@/services/menu.service";

export const useMenuStore = create<any>((set) => ({
  menu: [],
  loadMenu: async () => {
    const menu = await getMenu();
    set({ menu });
  },
}));
