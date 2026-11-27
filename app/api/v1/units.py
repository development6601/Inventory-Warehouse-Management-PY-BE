from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, require_permission
from app.schemas.units import UnitListResponse
from app.services import unit_service

router = APIRouter(prefix="/units", tags=["Units"])


@router.get("", response_model=UnitListResponse)
def list_units(
    _: Annotated[CurrentUser, Depends(require_permission("unit.list"))],
):
    return unit_service.list_units()
