import pytest
from pydantic import ValidationError
import sqlite3
from types import SimpleNamespace
from sqlalchemy.dialects import sqlite

from app.api.routes.assets import AssetRegistrationRequest, list_assets, register_asset
from app.services.twin_service import get_asset_row
from fastapi import HTTPException
from datetime import datetime, timezone
from unittest.mock import AsyncMock


def test_registration_request_accepts_wizard_shape_and_normalizes_coordinates():
    request = AssetRegistrationRequest(
        name="Test Bridge",
        asset_type="bridge",
        subtype="prestressed_concrete_bridge",
        district="East Godavari",
        latitude=16.989,
        longitude=81.782,
        dimensions={"length_m": 450, "height_m": 18},
        built_year=2015,
        material="Reinforced Concrete",
        submitted_by="usr-officer",
        submitted_role="OFFICER",
    )

    assert request.asset_type == "bridge"
    assert request.latitude == 16.989
    assert request.longitude == 81.782


def test_registration_request_rejects_invalid_coordinates():
    with pytest.raises(ValidationError, match="latitude"):
        AssetRegistrationRequest(
            name="Bad Location",
            asset_type="bridge",
            district="East Godavari",
            latitude=99,
            longitude=81,
            submitted_by="usr-officer",
            submitted_role="OFFICER",
        )


@pytest.mark.asyncio
async def test_public_registry_excludes_pending_and_rejected_registrations():
    # Execute the real count query against a small database. The empty page
    # result keeps this test independent of PostGIS geometry serialization.
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE assets (asset_code TEXT, asset_type TEXT, status TEXT)")
    connection.executemany("INSERT INTO assets VALUES (?, 'bridge', ?)", [
        ("AP_BR_EXISTING", "ACTIVE"), ("AP_BR_APPROVED", "VERIFIED"),
        ("AP_BR_PENDING", "PENDING_REVIEW"), ("AP_BR_REJECTED", "REJECTED"),
    ])

    async def scalar(statement):
        sql = str(statement.compile(dialect=sqlite.dialect(), compile_kwargs={"literal_binds": True}))
        return connection.execute(sql).fetchone()[0]

    async def execute(_statement):
        return SimpleNamespace(all=lambda: [])

    try:
        result = await list_assets(asset_type=None, district=None, search=None,
                                   limit=100, offset=0,
                                   session=SimpleNamespace(scalar=scalar, execute=execute))
        assert result.total == 2
    finally:
        connection.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["PENDING_REVIEW", "REJECTED"])
async def test_direct_asset_lookup_does_not_expose_private_registration(status):
    row = SimpleNamespace(Asset=SimpleNamespace(status=status))
    session = SimpleNamespace(execute=AsyncMock(return_value=SimpleNamespace(first=lambda: row)))
    with pytest.raises(HTTPException) as error:
        await get_asset_row(session, "AP_BR_PRIVATE")
    assert error.value.status_code == 404


@pytest.mark.asyncio
async def test_generated_bridge_code_matches_public_registry_scope():
    added = []

    async def flush():
        added[0].id = 1
        added[0].created_at = datetime.now(timezone.utc)

    session = SimpleNamespace(scalar=AsyncMock(return_value=None), add=added.append,
                              flush=flush, commit=AsyncMock())
    request = AssetRegistrationRequest(name="Test Bridge", asset_type="bridge", district="Krishna",
                                       latitude=16.5, longitude=80.5,
                                       submitted_by="usr-officer", submitted_role="OFFICER")
    result = await register_asset(request, session)
    assert result["asset_code"].startswith("AP_BR_")
    assert result["status"] == "PENDING_REVIEW"
    assert result["health_score"] is None
