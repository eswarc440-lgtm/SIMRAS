from __future__ import annotations

import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.services.recommendation_engine import build_recommendations

FEATURE_COLUMNS = [
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

MATERIAL_CODES = {
    "concrete": 1,
    "concrete_continuous": 2,
    "steel": 3,
    "steel_continuous": 4,
    "prestressed_concrete": 5,
    "prestressed_concrete_continuous": 6,
    "wood": 7,
    "masonry": 8,
    "aluminum": 9,
    "other": 0,
    "steel_and_concrete": 3,
}


@dataclass(slots=True)
class MLInput:
    asset_type: str
    age_years: float | None
    condition_rating: float | None
    material: str | None = None
    span_count: float | None = None
    max_span_m: float | None = None
    structure_length_m: float | None = None
    average_daily_traffic: float | None = None
    truck_traffic_percent: float | None = None
    skew_deg: float | None = None
    inventory_rating: float | None = None
    scour_rating: float | None = None
    waterway_rating: float | None = None
    design_type_code: float | None = None


@dataclass(slots=True)
class MLResult:
    health_score: float
    health_lower_bound: float
    health_upper_bound: float
    risk_score: float
    risk_level: str
    remaining_life_years: float
    rul_lower_bound: float
    rul_upper_bound: float
    confidence: float
    model_version: str
    feature_version: str
    status: str
    prediction_method: str
    model_validated: bool
    training_scope: str
    forecast_horizon_years: int
    factors: list[str]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def condition_to_rating(condition: str | None, score: float | None) -> float | None:
    if score is not None:
        return max(0.0, min(9.0, float(score) * 9.0 / 100.0))
    return {
        "GOOD": 7.5,
        "FAIR": 5.5,
        "POOR": 3.5,
        "CRITICAL": 1.5,
    }.get((condition or "").upper())


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_artifacts(artifact_dir: Path) -> tuple[dict, dict[str, Any]] | None:
    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.exists():
        return None
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("stage") not in {"RESEARCH_TRANSFER", "VALIDATED_LOCAL"}:
        return None
    models: dict[str, Any] = {}
    for filename in [
        "health.joblib",
        "risk.joblib",
        "risk_calibrator.joblib",
        "rul_lower.joblib",
        "rul_median.joblib",
        "rul_upper.joblib",
    ]:
        path = artifact_dir / filename
        expected = manifest.get("artifact_checksums", {}).get(filename)
        if not path.exists() or (expected and _checksum(path) != expected):
            return None
        models[filename] = joblib.load(path)
    return manifest, models


def _logit(value: float) -> np.ndarray:
    value = min(1 - 1e-6, max(1e-6, value))
    return np.array([[math.log(value / (1 - value))]])


def predict_bridge(
    data: MLInput,
    *,
    artifact_dir: str | Path | None = None,
) -> MLResult | None:
    """Serve only an accepted bridge artifact with enough structural evidence."""

    if data.asset_type.lower() != "bridge" or data.condition_rating is None:
        return None
    if data.age_years is None or not 0 <= data.age_years <= 200:
        return None
    if not 0 <= data.condition_rating <= 9:
        return None

    root = Path(artifact_dir or os.getenv("SIMRAS_ML_ARTIFACT_DIR", "/artifacts/bridge_nbi"))
    loaded = _load_artifacts(root)
    if loaded is None:
        return None
    manifest, models = loaded
    material_key = (data.material or "other").lower().replace(" ", "_")
    row = {
        "age_years": data.age_years,
        "condition_rating": data.condition_rating,
        "material_code": MATERIAL_CODES.get(material_key, 0),
        "design_type_code": data.design_type_code,
        "average_daily_traffic": data.average_daily_traffic,
        "truck_traffic_percent": data.truck_traffic_percent,
        "skew_deg": data.skew_deg,
        "span_count": data.span_count,
        "max_span_m": data.max_span_m,
        "structure_length_m": data.structure_length_m,
        "inventory_rating": data.inventory_rating,
        "scour_rating": data.scour_rating,
        "waterway_rating": data.waterway_rating,
    }
    frame = pd.DataFrame([row], columns=FEATURE_COLUMNS)
    health_rating = float(np.clip(models["health.joblib"].predict(frame)[0], 0, 9))
    health_score = health_rating * 100 / 9
    errors = manifest.get("health_error_quantiles_rating", {})
    health_lower = np.clip(health_rating + float(errors.get("lower", -1)), 0, 9) * 100 / 9
    health_upper = np.clip(health_rating + float(errors.get("upper", 1)), 0, 9) * 100 / 9

    raw_risk = float(models["risk.joblib"].predict_proba(frame)[0, 1])
    risk_probability = float(
        models["risk_calibrator.joblib"].predict_proba(_logit(raw_risk))[0, 1]
    )
    risk_score = risk_probability * 100
    risk_level = "HIGH" if risk_score >= 70 else "MEDIUM" if risk_score >= 40 else "LOW"

    rul_lower = float(np.clip(models["rul_lower.joblib"].predict(frame)[0], 0, 30))
    rul_median = float(np.clip(models["rul_median.joblib"].predict(frame)[0], 0, 30))
    rul_upper = float(np.clip(models["rul_upper.joblib"].predict(frame)[0], 0, 30))
    lower, upper = sorted((rul_lower, rul_upper))
    completeness = sum(value is not None for value in row.values()) / len(row)
    locally_validated = manifest.get("stage") == "VALIDATED_LOCAL"
    base_confidence = 0.85 if locally_validated else 0.58
    confidence = max(0.1, min(0.95, base_confidence * (0.65 + completeness * 0.35)))

    factors = [
        f"Latest structural condition maps to NBI-equivalent rating {data.condition_rating:.1f}/9",
        f"Model estimates {risk_probability:.1%} probability of poor condition within {manifest.get('prediction_horizon_years', 3)} years",
    ]
    if not locally_validated:
        factors.append("Model is trained on FHWA bridge histories and is not validated for Andhra Pradesh")
    factors.extend(manifest.get("limitations", []))
    recommendations = build_recommendations(
        condition_rating=data.condition_rating,
        risk_score=risk_score,
        rul_years=rul_median,
        confidence=confidence,
        model_validated=locally_validated,
    )
    return MLResult(
        health_score=round(health_score, 1),
        health_lower_bound=round(float(min(health_lower, health_upper)), 1),
        health_upper_bound=round(float(max(health_lower, health_upper)), 1),
        risk_score=round(risk_score, 1),
        risk_level=risk_level,
        remaining_life_years=round(rul_median, 1),
        rul_lower_bound=round(lower, 1),
        rul_upper_bound=round(upper, 1),
        confidence=round(confidence, 2),
        model_version=manifest["version"],
        feature_version=manifest["feature_version"],
        status="VALIDATED_LOCAL" if locally_validated else "RESEARCH_TRANSFER",
        prediction_method="calibrated_nbi_bridge_ml",
        model_validated=locally_validated,
        training_scope=manifest["training_scope"],
        forecast_horizon_years=int(manifest.get("prediction_horizon_years", 3)),
        factors=list(dict.fromkeys(factors)),
        recommendations=recommendations,
    )
