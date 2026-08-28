"""Add statewide source-reported GIS features.

Revision ID: 0002_statewide_map_features
Revises: 0001_initial
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry
from sqlalchemy.dialects.postgresql import JSONB

revision = "0002_statewide_map_features"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "map_features",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("external_id", sa.String(length=200), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=True),
        sa.Column("feature_type", sa.String(length=30), nullable=False),
        sa.Column("subtype", sa.String(length=80), nullable=True),
        sa.Column(
            "geometry",
            Geometry("GEOMETRY", srid=4326, spatial_index=False),
            nullable=False,
        ),
        sa.Column(
            "attributes",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "identity_status",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'SOURCE_REPORTED'"),
        ),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "source_id",
            "feature_type",
            "external_id",
            name="uq_map_features_source_type_external",
        ),
    )
    op.create_index("ix_map_features_feature_type", "map_features", ["feature_type"])
    op.create_index("ix_map_features_subtype", "map_features", ["subtype"])
    op.create_index(
        "ix_map_features_geometry_gist",
        "map_features",
        ["geometry"],
        postgresql_using="gist",
    )


def downgrade() -> None:
    op.drop_index("ix_map_features_geometry_gist", table_name="map_features")
    op.drop_index("ix_map_features_subtype", table_name="map_features")
    op.drop_index("ix_map_features_feature_type", table_name="map_features")
    op.drop_table("map_features")
