export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export interface GeometryPoint {
  type: "Point";
  coordinates: [number, number];
}

export interface AssetSummary {
  asset_code: string;
  name: string;
  asset_type: string;
  category?: string | null;
  type?: string | null;
  last_inspection_date?: string | null;
  subtype?: string | null;
  district?: string | null;
  identity_status: string;
  condition?: string | null;
  geometry?: GeometryPoint | null;
  latitude?: number | string | null;
  longitude?: number | string | null;
  coordinates?: {
    latitude?: number | string | null;
    longitude?: number | string | null;
  } | null;
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
  health_score?: number | null;
  remaining_useful_life_years?: number | null;
  dimension_authority?: string | null;
  assessment_basis?: string | null;
}

export interface StructuralSensor {
  id: string;
  name: string;
  type: "PIEZOMETER" | "STRAIN_GAUGE" | "INCLINOMETER" | "SCOUR_SENSOR" | "CRACK_GAUGE" | "VIBRATION" | "SURFACE_FRICTION";
  value: number;
  unit: string;
  threshold: number;
  status: "NORMAL" | "WARNING" | "CRITICAL";
  position: [number, number, number];
}

export interface TelemetryFeedRecord {
  asset_code: string;
  last_sync: string;
  sources: string[];
  water_level_m: number;
  max_water_level_m: number;
  storage_percent: number;
  storage_tmc?: number;
  inflow_cusecs: number;
  outflow_cusecs: number;
  gates_open: number;
  total_gates: number;
  gate_clearance_m: number;
  weather: {
    condition: "CLEAR" | "OVERCAST" | "RAIN" | "MONSOON_STORM";
    precipitation_mm_hr: number;
    wind_speed_kmh: number;
    temperature_c: number;
  };
  structural_sensors: StructuralSensor[];
  history_24h: Array<{
    time: string;
    water_level_m: number;
    inflow_cusecs: number;
    outflow_cusecs: number;
    strain_microstrain?: number;
  }>;
}

export interface CitizenHazardObservationRecord {
  id: string;
  asset_code: string;
  asset_name: string;
  reporter_name: string;
  reporter_phone?: string;
  observation_type: "WATER_OVERFLOW" | "DEBRIS_JAM" | "STRUCTURAL_CRACK" | "EROSION_SCOUR" | "GATE_MALFUNCTION" | "SURFACE_POTHOLE";
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  description: string;
  coordinates_3d: [number, number, number];
  verified_by_officer: boolean;
  reported_at: string;
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
    operational_risk_score?: number | null;
    operational_risk_level?: RiskLevel | null;
    operational_confidence?: number | null;
    operational_method?: string | null;
    operational_status?: string | null;
    remaining_life_years?: number | null;
    rul_lower_bound?: number | null;
    rul_upper_bound?: number | null;
    rul_confidence?: number | null;
    rul_status?: string | null;
    rul_basis?: string | null;
    rul_basis_url?: string | null;
    rul_method?: string | null;
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
