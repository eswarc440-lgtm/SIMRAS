from __future__ import annotations

import argparse
import asyncio
import csv
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

POWER_DAILY_POINT_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_PARAMETERS = ("T2M", "PRECTOTCORR", "RH2M", "WS10M")
FILL_VALUE = -999.0

PARAMETER_CONTRACT = {
    "T2M": ("temperature_2m", "degC"),
    "PRECTOTCORR": ("rainfall_24h", "mm"),
    "RH2M": ("relative_humidity_2m", "percent"),
    "WS10M": ("wind_speed_10m", "m/s"),
}


async def fetch_daily_weather(
    *,
    latitude: float,
    longitude: float,
    start: str,
    end: str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    owns_client = client is None
    client = client or httpx.AsyncClient(timeout=120)
    params = {
        "parameters": ",".join(POWER_PARAMETERS),
        "community": "AG",
        "longitude": longitude,
        "latitude": latitude,
        "start": start,
        "end": end,
        "format": "JSON",
    }
    try:
        response = await client.get(POWER_DAILY_POINT_URL, params=params)
        response.raise_for_status()
        return response.json()
    finally:
        if owns_client:
            await client.aclose()


def _valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and float(value) != FILL_VALUE


def _base_row(
    *,
    asset_code: str,
    variable: str,
    value: float,
    unit: str,
    observed_at: str,
    source_record_id: str,
) -> dict[str, Any]:
    return {
        "asset_code": asset_code,
        "variable": variable,
        "value": round(float(value), 6),
        "unit": unit,
        "observed_at": observed_at,
        "source_record_id": source_record_id,
        "source_type": "REANALYSIS",
        "spatial_method": "NASA_POWER_POINT_GRID_0.5x0.625_DEG",
        "quality_flag": "MODELLED_REANALYSIS",
        "confidence_score": 0.75,
        "is_estimated": True,
    }


def build_observation_rows(
    payload: dict[str, Any],
    *,
    asset_code: str,
) -> list[dict[str, Any]]:
    parameters = payload.get("properties", {}).get("parameter", {})
    missing = set(POWER_PARAMETERS) - set(parameters)
    if missing:
        raise ValueError(f"NASA POWER response is missing parameters: {sorted(missing)}")

    rows: list[dict[str, Any]] = []
    precipitation: list[tuple[str, float]] = []
    for parameter in POWER_PARAMETERS:
        variable, unit = PARAMETER_CONTRACT[parameter]
        for date_key, raw_value in sorted(parameters[parameter].items()):
            if not _valid_number(raw_value):
                continue
            observed_at = datetime.strptime(date_key, "%Y%m%d").replace(tzinfo=UTC).isoformat()
            rows.append(
                _base_row(
                    asset_code=asset_code,
                    variable=variable,
                    value=float(raw_value),
                    unit=unit,
                    observed_at=observed_at,
                    source_record_id=f"{asset_code}:{parameter}:{date_key}",
                )
            )
            if parameter == "PRECTOTCORR":
                precipitation.append((date_key, float(raw_value)))

    # Create a rolling seven-day total for every complete seven-day window.
    precipitation.sort()
    for index in range(6, len(precipitation)):
        window = precipitation[index - 6 : index + 1]
        last_date = window[-1][0]
        observed_at = datetime.strptime(last_date, "%Y%m%d").replace(tzinfo=UTC).isoformat()
        rows.append(
            _base_row(
                asset_code=asset_code,
                variable="rainfall_7d",
                value=sum(value for _, value in window),
                unit="mm",
                observed_at=observed_at,
                source_record_id=f"{asset_code}:RAINFALL7D:{last_date}",
            )
        )
    return rows


def write_observations_csv(rows: Iterable[dict[str, Any]], output_path: str | Path) -> Path:
    rows = list(rows)
    if not rows:
        raise ValueError("No NASA POWER observations were produced")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch NASA POWER weather for a SIMRAS asset")
    parser.add_argument("--asset-code", default="AP_DAM_00001")
    parser.add_argument("--latitude", type=float, default=16.5075)
    parser.add_argument("--longitude", type=float, default=80.605277778)
    parser.add_argument("--start", required=True, help="YYYYMMDD")
    parser.add_argument("--end", required=True, help="YYYYMMDD")
    parser.add_argument("--output", default="/data/processed/nasa-power-AP_DAM_00001.csv")
    args = parser.parse_args()

    payload = asyncio.run(
        fetch_daily_weather(
            latitude=args.latitude,
            longitude=args.longitude,
            start=args.start,
            end=args.end,
        )
    )
    rows = build_observation_rows(payload, asset_code=args.asset_code)
    output = write_observations_csv(rows, args.output)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["variable"]] = counts.get(row["variable"], 0) + 1
    print(json.dumps({"records": len(rows), "variables": counts, "output": str(output)}, indent=2))


if __name__ == "__main__":
    main()
