export type HealthStatus = "healthy" | "warning" | "critical";
export type RiskLevel = "low" | "medium" | "high";
export type AssetType = "Bridge" | "Road" | "Building" | "Water" | "Utility" | "Other";
export type AssetStatus = "Operational" | "Under Inspection" | "Under Repair" | "Restricted";

export interface InfrastructureAsset {
  id: string;
  name: string;
  type: AssetType;
  location: string;
  district: string;
  lat: number;
  lng: number;
  health: HealthStatus;
  healthScore: number;
  risk: RiskLevel;
  riskScore: number;
  lastInspection: string;
  status: AssetStatus;
  builtYear: number;
  rulYears: number;
}

export interface Prediction {
  id: string;
  assetId: string;
  assetName: string;
  prediction: string;
  risk: RiskLevel;
  confidence: number;
  predictedAt: string;
}

export interface AIInsight {
  id: string;
  title: string;
  body: string;
  assetId: string;
  risk: RiskLevel;
  confidence: number;
}

export interface ModelMetrics {
  name: string;
  version: string;
  r2: number;
  mae: number;
  rmse: number;
  trainedAt: string;
}

export interface TrendPoint {
  period: string;
  healthy: number;
  warning: number;
  critical: number;
  predictions?: number;
  riskIndex?: number;
}

export interface ReportItem {
  id: string;
  title: string;
  category: "AI Prediction" | "Infrastructure" | "Risk" | "Analytics" | "Inspection";
  type: string;
  generated: string;
  status: "Ready" | "Processing" | "Archived";
  summary: string;
  pages: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  body: string;
  severity: "critical" | "warning" | "info";
  time: string;
  read: boolean;
}

export interface InspectionRecord {
  id: string;
  date: string;
  inspector: string;
  finding: string;
  health: HealthStatus;
  score: number;
}

export interface AuthUser {
  name: string;
  email: string;
  phone: string;
  organization: string;
  role: string;
}

export interface DigitalTwinViewerProps {
  assetId: string;
  asset: InfrastructureAsset;
  modelUrl?: string | null;
  onError?: (error: Error) => void;
  onLoaded?: () => void;
}
