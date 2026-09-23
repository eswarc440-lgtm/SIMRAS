"""Run with SIMRAS_TEST_DATABASE_URL pointing at a disposable PostGIS database.

Each test gets its own transaction, rolled back even when it fails. Never use
the application database: the name guard is intentional.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture
async def connection():
    url = os.getenv("SIMRAS_TEST_DATABASE_URL")
    if not url:
        pytest.skip("Set SIMRAS_TEST_DATABASE_URL to a disposable PostGIS database")
    assert make_url(url).database.startswith("simras_bootstrap_test_"), "Refusing application DB"
    engine = create_async_engine(url)
    async with engine.connect() as conn:
        transaction = await conn.begin()
        try:
            yield conn
        finally:
            await transaction.rollback()
    await engine.dispose()


async def bootstrap(connection):
    from app.db.startup import prepare_database

    return await connection.run_sync(prepare_database)


async def client_for(connection):
    from app.db.session import get_db
    from app.main import app

    async def database():
        async with AsyncSession(bind=connection, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_db] = database
    return app, AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_pristine_bootstrap_stamps_only_valid_schema_and_imports_inventory(connection):
    result = await bootstrap(connection)
    assert result["database_state"] == "PRISTINE_DATABASE"
    assert result["canonical_import"]["rows_read"] == 194
    assert result["canonical_import"]["rows_inserted"] == 194
    assert result["canonical_import"]["rows_rejected"] == 0
    assert result["asset_count"] == 194
    from app.db.schema import current_head, schema_issues

    assert await connection.scalar(text("SELECT version_num FROM alembic_version")) == current_head()
    assert await connection.run_sync(schema_issues) == []
    assert await connection.scalar(text("SELECT count(*) FROM assets WHERE identity_status = 'VERIFIED'")) == 0
    tables = await connection.run_sync(lambda c: set(inspect(c).get_table_names()))
    assert {"map_features", "dam_inspection_events", "legacy_inspections", "notifications"} <= tables


@pytest.mark.asyncio
async def test_second_start_uses_upgrade_and_preserves_officer_assets(connection, monkeypatch):
    await bootstrap(connection)
    await connection.execute(text("""
        INSERT INTO assets (asset_code, name, asset_type, status, identity_status,
                            representative_geometry, is_estimated)
        VALUES ('OFFICER_EXTRA', 'Officer-added bridge', 'bridge', 'ACTIVE',
                'NEEDS_VERIFICATION', ST_SetSRID(ST_MakePoint(80, 16), 4326), false)
    """))
    from app.db import startup

    def forbidden(*args, **kwargs):
        pytest.fail("An existing database must never be created or stamped")

    monkeypatch.setattr(startup, "create_pristine_schema", forbidden)
    monkeypatch.setattr(startup.command, "stamp", forbidden)
    result = await bootstrap(connection)
    assert result["database_state"] == "EXISTING_DATABASE"
    assert result["canonical_import"]["rows_inserted"] == 0
    assert result["asset_count"] == 195
    assert await connection.scalar(text("SELECT name FROM assets WHERE asset_code='OFFICER_EXTRA'")) == "Officer-added bridge"


@pytest.mark.asyncio
@pytest.mark.parametrize("setup", [
    "CREATE TABLE assets (id integer PRIMARY KEY)",
    "CREATE TABLE alembic_version (version_num varchar(32))",
    "CREATE TABLE unrelated_business_data (id integer)",
])
async def test_partial_or_unversioned_schema_is_not_stamped(connection, setup):
    await connection.execute(text(setup))
    with pytest.raises(RuntimeError, match="PARTIAL_SCHEMA_DETECTED"):
        await bootstrap(connection)


@pytest.mark.asyncio
async def test_missing_required_table_at_head_fails_before_upgrade(connection, monkeypatch):
    await bootstrap(connection)
    await connection.execute(text("DROP TABLE predictions"))
    from app.db import startup

    def forbidden(*args, **kwargs):
        pytest.fail("Partial schema must be rejected before migration or stamping")

    monkeypatch.setattr(startup.command, "upgrade", forbidden)
    with pytest.raises(RuntimeError, match="PARTIAL_SCHEMA_DETECTED.*predictions"):
        await bootstrap(connection)


@pytest.mark.asyncio
async def test_migration_failure_propagates(connection, monkeypatch):
    await bootstrap(connection)
    from app.db import startup

    def fail(*args, **kwargs):
        raise RuntimeError("deliberate migration failure")

    monkeypatch.setattr(startup.command, "upgrade", fail)
    with pytest.raises(RuntimeError, match="deliberate migration failure"):
        await bootstrap(connection)


@pytest.mark.asyncio
async def test_failed_validation_cannot_stamp(connection, monkeypatch):
    from app.db import startup

    monkeypatch.setattr(startup, "schema_issues", lambda conn: ["missing test object"])
    with pytest.raises(RuntimeError, match="SCHEMA_VALIDATION_FAILED"):
        await bootstrap(connection)
    assert not await connection.run_sync(lambda c: inspect(c).has_table("alembic_version"))


@pytest.mark.asyncio
async def test_health_distinguishes_connectivity_from_schema(connection):
    app, client = await client_for(connection)
    try:
        async with client:
            response = await client.get("/health")
            assert response.status_code == 503
            assert response.json()["database"] == "up"
            assert response.json()["status"] == "degraded"
            assert "assets" in response.json()["missing_tables"]
            await bootstrap(connection)
            response = await client.get("/health")
            assert response.status_code == 200
            assert response.json()["schema"] == "ready"
            assert response.json()["required_tables"] == "ready"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_registry_filters_map_twins_and_selected_reports(connection):
    await bootstrap(connection)
    app, client = await client_for(connection)
    try:
        async with client:
            response = await client.get("/api/v1/assets?limit=500&offset=0")
            assert response.status_code == 200, response.text
            assets = response.json()["items"]
            assert len(assets) == 194
            for category, count in [("dam", 167), ("airport", 8), ("bridge", 2), ("temple", 7), ("barrage", 10)]:
                response = await client.get(f"/api/v1/assets?asset_type={category}&limit=2&offset=1")
                assert response.status_code == 200, response.text
                assert response.json()["total"] == count
                assert all(item["asset_type"] == category for item in response.json()["items"])
            response = await client.get("/api/v1/assets?search=Prakasam")
            assert response.status_code == 200, response.text
            assert any("Prakasam" in item["name"] for item in response.json()["items"])
            assert (await client.get("/api/v1/assets?offset=1000")).json()["items"] == []
            assert (await client.get("/api/v1/map/features")).status_code == 200
            for category in ("dam", "airport", "bridge", "temple", "barrage"):
                code = next(item["asset_code"] for item in assets if item["asset_type"] == category)
                response = await client.get(f"/api/v1/assets/{code}/twin")
                assert response.status_code == 200, response.text
                assert response.json()["asset"]["asset_code"] == code
                response = await client.get(f"/api/v1/reports/assets/{code}")
                assert response.status_code == 200, response.text
    finally:
        app.dependency_overrides.clear()


def test_entrypoint_never_launches_uvicorn_when_database_startup_fails(tmp_path):
    if os.name == "nt":
        pytest.skip("The container entrypoint requires bash")
    # Substitute only external processes; run the real entrypoint shell.
    for name, body in {
        "python": "#!/bin/sh\nexit 23\n",
        "uvicorn": "#!/bin/sh\necho UVICORN_STARTED\n",
        "alembic": "#!/bin/sh\nexit 23\n",
    }.items():
        path = tmp_path / name
        path.write_text(body)
        path.chmod(0o755)
    result = subprocess.run(
        ["/bin/bash", str(Path(__file__).resolve().parents[1] / "entrypoint.sh")],
        env={**os.environ, "PATH": f"{tmp_path}:/usr/bin:/bin"},
        text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert "UVICORN_STARTED" not in result.stdout
