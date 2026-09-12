import asyncio
import json
import math
import os
import re

from datetime import date

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path(
    "/tmp/ml9b"
)

SOURCES = (
    ROOT
    / "sources"
)

MANIFEST = (
    ROOT
    / "source_manifest.json"
)

OUT = Path(
    "/tmp/ml9b4/output"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


ASOF = pd.Timestamp(
    "2026-09-04"
).normalize()


LEVEL_MAX_MAE = 1.0


def normalize(value):

    value = str(
        value or ""
    ).upper()

    value = re.sub(
        r"[^A-Z0-9]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def db_url():

    value = os.environ[
        "DATABASE_URL"
    ]

    if value.startswith(
        "postgresql://"
    ):

        value = value.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    return value


# ============================================================
# VERIFY WORKSPACE
# ============================================================

if not MANIFEST.exists():

    raise RuntimeError(
        "Existing ML-9B manifest not found."
    )


manifest = json.loads(
    MANIFEST.read_text(
        encoding="utf-8-sig"
    )
)


print(
    "SOURCE_MANIFEST_ROWS =",
    len(manifest),
)


if len(manifest) != 8:

    raise RuntimeError(
        "Expected 8 source definitions."
    )


# ============================================================
# LOAD REAL NWDP OBSERVATIONS
# ============================================================

level_frames = []
storage_frames = []


for item in manifest:

    filename = item[
        "container_filename"
    ]

    source = (
        SOURCES
        / filename
    )


    if not source.exists():

        raise RuntimeError(
            "Missing source: "
            + filename
        )


    frame = pd.read_csv(
        source,
        low_memory=False,
    )


    target_column = item[
        "target_column"
    ]


    required = [
        "Station",
        "Data Acquisition Time",
        target_column,
    ]


    missing = [
        column
        for column in required
        if column not in frame.columns
    ]


    if missing:

        raise RuntimeError(
            f"{filename} missing columns: "
            f"{missing}"
        )


    parsed = pd.DataFrame(
        {
            "station":
                frame[
                    "Station"
                ].fillna(
                    ""
                ),

            "station_key":
                frame[
                    "Station"
                ].fillna(
                    ""
                ).map(
                    normalize
                ),

            "date":
                pd.to_datetime(
                    frame[
                        "Data Acquisition Time"
                    ],
                    dayfirst=True,
                    errors="coerce",
                ).dt.normalize(),

            "value":
                pd.to_numeric(
                    frame[
                        target_column
                    ],
                    errors="coerce",
                ),
        }
    )


    parsed = parsed[
        parsed[
            "station_key"
        ].ne("")
    ]


    parsed = parsed[
        parsed[
            "date"
        ].notna()
    ]


    parsed = parsed[
        parsed[
            "date"
        ] <= ASOF
    ]


    parsed = parsed[
        parsed[
            "value"
        ].notna()
    ]


    if item[
        "kind"
    ] == "LEVEL":

        level_frames.append(
            parsed
        )

    elif item[
        "kind"
    ] == "STORAGE":

        storage_frames.append(
            parsed
        )


if not level_frames:

    raise RuntimeError(
        "No real level observations."
    )


if not storage_frames:

    raise RuntimeError(
        "No real storage observations."
    )


level = pd.concat(
    level_frames,
    ignore_index=True,
)


storage = pd.concat(
    storage_frames,
    ignore_index=True,
)


# ============================================================
# DEDUPLICATE COPIED DATASETS
#
# Same NWDP files exist under multiple project paths.
# Keep one station/date observation.
# ============================================================

level = (
    level
    .sort_values(
        [
            "station_key",
            "date",
        ]
    )
    .drop_duplicates(
        [
            "station_key",
            "date",
        ],
        keep="last",
    )
)


storage = (
    storage
    .sort_values(
        [
            "station_key",
            "date",
        ]
    )
    .drop_duplicates(
        [
            "station_key",
            "date",
        ],
        keep="last",
    )
)


print(
    "REAL_LEVEL_OBSERVATIONS =",
    len(level),
)

print(
    "REAL_STORAGE_OBSERVATIONS =",
    len(storage),
)


# ============================================================
# CANONICAL ASSET IDENTITIES
# ============================================================

async def load_assets():

    engine = create_async_engine(
        db_url()
    )


    async with engine.connect() as conn:

        rows = (
            await conn.execute(
                text(
                    """
                    SELECT
                        asset_code,
                        name,
                        district,
                        asset_type,
                        identity_status

                    FROM public.assets

                    WHERE
                        LOWER(
                            CAST(
                                asset_type AS TEXT
                            )
                        )
                        IN (
                            'dam',
                            'barrage'
                        )

                    ORDER BY asset_code
                    """
                )
            )
        ).mappings().all()


    await engine.dispose()


    return [
        dict(row)
        for row in rows
    ]


# ============================================================
# FEATURE SET
# ============================================================

def build_features(
    merged
):

    merged = (
        merged
        .sort_values(
            "date"
        )
        .drop_duplicates(
            "date"
        )
        .set_index(
            "date"
        )
    )


    full_index = pd.date_range(
        merged.index.min(),
        merged.index.max(),
        freq="D",
    )


    series = merged.reindex(
        full_index
    )


    series.index.name = (
        "date"
    )


    features = pd.DataFrame(
        index=series.index
    )


    features[
        "level_current"
    ] = series[
        "level"
    ]


    features[
        "storage_current"
    ] = series[
        "storage"
    ]


    for variable in [
        "level",
        "storage",
    ]:

        for lag in [
            1,
            2,
            3,
            7,
            14,
        ]:

            features[
                f"{variable}_lag_{lag}"
            ] = series[
                variable
            ].shift(
                lag
            )


        for window in [
            3,
            7,
            14,
        ]:

            features[
                f"{variable}_mean_{window}"
            ] = (
                series[
                    variable
                ]
                .rolling(
                    window,
                    min_periods=window,
                )
                .mean()
            )


    doy = (
        features.index.dayofyear
    )


    features[
        "day_sin"
    ] = np.sin(
        2
        * np.pi
        * doy
        / 365.25
    )


    features[
        "day_cos"
    ] = np.cos(
        2
        * np.pi
        * doy
        / 365.25
    )


    features[
        "target_level"
    ] = series[
        "level"
    ].shift(
        -1
    )


    features[
        "target_storage"
    ] = series[
        "storage"
    ].shift(
        -1
    )


    feature_columns = [
        column
        for column in features.columns
        if not column.startswith(
            "target_"
        )
    ]


    train = features.dropna(
        subset=(
            feature_columns
            + [
                "target_level",
                "target_storage",
            ]
        )
    ).copy()


    latest_candidates = features.dropna(
        subset=feature_columns
    )


    if latest_candidates.empty:

        return (
            train,
            None,
            feature_columns,
        )


    latest = latest_candidates.iloc[
        -1
    ].copy()


    return (
        train,
        latest,
        feature_columns,
    )


# ============================================================
# BACKTEST TARGET
# ============================================================

def backtest(
    train,
    feature_columns,
    target,
    current,
    allow_ml,
):

    count = len(
        train
    )


    if count < 30:

        return {
            "status":
                "WITHHELD_INSUFFICIENT_BACKTEST",

            "method":
                None,

            "chosen_mae":
                None,

            "baseline_mae":
                None,

            "ml_mae":
                None,

            "improvement":
                None,
        }


    test_size = max(
        14,
        int(
            math.ceil(
                count
                * 0.15
            )
        ),
    )


    if count - test_size < 30:

        return {
            "status":
                "WITHHELD_INSUFFICIENT_TRAIN",

            "method":
                None,

            "chosen_mae":
                None,

            "baseline_mae":
                None,

            "ml_mae":
                None,

            "improvement":
                None,
        }


    training = train.iloc[
        :-test_size
    ]


    testing = train.iloc[
        -test_size:
    ]


    actual = testing[
        target
    ].to_numpy()


    baseline_prediction = testing[
        current
    ].to_numpy()


    baseline_mae = float(
        mean_absolute_error(
            actual,
            baseline_prediction,
        )
    )


    selected_method = (
        "PERSISTENCE"
    )

    selected_mae = (
        baseline_mae
    )

    ml_mae = None
    improvement = None


    if allow_ml:

        model = ExtraTreesRegressor(
            n_estimators=300,
            min_samples_leaf=2,
            max_features=0.85,
            random_state=42,
            n_jobs=-1,
        )


        model.fit(
            training[
                feature_columns
            ],
            training[
                target
            ],
        )


        prediction = model.predict(
            testing[
                feature_columns
            ]
        )


        ml_mae = float(
            mean_absolute_error(
                actual,
                prediction,
            )
        )


        if baseline_mae > 0:

            improvement = float(
                (
                    baseline_mae
                    - ml_mae
                )
                / baseline_mae
            )

        else:

            improvement = 0.0


        if (
            baseline_mae > 0
            and improvement >= 0.02
        ):

            selected_method = (
                "EXTRA_TREES"
            )

            selected_mae = (
                ml_mae
            )


    return {
        "status":
            (
                "VALIDATED_OPERATIONAL_ML"
                if selected_method
                == "EXTRA_TREES"
                else
                "VALIDATED_PERSISTENCE_BASELINE"
            ),

        "method":
            selected_method,

        "chosen_mae":
            float(
                selected_mae
            ),

        "baseline_mae":
            float(
                baseline_mae
            ),

        "ml_mae":
            (
                float(
                    ml_mae
                )
                if ml_mae
                is not None
                else None
            ),

        "improvement":
            improvement,

        "train_rows":
            len(
                training
            ),

        "test_rows":
            len(
                testing
            ),
    }


# ============================================================
# FORECAST TARGET
# ============================================================

def predict_target(
    train,
    latest,
    feature_columns,
    validation,
    target,
    current,
):

    method = validation.get(
        "method"
    )


    if method is None:

        return None


    if method == "PERSISTENCE":

        return float(
            latest[
                current
            ]
        )


    model = ExtraTreesRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        max_features=0.85,
        random_state=42,
        n_jobs=-1,
    )


    model.fit(
        train[
            feature_columns
        ],
        train[
            target
        ],
    )


    input_frame = pd.DataFrame(
        [
            latest[
                feature_columns
            ].to_dict()
        ]
    )


    return float(
        model.predict(
            input_frame
        )[0]
    )


# ============================================================
# DB TABLE
# ============================================================

DDL = """
CREATE TABLE IF NOT EXISTS
public.dam_barrage_operational_predictions_v1
(
    asset_code TEXT PRIMARY KEY,

    station_name TEXT NOT NULL,

    observation_date DATE NOT NULL,

    prediction_date DATE NOT NULL,

    observed_level_m DOUBLE PRECISION,

    predicted_level_m DOUBLE PRECISION,

    observed_storage_mcm DOUBLE PRECISION,

    predicted_storage_mcm DOUBLE PRECISION,

    level_status TEXT NOT NULL,

    storage_status TEXT NOT NULL,

    level_test_mae DOUBLE PRECISION,

    level_baseline_mae DOUBLE PRECISION,

    storage_test_mae DOUBLE PRECISION,

    storage_baseline_mae DOUBLE PRECISION,

    confidence DOUBLE PRECISION,

    model_status TEXT NOT NULL,

    prediction_semantics TEXT NOT NULL,

    source_name TEXT NOT NULL,

    forecast_method_level TEXT,

    forecast_method_storage TEXT,

    history_days INTEGER,

    test_rows INTEGER,

    generated_at TIMESTAMPTZ
        NOT NULL
        DEFAULT NOW()
);
"""


ALTER = [
    """
    ALTER TABLE
    public.dam_barrage_operational_predictions_v1
    ADD COLUMN IF NOT EXISTS
    forecast_method_level TEXT
    """,

    """
    ALTER TABLE
    public.dam_barrage_operational_predictions_v1
    ADD COLUMN IF NOT EXISTS
    forecast_method_storage TEXT
    """,

    """
    ALTER TABLE
    public.dam_barrage_operational_predictions_v1
    ADD COLUMN IF NOT EXISTS
    history_days INTEGER
    """,

    """
    ALTER TABLE
    public.dam_barrage_operational_predictions_v1
    ADD COLUMN IF NOT EXISTS
    test_rows INTEGER
    """,
]


# ============================================================
# MAIN
# ============================================================

async def main():

    assets = await load_assets()


    asset_names = {}


    for asset in assets:

        key = normalize(
            asset[
                "name"
            ]
        )


        if not key:
            continue


        asset_names.setdefault(
            key,
            [],
        ).append(
            asset
        )


    source_station_names = {}


    for frame in [
        level,
        storage,
    ]:

        for _, row in frame.iterrows():

            source_station_names[
                row[
                    "station_key"
                ]
            ] = str(
                row[
                    "station"
                ]
            )


    exact = {}


    for key, station in source_station_names.items():

        candidates = asset_names.get(
            key,
            [],
        )


        if len(candidates) == 1:

            exact[
                key
            ] = {
                "station":
                    station,

                "asset":
                    candidates[
                        0
                    ],
            }


    print(
        "SOURCE_STATIONS =",
        len(
            source_station_names
        ),
    )

    print(
        "EXACT_CANONICAL_STATIONS =",
        len(
            exact
        ),
    )


    results = []


    for station_key, mapping in sorted(
        exact.items()
    ):

        asset = mapping[
            "asset"
        ]


        station_level = level[
            level[
                "station_key"
            ]
            == station_key
        ][
            [
                "date",
                "value",
            ]
        ].rename(
            columns={
                "value":
                    "level"
            }
        )


        station_storage = storage[
            storage[
                "station_key"
            ]
            == station_key
        ][
            [
                "date",
                "value",
            ]
        ].rename(
            columns={
                "value":
                    "storage"
            }
        )


        merged = pd.merge(
            station_level,
            station_storage,
            on="date",
            how="inner",
        )


        merged = (
            merged
            .sort_values(
                "date"
            )
            .drop_duplicates(
                "date"
            )
        )


        common_days = len(
            merged
        )


        print()
        print(
            "================================================"
        )

        print(
            "ASSET =",
            asset[
                "asset_code"
            ],
            asset[
                "name"
            ],
        )

        print(
            "COMMON_REAL_DAYS =",
            common_days,
        )


        if common_days < 30:

            result = {
                "asset_code":
                    asset[
                        "asset_code"
                    ],

                "asset_name":
                    asset[
                        "name"
                    ],

                "station":
                    mapping[
                        "station"
                    ],

                "history_days":
                    common_days,

                "model_status":
                    "WITHHELD_LESS_THAN_30_DAYS",
            }


            results.append(
                result
            )

            print(
                "FINAL_STATUS =",
                result[
                    "model_status"
                ],
            )

            continue


        train, latest, feature_columns = (
            build_features(
                merged
            )
        )


        if latest is None:

            result = {
                "asset_code":
                    asset[
                        "asset_code"
                    ],

                "asset_name":
                    asset[
                        "name"
                    ],

                "station":
                    mapping[
                        "station"
                    ],

                "history_days":
                    common_days,

                "model_status":
                    "WITHHELD_NO_COMPLETE_FEATURE_WINDOW",
            }


            results.append(
                result
            )

            print(
                "FINAL_STATUS =",
                result[
                    "model_status"
                ],
            )

            continue


        observation_date = pd.Timestamp(
            latest.name
        ).normalize()


        prediction_date = (
            observation_date
            + pd.Timedelta(
                days=1
            )
        )


        age_days = int(
            (
                ASOF
                - observation_date
            ).days
        )


        allow_ml = (
            common_days >= 90
        )


        level_validation = backtest(
            train,
            feature_columns,
            "target_level",
            "level_current",
            allow_ml,
        )


        storage_validation = backtest(
            train,
            feature_columns,
            "target_storage",
            "storage_current",
            allow_ml,
        )


        observed_level = float(
            latest[
                "level_current"
            ]
        )


        observed_storage = float(
            latest[
                "storage_current"
            ]
        )


        level_prediction = predict_target(
            train,
            latest,
            feature_columns,
            level_validation,
            "target_level",
            "level_current",
        )


        storage_prediction = predict_target(
            train,
            latest,
            feature_columns,
            storage_validation,
            "target_storage",
            "storage_current",
        )


        # ====================================================
        # PRODUCTION QUALITY GATES
        # ====================================================

        level_mae = level_validation.get(
            "chosen_mae"
        )


        storage_mae = storage_validation.get(
            "chosen_mae"
        )


        storage_limit = max(
            0.10,
            abs(
                observed_storage
            )
            * 0.02,
        )


        level_reportable = (
            level_mae
            is not None
            and level_mae
            <= LEVEL_MAX_MAE
        )


        storage_reportable = (
            storage_mae
            is not None
            and storage_mae
            <= storage_limit
        )


        if age_days > 14:

            level_reportable = False
            storage_reportable = False


            level_status = (
                "WITHHELD_STALE_OBSERVATION"
            )

            storage_status = (
                "WITHHELD_STALE_OBSERVATION"
            )


        else:

            level_status = (
                level_validation[
                    "status"
                ]
                if level_reportable
                else
                "WITHHELD_VALIDATION_ERROR_TOO_HIGH"
            )


            storage_status = (
                storage_validation[
                    "status"
                ]
                if storage_reportable
                else
                "WITHHELD_VALIDATION_ERROR_TOO_HIGH"
            )


        if not level_reportable:

            level_prediction = None


        if not storage_reportable:

            storage_prediction = None


        if (
            not level_reportable
            and not storage_reportable
        ):

            if age_days > 14:

                overall_status = (
                    "WITHHELD_STALE_OBSERVATION"
                )

            else:

                overall_status = (
                    "WITHHELD_QUALITY_GATE"
                )


        else:

            uses_ml = (
                (
                    level_reportable
                    and level_validation[
                        "method"
                    ]
                    == "EXTRA_TREES"
                )
                or
                (
                    storage_reportable
                    and storage_validation[
                        "method"
                    ]
                    == "EXTRA_TREES"
                )
            )


            overall_status = (
                "VALIDATED_OPERATIONAL_ML"
                if uses_ml
                else
                "VALIDATED_PERSISTENCE_BASELINE"
            )


        # Confidence only for reportable ML.
        confidence = None


        if overall_status == "VALIDATED_OPERATIONAL_ML":

            improvements = []


            for validation, reportable in [
                (
                    level_validation,
                    level_reportable,
                ),
                (
                    storage_validation,
                    storage_reportable,
                ),
            ]:

                if (
                    reportable
                    and validation.get(
                        "method"
                    )
                    == "EXTRA_TREES"
                ):

                    improvement = validation.get(
                        "improvement"
                    )


                    if improvement is not None:

                        improvements.append(
                            max(
                                0.0,
                                min(
                                    1.0,
                                    float(
                                        improvement
                                    ),
                                ),
                            )
                        )


            if improvements:

                confidence = min(
                    0.90,
                    0.65
                    + 0.20
                    * (
                        sum(
                            improvements
                        )
                        / len(
                            improvements
                        )
                    ),
                )


        result = {
            "asset_code":
                asset[
                    "asset_code"
                ],

            "asset_name":
                asset[
                    "name"
                ],

            "station":
                mapping[
                    "station"
                ],

            "history_days":
                common_days,

            "observation_date":
                observation_date.date().isoformat(),

            "prediction_date":
                prediction_date.date().isoformat(),

            "forecast_age_days":
                age_days,

            "observed_level":
                observed_level,

            "predicted_level":
                level_prediction,

            "level_method":
                level_validation.get(
                    "method"
                ),

            "level_baseline_mae":
                level_validation.get(
                    "baseline_mae"
                ),

            "level_ml_mae":
                level_validation.get(
                    "ml_mae"
                ),

            "level_display_mae":
                level_mae,

            "level_reportable":
                bool(
                    level_reportable
                ),

            "level_status":
                level_status,

            "observed_storage":
                observed_storage,

            "predicted_storage":
                storage_prediction,

            "storage_method":
                storage_validation.get(
                    "method"
                ),

            "storage_baseline_mae":
                storage_validation.get(
                    "baseline_mae"
                ),

            "storage_ml_mae":
                storage_validation.get(
                    "ml_mae"
                ),

            "storage_display_mae":
                storage_mae,

            "storage_limit":
                storage_limit,

            "storage_reportable":
                bool(
                    storage_reportable
                ),

            "storage_status":
                storage_status,

            "model_status":
                overall_status,

            "confidence":
                confidence,

            "test_rows":
                min(
                    int(
                        level_validation.get(
                            "test_rows",
                            0,
                        )
                    ),
                    int(
                        storage_validation.get(
                            "test_rows",
                            0,
                        )
                    ),
                ),
        }


        results.append(
            result
        )


        print(
            "OBSERVATION_DATE =",
            result[
                "observation_date"
            ],
        )

        print(
            "DATA_AGE_DAYS =",
            age_days,
        )

        print()
        print(
            "LEVEL_METHOD =",
            result[
                "level_method"
            ],
        )

        print(
            "LEVEL_BASELINE_MAE =",
            result[
                "level_baseline_mae"
            ],
        )

        print(
            "LEVEL_ML_MAE =",
            result[
                "level_ml_mae"
            ],
        )

        print(
            "LEVEL_CHOSEN_MAE =",
            result[
                "level_display_mae"
            ],
        )

        print(
            "LEVEL_REPORTABLE =",
            result[
                "level_reportable"
            ],
        )

        print(
            "PREDICTED_LEVEL =",
            result[
                "predicted_level"
            ],
        )


        print()
        print(
            "STORAGE_METHOD =",
            result[
                "storage_method"
            ],
        )

        print(
            "STORAGE_BASELINE_MAE =",
            result[
                "storage_baseline_mae"
            ],
        )

        print(
            "STORAGE_ML_MAE =",
            result[
                "storage_ml_mae"
            ],
        )

        print(
            "STORAGE_CHOSEN_MAE =",
            result[
                "storage_display_mae"
            ],
        )

        print(
            "STORAGE_LIMIT =",
            result[
                "storage_limit"
            ],
        )

        print(
            "STORAGE_REPORTABLE =",
            result[
                "storage_reportable"
            ],
        )

        print(
            "PREDICTED_STORAGE =",
            result[
                "predicted_storage"
            ],
        )


        print()
        print(
            "FINAL_STATUS =",
            overall_status,
        )


    # ========================================================
    # PERSIST ONLY CURRENT + QUALITY-PASSED FORECASTS
    # ========================================================

    engine = create_async_engine(
        db_url()
    )


    async with engine.begin() as conn:

        await conn.execute(
            text(
                DDL
            )
        )


        for statement in ALTER:

            await conn.execute(
                text(
                    statement
                )
            )


        # ----------------------------------------------------
        # Remove previous derived forecast rows only for assets
        # evaluated in this run.
        # Source observations are untouched.
        # ----------------------------------------------------

        for mapping in exact.values():

            await conn.execute(
                text(
                    """
                    DELETE FROM
                    public.dam_barrage_operational_predictions_v1

                    WHERE asset_code=:asset_code
                    """
                ),
                {
                    "asset_code":
                        mapping[
                            "asset"
                        ][
                            "asset_code"
                        ]
                },
            )


        persisted = 0


        for row in results:

            if row.get(
                "model_status"
            ) not in {
                "VALIDATED_OPERATIONAL_ML",
                "VALIDATED_PERSISTENCE_BASELINE",
            }:

                continue


            if (
                row.get(
                    "predicted_level"
                )
                is None
                and row.get(
                    "predicted_storage"
                )
                is None
            ):

                continue


            # IMPORTANT:
            # Real Python date objects for asyncpg DATE.
            observation_date_db = date.fromisoformat(
                row[
                    "observation_date"
                ]
            )

            prediction_date_db = date.fromisoformat(
                row[
                    "prediction_date"
                ]
            )


            await conn.execute(
                text(
                    """
                    INSERT INTO
                    public.dam_barrage_operational_predictions_v1
                    (
                        asset_code,
                        station_name,

                        observation_date,
                        prediction_date,

                        observed_level_m,
                        predicted_level_m,

                        observed_storage_mcm,
                        predicted_storage_mcm,

                        level_status,
                        storage_status,

                        level_test_mae,
                        level_baseline_mae,

                        storage_test_mae,
                        storage_baseline_mae,

                        confidence,

                        model_status,

                        prediction_semantics,
                        source_name,

                        forecast_method_level,
                        forecast_method_storage,

                        history_days,
                        test_rows,

                        generated_at
                    )

                    VALUES
                    (
                        :asset_code,
                        :station,

                        :observation_date,
                        :prediction_date,

                        :observed_level,
                        :predicted_level,

                        :observed_storage,
                        :predicted_storage,

                        :level_status,
                        :storage_status,

                        :level_test_mae,
                        :level_baseline_mae,

                        :storage_test_mae,
                        :storage_baseline_mae,

                        :confidence,

                        :model_status,

                        :prediction_semantics,
                        :source_name,

                        :forecast_method_level,
                        :forecast_method_storage,

                        :history_days,
                        :test_rows,

                        NOW()
                    )

                    ON CONFLICT
                    (asset_code)

                    DO UPDATE SET

                        station_name =
                            EXCLUDED.station_name,

                        observation_date =
                            EXCLUDED.observation_date,

                        prediction_date =
                            EXCLUDED.prediction_date,

                        observed_level_m =
                            EXCLUDED.observed_level_m,

                        predicted_level_m =
                            EXCLUDED.predicted_level_m,

                        observed_storage_mcm =
                            EXCLUDED.observed_storage_mcm,

                        predicted_storage_mcm =
                            EXCLUDED.predicted_storage_mcm,

                        level_status =
                            EXCLUDED.level_status,

                        storage_status =
                            EXCLUDED.storage_status,

                        level_test_mae =
                            EXCLUDED.level_test_mae,

                        level_baseline_mae =
                            EXCLUDED.level_baseline_mae,

                        storage_test_mae =
                            EXCLUDED.storage_test_mae,

                        storage_baseline_mae =
                            EXCLUDED.storage_baseline_mae,

                        confidence =
                            EXCLUDED.confidence,

                        model_status =
                            EXCLUDED.model_status,

                        prediction_semantics =
                            EXCLUDED.prediction_semantics,

                        source_name =
                            EXCLUDED.source_name,

                        forecast_method_level =
                            EXCLUDED.forecast_method_level,

                        forecast_method_storage =
                            EXCLUDED.forecast_method_storage,

                        history_days =
                            EXCLUDED.history_days,

                        test_rows =
                            EXCLUDED.test_rows,

                        generated_at =
                            NOW()
                    """
                ),
                {
                    "asset_code":
                        row[
                            "asset_code"
                        ],

                    "station":
                        row[
                            "station"
                        ],

                    "observation_date":
                        observation_date_db,

                    "prediction_date":
                        prediction_date_db,

                    "observed_level":
                        row.get(
                            "observed_level"
                        ),

                    "predicted_level":
                        row.get(
                            "predicted_level"
                        ),

                    "observed_storage":
                        row.get(
                            "observed_storage"
                        ),

                    "predicted_storage":
                        row.get(
                            "predicted_storage"
                        ),

                    "level_status":
                        row[
                            "level_status"
                        ],

                    "storage_status":
                        row[
                            "storage_status"
                        ],

                    "level_test_mae":
                        (
                            row.get(
                                "level_ml_mae"
                            )
                            if row.get(
                                "level_method"
                            )
                            == "EXTRA_TREES"
                            else None
                        ),

                    "level_baseline_mae":
                        row.get(
                            "level_baseline_mae"
                        ),

                    "storage_test_mae":
                        (
                            row.get(
                                "storage_ml_mae"
                            )
                            if row.get(
                                "storage_method"
                            )
                            == "EXTRA_TREES"
                            else None
                        ),

                    "storage_baseline_mae":
                        row.get(
                            "storage_baseline_mae"
                        ),

                    "confidence":
                        row.get(
                            "confidence"
                        ),

                    "model_status":
                        row[
                            "model_status"
                        ],

                    "prediction_semantics":
                        (
                            "NEXT_DAY_RESERVOIR_"
                            "OPERATIONAL_FORECAST"
                        ),

                    "source_name":
                        (
                            "OFFICIAL_NWDP_MANUAL_"
                            "RESERVOIR_OBSERVATIONS"
                        ),

                    "forecast_method_level":
                        row.get(
                            "level_method"
                        ),

                    "forecast_method_storage":
                        row.get(
                            "storage_method"
                        ),

                    "history_days":
                        row.get(
                            "history_days"
                        ),

                    "test_rows":
                        row.get(
                            "test_rows"
                        ),
                },
            )


            persisted += 1


    await engine.dispose()


    reportable = [
        row
        for row in results
        if row.get(
            "model_status"
        )
        in {
            "VALIDATED_OPERATIONAL_ML",
            "VALIDATED_PERSISTENCE_BASELINE",
        }
    ]


    summary = {
        "version":
            "ml9b4_final_operational_forecast_v1",

        "as_of_date":
            ASOF.date().isoformat(),

        "source_files":
            len(
                manifest
            ),

        "source_stations":
            len(
                source_station_names
            ),

        "exact_canonical_stations":
            len(
                exact
            ),

        "assets_evaluated":
            len(
                results
            ),

        "reportable_forecasts":
            len(
                reportable
            ),

        "validated_ml_forecasts":
            sum(
                1
                for row in reportable
                if row[
                    "model_status"
                ]
                == "VALIDATED_OPERATIONAL_ML"
            ),

        "validated_baseline_forecasts":
            sum(
                1
                for row in reportable
                if row[
                    "model_status"
                ]
                == "VALIDATED_PERSISTENCE_BASELINE"
            ),

        "persisted_forecasts":
            persisted,

        "results":
            results,
    }


    (
        OUT
        / "ml9b4_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


    print()
    print(
        "================================================"
    )

    print(
        " ML-9B.4 FINAL SUMMARY"
    )

    print(
        "================================================"
    )

    print(
        "ASSETS_EVALUATED =",
        len(
            results
        ),
    )

    print(
        "REPORTABLE_FORECASTS =",
        len(
            reportable
        ),
    )

    print(
        "VALIDATED_ML_FORECASTS =",
        summary[
            "validated_ml_forecasts"
        ],
    )

    print(
        "VALIDATED_BASELINE_FORECASTS =",
        summary[
            "validated_baseline_forecasts"
        ],
    )

    print(
        "PERSISTED_FORECASTS =",
        persisted,
    )

    print()
    print(
        "STRUCTURAL_HEALTH = WITHHELD"
    )

    print(
        "STRUCTURAL_RISK = WITHHELD"
    )

    print(
        "STRUCTURAL_RUL = WITHHELD"
    )

    print()
    print(
        "ML9B4_FINAL=PASS"
    )


asyncio.run(
    main()
)