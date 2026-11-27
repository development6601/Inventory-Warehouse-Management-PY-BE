from __future__ import annotations

from pydantic import BaseModel


class UnitItem(BaseModel):
    code: str
    name: str
    abbreviation: str
    label: str


class UnitListResponse(BaseModel):
    items: list[UnitItem]
    total: int
