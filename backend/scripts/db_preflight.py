"""SIMRAS Database Preflight & Schema Readiness Verification.

Detects database state:
- PRISTINE_DATABASE: Fresh database. Creates full schema cleanly, validates, and stamps Alembic head.
- EXISTING_DATABASE: Standard existing database. Runs alembic upgrade head.
- PARTIAL_SCHEMA_DETECTED: Inconsistent partial state. Fails safely and halts startup.
"""
from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parents[1]
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.core.config import settings
from app.db.base import Base
from app.models import dam_inspection, entities  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("db_preflight")

POSTGIS_SYSTEM_TABLES = {
    "spatial_ref_sys",
    "geography_columns",
    "geometry_columns",
    "raster_columns",
    "raster_overviews",
}

CORE_REQUIRED_TABLES = {
    "assets",
    "data_sources",
    "asset_models",
    "predictions",
    "inspections",
    "maintenance",
    "map_features",
}


def get_alembic_config() -> AlembicConfig:
    alembic_ini = backend_root / "alembic.ini"
    config = AlembicConfig(str(alembic_ini))
    config.set_main_option("script_location", str(backend_root / "alembic"))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


async def wait_for_db(engine, max_retries: int = 30, delay_seconds: float = 2.0) -> bool:
    logger.info("Connecting to database at %s...", settings.database_url.split("@")[-1])
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("Database connection established successfully.")
            return True
        except Exception as exc:
            logger.warning(
                "Database connection attempt %d/%d failed: %s. Retrying in %.1fs...",
                attempt,
                max_retries,
                exc,
                delay_seconds,
            )
            await asyncio.sleep(delay_seconds)
    return False


async def inspect_database_state(engine) -> tuple[str, list[str], str | None]:
    """Inspect the database schema and return (state, tables, alembic_version)."""
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name;
                """
            )
        )
        all_tables = [r[0] for r in res]

        alembic_table_exists = "alembic_version" in all_tables
        simras_tables = [t for t in all_tables if t not in POSTGIS_SYSTEM_TABLES and t != "alembic_version"]

        alembic_version: str | None = None
        if alembic_table_exists:
            try:
                ver_res = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                row = ver_res.first()
                if row:
                    alembic_version = row[0]
            except Exception as e:
                logger.warning("Could not query alembic_version: %s", e)

    # State Classification
    if not alembic_table_exists and len(simras_tables) == 0:
        return "PRISTINE_DATABASE", simras_tables, None

    if alembic_table_exists and alembic_version is not None and CORE_REQUIRED_TABLES.issubset(set(simras_tables)):
        return "EXISTING_DATABASE", simras_tables, alembic_version

    return "PARTIAL_SCHEMA_DETECTED", simras_tables, alembic_version


async def initialize_pristine_database(engine) -> None:
    logger.info("State: PRISTINE_DATABASE. Bootstrapping initial clean schema...")

    async with engine.begin() as conn:
        logger.info("Ensuring PostGIS extension exists...")
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS postgis;"))

        logger.info("Creating all application tables via SQLAlchemy metadata...")
        await conn.run_sync(Base.metadata.create_all)

    # Validate that all tables were created
    async with engine.connect() as conn:
        res = await conn.execute(
            text(
                "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'"
            )
        )
        created_tables = set(r[0] for r in res)
        missing_tables = CORE_REQUIRED_TABLES - created_tables
        if missing_tables:
            raise RuntimeError(f"Failed to create required tables in pristine DB: {missing_tables}")

    # Stamp Alembic to head revision
    logger.info("Stamping Alembic to head revision...")
    alembic_cfg = get_alembic_config()
    await asyncio.to_thread(alembic_command.stamp, alembic_cfg, "head")

    logger.info("Pristine database bootstrap and Alembic stamp completed successfully.")


async def upgrade_existing_database() -> None:
    logger.info("State: EXISTING_DATABASE. Executing alembic upgrade head...")
    alembic_cfg = get_alembic_config()
    try:
        await asyncio.to_thread(alembic_command.upgrade, alembic_cfg, "head")
        logger.info("Alembic upgrade head completed successfully.")
    except Exception as exc:
        logger.error("Alembic upgrade failed: %s", exc)
        raise


async def validate_schema_readiness(engine) -> bool:
    """Final assertion that schema is completely ready for API traffic."""
    async with engine.connect() as conn:
        # Check PostGIS
        pg_res = await conn.execute(text("SELECT extversion FROM pg_extension WHERE extname = 'postgis'"))
        pg_ver = pg_res.scalar()
        if not pg_ver:
            logger.error("PostGIS extension is not installed or not active!")
            return False

        # Check Alembic version table has a head
        ver_res = await conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        ver = ver_res.scalar()
        if not ver:
            logger.error("Alembic version is empty or missing!")
            return False

        # Check required tables
        t_res = await conn.execute(
            text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
        )
        tables = set(r[0] for r in t_res)
        missing = CORE_REQUIRED_TABLES - tables
        if missing:
            logger.error("Database is missing core tables: %s", missing)
            return False

        logger.info(
            "Schema readiness confirmed: PostGIS %s, Alembic revision %s, %d public tables.",
            pg_ver,
            ver,
            len(tables),
        )
        return True


async def main() -> int:
    engine = create_async_engine(settings.database_url, echo=False)

    try:
        # 1. Wait for database
        if not await wait_for_db(engine):
            logger.critical("Could not connect to PostgreSQL within timeout. Halting startup.")
            return 1

        # 2. Inspect state
        state, tables, alembic_ver = await inspect_database_state(engine)
        logger.info("Database inspection result: state=%s, table_count=%d, alembic_version=%s", state, len(tables), alembic_ver)

        if state == "PRISTINE_DATABASE":
            await initialize_pristine_database(engine)
        elif state == "EXISTING_DATABASE":
            await upgrade_existing_database()
        elif state == "PARTIAL_SCHEMA_DETECTED":
            missing = CORE_REQUIRED_TABLES - set(tables)
            logger.critical(
                "PARTIAL_SCHEMA_DETECTED: Database has partial or corrupted schema.\n"
                "  Present tables: %s\n"
                "  Missing core tables: %s\n"
                "  Alembic revision: %s\n"
                "HALTING BACKEND STARTUP SAFELY. Never blindly stamp a partial database.",
                sorted(tables),
                sorted(list(missing)),
                alembic_ver,
            )
            return 1
        else:
            logger.critical("Unknown database state '%s'. Halting startup.", state)
            return 1

        # 3. Final validation
        if not await validate_schema_readiness(engine):
            logger.critical("Final schema readiness verification failed. Halting startup.")
            return 1

        logger.info("Database preflight completed successfully.")
        return 0

    finally:
        await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
