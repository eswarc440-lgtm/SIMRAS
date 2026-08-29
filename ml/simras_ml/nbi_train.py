from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline

from simras_ml.nbi import FEATURE_COLUMNS, add_targets, stable_partition


def _split(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    partitions = frame["bridge_key"].map(stable_partition)
    return frame[partitions < 70], frame[(partitions >= 70) & (partitions < 85)], frame[partitions >= 85]


def _pipeline(estimator) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("model", estimator),
        ]
    )


def _logit(values: np.ndarray) -> np.ndarray:
    values = np.clip(values, 1e-6, 1 - 1e-6)
    return np.log(values / (1 - values)).reshape(-1, 1)


def _ece(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0, 1, bins + 1)
    score = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        mask = (probabilities >= lower) & (probabilities < upper)
        if mask.any():
            score += mask.mean() * abs(labels[mask].mean() - probabilities[mask].mean())
    return float(score)


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def train_models(
    panel: pd.DataFrame,
    artifact_dir: Path,
    *,
    min_rows: int = 100_000,
    min_bridges: int = 20_000,
    min_years: int = 5,
    horizon_years: int = 3,
) -> dict:
    labelled = add_targets(panel, horizon_years=horizon_years)
    if len(labelled) < min_rows:
        raise ValueError(f"Training gate failed: {len(labelled):,} rows < {min_rows:,}")
    bridges = labelled["bridge_key"].nunique()
    years = labelled["report_year"].nunique()
    if bridges < min_bridges:
        raise ValueError(f"Training gate failed: {bridges:,} bridges < {min_bridges:,}")
    if years < min_years:
        raise ValueError(f"Training gate failed: {years} years < {min_years}")

    artifact_dir.mkdir(parents=True, exist_ok=True)
    train, calibration, test = _split(labelled)
    if min(len(train), len(calibration), len(test)) == 0:
        raise ValueError("Stable bridge-level split produced an empty partition")

    health = _pipeline(
        HistGradientBoostingRegressor(
            max_iter=160,
            learning_rate=0.06,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            random_state=440,
        )
    )
    health.fit(train[FEATURE_COLUMNS], train["next_condition_rating"])
    health_predictions = np.clip(health.predict(test[FEATURE_COLUMNS]), 0, 9)
    health_calibration_predictions = np.clip(
        health.predict(calibration[FEATURE_COLUMNS]), 0, 9
    )
    health_errors = (
        calibration["next_condition_rating"].to_numpy()
        - health_calibration_predictions
    )

    risk_data = labelled.dropna(subset=["poor_within_horizon"])
    risk_train, risk_calibration, risk_test = _split(risk_data)
    for partition_name, partition in {
        "training": risk_train,
        "calibration": risk_calibration,
        "test": risk_test,
    }.items():
        if partition["poor_within_horizon"].nunique() < 2:
            raise ValueError(
                f"Risk {partition_name} data must contain both poor and non-poor outcomes"
            )
    risk = _pipeline(
        HistGradientBoostingClassifier(
            max_iter=160,
            learning_rate=0.06,
            max_leaf_nodes=31,
            l2_regularization=1.0,
            random_state=440,
        )
    )
    risk.fit(risk_train[FEATURE_COLUMNS], risk_train["poor_within_horizon"].astype(int))
    raw_calibration = risk.predict_proba(risk_calibration[FEATURE_COLUMNS])[:, 1]
    calibrator = LogisticRegression(random_state=440)
    calibrator.fit(_logit(raw_calibration), risk_calibration["poor_within_horizon"].astype(int))
    raw_test = risk.predict_proba(risk_test[FEATURE_COLUMNS])[:, 1]
    risk_probabilities = calibrator.predict_proba(_logit(raw_test))[:, 1]
    risk_labels = risk_test["poor_within_horizon"].astype(int).to_numpy()

    rul_data = labelled.dropna(subset=["rul_years"]).copy()
    rul_data = rul_data[(rul_data["rul_years"] > 0) & (rul_data["rul_years"] <= 30)]
    rul_train, _, rul_test = _split(rul_data)
    if len(rul_train) < max(100, min_rows // 100):
        raise ValueError("RUL gate failed: insufficient observed deterioration events")
    if rul_test.empty:
        raise ValueError("RUL gate failed: no observed deterioration events in test partition")
    rul_models = {
        "rul_lower.joblib": HistGradientBoostingRegressor(
            loss="quantile", quantile=0.1, max_iter=120, random_state=440
        ),
        "rul_median.joblib": HistGradientBoostingRegressor(
            loss="absolute_error", max_iter=140, random_state=440
        ),
        "rul_upper.joblib": HistGradientBoostingRegressor(
            loss="quantile", quantile=0.9, max_iter=120, random_state=440
        ),
    }
    fitted_rul: dict[str, Pipeline] = {}
    for filename, estimator in rul_models.items():
        model = _pipeline(estimator)
        model.fit(rul_train[FEATURE_COLUMNS], rul_train["rul_years"])
        fitted_rul[filename] = model

    rul_median = np.clip(fitted_rul["rul_median.joblib"].predict(rul_test[FEATURE_COLUMNS]), 0, 30)
    rul_lower = np.clip(fitted_rul["rul_lower.joblib"].predict(rul_test[FEATURE_COLUMNS]), 0, 30)
    rul_upper = np.clip(fitted_rul["rul_upper.joblib"].predict(rul_test[FEATURE_COLUMNS]), 0, 30)
    observed_rul = rul_test["rul_years"].to_numpy()

    metrics = {
        "health_mae_rating": float(mean_absolute_error(test["next_condition_rating"], health_predictions)),
        "health_rmse_rating": float(mean_squared_error(test["next_condition_rating"], health_predictions) ** 0.5),
        "risk_roc_auc": float(roc_auc_score(risk_labels, risk_probabilities)),
        "risk_brier": float(brier_score_loss(risk_labels, risk_probabilities)),
        "risk_f1_at_0_5": float(f1_score(risk_labels, risk_probabilities >= 0.5)),
        "risk_ece": _ece(risk_labels, risk_probabilities),
        "rul_mae_years_observed_events": float(mean_absolute_error(observed_rul, rul_median)),
        "rul_interval_80_coverage_observed_events": float(
            np.mean((observed_rul >= np.minimum(rul_lower, rul_upper)) & (observed_rul <= np.maximum(rul_lower, rul_upper)))
        ),
    }
    gates = {
        "health_mae_le_1_0": metrics["health_mae_rating"] <= 1.0,
        "risk_auc_ge_0_70": metrics["risk_roc_auc"] >= 0.70,
        "risk_brier_le_0_20": metrics["risk_brier"] <= 0.20,
        "risk_ece_le_0_10": metrics["risk_ece"] <= 0.10,
        "rul_mae_le_5_years": metrics["rul_mae_years_observed_events"] <= 5.0,
    }
    stage = "RESEARCH_TRANSFER" if all(gates.values()) else "REJECTED"

    artifacts = {
        "health.joblib": health,
        "risk.joblib": risk,
        "risk_calibrator.joblib": calibrator,
        **fitted_rul,
    }
    checksums: dict[str, str] = {}
    for filename, model in artifacts.items():
        path = artifact_dir / filename
        joblib.dump(model, path)
        checksums[filename] = _checksum(path)

    manifest = {
        "model_name": "simras_nbi_bridge_deterioration",
        "version": datetime.now(UTC).strftime("nbi_transfer_%Y%m%d_%H%M%S"),
        "stage": stage,
        "model_validated": False,
        "training_scope": "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER",
        "prediction_horizon_years": horizon_years,
        "feature_version": "nbi_bridge_state_v1",
        "features": FEATURE_COLUMNS,
        "training_rows": len(labelled),
        "unique_bridges": bridges,
        "training_years": sorted(int(value) for value in labelled["report_year"].unique()),
        "metrics": metrics,
        "gates": gates,
        "health_error_quantiles_rating": {
            "lower": float(np.quantile(health_errors, 0.1)),
            "upper": float(np.quantile(health_errors, 0.9)),
        },
        "artifact_checksums": checksums,
        "data_source": "U.S. FHWA National Bridge Inventory annual downloads",
        "source_url": "https://www.fhwa.dot.gov/bridge/nbi/ascii.cfm",
        "limitations": [
            "Not locally validated for Andhra Pradesh",
            "RUL evaluation includes observed deterioration events and is subject to censoring bias",
            "Must not be the sole basis for structural or maintenance decisions",
            "Dam and barrage predictions are outside this model's scope",
        ],
        "created_at": datetime.now(UTC).isoformat(),
    }
    (artifact_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest
