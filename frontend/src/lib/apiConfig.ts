const getDefaultApiUrl = (): string => {
  if (typeof window !== "undefined") {
    return `${window.location.protocol}//${window.location.hostname}:8000/`;
  }
  return "http://localhost:8000/";
};

const normalizeApiBaseUrl = (url: string): string => {
  const trimmedUrl = url.trim();
  return trimmedUrl.endsWith("/") ? trimmedUrl : `${trimmedUrl}/`;
};

export const API_BASE_URL = normalizeApiBaseUrl(
  process.env.NEXT_PUBLIC_API_URL || getDefaultApiUrl(),
);
