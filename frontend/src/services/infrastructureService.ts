import { apiRequest } from "./api";
import type { InfrastructureAsset, InspectionRecord } from "../types";

/**
 * Backend asset response from PostgreSQL
 */
export interface BackendAsset {
  id?: number;
  asset_id: string;
  name: string;
  type: string;
  district?: string;
  location?: string;
  latitude?: string | number;
  longitude?: string | number;
  age?: number;
  design_life?: number;
  material?: string;
  condition?: string;
  status?: string;
  owner?: string;
  built_year?: number;
  health_score?: number;
  risk_score?: number;
  remaining_useful_life?: number;
  source?: string;
  source_id?: string;
  [key: string]: any;
}

/**
 * Transform backend asset to frontend format
 * Maps backend field names to frontend expectations
 */
function transformAsset(backendAsset: BackendAsset): any {
  return {
    ...backendAsset,
    id: backendAsset.asset_id || String(backendAsset.id),
    asset_id: backendAsset.asset_id,
    name: backendAsset.name,
    type: backendAsset.type,
    asset_type: backendAsset.type,
    location: backendAsset.location ?? backendAsset.district,
    district: backendAsset.district,
    lat: backendAsset.latitude != null ? Number(backendAsset.latitude) : undefined,
    lng: backendAsset.longitude != null ? Number(backendAsset.longitude) : undefined,
    latitude: backendAsset.latitude != null ? Number(backendAsset.latitude) : undefined,
    longitude: backendAsset.longitude != null ? Number(backendAsset.longitude) : undefined,
    built_year: backendAsset.built_year,
    age: backendAsset.age,
    design_life: backendAsset.design_life,
    health_score: backendAsset.health_score,
    risk_score: backendAsset.risk_score,
    remaining_useful_life: backendAsset.remaining_useful_life,
    condition: backendAsset.condition,
    status: backendAsset.status || "Unknown",
    owner: backendAsset.owner,
    material: backendAsset.material,
    source: backendAsset.source,
    source_id: backendAsset.source_id,
  };
}

/**
 * Infrastructure Service - handles asset queries and transformations
 */
export const infrastructureService = {
  /**
   * List all infrastructure assets with optional pagination and filtering
   */
  list: async (params: Record<string, string | number | undefined> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    });
    
    try {
      const payload = await apiRequest<{ total?: number; items?: BackendAsset[] } | BackendAsset[]>(
        `/api/v1/infrastructure${query.toString() ? `?${query}` : ""}`
      );

      const rawItems = Array.isArray(payload) ? payload : (payload.items ?? []);
      const total = Array.isArray(payload) ? rawItems.length : (payload.total ?? rawItems.length);
      const transformedAssets = rawItems.map(transformAsset);

      return {
        total,
        data: transformedAssets,
        items: transformedAssets,
      };
    } catch (error) {
      console.error("Failed to fetch infrastructure assets:", error);
      throw error;
    }
  },

  /**
   * Get a single infrastructure asset by ID
   */
  get: async (id: string) => {
    try {
      const asset = await apiRequest<BackendAsset>(
        `/api/v1/infrastructure/${encodeURIComponent(id)}`
      );
      return transformAsset(asset);
    } catch (error) {
      console.error(`Failed to fetch infrastructure asset ${id}:`, error);
      throw error;
    }
  },

  /**
   * Get infrastructure categories/summary
   */
  categories: async () => {
    try {
      return await apiRequest<any>("/api/v1/infrastructure/summary");
    } catch (error) {
      console.warn("Failed to fetch categories summary:", error);
      return { categories: [] };
    }
  },

  /**
   * Get analytics totals
   */
  totals: async () => {
    try {
      return await apiRequest<any>("/api/v1/dashboard/overview");
    } catch (error) {
      console.warn("Failed to fetch analytics summary:", error);
      return { total: 0, byDistrict: {}, byType: {} };
    }
  },

  /**
   * Get inspection records for an asset
   */
  inspections: async (id: string) => {
    try {
      return await apiRequest<InspectionRecord[]>(`/api/v1/assets/${encodeURIComponent(id)}/inspections`);
    } catch (error) {
      console.warn(`Failed to fetch inspections for asset ${id}:`, error);
      return [];
    }
  },
};




