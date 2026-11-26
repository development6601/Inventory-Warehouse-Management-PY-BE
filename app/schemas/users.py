from __future__ import annotations

from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import UserPublic, validate_password_value


class AdminCreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    password: str
    role: Literal["MANAGER", "STAFF"]
    warehouse_id: UUID
    joining_date: date | None = None
    address: str | None = None

    @field_validator("password")
    @classmethod
    def password_rules(cls, value: str) -> str:
        return validate_password_value(value)

    @field_validator("name", "phone")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class UserStatusRequest(BaseModel):
    is_active: bool


class UserListResponse(BaseModel):
    items: list[UserPublic]
    total: int


class UserStatusResponse(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
