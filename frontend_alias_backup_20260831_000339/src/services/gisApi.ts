/**
 * GIS API Client
 * 
 * Handles API calls to backend GIS endpoints for fetching geospatial data
 * Returns GeoJSON-formatted infrastructure asset data for map visualization
 */
import { apiRequest } from "./api";

/**
 * GeoJSON Point geometry (RFC 7946)
 * Coordinates are [longitude, latitude] per GeoJSON spec
 */
export interface GeoJSONPoint {
  type: "Point";
  coordinates: [number, number]; // [longitude, latitude]
}

/**
 * GeoJSON Feature properties for infrastructure assets
 */
export interface GeoJSONProperties {
  asset_id: string;
  name: string;
  type: string;
  district?: string;
  location?: string;
  condition?: string | null;
  status?: string | null;
  owner?: string | null;
  health_score?: number | null;
  risk_score?: number | null;
  age?: number | null;
  design_life?: number | null;
  material?: string | null;
  remaining_useful_life?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  [key: string]: any;
}

/**
 * GeoJSON Feature for a single infrastructure asset
 */
export interface GeoJSONFeature {
  type: "Feature";
  geometry: GeoJSONPoint;
  properties: GeoJSONProperties;
}

/**
 * GeoJSON FeatureCollection for multiple infrastructure assets
 */
export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

/**
 * GIS API service for geospatial queries and GeoJSON operations
 */
export const gisApi = {
  /**
   * Get all infrastructure assets as GeoJSON FeatureCollection
   * 
   * Supports filtering by:
   * - district: Geographic region
   * - type: Asset type (dam, bridge, road, etc.)
   * - status: Operational status
   * - min_health/max_health: Health score range (0-100)
   * - min_risk/max_risk: Risk score range (0-100)
   * 
   * @param options - Query parameters for filtering and pagination
   * @returns GeoJSON FeatureCollection with all matching assets
   */
  getAssets: async (options?: {
    skip?: number;
    limit?: number;
    district?: string;
    type?: string;
    status?: string;
    min_health?: number;
    max_health?: number;
    min_risk?: number;
    max_risk?: number;
  }): Promise<GeoJSONFeatureCollection> => {
    const params = new URLSearchParams();

    if (options) {
      if (options.skip !== undefined) params.append("skip", String(options.skip));
      if (options.limit !== undefined) params.append("limit", String(options.limit));
      if (options.district) params.append("district", options.district);
      if (options.type) params.append("type", options.type);
      if (options.status) params.append("status", options.status);
      if (options.min_health !== undefined) params.append("min_health", String(options.min_health));
      if (options.max_health !== undefined) params.append("max_health", String(options.max_health));
      if (options.min_risk !== undefined) params.append("min_risk", String(options.min_risk));
      if (options.max_risk !== undefined) params.append("max_risk", String(options.max_risk));
    }

    const queryString = params.toString();
    const url = `/api/v1/gis/assets${queryString ? `?${queryString}` : ""}`;

    try {
      return await apiRequest<GeoJSONFeatureCollection>(url);
    } catch (error) {
      console.error("Failed to fetch GIS assets:", error);
      throw error;
    }
  },

  /**
   * Get infrastructure assets within a bounding box
   * 
   * Useful for map viewport queries during pan/zoom operations
   * Returns all assets that fall within the specified geographic bounds
   * 
   * @param bbox - Bounding box coordinates
   * @param limit - Maximum number of results to return
   * @returns GeoJSON FeatureCollection with matching assets
   */
  getAssetsByBbox: async (
    bbox: {
      min_lat: number;
      max_lat: number;
      min_lon: number;
      max_lon: number;
    },
    limit?: number
  ): Promise<GeoJSONFeatureCollection> => {
    const params = new URLSearchParams();
    params.append("min_lat", String(bbox.min_lat));
    params.append("max_lat", String(bbox.max_lat));
    params.append("min_lon", String(bbox.min_lon));
    params.append("max_lon", String(bbox.max_lon));
    if (limit) params.append("limit", String(limit));

    try {
      return await apiRequest<GeoJSONFeatureCollection>(
        `/api/v1/gis/assets/bbox?${params.toString()}`
      );
    } catch (error) {
      console.error("Failed to fetch GIS assets by bbox:", error);
      throw error;
    }
  },

  /**
   * Get a single infrastructure asset as GeoJSON Feature
   * 
   * @param assetId - Asset identifier
   * @returns GeoJSON Feature with Point geometry and asset properties
   */
  getAsset: async (assetId: string): Promise<GeoJSONFeature> => {
    try {
      return await apiRequest<GeoJSONFeature>(
        `/api/v1/gis/assets/${encodeURIComponent(assetId)}`
      );
    } catch (error) {
      console.error(`Failed to fetch GIS asset ${assetId}:`, error);
      throw error;
    }
  },

  /**
   * Transform GeoJSON Feature to InfrastructureAsset format for map rendering
   * Extracts relevant properties and converts coordinates
   */
  featureToAsset: (feature: GeoJSONFeature) => {
    const [lng, lat] = feature.geometry.coordinates;
    return {
      ...feature.properties,
      id: feature.properties.asset_id,
      asset_id: feature.properties.asset_id,
      name: feature.properties.name,
      type: feature.properties.type,
      asset_type: feature.properties.type,
      lat,
      lng,
      latitude: lat,
      longitude: lng,
      condition: feature.properties.condition,
      status: feature.properties.status,
      health_score: feature.properties.health_score,
      risk_score: feature.properties.risk_score,
    };
  },
};




