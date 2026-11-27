from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import CurrentUser
from app.core.security import hash_password
from app.models import Role, User, UserWarehouse, Warehouse
from app.models.constants import RoleCode
from app.schemas.users import (
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    UserListResponse,
    UserStatusResponse,
)
from app.services.user_serializers import serialize_user


def _load_user(db: Session, user_id: UUID) -> User | None:
    return db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            joinedload(User.role),
            joinedload(User.warehouse_assignment).joinedload(
                UserWarehouse.warehouse
            ),
        )
    )


def _get_role(db: Session, code: str) -> Role:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System roles are not configured. Please contact support.",
        )
    return role


def _get_warehouse_by_code(db: Session, warehouse_code: str) -> Warehouse:
    warehouse = db.scalar(
        select(Warehouse).where(
            func.lower(Warehouse.warehouse_code) == warehouse_code.lower()
        )
    )
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Warehouse '{warehouse_code}' not found. "
                "Use a short code such as W1, W2, or W3."
            ),
        )
    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign users to an inactive warehouse.",
        )
    return warehouse


def admin_create_user(db: Session, payload: AdminCreateUserRequest):
    if payload.role == RoleCode.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Admin accounts cannot be created through this API. "
            ),
        )
    if payload.role not in (RoleCode.MANAGER, RoleCode.STAFF):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Allowed values are MANAGER and STAFF.",
        )

    existing = db.scalar(
        select(User).where(func.lower(User.email) == str(payload.email).lower())
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )

    warehouse = _get_warehouse_by_code(db, payload.warehouse_code)
    role = _get_role(db, payload.role)
    user = User(
        role_id=role.id,
        name=payload.name.strip(),
        email=str(payload.email).lower(),
        phone=payload.phone.strip(),
        address=payload.address,
        password_hash=hash_password(payload.password),
        joining_date=payload.joining_date or date.today(),
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(
        UserWarehouse(
            user_id=user.id,
            warehouse_id=warehouse.id,
        )
    )
    db.commit()
    created = _load_user(db, user.id)
    assert created is not None
    return serialize_user(created)


def list_users(db: Session) -> UserListResponse:
    users = db.scalars(
        select(User)
        .options(
            joinedload(User.role),
            joinedload(User.warehouse_assignment).joinedload(
                UserWarehouse.warehouse
            ),
        )
        .order_by(User.created_at.desc())
    ).unique().all()
    items = [serialize_user(u) for u in users]
    return UserListResponse(items=items, total=len(items))


def get_user(db: Session, current: CurrentUser, user_id: UUID):
    user = _load_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if current.is_admin or current.id == user_id:
        return serialize_user(user)

    if current.is_manager and current.warehouse_id is not None:
        target_wh = (
            user.warehouse_assignment.warehouse_id
            if user.warehouse_assignment
            else None
        )
        if target_wh == current.warehouse_id:
            return serialize_user(user)

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "You do not have enough credentials to view this user. "
            "Managers may only view users in their own warehouse."
        ),
    )


def admin_update_user(
    db: Session,
    user_id: UUID,
    payload: AdminUpdateUserRequest,
):
    """Admin-only update. Role/warehouse changes keep the one-warehouse rule."""
    user = _load_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide at least one field to update.",
        )

    if user.role.code == RoleCode.ADMIN and (
        "role" in data or "warehouse_code" in data
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot change role or warehouse through this API.",
        )

    if "name" in data and data["name"] is not None:
        user.name = data["name"]
    if "phone" in data and data["phone"] is not None:
        user.phone = data["phone"]
    if "address" in data:
        user.address = data["address"]
    if "joining_date" in data and data["joining_date"] is not None:
        user.joining_date = data["joining_date"]

    if "role" in data and data["role"] is not None:
        new_role = data["role"]
        if new_role == RoleCode.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot assign ADMIN role through this API.",
            )
        if new_role not in (RoleCode.MANAGER, RoleCode.STAFF):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid role. Allowed values are MANAGER and STAFF.",
            )
        user.role_id = _get_role(db, new_role).id

    if "warehouse_code" in data and data["warehouse_code"] is not None:
        warehouse = _get_warehouse_by_code(db, data["warehouse_code"])
        if user.warehouse_assignment is None:
            db.add(
                UserWarehouse(
                    user_id=user.id,
                    warehouse_id=warehouse.id,
                )
            )
        elif user.warehouse_assignment.warehouse_id != warehouse.id:
            # One warehouse only: move by replacing assignment
            db.delete(user.warehouse_assignment)
            db.flush()
            db.add(
                UserWarehouse(
                    user_id=user.id,
                    warehouse_id=warehouse.id,
                )
            )

    db.add(user)
    db.commit()
    updated = _load_user(db, user.id)
    assert updated is not None
    return serialize_user(updated)


def set_user_status(
    db: Session,
    current: CurrentUser,
    user_id: UUID,
    is_active: bool,
) -> UserStatusResponse:
    if current.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own account status.",
        )

    user = _load_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.is_active = is_active
    db.add(user)
    db.commit()
    return UserStatusResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
    )
