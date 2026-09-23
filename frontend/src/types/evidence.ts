export type EvidenceBand =
  | "LOW"
  | "MEDIUM"
  | "HIGH"
  | "CRITICAL"
  | "UNKNOWN";

export type ConditionState =
  | "HEALTHY"
  | "MONITOR"
  | "WEAK"
  | "HIGH_PRIORITY"
  | "CRITICAL"
  | "UNKNOWN";

export interface EvidenceSourceValue {
  value: number | string | null;
  unit?: string | null;
  observed_at?: string | null;
  ingested_at?: string | null;
  source_code?: string | null;
  source?: string | null;
  source_type?: string | null;
  spatial_method?: string | null;
  quality_flag?: string | null;
  confidence?: number | null;
  is_estimated?: boolean;
  freshness?: string | null;
}

export interface StructuralConditionState {
  condition: ConditionState;
  risk: EvidenceBand;
  origin: string;
  authority_level?: string | null;
  rating_system?: string | null;
  observed_at?: string | null;
  confidence?: number | null;
  source?: string | null;
  document?: string | null;
  document_url?: string | null;
  field_name?: string | null;
  evidence_type?: string | null;
  processing_method?: string | null;
  message?: string | null;
}

export interface HazardState {
  value: EvidenceBand;
  score?: number | null;
  origin: string;
  inputs_used: string[];
  note?: string | null;
}

export interface RiskState {
  value: EvidenceBand;
  origin: string;
  message?: string | null;
}

export interface OfficialEvidenceItem {
  id: number;
  evidence_type: string;
  field_name: string;
  numeric_value?: number | null;
  text_value?: string | null;
  unit?: string | null;
  rating_system?: string | null;
  observed_at?: string | null;
  authority_level?: string | null;
  origin?: string | null;
  quality_flag?: string | null;
  confidence_score?: number | null;
  is_official?: boolean;
  is_derived?: boolean;
  processing_method?: string | null;
  agency?: string | null;
  document_title?: string | null;
  document_url?: string | null;
  source_code?: string | null;
  source_name?: string | null;
}

export interface EvidenceStateResponse {
  asset: {
    asset_code: string;
    name: string;
    asset_type: string;
    subtype?: string | null;
    district?: string | null;
    owner?: string | null;
    built_year?: number | null;
    design_life_years?: number | null;
    material?: string | null;
    identity_status: string;
    identity_confidence?: number | null;
    latitude: number;
    longitude: number;
  };
  condition: StructuralConditionState;
  hazard: HazardState;
  risk: RiskState;
  health_score: null;
  risk_score: null;
  rul_years: null;
  forecast_ready: boolean;
  evidence_strength: "HIGH" | "MEDIUM" | "LOW" | "INSUFFICIENT";
  environment: Record<string, EvidenceSourceValue>;
  evidence: OfficialEvidenceItem[];
  governance: Record<string, string>;
  engine: {
    name: string;
    version: string;
    generated_at: string;
  };
}
