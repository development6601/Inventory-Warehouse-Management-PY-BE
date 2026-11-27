from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.schemas.common import (
    UserPublic,
    validate_password_value,
    validate_phone_value,
)


class AdminCreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    password: str
    # Validated in service so ADMIN gets a clear 400 (not raw schema 422)
    role: str = Field(min_length=1, max_length=30)
    warehouse_code: str = Field(
        min_length=1,
        max_length=30,
        description="Short warehouse code such as W1, W2, W3",
        examples=["W1"],
    )
    joining_date: date | None = None
    address: str | None = None

    @field_validator("password")
    @classmethod
    def password_rules(cls, value: str) -> str:
        return validate_password_value(value)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return value.strip()

    @field_validator("phone")
    @classmethod
    def phone_rules(cls, value: str) -> str:
        return validate_phone_value(value)

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("warehouse_code")
    @classmethod
    def normalize_warehouse_code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Warehouse code is required.")
        return cleaned


class UserStatusRequest(BaseModel):
    is_active: bool


class AdminUpdateUserRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    phone: str | None = Field(default=None, min_length=7, max_length=20)
    address: str | None = None
    joining_date: date | None = None
    role: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description="MANAGER or STAFF only. Admin-only change.",
    )
    warehouse_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=30,
        description="Move user to this warehouse (still one warehouse only).",
        examples=["W1"],
    )

    @field_validator("name")
    @classmethod
    def strip_optional_name(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip()

    @field_validator("phone")
    @classmethod
    def phone_rules(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return validate_phone_value(value)

    @field_validator("role")
    @classmethod
    def normalize_role(cls, value: str | None) -> str | None:
        if value is None:
            return value
        return value.strip().upper()

    @field_validator("warehouse_code")
    @classmethod
    def normalize_warehouse_code(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Warehouse code cannot be empty.")
        return cleaned

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> AdminUpdateUserRequest:
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self


class UserListResponse(BaseModel):
    items: list[UserPublic]
    total: int


class UserStatusResponse(BaseModel):
    id: UUID
    email: EmailStr
    is_active: bool
