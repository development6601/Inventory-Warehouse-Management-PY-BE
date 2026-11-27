from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.database.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.product_image import ProductImage
    from app.models.user import User
    from app.models.warehouse import Warehouse


class Product(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "products"

    warehouse_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("warehouses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    unit_code: Mapped[str] = mapped_column(String(10), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    minimum_stock_threshold: Mapped[Decimal] = mapped_column(
        Numeric(14, 3),
        nullable=False,
        default=Decimal("0"),
        server_default="0",
    )
    price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_by_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    warehouse: Mapped[Warehouse] = relationship()
    category: Mapped[Category] = relationship(back_populates="products")
    created_by: Mapped[User | None] = relationship(foreign_keys=[created_by_id])
    images: Mapped[list[ProductImage]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="ProductImage.sort_order",
    )

    __table_args__ = (
        Index(
            "uq_products_warehouse_sku_lower",
            "warehouse_id",
            func.lower(sku),
            unique=True,
        ),
        CheckConstraint(
            "unit_code IN ('G', 'KG', 'L', 'UNIT')",
            name="ck_products_unit_code",
        ),
        CheckConstraint(
            "minimum_stock_threshold >= 0",
            name="ck_products_minimum_stock_threshold",
        ),
        CheckConstraint(
            "price IS NULL OR price >= 0",
            name="ck_products_price",
        ),
    )

    def __repr__(self) -> str:
        return f"<Product sku={self.sku!r}>"
