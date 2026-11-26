"""Seed Module 1 roles, permissions, and role_permissions.

Does NOT create an Admin user. Use:
  python -m app.scripts.createsuperuser

Usage:
  python -m app.scripts.seed
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.db.seed_data import PERMISSIONS, ROLE_PERMISSION_MAP, ROLES
from app.models import Permission, Role, RolePermission


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


def seed_rbac(db: Session) -> None:
    roles_by_code = _upsert_roles(db)
    permissions_by_name = _upsert_permissions(db)
    links_created = _upsert_role_permissions(
        db,
        roles_by_code,
        permissions_by_name,
    )
    db.commit()
    print(f"Roles upserted: {len(roles_by_code)}")
    print(f"Permissions upserted: {len(permissions_by_name)}")
    print(f"Role-permission links created this run: {links_created}")
    for code, role in roles_by_code.items():
        n = db.scalar(
            select(func.count())
            .select_from(RolePermission)
            .where(RolePermission.role_id == role.id)
        )
        print(f"  {code}: {n} permissions")


def main() -> None:
    db = SessionLocal()
    try:
        seed_rbac(db)
        print("RBAC seed completed (no admin user created).")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
