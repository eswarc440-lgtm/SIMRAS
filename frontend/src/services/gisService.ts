import { apiRequest } from "./api";
import type { InfrastructureAsset } from "../types";

/**
 * GeoJSON Point geometry (RFC 7946)
 */
export interface GeoJSONPoint {
  type: "Point";
  coordinates: [number, number]; // [longitude, latitude]
}

/**
 * GeoJSON Feature for infrastructure assets
 */
export interface GeoJSONFeature {
  type: "Feature";
  geometry: GeoJSONPoint;
  properties: Record<string, any>;
}

/**
 * GeoJSON FeatureCollection
 */
export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONFeature[];
}

/**
 * GIS Service - handles geospatial queries and GeoJSON operations
 */
export const gisService = {
  /**
   * Get all infrastructure assets as GeoJSON FeatureCollection
   * Supports filtering by district, type, status, health, risk scores
   */
  getAssets: async (params: {
    skip?: number;
    limit?: number;
    district?: string;
    type?: string;
    status?: string;
    min_health?: number;
    max_health?: number;
    min_risk?: number;
    max_risk?: number;
  } = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") {
        query.set(key, String(value));
      }
    });
    return apiRequest<GeoJSONFeatureCollection>(
      `/api/v1/gis/assets${query.toString() ? `?${query}` : ""}`
    );
  },

  /**
   * Get assets within a bounding box
   * Useful for map viewport queries
   */
  getAssetsByBbox: async (bbox: {
    min_lat: number;
    max_lat: number;
    min_lon: number;
    max_lon: number;
    limit?: number;
  }) => {
    const query = new URLSearchParams();
    query.set("min_lat", String(bbox.min_lat));
    query.set("max_lat", String(bbox.max_lat));
    query.set("min_lon", String(bbox.min_lon));
    query.set("max_lon", String(bbox.max_lon));
    if (bbox.limit) query.set("limit", String(bbox.limit));

    return apiRequest<GeoJSONFeatureCollection>(
      `/api/v1/gis/assets/bbox?${query}`
    );
  },

  /**
   * Get a single asset as GeoJSON Feature
   */
  getAsset: async (assetId: string) => {
    return apiRequest<GeoJSONFeature>(
      `/api/v1/gis/assets/${encodeURIComponent(assetId)}`
    );
  },

  /**
   * Legacy: Get all assets as FeatureCollection
   * Maps to new endpoint
   */
  featureCollection: async (params: Record<string, string | number | undefined> = {}) => {
    const query = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== "") query.set(key, String(value));
    });
    return apiRequest<GeoJSONFeatureCollection>(
      `/api/v1/gis/assets${query.toString() ? `?${query}` : ""}`
    );
  },
};
