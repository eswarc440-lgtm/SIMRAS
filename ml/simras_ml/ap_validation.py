from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd


NBI_FEATURES = [
    "age_years",
    "condition_rating",
    "material_code",
    "design_type_code",
    "average_daily_traffic",
    "truck_traffic_percent",
    "skew_deg",
    "span_count",
    "max_span_m",
    "structure_length_m",
    "inventory_rating",
    "scour_rating",
    "waterway_rating",
]

CORE_FEATURES = {
    "age_years",
    "condition_rating",
    "design_type_code",
    "average_daily_traffic",
    "structure_length_m",
    "inventory_rating",
}

READY_STATUSES = {
    "DIRECT",
    "DERIVED",
    "DERIVED_OSM_GEOMETRY",
    "MAPPED_VERIFIED",
}


def _present(value) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _number(value):
    if not _present(value):
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def _derived_year(row: dict) -> int | None:
    for key in (
        "canonical_built_year",
        "osm_opening_year",
        "osm_start_year",
    ):
        value = _number(row.get(key))
        if value is not None:
            year = int(value)
            if 1800 <= year <= datetime.now(UTC).year:
                return year
    return None


def assess_record(row: dict) -> dict:
    statuses: dict[str, str] = {}
    values: dict[str, float | None] = {}

    current_year = datetime.now(UTC).year

    # First accept future verified AP engineering fields if supplied
    # using the exact NBI-compatible feature names.
    for feature in NBI_FEATURES:
        direct = _number(row.get(feature))
        if direct is not None:
            values[feature] = direct
            statuses[feature] = "DIRECT"

    # Age may be safely derived from a traceable built/opening year.
    if "age_years" not in statuses:
        year = _derived_year(row)
        if year is not None:
            values["age_years"] = max(0.0, float(current_year - year))
            statuses["age_years"] = "DERIVED"
        else:
            values["age_years"] = None
            statuses["age_years"] = "MISSING"

    # OSM mapped length is useful for single mapped ways.
    # Multi-way groups require topology/engineering review before
    # treating the aggregate as an ML engineering feature.
    if "structure_length_m" not in statuses:
        length = _number(row.get("osm_group_length_m"))
        segment_count = _number(row.get("segment_count"))

        if (
            length is not None
            and length > 0
            and segment_count == 1
        ):
            values["structure_length_m"] = length
            statuses["structure_length_m"] = "DERIVED_OSM_GEOMETRY"
        elif length is not None and length > 0:
            values["structure_length_m"] = None
            statuses["structure_length_m"] = "DERIVED_REVIEW_REQUIRED"
        else:
            values["structure_length_m"] = None
            statuses["structure_length_m"] = "MISSING"

    # Material text is not automatically an FHWA/NBI material code.
    if "material_code" not in statuses:
        values["material_code"] = None
        if _present(row.get("canonical_material")):
            statuses["material_code"] = "MAPPABLE_UNMAPPED"
        else:
            statuses["material_code"] = "MISSING"

    # AP/OSM bridge subtype is not automatically an NBI design code.
    if "design_type_code" not in statuses:
        values["design_type_code"] = None
        if _present(row.get("subtype")) or _present(
            row.get("osm_bridge_structure")
        ):
            statuses["design_type_code"] = "MAPPABLE_UNMAPPED"
        else:
            statuses["design_type_code"] = "MISSING"

    # Text condition such as GOOD is deliberately not converted
    # into an NBI 0-9 inspection rating without an approved mapping.
    if "condition_rating" not in statuses:
        values["condition_rating"] = None
        if _present(row.get("canonical_condition")):
            statuses["condition_rating"] = "MAPPABLE_UNMAPPED"
        else:
            statuses["condition_rating"] = "MISSING"

    for feature in NBI_FEATURES:
        if feature not in statuses:
            values[feature] = None
            statuses[feature] = "MISSING"

    ready = {
        feature
        for feature, status in statuses.items()
        if status in READY_STATUSES
    }

    coverage = len(ready) / len(NBI_FEATURES)

    identity_status = (
        row.get("canonical_identity_status")
        if _present(row.get("canonical_identity_status"))
        else row.get("identity_status")
    )

    identity_verified = str(identity_status).upper() == "VERIFIED"

    missing_core = sorted(CORE_FEATURES - ready)

    blockers: list[str] = []

    if not identity_verified:
        blockers.append("IDENTITY_NOT_VERIFIED")

    if missing_core:
        blockers.append(
            "MISSING_CORE_FEATURES:" + ",".join(missing_core)
        )

    if coverage < 0.70:
        blockers.append("FEATURE_COVERAGE_BELOW_70_PERCENT")

    review_required = [
        feature
        for feature, status in statuses.items()
        if status in {
            "DERIVED_REVIEW_REQUIRED",
            "MAPPABLE_UNMAPPED",
        }
    ]

    if review_required:
        blockers.append(
            "UNRESOLVED_MAPPINGS_OR_REVIEW:"
            + ",".join(sorted(review_required))
        )

    eligible = len(blockers) == 0

    return {
        "asset_code": row.get("asset_code"),
        "name": row.get("name"),
        "canonical_asset_code": row.get("canonical_asset_code"),
        "identity_status": identity_status,
        "identity_verified": identity_verified,
        "available_features": len(ready),
        "required_features": len(NBI_FEATURES),
        "feature_coverage": round(coverage, 4),
        "prediction_eligible": eligible,
        "blocker_count": len(blockers),
        "blockers": "|".join(blockers),
        "feature_status": json.dumps(statuses, sort_keys=True),
    }


def validate_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    results = pd.DataFrame(
        assess_record(row)
        for row in frame.to_dict("records")
    )

    total = len(results)

    summary = {
        "validation_type": "AP_NBI_TRANSFER_COMPATIBILITY",
        "generated_at": datetime.now(UTC).isoformat(),
        "total_bridge_candidates": total,
        "prediction_eligible": int(
            results["prediction_eligible"].sum()
        ),
        "prediction_withheld": int(
            (~results["prediction_eligible"]).sum()
        ),
        "verified_identities": int(
            results["identity_verified"].sum()
        ),
        "average_feature_coverage": float(
            results["feature_coverage"].mean()
        ) if total else 0.0,
        "max_feature_coverage": float(
            results["feature_coverage"].max()
        ) if total else 0.0,
        "stage": "AP_COMPATIBILITY_CHECKED",
        "local_engineering_validation": False,
        "promotion_allowed": False,
        "promotion_blocker": (
            "AP local labelled engineering validation has not yet been completed"
        ),
        "policy": (
            "Withhold predictions when identity/core engineering "
            "features are insufficient; never fabricate missing NBI fields."
        ),
    }

    return results, summary


def write_report(
    frame: pd.DataFrame,
    output_dir: Path,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)

    results, summary = validate_frame(frame)

    results.to_csv(
        output_dir / "ap_compatibility.csv",
        index=False,
    )

    (output_dir / "ap_validation_report.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    return summary
