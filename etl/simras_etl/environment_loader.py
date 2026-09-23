from __future__ import annotations

import csv
import os
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import asyncpg


@dataclass(frozen=True, slots=True)
class SourceDefinition:
    code: str
    name: str
    organisation: str
    source_type: str
    url: str
    licence: str | None
    refresh_policy: str
    is_authoritative: bool
    observation_source_type: str
    quality_flag: str
    is_estimated: bool


SOURCES = {
    "NASA_POWER_DAILY": SourceDefinition(
        code="NASA_POWER_DAILY",
        name="NASA POWER Daily Meteorology",
        organisation="NASA Langley Research Center",
        source_type="REANALYSIS",
        url="https://power.larc.nasa.gov/",
        licence=None,
        refresh_policy="Daily point refresh; retain modelled-data label",
        is_authoritative=True,
        observation_source_type="REANALYSIS",
        quality_flag="MODELLED_REANALYSIS",
        is_estimated=True,
    ),
    "NWDP_AP_RESERVOIR_DAILY": SourceDefinition(
        code="NWDP_AP_RESERVOIR_DAILY",
        name="AP Reservoir Level and Storage (Manual Daily)",
        organisation="Andhra Pradesh Surface Water Department / NWIC",
        source_type="OFFICIAL_TIME_SERIES",
        url=(
            "https://www.nwdp.nwic.gov.in/dataset/"
            "reservoir-water-level-manual-daily-andhra-pradesh-surface-water-department"
        ),
        licence=None,
        refresh_policy="Refresh from published NWDP CSV/API snapshot",
        is_authoritative=True,
        observation_source_type="OBSERVED",
        quality_flag="MANUAL_GOVERNMENT_OBSERVATION",
        is_estimated=False,
    ),
}

REQUIRED_FIELDS = {
    "asset_code",
    "variable",
    "value",
    "unit",
    "observed_at",
    "source_type",
    "spatial_method",
    "quality_flag",
    "confidence_score",
    "is_estimated",
}


def asyncpg_dsn(database_url: str) -> str:
    """Convert SQLAlchemy's asyncpg URL into a DSN accepted by asyncpg."""
    return database_url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().casefold()
    if normalized in {"true", "t", "1", "yes"}:
        return True
    if normalized in {"false", "f", "0", "no"}:
        return False
    raise ValueError(f"Invalid boolean value: {value!r}")


def _as_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"Timestamp must include a timezone: {value!r}")
    return parsed


def validate_observations(
    rows: Iterable[dict[str, Any]], source_code: str
) -> list[dict[str, Any]]:
    source = SOURCES.get(source_code)
    if source is None:
        raise ValueError(f"Unsupported environment source: {source_code}")

    validated: list[dict[str, Any]] = []
    seen: set[tuple[str, str, datetime]] = set()
    for index, raw in enumerate(rows, start=1):
        missing = REQUIRED_FIELDS.difference(raw)
        if missing:
            raise ValueError(f"Observation {index} is missing fields: {sorted(missing)}")
        if raw.get("source_code") not in (None, "", source_code):
            raise ValueError(f"Observation {index} has the wrong source code")

        row = {
            "asset_code": str(raw["asset_code"]).strip(),
            "variable": str(raw["variable"]).strip(),
            "value": float(raw["value"]),
            "unit": str(raw["unit"]).strip(),
            "observed_at": _as_datetime(raw["observed_at"]),
            "source_type": str(raw["source_type"]).strip(),
            "spatial_method": str(raw["spatial_method"]).strip(),
            "quality_flag": str(raw["quality_flag"]).strip(),
            "confidence_score": float(raw["confidence_score"]),
            "is_estimated": _as_bool(raw["is_estimated"]),
        }
        if not row["asset_code"] or not row["variable"] or not row["unit"]:
            raise ValueError(f"Observation {index} contains an empty identifier")
        if not 0 <= row["confidence_score"] <= 1:
            raise ValueError(f"Observation {index} has invalid confidence")
        if (
            row["source_type"] != source.observation_source_type
            or row["quality_flag"] != source.quality_flag
            or row["is_estimated"] is not source.is_estimated
        ):
            raise ValueError(f"Observation {index} has invalid provenance")

        identity = (row["asset_code"], row["variable"], row["observed_at"])
        if identity in seen:
            raise ValueError(f"Duplicate observation: {identity}")
        seen.add(identity)
        validated.append(row)

    if not validated:
        raise ValueError("No environment observations were provided")
    return validated


def read_observations_csv(path: str | Path) -> list[dict[str, Any]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


async def load_environment_observations(
    rows: Iterable[dict[str, Any]],
    *,
    source_code: str,
    database_url: str | None = None,
) -> dict[str, Any]:
    validated = validate_observations(rows, source_code)
    source = SOURCES[source_code]
    database_url = database_url or os.environ.get("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is not configured")

    connection = await asyncpg.connect(asyncpg_dsn(database_url))
    try:
        async with connection.transaction():
            await connection.execute(
                """
                INSERT INTO data_sources (
                    code, name, organisation, source_type, url, licence,
                    refresh_policy, is_authoritative
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (code) DO UPDATE SET
                    name = EXCLUDED.name,
                    organisation = EXCLUDED.organisation,
                    source_type = EXCLUDED.source_type,
                    url = EXCLUDED.url,
                    licence = EXCLUDED.licence,
                    refresh_policy = EXCLUDED.refresh_policy,
                    is_authoritative = EXCLUDED.is_authoritative,
                    updated_at = now()
                """,
                source.code,
                source.name,
                source.organisation,
                source.source_type,
                source.url,
                source.licence,
                source.refresh_policy,
                source.is_authoritative,
            )
            source_id = await connection.fetchval(
                "SELECT id FROM data_sources WHERE code = $1", source.code
            )

            asset_codes = sorted({row["asset_code"] for row in validated})
            asset_records = await connection.fetch(
                "SELECT id, asset_code FROM assets WHERE asset_code = ANY($1::text[])",
                asset_codes,
            )
            assets = {record["asset_code"]: record["id"] for record in asset_records}
            missing_assets = sorted(set(asset_codes).difference(assets))
            if missing_assets:
                raise ValueError(f"Unknown asset codes: {missing_assets}")

            if source_code == "NASA_POWER_DAILY":
                await connection.execute(
                    """
                    DELETE FROM environment_observations AS observation
                    USING assets AS asset
                    WHERE observation.asset_id = asset.id
                      AND asset.asset_code = ANY($1::text[])
                      AND observation.source_type = 'SYNTHETIC_DEMO'
                      AND observation.variable IN ('rainfall_24h', 'rainfall_7d')
                    """,
                    asset_codes,
                )

            identities = [
                (
                    assets[row["asset_code"]],
                    source_id,
                    row["variable"],
                    row["observed_at"],
                )
                for row in validated
            ]
            await connection.executemany(
                """
                DELETE FROM environment_observations
                WHERE asset_id = $1
                  AND source_id = $2
                  AND variable = $3
                  AND observed_at = $4
                """,
                identities,
            )

            values = [
                (
                    assets[row["asset_code"]],
                    row["variable"],
                    row["value"],
                    row["unit"],
                    row["observed_at"],
                    source_id,
                    row["source_type"],
                    row["spatial_method"],
                    row["quality_flag"],
                    row["confidence_score"],
                    row["is_estimated"],
                )
                for row in validated
            ]
            await connection.executemany(
                """
                INSERT INTO environment_observations (
                    asset_id, variable, value, unit, observed_at, ingested_at,
                    source_id, source_type, spatial_method, quality_flag,
                    confidence_score, is_estimated
                )
                VALUES ($1, $2, $3, $4, $5, now(), $6, $7, $8, $9, $10, $11)
                """,
                values,
            )
    finally:
        await connection.close()

    counts = Counter(row["variable"] for row in validated)
    return {
        "source_code": source_code,
        "records": len(validated),
        "variables": dict(sorted(counts.items())),
        "assets": sorted({row["asset_code"] for row in validated}),
        "latest_observed_at": max(row["observed_at"] for row in validated).isoformat(),
    }
