from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.deps import CurrentUser
from app.models import Category, Product, ProductImage, Warehouse
from app.models.constants import UnitCode
from app.schemas.products import (
    ProductCreateRequest,
    ProductImageMutationResponse,
    ProductImageResponse,
    ProductImagesAddRequest,
    ProductListItem,
    ProductListResponse,
    ProductResponse,
    ProductUpdateRequest,
)


def _unit_label(unit_code: str) -> str:
    return UnitCode.LABELS.get(unit_code, unit_code)


def _primary_image_url(product: Product) -> str | None:
    for image in product.images:
        if image.is_primary:
            return image.image_url
    if product.images:
        return product.images[0].image_url
    return None


def _to_image_response(image: ProductImage) -> ProductImageResponse:
    return ProductImageResponse(
        id=image.id,
        image_url=image.image_url,
        is_primary=image.is_primary,
        sort_order=image.sort_order,
        created_at=image.created_at,
    )


def _to_product_response(product: Product) -> ProductResponse:
    images = sorted(product.images, key=lambda item: (item.sort_order, str(item.id)))
    return ProductResponse(
        id=product.id,
        warehouse_id=product.warehouse_id,
        warehouse_code=product.warehouse.warehouse_code,
        sku=product.sku,
        name=product.name,
        description=product.description,
        category_id=product.category_id,
        category_name=product.category.name,
        unit_code=product.unit_code,
        unit_label=_unit_label(product.unit_code),
        minimum_stock_threshold=product.minimum_stock_threshold,
        price=product.price,
        is_active=product.is_active,
        images=[_to_image_response(image) for image in images],
        created_by_id=product.created_by_id,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def _product_load_options():
    return (
        joinedload(Product.category),
        joinedload(Product.warehouse),
        selectinload(Product.images),
    )


def _load_product(db: Session, product_id: UUID) -> Product | None:
    return db.scalar(
        select(Product)
        .where(Product.id == product_id)
        .options(*_product_load_options())
    )


def _load_product_by_sku(
    db: Session,
    sku: str,
    *,
    warehouse_id: UUID | None = None,
) -> Product | None:
    stmt = (
        select(Product)
        .where(func.lower(Product.sku) == sku.lower())
        .options(*_product_load_options())
    )
    if warehouse_id is not None:
        stmt = stmt.where(Product.warehouse_id == warehouse_id)
    return db.scalar(stmt)


def _get_product_or_404(db: Session, product_id: UUID) -> Product:
    product = _load_product(db, product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product


def _require_assigned_warehouse(current: CurrentUser) -> UUID:
    if current.warehouse_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have enough credentials for warehouse products yet. "
                "Ask an Admin to assign you to a warehouse, then try again."
            ),
        )
    return current.warehouse_id


def _assert_unit_change_allowed(
    db: Session,
    product_id: UUID,
    current_unit: str,
    new_unit: str,
) -> None:
    """Block unit changes once stock rows exist (Module 4 inventories)."""
    if current_unit == new_unit:
        return
    bind = db.get_bind()
    table_names = set(inspect(bind).get_table_names())
    if "inventories" not in table_names:
        return
    qty = db.execute(
        text(
            "select coalesce(sum(quantity_on_hand), 0) "
            "from inventories where product_id = cast(:pid as uuid)"
        ),
        {"pid": str(product_id)},
    ).scalar()
    if qty and float(qty) > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Cannot change unit while this product has stock in a warehouse. "
                "Clear stock first, or keep the current unit."
            ),
        )


def _resolve_list_warehouse_id(
    db: Session,
    current: CurrentUser,
    warehouse_code: str | None,
) -> UUID | None:
    """Admin may filter by code (or see all). Non-admin is locked to own WH."""
    if current.is_admin:
        if not warehouse_code:
            return None
        warehouse = _get_warehouse_by_code(db, warehouse_code)
        return warehouse.id

    own_id = _require_assigned_warehouse(current)
    if warehouse_code:
        warehouse = _get_warehouse_by_code(db, warehouse_code)
        if warehouse.id != own_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have enough credentials to view another "
                    "warehouse's products. You can only see your own warehouse."
                ),
            )
    return own_id


def _assert_product_access(current: CurrentUser, product: Product) -> None:
    if current.is_admin:
        return
    own_id = _require_assigned_warehouse(current)
    if product.warehouse_id != own_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found in your warehouse.",
        )


def _get_warehouse_by_code(db: Session, warehouse_code: str) -> Warehouse:
    warehouse = db.scalar(
        select(Warehouse).where(
            func.lower(Warehouse.warehouse_code) == warehouse_code.strip().lower()
        )
    )
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Warehouse '{warehouse_code.strip().upper()}' not found. "
                "Use a short code such as W1, W2, or W3."
            ),
        )
    return warehouse


def _assert_unique_sku(
    db: Session,
    warehouse_id: UUID,
    sku: str,
    *,
    exclude_id: UUID | None = None,
) -> None:
    stmt = select(Product).where(
        Product.warehouse_id == warehouse_id,
        func.lower(Product.sku) == sku.lower(),
    )
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    existing = db.scalar(stmt)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU already exists in this warehouse.",
        )


def _resolve_category(
    db: Session,
    *,
    category_id: UUID | None,
    category_name: str | None,
    require_active: bool,
) -> Category:
    if category_id is not None:
        category = db.get(Category, category_id)
    else:
        assert category_name is not None
        category = db.scalar(
            select(Category).where(
                func.lower(Category.name) == category_name.lower()
            )
        )

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found.",
        )
    if require_active and not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category is inactive and cannot be assigned.",
        )
    return category


def create_product(
    db: Session,
    current: CurrentUser,
    payload: ProductCreateRequest,
) -> ProductResponse:
    warehouse = _get_warehouse_by_code(db, payload.warehouse_code)
    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add products to an inactive warehouse.",
        )
    if not current.is_admin:
        own_id = _require_assigned_warehouse(current)
        if warehouse.id != own_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have enough credentials to create products "
                    "for another warehouse. Use your assigned warehouse only."
                ),
            )

    category = _resolve_category(
        db,
        category_id=payload.category_id,
        category_name=payload.category_name,
        require_active=True,
    )
    _assert_unique_sku(db, warehouse.id, payload.sku)

    product = Product(
        warehouse_id=warehouse.id,
        category_id=category.id,
        unit_code=payload.unit_code.value,
        sku=payload.sku,
        name=payload.name,
        description=payload.description,
        minimum_stock_threshold=payload.minimum_stock_threshold,
        price=payload.price,
        is_active=True,
        created_by_id=current.id,
    )
    db.add(product)
    db.flush()

    for index, url in enumerate(payload.image_urls):
        db.add(
            ProductImage(
                product_id=product.id,
                image_url=url,
                is_primary=(index == payload.primary_image_index),
                sort_order=index,
            )
        )

    db.commit()
    return _to_product_response(_get_product_or_404(db, product.id))


def list_products(
    db: Session,
    current: CurrentUser,
    *,
    is_active: bool | None = None,
    category_id: UUID | None = None,
    category_name: str | None = None,
    unit_code: str | None = None,
    warehouse_code: str | None = None,
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> ProductListResponse:
    scoped_warehouse_id = _resolve_list_warehouse_id(db, current, warehouse_code)

    filters = []
    if scoped_warehouse_id is not None:
        filters.append(Product.warehouse_id == scoped_warehouse_id)
    if is_active is not None:
        filters.append(Product.is_active.is_(is_active))
    if category_id is not None:
        filters.append(Product.category_id == category_id)
    if category_name:
        filters.append(func.lower(Category.name) == category_name.strip().lower())
    if unit_code:
        filters.append(Product.unit_code == unit_code.upper())
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(
            (Product.sku.ilike(pattern)) | (Product.name.ilike(pattern))
        )

    count_stmt = (
        select(func.count())
        .select_from(Product)
        .join(Category, Category.id == Product.category_id)
    )
    if filters:
        count_stmt = count_stmt.where(*filters)
    total = db.scalar(count_stmt) or 0

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    stmt = (
        select(Product)
        .join(Category, Category.id == Product.category_id)
        .options(*_product_load_options())
        .order_by(Product.name, Product.sku)
        .offset(offset)
        .limit(page_size)
    )
    if filters:
        stmt = stmt.where(*filters)

    products = db.scalars(stmt).unique().all()
    items = [
        ProductListItem(
            id=product.id,
            warehouse_id=product.warehouse_id,
            warehouse_code=product.warehouse.warehouse_code,
            sku=product.sku,
            name=product.name,
            category_id=product.category_id,
            category_name=product.category.name,
            unit_code=product.unit_code,
            unit_label=_unit_label(product.unit_code),
            minimum_stock_threshold=product.minimum_stock_threshold,
            price=product.price,
            is_active=product.is_active,
            primary_image_url=_primary_image_url(product),
            images_count=len(product.images),
        )
        for product in products
    ]
    return ProductListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


def get_product(
    db: Session,
    current: CurrentUser,
    product_id: UUID,
) -> ProductResponse:
    product = _get_product_or_404(db, product_id)
    _assert_product_access(current, product)
    return _to_product_response(product)


def get_product_by_sku(
    db: Session,
    current: CurrentUser,
    sku: str,
    *,
    warehouse_code: str | None = None,
) -> ProductResponse:
    if current.is_admin:
        warehouse_id = None
        if warehouse_code:
            warehouse_id = _get_warehouse_by_code(db, warehouse_code).id
    else:
        warehouse_id = _require_assigned_warehouse(current)
        if warehouse_code:
            requested = _get_warehouse_by_code(db, warehouse_code)
            if requested.id != warehouse_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "You do not have enough credentials to view another "
                        "warehouse's products."
                    ),
                )

    product = _load_product_by_sku(db, sku.strip(), warehouse_id=warehouse_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    _assert_product_access(current, product)
    return _to_product_response(product)


def update_product(
    db: Session,
    current: CurrentUser,
    product_id: UUID,
    payload: ProductUpdateRequest,
) -> ProductResponse:
    product = _get_product_or_404(db, product_id)
    _assert_product_access(current, product)
    data = payload.model_dump(exclude_unset=True)

    if "sku" in data and data["sku"] is not None:
        _assert_unique_sku(
            db,
            product.warehouse_id,
            data["sku"],
            exclude_id=product.id,
        )
        product.sku = data["sku"]
    if "name" in data and data["name"] is not None:
        product.name = data["name"]
    if "description" in data:
        product.description = data["description"]
    if "unit_code" in data and data["unit_code"] is not None:
        unit = data["unit_code"]
        new_unit = unit.value if hasattr(unit, "value") else unit
        _assert_unit_change_allowed(
            db,
            product.id,
            product.unit_code,
            new_unit,
        )
        product.unit_code = new_unit
    if "minimum_stock_threshold" in data and data["minimum_stock_threshold"] is not None:
        product.minimum_stock_threshold = data["minimum_stock_threshold"]
    if "price" in data:
        product.price = data["price"]

    if "category_id" in data or "category_name" in data:
        category = _resolve_category(
            db,
            category_id=data.get("category_id"),
            category_name=data.get("category_name"),
            require_active=True,
        )
        product.category_id = category.id

    db.add(product)
    db.commit()
    return _to_product_response(_get_product_or_404(db, product_id))


def set_product_status(
    db: Session,
    current: CurrentUser,
    product_id: UUID,
    is_active: bool,
) -> ProductResponse:
    product = _get_product_or_404(db, product_id)
    _assert_product_access(current, product)
    product.is_active = is_active
    db.add(product)
    db.commit()
    return _to_product_response(_get_product_or_404(db, product_id))


def add_product_images(
    db: Session,
    current: CurrentUser,
    product_id: UUID,
    payload: ProductImagesAddRequest,
) -> ProductImageMutationResponse:
    product = _get_product_or_404(db, product_id)
    _assert_product_access(current, product)
    next_order = max((image.sort_order for image in product.images), default=-1) + 1

    created: list[ProductImage] = []
    for offset, url in enumerate(payload.image_urls):
        image = ProductImage(
            product_id=product.id,
            image_url=url,
            is_primary=False,
            sort_order=next_order + offset,
        )
        db.add(image)
        created.append(image)

    db.flush()

    if payload.set_primary_index is not None:
        for image in product.images:
            image.is_primary = False
            db.add(image)
        created[payload.set_primary_index].is_primary = True
        db.add(created[payload.set_primary_index])
    elif not any(image.is_primary for image in product.images):
        created[0].is_primary = True
        db.add(created[0])

    db.commit()
    refreshed = _get_product_or_404(db, product_id)
    return ProductImageMutationResponse(
        message="Image(s) added successfully.",
        product=_to_product_response(refreshed),
    )


def delete_product_image(
    db: Session,
    current: CurrentUser,
    product_id: UUID,
    image_id: UUID,
) -> ProductImageMutationResponse:
    product = _get_product_or_404(db, product_id)
    _assert_product_access(current, product)
    image = next((item for item in product.images if item.id == image_id), None)
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for this product.",
        )
    if len(product.images) <= 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Product must have at least one image.",
        )

    was_primary = image.is_primary
    db.delete(image)
    db.flush()

    remaining = (
        db.scalars(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order, ProductImage.id)
        ).all()
    )
    if was_primary and remaining:
        for item in remaining:
            item.is_primary = False
            db.add(item)
        remaining[0].is_primary = True
        db.add(remaining[0])

    db.commit()
    refreshed = _get_product_or_404(db, product_id)
    return ProductImageMutationResponse(
        message="Image removed successfully.",
        product=_to_product_response(refreshed),
    )


def set_primary_image(
    db: Session,
    current: CurrentUser,
    product_id: UUID,
    image_id: UUID,
) -> ProductImageMutationResponse:
    product = _get_product_or_404(db, product_id)
    _assert_product_access(current, product)
    target = next((item for item in product.images if item.id == image_id), None)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found for this product.",
        )

    for image in product.images:
        image.is_primary = image.id == image_id
        db.add(image)

    db.commit()
    refreshed = _get_product_or_404(db, product_id)
    return ProductImageMutationResponse(
        message="Primary image updated.",
        product=_to_product_response(refreshed),
    )
