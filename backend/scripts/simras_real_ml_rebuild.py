from __future__ import annotations

import json
import math
import os
import re
import shutil
import warnings
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import joblib

from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import (
    mean_absolute_error,
    mean_squared_error,
    r2_score,
    accuracy_score,
    balanced_accuracy_score,
    roc_auc_score,
    average_precision_score,
    recall_score,
    precision_score,
    f1_score,
    brier_score_loss,
)
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

try:
    from xgboost import XGBRegressor, XGBClassifier
    HAVE_XGB = True
except Exception:
    HAVE_XGB = False

try:
    from lightgbm import LGBMRegressor, LGBMClassifier
    HAVE_LGBM = True
except Exception:
    HAVE_LGBM = False


# =============================================================================
# CONFIGURATION
# =============================================================================

ROOT = Path("/workspace")
BACKEND = ROOT / "backend"

RUN_ID = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

REPORT_ROOT = BACKEND / "reports" / "ml"
RUN_DIR = REPORT_ROOT / f"run_{RUN_ID}"
LATEST_DIR = REPORT_ROOT / "latest"

ARTIFACT_ROOT = BACKEND / "ml_artifacts"
CANDIDATE_DIR = ARTIFACT_ROOT / "candidates" / RUN_ID
PRODUCTION_DIR = ARTIFACT_ROOT / "production"

for p in [RUN_DIR, CANDIDATE_DIR]:
    p.mkdir(parents=True, exist_ok=True)

if LATEST_DIR.exists():
    shutil.rmtree(LATEST_DIR)
LATEST_DIR.mkdir(parents=True, exist_ok=True)

PRODUCTION_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# Strict quality gates.
# User requested approximately 97-98% real-world agreement.
# These are never forced; failure means NO production promotion.
# -------------------------------------------------------------------------

RISK_GATES = {
    "accuracy": 0.97,
    "balanced_accuracy": 0.95,
    "roc_auc": 0.97,
    "recall": 0.95,
    "brier_max": 0.08,
    "ece_max": 0.03,
}

HEALTH_GATES = {
    "r2": 0.95,
    "normalized_mae_max": 0.03,
    "agreement_within_5pct": 0.97,
}

MIN_ROWS = 200
MIN_GROUPS = 30
MIN_TEST_ROWS = 30
MIN_CLASS_EVENTS = 10

log_lines = []


def log(msg=""):
    print(msg, flush=True)
    log_lines.append(str(msg))


def dump_json(path, obj):
    path.write_text(
        json.dumps(obj, indent=2, default=str),
        encoding="utf-8",
    )


def normalize_name(x):
    return re.sub(r"[^a-z0-9]+", "_", str(x).strip().lower()).strip("_")


def normalize_columns(df):
    seen = {}
    cols = []
    for c in df.columns:
        base = normalize_name(c)
        if not base:
            base = "column"
        seen[base] = seen.get(base, 0) + 1
        if seen[base] > 1:
            base = f"{base}_{seen[base]}"
        cols.append(base)
    out = df.copy()
    out.columns = cols
    return out


def first_col(df, candidates):
    cols = set(df.columns)
    for c in candidates:
        c = normalize_name(c)
        if c in cols:
            return c
    return None


def skip_file(p: Path):
    s = str(p).lower().replace("\\", "/")
    blocked = [
        "/.git/",
        "/node_modules/",
        "/frontend/dist/",
        "/reports/ml/",
        "/ml_artifacts/",
        "/__pycache__/",
    ]
    return any(x in s for x in blocked)


# =============================================================================
# DATASET DISCOVERY
# =============================================================================

HEALTH_TARGETS = [
    "health_target",
    "target_health",
    "health_score_target",
    "future_health",
    "next_health",
    "condition_target",
    "condition_score_target",
    "health_score",
    "health",
]

RISK_TARGETS = [
    "risk_target",
    "target_risk",
    "risk_label",
    "high_risk",
    "failure_target",
    "failure_label",
    "unsafe",
    "deterioration_event",
    "risk_class",
]

GROUP_COLS = [
    "asset_id",
    "asset_code",
    "structure_number",
    "structure_id",
    "bridge_id",
    "dam_id",
    "facility_id",
]

DATE_COLS = [
    "state_date",
    "observation_date",
    "inspection_date",
    "measurement_date",
    "record_date",
    "date",
    "timestamp",
    "observed_at",
]

TYPE_COLS = [
    "asset_type",
    "infrastructure_type",
    "facility_type",
]

SOURCE_COLS = [
    "source",
    "source_type",
    "data_source",
    "provenance",
    "dataset_source",
    "organisation",
    "organization",
]


def read_dataset(path):
    try:
        if path.suffix.lower() == ".csv":
            return pd.read_csv(path, low_memory=False, nrows=500000)
        if path.suffix.lower() == ".parquet":
            return pd.read_parquet(path)
    except Exception as exc:
        return None
    return None


def dataset_score(path, df):
    name = str(path).lower()
    score = 0

    for token in [
        "train",
        "training",
        "nbi",
        "bridge",
        "dam",
        "inspection",
        "condition",
        "health",
        "risk",
        "feature",
        "dataset",
    ]:
        if token in name:
            score += 4

    if first_col(df, HEALTH_TARGETS):
        score += 30
    if first_col(df, RISK_TARGETS):
        score += 30
    if first_col(df, GROUP_COLS):
        score += 15
    if first_col(df, DATE_COLS):
        score += 8

    score += min(len(df) / 1000, 25)

    return score


candidate_files = []

for ext in ("*.csv", "*.parquet"):
    for p in ROOT.rglob(ext):
        if p.is_file() and not skip_file(p):
            ps = str(p).lower()
            if any(
                bad in ps
                for bad in [
                    "predicted_vs_actual",
                    "leaderboard",
                    "error_analysis",
                    "prediction_output",
                    "audit_latest",
                ]
            ):
                continue
            candidate_files.append(p)

dataset_inventory = []

log("=" * 100)
log("SIMRAS REAL-WORLD ML REBUILD + VALIDATION")
log("=" * 100)
log(f"RUN ID: {RUN_ID}")
log(f"ROOT: {ROOT}")
log("")
log("1. DISCOVER TRAINING DATA")
log("-" * 100)

for p in candidate_files:
    df = read_dataset(p)
    if df is None or len(df) < 20:
        continue

    df = normalize_columns(df)

    h = first_col(df, HEALTH_TARGETS)
    r = first_col(df, RISK_TARGETS)
    g = first_col(df, GROUP_COLS)
    d = first_col(df, DATE_COLS)
    t = first_col(df, TYPE_COLS)

    if not h and not r:
        continue

    item = {
        "path": str(p),
        "rows": int(len(df)),
        "columns": int(len(df.columns)),
        "health_target": h,
        "risk_target": r,
        "group_column": g,
        "date_column": d,
        "type_column": t,
        "score": dataset_score(p, df),
    }

    dataset_inventory.append(item)

dataset_inventory.sort(
    key=lambda x: (x["score"], x["rows"]),
    reverse=True,
)

for x in dataset_inventory[:30]:
    log(
        f"{x['rows']:>8,} rows | "
        f"health={x['health_target']} | "
        f"risk={x['risk_target']} | "
        f"group={x['group_column']} | "
        f"{x['path']}"
    )


# =============================================================================
# CURRENT DATABASE PREDICTION STATE
# =============================================================================

db_state = {}

try:
    from sqlalchemy import create_engine, text

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if db_url:
        db_url = db_url.replace("+asyncpg", "")
        engine = create_engine(db_url)

        with engine.connect() as conn:
            exists = conn.execute(
                text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema='public'
                      AND table_name='predictions'
                )
                """)
            ).scalar()

            if exists:
                rows = conn.execute(
                    text("""
                    SELECT
                        COALESCE(target,'?') AS target,
                        COALESCE(model_version,'?') AS model_version,
                        COUNT(*) AS n
                    FROM public.predictions
                    GROUP BY target, model_version
                    ORDER BY n DESC
                    """)
                ).mappings().all()

                db_state["predictions"] = [dict(r) for r in rows]

        engine.dispose()

except Exception as exc:
    db_state["error"] = str(exc)


# =============================================================================
# DATA REALITY / SYNTHETIC FILTERING
# =============================================================================

def synthetic_mask(df):
    mask = pd.Series(False, index=df.index)

    pattern = re.compile(
        r"\b(synthetic|demo|mock|fake|placeholder|generated[_ -]?label)\b",
        re.I,
    )

    candidate_cols = []

    for c in df.columns:
        lc = c.lower()
        if (
            c in SOURCE_COLS
            or "source" in lc
            or "provenance" in lc
            or "synthetic" in lc
            or "demo" in lc
        ):
            candidate_cols.append(c)

    for c in candidate_cols[:30]:
        try:
            mask |= df[c].astype(str).str.contains(pattern, na=False)
        except Exception:
            pass

    for c in df.columns:
        if "is_synthetic" in c.lower() or "synthetic_flag" in c.lower():
            try:
                mask |= (
                    df[c]
                    .astype(str)
                    .str.lower()
                    .isin(["true", "1", "yes", "y"])
                )
            except Exception:
                pass

    return mask


def provenance_status(path, df):
    source_text = []
    for c in df.columns:
        if (
            c in SOURCE_COLS
            or "source" in c.lower()
            or "provenance" in c.lower()
        ):
            try:
                vals = (
                    df[c]
                    .dropna()
                    .astype(str)
                    .drop_duplicates()
                    .head(100)
                    .tolist()
                )
                source_text.extend(vals)
            except Exception:
                pass

    blob = (
        str(path)
        + " "
        + " ".join(source_text)
    ).lower()

    if any(
        token in blob
        for token in [
            "synthetic",
            "demo",
            "mock",
            "placeholder",
        ]
    ):
        return "SYNTHETIC_OR_DEMO"

    if (
        "andhra pradesh" in blob
        and any(
            token in blob
            for token in [
                "inspection",
                "pwd",
                "roads and buildings",
                "water resources department",
                "wr department",
                "government",
            ]
        )
    ):
        return "LOCAL_GROUND_TRUTH_CANDIDATE"

    if any(
        token in blob
        for token in [
            "national bridge inventory",
            " nbi",
            "/nbi",
            "\\nbi",
        ]
    ):
        return "REAL_EXTERNAL_TRANSFER"

    if any(
        token in blob
        for token in [
            "nhai",
            "cwc",
            "india-wris",
            "india wris",
            "government",
            "inspection",
        ]
    ):
        return "REAL_SOURCE_REQUIRES_LOCAL_MATCH_VALIDATION"

    return "PROVENANCE_UNVERIFIED"


# =============================================================================
# TARGET NORMALIZATION
# =============================================================================

def binary_target(series):
    s = series.copy()

    numeric = pd.to_numeric(s, errors="coerce")
    numeric_unique = sorted(numeric.dropna().unique().tolist())

    if len(numeric_unique) == 2:
        lo, hi = numeric_unique
        y = numeric.map({lo: 0, hi: 1})
        return y.astype(float), {
            "type": "numeric_binary",
            str(lo): 0,
            str(hi): 1,
        }

    text = s.astype(str).str.strip().str.lower()

    positive = {
        "1",
        "true",
        "yes",
        "high",
        "critical",
        "fail",
        "failed",
        "failure",
        "unsafe",
        "poor",
        "severe",
        "deteriorated",
        "deterioration",
    }

    negative = {
        "0",
        "false",
        "no",
        "low",
        "medium",
        "safe",
        "good",
        "fair",
        "normal",
        "pass",
        "passed",
        "healthy",
    }

    mapping = {}
    values = set(text.dropna().unique())

    if values and values.issubset(positive | negative):
        for v in values:
            mapping[v] = 1 if v in positive else 0

        y = text.map(mapping)
        return y.astype(float), {
            "type": "text_binary",
            "mapping": mapping,
        }

    return None, {
        "type": "unsupported",
        "values": sorted(list(values))[:30],
    }


# =============================================================================
# TEMPORAL TARGET
# =============================================================================

def maybe_future_target(df, target_col, group_col, date_col):
    result = df.copy()

    already_future = any(
        token in target_col.lower()
        for token in ["future", "next", "forward"]
    )

    if already_future:
        result["__ml_target"] = result[target_col]
        return result, "explicit_future_target"

    if not group_col or not date_col:
        result["__ml_target"] = result[target_col]
        return result, "cross_sectional"

    try:
        parsed = pd.to_datetime(
            result[date_col],
            errors="coerce",
            utc=True,
        )

        valid_fraction = parsed.notna().mean()

        if valid_fraction < 0.7:
            result["__ml_target"] = result[target_col]
            return result, "cross_sectional"

        result["__parsed_date"] = parsed

        counts = result.groupby(group_col).size()
        repeated_fraction = float((counts >= 2).mean())

        if repeated_fraction < 0.20:
            result["__ml_target"] = result[target_col]
            return result, "cross_sectional"

        result = result.sort_values(
            [group_col, "__parsed_date"]
        )

        result["__ml_target"] = (
            result.groupby(group_col)[target_col].shift(-1)
        )

        future_rows = int(result["__ml_target"].notna().sum())

        if future_rows < MIN_ROWS:
            result["__ml_target"] = result[target_col]
            return result, "cross_sectional"

        result["__current_target_state"] = result[target_col]

        return result, "next_observation"

    except Exception:
        result["__ml_target"] = result[target_col]
        return result, "cross_sectional"


# =============================================================================
# FEATURE ENGINEERING
# =============================================================================

def build_features(
    df,
    original_target,
    group_col,
    date_col,
    task,
    prediction_mode,
):
    work = df.copy()

    if date_col and date_col in work.columns:
        dates = pd.to_datetime(
            work[date_col],
            errors="coerce",
            utc=True,
        )

        work["__date_year"] = dates.dt.year
        work["__date_month"] = dates.dt.month
        work["__date_dayofyear"] = dates.dt.dayofyear

    candidates = []

    for c in work.columns:
        lc = c.lower()

        if c in {
            "__ml_target",
            group_col,
            date_col,
            "__parsed_date",
        }:
            continue

        if c == original_target:
            if prediction_mode == "next_observation":
                candidates.append(c)
            continue

        # IDs / names / geometries must not become memorisation features.
        if any(
            token in lc
            for token in [
                "asset_id",
                "asset_code",
                "bridge_id",
                "dam_id",
                "structure_id",
                "structure_number",
                "external_id",
                "uuid",
                "geometry",
                "longitude",
                "latitude",
                "model_uri",
                "image_uri",
                "url",
                "checksum",
            ]
        ):
            continue

        # Never train on prediction outputs.
        if any(
            token in lc
            for token in [
                "predicted_",
                "prediction_",
                "model_output",
                "ai_score",
                "ai_prediction",
            ]
        ):
            continue

        # Explicit labels/outcomes are not features.
        if any(
            token in lc
            for token in [
                "_target",
                "target_",
                "_label",
                "label_",
                "ground_truth",
                "outcome",
            ]
        ):
            continue

        if task == "health" and prediction_mode == "cross_sectional":
            # Prevent health/condition target leakage.
            if any(
                token in lc
                for token in [
                    "health",
                    "condition_score",
                    "overall_condition",
                    "condition_rating",
                    "final_rating",
                ]
            ):
                continue

        if task == "risk":
            if any(
                token in lc
                for token in [
                    "risk_target",
                    "risk_label",
                    "predicted_risk",
                ]
            ):
                continue

        candidates.append(c)

    # Remove very high-cardinality string columns.
    final_cols = []

    for c in candidates:
        s = work[c]

        if s.dtype == "object" or str(s.dtype).startswith("string"):
            nunique = s.nunique(dropna=True)

            if nunique > max(250, int(len(work) * 0.40)):
                continue

        final_cols.append(c)

    X = work[final_cols].copy()

    # Useful missingness evidence.
    X["__missing_feature_count"] = X.isna().sum(axis=1)

    return X, final_cols + ["__missing_feature_count"]


def make_preprocessor(X):
    numeric_cols = [
        c
        for c in X.columns
        if pd.api.types.is_numeric_dtype(X[c])
    ]

    categorical_cols = [
        c
        for c in X.columns
        if c not in numeric_cols
    ]

    numeric_pipe = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
        ]
    )

    try:
        encoder = OneHotEncoder(
            handle_unknown="ignore",
            min_frequency=2,
            sparse_output=True,
        )
    except TypeError:
        encoder = OneHotEncoder(
            handle_unknown="ignore",
            sparse=True,
        )

    categorical_pipe = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            ),
            (
                "onehot",
                encoder,
            ),
        ]
    )

    return ColumnTransformer(
        transformers=[
            (
                "num",
                numeric_pipe,
                numeric_cols,
            ),
            (
                "cat",
                categorical_pipe,
                categorical_cols,
            ),
        ],
        remainder="drop",
    )


# =============================================================================
# GROUP / ASSET-SAFE SPLIT
# =============================================================================

def split_indices(df, group_col, y, classification):
    if group_col and group_col in df.columns:
        groups = (
            df[group_col]
            .astype(str)
            .fillna("__missing_asset")
        )
        genuine_group = True
    else:
        groups = pd.Series(
            [f"ROW_{i}" for i in range(len(df))],
            index=df.index,
        )
        genuine_group = False

    unique_groups = groups.nunique()

    for seed in range(42, 82):
        try:
            first = GroupShuffleSplit(
                n_splits=1,
                train_size=0.70,
                random_state=seed,
            )

            train_idx, temp_idx = next(
                first.split(df, y, groups)
            )

            temp_groups = groups.iloc[temp_idx]

            second = GroupShuffleSplit(
                n_splits=1,
                train_size=0.50,
                random_state=seed + 1000,
            )

            val_rel, test_rel = next(
                second.split(
                    df.iloc[temp_idx],
                    y.iloc[temp_idx],
                    temp_groups,
                )
            )

            val_idx = temp_idx[val_rel]
            test_idx = temp_idx[test_rel]

            if classification:
                if (
                    len(np.unique(y.iloc[train_idx])) < 2
                    or len(np.unique(y.iloc[val_idx])) < 2
                    or len(np.unique(y.iloc[test_idx])) < 2
                ):
                    continue

            train_groups = set(groups.iloc[train_idx])
            val_groups = set(groups.iloc[val_idx])
            test_groups = set(groups.iloc[test_idx])

            leakage = {
                "train_val_overlap": len(train_groups & val_groups),
                "train_test_overlap": len(train_groups & test_groups),
                "val_test_overlap": len(val_groups & test_groups),
            }

            return (
                train_idx,
                val_idx,
                test_idx,
                {
                    "genuine_asset_group": genuine_group,
                    "unique_groups": int(unique_groups),
                    "leakage": leakage,
                    "seed": seed,
                },
            )

        except Exception:
            continue

    raise RuntimeError(
        "Unable to create class-valid asset-separated train/validation/test split"
    )


# =============================================================================
# METRICS
# =============================================================================

def ece_score(y_true, prob, bins=10):
    y_true = np.asarray(y_true)
    prob = np.asarray(prob)

    edges = np.linspace(0, 1, bins + 1)
    total = len(y_true)
    ece = 0.0

    for i in range(bins):
        if i == bins - 1:
            mask = (
                (prob >= edges[i])
                & (prob <= edges[i + 1])
            )
        else:
            mask = (
                (prob >= edges[i])
                & (prob < edges[i + 1])
            )

        n = int(mask.sum())

        if not n:
            continue

        confidence = float(prob[mask].mean())
        actual = float(y_true[mask].mean())

        ece += (n / total) * abs(confidence - actual)

    return float(ece)


def regression_metrics(y_true, pred):
    y_true = np.asarray(y_true, dtype=float)
    pred = np.asarray(pred, dtype=float)

    mae = float(mean_absolute_error(y_true, pred))
    rmse = float(math.sqrt(mean_squared_error(y_true, pred)))
    r2 = float(r2_score(y_true, pred))

    target_range = float(np.nanmax(y_true) - np.nanmin(y_true))

    if target_range <= 0:
        normalized_mae = float("inf")
        agreement = 0.0
    else:
        normalized_mae = mae / target_range
        tolerance = 0.05 * target_range
        agreement = float(
            np.mean(np.abs(y_true - pred) <= tolerance)
        )

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "target_range": target_range,
        "normalized_mae": normalized_mae,
        "agreement_within_5pct_of_target_range": agreement,
    }


def classification_metrics(y_true, prob):
    y_true = np.asarray(y_true, dtype=int)
    prob = np.clip(np.asarray(prob, dtype=float), 0, 1)

    pred = (prob >= 0.50).astype(int)

    metrics = {
        "accuracy": float(accuracy_score(y_true, pred)),
        "balanced_accuracy": float(
            balanced_accuracy_score(y_true, pred)
        ),
        "recall": float(
            recall_score(y_true, pred, zero_division=0)
        ),
        "precision": float(
            precision_score(y_true, pred, zero_division=0)
        ),
        "f1": float(
            f1_score(y_true, pred, zero_division=0)
        ),
        "brier": float(
            brier_score_loss(y_true, prob)
        ),
        "ece": ece_score(y_true, prob),
        "prevalence": float(np.mean(y_true)),
    }

    try:
        metrics["roc_auc"] = float(
            roc_auc_score(y_true, prob)
        )
    except Exception:
        metrics["roc_auc"] = None

    try:
        metrics["pr_auc"] = float(
            average_precision_score(y_true, prob)
        )
    except Exception:
        metrics["pr_auc"] = None

    return metrics


# =============================================================================
# MODEL DEFINITIONS
# =============================================================================

def regression_candidates():
    models = [
        (
            "RF",
            "rf_v1",
            RandomForestRegressor(
                n_estimators=700,
                max_features=0.80,
                min_samples_leaf=1,
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "RF",
            "rf_v2",
            RandomForestRegressor(
                n_estimators=900,
                max_features="sqrt",
                min_samples_leaf=2,
                random_state=52,
                n_jobs=-1,
            ),
        ),
    ]

    if HAVE_XGB:
        models += [
            (
                "XGBOOST",
                "xgb_v1",
                XGBRegressor(
                    n_estimators=700,
                    max_depth=5,
                    learning_rate=0.035,
                    subsample=0.90,
                    colsample_bytree=0.90,
                    reg_lambda=2.0,
                    objective="reg:squarederror",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
            (
                "XGBOOST",
                "xgb_v2",
                XGBRegressor(
                    n_estimators=900,
                    max_depth=4,
                    learning_rate=0.025,
                    subsample=0.85,
                    colsample_bytree=0.90,
                    reg_lambda=4.0,
                    min_child_weight=3,
                    objective="reg:squarederror",
                    random_state=52,
                    n_jobs=-1,
                ),
            ),
        ]

    if HAVE_LGBM:
        models += [
            (
                "LIGHTGBM",
                "lgbm_v1",
                LGBMRegressor(
                    n_estimators=700,
                    learning_rate=0.035,
                    num_leaves=31,
                    max_depth=-1,
                    subsample=0.90,
                    colsample_bytree=0.90,
                    reg_lambda=2.0,
                    random_state=42,
                    n_jobs=-1,
                    verbosity=-1,
                ),
            ),
            (
                "LIGHTGBM",
                "lgbm_v2",
                LGBMRegressor(
                    n_estimators=900,
                    learning_rate=0.025,
                    num_leaves=24,
                    min_child_samples=25,
                    subsample=0.85,
                    colsample_bytree=0.90,
                    reg_lambda=4.0,
                    random_state=52,
                    n_jobs=-1,
                    verbosity=-1,
                ),
            ),
        ]

    return models


def classification_candidates(positive_ratio):
    ratio = max(
        (1.0 - positive_ratio) / max(positive_ratio, 1e-5),
        1.0,
    )

    models = [
        (
            "RF",
            "rf_v1",
            RandomForestClassifier(
                n_estimators=800,
                max_features=0.80,
                min_samples_leaf=1,
                class_weight="balanced",
                random_state=42,
                n_jobs=-1,
            ),
        ),
        (
            "RF",
            "rf_v2",
            RandomForestClassifier(
                n_estimators=1000,
                max_features="sqrt",
                min_samples_leaf=2,
                class_weight="balanced_subsample",
                random_state=52,
                n_jobs=-1,
            ),
        ),
    ]

    if HAVE_XGB:
        models += [
            (
                "XGBOOST",
                "xgb_v1",
                XGBClassifier(
                    n_estimators=800,
                    max_depth=5,
                    learning_rate=0.03,
                    subsample=0.90,
                    colsample_bytree=0.90,
                    reg_lambda=3.0,
                    scale_pos_weight=ratio,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
            (
                "XGBOOST",
                "xgb_v2",
                XGBClassifier(
                    n_estimators=1000,
                    max_depth=4,
                    learning_rate=0.02,
                    subsample=0.85,
                    colsample_bytree=0.90,
                    min_child_weight=3,
                    reg_lambda=5.0,
                    scale_pos_weight=ratio,
                    objective="binary:logistic",
                    eval_metric="logloss",
                    random_state=52,
                    n_jobs=-1,
                ),
            ),
        ]

    if HAVE_LGBM:
        models += [
            (
                "LIGHTGBM",
                "lgbm_v1",
                LGBMClassifier(
                    n_estimators=800,
                    learning_rate=0.03,
                    num_leaves=31,
                    class_weight="balanced",
                    subsample=0.90,
                    colsample_bytree=0.90,
                    reg_lambda=3.0,
                    random_state=42,
                    n_jobs=-1,
                    verbosity=-1,
                ),
            ),
            (
                "LIGHTGBM",
                "lgbm_v2",
                LGBMClassifier(
                    n_estimators=1000,
                    learning_rate=0.02,
                    num_leaves=24,
                    min_child_samples=25,
                    class_weight="balanced",
                    subsample=0.85,
                    colsample_bytree=0.90,
                    reg_lambda=5.0,
                    random_state=52,
                    n_jobs=-1,
                    verbosity=-1,
                ),
            ),
        ]

    return models


# =============================================================================
# CALIBRATION
# =============================================================================

def fit_calibrator(y_val, raw_prob):
    y_val = np.asarray(y_val, dtype=int)
    raw_prob = np.clip(np.asarray(raw_prob, dtype=float), 1e-6, 1 - 1e-6)

    positives = int(y_val.sum())
    negatives = int(len(y_val) - positives)

    if positives >= 20 and negatives >= 20:
        calibrator = IsotonicRegression(
            out_of_bounds="clip"
        )
        calibrator.fit(raw_prob, y_val)
        return "isotonic", calibrator

    calibrator = LogisticRegression(
        max_iter=1000
    )
    calibrator.fit(
        raw_prob.reshape(-1, 1),
        y_val,
    )

    return "platt", calibrator


def calibrated_probability(kind, calibrator, raw_prob):
    raw_prob = np.clip(
        np.asarray(raw_prob, dtype=float),
        1e-6,
        1 - 1e-6,
    )

    if kind == "isotonic":
        return calibrator.predict(raw_prob)

    return calibrator.predict_proba(
        raw_prob.reshape(-1, 1)
    )[:, 1]


# =============================================================================
# ASSET CLASS DETECTION
# =============================================================================

def infer_asset_class(path, df):
    type_col = first_col(df, TYPE_COLS)

    classes = {}

    if type_col:
        values = (
            df[type_col]
            .astype(str)
            .str.lower()
        )

        bridge_mask = values.str.contains(
            "bridge|flyover|viaduct",
            regex=True,
            na=False,
        )

        dam_mask = values.str.contains(
            "dam|barrage|reservoir",
            regex=True,
            na=False,
        )

        if int(bridge_mask.sum()) >= MIN_ROWS:
            classes["bridge"] = df.loc[bridge_mask].copy()

        if int(dam_mask.sum()) >= MIN_ROWS:
            classes["dam"] = df.loc[dam_mask].copy()

    if classes:
        return classes

    name = str(path).lower()

    if "bridge" in name or "nbi" in name:
        return {"bridge": df.copy()}

    if (
        "dam" in name
        or "barrage" in name
        or "reservoir" in name
    ):
        return {"dam": df.copy()}

    return {"general": df.copy()}


# =============================================================================
# TRAIN ONE TASK
# =============================================================================

leaderboard = []
predicted_vs_actual = []
calibration_reports = []
algorithm_reports = {
    "RF": [],
    "XGBOOST": [],
    "LIGHTGBM": [],
}

trained_results = []


def train_task(
    source_path,
    original_df,
    asset_class,
    task,
    target_col,
):
    log("")
    log(
        f"TRAINING {asset_class.upper()} / {task.upper()} "
        f"FROM {source_path}"
    )
    log("-" * 100)

    df = original_df.copy()

    synth = synthetic_mask(df)
    synthetic_removed = int(synth.sum())

    if synthetic_removed:
        df = df.loc[~synth].copy()

    df = df.drop_duplicates().copy()

    group_col = first_col(df, GROUP_COLS)
    date_col = first_col(df, DATE_COLS)

    df, prediction_mode = maybe_future_target(
        df,
        target_col,
        group_col,
        date_col,
    )

    df = df.loc[
        df["__ml_target"].notna()
    ].copy()

    if len(df) < MIN_ROWS:
        log(
            f"SKIP: only {len(df)} usable rows; "
            f"minimum={MIN_ROWS}"
        )
        return None

    provenance = provenance_status(
        source_path,
        df,
    )

    if task == "health":
        y = pd.to_numeric(
            df["__ml_target"],
            errors="coerce",
        )

        valid = y.notna()
        df = df.loc[valid].copy()
        y = y.loc[valid].astype(float)

        if y.nunique() < 5:
            log("SKIP: health target has insufficient numeric variation")
            return None

        classification = False
        target_mapping = None

    else:
        y, target_mapping = binary_target(
            df["__ml_target"]
        )

        if y is None:
            log(
                f"SKIP: risk target is not a defensible binary/high-risk label: "
                f"{target_mapping}"
            )
            return None

        valid = y.notna()
        df = df.loc[valid].copy()
        y = y.loc[valid].astype(int)

        if y.nunique() != 2:
            log("SKIP: risk target does not contain two classes")
            return None

        classification = True

    X, feature_cols = build_features(
        df,
        original_target=target_col,
        group_col=group_col,
        date_col=date_col,
        task=task,
        prediction_mode=prediction_mode,
    )

    if len(feature_cols) < 3:
        log("SKIP: fewer than 3 safe non-leaky features")
        return None

    (
        train_idx,
        val_idx,
        test_idx,
        split_report,
    ) = split_indices(
        df,
        group_col,
        y,
        classification,
    )

    X_train = X.iloc[train_idx]
    X_val = X.iloc[val_idx]
    X_test = X.iloc[test_idx]

    y_train = y.iloc[train_idx]
    y_val = y.iloc[val_idx]
    y_test = y.iloc[test_idx]

    log(
        f"Rows: train={len(train_idx):,}, "
        f"validation={len(val_idx):,}, "
        f"locked_test={len(test_idx):,}"
    )

    log(
        f"Groups={split_report['unique_groups']:,} | "
        f"asset-group available={split_report['genuine_asset_group']}"
    )

    log(
        f"Leakage: {split_report['leakage']}"
    )

    log(
        f"Prediction mode: {prediction_mode}"
    )

    log(
        f"Provenance: {provenance}"
    )

    if classification:
        candidates = classification_candidates(
            float(y_train.mean())
        )
    else:
        candidates = regression_candidates()

    preprocessor = make_preprocessor(
        X_train
    )

    fitted = []

    for algorithm, variant, estimator in candidates:
        log(
            f"  Training {algorithm} / {variant} ..."
        )

        pipe = Pipeline(
            steps=[
                (
                    "preprocess",
                    clone(preprocessor),
                ),
                (
                    "model",
                    estimator,
                ),
            ]
        )

        try:
            pipe.fit(
                X_train,
                y_train,
            )

            if classification:
                val_prob = pipe.predict_proba(
                    X_val
                )[:, 1]

                metrics = classification_metrics(
                    y_val,
                    val_prob,
                )

                roc = metrics.get("roc_auc")
                roc = roc if roc is not None else 0

                selection_score = (
                    0.50 * roc
                    + 0.30 * metrics["balanced_accuracy"]
                    + 0.20 * metrics["recall"]
                )

            else:
                val_pred = pipe.predict(
                    X_val
                )

                metrics = regression_metrics(
                    y_val,
                    val_pred,
                )

                selection_score = (
                    metrics["r2"]
                    - metrics["normalized_mae"]
                )

            entry = {
                "asset_class": asset_class,
                "task": task,
                "algorithm": algorithm,
                "variant": variant,
                "validation_metrics": metrics,
                "selection_score": float(selection_score),
            }

            algorithm_reports[algorithm].append(
                entry
            )

            fitted.append(
                (
                    selection_score,
                    algorithm,
                    variant,
                    pipe,
                    metrics,
                )
            )

            log(
                f"    validation={metrics}"
            )

        except Exception as exc:
            log(
                f"    FAILED: {exc}"
            )

    if not fitted:
        log("SKIP: all model candidates failed")
        return None

    fitted.sort(
        key=lambda x: x[0],
        reverse=True,
    )

    (
        _,
        winner_algorithm,
        winner_variant,
        winner_model,
        validation_metrics,
    ) = fitted[0]

    calibration_kind = None
    calibrator = None

    if classification:
        raw_val = winner_model.predict_proba(
            X_val
        )[:, 1]

        calibration_kind, calibrator = fit_calibrator(
            y_val,
            raw_val,
        )

        raw_test = winner_model.predict_proba(
            X_test
        )[:, 1]

        test_prob = calibrated_probability(
            calibration_kind,
            calibrator,
            raw_test,
        )

        test_metrics = classification_metrics(
            y_test,
            test_prob,
        )

        gates = {
            "accuracy_ge_0_97":
                test_metrics["accuracy"] >= RISK_GATES["accuracy"],

            "balanced_accuracy_ge_0_95":
                test_metrics["balanced_accuracy"]
                >= RISK_GATES["balanced_accuracy"],

            "roc_auc_ge_0_97":
                (
                    test_metrics["roc_auc"] is not None
                    and test_metrics["roc_auc"]
                    >= RISK_GATES["roc_auc"]
                ),

            "high_risk_recall_ge_0_95":
                test_metrics["recall"]
                >= RISK_GATES["recall"],

            "brier_le_0_08":
                test_metrics["brier"]
                <= RISK_GATES["brier_max"],

            "ece_le_0_03":
                test_metrics["ece"]
                <= RISK_GATES["ece_max"],

            "enough_positive_test_events":
                int(y_test.sum()) >= MIN_CLASS_EVENTS,
        }

        test_predictions = test_prob

        calibration_reports.append({
            "asset_class": asset_class,
            "task": task,
            "method": calibration_kind,
            "metrics": test_metrics,
        })

    else:
        test_pred = winner_model.predict(
            X_test
        )

        test_metrics = regression_metrics(
            y_test,
            test_pred,
        )

        gates = {
            "r2_ge_0_95":
                test_metrics["r2"] >= HEALTH_GATES["r2"],

            "normalized_mae_le_0_03":
                test_metrics["normalized_mae"]
                <= HEALTH_GATES["normalized_mae_max"],

            "agreement_within_5pct_ge_0_97":
                test_metrics[
                    "agreement_within_5pct_of_target_range"
                ]
                >= HEALTH_GATES["agreement_within_5pct"],
        }

        test_predictions = test_pred

    gates["zero_asset_leakage"] = (
        split_report["leakage"]["train_val_overlap"] == 0
        and split_report["leakage"]["train_test_overlap"] == 0
        and split_report["leakage"]["val_test_overlap"] == 0
    )

    gates["asset_group_identity_available"] = (
        split_report["genuine_asset_group"]
    )

    gates["minimum_group_count"] = (
        split_report["unique_groups"] >= MIN_GROUPS
    )

    gates["minimum_locked_test_rows"] = (
        len(test_idx) >= MIN_TEST_ROWS
    )

    quality_pass = all(
        bool(v)
        for v in gates.values()
    )

    local_provenance = (
        provenance
        == "LOCAL_GROUND_TRUTH_CANDIDATE"
    )

    # Passing an external real dataset proves transfer performance,
    # NOT AP-specific production accuracy.
    if quality_pass and local_provenance:
        stage = "PRODUCTION_ELIGIBLE"
    elif quality_pass:
        stage = "RESEARCH_TRANSFER_VALIDATED"
    else:
        stage = "RESEARCH_ONLY"

    model_name = (
        f"simras_{asset_class}_{task}_{winner_algorithm.lower()}_{RUN_ID}"
    )

    artifact_path = (
        CANDIDATE_DIR
        / f"{model_name}.joblib"
    )

    package = {
        "model": winner_model,
        "calibrator": calibrator,
        "calibration_kind": calibration_kind,
        "asset_class": asset_class,
        "task": task,
        "target_column": target_col,
        "target_mapping": target_mapping,
        "feature_columns": list(X.columns),
        "prediction_mode": prediction_mode,
        "provenance": provenance,
        "validation_metrics": validation_metrics,
        "locked_test_metrics": test_metrics,
        "quality_gates": gates,
        "stage": stage,
        "created_at": datetime.now(
            timezone.utc
        ).isoformat(),
    }

    joblib.dump(
        package,
        artifact_path,
    )

    # Real-vs-predicted report.
    for position, row_idx in enumerate(test_idx):
        original_index = df.iloc[row_idx].name

        if group_col:
            asset_id = str(
                df.iloc[row_idx][group_col]
            )
        else:
            asset_id = f"ROW_{original_index}"

        actual = float(
            y.iloc[row_idx]
        )

        predicted = float(
            test_predictions[position]
        )

        predicted_vs_actual.append({
            "asset_class": asset_class,
            "task": task,
            "asset_id": asset_id,
            "actual": actual,
            "predicted": predicted,
            "absolute_error": abs(actual - predicted),
            "model": model_name,
            "source_dataset": str(source_path),
        })

    leader = {
        "asset_class": asset_class,
        "task": task,
        "winner_algorithm": winner_algorithm,
        "winner_variant": winner_variant,
        "rows": int(len(df)),
        "groups": int(split_report["unique_groups"]),
        "prediction_mode": prediction_mode,
        "provenance": provenance,
        "synthetic_rows_removed": synthetic_removed,
        "locked_test_metrics": test_metrics,
        "quality_gates": gates,
        "quality_pass": quality_pass,
        "stage": stage,
        "artifact": str(artifact_path),
        "dataset": str(source_path),
    }

    leaderboard.append(
        leader
    )

    log("")
    log(
        f"WINNER: {winner_algorithm} / {winner_variant}"
    )

    log(
        f"LOCKED TEST: {test_metrics}"
    )

    log(
        f"GATES: {gates}"
    )

    log(
        f"STAGE: {stage}"
    )

    trained_results.append(
        leader
    )

    return leader


# =============================================================================
# SELECT DATASETS AND TRAIN
# =============================================================================

reality_report = {
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "dataset_inventory": dataset_inventory,
    "current_database_prediction_state": db_state,
    "rules": {
        "synthetic_demo_rows_removed": True,
        "asset_group_split_required_for_production": True,
        "locked_test_set": True,
        "unsupported_rul_not_trained": True,
        "classification_accuracy_target": 0.97,
        "health_regression_not_reported_as_fake_accuracy": True,
    },
}

dump_json(
    RUN_DIR / "01_DATASET_REALITY_REPORT.json",
    reality_report,
)

if not dataset_inventory:
    log("")
    log("NO QUALIFIED TRAINING DATASET FOUND.")
    log(
        "No model will be fabricated or promoted."
    )

else:
    # Use the strongest datasets first.
    # Avoid repeatedly training identical path/class/task combinations.
    trained_keys = set()

    for inventory in dataset_inventory[:10]:
        source_path = Path(
            inventory["path"]
        )

        raw = read_dataset(
            source_path
        )

        if raw is None:
            continue

        raw = normalize_columns(
            raw
        )

        for asset_class, subset in infer_asset_class(
            source_path,
            raw,
        ).items():

            if len(subset) < MIN_ROWS:
                continue

            health_target = first_col(
                subset,
                HEALTH_TARGETS,
            )

            risk_target = first_col(
                subset,
                RISK_TARGETS,
            )

            if health_target:
                key = (
                    asset_class,
                    "health",
                )

                if key not in trained_keys:
                    result = train_task(
                        source_path,
                        subset,
                        asset_class,
                        "health",
                        health_target,
                    )

                    if result:
                        trained_keys.add(
                            key
                        )

            if risk_target:
                key = (
                    asset_class,
                    "risk",
                )

                if key not in trained_keys:
                    result = train_task(
                        source_path,
                        subset,
                        asset_class,
                        "risk",
                        risk_target,
                    )

                    if result:
                        trained_keys.add(
                            key
                        )

            # Stop after bridge and dam have both tasks when possible.
            required = {
                ("bridge", "health"),
                ("bridge", "risk"),
                ("dam", "health"),
                ("dam", "risk"),
            }

            if required.issubset(
                trained_keys
            ):
                break


# =============================================================================
# REPORT GENERATION
# =============================================================================

log("")
log("=" * 100)
log("GENERATING ML REPORT PACK")
log("=" * 100)

# 02 Data quality
quality_report = {
    "datasets_considered": len(
        dataset_inventory
    ),
    "models_trained": len(
        trained_results
    ),
    "trained_results": trained_results,
    "xgboost_available": HAVE_XGB,
    "lightgbm_available": HAVE_LGBM,
}

dump_json(
    RUN_DIR / "02_DATA_QUALITY_REPORT.json",
    quality_report,
)

# 03 Leakage
leakage_report = {
    "models": [
        {
            "asset_class": x["asset_class"],
            "task": x["task"],
            "zero_asset_leakage":
                x["quality_gates"].get(
                    "zero_asset_leakage"
                ),
            "asset_group_identity_available":
                x["quality_gates"].get(
                    "asset_group_identity_available"
                ),
            "groups": x["groups"],
        }
        for x in trained_results
    ]
}

dump_json(
    RUN_DIR / "03_SPLIT_LEAKAGE_REPORT.json",
    leakage_report,
)

# Algorithm evaluations
dump_json(
    RUN_DIR / "04_RF_EVALUATION.json",
    algorithm_reports["RF"],
)

dump_json(
    RUN_DIR / "05_XGBOOST_EVALUATION.json",
    algorithm_reports["XGBOOST"],
)

dump_json(
    RUN_DIR / "06_LIGHTGBM_EVALUATION.json",
    algorithm_reports["LIGHTGBM"],
)

# Leaderboard CSV
leader_rows = []

for x in leaderboard:
    row = {
        "asset_class": x["asset_class"],
        "task": x["task"],
        "winner_algorithm": x["winner_algorithm"],
        "winner_variant": x["winner_variant"],
        "rows": x["rows"],
        "groups": x["groups"],
        "prediction_mode": x["prediction_mode"],
        "provenance": x["provenance"],
        "quality_pass": x["quality_pass"],
        "stage": x["stage"],
    }

    for k, v in x[
        "locked_test_metrics"
    ].items():
        row[f"test_{k}"] = v

    leader_rows.append(
        row
    )

pd.DataFrame(
    leader_rows
).to_csv(
    RUN_DIR / "07_MODEL_LEADERBOARD.csv",
    index=False,
)

# Calibration
dump_json(
    RUN_DIR / "08_CALIBRATION_REPORT.json",
    calibration_reports,
)

# Predicted vs Actual
pva = pd.DataFrame(
    predicted_vs_actual
)

pva.to_csv(
    RUN_DIR / "09_PREDICTED_VS_ACTUAL.csv",
    index=False,
)

if not pva.empty:
    error_analysis = (
        pva.sort_values(
            "absolute_error",
            ascending=False,
        )
    )
else:
    error_analysis = pva

error_analysis.to_csv(
    RUN_DIR / "10_ERROR_ANALYSIS.csv",
    index=False,
)


# =============================================================================
# ASSET REPORTS
# =============================================================================

def asset_report(asset_class):
    items = [
        x
        for x in leaderboard
        if x["asset_class"] == asset_class
    ]

    lines = [
        f"# SIMRAS {asset_class.title()} ML Validation Report",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
    ]

    if not items:
        lines += [
            "## Result",
            "",
            "No defensible training dataset/model was available for this asset class.",
            "",
            "The system must ABSTAIN rather than reuse another infrastructure class's model.",
        ]

        return "\n".join(
            lines
        )

    for x in items:
        lines += [
            f"## {x['task'].title()} model",
            "",
            f"- Winner: **{x['winner_algorithm']} / {x['winner_variant']}**",
            f"- Dataset: `{x['dataset']}`",
            f"- Rows: {x['rows']}",
            f"- Asset groups: {x['groups']}",
            f"- Prediction mode: {x['prediction_mode']}",
            f"- Provenance: {x['provenance']}",
            f"- Stage: **{x['stage']}**",
            f"- Quality gates passed: **{x['quality_pass']}**",
            "",
            "### Locked test metrics",
            "",
            "```json",
            json.dumps(
                x["locked_test_metrics"],
                indent=2,
            ),
            "```",
            "",
            "### Gates",
            "",
            "```json",
            json.dumps(
                x["quality_gates"],
                indent=2,
            ),
            "```",
            "",
        ]

    return "\n".join(
        lines
    )


(
    RUN_DIR
    / "11_BRIDGE_MODEL_REPORT.md"
).write_text(
    asset_report("bridge"),
    encoding="utf-8",
)

(
    RUN_DIR
    / "12_DAM_MODEL_REPORT.md"
).write_text(
    asset_report("dam"),
    encoding="utf-8",
)


# =============================================================================
# SAFE PROMOTION
# =============================================================================

promotion_manifest = {
    "run_id": RUN_ID,
    "generated_at": datetime.now(
        timezone.utc
    ).isoformat(),
    "promoted": [],
    "validated_transfer_models": [],
    "rejected": [],
    "rule": (
        "A model is promoted only when locked-test quality gates pass "
        "AND local ground-truth provenance is present."
    ),
}

for item in leaderboard:
    if item["stage"] == "PRODUCTION_ELIGIBLE":
        source = Path(
            item["artifact"]
        )

        destination = (
            PRODUCTION_DIR
            / source.name
        )

        shutil.copy2(
            source,
            destination,
        )

        promotion_manifest[
            "promoted"
        ].append({
            **item,
            "production_artifact":
                str(destination),
        })

    elif (
        item["stage"]
        == "RESEARCH_TRANSFER_VALIDATED"
    ):
        promotion_manifest[
            "validated_transfer_models"
        ].append(
            item
        )

    else:
        promotion_manifest[
            "rejected"
        ].append(
            item
        )

dump_json(
    RUN_DIR
    / "13_PRODUCTION_MODEL_MANIFEST.json",
    promotion_manifest,
)

# Stable current pointer only when legitimately production eligible.
if promotion_manifest["promoted"]:
    dump_json(
        PRODUCTION_DIR
        / "current.json",
        promotion_manifest,
    )


# =============================================================================
# FINAL REPORT
# =============================================================================

production_count = len(
    promotion_manifest["promoted"]
)

transfer_count = len(
    promotion_manifest[
        "validated_transfer_models"
    ]
)

rejected_count = len(
    promotion_manifest["rejected"]
)

if production_count:
    final_verdict = (
        "PASS — at least one model passed the locked-test gates "
        "and has local ground-truth provenance."
    )

elif transfer_count:
    final_verdict = (
        "TRANSFER VALIDATED — quality gates passed on a real external dataset, "
        "but Andhra Pradesh ground-truth validation is still required "
        "before claiming AP production accuracy."
    )

elif trained_results:
    final_verdict = (
        "NOT PRODUCTION READY — models were trained and tested, "
        "but one or more strict quality/provenance gates failed."
    )

else:
    final_verdict = (
        "NO DEFENSIBLE MODEL — no suitable real labelled dataset was available."
    )

final_lines = [
    "# SIMRAS FINAL ML VALIDATION REPORT",
    "",
    f"Run ID: `{RUN_ID}`",
    "",
    "## Final verdict",
    "",
    f"**{final_verdict}**",
    "",
    "## Required interpretation",
    "",
    "- The script does not manufacture a 97-98% score.",
    "- Risk uses a locked asset-separated test set.",
    "- 97% risk accuracy alone is insufficient; balanced accuracy, ROC-AUC, recall, Brier score and ECE must also pass.",
    "- Health is regression and is evaluated with MAE, RMSE, R² and predicted-vs-actual agreement.",
    "- Asset overlap between training and test must be zero.",
    "- Synthetic/demo rows are removed when explicitly marked.",
    "- Unsupported RUL is not trained or promoted.",
    "- A transfer model is not labelled as Andhra Pradesh production accuracy.",
    "",
    "## Promotion summary",
    "",
    f"- Production eligible: {production_count}",
    f"- Validated transfer models: {transfer_count}",
    f"- Rejected/research only: {rejected_count}",
    "",
    "## Model results",
    "",
]

for x in leaderboard:
    final_lines += [
        f"### {x['asset_class']} / {x['task']}",
        "",
        f"- Winner: {x['winner_algorithm']} / {x['winner_variant']}",
        f"- Stage: {x['stage']}",
        f"- Provenance: {x['provenance']}",
        f"- Quality pass: {x['quality_pass']}",
        f"- Test metrics: `{json.dumps(x['locked_test_metrics'], default=str)}`",
        "",
    ]

if db_state.get("predictions"):
    final_lines += [
        "## Existing database prediction state",
        "",
        "The following predictions existed before this rebuild:",
        "",
        "```json",
        json.dumps(
            db_state["predictions"],
            indent=2,
        ),
        "```",
        "",
        "Existing experimental RUL rows are not used as ground-truth labels.",
        "",
    ]

final_lines += [
    "## Real-vs-predicted evidence",
    "",
    "See:",
    "",
    "`09_PREDICTED_VS_ACTUAL.csv`",
    "",
    "and:",
    "",
    "`10_ERROR_ANALYSIS.csv`",
    "",
    "These files are the primary evidence for whether model outputs match held-out real-world labels.",
]

final_report_path = (
    RUN_DIR
    / "14_FINAL_ML_VALIDATION_REPORT.md"
)

final_report_path.write_text(
    "\n".join(final_lines),
    encoding="utf-8",
)

# Save console log
(
    RUN_DIR
    / "SIMRAS_ML_REBUILD_CONSOLE.txt"
).write_text(
    "\n".join(log_lines),
    encoding="utf-8",
)

# Copy run reports to latest
for p in RUN_DIR.iterdir():
    if p.is_file():
        shutil.copy2(
            p,
            LATEST_DIR / p.name,
        )

log("")
log("=" * 100)
log("SIMRAS ML REBUILD COMPLETE")
log("=" * 100)
log(f"FINAL VERDICT: {final_verdict}")
log("")
log(f"Production eligible models : {production_count}")
log(f"Validated transfer models  : {transfer_count}")
log(f"Rejected/research models   : {rejected_count}")
log("")
log("REPORTS:")
log(
    "/workspace/backend/reports/ml/latest/"
)
log("")
log(
    "OPEN FIRST:"
)
log(
    "backend/reports/ml/latest/14_FINAL_ML_VALIDATION_REPORT.md"
)
log("")
log(
    "REAL VS PREDICTED:"
)
log(
    "backend/reports/ml/latest/09_PREDICTED_VS_ACTUAL.csv"
)
log("")
log(
    "MODEL LEADERBOARD:"
)
log(
    "backend/reports/ml/latest/07_MODEL_LEADERBOARD.csv"
)
log("=" * 100)
