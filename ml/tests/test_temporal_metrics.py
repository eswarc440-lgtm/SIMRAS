from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.dummy import DummyRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from simras_ml.nbi import FEATURE_COLUMNS, stable_partition
from simras_ml.temporal_eval import evaluate_bridge_temporal_holdout


def _heldout_keys(count: int) -> list[str]:
    keys: list[str] = []
    index = 0
    while len(keys) < count:
        candidate = f"EVAL:{index:06d}"
        if stable_partition(candidate) >= 85:
            keys.append(candidate)
        index += 1
    return keys


def _feature_row(key: str, year: int, condition: float) -> dict:
    row = {
        "bridge_key": key,
        "report_year": year,
        "condition_rating": condition,
    }
    for column in FEATURE_COLUMNS:
        if column == "condition_rating":
            row[column] = condition
        elif column == "age_years":
            row[column] = float(year - 2000)
        else:
            row[column] = 1.0
    return row


def _artifact_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)

    train_x = pd.DataFrame(
        [
            {column: 1.0 for column in FEATURE_COLUMNS},
            {column: 2.0 for column in FEATURE_COLUMNS},
            {column: 3.0 for column in FEATURE_COLUMNS},
            {column: 4.0 for column in FEATURE_COLUMNS},
        ]
    )

    health = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", DummyRegressor(strategy="constant", constant=5.5)),
        ]
    )
    health.fit(train_x, np.array([5.5, 5.5, 5.5, 5.5]))

    risk = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("model", LogisticRegression(random_state=440)),
        ]
    )
    risk.fit(train_x, np.array([0, 0, 1, 1]))

    raw = risk.predict_proba(train_x)[:, 1]
    logits = np.log(np.clip(raw, 1e-6, 1 - 1e-6) / np.clip(1 - raw, 1e-6, 1))
    calibrator = LogisticRegression(random_state=440)
    calibrator.fit(logits.reshape(-1, 1), np.array([0, 0, 1, 1]))

    rul_models = {
        "rul_lower.joblib": DummyRegressor(strategy="constant", constant=0.5),
        "rul_median.joblib": DummyRegressor(strategy="constant", constant=1.0),
        "rul_upper.joblib": DummyRegressor(strategy="constant", constant=2.0),
    }
    for model in rul_models.values():
        model.fit(train_x, np.ones(len(train_x)))

    joblib.dump(health, path / "health.joblib")
    joblib.dump(risk, path / "risk.joblib")
    joblib.dump(calibrator, path / "risk_calibrator.joblib")
    for filename, model in rul_models.items():
        joblib.dump(model, path / filename)

    (path / "manifest.json").write_text(
        json.dumps(
            {
                "model_name": "simras_nbi_bridge_deterioration",
                "version": "test-temporal-v1",
                "stage": "RESEARCH_TRANSFER",
                "features": FEATURE_COLUMNS,
                "prediction_horizon_years": 3,
                "training_scope": "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER",
            }
        ),
        encoding="utf-8",
    )
    return path


def test_temporal_evaluator_reports_required_metrics_and_counts(tmp_path: Path):
    poor_key, nonpoor_key = _heldout_keys(2)
    rows: list[dict] = []

    for year, rating in {2022: 7.0, 2023: 6.0, 2024: 5.0, 2025: 4.0}.items():
        rows.append(_feature_row(poor_key, year, rating))
    for year, rating in {2022: 7.0, 2023: 7.0, 2024: 6.0, 2025: 6.0}.items():
        rows.append(_feature_row(nonpoor_key, year, rating))

    panel = pd.DataFrame(rows)
    artifact_dir = _artifact_dir(tmp_path / "bridge_nbi")

    result = evaluate_bridge_temporal_holdout(
        panel,
        artifact_dir=artifact_dir,
        outcome_year=2025,
        horizon_years=3,
    )

    assert result["evaluation_protocol"]["health"] == "2024_features_to_2025_condition"
    assert result["evaluation_protocol"]["risk"] == "2022_features_to_outcomes_through_2025"
    assert result["counts"]["health_rows"] == 2
    assert result["counts"]["risk_rows"] == 2
    assert result["counts"]["risk_positive"] == 1
    assert result["counts"]["risk_negative"] == 1
    assert result["counts"]["rul_events"] >= 1

    metrics = result["metrics"]
    for key in (
        "health_mae_rating",
        "health_rmse_rating",
        "health_persistence_mae_rating",
        "risk_roc_auc",
        "risk_pr_auc",
        "risk_accuracy_at_0_5",
        "risk_f1_at_0_5",
        "risk_brier",
        "risk_ece",
        "rul_mae_years_observed_events",
        "rul_interval_80_coverage_observed_events",
    ):
        assert key in metrics
        assert metrics[key] is not None

    assert result["model"]["version"] == "test-temporal-v1"
    assert result["model"]["stage"] == "RESEARCH_TRANSFER"
