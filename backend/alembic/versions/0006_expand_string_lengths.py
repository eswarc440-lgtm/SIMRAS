"""expand string lengths for fidelity_level and condition

Revision ID: 0006_expand_string_lengths
Revises: 0005_dam_inspection_ground_truth
Create Date: 2026-09-22 13:40:00.000000

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "0006_expand_string_lengths"
down_revision = "0005_dam_inspection_ground_truth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    # Check asset_models.fidelity_level
    if "asset_models" in inspector.get_table_names():
        op.alter_column(
            "asset_models",
            "fidelity_level",
            existing_type=sa.String(length=10),
            type_=sa.String(length=50),
            existing_nullable=False,
        )

    # Check assets.condition
    if "assets" in inspector.get_table_names():
        op.alter_column(
            "assets",
            "condition",
            existing_type=sa.String(length=30),
            type_=sa.String(length=100),
            existing_nullable=True,
        )


def downgrade() -> None:
    op.alter_column(
        "assets",
        "condition",
        existing_type=sa.String(length=100),
        type_=sa.String(length=30),
        existing_nullable=True,
    )
    op.alter_column(
        "asset_models",
        "fidelity_level",
        existing_type=sa.String(length=50),
        type_=sa.String(length=10),
        existing_nullable=False,
    )
