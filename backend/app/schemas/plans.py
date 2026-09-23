from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class PlanCreate(BaseModel):
    asset_code: str = Field(..., max_length=50)
    plan_type: str = Field(..., max_length=50)
    title: str = Field(..., max_length=300)
    description: str | None = Field(None, max_length=2000)
    priority: str = Field(default="MEDIUM", max_length=30)
    problem_identified: str | None = Field(None, max_length=2000)
    evidence: str | None = Field(None, max_length=2000)
    proposed_action: str | None = Field(None, max_length=2000)
    affected_components: list[str] | None = None
    proposed_start: datetime | None = None
    proposed_end: datetime | None = None
    estimated_cost: int | None = Field(None, ge=0)
    department: str | None = Field(None, max_length=200)


class PlanResponse(BaseModel):
    id: int
    plan_number: str
    asset_id: int
    asset_code: str
    plan_type: str
    title: str
    description: str | None
    priority: str
    problem_identified: str | None
    evidence: str | None
    proposed_action: str | None
    affected_components: list[str] | None
    proposed_start: datetime | None
    proposed_end: datetime | None
    estimated_cost: int | None
    department: str | None
    status: str
    created_by: int
    reviewed_by: int | None
    approved_by: int | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
