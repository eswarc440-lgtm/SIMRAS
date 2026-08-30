export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface GeometryPoint {
  type: "Point";
  coordinates: [number, number];
}

export interface AssetSummary {
  asset_code: string;
  name: string;
  asset_type: "bridge" | "dam" | "barrage";
  subtype?: string | null;
  district?: string | null;
  identity_status: string;
  condition?: string | null;
  geometry: GeometryPoint;
  risk_score?: number | null;
  risk_level?: RiskLevel | null;
  data_confidence?: number | null;
  twin_quality_score?: number;
  twin_quality?: "EXCELLENT" | "READY" | "PARTIAL" | "BASIC";
  twin_group?: "BEST" | "IMPROVING" | "BASIC";
  twin_quality_label?: string;
  twin_fidelity?: string;
  twin_source_backed?: boolean;
  twin_dimension_count?: number;
  twin_template?: string;
}

export interface AssetListResponse {
  items: AssetSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface SourceValue {
  value: number | string | null;
  unit?: string | null;
  source: string;
  source_type: string;
  observed_at?: string | null;
  ingested_at?: string | null;
  quality_flag: string;
  confidence?: number | null;
  is_estimated: boolean;
}

export interface TwinResponse {
  asset: AssetSummary;
  static: Record<string, unknown>;
  twin: {
    format: string;
    uri?: string | null;
    version: string;
    fidelity_level: string;
    model_source: string;
    source_url?: string | null;
    dimensions: Record<string, unknown>;
    is_asset_specific: boolean;
    heading_deg?: number | null;
    elevation_m?: number | null;
    horizontal_accuracy_m?: number | null;
  };
  environment: Record<string, SourceValue>;
  inspection: {
    inspection_date?: string | null;
    condition?: string | null;
    score?: number | null;
    quality_flag: string;
    is_synthetic: boolean;
  };
  maintenance: Array<Record<string, unknown>>;
  sensors_status: string;
  ai: {
    health_score?: number | null;
    health_lower_bound?: number | null;
    health_upper_bound?: number | null;
    risk_score?: number | null;
    risk_level?: RiskLevel | null;
    hazard_score?: number | null;
    hazard_level?: RiskLevel | null;
    remaining_life_years?: number | null;
    rul_lower_bound?: number | null;
    rul_upper_bound?: number | null;
    rul_confidence?: number | null;
    rul_status?: string | null;
    rul_basis?: string | null;
    rul_basis_url?: string | null;
    rul_lower_bound?: number | null;
    rul_upper_bound?: number | null;
    confidence?: number | null;
    model_version: string;
    feature_version: string;
    prediction_time: string;
    status: string;
    prediction_method?: string;
    model_validated?: boolean;
    training_scope?: string;
    forecast_horizon_years?: number | null;
    factors: string[];
    recommendations?: string[];
  };
  freshness: Record<string, string>;
  generated_at: string;
}
export interface MapFeatureProperties {
  external_id: string;
  name?: string | null;
  feature_type: string;
  subtype?: string | null;
  attributes: Record<string, unknown>;
  identity_status: string;
  confidence_score?: number | null;
  retrieved_at: string;
  source_code: string;
  source_name: string;
  source_url?: string | null;
  licence?: string | null;
}

export interface MapFeature {
  type: "Feature";
  id: number;
  geometry: {
    type: string;
    coordinates: unknown;
  };
  properties: MapFeatureProperties;
}

export interface MapFeatureCollection {
  type: "FeatureCollection";
  features: MapFeature[];
  total: number;
  limit: number;
  offset: number;
}

export interface MapFeatureSummaryItem {
  feature_type: string;
  subtype?: string | null;
  records: number;
}

export interface MapFeatureSummaryResponse {
  items: MapFeatureSummaryItem[];
}

export interface TwinCatalogItem {
  asset_code: string;
  name: string;
  asset_type: string;
  subtype?: string | null;
  district?: string | null;
  identity_status: string;
  fidelity_level: string;
  is_asset_specific: boolean;
  has_model_uri: boolean;
  has_source: boolean;
  dimension_count: number;
  representation: string;
  template: string;
  model_source: string;
  source_url?: string | null;
  source_backed: boolean;
  twin_quality_score: number;
  twin_quality: "EXCELLENT" | "READY" | "PARTIAL" | "BASIC";
  twin_group: "BEST" | "IMPROVING" | "BASIC";
  twin_quality_label: string;
}

export interface TwinCatalogResponse {
  items: TwinCatalogItem[];
  counts: {
    best: number;
    improving: number;
    basic: number;
    total: number;
  };
}