from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_permission
from app.database.connection import get_db
from app.schemas.common import MessageResponse
from app.schemas.warehouses import (
    AssignUserRequest,
    AssignedUserResponse,
    WarehouseCreateRequest,
    WarehouseListResponse,
    WarehouseResponse,
    WarehouseStatusRequest,
    WarehouseUpdateRequest,
    WarehouseUsersResponse,
)
from app.services import warehouse_service

router = APIRouter(prefix="/warehouses", tags=["Warehouses"])


@router.post("", response_model=WarehouseResponse, status_code=201)
def create_warehouse(
    payload: WarehouseCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("warehouse.create"))],
):
    return warehouse_service.create_warehouse(db, payload)


@router.get("", response_model=WarehouseListResponse)
def list_warehouses(
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("warehouse.list"))],
):
    return warehouse_service.list_warehouses(db, current)


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(
    warehouse_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[CurrentUser, Depends(require_permission("warehouse.view"))],
):
    return warehouse_service.get_warehouse(db, current, warehouse_id)


@router.patch("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: UUID,
    payload: WarehouseUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("warehouse.update"))],
):
    return warehouse_service.update_warehouse(db, warehouse_id, payload)


@router.patch("/{warehouse_id}/status", response_model=WarehouseResponse)
def set_warehouse_status(
    warehouse_id: UUID,
    payload: WarehouseStatusRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[CurrentUser, Depends(require_permission("warehouse.status"))],
):
    return warehouse_service.set_warehouse_status(
        db,
        warehouse_id,
        payload.is_active,
    )


@router.post("/{warehouse_id}/assign", response_model=AssignedUserResponse)
def assign_user(
    warehouse_id: UUID,
    payload: AssignUserRequest,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[
        CurrentUser,
        Depends(require_permission("user.assign_warehouse")),
    ],
):
    return warehouse_service.assign_user(db, current, warehouse_id, payload)


@router.delete(
    "/{warehouse_id}/assign/{user_id}",
    response_model=MessageResponse,
)
def unassign_user(
    warehouse_id: UUID,
    user_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[
        CurrentUser,
        Depends(require_permission("user.assign_warehouse")),
    ],
):
    return warehouse_service.unassign_user(db, current, warehouse_id, user_id)


@router.get("/{warehouse_id}/users", response_model=WarehouseUsersResponse)
def list_warehouse_users(
    warehouse_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    current: Annotated[
        CurrentUser,
        Depends(require_permission("warehouse.list_users")),
    ],
):
    return warehouse_service.list_warehouse_users(db, current, warehouse_id)
