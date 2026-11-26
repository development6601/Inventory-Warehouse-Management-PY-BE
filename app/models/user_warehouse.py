from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.warehouse import Warehouse


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserWarehouse(Base):
    """Links a user to exactly one warehouse (UNIQUE user_id).

    Staff vs Manager is determined by users.role_id, not this table.
    Multiple Managers per warehouse are allowed.
    """

    __tablename__ = "user_warehouses"
    __table_args__ = (
        UniqueConstraint("user_id", name="uq_user_warehouses_user_id"),
    )

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
    )
    assigned_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utc_now,
        server_default=func.now(),
    )

    user: Mapped[User] = relationship(
        back_populates="warehouse_assignment",
        foreign_keys=[user_id],
    )
    warehouse: Mapped[Warehouse] = relationship(back_populates="assignments")
    assigned_by: Mapped[User | None] = relationship(foreign_keys=[assigned_by_id])
