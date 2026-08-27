from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import geopandas as gpd
import httpx
import pandas as pd
from shapely.geometry import Point

WRIS_DAM_LAYER = (
    "https://arc.indiawris.gov.in/server/rest/services/"
    "SubInfoSysLCC/WaterResourceProject/MapServer/2/query"
)

# Records absent from the processed CWC snapshot may only enter the verified
# registry when an independent authoritative source has corroborated them.
CORROBORATED_NWDP_RECORDS: dict[str, dict[str, Any]] = {
    "AP01MH0009": {
        "asset_type": "barrage",
        "district": "NTR",
        "river": "Krishna",
        "built_year": 1957,
        "verification_status": "authoritative_registry_corroborated",
        "verification_confidence": 0.95,
        "source_primary": "NWDP/NWIC 2025 + AP Government Irrigation Circle",
        "source_geometry": "NWDP/NWIC 2025 DMS coordinates",
    }
}


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


def normalize_identifier(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"[^A-Z0-9]", "", str(value).upper())


def dms_to_decimal(value: Any) -> float:
    text = str(value).strip().upper()
    match = re.search(
        r"(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\D+(\d+(?:\.\d+)?)\D*([NSEW])",
        text,
    )
    if not match:
        raise ValueError(f"Invalid DMS coordinate: {value!r}")
    degrees, minutes, seconds = (float(match.group(i)) for i in range(1, 4))
    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Invalid DMS coordinate: {value!r}")
    decimal = degrees + minutes / 60 + seconds / 3600
    return -decimal if match.group(4) in {"S", "W"} else decimal


def _clean(value: Any) -> Any:
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


def _first(*values: Any) -> Any:
    for value in values:
        cleaned = _clean(value)
        if cleaned is not None:
            return cleaned
    return None


def _exact_cwc_index(cwc: gpd.GeoDataFrame) -> dict[str, pd.Series]:
    index: dict[str, pd.Series] = {}
    duplicates: set[str] = set()
    for _, row in cwc.iterrows():
        identifier = normalize_identifier(row.get("nrld_no"))
        if not identifier:
            continue
        if identifier in index:
            duplicates.add(identifier)
        else:
            index[identifier] = row
    if duplicates:
        raise ValueError(f"Duplicate CWC identifiers: {sorted(duplicates)[:10]}")
    return index


def build_ap_dam_registry(
    nwdp_path: str | Path,
    cwc_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Build verified and review AP dam registries without fuzzy merging."""
    nwdp = gpd.read_file(nwdp_path)
    cwc = gpd.read_file(cwc_path)
    nwdp = nwdp[
        nwdp["state"].astype(str).str.strip().str.casefold().eq("andhra pradesh")
    ].copy()
    cwc = cwc[cwc["state"].astype(str).str.strip().str.upper().eq("AP") | cwc["nrld_no"].fillna("").astype(str).str.strip().str.upper().str.startswith("AP")].copy()

    cwc_by_id = _exact_cwc_index(cwc)
    verified: list[dict[str, Any]] = []
    review: list[dict[str, Any]] = []

    seen_nwdp_ids: set[str] = set()
    for _, nrow in nwdp.iterrows():
        pic = normalize_identifier(nrow.get("PIC"))
        if not pic:
            review.append({"PIC": None, "dm_name": _clean(nrow.get("dm_name")), "reason": "MISSING_PIC"})
            continue
        if pic in seen_nwdp_ids:
            raise ValueError(f"Duplicate NWDP PIC: {pic}")
        seen_nwdp_ids.add(pic)

        crow = cwc_by_id.get(pic)
        override = CORROBORATED_NWDP_RECORDS.get(pic)
        if crow is not None:
            geometry = crow.geometry
            status = "cross_source_exact_id"
            confidence = 1.0
            source_primary = "NWDP/NWIC 2025"
            source_geometry = "CWC-WRIS 2024"
            cwc_nrld_no = _clean(crow.get("nrld_no"))
            cwc_strucode = _clean(crow.get("strucode"))
        elif override:
            geometry = Point(
                dms_to_decimal(nrow.get("longitude")),
                dms_to_decimal(nrow.get("latitude")),
            )
            status = override["verification_status"]
            confidence = override["verification_confidence"]
            source_primary = override["source_primary"]
            source_geometry = override["source_geometry"]
            cwc_nrld_no = None
            cwc_strucode = None
        else:
            review.append(
                {
                    "PIC": _clean(nrow.get("PIC")),
                    "dm_name": _clean(nrow.get("dm_name")),
                    "district": _clean(nrow.get("district")),
                    "reason": "NO_EXACT_CWC_ID_OR_CORROBORATION",
                }
            )
            continue

        if geometry is None or geometry.is_empty:
            raise ValueError(f"Verified record {pic} has no geometry")
        if not (-180 <= geometry.x <= 180 and -90 <= geometry.y <= 90):
            raise ValueError(f"Verified record {pic} has invalid coordinates")

        override = override or {}
        verified.append(
            {
                "asset_code": f"AP_DAM_NWDP_{pic}",
                "name": _clean(nrow.get("dm_name")),
                "asset_type": override.get("asset_type", "dam"),
                "district": _first(override.get("district"), nrow.get("district"), crow.get("dtcode") if crow is not None else None),
                "river": _first(override.get("river"), nrow.get("river"), crow.get("rivcode") if crow is not None else None),
                "basin": _first(nrow.get("basin"), crow.get("bacode") if crow is not None else None),
                "built_year": _first(override.get("built_year"), nrow.get("cmp_year"), crow.get("dm_cmp_yr") if crow is not None else None),
                "dam_type": _first(nrow.get("dm_type"), crow.get("dm_type") if crow is not None else None),
                "height_m": _first(nrow.get("ht_found"), crow.get("dm_height") if crow is not None else None),
                "length_m": _first(nrow.get("dm_length"), crow.get("dm_length") if crow is not None else None),
                "purpose": _clean(nrow.get("purpose")),
                "nwdp_pic": _clean(nrow.get("PIC")),
                "cwc_nrld_no": cwc_nrld_no,
                "cwc_strucode": cwc_strucode,
                "latitude": geometry.y,
                "longitude": geometry.x,
                "verification_status": status,
                "verification_confidence": confidence,
                "source_primary": source_primary,
                "source_geometry": source_geometry,
                "geometry": geometry,
            }
        )

    registry = gpd.GeoDataFrame(verified, geometry="geometry", crs="EPSG:4326")
    if registry.empty:
        raise ValueError("No verified AP dams were produced")
    if registry["asset_code"].duplicated().any():
        raise ValueError("Verified registry contains duplicate asset codes")
    if registry.geometry.isna().any() or not registry.geometry.is_valid.all():
        raise ValueError("Verified registry contains missing or invalid geometry")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    geojson_path = output_dir / "ap-dam-registry-verified.geojson"
    csv_path = output_dir / "ap-dam-registry-verified.csv"
    review_path = output_dir / "ap-dam-registry-review.csv"
    registry.to_file(geojson_path, driver="GeoJSON")
    registry.drop(columns="geometry").to_csv(csv_path, index=False)
    pd.DataFrame(review).to_csv(review_path, index=False)

    exact_count = int((registry["verification_status"] == "cross_source_exact_id").sum())
    corroborated_count = int(
        (registry["verification_status"] == "authoritative_registry_corroborated").sum()
    )
    return {
        "nwdp_ap_records": len(nwdp),
        "cwc_ap_records": len(cwc),
        "verified_records": len(registry),
        "exact_id_records": exact_count,
        "corroborated_records": corroborated_count,
        "review_records": len(review),
        "geojson": str(geojson_path),
        "csv": str(csv_path),
        "review_csv": str(review_path),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the verified AP dam registry")
    parser.add_argument("--nwdp", default="/data/raw/india-nwic-dams-2025.geojson")
    parser.add_argument("--cwc", default="/data/raw/cwc-wris-dams-2024.geojson")
    parser.add_argument("--output-dir", default="/data/processed")
    args = parser.parse_args()
    print(
        json.dumps(
            build_ap_dam_registry(args.nwdp, args.cwc, args.output_dir),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
