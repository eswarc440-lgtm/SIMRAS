from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class DataSource(Base, TimestampMixin):
    __tablename__ = "data_sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    organisation: Mapped[str | None] = mapped_column(String(200))
    source_type: Mapped[str] = mapped_column(String(50))
    url: Mapped[str | None] = mapped_column(Text)
    licence: Mapped[str | None] = mapped_column(String(200))
    refresh_policy: Mapped[str | None] = mapped_column(String(120))
    is_authoritative: Mapped[bool] = mapped_column(Boolean, default=False)


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(250), index=True)
    asset_type: Mapped[str] = mapped_column(String(30), index=True)
    subtype: Mapped[str | None] = mapped_column(String(80))
    district: Mapped[str | None] = mapped_column(String(120), index=True)
    owner: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")
    identity_status: Mapped[str] = mapped_column(String(30), default="NEEDS_VERIFICATION")
    built_year: Mapped[int | None] = mapped_column(Integer)
    design_life_years: Mapped[int | None] = mapped_column(Integer)
    material: Mapped[str | None] = mapped_column(String(100))
    condition: Mapped[str | None] = mapped_column(String(30))
    representative_geometry: Mapped[Any] = mapped_column(
        Geometry("POINT", srid=4326, spatial_index=False), nullable=False
    )
    source_id: Mapped[int | None] = mapped_column(ForeignKey("data_sources.id"))
    confidence_score: Mapped[float | None] = mapped_column(Float)
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)

    source: Mapped[DataSource | None] = relationship()
    identifiers: Mapped[list[AssetIdentifier]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )
    models: Mapped[list[AssetModel]] = relationship(
        back_populates="asset", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_assets_representative_geometry_gist", "representative_geometry", postgresql_using="gist"),
    )


class AssetIdentifier(Base):
    __tablename__ = "asset_identifiers"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    external_id: Mapped[str] = mapped_column(String(200))
    external_name: Mapped[str | None] = mapped_column(String(250))
    match_method: Mapped[str] = mapped_column(String(50), default="MANUAL")
    match_confidence: Mapped[float | None] = mapped_column(Float)

    asset: Mapped[Asset] = relationship(back_populates="identifiers")
    source: Mapped[DataSource] = relationship()

    __table_args__ = (UniqueConstraint("source_id", "external_id"),)


class AssetComponent(Base):
    __tablename__ = "asset_components"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    parent_component_id: Mapped[int | None] = mapped_column(ForeignKey("asset_components.id"))
    component_type: Mapped[str] = mapped_column(String(80))
    name: Mapped[str] = mapped_column(String(160))
    material: Mapped[str | None] = mapped_column(String(100))
    attributes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class AssetGeometry(Base):
    __tablename__ = "asset_geometries"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    geometry: Mapped[Any] = mapped_column(Geometry("GEOMETRY", srid=4326, spatial_index=False))
    geometry_type: Mapped[str] = mapped_column(String(30))
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    accuracy_m: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        Index("ix_asset_geometries_geometry_gist", "geometry", postgresql_using="gist"),
    )


class AssetModel(Base, TimestampMixin):
    __tablename__ = "asset_models"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    model_uri: Mapped[str | None] = mapped_column(Text)
    format: Mapped[str] = mapped_column(String(30), default="procedural")
    version: Mapped[str] = mapped_column(String(40), default="1")
    fidelity_level: Mapped[str] = mapped_column(String(10), default="L0")
    model_source: Mapped[str] = mapped_column(String(200), default="procedural")
    capture_date: Mapped[date | None] = mapped_column(Date)
    horizontal_accuracy_m: Mapped[float | None] = mapped_column(Float)
    heading_deg: Mapped[float | None] = mapped_column(Float)
    elevation_m: Mapped[float | None] = mapped_column(Float)
    checksum: Mapped[str | None] = mapped_column(String(100))
    is_asset_specific: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    asset: Mapped[Asset] = relationship(back_populates="models")


class Inspection(Base, TimestampMixin):
    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    inspection_date: Mapped[date] = mapped_column(Date, index=True)
    inspection_type: Mapped[str] = mapped_column(String(80))
    condition: Mapped[str] = mapped_column(String(30))
    score: Mapped[float | None] = mapped_column(Float)
    inspector: Mapped[str | None] = mapped_column(String(160))
    notes: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    quality_flag: Mapped[str] = mapped_column(String(30), default="UNVERIFIED")
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class Defect(Base, TimestampMixin):
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    inspection_id: Mapped[int] = mapped_column(ForeignKey("inspections.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("asset_components.id"))
    defect_type: Mapped[str] = mapped_column(String(80))
    severity: Mapped[str] = mapped_column(String(30))
    measurement: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    geometry: Mapped[Any | None] = mapped_column(Geometry("GEOMETRY", srid=4326))
    image_uri: Mapped[str | None] = mapped_column(Text)
    verification_status: Mapped[str] = mapped_column(String(30), default="CANDIDATE")


class Maintenance(Base, TimestampMixin):
    __tablename__ = "maintenance"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    component_id: Mapped[int | None] = mapped_column(ForeignKey("asset_components.id"))
    maintenance_date: Mapped[date] = mapped_column(Date)
    action: Mapped[str] = mapped_column(Text)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(30), default="COMPLETED")
    next_due: Mapped[date | None] = mapped_column(Date)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False)


class Sensor(Base, TimestampMixin):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    sensor_code: Mapped[str] = mapped_column(String(120), unique=True)
    observed_property: Mapped[str] = mapped_column(String(120))
    unit: Mapped[str] = mapped_column(String(40))
    location: Mapped[Any | None] = mapped_column(Geometry("POINT", srid=4326))
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), default="ACTIVE")


class Observation(Base):
    __tablename__ = "observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int] = mapped_column(ForeignKey("sensors.id", ondelete="CASCADE"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value: Mapped[float] = mapped_column(Float)
    quality_flag: Mapped[str] = mapped_column(String(30), default="VALID")
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EnvironmentObservation(Base):
    __tablename__ = "environment_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    variable: Mapped[str] = mapped_column(String(100), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(40))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    source_type: Mapped[str] = mapped_column(String(50))
    spatial_method: Mapped[str | None] = mapped_column(String(100))
    quality_flag: Mapped[str] = mapped_column(String(30), default="VALID")
    confidence_score: Mapped[float | None] = mapped_column(Float)
    is_estimated: Mapped[bool] = mapped_column(Boolean, default=False)

    __table_args__ = (Index("ix_environment_asset_variable_time", "asset_id", "variable", "observed_at"),)


class RemoteSensingObservation(Base):
    __tablename__ = "remote_sensing_observations"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    scene_id: Mapped[str] = mapped_column(String(200))
    sensor: Mapped[str] = mapped_column(String(80))
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    metric: Mapped[str] = mapped_column(String(80))
    value: Mapped[float | None] = mapped_column(Float)
    raster_uri: Mapped[str | None] = mapped_column(Text)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))


class StateSnapshot(Base):
    __tablename__ = "state_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    state_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    health_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    environment_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    operational_state: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)


class ModelRegistry(Base, TimestampMixin):
    __tablename__ = "model_registry"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_name: Mapped[str] = mapped_column(String(160))
    version: Mapped[str] = mapped_column(String(80))
    training_dataset: Mapped[str] = mapped_column(Text)
    feature_version: Mapped[str] = mapped_column(String(80))
    metrics: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    stage: Mapped[str] = mapped_column(String(30), default="EXPERIMENTAL")
    artifact_uri: Mapped[str | None] = mapped_column(Text)
    checksum: Mapped[str | None] = mapped_column(String(100))

    __table_args__ = (UniqueConstraint("model_name", "version"),)


class Prediction(Base):
    __tablename__ = "predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    prediction_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    target: Mapped[str] = mapped_column(String(50))
    value: Mapped[float | None] = mapped_column(Float)
    predicted_class: Mapped[str | None] = mapped_column(String(30))
    lower_bound: Mapped[float | None] = mapped_column(Float)
    upper_bound: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    model_version: Mapped[str] = mapped_column(String(120))
    feature_version: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="DECISION_SUPPORT")
    factors: Mapped[list[str]] = mapped_column(JSONB, default=list)

    __table_args__ = (Index("ix_predictions_asset_target_time", "asset_id", "target", "prediction_time"),)


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_id: Mapped[int] = mapped_column(ForeignKey("assets.id", ondelete="CASCADE"), index=True)
    severity: Mapped[str] = mapped_column(String(30), index=True)
    rule: Mapped[str] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text)
    created_at_event: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IngestionRun(Base):
    __tablename__ = "ingestion_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline: Mapped[str] = mapped_column(String(160))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_sources.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))
    records_in: Mapped[int] = mapped_column(Integer, default=0)
    records_loaded: Mapped[int] = mapped_column(Integer, default=0)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0)
    checksum: Mapped[str | None] = mapped_column(String(100))
    error_summary: Mapped[str | None] = mapped_column(Text)

