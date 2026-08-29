"""Add government evidence tables.

Revision ID: 0004_government_evidence
Revises: 0003_asset_twin_metadata
Create Date: 2026-08-29
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0004_government_evidence"
down_revision = "0003_asset_twin_metadata"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================================
    # Source documents
    # ========================================================

    op.create_table(
        "source_documents",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey(
                "data_sources.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),

        sa.Column(
            "agency",
            sa.String(length=200),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "document_type",
            sa.String(length=80),
            nullable=False,
        ),

        sa.Column(
            "document_url",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "source_record_id",
            sa.String(length=200),
            nullable=True,
        ),

        sa.Column(
            "published_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "retrieved_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "checksum",
            sa.String(length=128),
            nullable=True,
        ),

        sa.Column(
            "licence",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "raw_uri",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "metadata_json",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),

        sa.Column(
            "quality_flag",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'UNVERIFIED'"),
        ),

        sa.Column(
            "is_authoritative",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),

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
    )

    op.create_index(
        "ix_source_documents_source_id",
        "source_documents",
        ["source_id"],
    )

    op.create_index(
        "ix_source_documents_agency",
        "source_documents",
        ["agency"],
    )

    op.create_index(
        "ix_source_documents_document_type",
        "source_documents",
        ["document_type"],
    )

    op.create_index(
        "ix_source_documents_source_record_id",
        "source_documents",
        ["source_record_id"],
    )

    op.create_index(
        "ix_source_documents_published_at",
        "source_documents",
        ["published_at"],
    )

    op.create_index(
        "ix_source_documents_retrieved_at",
        "source_documents",
        ["retrieved_at"],
    )

    op.create_index(
        "ix_source_documents_quality_flag",
        "source_documents",
        ["quality_flag"],
    )

    op.create_index(
        "ix_source_documents_is_authoritative",
        "source_documents",
        ["is_authoritative"],
    )

    op.create_index(
        "ix_source_documents_agency_type",
        "source_documents",
        ["agency", "document_type"],
    )

    # ========================================================
    # Official evidence
    # ========================================================

    op.create_table(
        "official_evidence",

        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),

        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey(
                "assets.id",
                ondelete="CASCADE",
            ),
            nullable=True,
        ),

        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey(
                "source_documents.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        ),

        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey(
                "data_sources.id",
                ondelete="RESTRICT",
            ),
            nullable=False,
        ),

        sa.Column(
            "evidence_type",
            sa.String(length=100),
            nullable=False,
        ),

        sa.Column(
            "field_name",
            sa.String(length=120),
            nullable=False,
        ),

        sa.Column(
            "numeric_value",
            sa.Float(),
            nullable=True,
        ),

        sa.Column(
            "text_value",
            sa.Text(),
            nullable=True,
        ),

        sa.Column(
            "unit",
            sa.String(length=50),
            nullable=True,
        ),

        sa.Column(
            "rating_system",
            sa.String(length=100),
            nullable=True,
        ),

        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "valid_from",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "valid_to",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "authority_level",
            sa.String(length=30),
            nullable=False,
            server_default=sa.text("'UNKNOWN'"),
        ),

        sa.Column(
            "origin",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'OFFICIAL_REPORTED'"),
        ),

        sa.Column(
            "quality_flag",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'UNVERIFIED'"),
        ),

        sa.Column(
            "confidence_score",
            sa.Float(),
            nullable=True,
        ),

        sa.Column(
            "is_official",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),

        sa.Column(
            "is_derived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),

        sa.Column(
            "is_synthetic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),

        sa.Column(
            "processing_method",
            sa.String(length=120),
            nullable=True,
        ),

        sa.Column(
            "extraction_metadata",
            JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),

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
    )

    op.create_index(
        "ix_official_evidence_asset_id",
        "official_evidence",
        ["asset_id"],
    )

    op.create_index(
        "ix_official_evidence_document_id",
        "official_evidence",
        ["document_id"],
    )

    op.create_index(
        "ix_official_evidence_source_id",
        "official_evidence",
        ["source_id"],
    )

    op.create_index(
        "ix_official_evidence_evidence_type",
        "official_evidence",
        ["evidence_type"],
    )

    op.create_index(
        "ix_official_evidence_field_name",
        "official_evidence",
        ["field_name"],
    )

    op.create_index(
        "ix_official_evidence_rating_system",
        "official_evidence",
        ["rating_system"],
    )

    op.create_index(
        "ix_official_evidence_observed_at",
        "official_evidence",
        ["observed_at"],
    )

    op.create_index(
        "ix_official_evidence_authority_level",
        "official_evidence",
        ["authority_level"],
    )

    op.create_index(
        "ix_official_evidence_origin",
        "official_evidence",
        ["origin"],
    )

    op.create_index(
        "ix_official_evidence_quality_flag",
        "official_evidence",
        ["quality_flag"],
    )

    op.create_index(
        "ix_official_evidence_is_official",
        "official_evidence",
        ["is_official"],
    )

    op.create_index(
        "ix_official_evidence_is_synthetic",
        "official_evidence",
        ["is_synthetic"],
    )

    op.create_index(
        "ix_official_evidence_asset_field_time",
        "official_evidence",
        ["asset_id", "field_name", "observed_at"],
    )

    op.create_index(
        "ix_official_evidence_asset_type",
        "official_evidence",
        ["asset_id", "evidence_type"],
    )


def downgrade() -> None:
    op.drop_table("official_evidence")
    op.drop_table("source_documents")
