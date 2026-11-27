from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_permission
from app.database.connection import get_db
from app.schemas.categories import (
    CategoryCreateRequest,
    CategoryListResponse,
    CategoryResponse,
    CategoryStatusRequest,
    CategoryUpdateRequest,
)
from app.services import category_service

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    payload: CategoryCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("category.create"))],
):
    return category_service.create_category(db, payload)


@router.get("", response_model=CategoryListResponse)
def list_categories(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("category.list"))],
    is_active: Annotated[
        bool | None,
        Query(description="Filter by status. true = active only, false = inactive only."),
    ] = None,
    q: Annotated[
        str | None,
        Query(
            max_length=150,
            description=(
                "Search text. Matches category name (partial, case-insensitive). "
                "Example: q=grain returns categories whose name contains 'grain'."
            ),
            examples=["Grains", "oil"],
        ),
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (starts at 1).")] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="How many rows to return per page (max 100)."),
    ] = 20,
):
    return category_service.list_categories(
        db,
        is_active=is_active,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("category.view"))],
):
    return category_service.get_category(db, category_id)


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: UUID,
    payload: CategoryUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("category.update"))],
):
    return category_service.update_category(db, category_id, payload)


@router.patch("/{category_id}/status", response_model=CategoryResponse)
def set_category_status(
    category_id: UUID,
    payload: CategoryStatusRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("category.status"))],
):
    return category_service.set_category_status(db, category_id, payload.is_active)
