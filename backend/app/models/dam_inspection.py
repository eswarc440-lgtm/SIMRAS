from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class DamInspectionEvent(Base, TimestampMixin):
    """One source-backed government/engineer inspection event.

    An event becomes eligible as an ML ground-truth label only after SIMRAS has
    an asset match, an inspection date, an inspection type/category (when the
    source uses one), and a traceable authoritative source document.
    """

    __tablename__ = "dam_inspection_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int | None] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True, nullable=True
    )
    asset_name_reported: Mapped[str] = mapped_column(String(250), index=True)
    document_id: Mapped[int] = mapped_column(
        ForeignKey("source_documents.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[int] = mapped_column(
        ForeignKey("data_sources.id", ondelete="RESTRICT"), index=True
    )
    inspection_date: Mapped[date | None] = mapped_column(Date, index=True)
    inspection_type: Mapped[str | None] = mapped_column(String(80), index=True)
    inspection_category: Mapped[str | None] = mapped_column(String(20), index=True)
    overall_condition: Mapped[str | None] = mapped_column(String(80), index=True)
    inspector_agency: Mapped[str | None] = mapped_column(String(200))
    recommended_action: Mapped[str | None] = mapped_column(Text)
    source_page: Mapped[str | None] = mapped_column(String(80))
    authority_level: Mapped[str] = mapped_column(String(40), default="UNKNOWN", index=True)
    quality_flag: Mapped[str] = mapped_column(String(40), default="UNVERIFIED", index=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    training_eligible: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    label_scope: Mapped[str] = mapped_column(
        String(80), default="INSPECTION_EVENT", index=True
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index(
            "ix_dam_inspection_events_asset_date",
            "asset_id",
            "inspection_date",
        ),
        Index(
            "ix_dam_inspection_events_training",
            "training_eligible",
            "inspection_category",
        ),
    )


class DamInspectionFinding(Base, TimestampMixin):
    """Component/deficiency finding reported inside one inspection event."""

    __tablename__ = "dam_inspection_findings"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(
        ForeignKey("dam_inspection_events.id", ondelete="CASCADE"), index=True
    )
    component_name: Mapped[str] = mapped_column(String(120), index=True)
    condition_state: Mapped[str | None] = mapped_column(String(80), index=True)
    deficiency_type: Mapped[str | None] = mapped_column(String(120), index=True)
    severity: Mapped[str | None] = mapped_column(String(40), index=True)
    finding_text: Mapped[str | None] = mapped_column(Text)
    recommended_action: Mapped[str | None] = mapped_column(Text)
    source_page: Mapped[str | None] = mapped_column(String(80))
    quality_flag: Mapped[str] = mapped_column(String(40), default="UNVERIFIED", index=True)
    is_official: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    __table_args__ = (
        Index(
            "ix_dam_inspection_findings_event_component",
            "inspection_id",
            "component_name",
        ),
    )
