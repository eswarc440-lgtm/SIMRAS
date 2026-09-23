from __future__ import annotations

import argparse
import json
import math
import re
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

from simras_etl.nwdp_reservoir import (
    LATITUDE_COLUMN,
    LONGITUDE_COLUMN,
    STATION_COLUMN,
)

GENERIC_NAME_WORDS = {
    "dam",
    "project",
    "reservoir",
    "tank",
}


def normalize_name(value: object) -> str:
    words = re.findall(r"[a-z0-9]+", str(value).casefold())
    filtered = [word for word in words if word not in GENERIC_NAME_WORDS]
    return " ".join(filtered)


def _compact(value: str) -> str:
    return value.replace(" ", "")


def _name_scores(station_name: str, asset_name: str) -> tuple[float, bool]:
    station = normalize_name(station_name)
    asset = normalize_name(asset_name)
    similarity = SequenceMatcher(None, station, asset).ratio()
    station_compact = _compact(station)
    asset_compact = _compact(asset)
    containment = bool(station_compact and asset_compact) and (
        station_compact in asset_compact or asset_compact in station_compact
    )
    return round(similarity, 4), containment


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
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


def _station_inventory(level: pd.DataFrame, storage: pd.DataFrame) -> pd.DataFrame:
    required = {STATION_COLUMN, LATITUDE_COLUMN, LONGITUDE_COLUMN}
    for label, frame in (("level", level), ("storage", storage)):
        missing = required.difference(frame.columns)
        if missing:
            raise ValueError(f"{label} source is missing columns: {sorted(missing)}")

    def summarize(frame: pd.DataFrame, variable: str) -> pd.DataFrame:
        selected = frame[[STATION_COLUMN, LATITUDE_COLUMN, LONGITUDE_COLUMN]].copy()
        selected[LATITUDE_COLUMN] = pd.to_numeric(selected[LATITUDE_COLUMN], errors="coerce")
        selected[LONGITUDE_COLUMN] = pd.to_numeric(selected[LONGITUDE_COLUMN], errors="coerce")
        if selected[[LATITUDE_COLUMN, LONGITUDE_COLUMN]].isna().any().any():
            raise ValueError(f"{variable} source contains invalid coordinates")
        return (
            selected.groupby(
                [STATION_COLUMN, LATITUDE_COLUMN, LONGITUDE_COLUMN], dropna=False
            )
            .size()
            .rename(f"{variable}_records")
            .reset_index()
        )

    level_stations = summarize(level, "level")
    storage_stations = summarize(storage, "storage")
    inventory = level_stations.merge(
        storage_stations,
        on=[STATION_COLUMN, LATITUDE_COLUMN, LONGITUDE_COLUMN],
        how="outer",
    )
    inventory[["level_records", "storage_records"]] = inventory[
        ["level_records", "storage_records"]
    ].fillna(0).astype(int)
    return inventory.sort_values(STATION_COLUMN)


def build_station_match_report(
    level_path: str | Path,
    storage_path: str | Path,
    registry_path: str | Path,
    output_path: str | Path,
    *,
    maximum_distance_km: float = 2.0,
    minimum_name_similarity: float = 0.65,
) -> dict[str, object]:
    level = pd.read_csv(level_path)
    storage = pd.read_csv(storage_path)
    registry = pd.read_csv(registry_path)
    required_registry = {"asset_code", "name", "latitude", "longitude"}
    missing_registry = required_registry.difference(registry.columns)
    if missing_registry:
        raise ValueError(f"Registry is missing columns: {sorted(missing_registry)}")
    registry["latitude"] = pd.to_numeric(registry["latitude"], errors="coerce")
    registry["longitude"] = pd.to_numeric(registry["longitude"], errors="coerce")
    registry = registry.dropna(subset=["latitude", "longitude"]).copy()
    if registry.empty:
        raise ValueError("Registry contains no valid coordinates")

    report: list[dict[str, object]] = []
    for station in _station_inventory(level, storage).itertuples(index=False):
        station_name = str(getattr(station, STATION_COLUMN))
        station_latitude = float(getattr(station, LATITUDE_COLUMN))
        station_longitude = float(getattr(station, LONGITUDE_COLUMN))
        candidates = registry.copy()
        candidates["distance_km"] = candidates.apply(
            lambda asset: distance_km(
                station_latitude,
                station_longitude,
                float(asset["latitude"]),
                float(asset["longitude"]),
            ),
            axis=1,
        )
        nearest = candidates.sort_values("distance_km").iloc[0]
        similarity, containment = _name_scores(station_name, str(nearest["name"]))
        within_distance = float(nearest["distance_km"]) <= maximum_distance_km
        names_compatible = similarity >= minimum_name_similarity or containment
        if within_distance and names_compatible:
            status = "AUTO_MATCH"
        elif within_distance:
            status = "SPATIAL_REVIEW"
        else:
            status = "REVIEW"
        report.append(
            {
                "station_name": station_name,
                "station_latitude": station_latitude,
                "station_longitude": station_longitude,
                "level_records": int(station.level_records),
                "storage_records": int(station.storage_records),
                "asset_code": nearest["asset_code"],
                "asset_name": nearest["name"],
                "asset_latitude": float(nearest["latitude"]),
                "asset_longitude": float(nearest["longitude"]),
                "distance_km": round(float(nearest["distance_km"]), 3),
                "name_similarity": similarity,
                "name_containment": containment,
                "match_status": status,
            }
        )

    output = pd.DataFrame(report)
    duplicate_assets = output.loc[
        output["match_status"].eq("AUTO_MATCH"), "asset_code"
    ].duplicated(keep=False)
    duplicated_codes = set(
        output.loc[
            output["match_status"].eq("AUTO_MATCH"), "asset_code"
        ][duplicate_assets]
    )
    if duplicated_codes:
        output.loc[
            output["asset_code"].isin(duplicated_codes)
            & output["match_status"].eq("AUTO_MATCH"),
            "match_status",
        ] = "AMBIGUOUS_REVIEW"

    output = output.sort_values(["match_status", "distance_km", "station_name"])
    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(destination, index=False)
    counts = {
        key: int(value)
        for key, value in output["match_status"].value_counts().sort_index().items()
    }
    return {
        "stations": len(output),
        "status_counts": counts,
        "output": str(destination),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Match NWDP stations to verified AP dams")
    parser.add_argument(
        "--level", default="/data/raw/nwdp-ap-reservoir-level-2026-2030.csv"
    )
    parser.add_argument(
        "--storage", default="/data/raw/nwdp-ap-reservoir-storage-2026-2030.csv"
    )
    parser.add_argument(
        "--registry", default="/data/processed/ap-dam-registry-verified.csv"
    )
    parser.add_argument(
        "--output", default="/data/processed/nwdp-reservoir-station-matches.csv"
    )
    args = parser.parse_args()
    result = build_station_match_report(
        args.level,
        args.storage,
        args.registry,
        args.output,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
