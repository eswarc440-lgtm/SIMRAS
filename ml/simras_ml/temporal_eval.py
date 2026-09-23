from __future__ import annotations

import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    roc_auc_score,
)

from simras_ml.nbi import FEATURE_COLUMNS, stable_partition


def _heldout_bridge_keys(panel: pd.DataFrame) -> set[str]:
    return {
        str(key)
        for key in panel["bridge_key"].dropna().astype(str).unique()
        if stable_partition(str(key)) >= 85
    }


def _logit(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 1e-6, 1 - 1e-6)
    return np.log(clipped / (1 - clipped)).reshape(-1, 1)


def _ece(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    score = 0.0
    for lower, upper in zip(edges[:-1], edges[1:], strict=True):
        if upper == 1.0:
            mask = (probabilities >= lower) & (probabilities <= upper)
        else:
            mask = (probabilities >= lower) & (probabilities < upper)
        if mask.any():
            score += float(mask.mean()) * abs(
                float(labels[mask].mean()) - float(probabilities[mask].mean())
            )
    return float(score)


def build_temporal_holdouts(
    panel: pd.DataFrame,
    *,
    outcome_year: int = 2025,
    horizon_years: int = 3,
) -> dict[str, pd.DataFrame]:
    """Build strict temporal holdouts from held-out bridge identities.

    Health uses the observation immediately before ``outcome_year`` as the
    feature row and the ``outcome_year`` condition as the target.

    Risk uses the feature row at ``outcome_year - horizon_years`` and labels
    whether the bridge reaches poor condition (rating <= 4) at any later
    observation through ``outcome_year``.

    RUL contains only rows whose first later poor-condition event is observed
    exactly in ``outcome_year``. This is an observed-event deterioration
    horizon, not a structural failure-time forecast.
    """

    required = {"bridge_key", "report_year", "condition_rating"}
    missing = required - set(panel.columns)
    if missing:
        raise ValueError(f"Panel is missing required columns: {sorted(missing)}")

    if outcome_year not in set(panel["report_year"].dropna().astype(int)):
        raise ValueError(f"Outcome year {outcome_year} is not present in the panel")
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    heldout_keys = _heldout_bridge_keys(panel)
    heldout = panel[panel["bridge_key"].astype(str).isin(heldout_keys)].copy()
    heldout = heldout.sort_values(["bridge_key", "report_year"]).reset_index(drop=True)

    health_rows: list[dict] = []
    risk_rows: list[dict] = []
    rul_rows: list[dict] = []

    risk_feature_year = outcome_year - horizon_years

    for bridge_key, group in heldout.groupby("bridge_key", sort=True):
        rows = group.sort_values("report_year").to_dict("records")
        by_year = {int(row["report_year"]): row for row in rows}

        outcome = by_year.get(outcome_year)
        previous = by_year.get(outcome_year - 1)
        if outcome is not None and previous is not None:
            record = dict(previous)
            record["next_condition_rating"] = float(outcome["condition_rating"])
            health_rows.append(record)

        risk_feature = by_year.get(risk_feature_year)
        if risk_feature is not None and outcome is not None:
            future = [
                row
                for row in rows
                if risk_feature_year < int(row["report_year"]) <= outcome_year
            ]
            poor_within_horizon = float(
                any(float(row["condition_rating"]) <= 4.0 for row in future)
            )
            record = dict(risk_feature)
            record["poor_within_horizon"] = poor_within_horizon
            risk_rows.append(record)

        for index, current in enumerate(rows[:-1]):
            current_year = int(current["report_year"])
            future = [
                row
                for row in rows[index + 1 :]
                if int(row["report_year"]) <= outcome_year
            ]
            event = next(
                (
                    row
                    for row in future
                    if float(row["condition_rating"]) <= 4.0
                    and int(row["report_year"]) > current_year
                ),
                None,
            )
            if event is None or int(event["report_year"]) != outcome_year:
                continue
            record = dict(current)
            record["rul_years"] = float(outcome_year - current_year)
            rul_rows.append(record)

    return {
        "health": pd.DataFrame(health_rows),
        "risk": pd.DataFrame(risk_rows),
        "rul": pd.DataFrame(rul_rows),
    }


def evaluate_bridge_temporal_holdout(
    panel: pd.DataFrame,
    *,
    artifact_dir: str | Path,
    outcome_year: int = 2025,
    horizon_years: int = 3,
) -> dict:
    """Evaluate an existing bridge artifact without retraining or modifying it."""

    root = Path(artifact_dir)
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing bridge manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_artifacts = {
        "health": root / "health.joblib",
        "risk": root / "risk.joblib",
        "risk_calibrator": root / "risk_calibrator.joblib",
        "rul_lower": root / "rul_lower.joblib",
        "rul_median": root / "rul_median.joblib",
        "rul_upper": root / "rul_upper.joblib",
    }
    missing = [str(path) for path in required_artifacts.values() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing bridge artifacts: {', '.join(missing)}")

    models = {name: joblib.load(path) for name, path in required_artifacts.items()}
    holdouts = build_temporal_holdouts(
        panel,
        outcome_year=outcome_year,
        horizon_years=horizon_years,
    )
    health = holdouts["health"]
    risk = holdouts["risk"]
    rul = holdouts["rul"]

    if health.empty:
        raise ValueError("Health temporal holdout is empty")
    if risk.empty:
        raise ValueError("Risk temporal holdout is empty")
    if risk["poor_within_horizon"].nunique() < 2:
        raise ValueError("Risk temporal holdout must contain both poor and non-poor outcomes")

    health_predictions = np.clip(models["health"].predict(health[FEATURE_COLUMNS]), 0, 9)
    health_observed = health["next_condition_rating"].to_numpy(dtype=float)
    health_persistence = np.clip(
        health["condition_rating"].to_numpy(dtype=float),
        0,
        9,
    )

    raw_risk = models["risk"].predict_proba(risk[FEATURE_COLUMNS])[:, 1]
    risk_probabilities = models["risk_calibrator"].predict_proba(_logit(raw_risk))[:, 1]
    risk_labels = risk["poor_within_horizon"].astype(int).to_numpy()
    risk_classes = (risk_probabilities >= 0.5).astype(int)

    rul_mae: float | None = None
    rul_coverage: float | None = None
    if not rul.empty:
        observed_rul = rul["rul_years"].to_numpy(dtype=float)
        rul_median = np.clip(models["rul_median"].predict(rul[FEATURE_COLUMNS]), 0, 30)
        rul_lower = np.clip(models["rul_lower"].predict(rul[FEATURE_COLUMNS]), 0, 30)
        rul_upper = np.clip(models["rul_upper"].predict(rul[FEATURE_COLUMNS]), 0, 30)
        lower = np.minimum(rul_lower, rul_upper)
        upper = np.maximum(rul_lower, rul_upper)
        rul_mae = float(mean_absolute_error(observed_rul, rul_median))
        rul_coverage = float(np.mean((observed_rul >= lower) & (observed_rul <= upper)))

    metrics = {
        "health_mae_rating": float(mean_absolute_error(health_observed, health_predictions)),
        "health_rmse_rating": float(mean_squared_error(health_observed, health_predictions) ** 0.5),
        "health_persistence_mae_rating": float(
            mean_absolute_error(health_observed, health_persistence)
        ),
        "risk_roc_auc": float(roc_auc_score(risk_labels, risk_probabilities)),
        "risk_pr_auc": float(average_precision_score(risk_labels, risk_probabilities)),
        "risk_accuracy_at_0_5": float(accuracy_score(risk_labels, risk_classes)),
        "risk_f1_at_0_5": float(f1_score(risk_labels, risk_classes)),
        "risk_brier": float(brier_score_loss(risk_labels, risk_probabilities)),
        "risk_ece": _ece(risk_labels, risk_probabilities),
        "rul_mae_years_observed_events": rul_mae,
        "rul_interval_80_coverage_observed_events": rul_coverage,
    }

    return {
        "model": {
            "model_name": manifest.get("model_name"),
            "version": manifest.get("version"),
            "stage": manifest.get("stage"),
            "training_scope": manifest.get("training_scope"),
        },
        "evaluation_protocol": {
            "bridge_identity_holdout": "stable_partition >= 85",
            "health": f"{outcome_year - 1}_features_to_{outcome_year}_condition",
            "risk": (
                f"{outcome_year - horizon_years}_features_to_outcomes_through_{outcome_year}"
            ),
            "rul": f"observed_deterioration_events_first_seen_in_{outcome_year}",
            "outcome_year": outcome_year,
            "horizon_years": horizon_years,
            "artifact_retrained": False,
        },
        "counts": {
            "health_rows": int(len(health)),
            "health_bridges": int(health["bridge_key"].nunique()),
            "risk_rows": int(len(risk)),
            "risk_bridges": int(risk["bridge_key"].nunique()),
            "risk_positive": int(risk_labels.sum()),
            "risk_negative": int(len(risk_labels) - risk_labels.sum()),
            "rul_events": int(len(rul)),
            "rul_bridges": int(rul["bridge_key"].nunique()) if not rul.empty else 0,
        },
        "metrics": metrics,
        "targets": {
            "risk_roc_auc_target": 0.97,
            "risk_roc_auc_target_met": metrics["risk_roc_auc"] >= 0.97,
            "health_beats_persistence": (
                metrics["health_mae_rating"] < metrics["health_persistence_mae_rating"]
            ),
        },
    }
