"""Add missing current model fields without rewriting historical migrations.

Revision ID: 0007_bootstrap_contract
Revises: 0006
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007_bootstrap_contract"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Older installations have the full asset_id model; some later local
    # installations have only asset_code/source_url. Preserve rows in both.
    existing = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("asset_models")}
    columns = [
        sa.Column("asset_code", sa.String(100), nullable=True),
        sa.Column("asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("model_uri", sa.Text(), nullable=True),
        sa.Column("format", sa.String(30), nullable=False, server_default="procedural"),
        sa.Column("version", sa.String(40), nullable=False, server_default="1"),
        sa.Column("fidelity_level", sa.String(10), nullable=False, server_default="L0"),
        sa.Column("model_source", sa.String(200), nullable=False, server_default="procedural"),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("dimensions", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("capture_date", sa.Date(), nullable=True),
        sa.Column("horizontal_accuracy_m", sa.Float(), nullable=True),
        sa.Column("heading_deg", sa.Float(), nullable=True),
        sa.Column("elevation_m", sa.Float(), nullable=True),
        sa.Column("checksum", sa.String(100), nullable=True),
        sa.Column("is_asset_specific", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    ]
    for column in columns:
        if column.name not in existing:
            op.add_column("asset_models", column)
    for column in ("asset_code", "asset_id"):
        if not any(i["column_names"] == [column] for i in sa.inspect(op.get_bind()).get_indexes("asset_models")):
            op.create_index(f"ix_asset_models_{column}", "asset_models", [column])
    if "login_count" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}:
        op.add_column("users", sa.Column("login_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    raise RuntimeError("This additive compatibility migration is forward-only; preserve existing data")
