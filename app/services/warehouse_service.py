from __future__ import annotations

import re
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import CurrentUser
from app.models import Role, User, UserWarehouse, Warehouse
from app.models.constants import RoleCode
from app.schemas.common import ManagerBrief, MessageResponse
from app.schemas.warehouses import (
    AssignUserRequest,
    AssignedUserResponse,
    WarehouseCreateRequest,
    WarehouseListItem,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseUpdateRequest,
    WarehouseUserItem,
    WarehouseUsersResponse,
)


def _next_warehouse_code(db: Session) -> str:
    codes = db.scalars(select(Warehouse.warehouse_code)).all()
    max_n = 0
    for code in codes:
        match = re.fullmatch(r"[Ww](\d+)", code.strip())
        if match:
            max_n = max(max_n, int(match.group(1)))
    return f"W{max_n + 1}"


def _managers_for_warehouse(db: Session, warehouse_id: UUID) -> list[ManagerBrief]:
    rows = db.execute(
        select(User)
        .join(UserWarehouse, UserWarehouse.user_id == User.id)
        .join(Role, Role.id == User.role_id)
        .where(
            UserWarehouse.warehouse_id == warehouse_id,
            Role.code == RoleCode.MANAGER,
        )
        .order_by(User.name)
    ).scalars().all()
    return [
        ManagerBrief(
            id=u.id,
            name=u.name,
            email=u.email,
            phone=u.phone,
        )
        for u in rows
    ]


def _to_warehouse_response(db: Session, warehouse: Warehouse) -> WarehouseResponse:
    return WarehouseResponse(
        id=warehouse.id,
        warehouse_code=warehouse.warehouse_code,
        name=warehouse.name,
        location=warehouse.location,
        is_active=warehouse.is_active,
        managers=_managers_for_warehouse(db, warehouse.id),
        created_at=warehouse.created_at,
        updated_at=warehouse.updated_at,
    )


def _assert_unique_warehouse_name(
    db: Session,
    name: str,
    *,
    exclude_id: UUID | None = None,
) -> None:
    stmt = select(Warehouse).where(func.lower(Warehouse.name) == name.lower())
    if exclude_id is not None:
        stmt = stmt.where(Warehouse.id != exclude_id)
    existing = db.scalar(stmt)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Warehouse name already exists.",
        )


def create_warehouse(db: Session, payload: WarehouseCreateRequest) -> WarehouseResponse:
    name = payload.name.strip()
    _assert_unique_warehouse_name(db, name)
    warehouse = Warehouse(
        warehouse_code=_next_warehouse_code(db),
        name=name,
        location=payload.location.strip(),
        is_active=True,
    )
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return _to_warehouse_response(db, warehouse)


def list_warehouses(db: Session, current: CurrentUser) -> WarehouseListResponse:
    stmt = select(Warehouse).order_by(Warehouse.warehouse_code)
    if not current.is_admin:
        if current.warehouse_id is None:
            return WarehouseListResponse(items=[], total=0)
        stmt = stmt.where(Warehouse.id == current.warehouse_id)

    warehouses = db.scalars(stmt).all()
    items: list[WarehouseListItem] = []
    for wh in warehouses:
        managers_count = db.scalar(
            select(func.count())
            .select_from(UserWarehouse)
            .join(User, User.id == UserWarehouse.user_id)
            .join(Role, Role.id == User.role_id)
            .where(
                UserWarehouse.warehouse_id == wh.id,
                Role.code == RoleCode.MANAGER,
            )
        )
        items.append(
            WarehouseListItem(
                id=wh.id,
                warehouse_code=wh.warehouse_code,
                name=wh.name,
                location=wh.location,
                is_active=wh.is_active,
                managers_count=managers_count or 0,
            )
        )
    return WarehouseListResponse(items=items, total=len(items))


def get_warehouse(db: Session, current: CurrentUser, warehouse_id: UUID) -> WarehouseResponse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found.",
        )
    if not current.is_admin and current.warehouse_id != warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this warehouse.",
        )
    return _to_warehouse_response(db, warehouse)


def update_warehouse(
    db: Session,
    warehouse_id: UUID,
    payload: WarehouseUpdateRequest,
) -> WarehouseResponse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found.",
        )
    if payload.name is not None:
        name = payload.name.strip()
        _assert_unique_warehouse_name(db, name, exclude_id=warehouse.id)
        warehouse.name = name
    if payload.location is not None:
        warehouse.location = payload.location.strip()
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return _to_warehouse_response(db, warehouse)


def set_warehouse_status(
    db: Session,
    warehouse_id: UUID,
    is_active: bool,
) -> WarehouseResponse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found.",
        )
    warehouse.is_active = is_active
    db.add(warehouse)
    db.commit()
    db.refresh(warehouse)
    return _to_warehouse_response(db, warehouse)


def _resolve_assign_target(db: Session, payload: AssignUserRequest) -> User:
    if payload.user_id is not None:
        user = db.scalar(
            select(User)
            .where(User.id == payload.user_id)
            .options(
                joinedload(User.role),
                joinedload(User.warehouse_assignment),
            )
        )
    else:
        user = db.scalar(
            select(User)
            .where(func.lower(User.email) == str(payload.email).lower())
            .options(
                joinedload(User.role),
                joinedload(User.warehouse_assignment),
            )
        )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )
    return user


def assign_user(
    db: Session,
    current: CurrentUser,
    warehouse_id: UUID,
    payload: AssignUserRequest,
) -> AssignedUserResponse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found.",
        )
    if not warehouse.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign users to an inactive warehouse.",
        )

    if current.is_manager:
        if current.warehouse_id != warehouse_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only assign users to their own warehouse.",
            )
        if payload.role != RoleCode.STAFF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Managers can only assign the STAFF role.",
            )
    elif not current.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to assign users.",
        )

    if payload.role == RoleCode.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot be assigned to a warehouse.",
        )
    if payload.role not in (RoleCode.MANAGER, RoleCode.STAFF):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Allowed values are MANAGER and STAFF.",
        )

    user = _resolve_assign_target(db, payload)
    if user.role.code == RoleCode.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot be assigned to a warehouse.",
        )

    if (
        user.warehouse_assignment is not None
        and user.warehouse_assignment.warehouse_id != warehouse_id
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user is already assigned to another warehouse.",
        )

    role = db.scalar(select(Role).where(Role.code == payload.role))
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="System roles are not configured. Please contact support.",
        )

    user.role_id = role.id
    db.add(user)

    if user.warehouse_assignment is None:
        db.add(
            UserWarehouse(
                user_id=user.id,
                warehouse_id=warehouse_id,
                assigned_by_id=current.id,
            )
        )
    else:
        user.warehouse_assignment.assigned_by_id = current.id
        db.add(user.warehouse_assignment)

    db.commit()

    refreshed = db.scalar(
        select(User)
        .where(User.id == user.id)
        .options(
            joinedload(User.role),
            joinedload(User.warehouse_assignment).joinedload(
                UserWarehouse.warehouse
            ),
        )
    )
    assert refreshed is not None
    wh = refreshed.warehouse_assignment.warehouse if refreshed.warehouse_assignment else None
    return AssignedUserResponse(
        message="User assigned successfully.",
        user={
            "id": str(refreshed.id),
            "email": refreshed.email,
            "role": refreshed.role.code,
            "warehouse_id": str(wh.id) if wh else None,
            "warehouse_code": wh.warehouse_code if wh else None,
        },
    )


def unassign_user(
    db: Session,
    current: CurrentUser,
    warehouse_id: UUID,
    user_id: UUID,
) -> MessageResponse:
    assignment = db.scalar(
        select(UserWarehouse)
        .where(
            UserWarehouse.warehouse_id == warehouse_id,
            UserWarehouse.user_id == user_id,
        )
        .options(joinedload(UserWarehouse.user).joinedload(User.role))
    )
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No assignment found for this user in the selected warehouse.",
        )

    if current.is_manager:
        if current.warehouse_id != warehouse_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "You do not have enough credentials to unassign users "
                    "from another warehouse."
                ),
            )
        if assignment.user.role.code != RoleCode.STAFF:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Managers can only unassign STAFF. "
                    "Ask an Admin to remove a Manager from this warehouse "
                    "(Warehouses → View → Remove)."
                ),
            )
    elif not current.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You do not have enough credentials to unassign users. "
                "Only Admin (any user) or Manager (Staff only) can unassign."
            ),
        )

    role_label = assignment.user.role.code
    db.delete(assignment)
    db.commit()
    return MessageResponse(
        message=(
            f"{role_label} removed from this warehouse successfully. "
            "They are no longer assigned to any warehouse."
        )
    )


def list_warehouse_users(
    db: Session,
    current: CurrentUser,
    warehouse_id: UUID,
) -> WarehouseUsersResponse:
    warehouse = db.get(Warehouse, warehouse_id)
    if warehouse is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Warehouse not found.",
        )
    if not current.is_admin and current.warehouse_id != warehouse_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view users for this warehouse.",
        )

    users = db.scalars(
        select(User)
        .join(UserWarehouse, UserWarehouse.user_id == User.id)
        .where(UserWarehouse.warehouse_id == warehouse_id)
        .options(joinedload(User.role))
        .order_by(User.name)
    ).unique().all()

    items = [
        WarehouseUserItem(
            id=u.id,
            name=u.name,
            email=u.email,
            phone=u.phone,
            role=u.role.code,
        )
        for u in users
    ]
    return WarehouseUsersResponse(items=items, total=len(items))
