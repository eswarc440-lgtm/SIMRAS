import { applyDigitalTwinPriorityScores } from "../pages/digital-twin/twinPriority";
import type { EvidenceStateResponse } from "../types/evidence";
import type {
  AssetListResponse,
  MapFeatureCollection,
  MapFeatureSummaryResponse,
  TwinCatalogResponse,
  TwinResponse,
} from "../types/twin";

// Use relative URLs to leverage Vite proxy during development
// The proxy is configured in vite.config.ts to forward /api to the backend
const API_BASE_URL = "/api/v1";

async function request<T>(path: string): Promise<T> {
  const url = `${API_BASE_URL}${path}`;
  
  try {
    const response = await fetch(url, {
      method: "GET",
      cache: "no-store",
      headers: {
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      let detail = `HTTP ${response.status}`;
      
      const contentType = response.headers.get("content-type") || "";
      if (contentType.includes("application/json")) {
        try {
          const json = await response.json();
          detail = json?.detail || json?.message || detail;
        } catch {
          // JSON parse failed, use text
          detail = await response.text() || detail;
        }
      } else {
        detail = await response.text() || detail;
      }
      
      throw new Error(`${url} ${response.statusText}: ${detail}`);
    }

    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json")) {
      const text = await response.text();
      throw new Error(`Expected JSON response from ${url}, got: ${contentType}`);
    }

    return response.json() as Promise<T>;
  } catch (error) {
    if (error instanceof Error) {
      throw error;
    }
    throw new Error(`Request to ${url} failed: ${String(error)}`);
  }
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
    ).then((response) => ({
      ...response,
      items: applyDigitalTwinPriorityScores(response.items ?? []),
    }));
  },
  highRisk: () =>
    request<AssetListResponse["items"]>("/assets/high-risk?limit=10"),
  twin: (assetCode: string) =>
    request<TwinResponse>(`/assets/${assetCode}/twin`),
  assessment: (assetCode: string) =>
    request<Record<string, unknown>>(`/reports/assets/${encodeURIComponent(assetCode)}/assessment`),
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
