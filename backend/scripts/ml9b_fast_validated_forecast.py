import asyncio
import json
import math
import os
import re

from pathlib import Path

import numpy as np
import pandas as pd

from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


SOURCE_DIR = Path(
    "/tmp/ml9b/sources"
)

SOURCE_MANIFEST = Path(
    "/tmp/ml9b/source_manifest.json"
)

OUT = Path(
    "/tmp/ml9b/output"
)

ASOF = pd.Timestamp(
    "2026-09-04"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
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


def database_url():

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
# LOAD COPIED SOURCE MANIFEST
# ============================================================

manifest = json.loads(
    SOURCE_MANIFEST.read_text(
        encoding="utf-8-sig"
    )
)


level_frames = []
storage_frames = []


for item in manifest:

    filename = item[
        "container_filename"
    ]

    path = (
        SOURCE_DIR
        / filename
    )

    if not path.exists():
        continue


    frame = pd.read_csv(
        path,
        low_memory=False,
    )


    target = item[
        "target_column"
    ]


    if target not in frame.columns:
        continue


    if "Station" not in frame.columns:
        continue

    if "Data Acquisition Time" not in frame.columns:
        continue


    parsed_date = pd.to_datetime(
        frame[
            "Data Acquisition Time"
        ],
        dayfirst=True,
        errors="coerce",
    ).dt.normalize()


    values = pd.to_numeric(
        frame[
            target
        ],
        errors="coerce",
    )


    normalized = pd.DataFrame(
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
                parsed_date,

            "value":
                values,
        }
    )


    normalized = normalized[
        normalized[
            "station_key"
        ].ne("")
    ]


    normalized = normalized[
        normalized[
            "date"
        ].notna()
    ]


    normalized = normalized[
        normalized[
            "date"
        ] <= ASOF
    ]


    normalized = normalized[
        normalized[
            "value"
        ].notna()
    ]


    if item[
        "kind"
    ] == "LEVEL":

        level_frames.append(
            normalized
        )

    else:

        storage_frames.append(
            normalized
        )


if not level_frames:
    raise RuntimeError(
        "No usable level observations."
    )


if not storage_frames:
    raise RuntimeError(
        "No usable storage observations."
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
# DEDUPLICATE REAL OBSERVATIONS
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
    "COMBINED_LEVEL_OBSERVATIONS =",
    len(level),
)

print(
    "COMBINED_STORAGE_OBSERVATIONS =",
    len(storage),
)


# ============================================================
# EXACT CANONICAL ASSET MAPPING
# ============================================================

async def load_assets():

    engine = create_async_engine(
        database_url()
    )

    async with engine.connect() as conn:

        rows = (
            await conn.execute(
                text(
                    """
                    SELECT
                        asset_code,
                        name,
                        asset_type,
                        district,
                        identity_status
                    FROM public.assets
                    WHERE
                        LOWER(
                            CAST(
                                asset_type AS TEXT
                            )
                        )
                        IN ('dam','barrage')
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
# FEATURE ENGINEERING
#
# t information predicts t+1.
# No future data enters features.
# ============================================================

def create_features(
    merged
):

    series = (
        merged
        .set_index(
            "date"
        )
        .sort_index()
    )


    # Reindex daily.
    # Missing dates remain missing - NO interpolation.
    full_index = pd.date_range(
        series.index.min(),
        series.index.max(),
        freq="D",
    )


    series = series.reindex(
        full_index
    )


    series.index.name = (
        "date"
    )


    features = pd.DataFrame(
        index=series.index
    )


    for target in [
        "level",
        "storage",
    ]:

        features[
            target + "_current"
        ] = series[
            target
        ]


        for lag in [
            1,
            2,
            3,
            7,
            14,
        ]:

            features[
                target
                + "_lag_"
                + str(lag)
            ] = series[
                target
            ].shift(
                lag
            )


        for window in [
            3,
            7,
            14,
        ]:

            features[
                target
                + "_mean_"
                + str(window)
            ] = series[
                target
            ].rolling(
                window,
                min_periods=window,
            ).mean()


    day_of_year = (
        features.index.dayofyear
    )


    features[
        "day_sin"
    ] = np.sin(
        2
        * np.pi
        * day_of_year
        / 365.25
    )


    features[
        "day_cos"
    ] = np.cos(
        2
        * np.pi
        * day_of_year
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
        for column
        in features.columns
        if not column.startswith(
            "target_"
        )
    ]


    training = features.dropna(
        subset=(
            feature_columns
            + [
                "target_level",
                "target_storage",
            ]
        )
    ).copy()


    complete_feature_rows = features.dropna(
        subset=feature_columns
    )

    if complete_feature_rows.empty:

        latest = features.iloc[
            0:0
        ].copy()

        latest_complete = False

    else:

        latest = complete_feature_rows.iloc[
            -1:
        ].copy()

        latest_complete = True


    return (
        training,
        latest,
        feature_columns,
        latest_complete,
    )


# ============================================================
# VALIDATION
# ============================================================

def validate_target(
    training,
    feature_columns,
    target_column,
    current_column,
    allow_ml,
):

    count = len(
        training
    )


    if count < 20:

        return {
            "status":
                "WITHHELD_INSUFFICIENT_BACKTEST_ROWS"
        }


    test_size = max(
        7,
        int(
            math.ceil(
                count * 0.15
            )
        ),
    )


    if test_size >= count:

        return {
            "status":
                "WITHHELD_INSUFFICIENT_BACKTEST_ROWS"
        }


    train = training.iloc[
        :-test_size
    ].copy()


    test = training.iloc[
        -test_size:
    ].copy()


    y_test = test[
        target_column
    ].to_numpy()


    persistence = test[
        current_column
    ].to_numpy()


    persistence_mae = float(
        mean_absolute_error(
            y_test,
            persistence,
        )
    )


    result = {
        "persistence_mae":
            persistence_mae,

        "test_rows":
            len(test),

        "train_rows":
            len(train),

        "test_start":
            str(
                test.index.min().date()
            ),

        "test_end":
            str(
                test.index.max().date()
            ),

        "method":
            "PERSISTENCE",

        "status":
            "VALIDATED_PERSISTENCE_BASELINE",

        "ml_mae":
            None,

        "ml_improvement":
            None,

        "model":
            None,
    }


    if not allow_ml:

        return result


    # --------------------------------------------------------
    # One predefined ML model.
    # No algorithm shopping.
    # --------------------------------------------------------

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
            target_column
        ],
    )


    ml_predictions = model.predict(
        test[
            feature_columns
        ]
    )


    ml_mae = float(
        mean_absolute_error(
            y_test,
            ml_predictions,
        )
    )


    if persistence_mae > 0:

        improvement = (
            persistence_mae
            - ml_mae
        ) / persistence_mae

    else:

        improvement = 0.0


    result[
        "ml_mae"
    ] = ml_mae

    result[
        "ml_improvement"
    ] = float(
        improvement
    )


    # Require at least 2% improvement.
    if (
        persistence_mae > 0
        and improvement >= 0.02
    ):

        result[
            "method"
        ] = "EXTRA_TREES"

        result[
            "status"
        ] = "VALIDATED_OPERATIONAL_ML"

        result[
            "model"
        ] = model


    return result


# ============================================================
# DATABASE TABLE
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


async def main():

    assets = await load_assets()


    assets_by_name = {}


    for asset in assets:

        key = normalize(
            asset[
                "name"
            ]
        )

        if not key:
            continue


        if key not in assets_by_name:

            assets_by_name[
                key
            ] = []


        assets_by_name[
            key
        ].append(
            asset
        )


    source_names = {}


    for frame in [
        level,
        storage,
    ]:

        for _, row in frame.iterrows():

            source_names[
                row[
                    "station_key"
                ]
            ] = str(
                row[
                    "station"
                ]
            )


    exact = {}


    for key, station in source_names.items():

        matches = assets_by_name.get(
            key,
            [],
        )


        if len(matches) == 1:

            exact[
                key
            ] = {
                "station":
                    station,

                "asset":
                    matches[0],
            }


    print(
        "SOURCE_STATIONS =",
        len(
            source_names
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
                    "level"
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
                    "storage"
            }
        )


        merged = pd.merge(
            level_station,
            storage_station,
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


        history_days = len(
            merged
        )


        asset = mapping[
            "asset"
        ]


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
            history_days,
        )


        if history_days < 30:

            print(
                "STATUS = WITHHELD_LESS_THAN_30_DAYS"
            )

            continue


        (
            training,
            latest_features,
            feature_columns,
            latest_complete,
        ) = create_features(
            merged
        )


        if len(
            training
        ) < 20:

            print(
                "STATUS = WITHHELD_TOO_FEW_FEATURE_ROWS"
            )

            continue


        if not latest_complete:

            print(
                "STATUS = WITHHELD_LATEST_LAG_WINDOW_INCOMPLETE"
            )

            continue


        allow_ml = (
            history_days >= 90
        )


        level_result = validate_target(
            training,
            feature_columns,
            "target_level",
            "level_current",
            allow_ml,
        )


        storage_result = validate_target(
            training,
            feature_columns,
            "target_storage",
            "storage_current",
            allow_ml,
        )


        latest_date = pd.Timestamp(
            latest_features.index[
                -1
            ]
        ).normalize()


        latest_level = float(
            merged.loc[
                merged[
                    "date"
                ]
                == latest_date,
                "level",
            ].iloc[-1]
        )


        latest_storage = float(
            merged.loc[
                merged[
                    "date"
                ]
                == latest_date,
                "storage",
            ].iloc[-1]
        )


        # ====================================================
        # FORECAST NEXT UNOBSERVED DAY
        # ====================================================

        if (
            level_result[
                "method"
            ]
            == "EXTRA_TREES"
        ):

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
                    "target_level"
                ],
            )


            predicted_level = float(
                model.predict(
                    latest_features[
                        feature_columns
                    ]
                )[0]
            )

        else:

            predicted_level = (
                latest_level
            )


        if (
            storage_result[
                "method"
            ]
            == "EXTRA_TREES"
        ):

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
                    "target_storage"
                ],
            )


            predicted_storage = float(
                model.predict(
                    latest_features[
                        feature_columns
                    ]
                )[0]
            )

        else:

            predicted_storage = (
                latest_storage
            )


        prediction_date = (
            latest_date
            + pd.Timedelta(
                days=1
            )
        )


        any_ml = (
            level_result[
                "method"
            ]
            == "EXTRA_TREES"
            or storage_result[
                "method"
            ]
            == "EXTRA_TREES"
        )


        model_status = (
            "VALIDATED_OPERATIONAL_ML"
            if any_ml
            else "VALIDATED_PERSISTENCE_BASELINE"
        )


        # Confidence is withheld for baseline-only forecast.
        confidence = (
            None
            if not any_ml
            else 0.70
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
                history_days,

            "observation_date":
                str(
                    latest_date.date()
                ),

            "prediction_date":
                str(
                    prediction_date.date()
                ),

            "observed_level":
                latest_level,

            "predicted_level":
                predicted_level,

            "observed_storage":
                latest_storage,

            "predicted_storage":
                predicted_storage,

            "level_method":
                level_result[
                    "method"
                ],

            "storage_method":
                storage_result[
                    "method"
                ],

            "level_status":
                level_result[
                    "status"
                ],

            "storage_status":
                storage_result[
                    "status"
                ],

            "level_baseline_mae":
                level_result.get(
                    "persistence_mae"
                ),

            "level_ml_mae":
                level_result.get(
                    "ml_mae"
                ),

            "storage_baseline_mae":
                storage_result.get(
                    "persistence_mae"
                ),

            "storage_ml_mae":
                storage_result.get(
                    "ml_mae"
                ),

            "test_rows":
                min(
                    level_result.get(
                        "test_rows",
                        0,
                    ),
                    storage_result.get(
                        "test_rows",
                        0,
                    ),
                ),

            "model_status":
                model_status,

            "confidence":
                confidence,
        }


        results.append(
            result
        )


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
            "OBSERVED_LEVEL =",
            result[
                "observed_level"
            ],
        )

        print(
            "NEXT_DAY_LEVEL =",
            result[
                "predicted_level"
            ],
        )

        print(
            "OBSERVED_STORAGE =",
            result[
                "observed_storage"
            ],
        )

        print(
            "NEXT_DAY_STORAGE =",
            result[
                "predicted_storage"
            ],
        )

        print(
            "FORECAST_STATUS =",
            model_status,
        )


    # ========================================================
    # PERSIST ONLY BACKTESTED FORECASTS
    # ========================================================

    engine = create_async_engine(
        database_url()
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


        for row in results:

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

                        :level_ml_mae,
                        :level_baseline_mae,

                        :storage_ml_mae,
                        :storage_baseline_mae,

                        :confidence,

                        :model_status,
                        :semantics,
                        :source_name,

                        :level_method,
                        :storage_method,

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
                    **row,

                    "semantics":
                        (
                            "NEXT_DAY_RESERVOIR_"
                            "OPERATIONAL_FORECAST"
                        ),

                    "source_name":
                        (
                            "OFFICIAL_NWDP_MANUAL_"
                            "RESERVOIR_OBSERVATIONS"
                        ),
                },
            )


    async with engine.connect() as conn:

        persisted = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM
                public.dam_barrage_operational_predictions_v1
                """
            )
        )


    await engine.dispose()


    summary = {
        "version":
            "ml9b_validated_operational_forecast_v1",

        "source_files":
            len(
                manifest
            ),

        "combined_level_observations":
            len(
                level
            ),

        "combined_storage_observations":
            len(
                storage
            ),

        "source_stations":
            len(
                source_names
            ),

        "exact_canonical_stations":
            len(
                exact
            ),

        "reportable_forecasts":
            len(
                results
            ),

        "ml_forecasts":
            sum(
                1
                for row in results
                if row[
                    "model_status"
                ]
                == "VALIDATED_OPERATIONAL_ML"
            ),

        "baseline_forecasts":
            sum(
                1
                for row in results
                if row[
                    "model_status"
                ]
                == "VALIDATED_PERSISTENCE_BASELINE"
            ),

        "persisted_forecasts":
            int(
                persisted
                or 0
            ),

        "results":
            results,
    }


    (
        OUT
        / "ml9b_summary.json"
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
        " ML-9B FINAL FORECAST SUMMARY"
    )

    print(
        "================================================"
    )

    print(
        "SOURCE_FILES =",
        len(
            manifest
        ),
    )

    print(
        "SOURCE_STATIONS =",
        len(
            source_names
        ),
    )

    print(
        "EXACT_CANONICAL_STATIONS =",
        len(
            exact
        ),
    )

    print(
        "REPORTABLE_FORECASTS =",
        len(
            results
        ),
    )

    print(
        "VALIDATED_ML_FORECASTS =",
        summary[
            "ml_forecasts"
        ],
    )

    print(
        "VALIDATED_BASELINE_FORECASTS =",
        summary[
            "baseline_forecasts"
        ],
    )

    print(
        "PERSISTED_FORECASTS =",
        summary[
            "persisted_forecasts"
        ],
    )

    print()
    print(
        "STRUCTURAL_HEALTH = WITHHELD"
    )

    print(
        "STRUCTURAL_RISK = WITHHELD"
    )

    print(
        "RUL = WITHHELD"
    )

    print()
    print(
        "ML9B_FORECAST=PASS"
    )


asyncio.run(
    main()
)