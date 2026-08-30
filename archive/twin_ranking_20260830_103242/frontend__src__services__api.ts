import type {
  AssetListResponse,
  MapFeatureCollection,
  MapFeatureSummaryResponse,
  TwinResponse,
} from "../types/twin";
import type { EvidenceStateResponse } from "../types/evidence";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

if (!API_BASE_URL) {
  throw new Error("VITE_API_BASE_URL is not configured");
}
async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "GET",
    cache: "no-store",
    headers: {
      Accept: "application/json",
    },
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(
      `${response.status} ${response.statusText}: ${detail}`,
    );
  }

  return response.json() as Promise<T>;
}
export const api = {
  assets: () => request<AssetListResponse>("/assets?limit=1000"),
  highRisk: () =>
    request<AssetListResponse["items"]>("/assets/high-risk?limit=10"),
  twin: (assetCode: string) =>
    request<TwinResponse>(`/assets/${assetCode}/twin`),
  state: (assetCode: string) =>
    request<EvidenceStateResponse>(`/assets/${assetCode}/state`),
  summary: () => request<Record<string, number>>("/analytics/summary"),
  mapSummary: () => request<MapFeatureSummaryResponse>("/map/summary"),
  mapFeatures: (featureType?: string) => {
    const parameters = new URLSearchParams({ limit: "5000" });

    if (featureType) {
      parameters.set("feature_type", featureType);
    }

    return request<MapFeatureCollection>(
      `/map/features?${parameters.toString()}`,
    );
  },
};
