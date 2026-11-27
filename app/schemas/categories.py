from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Category name is required.")
        return cleaned

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Category name cannot be empty.")
        return cleaned

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> CategoryUpdateRequest:
        if self.name is None and self.description is None:
            raise ValueError("Provide at least one field to update.")
        return self


class CategoryStatusRequest(BaseModel):
    is_active: bool


class CategoryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    products_count: int = 0
    created_at: datetime
    updated_at: datetime


class CategoryListItem(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    products_count: int = 0


class CategoryListResponse(BaseModel):
    items: list[CategoryListItem]
    total: int
    page: int = 1
    page_size: int = 20
