from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    officer_id: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    email: EmailStr
    role: str = Field(default="OFFICER")
    department: str | None = None
    designation: str | None = None
    district: str | None = None
    phone: str | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=200)
    phone: str | None = None
    department: str | None = None
    designation: str | None = None
    district: str | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    last_login: datetime | None
    login_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
    expires_at: datetime


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PermissionCheck(BaseModel):
    permission: str
    resource: str | None = None


class RolePermissionResponse(BaseModel):
    role: str
    permission: str
    resource: str | None
    description: str | None

    class Config:
        from_attributes = True
