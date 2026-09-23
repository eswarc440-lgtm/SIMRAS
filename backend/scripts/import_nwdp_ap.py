from __future__ import annotations

import argparse
import asyncio
import csv
import math
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from sqlalchemy import text

from app.db.session import get_db


# ============================================================
# SIMRAS - Andhra Pradesh NWDP environmental importer
# ============================================================
#
# Design goals:
#   * Use the exact column names published in the downloaded NWDP CSVs.
#   * Never treat government telemetry as structural-health evidence.
#   * Distinguish direct reservoir association from spatial transfer.
#   * Keep low-confidence / distant station matches out of the database.
#   * Be safe to rerun without duplicating the same observation.
#   * Store only the latest station state for level/storage feeds and
#     latest 1h/24h/7d rainfall features for the current Digital Twin.
#     The raw CSVs remain available for future historical modelling.
#
# NWDP timestamps are interpreted as India Standard Time (UTC+05:30).

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "nwdp"

SOURCE_CODE = "NWDP_AP_SW"
SOURCE_TYPE = "GOVERNMENT_TELEMETRY"

IST = timezone(timedelta(hours=5, minutes=30))

# Andhra Pradesh sanity envelope; intentionally generous.
AP_LAT_MIN = 12.0
AP_LAT_MAX = 20.0
AP_LON_MIN = 76.0
AP_LON_MAX = 86.0

# Conservative spatial-transfer limits.
RAIN_MAX_DISTANCE_KM = 25.0
RIVER_MAX_DISTANCE_KM = 5.0
RESERVOIR_DIRECT_MAX_DISTANCE_KM = 5.0
RESERVOIR_NEAR_MAX_DISTANCE_KM = 2.0


# Exact schemas from the user's downloaded NWDP resources.
FILES: dict[str, dict[str, str]] = {
    "ap_rainfall_hourly_2026_2030.csv": {
        "kind": "rainfall",
        "station": "Station",
        "district": "District",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "time": "Data Acquisition Time",
        "value": "Telemetry Hourly Rainfall (mm)",
    },
    "ap_reservoir_level_daily_2026_2030.csv": {
        "kind": "reservoir_level",
        "station": "Station",
        "district": "District",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "time": "Data Acquisition Time",
        "value": "Manual Daily Reservoir water level (m)",
    },
    "ap_reservoir_storage_daily_2026_2030.csv": {
        "kind": "reservoir_storage",
        "station": "Station",
        "district": "District",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "time": "Data Acquisition Time",
        "value": "Manual Daily Reservoir storage (mcm)",
    },
    "ap_river_velocity_discharge_daily_2026_2030.csv": {
        "kind": "river_velocity_discharge",
        "station": "Station",
        "district": "District",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "time": "Data Acquisition Time",
        "level": "River Water Level (m)",
        "velocity": "Velocity (m/sec)",
        "discharge": "Total_discharge (m3/sec)",
    },
    "godavari_river_level_hourly_2026_2030.csv": {
        "kind": "river_level",
        "station": "Station",
        "district": "District",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "time": "Data Acquisition Time",
        "value": "River Water Level Telemetry Hourly (meter)",
    },
    "krishna_river_level_hourly_2026_2030.csv": {
        "kind": "river_level",
        "station": "Station",
        "district": "District",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "time": "Data Acquisition Time",
        "value": "River Water Level Telemetry Hourly (meter)",
    },
    "pennar_river_level_hourly_2026_2030.csv": {
        "kind": "river_level",
        "station": "Station",
        "district": "District",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "time": "Data Acquisition Time",
        "value": "River Water Level Telemetry Hourly (meter)",
    },
}


# ============================================================
# Normalisation helpers
# ============================================================


def normalize_name(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)

    removable = {
        "dam",
        "reservoir",
        "project",
        "barrage",
        "station",
        "telemetry",
        "awlr",
        "res",
    }

    tokens = [token for token in value.split() if token not in removable]
    return " ".join(tokens)


def name_similarity(first: str | None, second: str | None) -> float:
    a = normalize_name(first)
    b = normalize_name(second)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    compact_a = a.replace(" ", "")
    compact_b = b.replace(" ", "")

    if compact_a == compact_b:
        return 1.0

    containment_score = 0.0
    if min(len(compact_a), len(compact_b)) >= 5:
        if compact_a in compact_b or compact_b in compact_a:
            containment_score = 0.95

    return max(
        SequenceMatcher(None, a, b).ratio(),
        SequenceMatcher(None, compact_a, compact_b).ratio(),
        containment_score,
    )


def normalize_district(value: str | None) -> str:
    if not value:
        return ""

    value = re.sub(r"\s+", " ", value.strip().upper())

    aliases = {
        "CUDDAPAH": "YSR",
        "KADAPA": "YSR",
        "YSR KADAPA": "YSR",
        "NELLORE": "SRI POTTI SRIRAMULU NELLORE",
        "SPSR NELLORE": "SRI POTTI SRIRAMULU NELLORE",
    }

    return aliases.get(value, value)


# ============================================================
# Numeric/time helpers
# ============================================================


def numeric(value: Any) -> float | None:
    if value is None:
        return None

    raw = str(value).strip()
    if not raw or raw.lower() in {"na", "n/a", "null", "none", "-", "nan"}:
        return None

    try:
        parsed = float(raw.replace(",", ""))
    except ValueError:
        return None

    if not math.isfinite(parsed):
        return None

    return parsed


def parse_nwdp_time(value: str | None) -> datetime | None:
    if not value:
        return None

    raw = value.strip()

    formats = (
        "%d-%m-%Y %H:%M",
        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y",
    )

    for fmt in formats:
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=IST)
        except ValueError:
            continue

    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=IST)

    return parsed


def valid_ap_coordinate(latitude: float, longitude: float) -> bool:
    return (
        AP_LAT_MIN <= latitude <= AP_LAT_MAX
        and AP_LON_MIN <= longitude <= AP_LON_MAX
    )


# ============================================================
# Geography
# ============================================================


def distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius = 6371.0088

    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(lat1_r)
        * math.cos(lat2_r)
        * math.sin(dlon / 2.0) ** 2
    )

    a = min(1.0, max(0.0, a))
    return 2.0 * radius * math.asin(math.sqrt(a))


# ============================================================
# Database helpers
# ============================================================


async def get_source_id(session) -> int:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM data_sources
            WHERE code = CAST(:code AS VARCHAR)
            LIMIT 1
            """
        ),
        {"code": SOURCE_CODE},
    )

    source_id = result.scalar_one_or_none()
    if source_id is None:
        raise RuntimeError(
            "NWDP_AP_SW is not registered in data_sources. "
            "Run register_government_sources.py first."
        )

    return int(source_id)


async def load_assets(session) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT
                id,
                asset_code,
                name,
                asset_type,
                district,
                identity_status,
                confidence_score,
                ST_Y(representative_geometry) AS latitude,
                ST_X(representative_geometry) AS longitude
            FROM assets
            WHERE asset_type IN ('dam', 'barrage', 'bridge')
            """
        )
    )

    return [dict(row._mapping) for row in result]


async def delete_existing_source_observations(session, source_id: int) -> int:
    result = await session.execute(
        text(
            """
            DELETE FROM environment_observations
            WHERE source_id = CAST(:source_id AS INTEGER)
            RETURNING id
            """
        ),
        {"source_id": int(source_id)},
    )

    deleted = result.scalars().all()
    return len(deleted)


# ============================================================
# Asset matching
# ============================================================


def assets_of_type(
    asset_rows: list[dict[str, Any]],
    allowed_types: set[str],
) -> list[dict[str, Any]]:
    return [
        asset
        for asset in asset_rows
        if asset.get("asset_type") in allowed_types
        and asset.get("latitude") is not None
        and asset.get("longitude") is not None
    ]


def cap_by_asset_identity(base_confidence: float, asset: dict[str, Any]) -> float:
    asset_confidence = numeric(asset.get("confidence_score"))

    if asset_confidence is None:
        asset_confidence = 0.50

    return round(min(base_confidence, asset_confidence), 3)


def match_reservoir_station(
    *,
    station: str,
    district: str | None,
    latitude: float,
    longitude: float,
    asset_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    candidates = assets_of_type(asset_rows, {"dam", "barrage"})

    station_district = normalize_district(district)

    best_direct: dict[str, Any] | None = None
    best_near: dict[str, Any] | None = None

    for asset in candidates:
        asset_lat = float(asset["latitude"])
        asset_lon = float(asset["longitude"])

        distance = distance_km(latitude, longitude, asset_lat, asset_lon)
        similarity = name_similarity(station, asset.get("name"))

        asset_district = normalize_district(asset.get("district"))
        same_district = bool(
            station_district
            and asset_district
            and station_district == asset_district
        )

        # Direct association requires both a convincing name and close location.
        if similarity >= 0.82 and distance <= RESERVOIR_DIRECT_MAX_DISTANCE_KM:
            base_confidence = 0.90 + min(0.08, (similarity - 0.82) * 0.40)
            if distance <= 1.0:
                base_confidence += 0.02
            if same_district:
                base_confidence += 0.02

            candidate = {
                "asset": asset,
                "method": "NWDP_RESERVOIR_NAME_LOCATION",
                "confidence": cap_by_asset_identity(
                    min(base_confidence, 0.99), asset
                ),
                "is_estimated": False,
                "distance_km": round(distance, 3),
                "name_similarity": round(similarity, 3),
            }

            if best_direct is None or candidate["confidence"] > best_direct["confidence"]:
                best_direct = candidate

            continue

        # Location-only association is allowed only when extremely close and
        # there is at least weak textual/district support. It remains estimated.
        if distance <= RESERVOIR_NEAR_MAX_DISTANCE_KM and (
            similarity >= 0.50 or same_district
        ):
            base_confidence = 0.82
            if similarity >= 0.65:
                base_confidence += 0.04
            if same_district:
                base_confidence += 0.03

            candidate = {
                "asset": asset,
                "method": "NWDP_NEAREST_RESERVOIR_2KM",
                "confidence": cap_by_asset_identity(
                    min(base_confidence, 0.92), asset
                ),
                "is_estimated": True,
                "distance_km": round(distance, 3),
                "name_similarity": round(similarity, 3),
            }

            if best_near is None or candidate["confidence"] > best_near["confidence"]:
                best_near = candidate

    return best_direct or best_near


def match_nearest_asset(
    *,
    latitude: float,
    longitude: float,
    asset_rows: list[dict[str, Any]],
    allowed_types: set[str],
    max_distance_km: float,
    method: str,
    base_confidence: float,
) -> dict[str, Any] | None:
    best_asset: dict[str, Any] | None = None
    best_distance: float | None = None

    for asset in assets_of_type(asset_rows, allowed_types):
        distance = distance_km(
            latitude,
            longitude,
            float(asset["latitude"]),
            float(asset["longitude"]),
        )

        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_asset = asset

    if (
        best_asset is None
        or best_distance is None
        or best_distance > max_distance_km
    ):
        return None

    ratio = best_distance / max_distance_km if max_distance_km > 0 else 1.0
    confidence = max(0.55, base_confidence - ratio * 0.20)

    return {
        "asset": best_asset,
        "method": method,
        "confidence": cap_by_asset_identity(confidence, best_asset),
        "is_estimated": True,
        "distance_km": round(best_distance, 3),
        "name_similarity": None,
    }


def resolve_station(
    *,
    kind: str,
    station: str,
    district: str | None,
    latitude: float,
    longitude: float,
    asset_rows: list[dict[str, Any]],
) -> dict[str, Any] | None:
    if kind in {"reservoir_level", "reservoir_storage"}:
        return match_reservoir_station(
            station=station,
            district=district,
            latitude=latitude,
            longitude=longitude,
            asset_rows=asset_rows,
        )

    if kind in {"river_level", "river_velocity_discharge"}:
        return match_nearest_asset(
            latitude=latitude,
            longitude=longitude,
            asset_rows=asset_rows,
            allowed_types={"bridge", "barrage", "dam"},
            max_distance_km=RIVER_MAX_DISTANCE_KM,
            method="NWDP_NEAREST_RIVER_STATION_5KM",
            base_confidence=0.90,
        )

    if kind == "rainfall":
        return match_nearest_asset(
            latitude=latitude,
            longitude=longitude,
            asset_rows=asset_rows,
            allowed_types={"bridge", "barrage", "dam"},
            max_distance_km=RAIN_MAX_DISTANCE_KM,
            method="NWDP_NEAREST_RAIN_GAUGE_25KM",
            base_confidence=0.88,
        )

    return None


# ============================================================
# Observation insertion
# ============================================================


async def observation_exists(
    session,
    *,
    asset_id: int,
    variable: str,
    observed_at: datetime,
    source_id: int,
) -> bool:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM environment_observations
            WHERE asset_id = CAST(:asset_id AS INTEGER)
              AND variable = CAST(:variable AS VARCHAR)
              AND observed_at = CAST(:observed_at AS TIMESTAMPTZ)
              AND source_id = CAST(:source_id AS INTEGER)
            LIMIT 1
            """
        ),
        {
            "asset_id": int(asset_id),
            "variable": str(variable),
            "observed_at": observed_at,
            "source_id": int(source_id),
        },
    )

    return result.scalar_one_or_none() is not None


async def insert_observation(
    session,
    *,
    asset_id: int,
    variable: str,
    value: float,
    unit: str,
    observed_at: datetime,
    source_id: int,
    spatial_method: str,
    confidence: float,
    is_estimated: bool,
    is_derived: bool,
) -> bool:
    if await observation_exists(
        session,
        asset_id=asset_id,
        variable=variable,
        observed_at=observed_at,
        source_id=source_id,
    ):
        return False

    if is_derived and is_estimated:
        quality_flag = "OFFICIAL_DERIVED_SPATIAL"
    elif is_derived:
        quality_flag = "OFFICIAL_DERIVED"
    elif is_estimated:
        quality_flag = "OFFICIAL_SPATIAL_TRANSFER"
    else:
        quality_flag = "OFFICIAL_DIRECT"

    params = {
        "asset_id": int(asset_id),
        "variable": str(variable),
        "value": float(value),
        "unit": str(unit),
        "observed_at": observed_at,
        "source_id": int(source_id),
        "source_type": SOURCE_TYPE,
        "spatial_method": str(spatial_method),
        "quality_flag": quality_flag,
        "confidence": float(confidence),
        "is_estimated": bool(is_estimated),
    }

    # Use VALUES and explicit casts. This avoids asyncpg's ambiguous parameter
    # inference that occurred in the previous INSERT ... SELECT implementation.
    result = await session.execute(
        text(
            """
            INSERT INTO environment_observations (
                asset_id,
                variable,
                value,
                unit,
                observed_at,
                ingested_at,
                source_id,
                source_type,
                spatial_method,
                quality_flag,
                confidence_score,
                is_estimated
            )
            VALUES (
                CAST(:asset_id AS INTEGER),
                CAST(:variable AS VARCHAR),
                CAST(:value AS DOUBLE PRECISION),
                CAST(:unit AS VARCHAR),
                CAST(:observed_at AS TIMESTAMPTZ),
                NOW(),
                CAST(:source_id AS INTEGER),
                CAST(:source_type AS VARCHAR),
                CAST(:spatial_method AS VARCHAR),
                CAST(:quality_flag AS VARCHAR),
                CAST(:confidence AS DOUBLE PRECISION),
                CAST(:is_estimated AS BOOLEAN)
            )
            RETURNING id
            """
        ),
        params,
    )

    return result.scalar_one_or_none() is not None


# ============================================================
# CSV validation and reading
# ============================================================


def required_columns(config: dict[str, str]) -> set[str]:
    required = {
        config["station"],
        config["district"],
        config["latitude"],
        config["longitude"],
        config["time"],
    }

    kind = config["kind"]

    if kind in {"rainfall", "reservoir_level", "reservoir_storage", "river_level"}:
        required.add(config["value"])
    elif kind == "river_velocity_discharge":
        required.update(
            {
                config["level"],
                config["velocity"],
                config["discharge"],
            }
        )

    return required


def validate_headers(path: Path, fieldnames: list[str], config: dict[str, str]) -> None:
    missing = required_columns(config) - set(fieldnames)

    if missing:
        raise RuntimeError(
            f"{path.name}: missing expected NWDP columns: "
            + ", ".join(sorted(missing))
        )


def read_rows(
    path: Path,
    config: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    rows: list[dict[str, Any]] = []

    stats = {
        "file_rows": 0,
        "valid_rows": 0,
        "invalid_time": 0,
        "invalid_coordinate": 0,
        "missing_station": 0,
    }

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        if not reader.fieldnames:
            return rows, stats

        validate_headers(path, list(reader.fieldnames), config)

        for raw in reader:
            stats["file_rows"] += 1

            station = (raw.get(config["station"]) or "").strip()
            if not station:
                stats["missing_station"] += 1
                continue

            observed_at = parse_nwdp_time(raw.get(config["time"]))
            if observed_at is None:
                stats["invalid_time"] += 1
                continue

            latitude = numeric(raw.get(config["latitude"]))
            longitude = numeric(raw.get(config["longitude"]))

            if (
                latitude is None
                or longitude is None
                or not valid_ap_coordinate(latitude, longitude)
            ):
                stats["invalid_coordinate"] += 1
                continue

            rows.append(
                {
                    "raw": raw,
                    "station": station,
                    "district": raw.get(config["district"]),
                    "latitude": latitude,
                    "longitude": longitude,
                    "observed_at": observed_at,
                }
            )
            stats["valid_rows"] += 1

    return rows, stats


# ============================================================
# Feature preparation
# ============================================================


def rainfall_observations(
    rows: list[dict[str, Any]],
    config: dict[str, str],
) -> list[dict[str, Any]]:
    groups: dict[tuple[str, float, float], list[tuple[datetime, float, dict[str, Any]]]] = defaultdict(list)

    for row in rows:
        value = numeric(row["raw"].get(config["value"]))

        # Rainfall cannot be negative.
        if value is None or value < 0:
            continue

        key = (
            row["station"],
            round(row["latitude"], 6),
            round(row["longitude"], 6),
        )

        groups[key].append((row["observed_at"], value, row))

    output: list[dict[str, Any]] = []

    for records in groups.values():
        records.sort(key=lambda item: item[0])

        latest_time, latest_value, latest_row = records[-1]
        start_24h = latest_time - timedelta(hours=24)
        start_7d = latest_time - timedelta(days=7)

        values_24h = [
            value
            for timestamp, value, _ in records
            if start_24h < timestamp <= latest_time
        ]

        values_7d = [
            value
            for timestamp, value, _ in records
            if start_7d < timestamp <= latest_time
        ]

        base = {
            "station": latest_row["station"],
            "district": latest_row["district"],
            "latitude": latest_row["latitude"],
            "longitude": latest_row["longitude"],
            "observed_at": latest_time,
        }

        output.append(
            {
                **base,
                "variable": "rainfall_1h",
                "value": latest_value,
                "unit": "mm",
                "is_derived": False,
            }
        )

        # The NWDP resource is labelled hourly rainfall. We sum the available
        # official observations in each window. These are explicitly marked
        # DERIVED in quality_flag when inserted.
        if values_24h:
            output.append(
                {
                    **base,
                    "variable": "rainfall_24h",
                    "value": sum(values_24h),
                    "unit": "mm",
                    "is_derived": True,
                }
            )

        if values_7d:
            output.append(
                {
                    **base,
                    "variable": "rainfall_7d",
                    "value": sum(values_7d),
                    "unit": "mm",
                    "is_derived": True,
                }
            )

    return output


def latest_station_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    latest: dict[tuple[str, float, float], dict[str, Any]] = {}

    for row in rows:
        key = (
            row["station"],
            round(row["latitude"], 6),
            round(row["longitude"], 6),
        )

        current = latest.get(key)
        if current is None or row["observed_at"] > current["observed_at"]:
            latest[key] = row

    return list(latest.values())


def latest_observations(
    rows: list[dict[str, Any]],
    config: dict[str, str],
) -> list[dict[str, Any]]:
    kind = config["kind"]
    output: list[dict[str, Any]] = []

    for row in latest_station_rows(rows):
        raw = row["raw"]

        base = {
            "station": row["station"],
            "district": row["district"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "observed_at": row["observed_at"],
            "is_derived": False,
        }

        if kind == "reservoir_level":
            value = numeric(raw.get(config["value"]))
            if value is not None:
                output.append(
                    {
                        **base,
                        "variable": "reservoir_level",
                        "value": value,
                        "unit": "m",
                    }
                )

        elif kind == "reservoir_storage":
            value = numeric(raw.get(config["value"]))
            if value is not None:
                output.append(
                    {
                        **base,
                        "variable": "reservoir_storage",
                        "value": value,
                        "unit": "MCM",
                    }
                )

        elif kind == "river_level":
            value = numeric(raw.get(config["value"]))
            if value is not None:
                output.append(
                    {
                        **base,
                        "variable": "river_level",
                        "value": value,
                        "unit": "m",
                    }
                )

        elif kind == "river_velocity_discharge":
            level = numeric(raw.get(config["level"]))
            velocity = numeric(raw.get(config["velocity"]))
            discharge = numeric(raw.get(config["discharge"]))

            if level is not None:
                output.append(
                    {
                        **base,
                        "variable": "river_level",
                        "value": level,
                        "unit": "m",
                    }
                )

            if velocity is not None:
                output.append(
                    {
                        **base,
                        "variable": "river_velocity",
                        "value": velocity,
                        "unit": "m/s",
                    }
                )

            if discharge is not None:
                output.append(
                    {
                        **base,
                        "variable": "river_discharge",
                        "value": discharge,
                        "unit": "m3/s",
                    }
                )

    return output


# ============================================================
# File processing
# ============================================================


async def process_file(
    session,
    *,
    path: Path,
    config: dict[str, str],
    source_id: int,
    asset_rows: list[dict[str, Any]],
    commit: bool,
) -> dict[str, int]:
    kind = config["kind"]

    rows, read_stats = read_rows(path, config)

    if kind == "rainfall":
        observations = rainfall_observations(rows, config)
    else:
        observations = latest_observations(rows, config)

    stats: dict[str, int] = {
        **read_stats,
        "prepared_observations": len(observations),
        "matched": 0,
        "unmatched": 0,
        "inserted": 0,
        "duplicates": 0,
    }

    station_cache: dict[tuple[str, float, float], dict[str, Any] | None] = {}
    samples_printed = 0

    for observation in observations:
        station_key = (
            observation["station"],
            round(observation["latitude"], 6),
            round(observation["longitude"], 6),
        )

        if station_key not in station_cache:
            station_cache[station_key] = resolve_station(
                kind=kind,
                station=observation["station"],
                district=observation["district"],
                latitude=observation["latitude"],
                longitude=observation["longitude"],
                asset_rows=asset_rows,
            )

        match = station_cache[station_key]

        if match is None:
            stats["unmatched"] += 1
            continue

        stats["matched"] += 1
        asset = match["asset"]

        if samples_printed < 12:
            print(
                "MATCH:",
                observation["station"],
                "->",
                asset["asset_code"],
                "|",
                asset["name"],
                "|",
                observation["variable"],
                "| distance_km=",
                match["distance_km"],
                "| confidence=",
                match["confidence"],
                "| identity=",
                asset.get("identity_status"),
            )
            samples_printed += 1

        if not commit:
            continue

        inserted = await insert_observation(
            session,
            asset_id=int(asset["id"]),
            variable=str(observation["variable"]),
            value=float(observation["value"]),
            unit=str(observation["unit"]),
            observed_at=observation["observed_at"],
            source_id=source_id,
            spatial_method=str(match["method"]),
            confidence=float(match["confidence"]),
            is_estimated=bool(match["is_estimated"]),
            is_derived=bool(observation.get("is_derived", False)),
        )

        if inserted:
            stats["inserted"] += 1
        else:
            stats["duplicates"] += 1

    return stats


# ============================================================
# Main
# ============================================================


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import AP NWDP environmental observations into SIMRAS."
    )

    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write matched observations to PostgreSQL. Without this flag the run is dry-run only.",
    )

    parser.add_argument(
        "--replace",
        action="store_true",
        help=(
            "Delete existing NWDP_AP_SW environment observations before importing. "
            "Requires --commit. Use only when intentionally rebuilding NWDP mappings."
        ),
    )

    args = parser.parse_args()

    if args.replace and not args.commit:
        parser.error("--replace requires --commit")

    async for session in get_db():
        source_id = await get_source_id(session)
        asset_rows = await load_assets(session)

        print("=" * 60)
        print("SIMRAS NWDP AP IMPORTER")
        print("=" * 60)
        print("Source code:", SOURCE_CODE)
        print("Infrastructure assets:", len(asset_rows))
        print("Mode:", "COMMIT" if args.commit else "DRY RUN")
        print("River transfer radius:", f"{RIVER_MAX_DISTANCE_KM:.1f} km")
        print("Rainfall transfer radius:", f"{RAIN_MAX_DISTANCE_KM:.1f} km")

        if args.replace:
            deleted = await delete_existing_source_observations(session, source_id)
            print("Existing NWDP observations deleted:", deleted)

        summaries: dict[str, dict[str, int]] = {}

        try:
            for filename, config in FILES.items():
                path = DATA_DIR / filename

                print()
                print("-" * 60)
                print("FILE:", filename)
                print("TYPE:", config["kind"])

                if not path.exists():
                    print("SKIPPED: file missing")
                    continue

                stats = await process_file(
                    session,
                    path=path,
                    config=config,
                    source_id=source_id,
                    asset_rows=asset_rows,
                    commit=args.commit,
                )

                summaries[filename] = stats
                print("STATS:", stats)

            if args.commit:
                await session.commit()
                print()
                print("DATABASE COMMIT COMPLETE")
            else:
                await session.rollback()
                print()
                print("DRY RUN COMPLETE - DATABASE NOT MODIFIED")

        except Exception:
            await session.rollback()
            print()
            print("IMPORT FAILED - TRANSACTION ROLLED BACK")
            raise

        print()
        print("=" * 60)
        print("SUMMARY")
        print("=" * 60)

        total_inserted = 0
        total_matched = 0

        for filename, stats in summaries.items():
            print(filename, stats)
            total_inserted += stats.get("inserted", 0)
            total_matched += stats.get("matched", 0)

        print()
        print("TOTAL MATCHED OBSERVATIONS:", total_matched)
        print("TOTAL INSERTED OBSERVATIONS:", total_inserted)

        break


if __name__ == "__main__":
    asyncio.run(main())
