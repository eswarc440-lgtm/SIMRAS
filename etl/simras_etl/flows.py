from __future__ import annotations

from prefect import flow, task

from simras_etl.india_wris import fetch_dam_features
from simras_etl.osm_bridges import fetch_ap_bridges


@task(retries=3, retry_delay_seconds=30)
async def extract_bridges() -> dict:
    return await fetch_ap_bridges()


@task(retries=3, retry_delay_seconds=30)
async def extract_dams() -> dict:
    return await fetch_dam_features()


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


if __name__ == "__main__":
    import asyncio

    print(asyncio.run(asset_registry_refresh()))

