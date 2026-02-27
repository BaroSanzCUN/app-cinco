// src/services/empleado.service.ts
import api from "@/lib/api";
import { Empleado } from "@/types/empleado";
import { cache } from "@/lib/cache";

const CACHE_TTL = {
  ALL_EMPLOYEES: 10 * 60 * 1000, // 10 minutos para lista completa
  SEARCH: 5 * 60 * 1000, // 5 minutos para búsquedas
  SINGLE: 15 * 60 * 1000, // 15 minutos para empleado individual
};

export const getEmpleados = async (): Promise<Empleado[]> => {
  return cache.getOrFetch(
    "empleados:all",
    async () => {
      const res = await api.get("/empleados/empleados/");
      return res.data;
    },
    CACHE_TTL.ALL_EMPLOYEES
  );
};

export const searchEmpleados = async (query: string): Promise<Empleado[]> => {
  const cacheKey = `empleados:search:${query.toLowerCase().trim()}`;
  
  return cache.getOrFetch(
    cacheKey,
    async () => {
      const res = await api.get("/empleados/empleados/", {
        params: { search: query }
      });
      return res.data;
    },
    CACHE_TTL.SEARCH
  );
};

export const getEmpleadoByCedula = async (cedula: string): Promise<Empleado> => {
  const cacheKey = `empleados:cedula:${cedula}`;
  
  return cache.getOrFetch(
    cacheKey,
    async () => {
      const res = await api.get(`/empleados/empleados/${cedula}/`);
      return res.data;
    },
    CACHE_TTL.SINGLE
  );
};

export const getEmpleadoById = async (id: number): Promise<Empleado> => {
  const cacheKey = `empleados:id:${id}`;

  return cache.getOrFetch(
    cacheKey,
    async () => {
      const res = await api.get(`/empleados/empleados/${id}/`);
      return res.data;
    },
    CACHE_TTL.SINGLE
  );
};

/**
 * Limpiar el caché de empleados
 * Útil cuando se actualiza, crea o elimina un empleado
 */
export const clearEmpleadosCache = (): void => {
  // Obtener todas las claves del caché
  const stats = cache.getStats();
  
  // Eliminar todas las claves que comiencen con "empleados:"
  stats.keys.forEach((key) => {
    if (key.startsWith("empleados:")) {
      cache.delete(key);
    }
  });
};
