/**
 * Services Index
 * 
 * Centralized export of all API service modules
 */

export { API_BASE_URL, apiRequest, mockRequest } from "./api";
export type { ApiError } from "./api";

export { infrastructureService } from "./infrastructureService";
export type { BackendAsset } from "./infrastructureService";

export { gisService } from "./gisService";
export type {
  GeoJSONPoint,
  GeoJSONFeature,
  GeoJSONFeatureCollection,
} from "./gisService";

export { gisApi } from "./gisApi";
export type {
  GeoJSONProperties,
} from "./gisApi";

export { digitalTwinApi } from "./digitalTwinApi";
export type {
  DigitalTwinMetadata,
  DigitalTwinResponse,
  ModelsRegistry,
} from "./digitalTwinApi";

export { predictionService } from "./predictionService";
export type {
  AssetPrediction,
  PredictionSummary,
} from "./predictionService";

export { analyticsService } from "./analyticsService";
export { authService } from "./authService";
export { reportService } from "./reportService";
