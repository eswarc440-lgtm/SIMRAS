import { apiRequest } from "./api";

/**
 * Single asset prediction data
 */
export interface AssetPrediction {
  asset_id: string;
  asset_name: string;
  asset_type: string;
  health_score: number | null;
  risk_score: number | null;
  risk_level: string | null;
  predicted_risk_score: number;
  risk_category: string;
  remaining_life: number | null;
  prediction_timestamp: string | null;
  model_version?: string;
  confidence?: number;
}

/**
 * Prediction summary statistics
 */
export interface PredictionSummary {
  total_assets: number;
  predicted_assets: number;
  high_risk_assets: number;
  medium_risk_assets: number;
  low_risk_assets: number;
  average_health_score: number;
  average_risk_score: number;
  average_remaining_life?: number;
}

/**
 * Prediction service for AI predictions and risk assessment
 */
export const predictionService = {
  /**
   * List all predictions with optional filtering
   */
  list: async () => {
    try {
      const payload = await apiRequest<{ items?: AssetPrediction[]; predictions?: AssetPrediction[] }>(
        "/api/v1/predictions"
      );
      return payload.items ?? payload.predictions ?? [];
    } catch (error) {
      console.warn("Failed to fetch predictions list:", error);
      return [];
    }
  },

  /**
   * Get prediction for a single asset
   * Generates new prediction if not cached
   */
  getAssetPrediction: async (assetId: string): Promise<AssetPrediction | null> => {
    try {
      return await apiRequest<AssetPrediction>(
        `/api/v1/predictions/${encodeURIComponent(assetId)}`
      );
    } catch (error) {
      console.warn(`Failed to fetch prediction for asset ${assetId}:`, error);
      return null;
    }
  },

  /**
   * Generate new prediction for an asset
   * Uses trained ML models to compute health/risk/RUL
   */
  generatePrediction: async (assetId: string): Promise<AssetPrediction | null> => {
    try {
      return await apiRequest<AssetPrediction>(
        `/api/v1/predictions/${encodeURIComponent(assetId)}`,
        { method: "POST" }
      );
    } catch (error) {
      console.warn(`Failed to generate prediction for asset ${assetId}:`, error);
      return null;
    }
  },

  /**
   * Get predictions for multiple assets
   */
  getAssetPredictions: async (assetIds: string[]): Promise<{
    predictions: AssetPrediction[];
  }> => {
    try {
      return await apiRequest<{ predictions: AssetPrediction[] }>(
        "/api/v1/predictions/batch",
        {
          method: "POST",
          body: JSON.stringify(assetIds),
        }
      );
    } catch (error) {
      console.warn("Failed to fetch batch predictions:", error);
      return { predictions: [] };
    }
  },

  /**
   * Get prediction summary statistics
   */
  getSummary: async (): Promise<PredictionSummary> => {
    try {
      return await apiRequest<PredictionSummary>(
        "/api/v1/predictions/summary"
      );
    } catch (error) {
      console.warn("Failed to fetch prediction summary:", error);
      return {
        total_assets: 0,
        predicted_assets: 0,
        high_risk_assets: 0,
        medium_risk_assets: 0,
        low_risk_assets: 0,
        average_health_score: 0,
        average_risk_score: 0,
      };
    }
  },

  /**
   * Get high-risk assets
   */
  getHighRiskAssets: async (): Promise<AssetPrediction[]> => {
    try {
      return await apiRequest<AssetPrediction[]>(
        "/api/v1/predictions/high-risk"
      );
    } catch (error) {
      console.warn("Failed to fetch high-risk assets:", error);
      return [];
    }
  },

  /**
   * Legacy methods for backward compatibility
   */
  insights: async () => {
    try {
      return await apiRequest<any>("/api/v1/dashboard/overview");
    } catch {
      return [];
    }
  },

  models: async () => Promise.resolve([]),

  evaluation: async () => {
    try {
      return await apiRequest<PredictionSummary>("/api/v1/dashboard/overview");
    } catch {
      return {
        total_assets: 0,
        predicted_assets: 0,
        high_risk_assets: 0,
        medium_risk_assets: 0,
        low_risk_assets: 0,
        average_health_score: 0,
        average_risk_score: 0,
      };
    }
  },
};
