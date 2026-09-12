const configured =
  import.meta.env.VITE_BACKEND_URL ??
  import.meta.env.VITE_API_BASE_URL ??
  "http://127.0.0.1:8000";

export const API_BASE_URL = configured.replace(/\/api\/v1\/?$/, "");

export interface ApiError { status: number; message: string; }

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path.startsWith("/") ? path : `/${path}`}`;
  const response = await fetch(url, {
    ...init,
    headers: { Accept: "application/json", "Content-Type": "application/json", ...(init.headers ?? {}) },
  });
  if (!response.ok) {
    let detail = "Request failed";
    try { const payload = await response.json(); detail = payload?.detail ?? payload?.message ?? JSON.stringify(payload); }
    catch { detail = await response.text(); }
    throw { status: response.status, message: detail } as ApiError;
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function mockRequest<T>(data: T, latency = 0): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(data), latency));
}

// Compatibility bridge for preserved SIMRAS twin modules.
export { api } from "./simrasTwinApi";

