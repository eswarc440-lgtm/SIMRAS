"""GIS registry DDL from migration 0002, also available to pristine bootstrap."""
from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Index, String, Table, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base import Base


map_features = Table(
    "map_features", Base.metadata,
    Column("id", BigInteger, primary_key=True),
    Column("source_id", ForeignKey("data_sources.id", ondelete="RESTRICT"), nullable=False),
    Column("external_id", String(200), nullable=False),
    Column("name", String(250)),
    Column("feature_type", String(30), nullable=False),
    Column("subtype", String(80)),
    Column("geometry", Geometry("GEOMETRY", srid=4326, spatial_index=False), nullable=False),
    Column("attributes", JSONB, nullable=False, server_default=text("'{}'::jsonb")),
    Column("identity_status", String(30), nullable=False, server_default="SOURCE_REPORTED"),
    Column("confidence_score", Float),
    Column("retrieved_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    Column("updated_at", DateTime(timezone=True), nullable=False, server_default=text("now()")),
    UniqueConstraint("source_id", "feature_type", "external_id", name="uq_map_features_source_type_external"),
    Index("ix_map_features_feature_type", "feature_type"),
    Index("ix_map_features_subtype", "subtype"),
    Index("ix_map_features_geometry_gist", "geometry", postgresql_using="gist"),
)
