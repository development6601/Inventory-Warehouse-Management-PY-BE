from __future__ import annotations

from app.models.constants import UnitCode
from app.schemas.units import UnitItem, UnitListResponse


def list_units() -> UnitListResponse:
    items = [
        UnitItem(
            code=code,
            name=UnitCode.NAMES[code],
            abbreviation=UnitCode.ABBREVIATIONS[code],
            label=UnitCode.LABELS[code],
        )
        for code in UnitCode.ALL
    ]
    return UnitListResponse(items=items, total=len(items))
