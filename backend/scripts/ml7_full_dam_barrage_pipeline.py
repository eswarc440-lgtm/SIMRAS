import os
import json
import math
import asyncio
import urllib.parse
import urllib.request
import time
from pathlib import Path
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    brier_score_loss,
    f1_score,
    accuracy_score,
    log_loss,
    roc_curve,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler


# ============================================================
# CONFIGURATION
# ============================================================

NOW = datetime.now(timezone.utc)

STAMP = NOW.strftime("%Y%m%d_%H%M%S")

ROOT = Path("/app/data/ml/dam_barrage")

OUT = ROOT / f"ml7_{STAMP}"

MODEL_DIR = OUT / "models"

OUT.mkdir(
    parents=True,
    exist_ok=True,
)

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


NID_URL = (
    "https://geospatial.sec.usace.army.mil/"
    "dls/rest/services/NID/"
    "National_Inventory_of_Dams_Public_Service/"
    "FeatureServer/0/query"
)


MODEL_VERSION = (
    "nid_dam_condition_transfer_"
    + NOW.strftime("%Y%m%d")
)

FEATURE_VERSION = (
    "cwc_ap_nid_shared_dam_v1"
)


# ============================================================
# OFFICIAL CWC PRakasam BARRAGE PROFILE
#
# Source:
# CWC National Register of Specified Dams 2025
# CWC History of Irrigation Development in Andhra Pradesh
# ============================================================

PRAKASAM_CWC = {
    "river":
        "Krishna",

    "structure_type":
        "Barrage",

    # Physical structural family used only for cross-domain
    # ML feature mapping.
    "model_structure_type":
        "Gravity",

    "height_m":
        22.25,

    "length_m":
        1233.0,

    "completion_year":
        1957,

    "spillway_capacity_cumecs":
        33693.0,

    "design_flood_cumecs":
        33984.0,

    "gates":
        70,

    "gate_width_m":
        12.19,

    "gate_height_m":
        3.66,

    "pier_thickness_m":
        2.44,

    "pond_level_m":
        17.38,

    "purpose":
        "Irrigation",

    "source_authority":
        "Central Water Commission / Andhra Pradesh WRD",

    "source_document":
        (
            "National Register of Specified Dams 2025; "
            "History of Irrigation Development in Andhra Pradesh"
        ),

    "source_url":
        (
            "https://dharma.cwc.gov.in/dharma/public/"
            "uploads/front_upload_file/"
            "174860534186541140.pdf"
        ),

    "evidence_class":
        "GOVERNMENT_FACT",

    "quality_status":
        "CWC_VERIFIED",
}


# ============================================================
# HELPERS
# ============================================================

def clean_number(value):

    if value is None:
        return None

    if isinstance(
        value,
        (int, float, np.integer, np.floating),
    ):

        if math.isfinite(
            float(value)
        ):
            return float(value)

        return None

    text_value = str(value).strip()

    if not text_value:
        return None

    text_value = (
        text_value
        .replace(",", "")
        .replace("m³/s", "")
        .replace("m3/s", "")
        .replace("m", "")
        .strip()
    )

    try:
        result = float(text_value)

        if math.isfinite(result):
            return result

    except Exception:
        pass

    return None


def clean_int(value):

    number = clean_number(value)

    if number is None:
        return None

    return int(
        round(number)
    )


def clean_text(value):

    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    if value.upper() in {
        "UNKNOWN",
        "N/A",
        "NA",
        "NULL",
        "NONE",
        "-",
    }:
        return None

    return value


def flatten_json(value):

    result = {}

    if not isinstance(
        value,
        dict,
    ):
        return result

    for key, item in value.items():

        result[str(key).lower()] = item

        if isinstance(
            item,
            dict,
        ):

            for child_key, child_value in item.items():

                result[
                    str(child_key).lower()
                ] = child_value

    return result


def first_value(
    row,
    names,
):

    for name in names:

        name = name.lower()

        if name not in row:
            continue

        value = row[name]

        if value is None:
            continue

        if isinstance(
            value,
            str,
        ) and not value.strip():
            continue

        return value

    return None


def simple_dam_type(value):

    value = (
        clean_text(value)
        or "OTHER"
    ).upper()

    if (
        "EARTH" in value
        or "EARTHEN" in value
        or "EMBANKMENT" in value
    ):
        return "EARTH"

    if (
        "GRAVITY" in value
        or "MASONRY" in value
        or "CONCRETE" in value
        or "BARRAGE" in value
        or value == "PG"
    ):
        return "GRAVITY"

    if (
        "ROCK" in value
        or "RF" in value
    ):
        return "ROCKFILL"

    if "ARCH" in value:
        return "ARCH"

    if "BUTTRESS" in value:
        return "BUTTRESS"

    return "OTHER"


def simple_purpose(value):

    value = (
        clean_text(value)
        or "OTHER"
    ).upper()

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


def normalize_condition(value):

    if value is None:
        return None

    value = str(value).strip().upper()

    if not value:
        return None

    # Order matters because UNSATISFACTORY contains SATISFACTORY.
    if "UNSATISFACTORY" in value:
        return "UNSATISFACTORY"

    if "POOR" in value:
        return "POOR"

    if "FAIR" in value:
        return "FAIR"

    if "SATISFACTORY" in value:
        return "SATISFACTORY"

    return None


def risk_level(
    probability,
    medium_threshold,
    high_threshold,
):

    if probability >= high_threshold:
        return "HIGH"

    if probability >= medium_threshold:
        return "MEDIUM"

    return "LOW"


def m_to_ft(value):

    if value is None:
        return np.nan

    return float(value) * 3.280839895


def mcm_to_acre_ft(value):

    if value is None:
        return np.nan

    return float(value) * 810.713194


def cumecs_to_cfs(value):

    if value is None:
        return np.nan

    return float(value) * 35.31466672


# ============================================================
# DOWNLOAD REAL USACE NID CONDITION DATA
# ============================================================

def fetch_nid():

    print()
    print("=" * 100)
    print("DOWNLOADING USACE NID CONDITION ASSESSMENTS")
    print("=" * 100)

    out_fields = [
        "NIDID",
        "NAME",
        "YEAR_COMPLETED",
        "DAM_HEIGHT",
        "DAM_LENGTH",
        "MAX_STORAGE",
        "MAX_DISCHARGE",
        "PRIMARY_DAM_TYPE",
        "PRIMARY_PURPOSE",
        "CONDITION_ASSESSMENT",
        "CONDITION_ASSESS_DATE",
    ]

    records = []

    offset = 0
    page_size = 2000

    while True:

        params = {
            "where":
                "CONDITION_ASSESSMENT IS NOT NULL",

            "outFields":
                ",".join(out_fields),

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
                params
            )
        )

        last_error = None

        for attempt in range(1, 5):

            try:

                request = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent":
                            "SIMRAS-Research/1.0",
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

            except Exception as exc:

                last_error = exc

                if attempt == 4:
                    raise

                time.sleep(
                    attempt * 2
                )

        if "error" in payload:

            raise RuntimeError(
                "NID API error: "
                + json.dumps(
                    payload["error"]
                )
            )

        features = payload.get(
            "features",
            [],
        )

        if not features:
            break

        page = [
            feature.get(
                "attributes",
                {},
            )
            for feature in features
        ]

        records.extend(page)

        print(
            f"NID rows downloaded: {len(records):,}"
        )

        if len(features) < page_size:
            break

        offset += page_size

    if not records:

        raise RuntimeError(
            "NID returned zero condition records."
        )

    dataframe = pd.DataFrame(
        records
    )

    dataframe[
        "condition_class"
    ] = dataframe[
        "CONDITION_ASSESSMENT"
    ].map(
        normalize_condition
    )

    dataframe = dataframe[
        dataframe[
            "condition_class"
        ].notna()
    ].copy()

    dataframe[
        "year_completed"
    ] = pd.to_numeric(
        dataframe[
            "YEAR_COMPLETED"
        ],
        errors="coerce",
    )

    dataframe[
        "age_years"
    ] = (
        NOW.year
        - dataframe[
            "year_completed"
        ]
    )

    dataframe[
        "dam_height_ft"
    ] = pd.to_numeric(
        dataframe[
            "DAM_HEIGHT"
        ],
        errors="coerce",
    )

    dataframe[
        "dam_length_ft"
    ] = pd.to_numeric(
        dataframe[
            "DAM_LENGTH"
        ],
        errors="coerce",
    )

    dataframe[
        "max_storage_acft"
    ] = pd.to_numeric(
        dataframe[
            "MAX_STORAGE"
        ],
        errors="coerce",
    )

    dataframe[
        "max_discharge_cfs"
    ] = pd.to_numeric(
        dataframe[
            "MAX_DISCHARGE"
        ],
        errors="coerce",
    )

    dataframe[
        "dam_type"
    ] = dataframe[
        "PRIMARY_DAM_TYPE"
    ].map(
        simple_dam_type
    )

    dataframe[
        "purpose"
    ] = dataframe[
        "PRIMARY_PURPOSE"
    ].map(
        simple_purpose
    )

    dataframe[
        "adverse_condition"
    ] = dataframe[
        "condition_class"
    ].isin(
        [
            "POOR",
            "UNSATISFACTORY",
        ]
    ).astype(int)

    return dataframe


# ============================================================
# TRAIN MODELS
# ============================================================

def train_models(
    nid,
):

    print()
    print("=" * 100)
    print("TRAINING NID -> AP RESEARCH TRANSFER MODELS")
    print("=" * 100)

    numeric = [
        "age_years",
        "dam_height_ft",
        "dam_length_ft",
        "max_storage_acft",
        "max_discharge_cfs",
    ]

    categorical = [
        "dam_type",
        "purpose",
    ]

    features = (
        numeric
        + categorical
    )

    X = nid[
        features
    ].copy()

    y_risk = nid[
        "adverse_condition"
    ].astype(int)

    y_health = nid[
        "condition_class"
    ].astype(str)


    indices = np.arange(
        len(nid)
    )

    train_index, test_index = train_test_split(
        indices,
        test_size=0.25,
        random_state=440,
        stratify=y_risk,
    )


    numeric_pipe = Pipeline(
        [
            (
                "imputer",
                SimpleImputer(
                    strategy="median"
                ),
            ),
            (
                "scale",
                StandardScaler(),
            ),
        ]
    )


    categorical_pipe = Pipeline(
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
                    min_frequency=10,
                ),
            ),
        ]
    )


    preprocess = ColumnTransformer(
        [
            (
                "numeric",
                numeric_pipe,
                numeric,
            ),
            (
                "categorical",
                categorical_pipe,
                categorical,
            ),
        ]
    )


    base_risk = Pipeline(
        [
            (
                "preprocess",
                preprocess,
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=1500,
                    class_weight="balanced",
                    solver="liblinear",
                ),
            ),
        ]
    )


    risk_model = CalibratedClassifierCV(
        estimator=base_risk,
        method="sigmoid",
        cv=3,
    )


    risk_model.fit(
        X.iloc[
            train_index
        ],
        y_risk.iloc[
            train_index
        ],
    )


    risk_prob = risk_model.predict_proba(
        X.iloc[
            test_index
        ]
    )[:, 1]


    y_test_risk = y_risk.iloc[
        test_index
    ].to_numpy()


    prevalence = float(
        np.mean(
            y_test_risk
        )
    )

    auc = float(
        roc_auc_score(
            y_test_risk,
            risk_prob,
        )
    )

    pr_auc = float(
        average_precision_score(
            y_test_risk,
            risk_prob,
        )
    )

    brier = float(
        brier_score_loss(
            y_test_risk,
            risk_prob,
        )
    )

    baseline_brier = float(
        np.mean(
            (
                y_test_risk
                - prevalence
            ) ** 2
        )
    )


    fpr, tpr, thresholds = roc_curve(
        y_test_risk,
        risk_prob,
    )

    valid_thresholds = np.isfinite(
        thresholds
    )

    fpr = fpr[
        valid_thresholds
    ]

    tpr = tpr[
        valid_thresholds
    ]

    thresholds = thresholds[
        valid_thresholds
    ]


    best_index = int(
        np.argmax(
            tpr - fpr
        )
    )


    high_threshold = float(
        np.clip(
            thresholds[
                best_index
            ],
            0.15,
            0.80,
        )
    )


    medium_threshold = float(
        min(
            high_threshold * 0.60,
            max(
                prevalence,
                0.05,
            ),
        )
    )


    risk_gates = {
        "auc_ge_0_70":
            auc >= 0.70,

        "pr_auc_gt_prevalence":
            pr_auc > prevalence,

        "brier_beats_baseline":
            brier < baseline_brier,
    }


    # --------------------------------------------------------
    # HEALTH / CONDITION MODEL
    # --------------------------------------------------------

    health_model = Pipeline(
        [
            (
                "preprocess",
                preprocess,
            ),
            (
                "model",
                LogisticRegression(
                    max_iter=1800,
                    class_weight="balanced",
                    solver="lbfgs",
                ),
            ),
        ]
    )


    health_model.fit(
        X.iloc[
            train_index
        ],
        y_health.iloc[
            train_index
        ],
    )


    health_pred = health_model.predict(
        X.iloc[
            test_index
        ]
    )


    y_test_health = y_health.iloc[
        test_index
    ]


    health_accuracy = float(
        accuracy_score(
            y_test_health,
            health_pred,
        )
    )


    health_macro_f1 = float(
        f1_score(
            y_test_health,
            health_pred,
            average="macro",
        )
    )


    majority = (
        y_health.iloc[
            train_index
        ]
        .value_counts()
        .index[0]
    )


    majority_pred = np.full(
        len(
            test_index
        ),
        majority,
        dtype=object,
    )


    baseline_macro_f1 = float(
        f1_score(
            y_test_health,
            majority_pred,
            average="macro",
            zero_division=0,
        )
    )


    health_gates = {
        "macro_f1_beats_majority":
            health_macro_f1
            > baseline_macro_f1,

        "macro_f1_ge_0_40":
            health_macro_f1
            >= 0.40,
    }


    metrics = {
        "training_source":
            "USACE National Inventory of Dams",

        "status":
            "RESEARCH_TRANSFER",

        "rows":
            int(
                len(nid)
            ),

        "risk": {
            "roc_auc":
                auc,

            "pr_auc":
                pr_auc,

            "prevalence":
                prevalence,

            "brier":
                brier,

            "baseline_brier":
                baseline_brier,

            "medium_threshold":
                medium_threshold,

            "high_threshold":
                high_threshold,

            "gates":
                risk_gates,
        },

        "health_condition": {
            "accuracy":
                health_accuracy,

            "macro_f1":
                health_macro_f1,

            "majority_macro_f1":
                baseline_macro_f1,

            "gates":
                health_gates,
        },
    }


    print(
        json.dumps(
            metrics,
            indent=2,
        )
    )


    if not all(
        risk_gates.values()
    ):

        raise RuntimeError(
            "Risk model failed quality gates. "
            "No AP predictions will be persisted."
        )


    if not all(
        health_gates.values()
    ):

        raise RuntimeError(
            "Health condition model failed quality gates. "
            "No AP Health predictions will be persisted."
        )


    joblib.dump(
        risk_model,
        MODEL_DIR
        / "risk_model.joblib",
    )


    joblib.dump(
        health_model,
        MODEL_DIR
        / "health_condition_model.joblib",
    )


    (
        MODEL_DIR
        / "metrics.json"
    ).write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )


    return (
        risk_model,
        health_model,
        metrics,
        numeric,
        categorical,
    )


# ============================================================
# DATABASE
# ============================================================

async def main():

    database_url = os.getenv(
        "DATABASE_URL"
    )

    if not database_url:

        raise RuntimeError(
            "DATABASE_URL is not available."
        )


    if database_url.startswith(
        "postgresql://"
    ):

        database_url = database_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )


    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
    )


    nid = fetch_nid()


    print()
    print(
        "NID usable condition rows:",
        f"{len(nid):,}",
    )


    print()
    print(
        "NID condition distribution:"
    )

    print(
        nid[
            "condition_class"
        ]
        .value_counts()
        .to_string()
    )


    nid_path = (
        OUT
        / "nid_condition_training.csv"
    )


    nid.to_csv(
        nid_path,
        index=False,
    )


    (
        risk_model,
        health_model,
        metrics,
        numeric_features,
        categorical_features,
    ) = train_models(
        nid
    )


    # Reference ranges used as lightweight
    # domain / out-of-distribution gate.
    ranges = {}


    for column in numeric_features:

        series = pd.to_numeric(
            nid[column],
            errors="coerce",
        ).dropna()

        ranges[column] = {
            "p01":
                float(
                    series.quantile(
                        0.01
                    )
                ),

            "p99":
                float(
                    series.quantile(
                        0.99
                    )
                ),
        }


    async with engine.begin() as conn:

        # ====================================================
        # STANDARDIZED ENGINEERING PROFILE TABLE
        # ====================================================

        await conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS
                public.dam_barrage_engineering_profiles
                (
                    asset_id BIGINT PRIMARY KEY
                        REFERENCES public.assets(id)
                        ON DELETE CASCADE,

                    asset_code TEXT NOT NULL,

                    asset_type TEXT NOT NULL,

                    river TEXT,

                    structure_type TEXT,

                    model_structure_type TEXT,

                    height_m DOUBLE PRECISION,

                    length_m DOUBLE PRECISION,

                    gross_storage_mcm DOUBLE PRECISION,

                    live_storage_mcm DOUBLE PRECISION,

                    spillway_capacity_cumecs DOUBLE PRECISION,

                    design_flood_cumecs DOUBLE PRECISION,

                    gates INTEGER,

                    gate_width_m DOUBLE PRECISION,

                    gate_height_m DOUBLE PRECISION,

                    pier_thickness_m DOUBLE PRECISION,

                    pond_level_m DOUBLE PRECISION,

                    purpose TEXT,

                    completion_year INTEGER,

                    source_authority TEXT,

                    source_document TEXT,

                    source_url TEXT,

                    evidence_class TEXT,

                    quality_status TEXT,

                    feature_completeness DOUBLE PRECISION,

                    updated_at TIMESTAMPTZ NOT NULL
                        DEFAULT NOW()
                )
                """
            )
        )


        # ====================================================
        # CANONICAL ASSETS
        # ====================================================

        asset_rows = (
            await conn.execute(
                text(
                    """
                    SELECT
                        id,
                        asset_code,
                        name,
                        district,
                        built_year,
                        CAST(
                            asset_type AS TEXT
                        ) AS asset_type

                    FROM public.assets

                    WHERE
                        LOWER(
                            CAST(
                                asset_type AS TEXT
                            )
                        ) IN (
                            'dam',
                            'barrage'
                        )

                    ORDER BY id
                    """
                )
            )
        ).mappings().all()


        print()
        print("=" * 100)
        print("AP DAM + BARRAGE ASSETS")
        print("=" * 100)

        print(
            "Canonical assets:",
            len(asset_rows),
        )


        # ====================================================
        # DISCOVER EXISTING FEATURE SNAPSHOT TABLE
        # ====================================================

        snapshot_exists = bool(
            await conn.scalar(
                text(
                    """
                    SELECT EXISTS (
                        SELECT 1
                        FROM information_schema.tables
                        WHERE
                            table_schema='public'
                            AND table_name=
                            'dam_barrage_feature_snapshots'
                    )
                    """
                )
            )
        )


        snapshot_columns = set()

        snapshot_link = None

        snapshot_order = None


        if snapshot_exists:

            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT column_name

                        FROM information_schema.columns

                        WHERE
                            table_schema='public'
                            AND table_name=
                            'dam_barrage_feature_snapshots'
                        """
                    )
                )
            ).all()


            snapshot_columns = {
                row[0]
                for row in rows
            }


            for candidate in [
                "asset_id",
                "canonical_asset_id",
            ]:

                if candidate in snapshot_columns:

                    snapshot_link = candidate
                    break


            for candidate in [
                "snapshot_time",
                "observation_time",
                "updated_at",
                "created_at",
                "id",
            ]:

                if candidate in snapshot_columns:

                    snapshot_order = candidate
                    break


        # ====================================================
        # CREATE STANDARDIZED PROFILES
        # ====================================================

        profiles = []


        for asset in asset_rows:

            snapshot = {}


            if snapshot_link:

                order_clause = ""

                if snapshot_order:

                    order_clause = (
                        f' ORDER BY "{snapshot_order}" DESC NULLS LAST'
                    )


                query = (
                    "SELECT row_to_json(s)::text "
                    "FROM public.dam_barrage_feature_snapshots s "
                    f'WHERE s."{snapshot_link}" = :asset_id '
                    + order_clause
                    + " LIMIT 1"
                )


                raw_snapshot = await conn.scalar(
                    text(query),
                    {
                        "asset_id":
                            asset["id"],
                    },
                )


                if raw_snapshot:

                    try:

                        snapshot = flatten_json(
                            json.loads(
                                raw_snapshot
                            )
                        )

                    except Exception:

                        snapshot = {}


            row = {
                "asset_id":
                    int(
                        asset["id"]
                    ),

                "asset_code":
                    asset[
                        "asset_code"
                    ],

                "asset_type":
                    str(
                        asset[
                            "asset_type"
                        ]
                    ).lower(),

                "name":
                    asset[
                        "name"
                    ],

                "river":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "river",
                                "river_name",
                                "river_or_stream",
                            ],
                        )
                    ),

                "structure_type":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "structure_type",
                                "dam_type",
                                "type",
                            ],
                        )
                    ),

                "model_structure_type":
                    None,

                "height_m":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "height_m",
                                "dam_height_m",
                                "structure_height_m",
                                "max_height_m",
                            ],
                        )
                    ),

                "length_m":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "length_m",
                                "dam_length_m",
                                "crest_length_m",
                                "structure_length_m",
                                "actual_length_m",
                            ],
                        )
                    ),

                "gross_storage_mcm":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "gross_storage_mcm",
                                "gross_storage",
                                "storage_capacity_mcm",
                                "capacity_mcm",
                            ],
                        )
                    ),

                "live_storage_mcm":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "live_storage_mcm",
                                "live_storage",
                            ],
                        )
                    ),

                "spillway_capacity_cumecs":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "spillway_capacity_cumecs",
                                "spillway_capacity_m3s",
                                "max_discharge_cumecs",
                            ],
                        )
                    ),

                "design_flood_cumecs":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "design_flood_cumecs",
                                "design_flood_m3s",
                                "design_flood",
                            ],
                        )
                    ),

                "gates":
                    clean_int(
                        first_value(
                            snapshot,
                            [
                                "gates",
                                "gate_count",
                                "number_of_gates",
                                "num_gates",
                            ],
                        )
                    ),

                "gate_width_m":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "gate_width_m",
                            ],
                        )
                    ),

                "gate_height_m":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "gate_height_m",
                            ],
                        )
                    ),

                "pier_thickness_m":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "pier_thickness_m",
                            ],
                        )
                    ),

                "pond_level_m":
                    clean_number(
                        first_value(
                            snapshot,
                            [
                                "pond_level_m",
                            ],
                        )
                    ),

                "purpose":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "purpose",
                                "primary_purpose",
                            ],
                        )
                    ),

                "completion_year":
                    clean_int(
                        first_value(
                            snapshot,
                            [
                                "completion_year",
                                "year_completed",
                                "built_year",
                            ],
                        )
                    )
                    or clean_int(
                        asset[
                            "built_year"
                        ]
                    ),

                "source_authority":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "source_authority",
                                "authority",
                                "source_name",
                            ],
                        )
                    ),

                "source_document":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "source_document",
                                "document_name",
                            ],
                        )
                    ),

                "source_url":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "source_url",
                                "url",
                            ],
                        )
                    ),

                "evidence_class":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "evidence_class",
                            ],
                        )
                    ),

                "quality_status":
                    clean_text(
                        first_value(
                            snapshot,
                            [
                                "quality_status",
                                "quality_flag",
                            ],
                        )
                    ),
            }


            # ------------------------------------------------
            # CWC VERIFIED PRAKASAM OVERRIDE
            # ------------------------------------------------

            if (
                "prakasam barrage"
                in str(
                    asset["name"]
                ).lower()
                or asset[
                    "asset_code"
                ] == "AP_DAM_00001"
            ):

                for key, value in PRAKASAM_CWC.items():

                    row[key] = value


            if not row[
                "model_structure_type"
            ]:

                row[
                    "model_structure_type"
                ] = simple_dam_type(
                    row[
                        "structure_type"
                    ]
                )


            factual_fields = [
                row[
                    "completion_year"
                ],
                row[
                    "height_m"
                ],
                row[
                    "length_m"
                ],
                row[
                    "gross_storage_mcm"
                ],
                row[
                    "spillway_capacity_cumecs"
                ],
                row[
                    "model_structure_type"
                ],
                row[
                    "purpose"
                ],
            ]


            completeness = (
                sum(
                    value is not None
                    for value
                    in factual_fields
                )
                /
                len(
                    factual_fields
                )
            )


            row[
                "feature_completeness"
            ] = completeness


            profiles.append(
                row
            )


            await conn.execute(
                text(
                    """
                    INSERT INTO
                    public.dam_barrage_engineering_profiles
                    (
                        asset_id,
                        asset_code,
                        asset_type,
                        river,
                        structure_type,
                        model_structure_type,
                        height_m,
                        length_m,
                        gross_storage_mcm,
                        live_storage_mcm,
                        spillway_capacity_cumecs,
                        design_flood_cumecs,
                        gates,
                        gate_width_m,
                        gate_height_m,
                        pier_thickness_m,
                        pond_level_m,
                        purpose,
                        completion_year,
                        source_authority,
                        source_document,
                        source_url,
                        evidence_class,
                        quality_status,
                        feature_completeness,
                        updated_at
                    )
                    VALUES
                    (
                        :asset_id,
                        :asset_code,
                        :asset_type,
                        :river,
                        :structure_type,
                        :model_structure_type,
                        :height_m,
                        :length_m,
                        :gross_storage_mcm,
                        :live_storage_mcm,
                        :spillway_capacity_cumecs,
                        :design_flood_cumecs,
                        :gates,
                        :gate_width_m,
                        :gate_height_m,
                        :pier_thickness_m,
                        :pond_level_m,
                        :purpose,
                        :completion_year,
                        :source_authority,
                        :source_document,
                        :source_url,
                        :evidence_class,
                        :quality_status,
                        :feature_completeness,
                        NOW()
                    )

                    ON CONFLICT (asset_id)
                    DO UPDATE SET
                        asset_code =
                            EXCLUDED.asset_code,

                        asset_type =
                            EXCLUDED.asset_type,

                        river =
                            EXCLUDED.river,

                        structure_type =
                            EXCLUDED.structure_type,

                        model_structure_type =
                            EXCLUDED.model_structure_type,

                        height_m =
                            EXCLUDED.height_m,

                        length_m =
                            EXCLUDED.length_m,

                        gross_storage_mcm =
                            EXCLUDED.gross_storage_mcm,

                        live_storage_mcm =
                            EXCLUDED.live_storage_mcm,

                        spillway_capacity_cumecs =
                            EXCLUDED.spillway_capacity_cumecs,

                        design_flood_cumecs =
                            EXCLUDED.design_flood_cumecs,

                        gates =
                            EXCLUDED.gates,

                        gate_width_m =
                            EXCLUDED.gate_width_m,

                        gate_height_m =
                            EXCLUDED.gate_height_m,

                        pier_thickness_m =
                            EXCLUDED.pier_thickness_m,

                        pond_level_m =
                            EXCLUDED.pond_level_m,

                        purpose =
                            EXCLUDED.purpose,

                        completion_year =
                            EXCLUDED.completion_year,

                        source_authority =
                            EXCLUDED.source_authority,

                        source_document =
                            EXCLUDED.source_document,

                        source_url =
                            EXCLUDED.source_url,

                        evidence_class =
                            EXCLUDED.evidence_class,

                        quality_status =
                            EXCLUDED.quality_status,

                        feature_completeness =
                            EXCLUDED.feature_completeness,

                        updated_at =
                            NOW()
                    """
                ),
                row,
            )


        ap = pd.DataFrame(
            profiles
        )


        profile_path = (
            OUT
            / "ap_dam_barrage_profiles.csv"
        )


        ap.to_csv(
            profile_path,
            index=False,
        )


        # ====================================================
        # AP -> NID SHARED FEATURE CROSSWALK
        # ====================================================

        inference = pd.DataFrame(
            {
                "age_years":
                    ap[
                        "completion_year"
                    ].apply(
                        lambda value:
                            (
                                NOW.year
                                - int(value)
                            )
                            if pd.notna(value)
                            else np.nan
                    ),

                "dam_height_ft":
                    ap[
                        "height_m"
                    ].apply(
                        lambda x:
                            m_to_ft(x)
                            if pd.notna(x)
                            else np.nan
                    ),

                "dam_length_ft":
                    ap[
                        "length_m"
                    ].apply(
                        lambda x:
                            m_to_ft(x)
                            if pd.notna(x)
                            else np.nan
                    ),

                "max_storage_acft":
                    ap[
                        "gross_storage_mcm"
                    ].apply(
                        lambda x:
                            mcm_to_acre_ft(x)
                            if pd.notna(x)
                            else np.nan
                    ),

                "max_discharge_cfs":
                    ap[
                        "spillway_capacity_cumecs"
                    ].apply(
                        lambda x:
                            cumecs_to_cfs(x)
                            if pd.notna(x)
                            else np.nan
                    ),

                "dam_type":
                    ap[
                        "model_structure_type"
                    ].apply(
                        simple_dam_type
                    ),

                "purpose":
                    ap[
                        "purpose"
                    ].apply(
                        simple_purpose
                    ),
            }
        )


        # ====================================================
        # OOD + COMPLETENESS GATES
        # ====================================================

        ood_counts = []


        for index in range(
            len(inference)
        ):

            count = 0

            for column in numeric_features:

                value = inference.iloc[
                    index
                ][column]

                if pd.isna(
                    value
                ):
                    continue

                low = ranges[
                    column
                ][
                    "p01"
                ]

                high = ranges[
                    column
                ][
                    "p99"
                ]

                if (
                    float(value) < low
                    or float(value) > high
                ):
                    count += 1

            ood_counts.append(
                count
            )


        ap[
            "ood_feature_count"
        ] = ood_counts


        ap[
            "eligible_for_transfer"
        ] = (
            (
                ap[
                    "feature_completeness"
                ] >= 0.57
            )
            &
            (
                ap[
                    "ood_feature_count"
                ] <= 2
            )
            &
            (
                ap[
                    "completion_year"
                ].notna()
            )
            &
            (
                ap[
                    "height_m"
                ].notna()
                |
                ap[
                    "length_m"
                ].notna()
            )
        )


        # ====================================================
        # MODEL INFERENCE
        # ====================================================

        risk_prob = risk_model.predict_proba(
            inference
        )[:, 1]


        health_prob = health_model.predict_proba(
            inference
        )


        health_classes = health_model.named_steps[
            "model"
        ].classes_


        condition_health_index = {
            "SATISFACTORY":
                90.0,

            "FAIR":
                70.0,

            "POOR":
                40.0,

            "UNSATISFACTORY":
                15.0,
        }


        health_scores = []


        for probabilities in health_prob:

            value = 0.0

            for class_name, probability in zip(
                health_classes,
                probabilities,
            ):

                value += (
                    condition_health_index[
                        str(
                            class_name
                        )
                    ]
                    * float(
                        probability
                    )
                )

            health_scores.append(
                value
            )


        predicted_condition = health_model.predict(
            inference
        )


        medium_threshold = metrics[
            "risk"
        ][
            "medium_threshold"
        ]


        high_threshold = metrics[
            "risk"
        ][
            "high_threshold"
        ]


        ap[
            "risk_score"
        ] = (
            risk_prob
            * 100.0
        )


        ap[
            "risk_level"
        ] = [
            risk_level(
                float(probability),
                medium_threshold,
                high_threshold,
            )
            for probability
            in risk_prob
        ]


        ap[
            "health_score"
        ] = health_scores


        ap[
            "predicted_condition"
        ] = predicted_condition


        # ====================================================
        # PERSIST ONLY ELIGIBLE RESEARCH TRANSFER PREDICTIONS
        # ====================================================

        persisted_health = 0
        persisted_risk = 0
        abstained = 0


        for index, row in ap.iterrows():

            if not bool(
                row[
                    "eligible_for_transfer"
                ]
            ):

                abstained += 1
                continue


            asset_id = int(
                row[
                    "asset_id"
                ]
            )


            factors = {
                "prediction_semantics": {
                    "risk":
                        (
                            "Calibrated probability of POOR or "
                            "UNSATISFACTORY condition under a "
                            "USACE NID -> Andhra Pradesh "
                            "research-transfer model. "
                            "Not probability of collapse."
                        ),

                    "health":
                        (
                            "SIMRAS research condition index "
                            "derived from expected probabilities "
                            "of official NID condition classes. "
                            "This is not an official CWC health score."
                        ),

                    "rul":
                        "WITHHELD",
                },

                "training_source":
                    "USACE National Inventory of Dams",

                "ap_engineering_source":
                    row.get(
                        "source_authority"
                    ),

                "model_status":
                    "RESEARCH_TRANSFER",

                "ap_ground_truth_validated":
                    False,

                "feature_completeness":
                    float(
                        row[
                            "feature_completeness"
                        ]
                    ),

                "ood_feature_count":
                    int(
                        row[
                            "ood_feature_count"
                        ]
                    ),

                "health_condition_mapping": {
                    "SATISFACTORY":
                        90,

                    "FAIR":
                        70,

                    "POOR":
                        40,

                    "UNSATISFACTORY":
                        15,
                },

                "recommendations": [
                    (
                        "Use the prediction as research-transfer "
                        "decision support until an Andhra Pradesh "
                        "structural inspection is available."
                    ),
                    (
                        "Keep reservoir level, discharge and flood "
                        "observations separate from structural "
                        "condition probability."
                    ),
                    (
                        "Perform documented field inspection before "
                        "engineering intervention decisions."
                    ),
                ],
            }


            factors_json = json.dumps(
                factors
            )


            async def upsert_prediction(
                target,
                value,
                predicted_class,
            ):

                existing = await conn.scalar(
                    text(
                        """
                        SELECT id

                        FROM public.predictions

                        WHERE
                            asset_id = :asset_id
                            AND LOWER(target) =
                                LOWER(:target)
                            AND model_version =
                                :model_version

                        ORDER BY
                            prediction_time DESC,
                            id DESC

                        LIMIT 1
                        """
                    ),
                    {
                        "asset_id":
                            asset_id,

                        "target":
                            target,

                        "model_version":
                            MODEL_VERSION,
                    },
                )


                parameters = {
                    "asset_id":
                        asset_id,

                    "target":
                        target,

                    "value":
                        float(value),

                    "predicted_class":
                        str(
                            predicted_class
                        ),

                    "model_version":
                        MODEL_VERSION,

                    "feature_version":
                        FEATURE_VERSION,

                    "status":
                        "RESEARCH_TRANSFER",

                    "factors":
                        factors_json,
                }


                if existing:

                    await conn.execute(
                        text(
                            """
                            UPDATE public.predictions

                            SET
                                prediction_time =
                                    NOW(),

                                value =
                                    :value,

                                predicted_class =
                                    :predicted_class,

                                confidence_score =
                                    NULL,

                                lower_bound =
                                    NULL,

                                upper_bound =
                                    NULL,

                                feature_version =
                                    :feature_version,

                                status =
                                    :status,

                                factors =
                                    CAST(
                                        :factors
                                        AS jsonb
                                    )

                            WHERE id =
                                :prediction_id
                            """
                        ),
                        {
                            **parameters,
                            "prediction_id":
                                existing,
                        },
                    )

                else:

                    await conn.execute(
                        text(
                            """
                            INSERT INTO
                            public.predictions
                            (
                                asset_id,
                                prediction_time,
                                target,
                                value,
                                predicted_class,
                                lower_bound,
                                upper_bound,
                                confidence_score,
                                model_version,
                                feature_version,
                                status,
                                factors
                            )
                            VALUES
                            (
                                :asset_id,
                                NOW(),
                                :target,
                                :value,
                                :predicted_class,
                                NULL,
                                NULL,
                                NULL,
                                :model_version,
                                :feature_version,
                                :status,
                                CAST(
                                    :factors
                                    AS jsonb
                                )
                            )
                            """
                        ),
                        parameters,
                    )


            await upsert_prediction(
                "risk",
                row[
                    "risk_score"
                ],
                row[
                    "risk_level"
                ],
            )


            persisted_risk += 1


            await upsert_prediction(
                "health",
                row[
                    "health_score"
                ],
                row[
                    "predicted_condition"
                ],
            )


            persisted_health += 1


        # ====================================================
        # FINAL DB VERIFICATION
        # ====================================================

        stored = (
            await conn.execute(
                text(
                    """
                    SELECT
                        p.target,
                        p.status,
                        COUNT(*) AS total

                    FROM public.predictions p

                    JOIN public.assets a
                        ON a.id = p.asset_id

                    WHERE
                        p.model_version =
                            :model_version

                        AND LOWER(
                            CAST(
                                a.asset_type AS TEXT
                            )
                        ) IN (
                            'dam',
                            'barrage'
                        )

                    GROUP BY
                        p.target,
                        p.status

                    ORDER BY
                        p.target,
                        p.status
                    """
                ),
                {
                    "model_version":
                        MODEL_VERSION,
                },
            )
        ).mappings().all()


        prakasam = (
            await conn.execute(
                text(
                    """
                    SELECT
                        a.asset_code,
                        a.name,

                        d.river,
                        d.structure_type,
                        d.height_m,
                        d.length_m,
                        d.gates,
                        d.gate_width_m,
                        d.gate_height_m,
                        d.pier_thickness_m,
                        d.pond_level_m,
                        d.design_flood_cumecs,
                        d.spillway_capacity_cumecs,
                        d.completion_year,
                        d.source_authority,

                        p.target,
                        p.value,
                        p.predicted_class,
                        p.status,
                        p.confidence_score

                    FROM public.assets a

                    JOIN
                    public.dam_barrage_engineering_profiles d
                        ON d.asset_id = a.id

                    LEFT JOIN public.predictions p
                        ON p.asset_id = a.id
                        AND p.model_version =
                            :model_version

                    WHERE
                        LOWER(a.name)
                        LIKE '%prakasam barrage%'

                    ORDER BY p.target
                    """
                ),
                {
                    "model_version":
                        MODEL_VERSION,
                },
            )
        ).mappings().all()


        # ====================================================
        # AUDIT
        # ====================================================

        ap.to_csv(
            OUT
            / "ap_dam_barrage_inference.csv",
            index=False,
        )


        summary = {
            "phase":
                "ML-7",

            "model_version":
                MODEL_VERSION,

            "feature_version":
                FEATURE_VERSION,

            "canonical_assets":
                int(
                    len(ap)
                ),

            "eligible":
                int(
                    ap[
                        "eligible_for_transfer"
                    ].sum()
                ),

            "abstained":
                int(
                    (
                        ~ap[
                            "eligible_for_transfer"
                        ]
                    ).sum()
                ),

            "risk_predictions_persisted":
                persisted_risk,

            "health_predictions_persisted":
                persisted_health,

            "confidence_policy":
                "WITHHELD_PENDING_AP_VALIDATION",

            "rul_policy":
                "WITHHELD_NO_LONGITUDINAL_AP_DETERIORATION_LABELS",

            "hydrology_policy":
                (
                    "HYDROLOGY_IS_OBSERVATION_NOT_"
                    "STRUCTURAL_FAILURE_PROBABILITY"
                ),

            "metrics":
                metrics,

            "stored_counts": [
                dict(
                    item
                )
                for item
                in stored
            ],

            "prakasam":
                [
                    dict(
                        item
                    )
                    for item
                    in prakasam
                ],
        }


        (
            OUT
            / "ml7_summary.json"
        ).write_text(
            json.dumps(
                summary,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )


        (
            ROOT
            / "LATEST_ML7.txt"
        ).write_text(
            str(
                OUT
            ),
            encoding="utf-8",
        )


        # ====================================================
        # OUTPUT
        # ====================================================

        print()
        print("=" * 100)
        print("ML-7 AP INFERENCE")
        print("=" * 100)

        print(
            "Canonical dams+barrages :",
            len(ap),
        )

        print(
            "Eligible predictions    :",
            int(
                ap[
                    "eligible_for_transfer"
                ].sum()
            ),
        )

        print(
            "Abstained               :",
            int(
                (
                    ~ap[
                        "eligible_for_transfer"
                    ]
                ).sum()
            ),
        )

        print(
            "Health persisted        :",
            persisted_health,
        )

        print(
            "Risk persisted          :",
            persisted_risk,
        )


        print()
        print("=" * 100)
        print("PRAKASAM BARRAGE")
        print("=" * 100)


        if not prakasam:

            print(
                "Prakasam Barrage not found."
            )

        else:

            for item in prakasam:

                print(
                    json.dumps(
                        dict(item),
                        indent=2,
                        default=str,
                    )
                )


        print()
        print("=" * 100)
        print("KPI POLICY")
        print("=" * 100)

        print(
            "Health Score : RESEARCH_TRANSFER "
            "where eligibility gates pass"
        )

        print(
            "Risk Score   : RESEARCH_TRANSFER "
            "where eligibility gates pass"
        )

        print(
            "Risk Level   : LOW / MEDIUM / HIGH "
            "from trained model thresholds"
        )

        print(
            "Confidence   : WITHHELD "
            "(AP ground-truth validation pending)"
        )

        print(
            "RUL          : WITHHELD "
            "(no validated longitudinal AP deterioration target)"
        )

        print()
        print(
            "Flood / discharge values remain "
            "HYDROLOGY OBSERVATIONS."
        )

        print(
            "They are NOT structural failure probability."
        )

        print()
        print(
            "Model folder:",
            MODEL_DIR,
        )

        print(
            "Audit folder:",
            OUT,
        )


    await engine.dispose()


asyncio.run(
    main()
)