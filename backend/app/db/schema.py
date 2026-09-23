"""Explicit schema contract shared by bootstrap, readiness and regression tests.

0001 uses mutable ORM metadata and cannot be replayed on an empty database.
Never use this module to repair existing schemas: those must use Alembic.
"""
from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.db.base import Base
from app.models import entities, operational  # noqa: F401
from app.models import dam_inspection, map_feature  # noqa: F401

BACKEND_ROOT = Path(__file__).resolve().parents[2]
BASE_TABLES = frozenset({
    "data_sources", "assets", "asset_identifiers", "asset_components",
    "asset_geometries", "asset_models", "inspections", "defects", "maintenance",
    "sensors", "observations", "environment_observations", "remote_sensing_observations",
    "state_snapshots", "model_registry", "predictions", "alerts", "ingestion_runs",
})
WORKFLOW_TABLES = frozenset({
    "users", "user_sessions", "password_reset_tokens", "login_audit", "role_permissions",
    "asset_assignments", "asset_reviews", "inspections", "inspection_components",
    "inspection_defects", "inspection_documents", "inspection_assignments", "maintenance",
    "maintenance_documents", "maintenance_progress", "maintenance_components", "asset_plans",
    "plan_status_history", "plan_documents", "notifications", "audit_log",
    "ai_assistant_audit", "evidence_revisions",
})
REQUIRED_TABLES = (
    BASE_TABLES - {"defects"}
    | WORKFLOW_TABLES
    | {"legacy_inspections", "legacy_maintenance", "legacy_defects", "map_features",
       "source_documents", "official_evidence", "dam_inspection_events", "dam_inspection_findings"}
)


def alembic_config(connection=None) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def current_head() -> str:
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    if head != "0007_bootstrap_contract":
        raise RuntimeError("Bootstrap contract must be reviewed when Alembic head changes")
    return head


def tables_at_revision(revision: str) -> frozenset[str]:
    tables = set(BASE_TABLES)
    for name, additions in [
        ("0001_initial", set()),
        ("0002_statewide_map_features", {"map_features"}),
        ("0003_asset_twin_metadata", set()),
        ("0004_government_evidence", {"source_documents", "official_evidence"}),
        ("0005_dam_inspection_ground_truth", {"dam_inspection_events", "dam_inspection_findings"}),
    ]:
        tables.update(additions)
        if revision == name:
            return frozenset(tables)
    if revision in {"0006", "0007_bootstrap_contract"}:
        return REQUIRED_TABLES
    raise RuntimeError(f"Unsupported Alembic revision: {revision!r}; review migration history before recovery")


def schema_snapshot(connection) -> dict:
    # Ignore only extension-owned relations (e.g. PostGIS spatial_ref_sys).
    # Unknown tables/views/sequences in public are evidence of a nonempty schema.
    relations = set(connection.scalars(sa.text("""
        SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname='public' AND c.relkind IN ('r','p','v','m','S','f')
          AND NOT EXISTS (
              SELECT 1 FROM pg_depend d WHERE d.classid='pg_class'::regclass
                AND d.objid=c.oid AND d.deptype='e')
    """)))
    tables = set(sa.inspect(connection).get_table_names(schema="public"))
    revisions = []
    if "alembic_version" in tables:
        revisions = list(connection.scalars(sa.text("SELECT version_num FROM public.alembic_version")))
    return {"relations": relations, "tables": tables, "revisions": revisions}


def classify_database(snapshot: dict) -> str:
    if not snapshot["relations"] and not snapshot["revisions"]:
        return "PRISTINE_DATABASE"
    revisions = snapshot["revisions"]
    expected = REQUIRED_TABLES
    reason = "Missing or ambiguous Alembic revision"
    if len(revisions) == 1:
        try:
            expected = tables_at_revision(revisions[0])
            if expected <= snapshot["tables"]:
                return "EXISTING_DATABASE"
            reason = "Required tables for recorded revision are missing"
        except RuntimeError as exc:
            reason = str(exc)
    raise RuntimeError(
        f"PARTIAL_SCHEMA_DETECTED: {reason}; present tables={sorted(snapshot['tables'])}; "
        f"missing tables={sorted(expected - snapshot['tables'])}; current Alembic revision={revisions}; "
        "Recovery: preserve a pg_dump, compare the recorded revision with the schema, "
        "and apply a reviewed forward migration or restore a verified backup. Do not stamp or reset."
    )


def schema_issues(connection) -> list[str]:
    inspector = sa.inspect(connection)
    tables = set(inspector.get_table_names(schema="public"))
    issues = [f"missing table: {name}" for name in sorted(REQUIRED_TABLES - tables)]
    if not connection.scalar(sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='postgis')")):
        issues.append("missing extension: postgis")
    for name in sorted(REQUIRED_TABLES & tables):
        expected = Base.metadata.tables[name]
        columns = {column["name"]: column for column in inspector.get_columns(name, schema="public")}
        for column in expected.columns:
            if column.name not in columns:
                issues.append(f"missing column: {name}.{column.name}")
                continue
            actual_type = columns[column.name]["type"]
            if actual_type._type_affinity is not column.type._type_affinity:
                issues.append(f"incompatible type: {name}.{column.name}")
            if hasattr(column.type, "srid") and (
                actual_type.srid != column.type.srid or actual_type.geometry_type != column.type.geometry_type
            ):
                issues.append(f"incompatible geometry: {name}.{column.name}")
        pk = inspector.get_pk_constraint(name, schema="public")["constrained_columns"]
        if tuple(pk) != tuple(c.name for c in expected.primary_key):
            issues.append(f"missing primary key: {name}")
        foreign_keys = {
            (tuple(f["constrained_columns"]), f["referred_table"], tuple(f["referred_columns"]))
            for f in inspector.get_foreign_keys(name, schema="public")
        }
        for fk in expected.foreign_key_constraints:
            signature = (tuple(c.name for c in fk.columns), fk.referred_table.name,
                         tuple(e.column.name for e in fk.elements))
            if signature not in foreign_keys:
                issues.append(f"missing foreign key: {name}.{','.join(signature[0])}")
        indexes = inspector.get_indexes(name, schema="public")
        uniques = {tuple(c["column_names"]) for c in inspector.get_unique_constraints(name, schema="public")}
        uniques.update(tuple(i["column_names"]) for i in indexes if i["unique"])
        for constraint in expected.constraints:
            if isinstance(constraint, sa.UniqueConstraint) and tuple(c.name for c in constraint.columns) not in uniques:
                issues.append(f"missing unique constraint: {name}.{constraint.name}")
        for index in expected.indexes:
            cols = tuple(c.name for c in index.columns)
            if index.unique and cols not in uniques:
                issues.append(f"missing unique index: {name}.{index.name}")
            if index.dialect_options["postgresql"].get("using") == "gist" and not any(
                tuple(i["column_names"]) == cols and i["dialect_options"].get("postgresql_using") == "gist"
                for i in indexes
            ):
                issues.append(f"missing spatial index: {name}.{index.name}")
    return issues


def create_pristine_schema(connection) -> None:
    if classify_database(schema_snapshot(connection)) != "PRISTINE_DATABASE":
        raise RuntimeError("Refusing create_all on a non-pristine schema")
    if set(Base.metadata.tables) != REQUIRED_TABLES:
        raise RuntimeError("Model imports and explicit required-table contract differ")
    connection.execute(sa.text("CREATE EXTENSION IF NOT EXISTS postgis"))
    Base.metadata.create_all(connection)
    # Migration 0003's source_url/dimensions and 0002's GIS table/indexes are
    # represented in metadata. No migration defines views, functions or triggers.
