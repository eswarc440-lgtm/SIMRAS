from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import asyncpg
import httpx
from shapely.geometry import LineString, Point

OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
)

AREA_PREFIX = """
[out:json][timeout:600][maxsize:1073741824];
area["ISO3166-2"="IN-AP"]->.searchArea;
""".strip()

LAYER_QUERIES = {
    "airport": f"""{AREA_PREFIX}
(
  nwr["aeroway"="aerodrome"](area.searchArea);
);
out center;
""",
    "bridge": f"""{AREA_PREFIX}
(
  way["bridge"]["bridge"!="no"](area.searchArea);
  relation["bridge"]["bridge"!="no"](area.searchArea);
);
out center;
""",
    "barrage": f"""{AREA_PREFIX}
(
  nwr["waterway"~"^(dam|weir)$"]["name"~"barrage|anicut",i](area.searchArea);
  nwr["man_made"="dam"]["name"~"barrage|anicut",i](area.searchArea);
);
out center;
""",
    "temple": f"""{AREA_PREFIX}
(
  nwr["amenity"="place_of_worship"]["religion"="hindu"]["name"](area.searchArea);
  nwr["amenity"="place_of_worship"]["place_of_worship"="temple"]["name"](area.searchArea);
);
out center;
""",
    # The OSM basemap still displays every mapped street. This overlay deliberately
    # carries the statewide strategic road network to keep API and browser payloads safe.
    "road": f"""{AREA_PREFIX}
(
  way["highway"~"^(motorway|trunk|primary|secondary)$"](area.searchArea);
);
out geom;
""",
}

ALLOWED_TAGS = {
    "name",
    "name:en",
    "alt_name",
    "aeroway",
    "aerodrome",
    "aerodrome:type",
    "iata",
    "icao",
    "operator",
    "bridge",
    "bridge:structure",
    "highway",
    "railway",
    "ref",
    "lanes",
    "surface",
    "maxspeed",
    "waterway",
    "man_made",
    "amenity",
    "religion",
    "denomination",
    "place_of_worship",
    "tourism",
    "historic",
    "heritage",
    "wikidata",
    "wikipedia",
    "website",
}


@dataclass(frozen=True)
class MapFeatureRow:
    external_id: str
    name: str | None
    feature_type: str
    subtype: str | None
    geometry_wkt: str
    attributes: dict[str, Any]
    identity_status: str
    confidence_score: float
    retrieved_at: datetime


def database_url() -> str:
    value = os.environ.get("DATABASE_URL")
    if not value:
        raise RuntimeError("DATABASE_URL is not configured")
    return value.replace("postgresql+asyncpg://", "postgresql://", 1)


def _point_for(element: dict[str, Any]) -> Point | None:
    center = element.get("center") or {}
    latitude = center.get("lat", element.get("lat"))
    longitude = center.get("lon", element.get("lon"))
    if latitude is None or longitude is None:
        return None
    return Point(float(longitude), float(latitude))


def element_geometry(layer: str, element: dict[str, Any]):
    if layer == "road":
        coordinates = [
            (float(point["lon"]), float(point["lat"]))
            for point in element.get("geometry", [])
            if point.get("lon") is not None and point.get("lat") is not None
        ]
        if len(coordinates) < 2:
            return None
        return LineString(coordinates)
    return _point_for(element)


def classify_subtype(layer: str, tags: dict[str, Any]) -> str:
    if layer == "airport":
        return str(tags.get("aerodrome:type") or tags.get("aerodrome") or "aerodrome")
    if layer == "bridge":
        if tags.get("railway") and tags.get("highway"):
            return "mixed_transport_bridge"
        if tags.get("railway"):
            return "rail_bridge"
        highway = tags.get("highway")
        if highway in {"motorway", "trunk", "primary", "secondary"}:
            return "major_road_bridge"
        if highway:
            return "road_bridge"
        return "other_bridge"
    if layer == "barrage":
        name = str(tags.get("name") or "").lower()
        return "anicut" if "anicut" in name else "barrage"
    if layer == "temple":
        landmark_keys = {"wikidata", "wikipedia", "heritage", "historic", "tourism"}
        return "landmark_temple" if landmark_keys.intersection(tags) else "named_temple"
    if layer == "road":
        return str(tags.get("highway") or "road")
    return layer


def transform_layer(
    layer: str,
    payload: dict[str, Any],
    retrieved_at: datetime,
) -> list[MapFeatureRow]:
    rows: list[MapFeatureRow] = []
    seen: set[str] = set()
    for element in payload.get("elements", []):
        osm_type = str(element.get("type") or "unknown")
        osm_id = element.get("id")
        if osm_id is None:
            continue
        external_id = f"{osm_type}/{osm_id}"
        if external_id in seen:
            continue
        geometry = element_geometry(layer, element)
        if geometry is None or geometry.is_empty or not geometry.is_valid:
            continue
        tags = element.get("tags") or {}
        attributes = {key: tags[key] for key in ALLOWED_TAGS if key in tags}
        name = tags.get("name:en") or tags.get("name")
        is_named = bool(name)
        confidence = 0.75 if is_named else 0.55
        if layer == "temple" and classify_subtype(layer, tags) == "landmark_temple":
            confidence = 0.80
        rows.append(
            MapFeatureRow(
                external_id=external_id,
                name=str(name) if name else None,
                feature_type=layer,
                subtype=classify_subtype(layer, tags),
                geometry_wkt=geometry.wkt,
                attributes=attributes,
                identity_status="SOURCE_REPORTED",
                confidence_score=confidence,
                retrieved_at=retrieved_at,
            )
        )
        seen.add(external_id)
    return rows


async def fetch_layer(client: httpx.AsyncClient, layer: str) -> dict[str, Any]:
    query = LAYER_QUERIES[layer]
    failures: list[str] = []
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = await client.post(endpoint, data={"data": query})
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload.get("elements"), list):
                raise ValueError("Overpass response has no elements list")
            return payload
        except (httpx.HTTPError, ValueError) as exc:
            failures.append(f"{endpoint}: {exc}")
    raise RuntimeError(f"Unable to fetch {layer}: {'; '.join(failures)}")


async def _source_id(connection: asyncpg.Connection) -> int:
    return await connection.fetchval(
        """
        INSERT INTO data_sources (
            code, name, organisation, source_type, url, licence,
            refresh_policy, is_authoritative
        )
        VALUES (
            'OSM_OVERPASS_AP',
            'OpenStreetMap Andhra Pradesh statewide extract',
            'OpenStreetMap contributors',
            'OPEN_COMMUNITY_RECORD',
            'https://www.openstreetmap.org/',
            'ODbL 1.0',
            'Weekly',
            false
        )
        ON CONFLICT (code) DO UPDATE
        SET name = EXCLUDED.name,
            organisation = EXCLUDED.organisation,
            source_type = EXCLUDED.source_type,
            url = EXCLUDED.url,
            licence = EXCLUDED.licence,
            refresh_policy = EXCLUDED.refresh_policy,
            is_authoritative = EXCLUDED.is_authoritative,
            updated_at = now()
        RETURNING id
        """
    )


async def replace_layer(
    connection: asyncpg.Connection,
    source_id: int,
    layer: str,
    rows: list[MapFeatureRow],
) -> int:
    if not rows:
        raise RuntimeError(f"Refusing to replace {layer} with an empty result")
    statement = """
        INSERT INTO map_features (
            source_id, external_id, name, feature_type, subtype, geometry,
            attributes, identity_status, confidence_score, retrieved_at
        )
        VALUES (
            $1, $2, $3, $4, $5, ST_GeomFromText($6, 4326),
            $7::jsonb, $8, $9, $10
        )
        ON CONFLICT (source_id, feature_type, external_id) DO UPDATE
        SET name = EXCLUDED.name,
            subtype = EXCLUDED.subtype,
            geometry = EXCLUDED.geometry,
            attributes = EXCLUDED.attributes,
            identity_status = EXCLUDED.identity_status,
            confidence_score = EXCLUDED.confidence_score,
            retrieved_at = EXCLUDED.retrieved_at,
            updated_at = now()
    """
    values = [
        (
            source_id,
            row.external_id,
            row.name,
            row.feature_type,
            row.subtype,
            row.geometry_wkt,
            json.dumps(row.attributes, ensure_ascii=False),
            row.identity_status,
            row.confidence_score,
            row.retrieved_at,
        )
        for row in rows
    ]
    async with connection.transaction():
        await connection.execute(
            "DELETE FROM map_features WHERE source_id = $1 AND feature_type = $2",
            source_id,
            layer,
        )
        await connection.executemany(statement, values)
    return len(rows)


async def refresh_statewide_osm(
    layers: list[str],
    output_dir: Path,
) -> dict[str, int]:
    unknown = sorted(set(layers) - set(LAYER_QUERIES))
    if unknown:
        raise ValueError(f"Unknown layers: {', '.join(unknown)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(UTC)
    transformed: dict[str, list[MapFeatureRow]] = {}
    timeout = httpx.Timeout(660, connect=30)
    headers = {
        "User-Agent": "SIMRAS-Academic-Digital-Twin/0.1",
        "Accept": "application/json",
    }
    async with httpx.AsyncClient(
        timeout=timeout,
        headers=headers,
        follow_redirects=True,
    ) as client:
        for layer in layers:
            print(f"Fetching AP OSM layer: {layer}")
            payload = await fetch_layer(client, layer)
            raw_path = output_dir / f"osm-ap-{layer}.json"
            raw_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            rows = transform_layer(layer, payload, retrieved_at)
            if not rows:
                raise RuntimeError(f"Overpass returned no usable {layer} geometries")
            transformed[layer] = rows
            print(f"Prepared {len(rows)} {layer} features")

    connection = await asyncpg.connect(database_url())
    try:
        source_id = await _source_id(connection)
        counts: dict[str, int] = {}
        for layer in layers:
            counts[layer] = await replace_layer(
                connection,
                source_id,
                layer,
                transformed[layer],
            )
            print(f"Loaded {counts[layer]} {layer} features")
        return counts
    finally:
        await connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch and load source-labelled Andhra Pradesh OSM map layers."
    )
    parser.add_argument(
        "--layers",
        default=",".join(LAYER_QUERIES),
        help="Comma-separated layers: airport,bridge,barrage,temple,road",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/data/raw/osm-statewide"),
    )
    args = parser.parse_args()
    layers = [value.strip() for value in args.layers.split(",") if value.strip()]
    counts = asyncio.run(refresh_statewide_osm(layers, args.output_dir))
    print(json.dumps({"status": "LOADED", "counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
