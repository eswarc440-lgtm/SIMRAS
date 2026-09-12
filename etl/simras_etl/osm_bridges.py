from __future__ import annotations

from datetime import UTC, datetime

import httpx

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
AP_AREA_QUERY = """
[out:json][timeout:180];
area["ISO3166-2"="IN-AP"]->.searchArea;
(
  way["bridge"](area.searchArea);
  relation["bridge"](area.searchArea);
);
out center tags;
""".strip()


async def fetch_ap_bridges(client: httpx.AsyncClient | None = None) -> dict:
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=240)
    try:
        response = await client.post(OVERPASS_URL, data={"data": AP_AREA_QUERY})
        response.raise_for_status()
        payload = response.json()
        return {
            "source": "OpenStreetMap Overpass",
            "source_type": "OPEN_COMMUNITY_RECORD",
            "retrieved_at": datetime.now(UTC).isoformat(),
            "licence": "ODbL 1.0",
            "elements": payload.get("elements", []),
        }
    finally:
        if owns_client:
            await client.aclose()

