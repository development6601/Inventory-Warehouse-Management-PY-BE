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
from app.schemas.users import AdminCreateUserRequest, UserListResponse, UserStatusResponse
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
            detail=f"Role {code} is not seeded",
        )
    return role


def admin_create_user(db: Session, payload: AdminCreateUserRequest):
    if payload.role not in (RoleCode.MANAGER, RoleCode.STAFF):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be MANAGER or STAFF",
        )

    existing = db.scalar(
        select(User).where(func.lower(User.email) == str(payload.email).lower())
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    warehouse = db.get(Warehouse, payload.warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found",
        )
    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign users to an inactive warehouse",
        )

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
            detail="User not found",
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
        detail="Permission denied",
    )


def set_user_status(
    db: Session,
    current: CurrentUser,
    user_id: UUID,
    is_active: bool,
) -> UserStatusResponse:
    if current.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own active status",
        )

    user = _load_user(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.is_active = is_active
    db.add(user)
    db.commit()
    return UserStatusResponse(
        id=user.id,
        email=user.email,
        is_active=user.is_active,
    )
