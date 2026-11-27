"""Seed RBAC and Module 2 sample catalog data.

Does NOT create an Admin user. Use:
  python -m app.scripts.createsuperuser

Usage:
  python -m app.scripts.seed
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.db.seed_data import (
    PERMISSIONS,
    ROLE_PERMISSION_MAP,
    ROLES,
    SAMPLE_CATEGORIES,
    SAMPLE_PRODUCTS,
)
from app.models import (
    Category,
    Permission,
    Product,
    ProductImage,
    Role,
    RolePermission,
    Warehouse,
)


def _upsert_roles(db: Session) -> dict[str, Role]:
    roles_by_code: dict[str, Role] = {}
    for item in ROLES:
        role = db.scalar(select(Role).where(Role.code == item["code"]))
        if role is None:
            role = Role(
                code=item["code"],
                name=item["name"],
                description=item["description"],
            )
            db.add(role)
        else:
            role.name = item["name"]
            role.description = item["description"]
        roles_by_code[item["code"]] = role
    db.flush()
    return roles_by_code


def _upsert_permissions(db: Session) -> dict[str, Permission]:
    permissions_by_name: dict[str, Permission] = {}
    for item in PERMISSIONS:
        permission = db.scalar(
            select(Permission).where(Permission.name == item["name"])
        )
        if permission is None:
            permission = Permission(
                name=item["name"],
                module=item["module"],
                action=item["action"],
                description=item["description"],
            )
            db.add(permission)
        else:
            permission.module = item["module"]
            permission.action = item["action"]
            permission.description = item["description"]
        permissions_by_name[item["name"]] = permission
    db.flush()
    return permissions_by_name


def _upsert_role_permissions(
    db: Session,
    roles_by_code: dict[str, Role],
    permissions_by_name: dict[str, Permission],
) -> int:
    created = 0
    for role_code, permission_names in ROLE_PERMISSION_MAP.items():
        role = roles_by_code[role_code]
        for permission_name in permission_names:
            permission = permissions_by_name[permission_name]
            existing = db.scalar(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == permission.id,
                )
            )
            if existing is None:
                db.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=permission.id,
                    )
                )
                created += 1
    db.flush()
    return created


def _prune_removed_permissions(db: Session) -> int:
    """Delete permissions (and links) that are no longer in the catalog."""
    allowed_names = {item["name"] for item in PERMISSIONS}
    stale = db.scalars(
        select(Permission).where(Permission.name.not_in(allowed_names))
    ).all()
    removed = 0
    for permission in stale:
        db.execute(
            delete(RolePermission).where(
                RolePermission.permission_id == permission.id
            )
        )
        db.delete(permission)
        removed += 1
    db.flush()
    return removed


def seed_rbac(db: Session) -> None:
    roles_by_code = _upsert_roles(db)
    permissions_by_name = _upsert_permissions(db)
    links_created = _upsert_role_permissions(
        db,
        roles_by_code,
        permissions_by_name,
    )
    pruned = _prune_removed_permissions(db)
    db.commit()
    print(f"Roles upserted: {len(roles_by_code)}")
    print(f"Permissions upserted: {len(permissions_by_name)}")
    print(f"Role-permission links created this run: {links_created}")
    print(f"Stale permissions pruned: {pruned}")
    for code, role in roles_by_code.items():
        n = db.scalar(
            select(func.count())
            .select_from(RolePermission)
            .where(RolePermission.role_id == role.id)
        )
        print(f"  {code}: {n} permissions")


def seed_sample_catalog(db: Session) -> None:
    """Idempotent sample categories/products for verifying Module 2 tables."""
    categories_by_name: dict[str, Category] = {}
    created_categories = 0
    for item in SAMPLE_CATEGORIES:
        category = db.scalar(
            select(Category).where(func.lower(Category.name) == item["name"].lower())
        )
        if category is None:
            category = Category(
                name=item["name"],
                description=item["description"],
                is_active=True,
            )
            db.add(category)
            db.flush()
            created_categories += 1
        categories_by_name[item["name"]] = category

    warehouse = db.scalar(
        select(Warehouse).order_by(Warehouse.warehouse_code.asc()).limit(1)
    )
    if warehouse is None:
        warehouse = Warehouse(
            warehouse_code="W1",
            name="Main Warehouse",
            location="Head Office",
            is_active=True,
        )
        db.add(warehouse)
        db.flush()
        print("Sample warehouse created: W1 — Main Warehouse")

    created_products = 0
    for item in SAMPLE_PRODUCTS:
        existing = db.scalar(
            select(Product).where(
                Product.warehouse_id == warehouse.id,
                func.lower(Product.sku) == item["sku"].lower(),
            )
        )
        if existing is not None:
            continue

        category = categories_by_name.get(item["category_name"])
        if category is None:
            category = db.scalar(
                select(Category).where(
                    func.lower(Category.name) == item["category_name"].lower()
                )
            )
        if category is None:
            raise RuntimeError(
                f"Sample category missing for product {item['sku']}: "
                f"{item['category_name']}"
            )

        product = Product(
            warehouse_id=warehouse.id,
            category_id=category.id,
            unit_code=item["unit_code"],
            sku=item["sku"],
            name=item["name"],
            description=item.get("description"),
            minimum_stock_threshold=Decimal(item["minimum_stock_threshold"]),
            price=Decimal(item["price"]) if item.get("price") is not None else None,
            is_active=True,
        )
        db.add(product)
        db.flush()

        for index, url in enumerate(item["image_urls"]):
            db.add(
                ProductImage(
                    product_id=product.id,
                    image_url=url,
                    is_primary=(index == 0),
                    sort_order=index,
                )
            )
        created_products += 1

    db.commit()
    print(f"Sample categories created this run: {created_categories}")
    print(f"Sample products created this run: {created_products}")
    print(f"Categories total: {db.scalar(select(func.count()).select_from(Category))}")
    print(f"Products total: {db.scalar(select(func.count()).select_from(Product))}")
    print(
        f"Product images total: "
        f"{db.scalar(select(func.count()).select_from(ProductImage))}"
    )


def main() -> None:
    db = SessionLocal()
    try:
        seed_rbac(db)
        print("RBAC seed completed (no admin user created).")
        seed_sample_catalog(db)
        print("Sample catalog seed completed.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
