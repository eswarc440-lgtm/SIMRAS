/**
 * Digital Twin API Service
 *
 * Handles API calls to backend Digital Twin endpoints for model metadata,
 * asset visualization data, and 3D model information
 */
import { apiRequest } from "./api";

/**
 * Digital Twin metadata for an asset
 */
export interface DigitalTwinMetadata {
  asset_id: string;
  asset_type: string;
  model_type: "procedural" | "gltf" | "placeholder";
  model_url?: string;
  geometry?: string;
  vertices?: number;
  faces?: number;
  materials?: number;
  animations?: number;
  bounding_box?: {
    x: [number, number];
    y: [number, number];
    z: [number, number];
  };
  scale_factor?: number;
  last_updated?: string;
  metadata?: Record<string, any>;
}

/**
 * Digital Twin response with asset and model data
 */
export interface DigitalTwinResponse {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  model: DigitalTwinMetadata;
  health_score?: number;
  risk_score?: number;
  condition?: string;
  location?: string;
}

/**
 * Models registry containing all available 3D models
 */
export interface ModelsRegistry {
  version: string;
  last_updated: string;
  total_models: number;
  models: DigitalTwinMetadata[];
}

/**
 * Digital Twin API service
 */
export const digitalTwinApi = {
  /**
   * Get complete Digital Twin data for an asset
   *
   * Includes asset information, 3D model metadata, and AI predictions
   *
   * @param assetId - Asset identifier
   * @returns Digital Twin data with model information
   */
  getAssetDigitalTwin: async (assetId: string): Promise<DigitalTwinResponse> => {
    try {
      const response = await apiRequest<DigitalTwinResponse>(
        `/api/v1/digital-twin/assets/${encodeURIComponent(assetId)}`
      );
      return response;
    } catch (error) {
      console.error(`Failed to fetch Digital Twin for asset ${assetId}:`, error);
      throw error;
    }
  },

  /**
   * Get 3D model statistics
   *
   * Returns count of available models, breakdown by type and source
   *
   * @returns Model statistics
   */
  getModelStats: async (): Promise<{
    total_models: number;
    by_type: Record<string, number>;
    by_source: Record<string, number>;
  }> => {
    try {
      const response = await apiRequest<{ total_models: number; by_type: Record<string, number>; by_source: Record<string, number> }>("/api/v1/digital-twin/stats");
      return response;
    } catch (error) {
      console.error("Failed to fetch model statistics:", error);
      return {
        total_models: 0,
        by_type: {},
        by_source: {},
      };
    }
  },

  /**
   * Get list of assets with available 3D models
   *
   * @param skip - Pagination offset
   * @param limit - Number of results
   * @returns Array of asset IDs with available models
   */
  getAssetsWithModels: async (
    skip: number = 0,
    limit: number = 100
  ): Promise<string[]> => {
    try {
      const response = await apiRequest<string[]>(
        `/api/v1/digital-twin/models/available?skip=${skip}&limit=${limit}`
      );
      return response;
    } catch (error) {
      console.error("Failed to fetch assets with models:", error);
      return [];
    }
  },

  /**
   * Get models registry from public/models/models.json
   *
   * This is a local JSON file, not an API call
   *
   * @returns Models registry
   */
  getModelsRegistry: async (): Promise<ModelsRegistry> => {
    try {
      const response = await fetch("/models/models.json");
      if (!response.ok) {
        throw new Error(`Failed to load models registry: ${response.statusText}`);
      }
      return response.json();
    } catch (error) {
      console.error("Failed to fetch models registry:", error);
      return {
        version: "0.0.0",
        last_updated: new Date().toISOString(),
        total_models: 0,
        models: [],
      };
    }
  },

  /**
   * Get specific model metadata from registry
   *
   * @param assetId - Asset identifier
   * @returns Model metadata or null if not found
   */
  getModelMetadata: async (assetId: string): Promise<DigitalTwinMetadata | null> => {
    try {
      const registry = await digitalTwinApi.getModelsRegistry();
      const model = registry.models.find((m) => m.asset_id === assetId);
      return model || null;
    } catch (error) {
      console.error(`Failed to get model metadata for ${assetId}:`, error);
      return null;
    }
  },

  /**
   * Check if model file is available
   *
   * Makes a HEAD request to verify file exists at the given URL
   *
   * @param modelUrl - URL to the model file
   * @returns true if file is accessible, false otherwise
   */
  checkModelAvailability: async (modelUrl: string): Promise<boolean> => {
    try {
      const response = await fetch(modelUrl, { method: "HEAD" });
      return response.ok;
    } catch (error) {
      console.error(`Model not available at ${modelUrl}:`, error);
      return false;
    }
  },

  /**
   * Get asset-specific 3D model type for procedural generation
   *
   * @param assetId - Asset identifier
   * @returns Asset type string (dam, bridge, road, etc.)
   */
  getAssetModelType: async (assetId: string): Promise<string | null> => {
    try {
      const dtData = await digitalTwinApi.getAssetDigitalTwin(assetId);
      return dtData.asset_type || null;
    } catch (error) {
      console.error(`Failed to get asset model type for ${assetId}:`, error);
      return null;
    }
  },
};




