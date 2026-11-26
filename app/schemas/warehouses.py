from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, model_validator

from app.schemas.common import ManagerBrief


class WarehouseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    location: str = Field(min_length=1)


class WarehouseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    location: str | None = Field(default=None, min_length=1)


class WarehouseStatusRequest(BaseModel):
    is_active: bool


class WarehouseResponse(BaseModel):
    id: UUID
    warehouse_code: str
    name: str
    location: str
    is_active: bool
    managers: list[ManagerBrief] = []
    created_at: datetime
    updated_at: datetime


class WarehouseListItem(BaseModel):
    id: UUID
    warehouse_code: str
    name: str
    location: str
    is_active: bool
    managers_count: int = 0


class WarehouseListResponse(BaseModel):
    items: list[WarehouseListItem]
    total: int


class AssignUserRequest(BaseModel):
    role: Literal["MANAGER", "STAFF"]
    user_id: UUID | None = None
    email: EmailStr | None = None

    @model_validator(mode="after")
    def require_user_identity(self) -> AssignUserRequest:
        if self.user_id is None and self.email is None:
            raise ValueError("Either user_id or email is required")
        if self.user_id is not None and self.email is not None:
            raise ValueError("Provide only one of user_id or email")
        return self


class AssignedUserResponse(BaseModel):
    message: str
    user: dict


class WarehouseUserItem(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    phone: str
    role: str


class WarehouseUsersResponse(BaseModel):
    items: list[WarehouseUserItem]
    total: int
