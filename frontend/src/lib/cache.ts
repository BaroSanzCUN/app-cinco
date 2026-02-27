// src/lib/cache.ts
/**
 * Sistema de caché simple en memoria para mejorar el rendimiento
 * Las búsquedas y datos frecuentes se cachean automáticamente
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  expiresAt: number;
}

class MemoryCache {
  private cache: Map<string, CacheEntry<any>> = new Map();
  private defaultTTL: number = 5 * 60 * 1000; // 5 minutos por defecto

  /**
   * Guardar datos en caché
   * @param key - Clave única del caché
   * @param data - Datos a cachear
   * @param ttl - Tiempo de vida en milisegundos (opcional)
   */
  set<T>(key: string, data: T, ttl?: number): void {
    const now = Date.now();
    const expiresAt = now + (ttl || this.defaultTTL);

    this.cache.set(key, {
      data,
      timestamp: now,
      expiresAt,
    });
  }

  /**
   * Obtener datos del caché
   * @param key - Clave del caché
   * @returns Los datos o null si no existen o expiraron
   */
  get<T>(key: string): T | null {
    const entry = this.cache.get(key);

    if (!entry) {
      return null;
    }

    const now = Date.now();

    // Si expiró, eliminarlo y retornar null
    if (now > entry.expiresAt) {
      this.cache.delete(key);
      return null;
    }

    return entry.data as T;
  }

  /**
   * Verificar si una clave existe en caché y no ha expirado
   */
  has(key: string): boolean {
    return this.get(key) !== null;
  }

  /**
   * Eliminar una entrada del caché
   */
  delete(key: string): void {
    this.cache.delete(key);
  }

  /**
   * Limpiar todo el caché
   */
  clear(): void {
    this.cache.clear();
  }

  /**
   * Limpiar entradas expiradas
   */
  cleanExpired(): void {
    const now = Date.now();
    const keysToDelete: string[] = [];

    this.cache.forEach((entry, key) => {
      if (now > entry.expiresAt) {
        keysToDelete.push(key);
      }
    });

    keysToDelete.forEach((key) => this.cache.delete(key));
  }

  /**
   * Obtener estadísticas del caché
   */
  getStats(): {
    size: number;
    keys: string[];
  } {
    return {
      size: this.cache.size,
      keys: Array.from(this.cache.keys()),
    };
  }

  /**
   * Wrapper para funciones asíncronas con caché automático
   * @param key - Clave del caché
   * @param fetcher - Función que obtiene los datos
   * @param ttl - Tiempo de vida opcional
   */
  async getOrFetch<T>(
    key: string,
    fetcher: () => Promise<T>,
    ttl?: number
  ): Promise<T> {
    // Intentar obtener del caché primero
    const cached = this.get<T>(key);
    if (cached !== null) {
      return cached;
    }

    // Si no está en caché, obtener los datos
    const data = await fetcher();

    // Guardar en caché
    this.set(key, data, ttl);

    return data;
  }
}

// Instancia singleton del caché
export const cache = new MemoryCache();

// Limpiar entradas expiradas cada 5 minutos
if (typeof window !== "undefined") {
  setInterval(() => {
    cache.cleanExpired();
  }, 5 * 60 * 1000);
}

export default cache;
