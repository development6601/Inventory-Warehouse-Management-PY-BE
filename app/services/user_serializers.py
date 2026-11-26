from __future__ import annotations

from app.models import User
from app.schemas.common import TokenUserSummary, UserPublic, WarehouseBrief


def serialize_user(user: User) -> UserPublic:
    assignment = user.warehouse_assignment
    warehouse = assignment.warehouse if assignment else None
    return UserPublic(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        address=user.address,
        joining_date=user.joining_date,
        role=user.role.code,
        role_name=user.role.name,
        is_active=user.is_active,
        last_login_at=user.last_login_at,
        warehouse_id=warehouse.id if warehouse else None,
        warehouse_code=warehouse.warehouse_code if warehouse else None,
        warehouse=(
            WarehouseBrief(
                id=warehouse.id,
                warehouse_code=warehouse.warehouse_code,
                name=warehouse.name,
                location=warehouse.location,
            )
            if warehouse
            else None
        ),
    )


def serialize_token_user(user: User) -> TokenUserSummary:
    assignment = user.warehouse_assignment
    warehouse = assignment.warehouse if assignment else None
    return TokenUserSummary(
        id=user.id,
        name=user.name,
        email=user.email,
        phone=user.phone,
        role=user.role.code,
        role_name=user.role.name,
        warehouse_id=warehouse.id if warehouse else None,
        warehouse_code=warehouse.warehouse_code if warehouse else None,
        is_active=user.is_active,
    )
