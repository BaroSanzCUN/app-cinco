// app/lib/api.ts
import axios from "axios";
import { clearUser } from "@/utils/storage";
import { classifyError, ApiErrorType } from "@/lib/errorHandler";

const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/";

const api = axios.create({
  baseURL,
  timeout: 10000, // 10 segundos
  withCredentials: true, // Envía cookies automáticamente
  headers: {
    "Content-Type": "application/json",
  },
});

const refreshApi = axios.create({
  baseURL,
  timeout: 10000,
  withCredentials: true, // Envía cookies automáticamente
  headers: {
    "Content-Type": "application/json",
  },
});

const csrfApi = axios.create({
  baseURL,
  timeout: 10000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

let isRefreshing = false;
let failedQueue: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: any) => void;
  config: any;
}> = [];

const processQueue = (error: any) => {
  failedQueue.forEach(({ resolve, reject, config }) => {
    if (error) {
      reject(error);
      return;
    }

    // Ya no necesitamos agregar token manualmente, se envía en cookies
    resolve(api(config));
  });

  failedQueue = [];
};

const getCookieValue = (name: string): string | null => {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(new RegExp(`(^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : null;
};

let csrfPromise: Promise<void> | null = null;

const ensureCsrfToken = async (): Promise<void> => {
  if (getCookieValue("csrftoken")) return;
  if (!csrfPromise) {
    csrfPromise = csrfApi
      .get("/auth/csrf/")
      .then(() => undefined)
      .finally(() => {
        csrfPromise = null;
      });
  }
  await csrfPromise;
};

/**
 * Normaliza URLs para que siempre terminen con /
 * Ej: /auth/login -> /auth/login/
 */
const normalizeUrl = (url: string): string => {
  if (!url) return url;
  
  // No agregar / si contiene parámetros query
  if (url.includes("?")) {
    const [path, query] = url.split("?");
    return `${path.endsWith("/") ? path : path + "/"}?${query}`;
  }
  
  return url.endsWith("/") ? url : url + "/";
};

// Interceptor para normalizar URLs
api.interceptors.request.use(
  async (config) => {
    // Normalizar URL
    if (config.url) {
      config.url = normalizeUrl(config.url);
    }

    // Las cookies se envían automáticamente con withCredentials: true
    const method = (config.method || "get").toLowerCase();
    const needsCsrf = ["post", "put", "patch", "delete"].includes(method);
    if (needsCsrf) {
      await ensureCsrfToken();
      const csrfToken = getCookieValue("csrftoken");
      if (csrfToken) {
        config.headers = config.headers || {};
        config.headers["X-CSRFToken"] = csrfToken;
      }
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Interceptor para manejar errores globalmente
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config;
    const classified = classifyError(error);
    const isLoginRequest = original?.url?.includes("/auth/login");

    if (
      classified.type === ApiErrorType.AUTHENTICATION &&
      !isLoginRequest &&
      !original?._retry &&
      !original?.url?.includes("/auth/refresh/")
    ) {
      original._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          failedQueue.push({ resolve, reject, config: original });
        });
      }

      isRefreshing = true;

      try {
        // Llamar al endpoint de refresh - las cookies se envían automáticamente
        await refreshApi.post("/auth/refresh/");

        // Las nuevas cookies se establecen automáticamente en la respuesta
        processQueue(null);

        // Reintentar la petición original
        return api(original);
      } catch (refreshError: any) {
        // Clasificar el error del refresh
        const classifiedRefreshError = classifyError(refreshError);
        processQueue(classifiedRefreshError);
        clearUser(); // Limpiar datos del usuario
        if (
          typeof window !== "undefined" &&
          !window.location.pathname.includes("/login")
        ) {
          window.location.href = "/login";
        }
        return Promise.reject(classifiedRefreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(classified);
  }
);

export default api;