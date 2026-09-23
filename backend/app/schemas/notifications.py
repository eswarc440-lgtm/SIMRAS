from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    user_id: int
    notification_type: str = Field(..., max_length=50)
    severity: str = Field(default="INFO", max_length=30)
    title: str = Field(..., max_length=300)
    message: str = Field(..., max_length=2000)
    asset_id: int | None = None
    inspection_id: int | None = None
    maintenance_id: int | None = None
    plan_id: int | None = None
    link: str | None = None


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    notification_type: str
    severity: str
    title: str
    message: str
    asset_id: int | None
    inspection_id: int | None
    maintenance_id: int | None
    plan_id: int | None
    link: str | None
    is_read: bool
    read_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
