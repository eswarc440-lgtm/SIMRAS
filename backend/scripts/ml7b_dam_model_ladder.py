import json
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    ExtraTreesClassifier,
    ExtraTreesRegressor,
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    mean_absolute_error,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# CONFIG
# ============================================================

NOW = datetime.now(timezone.utc)
STAMP = NOW.strftime("%Y%m%d_%H%M%S")

ROOT = Path("/app/data/ml/dam_barrage")
OUT = ROOT / f"ml7b_model_ladder_{STAMP}"
MODEL_DIR = OUT / "models"

OUT.mkdir(parents=True, exist_ok=True)
MODEL_DIR.mkdir(parents=True, exist_ok=True)

NID_URL = (
    "https://geospatial.sec.usace.army.mil/"
    "dls/rest/services/NID/"
    "National_Inventory_of_Dams_Public_Service/"
    "FeatureServer/0/query"
)

RANDOM_STATE = 440


# ============================================================
# HELPERS
# ============================================================

def condition_class(value):

    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    if "UNSATISFACTORY" in value:
        return "UNSATISFACTORY"

    if "POOR" in value:
        return "POOR"

    if "FAIR" in value:
        return "FAIR"

    if "SATISFACTORY" in value:
        return "SATISFACTORY"

    return None


def coarse_type(value):

    value = str(value or "").upper()

    if (
        "EARTH" in value
        or "EMBANKMENT" in value
        or value in {"ER", "RE"}
    ):
        return "EARTH"

    if (
        "GRAVITY" in value
        or "MASONRY" in value
        or "CONCRETE" in value
        or value in {"PG", "CB"}
    ):
        return "GRAVITY"

    if (
        "ROCK" in value
        or value == "RF"
    ):
        return "ROCKFILL"

    if "ARCH" in value:
        return "ARCH"

    if "BUTTRESS" in value:
        return "BUTTRESS"

    return "OTHER"


def coarse_purpose(value):

    value = str(value or "").upper()

    if "IRRIG" in value:
        return "IRRIGATION"

    if (
        "FLOOD" in value
        or "CONTROL" in value
    ):
        return "FLOOD_CONTROL"

    if (
        "WATER SUPPLY" in value
        or "WATER_SUPPLY" in value
    ):
        return "WATER_SUPPLY"

    if (
        "HYDRO" in value
        or "POWER" in value
    ):
        return "HYDROPOWER"

    if "RECREATION" in value:
        return "RECREATION"

    return "OTHER"


def epoch_date(value):

    if pd.isna(value):
        return pd.NaT

    try:

        number = float(value)

        if number > 10_000_000_000:
            return pd.to_datetime(
                number,
                unit="ms",
                utc=True,
                errors="coerce",
            )

        return pd.to_datetime(
            number,
            unit="s",
            utc=True,
            errors="coerce",
        )

    except Exception:

        return pd.to_datetime(
            value,
            utc=True,
            errors="coerce",
        )


def ece(y, p, bins=10):

    y = np.asarray(y)
    p = np.asarray(p)

    edges = np.linspace(
        0.0,
        1.0,
        bins + 1,
    )

    result = 0.0

    for i in range(bins):

        if i == bins - 1:

            mask = (
                (p >= edges[i])
                & (p <= edges[i + 1])
            )

        else:

            mask = (
                (p >= edges[i])
                & (p < edges[i + 1])
            )

        if not np.any(mask):
            continue

        result += (
            np.mean(mask)
            * abs(
                np.mean(y[mask])
                - np.mean(p[mask])
            )
        )

    return float(result)


# ============================================================
# DOWNLOAD RICH NID DATA
# ============================================================

def download_nid():

    fields = [
        "OBJECTID",
        "NIDID",
        "STATE",
        "YEAR_COMPLETED",
        "PRIMARY_DAM_TYPE",
        "PRIMARY_PURPOSE",
        "DAM_HEIGHT",
        "HYDRAULIC_HEIGHT",
        "STRUCTURAL_HEIGHT",
        "DAM_LENGTH",
        "DAM_VOLUME",
        "NID_STORAGE",
        "MAX_STORAGE",
        "NORMAL_STORAGE",
        "SURFACE_AREA",
        "DRAINAGE_AREA",
        "MAX_DISCHARGE",
        "SPILLWAY_TYPE",
        "SPILLWAY_WIDTH",
        "CONDITION_ASSESSMENT",
        "CONDITION_ASSESS_DATE",
        "LAST_INSPECTION_DATE",
        "INSPECTION_FREQUENCY",
        "HAZARD_POTENTIAL",
    ]

    rows = []
    offset = 0
    page_size = 2000

    print()
    print("=" * 100)
    print("DOWNLOAD REAL USACE NID CONDITION DATA")
    print("=" * 100)

    while True:

        parameters = {
            "where":
                "CONDITION_ASSESSMENT IS NOT NULL",

            "outFields":
                ",".join(fields),

            "returnGeometry":
                "false",

            "resultOffset":
                offset,

            "resultRecordCount":
                page_size,

            "orderByFields":
                "OBJECTID",

            "f":
                "json",
        }

        url = (
            NID_URL
            + "?"
            + urllib.parse.urlencode(
                parameters
            )
        )

        payload = None

        for attempt in range(1, 5):

            try:

                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent":
                            "SIMRAS-Research/1.0"
                    },
                )

                with urllib.request.urlopen(
                    request,
                    timeout=90,
                ) as response:

                    payload = json.loads(
                        response.read().decode(
                            "utf-8"
                        )
                    )

                break

            except Exception:

                if attempt == 4:
                    raise

                time.sleep(
                    attempt * 2
                )

        if payload is None:

            raise RuntimeError(
                "No NID response."
            )

        if "error" in payload:

            raise RuntimeError(
                json.dumps(
                    payload["error"]
                )
            )

        features = payload.get(
            "features",
            [],
        )

        if not features:
            break

        rows.extend(
            feature.get(
                "attributes",
                {}
            )
            for feature in features
        )

        print(
            f"Downloaded: {len(rows):,}"
        )

        if len(features) < page_size:
            break

        offset += page_size

    frame = pd.DataFrame(rows)

    if frame.empty:

        raise RuntimeError(
            "NID returned no records."
        )

    return frame


# ============================================================
# CLEAN + FEATURE ENGINEERING
# ============================================================

raw = download_nid()

raw[
    "condition_class"
] = raw[
    "CONDITION_ASSESSMENT"
].map(
    condition_class
)

df = raw[
    raw[
        "condition_class"
    ].notna()
].copy()


numeric_raw = [
    "YEAR_COMPLETED",
    "DAM_HEIGHT",
    "HYDRAULIC_HEIGHT",
    "STRUCTURAL_HEIGHT",
    "DAM_LENGTH",
    "DAM_VOLUME",
    "NID_STORAGE",
    "MAX_STORAGE",
    "NORMAL_STORAGE",
    "SURFACE_AREA",
    "DRAINAGE_AREA",
    "MAX_DISCHARGE",
    "SPILLWAY_WIDTH",
    "INSPECTION_FREQUENCY",
]

for column in numeric_raw:

    df[column] = pd.to_numeric(
        df[column],
        errors="coerce",
    )


df[
    "condition_date"
] = df[
    "CONDITION_ASSESS_DATE"
].map(
    epoch_date
)


# IMPORTANT:
# Age is calculated at the assessment date,
# not automatically at 2026.
condition_year = (
    df[
        "condition_date"
    ].dt.year
)


df[
    "age_at_assessment"
] = (
    condition_year
    - df[
        "YEAR_COMPLETED"
    ]
)


invalid_age = (
    (df["age_at_assessment"] < 0)
    | (df["age_at_assessment"] > 300)
)

df.loc[
    invalid_age,
    "age_at_assessment"
] = np.nan


df[
    "dam_type"
] = df[
    "PRIMARY_DAM_TYPE"
].map(
    coarse_type
)


df[
    "purpose"
] = df[
    "PRIMARY_PURPOSE"
].map(
    coarse_purpose
)


df[
    "spillway_type"
] = (
    df[
        "SPILLWAY_TYPE"
    ]
    .fillna("UNKNOWN")
    .astype(str)
    .str.upper()
    .str.slice(0, 80)
)


# These are logged copies of factual physical variables.
for source, destination in [
    ("DAM_HEIGHT", "log_height"),
    ("DAM_LENGTH", "log_length"),
    ("MAX_STORAGE", "log_storage"),
    ("MAX_DISCHARGE", "log_discharge"),
    ("DRAINAGE_AREA", "log_drainage"),
    ("DAM_VOLUME", "log_volume"),
]:

    values = pd.to_numeric(
        df[source],
        errors="coerce",
    )

    df[destination] = np.log1p(
        values.clip(lower=0)
    )


# Structural-condition target.
df[
    "adverse_condition"
] = df[
    "condition_class"
].isin(
    [
        "POOR",
        "UNSATISFACTORY",
    ]
).astype(int)


# Explicit ordinal research index target.
severity = {
    "UNSATISFACTORY": 0.0,
    "POOR": 1.0,
    "FAIR": 2.0,
    "SATISFACTORY": 3.0,
}

df[
    "condition_ordinal"
] = df[
    "condition_class"
].map(
    severity
)


df = df[
    df["STATE"].notna()
].copy()


print()
print("=" * 100)
print("CLEAN TRAINING DATA")
print("=" * 100)

print(
    "Usable rows:",
    f"{len(df):,}",
)

print()
print(
    df[
        "condition_class"
    ]
    .value_counts()
    .to_string()
)


# ============================================================
# GEOGRAPHIC GROUP HOLDOUT
#
# States in test are not present in train.
# ============================================================

groups = df[
    "STATE"
].astype(str)


outer = GroupShuffleSplit(
    n_splits=1,
    test_size=0.20,
    random_state=RANDOM_STATE,
)

development_index, test_index = next(
    outer.split(
        df,
        groups=groups,
    )
)


development = df.iloc[
    development_index
].copy()

test = df.iloc[
    test_index
].copy()


inner_groups = development[
    "STATE"
].astype(str)


inner = GroupShuffleSplit(
    n_splits=1,
    test_size=0.25,
    random_state=RANDOM_STATE + 1,
)


train_index, validation_index = next(
    inner.split(
        development,
        groups=inner_groups,
    )
)


train = development.iloc[
    train_index
].copy()

validation = development.iloc[
    validation_index
].copy()


print()
print("Train rows     :", len(train))
print("Validation rows:", len(validation))
print("Test rows      :", len(test))

print(
    "Train states    :",
    train["STATE"].nunique(),
)

print(
    "Validation states:",
    validation["STATE"].nunique(),
)

print(
    "Test states     :",
    test["STATE"].nunique(),
)


# ============================================================
# CORE AP-TRANSFER FEATURE SET
#
# These correspond to facts SIMRAS can reasonably acquire
# from CWC/AP engineering records.
# ============================================================

CORE_NUMERIC = [
    "age_at_assessment",
    "DAM_HEIGHT",
    "DAM_LENGTH",
    "MAX_STORAGE",
    "MAX_DISCHARGE",
    "log_height",
    "log_length",
    "log_storage",
    "log_discharge",
]

CORE_CATEGORICAL = [
    "dam_type",
    "purpose",
]


# Extended NID benchmark is evaluated separately.
# It is NOT automatically usable for AP inference.
EXTENDED_NUMERIC = CORE_NUMERIC + [
    "HYDRAULIC_HEIGHT",
    "STRUCTURAL_HEIGHT",
    "DAM_VOLUME",
    "NID_STORAGE",
    "NORMAL_STORAGE",
    "SURFACE_AREA",
    "DRAINAGE_AREA",
    "SPILLWAY_WIDTH",
    "log_drainage",
    "log_volume",
]

EXTENDED_CATEGORICAL = CORE_CATEGORICAL + [
    "spillway_type",
]


def preprocessing(
    numeric,
    categorical,
    scale=False,
):

    numeric_steps = [
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            ),
        ),
    ]

    if scale:

        numeric_steps.append(
            (
                "scale",
                StandardScaler(),
            )
        )

    numeric_pipe = Pipeline(
        numeric_steps
    )

    category_pipe = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="most_frequent"
                ),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore",
                    min_frequency=20,
                    sparse_output=False,
                ),
            ),
        ]
    )

    return ColumnTransformer(
        [
            (
                "numeric",
                numeric_pipe,
                numeric,
            ),
            (
                "categorical",
                category_pipe,
                categorical,
            ),
        ],
        sparse_threshold=0.0,
    )


def classifier_pipeline(
    model,
    numeric,
    categorical,
    scale=False,
):

    return Pipeline(
        [
            (
                "preprocess",
                preprocessing(
                    numeric,
                    categorical,
                    scale=scale,
                ),
            ),
            (
                "model",
                model,
            ),
        ]
    )


# ============================================================
# RISK MODEL LADDER
# ============================================================

risk_candidates = {
    "CORE_LOGISTIC":
        classifier_pipeline(
            LogisticRegression(
                max_iter=2000,
                class_weight="balanced",
                solver="liblinear",
            ),
            CORE_NUMERIC,
            CORE_CATEGORICAL,
            scale=True,
        ),

    "CORE_RANDOM_FOREST":
        classifier_pipeline(
            RandomForestClassifier(
                n_estimators=600,
                min_samples_leaf=5,
                max_features="sqrt",
                class_weight="balanced_subsample",
                n_jobs=-1,
                random_state=RANDOM_STATE,
            ),
            CORE_NUMERIC,
            CORE_CATEGORICAL,
        ),

    "CORE_EXTRA_TREES":
        classifier_pipeline(
            ExtraTreesClassifier(
                n_estimators=700,
                min_samples_leaf=4,
                max_features="sqrt",
                class_weight="balanced",
                n_jobs=-1,
                random_state=RANDOM_STATE,
            ),
            CORE_NUMERIC,
            CORE_CATEGORICAL,
        ),

    "CORE_HIST_GRADIENT":
        classifier_pipeline(
            HistGradientBoostingClassifier(
                learning_rate=0.05,
                max_iter=350,
                max_leaf_nodes=31,
                min_samples_leaf=25,
                l2_regularization=1.0,
                random_state=RANDOM_STATE,
            ),
            CORE_NUMERIC,
            CORE_CATEGORICAL,
        ),
}


X_train = train[
    CORE_NUMERIC
    + CORE_CATEGORICAL
]

X_validation = validation[
    CORE_NUMERIC
    + CORE_CATEGORICAL
]

y_train = train[
    "adverse_condition"
].astype(int)

y_validation = validation[
    "adverse_condition"
].astype(int)


risk_validation = {}


print()
print("=" * 100)
print("RISK MODEL LADDER - VALIDATION")
print("=" * 100)


for name, model in risk_candidates.items():

    model.fit(
        X_train,
        y_train,
    )

    probability = model.predict_proba(
        X_validation
    )[:, 1]

    auc = float(
        roc_auc_score(
            y_validation,
            probability,
        )
    )

    pr = float(
        average_precision_score(
            y_validation,
            probability,
        )
    )

    risk_validation[name] = {
        "roc_auc": auc,
        "pr_auc": pr,
    }

    print(
        f"{name:<25} "
        f"AUC={auc:.6f} "
        f"PR-AUC={pr:.6f}"
    )


best_risk_name = max(
    risk_validation,
    key=lambda name: (
        risk_validation[name]["roc_auc"],
        risk_validation[name]["pr_auc"],
    ),
)


print()
print(
    "Selected CORE risk model:",
    best_risk_name,
)


# ============================================================
# FINAL RISK MODEL
#
# Candidate selection used validation.
# The final quality score is measured only on untouched test.
# ============================================================

development_features = development[
    CORE_NUMERIC
    + CORE_CATEGORICAL
]

development_target = development[
    "adverse_condition"
].astype(int)


best_base = clone(
    risk_candidates[
        best_risk_name
    ]
)


risk_model = CalibratedClassifierCV(
    estimator=best_base,
    method="sigmoid",
    cv=5,
)


risk_model.fit(
    development_features,
    development_target,
)


X_test = test[
    CORE_NUMERIC
    + CORE_CATEGORICAL
]

y_test = test[
    "adverse_condition"
].astype(int)


risk_probability = risk_model.predict_proba(
    X_test
)[:, 1]


risk_auc = float(
    roc_auc_score(
        y_test,
        risk_probability,
    )
)


risk_pr = float(
    average_precision_score(
        y_test,
        risk_probability,
    )
)


risk_prevalence = float(
    y_test.mean()
)


risk_brier = float(
    brier_score_loss(
        y_test,
        risk_probability,
    )
)


baseline_brier = float(
    np.mean(
        (
            y_test.to_numpy()
            - risk_prevalence
        ) ** 2
    )
)


risk_ece = ece(
    y_test.to_numpy(),
    risk_probability,
)


risk_gates = {
    "roc_auc_ge_0_70":
        risk_auc >= 0.70,

    "pr_auc_gt_prevalence":
        risk_pr > risk_prevalence,

    "brier_beats_baseline":
        risk_brier < baseline_brier,

    "ece_le_0_10":
        risk_ece <= 0.10,
}


# ============================================================
# HEALTH / CONDITION ORDINAL MODEL LADDER
#
# No fabricated official CWC Health score.
# This predicts an ordinal research condition index.
# ============================================================

health_candidates = {
    "CORE_RANDOM_FOREST":
        Pipeline(
            [
                (
                    "preprocess",
                    preprocessing(
                        CORE_NUMERIC,
                        CORE_CATEGORICAL,
                    ),
                ),
                (
                    "model",
                    RandomForestRegressor(
                        n_estimators=600,
                        min_samples_leaf=5,
                        max_features="sqrt",
                        n_jobs=-1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

    "CORE_EXTRA_TREES":
        Pipeline(
            [
                (
                    "preprocess",
                    preprocessing(
                        CORE_NUMERIC,
                        CORE_CATEGORICAL,
                    ),
                ),
                (
                    "model",
                    ExtraTreesRegressor(
                        n_estimators=700,
                        min_samples_leaf=4,
                        max_features="sqrt",
                        n_jobs=-1,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),

    "CORE_HIST_GRADIENT":
        Pipeline(
            [
                (
                    "preprocess",
                    preprocessing(
                        CORE_NUMERIC,
                        CORE_CATEGORICAL,
                    ),
                ),
                (
                    "model",
                    HistGradientBoostingRegressor(
                        learning_rate=0.05,
                        max_iter=350,
                        max_leaf_nodes=31,
                        min_samples_leaf=25,
                        l2_regularization=1.0,
                        random_state=RANDOM_STATE,
                    ),
                ),
            ]
        ),
}


health_validation = {}

health_y_train = train[
    "condition_ordinal"
].astype(float)

health_y_validation = validation[
    "condition_ordinal"
].astype(float)


print()
print("=" * 100)
print("HEALTH ORDINAL MODEL LADDER - VALIDATION")
print("=" * 100)


for name, model in health_candidates.items():

    model.fit(
        X_train,
        health_y_train,
    )

    prediction = np.clip(
        model.predict(
            X_validation
        ),
        0.0,
        3.0,
    )

    mae = float(
        mean_absolute_error(
            health_y_validation,
            prediction,
        )
    )

    health_validation[name] = {
        "mae": mae,
    }

    print(
        f"{name:<25} "
        f"MAE={mae:.6f}"
    )


best_health_name = min(
    health_validation,
    key=lambda name:
        health_validation[name]["mae"],
)


print()
print(
    "Selected CORE Health model:",
    best_health_name,
)


health_model = clone(
    health_candidates[
        best_health_name
    ]
)


health_model.fit(
    development_features,
    development[
        "condition_ordinal"
    ].astype(float),
)


health_test_actual = test[
    "condition_ordinal"
].astype(float)


health_test_prediction = np.clip(
    health_model.predict(
        X_test
    ),
    0.0,
    3.0,
)


health_mae = float(
    mean_absolute_error(
        health_test_actual,
        health_test_prediction,
    )
)


baseline_value = float(
    development[
        "condition_ordinal"
    ].median()
)


baseline_prediction = np.full(
    len(test),
    baseline_value,
)


health_baseline_mae = float(
    mean_absolute_error(
        health_test_actual,
        baseline_prediction,
    )
)


health_improvement = (
    (
        health_baseline_mae
        - health_mae
    )
    / health_baseline_mae
    if health_baseline_mae > 0
    else 0.0
)


health_gates = {
    "mae_beats_baseline":
        health_mae
        < health_baseline_mae,

    "mae_improvement_ge_05":
        health_improvement
        >= 0.05,

    "ordinal_mae_le_0_80":
        health_mae
        <= 0.80,
}


# ============================================================
# EXTENDED NID BENCHMARK
#
# This is a research benchmark only.
# It is NOT approved for AP inference merely because it scores
# better, because AP may not have every extended input.
# ============================================================

extended_model = classifier_pipeline(
    ExtraTreesClassifier(
        n_estimators=700,
        min_samples_leaf=4,
        max_features="sqrt",
        class_weight="balanced",
        n_jobs=-1,
        random_state=RANDOM_STATE,
    ),
    EXTENDED_NUMERIC,
    EXTENDED_CATEGORICAL,
)


extended_model.fit(
    development[
        EXTENDED_NUMERIC
        + EXTENDED_CATEGORICAL
    ],
    development_target,
)


extended_probability = (
    extended_model.predict_proba(
        test[
            EXTENDED_NUMERIC
            + EXTENDED_CATEGORICAL
        ]
    )[:, 1]
)


extended_auc = float(
    roc_auc_score(
        y_test,
        extended_probability,
    )
)


extended_pr = float(
    average_precision_score(
        y_test,
        extended_probability,
    )
)


# ============================================================
# SUMMARY
# ============================================================

summary = {
    "phase":
        "ML-7B",

    "training_source":
        "USACE National Inventory of Dams",

    "validation_design":
        (
            "State-group train/validation/test split. "
            "State is not used as a prediction feature."
        ),

    "target_semantics": {
        "risk":
            (
                "Probability of POOR or UNSATISFACTORY "
                "condition. Not collapse probability."
            ),

        "health":
            (
                "Research-transfer ordinal condition index. "
                "Not an official CWC Health Score."
            ),
    },

    "rows":
        int(
            len(df)
        ),

    "best_core_risk_model":
        best_risk_name,

    "risk_test": {
        "roc_auc":
            risk_auc,

        "pr_auc":
            risk_pr,

        "prevalence":
            risk_prevalence,

        "brier":
            risk_brier,

        "baseline_brier":
            baseline_brier,

        "ece":
            risk_ece,

        "gates":
            risk_gates,

        "approved":
            bool(
                all(
                    risk_gates.values()
                )
            ),
    },

    "best_core_health_model":
        best_health_name,

    "health_test": {
        "ordinal_mae":
            health_mae,

        "baseline_mae":
            health_baseline_mae,

        "improvement_fraction":
            health_improvement,

        "gates":
            health_gates,

        "approved":
            bool(
                all(
                    health_gates.values()
                )
            ),
    },

    "extended_nid_benchmark": {
        "roc_auc":
            extended_auc,

        "pr_auc":
            extended_pr,

        "ap_inference_status":
            "NOT_AUTOMATICALLY_APPROVED",
    },

    "ap_predictions_written":
        0,

    "database_modified":
        False,

    "confidence_policy":
        "WITHHELD_PENDING_AP_GROUND_TRUTH_VALIDATION",

    "rul_policy":
        "WITHHELD",
}


print()
print("=" * 100)
print("ML-7B UNTOUCHED TEST RESULTS")
print("=" * 100)

print()
print("RISK")
print(
    json.dumps(
        summary[
            "risk_test"
        ],
        indent=2,
    )
)

print()
print("HEALTH")
print(
    json.dumps(
        summary[
            "health_test"
        ],
        indent=2,
    )
)

print()
print("EXTENDED NID BENCHMARK")
print(
    json.dumps(
        summary[
            "extended_nid_benchmark"
        ],
        indent=2,
    )
)


# ============================================================
# SAVE
# ============================================================

df.to_csv(
    OUT / "nid_ml7b_training.csv",
    index=False,
)


(
    OUT
    / "ml7b_summary.json"
).write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


if all(
    risk_gates.values()
):

    joblib.dump(
        risk_model,
        MODEL_DIR
        / "approved_core_risk_model.joblib",
    )


if all(
    health_gates.values()
):

    joblib.dump(
        health_model,
        MODEL_DIR
        / "approved_core_health_model.joblib",
    )


(
    ROOT
    / "LATEST_ML7B.txt"
).write_text(
    str(OUT),
    encoding="utf-8",
)


print()
print("=" * 100)
print("ML-7B DECISION")
print("=" * 100)

print(
    "Risk model approved  :",
    all(
        risk_gates.values()
    ),
)

print(
    "Health model approved:",
    all(
        health_gates.values()
    ),
)

print()
print(
    "AP predictions written: 0"
)

print(
    "Database modified     : NO"
)

print(
    "Confidence            : WITHHELD"
)

print(
    "RUL                   : WITHHELD"
)

print()
print(
    "Output:",
    OUT,
)


if (
    all(
        risk_gates.values()
    )
    and all(
        health_gates.values()
    )
):

    print()
    print(
        "NEXT = ML-7C AP FEATURE CROSSWALK + "
        "ELIGIBILITY + INFERENCE"
    )

elif all(
    risk_gates.values()
):

    print()
    print(
        "NEXT = ML-7C persist Risk only; "
        "continue Health research"
    )

elif all(
    health_gates.values()
):

    print()
    print(
        "NEXT = ML-7C persist Health research index only; "
        "continue Risk research"
    )

else:

    print()
    print(
        "NEXT = ML-7C acquire stronger condition features. "
        "DO NOT lower quality gates."
    )