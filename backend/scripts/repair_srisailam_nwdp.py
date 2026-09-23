from __future__ import annotations

import argparse
import asyncio
import csv
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.db.session import get_db


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw" / "nwdp"

ASSET_CODE = "AP_DAM_NWDP_AP01VH0059"
SOURCE_CODE = "NWDP_AP_SW"
STATION_NAME = "SRI SAILAM PROJECT"

IST = ZoneInfo("Asia/Kolkata")

FILES = (
    {
        "filename": "ap_reservoir_level_daily_2026_2030.csv",
        "variable": "reservoir_level",
        "value_column": "Manual Daily Reservoir water level (m)",
        "unit": "m",
    },
    {
        "filename": "ap_reservoir_storage_daily_2026_2030.csv",
        "variable": "reservoir_storage",
        "value_column": "Manual Daily Reservoir storage (mcm)",
        "unit": "MCM",
    },
)


def parse_time(value: str) -> datetime:
    parsed = datetime.strptime(value.strip(), "%d-%m-%Y %H:%M")
    return parsed.replace(tzinfo=IST)


def as_float(value: str) -> float:
    return float(value.replace(",", "").strip())


def station_matches(value: str | None) -> bool:
    if not value:
        return False

    normalized = " ".join(
        value.upper()
        .replace(".", " ")
        .replace("_", " ")
        .split()
    )

    target = " ".join(
        STATION_NAME.upper()
        .replace(".", " ")
        .replace("_", " ")
        .split()
    )

    return normalized == target


def latest_station_row(path: Path) -> dict | None:
    latest: dict | None = None
    latest_time: datetime | None = None

    with path.open(
        "r",
        encoding="utf-8-sig",
        errors="replace",
        newline="",
    ) as handle:
        reader = csv.DictReader(handle)

        for row in reader:
            if not station_matches(row.get("Station")):
                continue

            try:
                observed_at = parse_time(
                    row["Data Acquisition Time"]
                )
            except Exception:
                continue

            if latest_time is None or observed_at > latest_time:
                latest_time = observed_at
                latest = dict(row)
                latest["_observed_at"] = observed_at

    return latest


async def get_asset(session):
    result = await session.execute(
        text(
            """
            SELECT id, asset_code, name, identity_status
            FROM assets
            WHERE asset_code = CAST(:asset_code AS VARCHAR)
            LIMIT 1
            """
        ),
        {"asset_code": ASSET_CODE},
    )
    row = result.mappings().first()

    if row is None:
        raise RuntimeError(
            f"Asset {ASSET_CODE} not found"
        )

    return dict(row)


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

    value = result.scalar_one_or_none()

    if value is None:
        raise RuntimeError(
            f"Source {SOURCE_CODE} not found"
        )

    return int(value)


async def insert_observation(
    session,
    *,
    asset_id: int,
    source_id: int,
    variable: str,
    value: float,
    unit: str,
    observed_at: datetime,
) -> bool:
    exists = await session.execute(
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
            "asset_id": asset_id,
            "variable": variable,
            "observed_at": observed_at,
            "source_id": source_id,
        },
    )

    if exists.scalar_one_or_none() is not None:
        return False

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
                'GOVERNMENT_TELEMETRY',
                'NWDP_EXACT_RESERVOIR_STATION',
                'OFFICIAL_DIRECT',
                0.95,
                FALSE
            )
            RETURNING id
            """
        ),
        {
            "asset_id": asset_id,
            "variable": variable,
            "value": value,
            "unit": unit,
            "observed_at": observed_at,
            "source_id": source_id,
        },
    )

    return result.scalar_one_or_none() is not None


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Insert the exact Srisailam NWDP reservoir observations.",
    )
    args = parser.parse_args()

    async for session in get_db():
        asset = await get_asset(session)
        source_id = await get_source_id(session)

        print("=" * 68)
        print("SIMRAS SRISAILAM NWDP REPAIR")
        print("=" * 68)
        print("MODE:", "COMMIT" if args.commit else "DRY RUN")
        print(
            "ASSET:",
            asset["asset_code"],
            "|",
            asset["name"],
            "|",
            asset["identity_status"],
        )

        prepared = 0
        inserted = 0

        for config in FILES:
            path = DATA_DIR / config["filename"]

            if not path.exists():
                print("MISSING:", path)
                continue

            row = latest_station_row(path)

            if row is None:
                print(
                    "NO EXACT STATION ROW:",
                    config["filename"],
                )
                continue

            value = as_float(
                row[config["value_column"]]
            )
            observed_at = row["_observed_at"]

            prepared += 1

            print(
                "FOUND:",
                row["Station"],
                "|",
                config["variable"],
                "=",
                value,
                config["unit"],
                "|",
                observed_at.isoformat(),
            )

            if args.commit:
                did_insert = await insert_observation(
                    session,
                    asset_id=int(asset["id"]),
                    source_id=source_id,
                    variable=config["variable"],
                    value=value,
                    unit=config["unit"],
                    observed_at=observed_at,
                )

                if did_insert:
                    inserted += 1
                    print("  INSERTED")
                else:
                    print("  ALREADY EXISTS")

        if args.commit:
            await session.commit()
            print("DATABASE COMMIT COMPLETE")
        else:
            await session.rollback()
            print("DRY RUN COMPLETE")

        print("PREPARED:", prepared)
        print("INSERTED:", inserted)
        break


if __name__ == "__main__":
    asyncio.run(main())
