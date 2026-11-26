from __future__ import annotations

import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


# At least 8 chars, one uppercase, one lowercase, one digit, one special character
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[^A-Za-z0-9]).{8,}$"
)


def validate_password_value(value: str) -> str:
    if not PASSWORD_PATTERN.match(value):
        raise ValueError(
            "Password must be at least 8 characters and include "
            "one uppercase letter, one lowercase letter, one number, "
            "and one special character"
        )
    return value


class MessageResponse(BaseModel):
    message: str


class WarehouseBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warehouse_code: str
    name: str
    location: str


class ManagerBrief(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: str


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    phone: str
    address: str | None = None
    joining_date: date
    role: str
    role_name: str
    is_active: bool
    last_login_at: datetime | None = None
    warehouse_id: UUID | None = None
    warehouse_code: str | None = None
    warehouse: WarehouseBrief | None = None


class TokenUserSummary(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: str
    role: str
    role_name: str
    warehouse_id: UUID | None = None
    warehouse_code: str | None = None
    is_active: bool


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: TokenUserSummary


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
