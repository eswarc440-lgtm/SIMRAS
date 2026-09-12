from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd

LEVEL_COLUMN = "Manual Daily Reservoir water level (m)"
STORAGE_COLUMN = "Manual Daily Reservoir storage (mcm)"
TIME_COLUMN = "Data Acquisition Time"
STATION_COLUMN = "Station"
LATITUDE_COLUMN = "Latitude"
LONGITUDE_COLUMN = "Longitude"


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius_km = 6371.0088
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    value = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return radius_km * 2 * math.asin(math.sqrt(value))


def _select_station(frame: pd.DataFrame, station_pattern: str) -> pd.DataFrame:
    required = {
        STATION_COLUMN,
        TIME_COLUMN,
        LATITUDE_COLUMN,
        LONGITUDE_COLUMN,
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    selected = frame[
        frame[STATION_COLUMN]
        .astype(str)
        .str.contains(station_pattern, case=False, regex=False, na=False)
    ].copy()
    if selected.empty:
        raise ValueError(f"Station not found: {station_pattern}")
    return selected


def _canonical_rows(
    frame: pd.DataFrame,
    *,
    value_column: str,
    variable: str,
    unit: str,
    asset_code: str,
    station_pattern: str,
    asset_latitude: float,
    asset_longitude: float,
    maximum_distance_km: float,
) -> pd.DataFrame:
    if value_column not in frame.columns:
        raise ValueError(f"Missing measurement column: {value_column}")
    selected = _select_station(frame, station_pattern)
    selected[value_column] = pd.to_numeric(selected[value_column], errors="coerce")
    selected[TIME_COLUMN] = pd.to_datetime(
        selected[TIME_COLUMN], format="%d-%m-%Y %H:%M", errors="coerce"
    )
    if selected[value_column].isna().any() or selected[TIME_COLUMN].isna().any():
        raise ValueError(f"Invalid {variable} value or timestamp")
    if (selected[value_column] < 0).any():
        raise ValueError(f"Negative {variable} observation")

    station_locations = selected[[LATITUDE_COLUMN, LONGITUDE_COLUMN]].drop_duplicates()
    distances = station_locations.apply(
        lambda row: _distance_km(
            asset_latitude,
            asset_longitude,
            float(row[LATITUDE_COLUMN]),
            float(row[LONGITUDE_COLUMN]),
        ),
        axis=1,
    )
    if float(distances.max()) > maximum_distance_km:
        raise ValueError(
            f"{variable} station is {float(distances.max()):.3f} km from the asset; "
            f"maximum is {maximum_distance_km:.3f} km"
        )

    observed_at = (
        selected[TIME_COLUMN]
        .dt.tz_localize("Asia/Kolkata")
        .dt.tz_convert("UTC")
        .map(lambda value: value.isoformat().replace("+00:00", "Z"))
    )
    output = pd.DataFrame(
        {
            "asset_code": asset_code,
            "variable": variable,
            "value": selected[value_column].astype(float),
            "unit": unit,
            "observed_at": observed_at,
            "source_code": "NWDP_AP_RESERVOIR_DAILY",
            "source_type": "OBSERVED",
            "spatial_method": "exact_station_name_and_coordinate_match",
            "quality_flag": "MANUAL_GOVERNMENT_OBSERVATION",
            "confidence_score": 0.90,
            "is_estimated": False,
            "station_name": selected[STATION_COLUMN].astype(str),
            "station_latitude": selected[LATITUDE_COLUMN].astype(float),
            "station_longitude": selected[LONGITUDE_COLUMN].astype(float),
        }
    )
    if output.duplicated(["asset_code", "variable", "observed_at"]).any():
        raise ValueError(f"Duplicate {variable} observations")
    return output.sort_values("observed_at")


def build_reservoir_observations(
    level_path: str | Path,
    storage_path: str | Path,
    output_path: str | Path,
    *,
    asset_code: str = "AP_DAM_NWDP_AP01VH0059",
    station_pattern: str = "SRI SAILAM PROJECT",
    asset_latitude: float = 16.0866523,
    asset_longitude: float = 78.8967766,
    maximum_distance_km: float = 2.0,
) -> dict[str, object]:
    level = pd.read_csv(level_path)
    storage = pd.read_csv(storage_path)
    level_rows = _canonical_rows(
        level,
        value_column=LEVEL_COLUMN,
        variable="reservoir_level",
        unit="m",
        asset_code=asset_code,
        station_pattern=station_pattern,
        asset_latitude=asset_latitude,
        asset_longitude=asset_longitude,
        maximum_distance_km=maximum_distance_km,
    )
    storage_rows = _canonical_rows(
        storage,
        value_column=STORAGE_COLUMN,
        variable="reservoir_storage",
        unit="mcm",
        asset_code=asset_code,
        station_pattern=station_pattern,
        asset_latitude=asset_latitude,
        asset_longitude=asset_longitude,
        maximum_distance_km=maximum_distance_km,
    )
    combined = pd.concat([level_rows, storage_rows], ignore_index=True)
    combined = combined.sort_values(["observed_at", "variable"])
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)
    return {
        "records": len(combined),
        "variables": {
            key: int(value)
            for key, value in combined["variable"].value_counts().sort_index().items()
        },
        "latest_observed_at": combined["observed_at"].max(),
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build verified NWDP reservoir observations")
    parser.add_argument(
        "--level",
        default="/data/raw/nwdp-ap-reservoir-level-2026-2030.csv",
    )
    parser.add_argument(
        "--storage",
        default="/data/raw/nwdp-ap-reservoir-storage-2026-2030.csv",
    )
    parser.add_argument(
        "--output",
        default="/data/processed/nwdp-reservoir-AP_DAM_NWDP_AP01VH0059.csv",
    )
    args = parser.parse_args()
    result = build_reservoir_observations(args.level, args.storage, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
