from __future__ import annotations

import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, RegressorMixin
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from simras_ml.nbi import FEATURE_COLUMNS, add_targets, stable_partition


class PersistenceHealthModel(BaseEstimator, RegressorMixin):
    """Explicit baseline: current condition rating predicts next condition rating."""

    def fit(self, x, y=None):
        return self

    def predict(self, x):
        if isinstance(x, pd.DataFrame):
            if "condition_rating" not in x.columns:
                raise ValueError("condition_rating is required for persistence health")
            return x["condition_rating"].to_numpy(dtype=float)
        condition_index = FEATURE_COLUMNS.index("condition_rating")
        values = np.asarray(x, dtype=float)
        return values[:, condition_index]


def _checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def _pipeline(estimator) -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
            ("model", estimator),
        ]
    )


def train_challenger_models(
    panel: pd.DataFrame,
    artifact_dir: Path,
    *,
    champion_dir: Path,
    max_training_year: int = 2024,
    min_rows: int = 100_000,
    min_bridges: int = 20_000,
    min_years: int = 4,
    horizon_years: int = 3,
) -> dict:
    """Train a bridge-risk challenger without touching the accepted champion.

    The final temporal outcome year must remain outside this function. Rows later
    than ``max_training_year`` are discarded before targets are constructed, and
    bridge identities assigned to stable partition >= 85 are never used for fit
    or calibration so they remain available for the final temporal comparison.
    """

    training_panel = panel[panel["report_year"] <= max_training_year].copy()
    if training_panel.empty:
        raise ValueError("No rows remain after applying max_training_year")

    labelled = add_targets(training_panel, horizon_years=horizon_years)
    if len(labelled) < min_rows:
        raise ValueError(f"Training gate failed: {len(labelled):,} rows < {min_rows:,}")

    bridges = int(labelled["bridge_key"].nunique())
    training_years = sorted(int(value) for value in labelled["report_year"].unique())
    if bridges < min_bridges:
        raise ValueError(f"Training gate failed: {bridges:,} bridges < {min_bridges:,}")
    if len(training_years) < min_years:
        raise ValueError(
            f"Training gate failed: {len(training_years)} labelled years < {min_years}"
        )
    if any(year > max_training_year for year in training_years):
        raise ValueError("Temporal leakage detected in challenger training years")

    risk_data = labelled.dropna(subset=["poor_within_horizon"]).copy()
    partitions = risk_data["bridge_key"].map(stable_partition)
    risk_train = risk_data[partitions < 70].copy()
    risk_calibration = risk_data[(partitions >= 70) & (partitions < 85)].copy()

    for name, frame in {"training": risk_train, "calibration": risk_calibration}.items():
        if frame.empty:
            raise ValueError(f"Risk {name} partition is empty")
        if frame["poor_within_horizon"].nunique() < 2:
            raise ValueError(f"Risk {name} data must contain both outcome classes")

    positives = float(risk_train["poor_within_horizon"].sum())
    negatives = float(len(risk_train) - positives)
    if positives <= 0:
        raise ValueError("Risk training data has no positive outcomes")
    scale_pos_weight = max(1.0, negatives / positives)

    risk = _pipeline(
        XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_estimators=320,
            learning_rate=0.035,
            max_depth=5,
            min_child_weight=3.0,
            subsample=0.90,
            colsample_bytree=0.90,
            reg_alpha=0.05,
            reg_lambda=2.0,
            scale_pos_weight=scale_pos_weight,
            tree_method="hist",
            random_state=440,
            n_jobs=2,
        )
    )
    risk.fit(
        risk_train[FEATURE_COLUMNS],
        risk_train["poor_within_horizon"].astype(int),
    )

    raw_calibration = risk.predict_proba(risk_calibration[FEATURE_COLUMNS])[:, 1]
    calibrator = LogisticRegression(random_state=440, max_iter=1000)
    calibrator.fit(
        _logit(raw_calibration),
        risk_calibration["poor_within_horizon"].astype(int),
    )

    artifact_dir = Path(artifact_dir)
    champion_dir = Path(champion_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    health = PersistenceHealthModel()
    joblib.dump(health, artifact_dir / "health.joblib")
    joblib.dump(risk, artifact_dir / "risk.joblib")
    joblib.dump(calibrator, artifact_dir / "risk_calibrator.joblib")

    copied_rul: list[str] = []
    for filename in ("rul_lower.joblib", "rul_median.joblib", "rul_upper.joblib"):
        source = champion_dir / filename
        if not source.exists():
            raise FileNotFoundError(f"Champion RUL artifact missing: {source}")
        shutil.copy2(source, artifact_dir / filename)
        copied_rul.append(filename)

    artifact_files = [
        "health.joblib",
        "risk.joblib",
        "risk_calibrator.joblib",
        *copied_rul,
    ]
    checksums = {
        filename: _checksum(artifact_dir / filename)
        for filename in artifact_files
    }

    manifest = {
        "model_name": "simras_nbi_bridge_deterioration_challenger",
        "version": datetime.now(UTC).strftime("nbi_xgb_challenger_%Y%m%d_%H%M%S"),
        "stage": "CHALLENGER_RESEARCH_TRANSFER",
        "model_validated": False,
        "training_scope": "FHWA_NBI_US_BRIDGES_RESEARCH_TRANSFER",
        "feature_version": "nbi_bridge_state_v1",
        "features": FEATURE_COLUMNS,
        "prediction_horizon_years": horizon_years,
        "health_method": "PERSISTENCE_BASELINE",
        "risk_algorithm": "XGBoostClassifier",
        "rul_method": "COPIED_FROM_ACCEPTED_CHAMPION",
        "champion_preserved": True,
        "max_training_year": max_training_year,
        "training_years": training_years,
        "training_rows": int(len(labelled)),
        "unique_bridges": bridges,
        "risk_training_rows": int(len(risk_train)),
        "risk_calibration_rows": int(len(risk_calibration)),
        "risk_training_bridges": int(risk_train["bridge_key"].nunique()),
        "risk_calibration_bridges": int(risk_calibration["bridge_key"].nunique()),
        "heldout_identity_rule": "stable_partition >= 85",
        "heldout_identities_used_for_training": False,
        "risk_scale_pos_weight": float(scale_pos_weight),
        "artifact_checksums": checksums,
        "data_source": "U.S. FHWA National Bridge Inventory annual downloads",
        "limitations": [
            "Not locally validated for Andhra Pradesh",
            "2025 is excluded from challenger training and reserved for temporal evaluation",
            "Health uses the persistence baseline because the learned health model did not beat it",
            "RUL artifacts are copied unchanged from the accepted research-transfer champion",
            "RUL represents observed deterioration-event timing, not structural failure time",
        ],
        "created_at": datetime.now(UTC).isoformat(),
    }
    (artifact_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )
    return manifest
