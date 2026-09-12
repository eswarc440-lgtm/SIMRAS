from datetime import date

from pydantic import BaseModel, Field


class InspectionCreate(BaseModel):
    asset_code: str
    inspection_date: date
    inspection_type: str = "GENERAL"
    condition: str
    score: float | None = Field(default=None, ge=0, le=100)
    inspector: str | None = None
    notes: str | None = None
    source_record_id: str | None = None


class MaintenanceCreate(BaseModel):
    asset_code: str
    maintenance_date: date
    action: str
    status: str = "COMPLETED"
    next_due: date | None = None
    cost: float | None = Field(default=None, ge=0)


class AlertCreate(BaseModel):
    asset_code: str
    severity: str = Field(pattern="^(INFO|LOW|MEDIUM|HIGH|CRITICAL)$")
    rule: str
    message: str


class AlertAction(BaseModel):
    action: str = Field(pattern="^(ACKNOWLEDGE|RESOLVE)$")

