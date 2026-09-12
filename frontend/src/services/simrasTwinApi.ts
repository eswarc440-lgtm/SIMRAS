import type {
  AssetListResponse,
  MapFeatureCollection,
  MapFeatureSummaryResponse,
  TwinResponse,
  TwinCatalogResponse,
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
  twinCatalog: () => request<TwinCatalogResponse>("/twin-catalog"),
  riskPrediction: (assetCode: string) =>
    request<{
      available: boolean;
      asset_code: string;
      asset_name?: string | null;
      asset_type?: string | null;
      risk_score: number | null;
      risk_level: string | null;
      confidence_score: number | null;
      status: string;
      model_version: string | null;
      feature_version: string | null;
      prediction_time: string | null;
      factors: Record<string, unknown> | null;
      interpretation: string;
    }>(
      `/assets/${encodeURIComponent(assetCode)}/risk-prediction`,
    ),

  damBarrageProfile: (assetCode: string) =>
    request<any>(
      `/assets/${encodeURIComponent(assetCode)}/dam-barrage-profile`,
    ),

  assets: (options?: {
    assetType?: string;
    district?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }) => {
    const parameters = new URLSearchParams({
      limit: String(options?.limit ?? 1000),
      offset: String(options?.offset ?? 0),
    });

    if (options?.assetType) {
      parameters.set("asset_type", options.assetType);
    }

    if (options?.district) {
      parameters.set("district", options.district);
    }

    if (options?.search) {
      parameters.set("search", options.search);
    }

    return request<AssetListResponse>(
      `/assets?${parameters.toString()}`,
    );
  },
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

export const damBarrageProfile = (
  assetCode: string,
) =>
  request<any>(
    `/assets/${encodeURIComponent(assetCode)}/dam-barrage-profile`,
  );

export const bridgeReportProfile = (
  assetCode: string,
) =>
  request<any>(
    `/assets/${encodeURIComponent(assetCode)}/bridge-report-profile`,
  );

