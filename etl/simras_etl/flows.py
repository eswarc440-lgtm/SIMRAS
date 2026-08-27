from __future__ import annotations

from datetime import UTC, datetime, timedelta

from prefect import flow, task

from simras_etl.environment_loader import (
    load_environment_observations,
    read_observations_csv,
)
from simras_etl.india_wris import fetch_dam_features
from simras_etl.nasa_power import (
    build_observation_rows,
    fetch_daily_weather,
    write_observations_csv,
)
from simras_etl.nwdp_reservoir import build_reservoir_observations
from simras_etl.osm_bridges import fetch_ap_bridges


@task(retries=3, retry_delay_seconds=30)
async def extract_bridges() -> dict:
    return await fetch_ap_bridges()


@task(retries=3, retry_delay_seconds=30)
async def extract_dams() -> dict:
    return await fetch_dam_features()


@task(retries=3, retry_delay_seconds=30)
async def refresh_nasa_power(
    *,
    asset_code: str,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    output_path: str,
) -> dict:
    payload = await fetch_daily_weather(
        latitude=latitude,
        longitude=longitude,
        start=start,
        end=end,
    )
    rows = build_observation_rows(payload, asset_code=asset_code)
    output = write_observations_csv(rows, output_path)
    loaded = await load_environment_observations(
        rows, source_code="NASA_POWER_DAILY"
    )
    return {**loaded, "output": str(output)}


@task(retries=2, retry_delay_seconds=15)
async def refresh_nwdp_reservoir(
    *,
    level_path: str,
    storage_path: str,
    output_path: str,
) -> dict:
    transformed = build_reservoir_observations(
        level_path,
        storage_path,
        output_path,
    )
    rows = read_observations_csv(output_path)
    loaded = await load_environment_observations(
        rows, source_code="NWDP_AP_RESERVOIR_DAILY"
    )
    return {**transformed, "loaded": loaded}


@flow(name="simras-asset-registry-refresh", log_prints=True)
async def asset_registry_refresh() -> dict:
    """Extract raw sources; transformation/loading is intentionally approval-gated."""
    bridges = await extract_bridges()
    dams = await extract_dams()
    return {
        "bridge_records": len(bridges.get("elements", [])),
        "dam_records": len(dams.get("payload", {}).get("features", [])),
        "status": "EXTRACTED_PENDING_IDENTITY_MATCH",
    }


@flow(name="simras-environment-refresh", log_prints=True)
async def environment_refresh(
    *,
    nasa_start: str | None = None,
    nasa_end: str | None = None,
) -> dict:
    """Refresh the two validated Stage 4 pilot feeds and load them idempotently."""
    end_date = datetime.now(UTC).date() - timedelta(days=1)
    start_date = end_date - timedelta(days=60)
    nasa_start = nasa_start or start_date.strftime("%Y%m%d")
    nasa_end = nasa_end or end_date.strftime("%Y%m%d")

    nasa = await refresh_nasa_power(
        asset_code="AP_DAM_00001",
        latitude=16.5075,
        longitude=80.605277778,
        start=nasa_start,
        end=nasa_end,
        output_path="/data/processed/nasa-power-AP_DAM_00001.csv",
    )
    reservoir = await refresh_nwdp_reservoir(
        level_path="/data/raw/nwdp-ap-reservoir-level-2026-2030.csv",
        storage_path="/data/raw/nwdp-ap-reservoir-storage-2026-2030.csv",
        output_path="/data/processed/nwdp-reservoir-AP_DAM_NWDP_AP01VH0059.csv",
    )
    return {
        "status": "LOADED",
        "nasa_power": nasa,
        "nwdp_reservoir": reservoir,
    }


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(asset_registry_refresh()))
