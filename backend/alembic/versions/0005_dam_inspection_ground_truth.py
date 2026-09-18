"""Add dam inspection ground-truth tables.

Revision ID: 0005_dam_inspection_ground_truth
Revises: 0004_government_evidence
Create Date: 2026-09-18
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision = "0005_dam_inspection_ground_truth"
down_revision = "0004_government_evidence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "dam_inspection_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "asset_id",
            sa.Integer(),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("asset_name_reported", sa.String(length=250), nullable=False),
        sa.Column(
            "document_id",
            sa.Integer(),
            sa.ForeignKey("source_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_id",
            sa.Integer(),
            sa.ForeignKey("data_sources.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("inspection_date", sa.Date(), nullable=True),
        sa.Column("inspection_type", sa.String(length=80), nullable=True),
        sa.Column("inspection_category", sa.String(length=20), nullable=True),
        sa.Column("overall_condition", sa.String(length=80), nullable=True),
        sa.Column("inspector_agency", sa.String(length=200), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("source_page", sa.String(length=80), nullable=True),
        sa.Column(
            "authority_level",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'UNKNOWN'"),
        ),
        sa.Column(
            "quality_flag",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'UNVERIFIED'"),
        ),
        sa.Column(
            "is_official",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_synthetic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "training_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "label_scope",
            sa.String(length=80),
            nullable=False,
            server_default=sa.text("'INSPECTION_EVENT'"),
        ),
        sa.Column(
            "metadata_json",
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

    op.create_index("ix_dam_inspection_events_asset_id", "dam_inspection_events", ["asset_id"])
    op.create_index(
        "ix_dam_inspection_events_asset_name_reported",
        "dam_inspection_events",
        ["asset_name_reported"],
    )
    op.create_index("ix_dam_inspection_events_document_id", "dam_inspection_events", ["document_id"])
    op.create_index("ix_dam_inspection_events_source_id", "dam_inspection_events", ["source_id"])
    op.create_index("ix_dam_inspection_events_inspection_date", "dam_inspection_events", ["inspection_date"])
    op.create_index("ix_dam_inspection_events_inspection_type", "dam_inspection_events", ["inspection_type"])
    op.create_index(
        "ix_dam_inspection_events_inspection_category",
        "dam_inspection_events",
        ["inspection_category"],
    )
    op.create_index("ix_dam_inspection_events_overall_condition", "dam_inspection_events", ["overall_condition"])
    op.create_index("ix_dam_inspection_events_authority_level", "dam_inspection_events", ["authority_level"])
    op.create_index("ix_dam_inspection_events_quality_flag", "dam_inspection_events", ["quality_flag"])
    op.create_index("ix_dam_inspection_events_is_official", "dam_inspection_events", ["is_official"])
    op.create_index("ix_dam_inspection_events_is_synthetic", "dam_inspection_events", ["is_synthetic"])
    op.create_index("ix_dam_inspection_events_training_eligible", "dam_inspection_events", ["training_eligible"])
    op.create_index("ix_dam_inspection_events_label_scope", "dam_inspection_events", ["label_scope"])
    op.create_index(
        "ix_dam_inspection_events_asset_date",
        "dam_inspection_events",
        ["asset_id", "inspection_date"],
    )
    op.create_index(
        "ix_dam_inspection_events_training",
        "dam_inspection_events",
        ["training_eligible", "inspection_category"],
    )

    op.create_table(
        "dam_inspection_findings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "inspection_id",
            sa.Integer(),
            sa.ForeignKey("dam_inspection_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("component_name", sa.String(length=120), nullable=False),
        sa.Column("condition_state", sa.String(length=80), nullable=True),
        sa.Column("deficiency_type", sa.String(length=120), nullable=True),
        sa.Column("severity", sa.String(length=40), nullable=True),
        sa.Column("finding_text", sa.Text(), nullable=True),
        sa.Column("recommended_action", sa.Text(), nullable=True),
        sa.Column("source_page", sa.String(length=80), nullable=True),
        sa.Column(
            "quality_flag",
            sa.String(length=40),
            nullable=False,
            server_default=sa.text("'UNVERIFIED'"),
        ),
        sa.Column(
            "is_official",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "is_synthetic",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "metadata_json",
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
        "ix_dam_inspection_findings_inspection_id",
        "dam_inspection_findings",
        ["inspection_id"],
    )
    op.create_index(
        "ix_dam_inspection_findings_component_name",
        "dam_inspection_findings",
        ["component_name"],
    )
    op.create_index(
        "ix_dam_inspection_findings_condition_state",
        "dam_inspection_findings",
        ["condition_state"],
    )
    op.create_index(
        "ix_dam_inspection_findings_deficiency_type",
        "dam_inspection_findings",
        ["deficiency_type"],
    )
    op.create_index("ix_dam_inspection_findings_severity", "dam_inspection_findings", ["severity"])
    op.create_index("ix_dam_inspection_findings_quality_flag", "dam_inspection_findings", ["quality_flag"])
    op.create_index("ix_dam_inspection_findings_is_official", "dam_inspection_findings", ["is_official"])
    op.create_index("ix_dam_inspection_findings_is_synthetic", "dam_inspection_findings", ["is_synthetic"])
    op.create_index(
        "ix_dam_inspection_findings_event_component",
        "dam_inspection_findings",
        ["inspection_id", "component_name"],
    )


def downgrade() -> None:
    op.drop_table("dam_inspection_findings")
    op.drop_table("dam_inspection_events")
