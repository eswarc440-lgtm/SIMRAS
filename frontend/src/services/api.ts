import type { AssetListResponse, TwinResponse } from "../types/twin";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error("VITE_API_BASE_URL is not configured");
}

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Accept: "application/json" },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status} ${response.statusText}: ${detail}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  assets: () => request<AssetListResponse>("/assets?limit=1000"),
  highRisk: () => request<AssetListResponse["items"]>("/assets/high-risk?limit=10"),
  twin: (assetCode: string) => request<TwinResponse>(`/assets/${assetCode}/twin`),
  summary: () => request<Record<string, number>>("/analytics/summary"),
};

