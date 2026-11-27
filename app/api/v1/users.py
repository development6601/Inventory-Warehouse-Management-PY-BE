from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_permission
from app.database.connection import get_db
from app.schemas.common import UserPublic
from app.schemas.users import (
    AdminCreateUserRequest,
    AdminUpdateUserRequest,
    UserListResponse,
    UserStatusRequest,
    UserStatusResponse,
)
from app.services import user_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserPublic, status_code=201)
def create_user(
    payload: AdminCreateUserRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("user.create"))],
):
    return user_service.admin_create_user(db, payload)


@router.get("", response_model=UserListResponse)
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("user.list"))],
):
    return user_service.list_users(db)


@router.get("/{user_id}", response_model=UserPublic)
def get_user(
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("user.view"))],
):
    return user_service.get_user(db, current, user_id)


@router.patch("/{user_id}", response_model=UserPublic)
def update_user(
    user_id: UUID,
    payload: AdminUpdateUserRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("user.update"))],
):
    return user_service.admin_update_user(db, user_id, payload)


@router.patch("/{user_id}/status", response_model=UserStatusResponse)
def set_status(
    user_id: UUID,
    payload: UserStatusRequest,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("user.activate"))],
):
    return user_service.set_user_status(db, current, user_id, payload.is_active)
