from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_permission
from app.database.connection import get_db
from app.schemas.products import (
    ProductCreateRequest,
    ProductImageMutationResponse,
    ProductImagesAddRequest,
    ProductListResponse,
    ProductResponse,
    ProductStatusRequest,
    ProductUpdateRequest,
    ProductUnitCode,
)
from app.services import product_service

router = APIRouter(prefix="/products", tags=["Products"])


@router.post("", response_model=ProductResponse, status_code=201)
def create_product(
    payload: ProductCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.create"))],
):
    return product_service.create_product(db, current, payload)


@router.get("", response_model=ProductListResponse)
def list_products(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.list"))],
    is_active: Annotated[
        bool | None,
        Query(description="Filter by status. true = active only, false = inactive only."),
    ] = None,
    category_id: Annotated[
        UUID | None,
        Query(description="Filter by category UUID."),
    ] = None,
    category_name: Annotated[
        str | None,
        Query(
            max_length=150,
            description="Filter by exact category name (case-insensitive).",
            examples=["Grains"],
        ),
    ] = None,
    unit_code: Annotated[
        ProductUnitCode | None,
        Query(description="Filter by unit: G, KG, L, or UNIT."),
    ] = None,
    warehouse_code: Annotated[
        str | None,
        Query(
            max_length=30,
            description=(
                "Filter by warehouse code (W1, W2, …). "
                "Admin can filter any warehouse. "
                "Manager/Staff only see their own warehouse."
            ),
            examples=["W1"],
        ),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            max_length=255,
            description=(
                "Search text. Matches product SKU or product name "
                "(partial, case-insensitive). "
                "Example: q=RICE finds SKU/name containing 'RICE'."
            ),
            examples=["RICE", "oil"],
        ),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (starts at 1).")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="How many rows to return per page (max 100)."),
    ] = 20,
):
    return product_service.list_products(
        db,
        current,
        is_active=is_active,
        category_id=category_id,
        category_name=category_name,
        unit_code=unit_code.value if unit_code else None,
        warehouse_code=warehouse_code,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/by-sku/{sku}", response_model=ProductResponse)
def get_product_by_sku(
    sku: str,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.view"))],
    warehouse_code: Annotated[
        str | None,
        Query(
            max_length=30,
            description="Disambiguate SKU by warehouse code (W1, W2, …).",
        ),
    ] = None,
):
    return product_service.get_product_by_sku(
        db,
        current,
        sku,
        warehouse_code=warehouse_code,
    )


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.view"))],
):
    return product_service.get_product(db, current, product_id)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: UUID,
    payload: ProductUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.update"))],
):
    return product_service.update_product(db, current, product_id, payload)


@router.patch("/{product_id}/status", response_model=ProductResponse)
def set_product_status(
    product_id: UUID,
    payload: ProductStatusRequest,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.status"))],
):
    return product_service.set_product_status(
        db,
        current,
        product_id,
        payload.is_active,
    )


@router.post(
    "/{product_id}/images",
    response_model=ProductImageMutationResponse,
)
def add_product_images(
    product_id: UUID,
    payload: ProductImagesAddRequest,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.update"))],
):
    return product_service.add_product_images(db, current, product_id, payload)


@router.delete(
    "/{product_id}/images/{image_id}",
    response_model=ProductImageMutationResponse,
)
def delete_product_image(
    product_id: UUID,
    image_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.update"))],
):
    return product_service.delete_product_image(db, current, product_id, image_id)


@router.patch(
    "/{product_id}/images/{image_id}/primary",
    response_model=ProductImageMutationResponse,
)
def set_primary_image(
    product_id: UUID,
    image_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("product.update"))],
):
    return product_service.set_primary_image(db, current, product_id, image_id)
