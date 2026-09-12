from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import joblib
import mlflow
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from xgboost import XGBClassifier, XGBRegressor

from simras_ml.features import (
    CATEGORICAL_FEATURES,
    HEALTH_TARGET,
    NUMERIC_FEATURES,
    RISK_TARGET,
    required_columns,
)


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_pipeline(task: str) -> Pipeline:
    preprocessor = ColumnTransformer(
        [
            (
                "numeric",
                Pipeline([("impute", SimpleImputer(strategy="median"))]),
                NUMERIC_FEATURES,
            ),
            (
                "categorical",
                Pipeline(
                    [
                        ("impute", SimpleImputer(strategy="most_frequent")),
                        ("encode", OneHotEncoder(handle_unknown="ignore")),
                    ]
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )
    estimator = (
        XGBRegressor(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="reg:squarederror",
            random_state=42,
        )
        if task == "health"
        else XGBClassifier(
            n_estimators=400,
            max_depth=5,
            learning_rate=0.04,
            subsample=0.85,
            colsample_bytree=0.85,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=42,
        )
    )
    return Pipeline([("features", preprocessor), ("model", estimator)])


def evaluate(task: str, pipeline: Pipeline, test: pd.DataFrame, target: str) -> dict[str, float]:
    truth = test[target]
    if task == "health":
        predicted = pipeline.predict(test)
        return {
            "mae": float(mean_absolute_error(truth, predicted)),
            "rmse": float(np.sqrt(mean_squared_error(truth, predicted))),
            "r2": float(r2_score(truth, predicted)),
        }

    probability = pipeline.predict_proba(test)[:, 1]
    return {
        "roc_auc": float(roc_auc_score(truth, probability)),
        "pr_auc": float(average_precision_score(truth, probability)),
        "brier": float(brier_score_loss(truth, probability)),
    }


def train(task: str, data_path: Path, output_dir: Path) -> dict:
    frame = pd.read_csv(data_path, parse_dates=["state_time"])
    missing = required_columns(task) - set(frame.columns)
    if missing:
        raise ValueError(f"Training data is missing columns: {sorted(missing)}")
    if frame["asset_code"].nunique() < 10:
        raise ValueError("At least 10 independently identified assets are required")

    target = HEALTH_TARGET if task == "health" else RISK_TARGET
    frame = frame.sort_values(["state_time", "asset_code"])
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    train_index, test_index = next(splitter.split(frame, groups=frame["asset_code"]))
    train_frame = frame.iloc[train_index]
    test_frame = frame.iloc[test_index]
    if set(train_frame.asset_code) & set(test_frame.asset_code):
        raise RuntimeError("Asset leakage detected in train/test split")

    pipeline = build_pipeline(task)
    pipeline.fit(train_frame, train_frame[target])
    metrics = evaluate(task, pipeline, test_frame, target)

    created_at = datetime.now(UTC)
    version = created_at.strftime("%Y%m%dT%H%M%SZ")
    output_dir.mkdir(parents=True, exist_ok=True)
    model_path = output_dir / f"{task}_xgb_{version}.joblib"
    joblib.dump(pipeline, model_path)
    model_checksum = checksum(model_path)
    dataset_checksum = checksum(data_path)

    card = {
        "model_name": f"{task}_xgb",
        "version": version,
        "task": task,
        "status": "EXPERIMENTAL_PENDING_REVIEW",
        "feature_version": "asset_state_v1",
        "created_at": created_at.isoformat(),
        "training_rows": len(train_frame),
        "test_rows": len(test_frame),
        "training_assets": train_frame.asset_code.nunique(),
        "test_assets": test_frame.asset_code.nunique(),
        "dataset_checksum": dataset_checksum,
        "model_checksum": model_checksum,
        "metrics": metrics,
        "limitations": [
            "Not an engineering safety determination",
            "Requires label and calibration review before deployment",
            "RUL is outside this model's scope",
        ],
    }
    card_path = output_dir / f"{task}_xgb_{version}.json"
    card_path.write_text(json.dumps(card, indent=2), encoding="utf-8")

    mlflow.set_experiment("simras-health-risk")
    with mlflow.start_run(run_name=f"{task}-{version}"):
        mlflow.log_params({"task": task, "feature_version": "asset_state_v1"})
        mlflow.log_metrics(metrics)
        mlflow.log_artifact(str(card_path))
        mlflow.log_artifact(str(model_path))
    return card


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", choices=["health", "risk"], required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("artifacts/models"))
    args = parser.parse_args()
    print(json.dumps(train(args.task, args.data, args.output), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
