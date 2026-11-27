"""products warehouse scope + unique warehouse names

Revision ID: 20261127_0003
Revises: 20261127_0002
Create Date: 2026-11-27

"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261127_0003"
down_revision: Union[str, Sequence[str], None] = "20261127_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()

    # Deduplicate warehouse names from earlier test data before unique index.
    dup_names = conn.execute(
        sa.text(
            """
            SELECT lower(name) AS n
            FROM warehouses
            GROUP BY lower(name)
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    for (dup_name,) in dup_names:
        rows = conn.execute(
            sa.text(
                """
                SELECT id, warehouse_code
                FROM warehouses
                WHERE lower(name) = :n
                ORDER BY warehouse_code
                """
            ),
            {"n": dup_name},
        ).fetchall()
        for index, (wid, code) in enumerate(rows):
            if index == 0:
                continue
            conn.execute(
                sa.text(
                    """
                    UPDATE warehouses
                    SET name = name || ' (' || :code || ')'
                    WHERE id = :id
                    """
                ),
                {"code": code, "id": wid},
            )

    op.create_index(
        "uq_warehouses_name_lower",
        "warehouses",
        [sa.text("lower(name)")],
        unique=True,
    )

    op.add_column("products", sa.Column("warehouse_id", sa.Uuid(), nullable=True))

    # Backfill existing products onto the first warehouse (by code).
    # If none exists, create a default warehouse so NOT NULL can be applied.
    first_wh = conn.execute(
        sa.text(
            "SELECT id FROM warehouses ORDER BY lower(warehouse_code) ASC LIMIT 1"
        )
    ).scalar()
    if first_wh is None:
        conn.execute(
            sa.text(
                """
                INSERT INTO warehouses (id, warehouse_code, name, location, is_active)
                VALUES (
                    '00000000-0000-4000-8000-000000000001'::uuid,
                    'W1',
                    'Default Warehouse',
                    'Unassigned',
                    true
                )
                """
            )
        )
        first_wh = conn.execute(
            sa.text(
                "SELECT id FROM warehouses ORDER BY lower(warehouse_code) ASC LIMIT 1"
            )
        ).scalar()

    conn.execute(
        sa.text("UPDATE products SET warehouse_id = :wid WHERE warehouse_id IS NULL"),
        {"wid": first_wh},
    )

    op.alter_column("products", "warehouse_id", nullable=False)
    op.create_foreign_key(
        "fk_products_warehouse_id",
        "products",
        "warehouses",
        ["warehouse_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.drop_index("uq_products_sku_lower", table_name="products")
    op.create_index(
        "uq_products_warehouse_sku_lower",
        "products",
        ["warehouse_id", sa.text("lower(sku)")],
        unique=True,
    )
    op.create_index(
        "ix_products_warehouse_id",
        "products",
        ["warehouse_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_products_warehouse_id", table_name="products")
    op.drop_index("uq_products_warehouse_sku_lower", table_name="products")
    op.create_index(
        "uq_products_sku_lower",
        "products",
        [sa.text("lower(sku)")],
        unique=True,
    )
    op.drop_constraint("fk_products_warehouse_id", "products", type_="foreignkey")
    op.drop_column("products", "warehouse_id")
    op.drop_index("uq_warehouses_name_lower", table_name="warehouses")
