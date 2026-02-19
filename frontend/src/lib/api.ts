// app/lib/api.ts
import axios from "axios";
import { clearTokens, getTokens, saveTokens } from "@/utils/storage";
import { classifyError, ApiErrorType } from "@/lib/errorHandler";

const baseURL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/";

const api = axios.create({
  baseURL,
  timeout: 10000, // 10 segundos
  headers: {
    "Content-Type": "application/json",
  },
});

const refreshApi = axios.create({
  baseURL,
  timeout: 10000,
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

const processQueue = (error: any, token: string | null) => {
  failedQueue.forEach(({ resolve, reject, config }) => {
    if (error) {
      reject(error);
      return;
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    resolve(api(config));
  });

  failedQueue = [];
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

// Interceptor para agregar token automáticamente
api.interceptors.request.use(
  (config) => {
    // Normalizar URL
    if (config.url) {
      config.url = normalizeUrl(config.url);
    }

    if (typeof window !== "undefined") {
      const { accessToken } = getTokens();
      if (accessToken) {
        config.headers.Authorization = `Bearer ${accessToken}`;
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
        const { refreshToken } = getTokens();

        if (!refreshToken) {
          clearTokens();
          if (
            typeof window !== "undefined" &&
            window.location.pathname !== "/login"
          ) {
            window.location.href = "/login";
          }
          return Promise.reject(error);
        }

        const res = await refreshApi.post("/auth/refresh/", {
          refresh_token: refreshToken,
        });

        saveTokens(res.data);
        const newAccessToken = res.data.access || res.data.access_token;
        processQueue(null, newAccessToken);

        original.headers.Authorization = `Bearer ${newAccessToken}`;
        return api(original);
      } catch (refreshError) {
        processQueue(refreshError, null);
        clearTokens();
        if (
          typeof window !== "undefined" &&
          !window.location.pathname.includes("/login")
        ) {
          window.location.href = "/login";
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(classified);
  }
);

export default api;