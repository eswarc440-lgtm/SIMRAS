from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from simras_etl.nwdp_reservoir import (
    LEVEL_COLUMN,
    STORAGE_COLUMN,
    _canonical_rows,
)

MATCH_REQUIRED_COLUMNS = {
    "station_name",
    "asset_code",
    "asset_latitude",
    "asset_longitude",
    "distance_km",
    "level_records",
    "storage_records",
    "match_status",
}


def build_matched_reservoir_observations(
    level_path: str | Path,
    storage_path: str | Path,
    matches_path: str | Path,
    output_path: str | Path,
    *,
    maximum_distance_km: float = 2.0,
) -> dict[str, object]:
    level = pd.read_csv(level_path)
    storage = pd.read_csv(storage_path)
    matches = pd.read_csv(matches_path)
    missing = MATCH_REQUIRED_COLUMNS.difference(matches.columns)
    if missing:
        raise ValueError(f"Station match report is missing columns: {sorted(missing)}")

    approved = matches[matches["match_status"].eq("AUTO_MATCH")].copy()
    if approved.empty:
        raise ValueError("Station match report contains no AUTO_MATCH records")
    approved["distance_km"] = pd.to_numeric(approved["distance_km"], errors="coerce")
    if approved["distance_km"].isna().any() or (
        approved["distance_km"] > maximum_distance_km
    ).any():
        raise ValueError("AUTO_MATCH record exceeds the maximum station distance")
    if approved["asset_code"].duplicated().any():
        raise ValueError("AUTO_MATCH records contain duplicate asset assignments")

    frames: list[pd.DataFrame] = []
    for match in approved.itertuples(index=False):
        common = {
            "asset_code": str(match.asset_code),
            "station_pattern": str(match.station_name),
            "asset_latitude": float(match.asset_latitude),
            "asset_longitude": float(match.asset_longitude),
            "maximum_distance_km": maximum_distance_km,
        }
        expected_level = int(match.level_records)
        expected_storage = int(match.storage_records)
        if expected_level:
            level_rows = _canonical_rows(
                level,
                value_column=LEVEL_COLUMN,
                variable="reservoir_level",
                unit="m",
                **common,
            )
            if len(level_rows) != expected_level:
                raise ValueError(
                    f"Level record count changed for {match.station_name}: "
                    f"expected {expected_level}, got {len(level_rows)}"
                )
            frames.append(level_rows)
        if expected_storage:
            storage_rows = _canonical_rows(
                storage,
                value_column=STORAGE_COLUMN,
                variable="reservoir_storage",
                unit="mcm",
                **common,
            )
            if len(storage_rows) != expected_storage:
                raise ValueError(
                    f"Storage record count changed for {match.station_name}: "
                    f"expected {expected_storage}, got {len(storage_rows)}"
                )
            frames.append(storage_rows)

    if not frames:
        raise ValueError("Approved stations contain no observations")
    combined = pd.concat(frames, ignore_index=True)
    identity = ["asset_code", "variable", "observed_at"]
    if combined.duplicated(identity).any():
        raise ValueError("Matched reservoir output contains duplicate observations")
    combined = combined.sort_values(identity)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(output, index=False)

    asset_counts = {
        key: int(value)
        for key, value in combined["asset_code"].value_counts().sort_index().items()
    }
    variable_counts = {
        key: int(value)
        for key, value in combined["variable"].value_counts().sort_index().items()
    }
    return {
        "records": len(combined),
        "assets": len(asset_counts),
        "asset_records": asset_counts,
        "variables": variable_counts,
        "latest_observed_at": combined["observed_at"].max(),
        "output": str(output),
    }


def main() -> None:
    result = build_matched_reservoir_observations(
        "/data/raw/nwdp-ap-reservoir-level-2026-2030.csv",
        "/data/raw/nwdp-ap-reservoir-storage-2026-2030.csv",
        "/data/processed/nwdp-reservoir-station-matches.csv",
        "/data/processed/nwdp-reservoir-auto-matched.csv",
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
