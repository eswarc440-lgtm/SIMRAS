from __future__ import annotations

from datetime import UTC, datetime

import httpx

WRIS_DAM_LAYER = (
    "https://arc.indiawris.gov.in/server/rest/services/"
    "SubInfoSysLCC/WaterResourceProject/MapServer/2/query"
)


async def fetch_dam_features(client: httpx.AsyncClient | None = None) -> dict:
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=120)
    params = {
        "where": "1=1",
        "outFields": "*",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }
    try:
        response = await client.get(WRIS_DAM_LAYER, params=params)
        response.raise_for_status()
        return {
            "source": "India-WRIS Dam Feature Layer",
            "source_type": "GOVERNMENT_RECORD",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "payload": response.json(),
        }
    finally:
        if owns_client:
            await client.aclose()

