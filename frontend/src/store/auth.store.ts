// src/store/auth.store.ts
import { create } from "zustand";
import { clearUser, saveUser } from "@/utils/storage";
import axios from "axios";

const getDefaultApiUrl = (): string => {
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000/`;
  }
  return "http://localhost:8000/";
};

const baseURL = process.env.NEXT_PUBLIC_API_URL || getDefaultApiUrl();

interface AuthState {
  user: any;
  isAuthenticated: boolean;
  login: (data: any) => void;
  logout: () => Promise<void>;
  setAuthenticated: (isAuthenticated: boolean, user?: any) => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: false,

  login: (data) => {
    // Los tokens se reciben automáticamente en cookies httpOnly
    // Solo guardamos los datos del usuario
    if (data.user) {
      saveUser(data.user);
      set({ user: data.user, isAuthenticated: true });
    }
  },

  logout: async () => {
    try {
      // Llamar al endpoint de logout para limpiar cookies y revocar token
      await axios.post(
        `${baseURL}auth/logout/`,
        {},
        {
          withCredentials: true, // Enviar cookies
        },
      );
    } catch (error) {
      console.error("Error al cerrar sesión:", error);
    } finally {
      // Limpiar datos locales siempre, incluso si la llamada falla
      clearUser();
      set({ user: null, isAuthenticated: false });
    }
  },

  setAuthenticated: (isAuthenticated, user = null) => {
    set({ isAuthenticated, user });
  },
}));
