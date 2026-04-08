import axios from "axios";
import { clearUser } from "@/utils/storage";
import { classifyError, ApiErrorType } from "@/lib/errorHandler";
import { API_BASE_URL } from "@/lib/apiConfig";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

const refreshApi = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

const csrfApi = axios.create({
  baseURL: API_BASE_URL,
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

const normalizeUrl = (url: string): string => {
  if (!url) return url;

  if (url.includes("?")) {
    const [path, query] = url.split("?");
    return `${path.endsWith("/") ? path : `${path}/`}?${query}`;
  }

  return url.endsWith("/") ? url : `${url}/`;
};

api.interceptors.request.use(
  async (config) => {
    if (config.url) {
      config.url = normalizeUrl(config.url);
    }

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
  (error) => Promise.reject(error),
);

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
        await refreshApi.post("/auth/refresh/");
        processQueue(null);
        return api(original);
      } catch (refreshError: any) {
        const classifiedRefreshError = classifyError(refreshError);
        processQueue(classifiedRefreshError);
        clearUser();
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
  },
);

export default api;
