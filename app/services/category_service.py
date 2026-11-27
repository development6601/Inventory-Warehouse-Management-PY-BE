from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Category, Product
from app.schemas.categories import (
    CategoryCreateRequest,
    CategoryListItem,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdateRequest,
)


def _products_count(db: Session, category_id: UUID) -> int:
    return (
        db.scalar(
            select(func.count())
            .select_from(Product)
            .where(Product.category_id == category_id)
        )
        or 0
    )


def _to_response(db: Session, category: Category) -> CategoryResponse:
    return CategoryResponse(
        id=category.id,
        name=category.name,
        description=category.description,
        is_active=category.is_active,
        products_count=_products_count(db, category.id),
        created_at=category.created_at,
        updated_at=category.updated_at,
    )


def _get_category_or_404(db: Session, category_id: UUID) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )
    return category


def _assert_unique_name(
    db: Session,
    name: str,
    *,
    exclude_id: UUID | None = None,
) -> None:
    stmt = select(Category).where(func.lower(Category.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Category.id != exclude_id)
    existing = db.scalar(stmt)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category name already exists.",
        )


def create_category(db: Session, payload: CategoryCreateRequest) -> CategoryResponse:
    _assert_unique_name(db, payload.name)
    category = Category(
        name=payload.name,
        description=payload.description,
        is_active=True,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return _to_response(db, category)


def list_categories(
    db: Session,
    *,
    is_active: bool | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> CategoryListResponse:
    filters = []
    if is_active is not None:
        filters.append(Category.is_active.is_(is_active))
    if q:
        filters.append(Category.name.ilike(f"%{q.strip()}%"))

    count_stmt = select(func.count()).select_from(Category)
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    stmt = select(Category).order_by(Category.name).offset(offset).limit(page_size)
    if filters:
        stmt = stmt.where(*filters)

    categories = db.scalars(stmt).all()
    items = [
        CategoryListItem(
            id=category.id,
            name=category.name,
            description=category.description,
            is_active=category.is_active,
            products_count=_products_count(db, category.id),
        )
        for category in categories
    ]
    return CategoryListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def get_category(db: Session, category_id: UUID) -> CategoryResponse:
    category = _get_category_or_404(db, category_id)
    return _to_response(db, category)


def update_category(
    db: Session,
    category_id: UUID,
    payload: CategoryUpdateRequest,
) -> CategoryResponse:
    category = _get_category_or_404(db, category_id)
    data = payload.model_dump(exclude_unset=True)

    if "name" in data and data["name"] is not None:
        _assert_unique_name(db, data["name"], exclude_id=category.id)
        category.name = data["name"]
    if "description" in data:
        category.description = data["description"]

    db.add(category)
    db.commit()
    db.refresh(category)
    return _to_response(db, category)


def set_category_status(
    db: Session,
    category_id: UUID,
    is_active: bool,
) -> CategoryResponse:
    category = _get_category_or_404(db, category_id)
    category.is_active = is_active
    db.add(category)
    db.commit()
    db.refresh(category)
    return _to_response(db, category)
