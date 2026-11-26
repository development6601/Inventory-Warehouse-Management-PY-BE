from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.security import decode_access_token
from app.database.connection import get_db
from app.models import Permission, Role, RolePermission, User, UserWarehouse
from app.models.constants import RoleCode

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class CurrentUser:
    user: User
    role_code: str
    warehouse_id: UUID | None
    permission_names: set[str]

    @property
    def id(self) -> UUID:
        return self.user.id

    @property
    def is_admin(self) -> bool:
        return self.role_code == RoleCode.ADMIN

    @property
    def is_manager(self) -> bool:
        return self.role_code == RoleCode.MANAGER


def get_user_permission_names(db: Session, role_id: UUID) -> set[str]:
    rows = db.scalars(
        select(Permission.name)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    ).all()
    return set(rows)


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(bearer_scheme),
    ],
    db: Annotated[Session, Depends(get_db)],
) -> CurrentUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = UUID(payload["sub"])
    except (PyJWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    user = db.scalar(
        select(User)
        .where(User.id == user_id)
        .options(
            joinedload(User.role),
            joinedload(User.warehouse_assignment).joinedload(
                UserWarehouse.warehouse
            ),
        )
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    warehouse_id = None
    if user.warehouse_assignment is not None:
        warehouse_id = user.warehouse_assignment.warehouse_id

    return CurrentUser(
        user=user,
        role_code=user.role.code,
        warehouse_id=warehouse_id,
        permission_names=get_user_permission_names(db, user.role_id),
    )


def require_permission(permission_name: str) -> Callable:
    def dependency(
        current: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if permission_name not in current.permission_names:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission_name}",
            )
        return current

    return dependency


def get_optional_role_by_code(db: Session, code: str) -> Role | None:
    return db.scalar(select(Role).where(Role.code == code))
