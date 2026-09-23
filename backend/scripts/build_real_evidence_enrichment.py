from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("/data") if Path("/data/seed/assets.csv").exists() else ROOT / "data"
BACKEND_ROOT = Path("/app") if Path("/app/data").exists() else ROOT / "backend"
SEED = DATA_ROOT / "seed" / "assets.csv"
OUTPUT_ROOT = DATA_ROOT / "real_evidence"
ALLOWED_STATUS = {"VERIFIED", "SOURCE_REPORTED", "DERIVED", "CONFLICT", "NOT_FOUND"}

SOURCE_CONFIG = (
    ("backend/data/processed/dam_barrage/AP_DAM_BARRAGE_ENGINEERING_FEATURES.csv", "Central Water Commission / NRLD / AP Water Resources Department", "AP dam and barrage engineering feature register", "A1_GOVERNMENT"),
    ("backend/data/processed/dam_barrage/AP_DAM_BARRAGE_ML_FEATURES_V1.csv", "Central Water Commission / NRLD / AP Water Resources Department", "AP dam and barrage normalized ML feature register", "A1_GOVERNMENT"),
    ("backend/data/processed/dam_barrage/AP_DAM_BARRAGE_HYDROLOGY_FEATURES_V1.csv", "National Water Data Portal / AP hydrology sources", "AP dam and barrage hydrology feature register", "A1_GOVERNMENT"),
    ("backend/data/processed/bridge/AP_BRIDGE_ENGINEERING_FEATURES.csv", "Government of Andhra Pradesh / official bridge engineering sources", "AP bridge engineering feature register", "A1_GOVERNMENT"),
    ("backend/data/processed/bridge/AP_BRIDGE_ENGINEERING_EVIDENCE.csv", "Government of Andhra Pradesh / official bridge engineering sources", "AP bridge engineering evidence register", "A1_GOVERNMENT"),
    ("backend/data/processed/airport/AP_AIRPORT_ENGINEERING_FEATURES.csv", "Airports Authority of India", "AIM India eAIP airport engineering register", "A1_GOVERNMENT"),
    ("backend/data/processed/airport/AP_AIRPORT_MAINTENANCE_EVIDENCE_VERIFIED.csv", "Airports Authority of India", "AAI maintenance and procurement evidence", "A1_GOVERNMENT"),
    ("backend/data/processed/temple/AP_TEMPLE_ENGINEERING_FEATURES.csv", "Temple authorities / official temple sources", "AP temple engineering feature register", "A1_GOVERNMENT"),
    ("backend/data/processed/temple/AP_TEMPLE_ENGINEERING_EVIDENCE.csv", "Temple authorities / official temple sources", "AP temple engineering evidence register", "A1_GOVERNMENT"),
)

FIELD_ALIASES = {
    "completion_year": "commissioned_year",
    "commencement_year": "built_year",
    "full_operation_year": "commissioned_year",
    "dam_height_m": "height_m",
    "dam_length_m": "length_m",
    "reported_total_length_m": "length_m",
    "max_reported_span_m": "max_span_m",
    "runway_length_m": "runway_length_m",
    "runway_width_m": "runway_width_m",
    "aerodrome_elevation_ft": "elevation_ft",
    "pavement_strength_raw": "runway_pcn",
    "gate_count": "gate_count",
    "pier_count": "pier_count",
    "span_count": "span_count",
    "material_summary": "material",
    "verified_materials": "material",
}

NUMERIC_FIELDS = {
    "built_year", "commissioned_year", "length_m", "width_m", "height_m", "design_life_years",
    "gate_count", "gate_width_m", "gate_height_m", "spillway_capacity_m3s", "reservoir_capacity_mcm",
    "live_storage_mcm", "span_count", "pier_count", "max_span_m", "deck_width_m", "aadt",
    "truck_percent", "runway_length_m", "runway_width_m", "runway_pcn", "elevation_ft",
    "rainfall_24h", "rainfall_7d", "rainfall_30d", "water_level", "storage", "discharge",
    "flood_exposure", "elevation_m", "slope_deg",
}


def now() -> str:
    return datetime.now(UTC).isoformat()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))



async def database_inventory() -> list[dict[str, Any]]:
    from sqlalchemy import func, select

    from app.db.session import SessionLocal
    from app.models.entities import Asset

    async with SessionLocal() as session:
        result = await session.execute(
            select(
                Asset.asset_code,
                Asset.name,
                Asset.asset_type,
                Asset.subtype,
                Asset.district,
                Asset.built_year,
                Asset.design_life_years,
                Asset.material,
                Asset.owner,
                Asset.identity_status,
                Asset.confidence_score,
                func.ST_X(Asset.representative_geometry).label("longitude"),
                func.ST_Y(Asset.representative_geometry).label("latitude"),
            ).order_by(Asset.asset_code.asc())
        )
        rows = []
        for row in result.mappings().all():
            item = dict(row)
            rows.append({key: str(value) if value is not None else "" for key, value in item.items()})
        return rows


def clean(value: Any) -> Any:
    if value is None:
        return None
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none", "null", "n/a", "na"}:
        return None
    return text


def scalar(value: Any) -> Any:
    value = clean(value)
    if value is None:
        return None
    try:
        number = float(value)
        if number.is_integer():
            return int(number)
        return number
    except (TypeError, ValueError):
        return value


def asset_code(row: dict[str, Any]) -> str | None:
    for key in ("asset_code", "code", "external_id"):
        value = clean(row.get(key))
        if value:
            return value
    return None


def source_record(authority: str, title: str, source_type: str, url: str | None = None) -> dict[str, Any]:
    return {
        "source_authority": authority,
        "source_title": title,
        "source_url": url,
        "source_type": source_type,
        "published_at": None,
        "retrieved_at": now(),
    }


def value_record(value: Any, *, authority: str, title: str, source_type: str, status: str = "SOURCE_REPORTED", unit: str | None = None, url: str | None = None, reason: str | None = None) -> dict[str, Any]:
    status = status if status in ALLOWED_STATUS else "NOT_FOUND"
    record = {"value": scalar(value), "unit": unit, **source_record(authority, title, source_type, url), "verification_status": status}
    if reason:
        record["reason"] = reason
    return record


def numeric_or_text_field(key: str, value: Any) -> tuple[Any, str | None]:
    value = scalar(value)
    if value is None:
        return None, None
    if key.endswith("_year") or key.endswith("_count"):
        return value, None
    if key.endswith("_m"):
        return value, "m"
    if key.endswith("_mcm"):
        return value, "MCM"
    if key.endswith("_m3s"):
        return value, "m3/s"
    if key.endswith("_ft"):
        return value, "ft"
    if key in {"aadt", "truck_percent", "runway_pcn", "slope_deg", "flood_exposure"}:
        return value, None
    return value, None


def add_candidate(candidates: dict[str, list[dict[str, Any]]], field: str, value: Any, *, config: tuple[str, str, str], row: dict[str, Any]) -> None:
    value = clean(value)
    if value is None:
        return
    canonical = FIELD_ALIASES.get(field, field)
    if canonical not in NUMERIC_FIELDS and canonical not in {"material", "structure_type", "road_or_rail", "runway_orientation", "operator", "owner", "district"}:
        return
    parsed, unit = numeric_or_text_field(canonical, value)
    candidates[canonical].append(value_record(parsed, authority=config[1], title=config[2], source_type=config[3], unit=unit, url=clean(row.get("source_url"))))


def choose_field(candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not candidates:
        return None
    normalized = {json.dumps(item.get("value"), sort_keys=True) for item in candidates}
    if len(normalized) > 1:
        return {
            "value": None,
            "unit": candidates[0].get("unit"),
            **{key: candidates[0].get(key) for key in ("source_authority", "source_title", "source_url", "source_type", "published_at", "retrieved_at")},
            "verification_status": "CONFLICT",
            "candidates": candidates,
            "reason": "MULTIPLE_SOURCES_DISAGREE_ON_SAME_CANONICAL_FIELD",
        }
    selected = dict(candidates[0])
    if len(candidates) > 1:
        selected["sources"] = candidates
    return selected


def build(args: argparse.Namespace, inventory: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    generated = now()
    assets = inventory if inventory is not None else read_csv(SEED)
    by_code: dict[str, dict[str, Any]] = {}
    for row in assets:
        code = asset_code(row)
        if not code:
            continue
        by_code[code] = {
            "asset_code": code,
            "name": clean(row.get("name")),
            "category": str(clean(row.get("asset_type")) or "").upper(),
            "identity": {
                "official_name": value_record(row.get("name"), authority="SIMRAS master inventory", title="SIMRAS registered asset inventory", source_type="INTERNAL_REGISTER"),
                "alternative_names": [],
                "category": value_record(str(clean(row.get("asset_type")) or "").upper(), authority="SIMRAS master inventory", title="SIMRAS registered asset inventory", source_type="INTERNAL_REGISTER"),
                "district": value_record(row.get("district"), authority="SIMRAS master inventory", title="SIMRAS registered asset inventory", source_type="INTERNAL_REGISTER"),
                "latitude": value_record(row.get("latitude"), authority="SIMRAS master inventory", title="SIMRAS registered asset inventory", source_type="INTERNAL_REGISTER", unit="degrees"),
                "longitude": value_record(row.get("longitude"), authority="SIMRAS master inventory", title="SIMRAS registered asset inventory", source_type="INTERNAL_REGISTER", unit="degrees"),
                "owner": value_record(row.get("owner"), authority="SIMRAS master inventory", title="SIMRAS registered asset inventory", source_type="INTERNAL_REGISTER"),
                "operator": value_record(row.get("owner"), authority="SIMRAS master inventory", title="SIMRAS registered asset inventory", source_type="INTERNAL_REGISTER"),
            },
            "engineering": {},
            "inspection_maintenance": {
                "latest_inspection_date": None,
                "condition_rating": None,
                "condition_status": "NO_AUTHORITATIVE_INSPECTION_FOUND",
                "inspection_agency": None,
                "defects": [],
                "maintenance_date": None,
                "rehabilitation_tender_evidence": [],
            },
            "environment": {},
            "sources": [],
            "modelUsage": {},
            "geometryConfidence": "SOURCE_REPORTED_LOCATION_ONLY",
            "lastVerified": generated,
            "_candidates": defaultdict(list),
        }

    ledger: list[dict[str, Any]] = []
    for relative, authority, title, source_type in SOURCE_CONFIG:
        path = BACKEND_ROOT / relative.removeprefix("backend/")
        config = (relative, authority, title, source_type)
        for row in read_csv(path):
            code = asset_code(row)
            if not code or code not in by_code:
                continue
            record = by_code[code]
            for field, raw in row.items():
                if field in {"asset_code", "asset_name", "asset_id", "name", "feature_version", "generated_at"}:
                    continue
                if field.startswith("is_") or field.endswith("_status") or field.endswith("_confidence"):
                    continue
                add_candidate(record["_candidates"], field, raw, config=config, row=row)
                if clean(raw) is not None:
                    ledger.append({"asset_code": code, "field": FIELD_ALIASES.get(field, field), "value": scalar(raw), "source_authority": authority, "source_title": title, "source_url": clean(row.get("source_url")), "source_type": source_type, "verification_status": "SOURCE_REPORTED", "retrieved_at": generated})
            if source_type == "A1_GOVERNMENT":
                record["sources"].append(source_record(authority, title, source_type, clean(row.get("source_url"))))

    conflicts: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    required_by_category = {
        "DAM": ["built_year", "length_m", "height_m", "gate_count"],
        "BARRAGE": ["built_year", "length_m", "gate_count"],
        "BRIDGE": ["built_year", "length_m", "span_count", "pier_count"],
        "AIRPORT": ["runway_length_m", "runway_width_m"],
        "TEMPLE": ["structure_type"],
    }
    for code, record in by_code.items():
        for field, candidates in record.pop("_candidates").items():
            selected = choose_field(candidates)
            if selected is None:
                continue
            record["engineering"][field] = selected
            if selected["verification_status"] == "CONFLICT":
                conflicts.append({"asset_code": code, "field": field, "candidate_values": json.dumps([item.get("value") for item in candidates]), "sources": json.dumps([item.get("source_title") for item in candidates]), "reason": selected["reason"]})
        required = required_by_category.get(record["category"], [])
        for field in required:
            if field not in record["engineering"]:
                missing.append({"asset_code": code, "name": record["name"], "category": record["category"], "field": field, "reason": "AUTHORITATIVE_EVIDENCE_NOT_AVAILABLE"})
        source_titles = {item["source_title"] for item in record["sources"]}
        record["sources"] = list({json.dumps(item, sort_keys=True): item for item in record["sources"]}.values())
        record["source_count"] = len(source_titles)
        record["verified_source_count"] = sum(1 for item in record["sources"] if item["source_type"] == "A1_GOVERNMENT")

    return {"schema_version": "simras-real-evidence-v1", "generated_at": generated, "asset_count": len(by_code), "assets": list(by_code.values()), "ledger": ledger, "missing": missing, "conflicts": conflicts}


def flatten_field(record: dict[str, Any], field: str) -> Any:
    item = record.get("engineering", {}).get(field)
    return item.get("value") if isinstance(item, dict) else None


def engineering_value(record: dict[str, Any], *fields: str) -> Any:
    for field in fields:
        value = flatten_field(record, field)
        if value is not None:
            return value
    return None


def write_outputs(bundle: dict[str, Any], output_root: Path) -> None:
    for name in ("raw", "enriched", "audit", "master"):
        (output_root / name).mkdir(parents=True, exist_ok=True)
    assets = bundle["assets"]
    clean_assets = json.loads(json.dumps(assets))
    for record in clean_assets:
        record.pop("_candidates", None)
    (output_root / "enriched" / "SIMRAS_194_REAL_DATA.json").write_text(json.dumps({"schema_version": bundle["schema_version"], "generated_at": bundle["generated_at"], "asset_count": bundle["asset_count"], "assets": clean_assets}, indent=2), encoding="utf-8")

    fields = ["asset_code", "name", "category", "source_count", "verified_source_count", "geometry_confidence", "condition_status"]
    with (output_root / "master" / "SIMRAS_194_REAL_DATA.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for item in assets:
            writer.writerow({"asset_code": item["asset_code"], "name": item["name"], "category": item["category"], "source_count": item.get("source_count", 0), "verified_source_count": item.get("verified_source_count", 0), "geometry_confidence": item["geometryConfidence"], "condition_status": item["inspection_maintenance"]["condition_status"]})

    ledger_fields = ["asset_code", "field", "value", "source_authority", "source_title", "source_url", "source_type", "verification_status", "retrieved_at"]
    for filename, rows, fields_out in (("SIMRAS_SOURCE_LEDGER.csv", bundle["ledger"], ledger_fields), ("SIMRAS_MISSING_FIELDS.csv", bundle["missing"], ["asset_code", "name", "category", "field", "reason"]), ("SIMRAS_CONFLICTS.csv", bundle["conflicts"], ["asset_code", "field", "candidate_values", "sources", "reason"])):
        with (output_root / "audit" / filename).open("w", newline="", encoding="utf-8-sig") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields_out)
            writer.writeheader()
            writer.writerows(rows)

    feature_fields = ["asset_code", "category", "built_year", "age_years", "design_life_years", "age_design_life_ratio", "condition_rating", "inspection_score", "defect_count", "days_since_inspection", "days_since_maintenance", "rainfall_24h", "rainfall_7d", "rainfall_30d", "water_level", "water_level_anomaly", "flood_exposure", "elevation_m", "slope_deg", "traffic_load_ratio", "source_confidence", "length_m", "width_m", "height_m", "gate_count", "span_count", "pier_count", "max_span_m", "runway_length_m", "runway_width_m", "runway_pcn", "missing_feature_ratio"]
    with (output_root / "enriched" / "SIMRAS_194_FEATURES.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=feature_fields)
        writer.writeheader()
        for item in assets:
            engineering = item.get("engineering", {})
            built = flatten_field(item, "built_year")
            design = flatten_field(item, "design_life_years")
            age = None
            if built is not None:
                age = datetime.now(UTC).year - int(float(built))
            required = ["age_years", "design_life_years", "condition_rating", "inspection_score", "rainfall_24h", "rainfall_7d", "water_level_anomaly"]
            values = {
                "asset_code": item["asset_code"],
                "category": item["category"],
                "built_year": built,
                "age_years": age,
                "design_life_years": design,
                "age_design_life_ratio": (age / float(design) if age is not None and design not in (None, 0) else None),
                "condition_rating": None,
                "inspection_score": None,
                "defect_count": None,
                "days_since_inspection": None,
                "days_since_maintenance": None,
                "rainfall_24h": None,
                "rainfall_7d": None,
                "rainfall_30d": None,
                "water_level": engineering_value(item, "water_level", "manual_daily_reservoir_water_level_m_latest"),
                "water_level_anomaly": engineering_value(item, "water_level_anomaly"),
                "flood_exposure": None,
                "elevation_m": engineering_value(item, "elevation_m"),
                "slope_deg": engineering_value(item, "slope_deg"),
                "traffic_load_ratio": None,
                "source_confidence": None,
                "length_m": engineering_value(item, "length_m"),
                "width_m": engineering_value(item, "width_m", "deck_width_m", "runway_width_m"),
                "height_m": engineering_value(item, "height_m"),
                "gate_count": engineering_value(item, "gate_count"),
                "span_count": engineering_value(item, "span_count"),
                "pier_count": engineering_value(item, "pier_count"),
                "max_span_m": engineering_value(item, "max_span_m"),
                "runway_length_m": engineering_value(item, "runway_length_m"),
                "runway_width_m": engineering_value(item, "runway_width_m"),
                "runway_pcn": engineering_value(item, "runway_pcn"),
            }
            required = ["age_years", "design_life_years", "condition_rating", "inspection_score", "rainfall_24h", "rainfall_7d", "water_level_anomaly"]
            values["missing_feature_ratio"] = sum(values[field] is None for field in required) / len(required)
            writer.writerow(values)

    audit_fields = ["asset_code", "name", "category", "identity_verified", "engineering_fields_required", "engineering_fields_found", "inspection_found", "environment_found", "traffic_or_operational_load_found", "source_count", "verified_source_count", "feature_coverage", "prediction_basis", "health_score", "risk_score", "risk_level", "confidence", "rul_years"]
    with (output_root / "audit" / "SIMRAS_REAL_DATA_AUDIT.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.DictWriter(stream, fieldnames=audit_fields)
        writer.writeheader()
        required_by_category = {"DAM": ["built_year", "length_m", "height_m", "gate_count"], "BARRAGE": ["built_year", "length_m", "gate_count"], "BRIDGE": ["built_year", "length_m", "span_count", "pier_count"], "AIRPORT": ["runway_length_m", "runway_width_m"], "TEMPLE": ["structure_type"]}
        for item in assets:
            required = required_by_category.get(item["category"], [])
            found = [field for field in required if flatten_field(item, field) is not None]
            writer.writerow({"asset_code": item["asset_code"], "name": item["name"], "category": item["category"], "identity_verified": item["identity"]["official_name"]["verification_status"], "engineering_fields_required": len(required), "engineering_fields_found": len(found), "inspection_found": False, "environment_found": bool(item["environment"]), "traffic_or_operational_load_found": flatten_field(item, "aadt") is not None, "source_count": item.get("source_count", 0), "verified_source_count": item.get("verified_source_count", 0), "feature_coverage": round(len(found) / max(len(required), 1), 3), "prediction_basis": "NOT_RUN_ENRICHMENT_PHASE", "health_score": None, "risk_score": None, "risk_level": None, "confidence": None, "rul_years": None})

    # Keep the requested filenames at the phase root as well as organized
    # copies in master/enriched/audit for downstream jobs.
    root_json = output_root / "SIMRAS_194_REAL_DATA.json"
    root_json.write_text((output_root / "enriched" / root_json.name).read_text(encoding="utf-8"), encoding="utf-8")
    for filename, folder in (
        ("SIMRAS_194_REAL_DATA.csv", "master"),
        ("SIMRAS_SOURCE_LEDGER.csv", "audit"),
        ("SIMRAS_MISSING_FIELDS.csv", "audit"),
        ("SIMRAS_CONFLICTS.csv", "audit"),
        ("SIMRAS_194_FEATURES.csv", "enriched"),
        ("SIMRAS_REAL_DATA_AUDIT.csv", "audit"),
    ):
        source = output_root / folder / filename
        target = output_root / filename
        target.write_bytes(source.read_bytes())


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SIMRAS source-backed real-evidence layers.")
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--from-db", action="store_true", help="Use the live canonical assets table instead of the four-row offline seed inventory.")
    args = parser.parse_args()
    inventory = asyncio.run(database_inventory()) if args.from_db else None
    bundle = build(args, inventory)
    write_outputs(bundle, args.output_root)
    print(f"total assets: {bundle['asset_count']}")
    print(f"assets enriched: {sum(1 for item in bundle['assets'] if item['source_count'])}")
    print(f"source conflicts: {len(bundle['conflicts'])}")
    print(f"missing critical fields: {len(bundle['missing'])}")
    print("inspection coverage: 0 (condition is never fabricated by this phase)")
    print("prediction phase: NOT RUN; Digital Twin and prediction UI unchanged")


if __name__ == "__main__":
    main()
