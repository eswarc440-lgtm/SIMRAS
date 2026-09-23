from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class InspectionCreate(BaseModel):
    asset_code: str = Field(..., max_length=50)
    inspection_date: datetime
    scheduled_date: datetime
    due_date: datetime
    inspection_agency: str | None = Field(None, max_length=200)
    inspection_type: str = Field(..., max_length=50)
    assigned_officer_id: int | None = None
    priority: str = Field(default="MEDIUM", max_length=30)

    # Condition fields
    deck_condition: str | None = Field(None, max_length=30)
    superstructure_condition: str | None = Field(None, max_length=30)
    substructure_condition: str | None = Field(None, max_length=30)
    foundation_condition: str | None = Field(None, max_length=30)
    scour_condition: str | None = Field(None, max_length=30)
    bearing_condition: str | None = Field(None, max_length=30)
    joint_condition: str | None = Field(None, max_length=30)

    overall_condition: str | None = Field(None, max_length=30)
    defect_count: int = Field(default=0, ge=0)
    max_defect_severity: str | None = Field(None, max_length=30)

    observation: str | None = Field(None, max_length=5000)
    recommendation: str | None = Field(None, max_length=5000)


class InspectionUpdate(BaseModel):
    started_date: datetime | None = None
    status: str | None = Field(None, max_length=30)
    deck_condition: str | None = None
    superstructure_condition: str | None = None
    substructure_condition: str | None = None
    foundation_condition: str | None = None
    scour_condition: str | None = None
    bearing_condition: str | None = None
    joint_condition: str | None = None
    overall_condition: str | None = None
    defect_count: int | None = None
    max_defect_severity: str | None = None
    observation: str | None = None
    recommendation: str | None = None


class InspectionResponse(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    inspection_date: datetime
    scheduled_date: datetime
    started_date: datetime | None
    due_date: datetime
    inspection_agency: str | None
    inspection_type: str
    assigned_officer: int | None
    priority: str
    status: str
    deck_condition: str | None
    superstructure_condition: str | None
    substructure_condition: str | None
    foundation_condition: str | None
    scour_condition: str | None
    bearing_condition: str | None
    joint_condition: str | None
    overall_condition: str | None
    defect_count: int
    max_defect_severity: str | None
    observation: str | None
    recommendation: str | None
    created_by: int
    reviewed_by: int | None
    verification_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class InspectionComponentCreate(BaseModel):
    component_name: str = Field(..., max_length=100)
    component_type: str = Field(..., max_length=50)
    condition: str | None = Field(None, max_length=30)
    observation: str | None = Field(None, max_length=2000)
    evidence: dict[str, Any] | None = None


class InspectionDefectCreate(BaseModel):
    component_id: int | None = None
    defect_type: str = Field(..., max_length=80)
    severity: str = Field(..., max_length=30)
    measurement: dict[str, Any] | None = None
    location: str | None = Field(None, max_length=500)
    observation: str | None = Field(None, max_length=2000)
    recommendation: str | None = Field(None, max_length=2000)
