import asyncio
import csv
import json
import math
import os
import pickle
import re

from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


LEVEL_FILE = Path(
    os.environ["ML9_LEVEL"]
)

STORAGE_FILE = Path(
    os.environ["ML9_STORAGE"]
)

MATCH_FILE = Path(
    os.environ["ML9_MATCHES"]
)

OUT = Path(
    os.environ["ML9_OUT"]
)

ASOF = pd.Timestamp(
    os.environ["ML9_ASOF"]
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)

MODEL_DIR = OUT / "models"

MODEL_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


LEVEL_COL = (
    "Manual Daily Reservoir water level (m)"
)

STORAGE_COL = (
    "Manual Daily Reservoir storage (mcm)"
)

DATE_COL = (
    "Data Acquisition Time"
)

STATION_COL = (
    "Station"
)


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


def async_url():

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


def load_source(
    path,
    target,
):

    frame = pd.read_csv(
        path
    )

    required = [
        STATION_COL,
        DATE_COL,
        target,
    ]

    missing = [
        col
        for col in required
        if col not in frame.columns
    ]

    if missing:

        raise RuntimeError(
            f"Missing source columns: {missing}"
        )


    frame["station_key"] = (
        frame[
            STATION_COL
        ]
        .fillna("")
        .map(normalize)
    )


    frame["date"] = pd.to_datetime(
        frame[
            DATE_COL
        ],
        dayfirst=True,
        errors="coerce",
    ).dt.normalize()


    frame["value"] = pd.to_numeric(
        frame[
            target
        ],
        errors="coerce",
    )


    frame = frame[
        frame["date"].notna()
    ].copy()


    frame = frame[
        frame["date"]
        <= ASOF
    ].copy()


    frame = frame[
        frame["value"].notna()
    ].copy()


    # One daily observation per station.
    frame = (
        frame
        .sort_values(
            [
                "station_key",
                "date",
            ]
        )
        .groupby(
            [
                "station_key",
                "date",
            ],
            as_index=False,
        )
        .agg(
            value=(
                "value",
                "last",
            )
        )
    )


    return frame


def load_matches():

    frame = pd.read_csv(
        MATCH_FILE
    )

    required = [
        "station",
        "asset_code",
        "asset_name",
    ]

    missing = [
        col
        for col in required
        if col not in frame.columns
    ]

    if missing:

        raise RuntimeError(
            f"Mapping columns missing: {missing}"
        )


    result = {}


    for _, row in frame.iterrows():

        key = normalize(
            row["station"]
        )

        if not key:
            continue

        result[key] = {
            "station":
                str(
                    row["station"]
                ),

            "asset_code":
                str(
                    row["asset_code"]
                ),

            "asset_name":
                str(
                    row["asset_name"]
                ),
        }


    return result


def make_features(
    frame,
    target_name,
):

    data = frame.copy()

    data = data.sort_values(
        "date"
    ).reset_index(
        drop=True
    )


    # --------------------------------------------------------
    # Strictly historical features.
    # --------------------------------------------------------

    for lag in [
        1,
        2,
        3,
        7,
        14,
    ]:

        data[
            f"{target_name}_lag_{lag}"
        ] = data[
            target_name
        ].shift(
            lag
        )


    for window in [
        3,
        7,
        14,
    ]:

        shifted = data[
            target_name
        ].shift(
            1
        )

        data[
            f"{target_name}_mean_{window}"
        ] = (
            shifted
            .rolling(
                window
            )
            .mean()
        )

        data[
            f"{target_name}_std_{window}"
        ] = (
            shifted
            .rolling(
                window
            )
            .std()
        )


    doy = data[
        "date"
    ].dt.dayofyear


    data[
        "day_sin"
    ] = np.sin(
        2
        * np.pi
        * doy
        / 365.25
    )

    data[
        "day_cos"
    ] = np.cos(
        2
        * np.pi
        * doy
        / 365.25
    )


    # Target is next day's value.
    data[
        "target"
    ] = data[
        target_name
    ].shift(
        -1
    )


    data[
        "target_date"
    ] = data[
        "date"
    ] + pd.Timedelta(
        days=1
    )


    feature_cols = [
        column
        for column in data.columns
        if (
            column.startswith(
                f"{target_name}_lag_"
            )
            or column.startswith(
                f"{target_name}_mean_"
            )
            or column.startswith(
                f"{target_name}_std_"
            )
            or column in {
                "day_sin",
                "day_cos",
            }
        )
    ]


    data = data.dropna(
        subset=(
            feature_cols
            + [
                "target",
            ]
        )
    ).copy()


    return (
        data,
        feature_cols,
    )


def evaluate_model(
    data,
    features,
    target_name,
):

    n = len(
        data
    )


    if n < 60:

        return {
            "status":
                "WITHHELD_INSUFFICIENT_HISTORY",

            "samples":
                n,
        }


    # --------------------------------------------------------
    # Chronological holdout.
    # Last 20%, minimum 14 observations.
    # --------------------------------------------------------

    test_size = max(
        14,
        int(
            math.ceil(
                n * 0.20
            )
        ),
    )


    if n - test_size < 40:

        return {
            "status":
                "WITHHELD_INSUFFICIENT_TRAINING_ROWS",

            "samples":
                n,
        }


    train = data.iloc[
        :-test_size
    ].copy()

    test = data.iloc[
        -test_size:
    ].copy()


    X_train = train[
        features
    ]

    y_train = train[
        "target"
    ]


    X_test = test[
        features
    ]

    y_test = test[
        "target"
    ]


    # Persistence baseline:
    # tomorrow = today's observation.
    baseline_prediction = test[
        target_name
    ].to_numpy()


    baseline_mae = mean_absolute_error(
        y_test,
        baseline_prediction,
    )


    baseline_rmse = math.sqrt(
        mean_squared_error(
            y_test,
            baseline_prediction,
        )
    )


    model = ExtraTreesRegressor(
        n_estimators=300,
        min_samples_leaf=2,
        max_features=0.85,
        random_state=42,
        n_jobs=-1,
    )


    model.fit(
        X_train,
        y_train,
    )


    prediction = model.predict(
        X_test
    )


    ml_mae = mean_absolute_error(
        y_test,
        prediction,
    )


    ml_rmse = math.sqrt(
        mean_squared_error(
            y_test,
            prediction,
        )
    )


    # --------------------------------------------------------
    # Gate.
    #
    # If persistence is literally perfect, ML should not
    # pretend to be better.
    # --------------------------------------------------------

    epsilon = 1e-9


    if baseline_mae <= epsilon:

        passed = (
            ml_mae <= epsilon
        )

        improvement = (
            0.0
            if not passed
            else 1.0
        )

    else:

        improvement = (
            baseline_mae
            - ml_mae
        ) / baseline_mae

        passed = (
            ml_mae
            < baseline_mae
            and ml_rmse
            <= baseline_rmse
        )


    status = (
        "VALIDATED_OPERATIONAL_ML"
        if passed
        else "WITHHELD_ML_DID_NOT_BEAT_BASELINE"
    )


    # --------------------------------------------------------
    # Confidence = held-out evidence quality, NOT certainty.
    # --------------------------------------------------------

    if passed:

        sample_factor = min(
            1.0,
            len(test) / 30.0,
        )


        performance_factor = max(
            0.0,
            min(
                1.0,
                improvement,
            ),
        )


        confidence = (
            0.50
            + 0.20
            * sample_factor
            + 0.20
            * performance_factor
        )


        confidence = min(
            0.90,
            max(
                0.50,
                confidence,
            ),
        )

    else:

        confidence = None


    return {
        "status":
            status,

        "passed":
            bool(
                passed
            ),

        "samples":
            n,

        "train_rows":
            len(
                train
            ),

        "test_rows":
            len(
                test
            ),

        "train_start":
            str(
                train[
                    "date"
                ].min().date()
            ),

        "train_end":
            str(
                train[
                    "date"
                ].max().date()
            ),

        "test_start":
            str(
                test[
                    "date"
                ].min().date()
            ),

        "test_end":
            str(
                test[
                    "date"
                ].max().date()
            ),

        "baseline_mae":
            float(
                baseline_mae
            ),

        "baseline_rmse":
            float(
                baseline_rmse
            ),

        "ml_mae":
            float(
                ml_mae
            ),

        "ml_rmse":
            float(
                ml_rmse
            ),

        "mae_improvement_fraction":
            float(
                improvement
            ),

        "confidence":
            (
                float(
                    confidence
                )
                if confidence
                is not None
                else None
            ),

        "model":
            model,

        "features":
            features,
    }


def train_station(
    station_key,
    station_info,
    level,
    storage,
):

    level_station = level[
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
                "level",
        }
    )


    storage_station = storage[
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
                "storage",
        }
    )


    merged = pd.merge(
        level_station,
        storage_station,
        how="inner",
        on="date",
    )


    merged = merged.sort_values(
        "date"
    ).drop_duplicates(
        "date"
    )


    if len(
        merged
    ) < 90:

        return {
            "asset_code":
                station_info[
                    "asset_code"
                ],

            "asset_name":
                station_info[
                    "asset_name"
                ],

            "station":
                station_info[
                    "station"
                ],

            "common_days":
                len(
                    merged
                ),

            "status":
                "WITHHELD_LESS_THAN_90_COMMON_DAYS",
        }


    outputs = {
        "asset_code":
            station_info[
                "asset_code"
            ],

        "asset_name":
            station_info[
                "asset_name"
            ],

        "station":
            station_info[
                "station"
            ],

        "common_days":
            len(
                merged
            ),

        "observation_start":
            str(
                merged[
                    "date"
                ].min().date()
            ),

        "observation_end":
            str(
                merged[
                    "date"
                ].max().date()
            ),

        "latest_level":
            float(
                merged.iloc[
                    -1
                ][
                    "level"
                ]
            ),

        "latest_storage":
            float(
                merged.iloc[
                    -1
                ][
                    "storage"
                ]
            ),

        "latest_observation_date":
            str(
                merged.iloc[
                    -1
                ][
                    "date"
                ].date()
            ),
    }


    level_data, level_features = (
        make_features(
            merged,
            "level",
        )
    )


    storage_data, storage_features = (
        make_features(
            merged,
            "storage",
        )
    )


    level_result = evaluate_model(
        level_data,
        level_features,
        "level",
    )


    storage_result = evaluate_model(
        storage_data,
        storage_features,
        "storage",
    )


    outputs[
        "level_validation"
    ] = {
        key: value
        for key, value
        in level_result.items()
        if key not in {
            "model",
            "features",
        }
    }


    outputs[
        "storage_validation"
    ] = {
        key: value
        for key, value
        in storage_result.items()
        if key not in {
            "model",
            "features",
        }
    }


    # --------------------------------------------------------
    # Forecast only passed targets.
    #
    # Refit passed model on all eligible history.
    # --------------------------------------------------------

    predicted_for = (
        merged[
            "date"
        ].max()
        + pd.Timedelta(
            days=1
        )
    )


    outputs[
        "prediction_date"
    ] = str(
        predicted_for.date()
    )


    # LEVEL
    if level_result.get(
        "passed"
    ):

        model = level_result[
            "model"
        ]


        model.fit(
            level_data[
                level_result[
                    "features"
                ]
            ],
            level_data[
                "target"
            ],
        )


        latest_feature_row = (
            level_data.iloc[
                -1:
            ][
                level_result[
                    "features"
                ]
            ]
        )


        # The feature row dated t predicts t+1.
        level_prediction = float(
            model.predict(
                latest_feature_row
            )[0]
        )


        outputs[
            "predicted_level"
        ] = level_prediction


        model_file = (
            MODEL_DIR
            / (
                station_info[
                    "asset_code"
                ]
                + "_level.pkl"
            )
        )


        with model_file.open(
            "wb"
        ) as handle:

            pickle.dump(
                {
                    "model":
                        model,

                    "features":
                        level_result[
                            "features"
                        ],

                    "target":
                        "level",

                    "asset_code":
                        station_info[
                            "asset_code"
                        ],
                },
                handle,
            )


    else:

        outputs[
            "predicted_level"
        ] = None


    # STORAGE
    if storage_result.get(
        "passed"
    ):

        model = storage_result[
            "model"
        ]


        model.fit(
            storage_data[
                storage_result[
                    "features"
                ]
            ],
            storage_data[
                "target"
            ],
        )


        latest_feature_row = (
            storage_data.iloc[
                -1:
            ][
                storage_result[
                    "features"
                ]
            ]
        )


        storage_prediction = float(
            model.predict(
                latest_feature_row
            )[0]
        )


        outputs[
            "predicted_storage"
        ] = storage_prediction


        model_file = (
            MODEL_DIR
            / (
                station_info[
                    "asset_code"
                ]
                + "_storage.pkl"
            )
        )


        with model_file.open(
            "wb"
        ) as handle:

            pickle.dump(
                {
                    "model":
                        model,

                    "features":
                        storage_result[
                            "features"
                        ],

                    "target":
                        "storage",

                    "asset_code":
                        station_info[
                            "asset_code"
                        ],
                },
                handle,
            )


    else:

        outputs[
            "predicted_storage"
        ] = None


    passed_targets = []


    if level_result.get(
        "passed"
    ):

        passed_targets.append(
            "LEVEL"
        )


    if storage_result.get(
        "passed"
    ):

        passed_targets.append(
            "STORAGE"
        )


    outputs[
        "passed_targets"
    ] = passed_targets


    outputs[
        "status"
    ] = (
        "VALIDATED_OPERATIONAL_ML"
        if passed_targets
        else "WITHHELD_NO_MODEL_PASSED"
    )


    confidences = [
        value
        for value in [
            level_result.get(
                "confidence"
            ),
            storage_result.get(
                "confidence"
            ),
        ]
        if value is not None
    ]


    outputs[
        "confidence"
    ] = (
        float(
            sum(
                confidences
            )
            / len(
                confidences
            )
        )
        if confidences
        else None
    )


    return outputs


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

    generated_at TIMESTAMPTZ
        NOT NULL
        DEFAULT NOW()
);
"""


async def persist(
    results,
):

    engine = create_async_engine(
        async_url()
    )


    async with engine.begin() as conn:

        await conn.execute(
            text(
                DDL
            )
        )


        for result in results:

            if result.get(
                "status"
            ) != "VALIDATED_OPERATIONAL_ML":

                continue


            level_validation = result.get(
                "level_validation",
                {},
            )


            storage_validation = result.get(
                "storage_validation",
                {},
            )


            # At least one forecast must have passed.
            if (
                result.get(
                    "predicted_level"
                )
                is None
                and result.get(
                    "predicted_storage"
                )
                is None
            ):

                continue


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
                        generated_at
                    )
                    VALUES
                    (
                        :asset_code,
                        :station_name,
                        :observation_date,
                        :prediction_date,

                        :observed_level_m,
                        :predicted_level_m,

                        :observed_storage_mcm,
                        :predicted_storage_mcm,

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

                        generated_at =
                            NOW()
                    """
                ),
                {
                    "asset_code":
                        result[
                            "asset_code"
                        ],

                    "station_name":
                        result[
                            "station"
                        ],

                    "observation_date":
                        result[
                            "latest_observation_date"
                        ],

                    "prediction_date":
                        result[
                            "prediction_date"
                        ],

                    "observed_level_m":
                        result.get(
                            "latest_level"
                        ),

                    "predicted_level_m":
                        result.get(
                            "predicted_level"
                        ),

                    "observed_storage_mcm":
                        result.get(
                            "latest_storage"
                        ),

                    "predicted_storage_mcm":
                        result.get(
                            "predicted_storage"
                        ),

                    "level_status":
                        level_validation.get(
                            "status",
                            "WITHHELD",
                        ),

                    "storage_status":
                        storage_validation.get(
                            "status",
                            "WITHHELD",
                        ),

                    "level_test_mae":
                        level_validation.get(
                            "ml_mae"
                        ),

                    "level_baseline_mae":
                        level_validation.get(
                            "baseline_mae"
                        ),

                    "storage_test_mae":
                        storage_validation.get(
                            "ml_mae"
                        ),

                    "storage_baseline_mae":
                        storage_validation.get(
                            "baseline_mae"
                        ),

                    "confidence":
                        result.get(
                            "confidence"
                        ),

                    "model_status":
                        result[
                            "status"
                        ],

                    "prediction_semantics":
                        (
                            "NEXT_DAY_RESERVOIR_"
                            "LEVEL_STORAGE_OPERATIONAL_FORECAST"
                        ),

                    "source_name":
                        (
                            "NWDP_MANUAL_DAILY_RESERVOIR_OBSERVATIONS"
                        ),
                },
            )


    async with engine.connect() as conn:

        count = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM
                public.dam_barrage_operational_predictions_v1
                """
            )
        )


    await engine.dispose()

    return int(
        count
        or 0
    )


async def main():

    level = load_source(
        LEVEL_FILE,
        LEVEL_COL,
    )


    storage = load_source(
        STORAGE_FILE,
        STORAGE_COL,
    )


    mappings = load_matches()


    print(
        "EXACT_MAPPED_STATIONS =",
        len(
            mappings
        ),
    )


    results = []


    for station_key, info in sorted(
        mappings.items()
    ):

        result = train_station(
            station_key,
            info,
            level,
            storage,
        )

        results.append(
            result
        )


        print()
        print(
            "================================================"
        )

        print(
            "ASSET =",
            result.get(
                "asset_code"
            ),
            result.get(
                "asset_name"
            ),
        )

        print(
            "STATION =",
            result.get(
                "station"
            ),
        )

        print(
            "COMMON_DAYS =",
            result.get(
                "common_days"
            ),
        )

        print(
            "STATUS =",
            result.get(
                "status"
            ),
        )


        lv = result.get(
            "level_validation",
            {},
        )


        sv = result.get(
            "storage_validation",
            {},
        )


        if lv:

            print(
                "LEVEL_STATUS =",
                lv.get(
                    "status"
                ),
            )

            print(
                "LEVEL_ML_MAE =",
                lv.get(
                    "ml_mae"
                ),
            )

            print(
                "LEVEL_BASELINE_MAE =",
                lv.get(
                    "baseline_mae"
                ),
            )


        if sv:

            print(
                "STORAGE_STATUS =",
                sv.get(
                    "status"
                ),
            )

            print(
                "STORAGE_ML_MAE =",
                sv.get(
                    "ml_mae"
                ),
            )

            print(
                "STORAGE_BASELINE_MAE =",
                sv.get(
                    "baseline_mae"
                ),
            )


        print(
            "PREDICTED_LEVEL =",
            result.get(
                "predicted_level"
            ),
        )

        print(
            "PREDICTED_STORAGE =",
            result.get(
                "predicted_storage"
            ),
        )


    persisted_count = await persist(
        results
    )


    validated_assets = sum(
        1
        for row in results
        if row.get(
            "status"
        )
        == "VALIDATED_OPERATIONAL_ML"
    )


    summary = {
        "version":
            "ml9_fast_operational_forecast_v1",

        "as_of_date":
            str(
                ASOF.date()
            ),

        "exact_mapped_stations":
            len(
                mappings
            ),

        "assets_evaluated":
            len(
                results
            ),

        "validated_assets":
            validated_assets,

        "persisted_prediction_assets":
            persisted_count,

        "prediction_semantics":
            (
                "next-day operational reservoir "
                "level/storage forecast"
            ),

        "structural_prediction":
            False,

        "results":
            results,
    }


    # Remove non-serializable objects.
    for result in summary[
        "results"
    ]:

        for key in [
            "level_validation",
            "storage_validation",
        ]:

            if key in result:

                result[key] = {
                    k: v
                    for k, v
                    in result[
                        key
                    ].items()
                }


    (
        OUT
        / "ml9_fast_summary.json"
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
        " ML-9 FAST FORECAST SUMMARY"
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
        "VALIDATED_ASSETS =",
        validated_assets,
    )

    print(
        "PERSISTED_PREDICTION_ASSETS =",
        persisted_count,
    )

    print(
        "STRUCTURAL_PREDICTION = NO"
    )

    print()
    print(
        "ML9_FAST_FORECAST=PASS"
    )


asyncio.run(
    main()
)