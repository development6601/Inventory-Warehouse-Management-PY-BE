from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from app.models.constants import UnitCode
from app.schemas.common import validate_image_url_value


class ProductUnitCode(str, Enum):
    G = UnitCode.G
    KG = UnitCode.KG
    L = UnitCode.L
    UNIT = UnitCode.UNIT


def _validate_image_url(value: str) -> str:
    return validate_image_url_value(value)


class ProductImageResponse(BaseModel):
    id: UUID
    image_url: str
    is_primary: bool
    sort_order: int
    created_at: datetime


class ProductCreateRequest(BaseModel):
    sku: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    warehouse_code: str = Field(
        min_length=1,
        max_length=30,
        description="Short warehouse code such as W1, W2, W3",
        examples=["W1"],
    )
    category_id: UUID | None = None
    category_name: str | None = Field(default=None, min_length=1, max_length=150)
    unit_code: ProductUnitCode
    minimum_stock_threshold: Decimal = Field(ge=0, max_digits=14, decimal_places=3)
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    image_urls: list[str] = Field(min_length=1)
    primary_image_index: int = Field(default=0, ge=0)

    @field_validator("sku", "name")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field is required.")
        return cleaned

    @field_validator("warehouse_code")
    @classmethod
    def normalize_warehouse_code(cls, value: str) -> str:
        cleaned = value.strip().upper()
        if not cleaned:
            raise ValueError("Warehouse code is required.")
        return cleaned

    @field_validator("category_name")
    @classmethod
    def strip_category_name(cls, value: str | None) -> str | None:
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

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("At least one image URL is required.")
        return [_validate_image_url(url) for url in value]

    @model_validator(mode="after")
    def validate_category_and_primary(self) -> ProductCreateRequest:
        if self.category_id is None and self.category_name is None:
            raise ValueError("Either category_id or category_name is required.")
        if self.category_id is not None and self.category_name is not None:
            raise ValueError("Provide only one of category_id or category_name.")
        if self.primary_image_index >= len(self.image_urls):
            raise ValueError("primary_image_index is out of range for image_urls.")
        return self


class ProductUpdateRequest(BaseModel):
    sku: str | None = Field(default=None, min_length=1, max_length=100)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    category_id: UUID | None = None
    category_name: str | None = Field(default=None, min_length=1, max_length=150)
    unit_code: ProductUnitCode | None = None
    minimum_stock_threshold: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=14,
        decimal_places=3,
    )
    price: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)

    @field_validator("sku", "name")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("This field cannot be empty.")
        return cleaned

    @field_validator("category_name")
    @classmethod
    def strip_category_name(cls, value: str | None) -> str | None:
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
    def validate_update_fields(self) -> ProductUpdateRequest:
        if self.category_id is not None and self.category_name is not None:
            raise ValueError("Provide only one of category_id or category_name.")
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self


class ProductStatusRequest(BaseModel):
    is_active: bool


class ProductImagesAddRequest(BaseModel):
    image_urls: list[str] = Field(min_length=1)
    set_primary_index: int | None = Field(default=None, ge=0)

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, value: list[str]) -> list[str]:
        return [_validate_image_url(url) for url in value]

    @model_validator(mode="after")
    def validate_primary_index(self) -> ProductImagesAddRequest:
        if (
            self.set_primary_index is not None
            and self.set_primary_index >= len(self.image_urls)
        ):
            raise ValueError("set_primary_index is out of range for image_urls.")
        return self


class ProductResponse(BaseModel):
    id: UUID
    warehouse_id: UUID
    warehouse_code: str
    sku: str
    name: str
    description: str | None
    category_id: UUID
    category_name: str
    unit_code: str
    unit_label: str
    minimum_stock_threshold: Decimal
    price: Decimal | None
    is_active: bool
    images: list[ProductImageResponse]
    created_by_id: UUID | None
    created_at: datetime
    updated_at: datetime


class ProductListItem(BaseModel):
    id: UUID
    warehouse_id: UUID
    warehouse_code: str
    sku: str
    name: str
    category_id: UUID
    category_name: str
    unit_code: str
    unit_label: str
    minimum_stock_threshold: Decimal
    price: Decimal | None
    is_active: bool
    primary_image_url: str | None
    images_count: int


class ProductListResponse(BaseModel):
    items: list[ProductListItem]
    total: int
    page: int
    page_size: int


class ProductImageMutationResponse(BaseModel):
    message: str
    product: ProductResponse
