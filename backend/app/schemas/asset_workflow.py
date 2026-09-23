from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AssetCreate(BaseModel):
    asset_type: str = Field(..., description="DAM, BARRAGE, BRIDGE, AIRPORT, TEMPLE")
    official_name: str = Field(..., min_length=2, max_length=250)
    alternative_name: str | None = Field(None, max_length=250)
    district: str | None = Field(None, max_length=120)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    owning_authority: str | None = Field(None, max_length=200)
    operating_authority: str | None = Field(None, max_length=200)
    construction_year: int | None = Field(None, ge=1800, le=2100)
    commissioning_year: int | None = Field(None, ge=1800, le=2100)
    structure_type: str | None = Field(None, max_length=100)
    source_authority: str | None = Field(None, max_length=200)
    source_url: str | None = Field(None, max_length=500)
    supporting_document: str | None = Field(None, max_length=500)
    remarks: str | None = Field(None, max_length=1000)

    # Category-specific fields
    length: float | None = Field(None, gt=0)
    width: float | None = Field(None, gt=0)
    span_count: int | None = Field(None, gt=0)
    pier_count: int | None = Field(None, gt=0)
    max_span: float | None = Field(None, gt=0)
    material: str | None = Field(None, max_length=100)
    road_rail: str | None = Field(None, max_length=50)
    foundation: str | None = Field(None, max_length=100)

    height: float | None = Field(None, gt=0)
    capacity: float | None = Field(None, gt=0)
    gate_count: int | None = Field(None, gt=0)
    gate_dimensions: str | None = Field(None, max_length=100)
    spillway_capacity: float | None = Field(None, gt=0)
    river: str | None = Field(None, max_length=100)

    runway_length: float | None = Field(None, gt=0)
    runway_width: float | None = Field(None, gt=0)
    runway_heading: float | None = Field(None, ge=0, le=360)
    pcn: str | None = Field(None, max_length=50)
    elevation: float | None = Field(None)

    construction_period: str | None = Field(None, max_length=100)
    authority: str | None = Field(None, max_length=200)
    footprint: float | None = Field(None, gt=0)
    temple_height: float | None = Field(None, gt=0)
    heritage_evidence: str | None = Field(None, max_length=500)


class AssetResponse(BaseModel):
    id: int
    asset_code: str
    name: str
    asset_type: str
    subtype: str | None
    district: str | None
    owner: str | None
    status: str
    identity_status: str
    built_year: int | None
    design_life_years: int | None
    material: str | None
    condition: str | None
    confidence_score: float | None
    is_estimated: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetReviewCreate(BaseModel):
    review_type: str = Field(..., max_length=50)
    inspection_date: datetime | None = None
    condition: str | None = Field(None, max_length=30)
    observation: str | None = Field(None, max_length=2000)
    components_inspected: list[str] | None = None
    recommendation: str | None = Field(None, max_length=2000)
    remarks: str | None = Field(None, max_length=1000)


class AssetReviewResponse(BaseModel):
    id: int
    asset_id: int
    reviewed_by: int
    review_type: str
    inspection_date: datetime | None
    condition: str | None
    observation: str | None
    components_inspected: list[str] | None
    recommendation: str | None
    remarks: str | None
    verification_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetAssignmentCreate(BaseModel):
    assignment_type: str = Field(..., max_length=50)
    assigned_to: int = Field(..., description="User ID to assign")


class AssetAssignmentResponse(BaseModel):
    id: int
    asset_id: int
    user_id: int
    assignment_type: str
    assigned_by: int
    assigned_at: datetime
    is_active: bool

    class Config:
        from_attributes = True
