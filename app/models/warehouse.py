from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user_warehouse import UserWarehouse


class Warehouse(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warehouses"

    warehouse_code: Mapped[str] = mapped_column(String(30), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    assignments: Mapped[list[UserWarehouse]] = relationship(
        back_populates="warehouse",
    )

    __table_args__ = (
        Index(
            "uq_warehouses_code_lower",
            func.lower(warehouse_code),
            unique=True,
        ),
        Index(
            "uq_warehouses_name_lower",
            func.lower(name),
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return f"<Warehouse code={self.warehouse_code!r}>"
