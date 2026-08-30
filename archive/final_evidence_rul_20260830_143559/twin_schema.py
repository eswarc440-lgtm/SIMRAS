from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GeometryPoint(BaseModel):
    type: str = "Point"
    coordinates: tuple[float, float]


class AssetSummary(BaseModel):
    asset_code: str
    name: str
    asset_type: str
    subtype: str | None = None
    district: str | None = None
    identity_status: str
    condition: str | None = None
    geometry: GeometryPoint
    risk_score: float | None = None
    risk_level: str | None = None
    data_confidence: float | None = None


class AssetListResponse(BaseModel):
    items: list[AssetSummary]
    total: int
    limit: int
    offset: int


class SourceValue(BaseModel):
    value: float | str | None
    unit: str | None = None
    source: str
    source_type: str
    observed_at: datetime | date | None = None
    ingested_at: datetime | None = None
    quality_flag: str
    confidence: float | None = Field(default=None, ge=0, le=1)
    is_estimated: bool = False


class ModelMetadata(BaseModel):
    format: str
    uri: str | None = None
    version: str
    fidelity_level: str
    model_source: str
    source_url: str | None = None
    dimensions: dict[str, Any] = Field(default_factory=dict)
    is_asset_specific: bool
    heading_deg: float | None = None
    elevation_m: float | None = None
    horizontal_accuracy_m: float | None = None


class InspectionState(BaseModel):
    inspection_date: date | None = None
    condition: str | None = None
    score: float | None = None
    quality_flag: str = "NOT_AVAILABLE"
    is_synthetic: bool = False


class PredictionState(BaseModel):
    health_score: float | None = None
    health_lower_bound: float | None = None
    health_upper_bound: float | None = None
    risk_score: float | None = None
    risk_level: str | None = None
    hazard_score: float | None = None
    hazard_level: str | None = None
    remaining_life_years: float | None = None
    rul_lower_bound: float | None = None
    rul_upper_bound: float | None = None
    confidence: float | None = None
    model_version: str
    feature_version: str
    prediction_time: datetime
    status: str
    prediction_method: str = "unknown"
    model_validated: bool = False
    training_scope: str = "UNKNOWN"
    forecast_horizon_years: int | None = None
    factors: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class TwinResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    asset: AssetSummary
    static: dict[str, Any]
    twin: ModelMetadata
    environment: dict[str, SourceValue]
    inspection: InspectionState
    maintenance: list[dict[str, Any]]
    sensors_status: str
    ai: PredictionState
    freshness: dict[str, str]
    generated_at: datetime


class GeoJSONFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict[str, Any]]


class HealthResponse(BaseModel):
    status: str
    service: str
    database: str
    checked_at: datetime
