from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class MaintenanceCreate(BaseModel):
    asset_code: str = Field(..., max_length=50)
    maintenance_type: str = Field(..., max_length=50)
    component: str | None = Field(None, max_length=100)
    priority: str = Field(default="MEDIUM", max_length=30)
    problem: str | None = Field(None, max_length=2000)
    reason: str | None = Field(None, max_length=2000)
    proposed_action: str | None = Field(None, max_length=2000)
    assigned_department: str | None = Field(None, max_length=200)
    contractor: str | None = Field(None, max_length=200)
    estimated_cost: int | None = Field(None, ge=0)
    start_date: datetime | None = None
    due_date: datetime


class MaintenanceUpdate(BaseModel):
    status: str | None = Field(None, max_length=30)
    progress: int | None = Field(None, ge=0, le=100)
    actual_cost: int | None = Field(None, ge=0)
    completion_date: datetime | None = None


class MaintenanceResponse(BaseModel):
    id: int
    asset_id: int
    asset_code: str
    maintenance_type: str
    component: str | None
    priority: str
    status: str
    problem: str | None
    reason: str | None
    proposed_action: str | None
    assigned_department: str | None
    contractor: str | None
    estimated_cost: int | None
    actual_cost: int | None
    start_date: datetime | None
    due_date: datetime
    completion_date: datetime | None
    progress: int
    related_inspection_id: int | None
    related_plan_id: int | None
    created_by: int
    reviewed_by: int | None
    verification_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
