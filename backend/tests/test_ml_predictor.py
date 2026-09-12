from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np

from app.services.ml_predictor import MLInput, predict_bridge


class ConstantRegressor:
    def __init__(self, value: float):
        self.value = value

    def predict(self, frame):
        return np.full(len(frame), self.value)


class ConstantClassifier:
    def __init__(self, probability: float):
        self.probability = probability

    def predict_proba(self, frame):
        return np.tile([1 - self.probability, self.probability], (len(frame), 1))


class LogisticIdentity:
    def predict_proba(self, values):
        probability = 1 / (1 + np.exp(-values[:, 0]))
        return np.column_stack([1 - probability, probability])


def _checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifacts(root: Path, stage: str = "RESEARCH_TRANSFER") -> None:
    models = {
        "health.joblib": ConstantRegressor(6.3),
        "risk.joblib": ConstantClassifier(0.42),
        "risk_calibrator.joblib": LogisticIdentity(),
        "rul_lower.joblib": ConstantRegressor(4),
        "rul_median.joblib": ConstantRegressor(4),
        "rul_upper.joblib": ConstantRegressor(11),
    }
    checksums = {}
    for name, model in models.items():
        joblib.dump(model, root / name)
        checksums[name] = _checksum(root / name)
    (root / "manifest.json").write_text(
        json.dumps(
            {
                "version": "test_v1",
                "feature_version": "test_features",
                "stage": stage,
                "training_scope": "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER",
                "prediction_horizon_years": 3,
                "health_error_quantiles_rating": {"lower": -0.8, "upper": 0.9},
                "artifact_checksums": checksums,
                "limitations": ["Not locally validated"],
            }
        ),
        encoding="utf-8",
    )


def test_research_transfer_prediction_is_disclosed(tmp_path: Path) -> None:
    _artifacts(tmp_path)
    result = predict_bridge(
        MLInput(
            asset_type="bridge",
            age_years=29,
            condition_rating=7.4,
            material="steel_and_concrete",
            span_count=28,
            max_span_m=97.55,
            structure_length_m=2745,
        ),
        artifact_dir=tmp_path,
    )
    assert result is not None
    assert result.status == "RESEARCH_TRANSFER"
    assert result.model_validated is False
    assert result.health_lower_bound <= result.health_score <= result.health_upper_bound
    assert result.rul_lower_bound <= result.remaining_life_years <= result.rul_upper_bound
    assert any("not validated" in item.lower() for item in result.factors)
    assert any("conditional" in item.lower() for item in result.factors)
    assert not any("rehabilitation options" in item.lower() for item in result.recommendations)
    assert any("do not use" in item.lower() for item in result.recommendations)


def test_rejected_or_out_of_scope_model_abstains(tmp_path: Path) -> None:
    _artifacts(tmp_path, stage="REJECTED")
    assert (
        predict_bridge(
            MLInput(asset_type="bridge", age_years=30, condition_rating=6),
            artifact_dir=tmp_path,
        )
        is None
    )
    assert (
        predict_bridge(
            MLInput(asset_type="dam", age_years=50, condition_rating=6),
            artifact_dir=tmp_path,
        )
        is None
    )
