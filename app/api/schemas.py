"""Pydantic request/response schemas for the API."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


# ── Auth ────────────────────────────────────────────────────────────
class RegisterParentRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=120)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: UUID
    email: EmailStr
    role: str
    full_name: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# ── Children ────────────────────────────────────────────────────────
class ChildCreateRequest(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    birthdate: date
    grade: int | None = Field(default=None, ge=0, le=12)
    locale: str = "hy-AM"
    preferences: dict = Field(default_factory=dict)


class ChildOut(BaseModel):
    id: UUID
    display_name: str
    birthdate: date
    grade: int | None
    locale: str
    preferences: dict
    created_at: datetime

    model_config = {"from_attributes": True}
