from __future__ import annotations

import os
import re
import json
import math
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


ROOT = Path("/app")

RAW = ROOT / "data" / "official" / "dam" / "hydrology"
PROCESSED = ROOT / "data" / "processed" / "dam_barrage"
REPORTS = ROOT / "reports"

MATCH_FILE = PROCESSED / "AP_HYDROLOGY_ASSET_MATCHES.csv"

OUT_FEATURES = (
    PROCESSED
    / "AP_DAM_BARRAGE_ML_FEATURES_V1.csv"
)

OUT_DYNAMIC = (
    PROCESSED
    / "AP_DAM_BARRAGE_HYDROLOGY_FEATURES_V1.csv"
)

REPORT_JSON = (
    REPORTS
    / "STEP3_DAM_BARRAGE_FEATURE_REPORT.json"
)

REPORT_TXT = (
    REPORTS
    / "STEP3_DAM_BARRAGE_FEATURE_REPORT.txt"
)

PROCESSED.mkdir(parents=True, exist_ok=True)
REPORTS.mkdir(parents=True, exist_ok=True)

lines = []


def log(msg=""):
    print(msg, flush=True)
    lines.append(str(msg))


def clean_string(value):
    if value is None:
        return ""

    return str(value).strip()


def clean_metric(value):
    value = str(value).lower().strip()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value
    ).strip("_")

    return value[:60] or "value"


def detect_column(columns, words):
    normalized = {
        str(c).strip().lower(): c
        for c in columns
    }

    for word in words:
        word = word.lower()

        for lc, original in normalized.items():
            if lc == word:
                return original

    for word in words:
        word = word.lower()

        for lc, original in normalized.items():
            if word in lc:
                return original

    return None


NAME_WORDS = [
    "reservoir",
    "reservoir name",
    "station",
    "station name",
    "project",
    "project name",
    "dam name",
    "site",
]

CODE_WORDS = [
    "station code",
    "reservoir code",
    "project code",
    "site code",
]

DATE_WORDS = [
    "acquisition time",
    "acquisition date",
    "observation time",
    "observation date",
    "data time",
    "date time",
    "datetime",
    "timestamp",
    "recorded at",
    "reading date",
    "date",
    "time",
]

PARAMETER_WORDS = [
    "parameter type",
    "parameter name",
    "parameter",
    "variable",
    "measurement type",
]

VALUE_WORDS = [
    "value",
    "observed value",
    "measurement value",
    "reading",
    "water level",
    "reservoir level",
    "storage",
    "discharge",
    "velocity",
    "flow",
]

UNIT_WORDS = [
    "unit",
    "units",
    "parameter unit",
]


def detect_date_by_content(sample, excluded):

    best_col = None
    best_ratio = 0

    for col in sample.columns:

        if col in excluded:
            continue

        series = sample[col]

        # Avoid turning ordinary numeric columns into nanosecond dates.
        if pd.api.types.is_numeric_dtype(series):
            continue

        try:
            parsed = pd.to_datetime(
                series,
                errors="coerce",
                dayfirst=True
            )

            ratio = float(
                parsed.notna().mean()
            )

            if ratio > best_ratio:
                best_ratio = ratio
                best_col = col

        except Exception:
            pass

    if best_ratio >= 0.60:
        return best_col

    return None


def infer_file_metric(filename):

    name = filename.lower()

    if "reservoir_level" in name:
        return "reservoir_level"

    if "reservoir_storage" in name:
        return "reservoir_storage"

    if "river_velocity" in name:
        return "river_velocity_discharge"

    if "river_discharge" in name:
        return "river_discharge"

    if "scada" in name:
        return "scada"

    return "hydrology"


def detect_measurement_columns(
    sample,
    name_col,
    code_col,
    date_col,
    parameter_col,
    unit_col
):

    excluded = {
        x
        for x in [
            name_col,
            code_col,
            date_col,
            parameter_col,
            unit_col,
        ]
        if x
    }

    candidates = []

    # First prefer explicit measurement names.
    for col in sample.columns:

        if col in excluded:
            continue

        lc = str(col).lower()

        if any(
            word in lc
            for word in [
                "value",
                "level",
                "storage",
                "discharge",
                "velocity",
                "flow",
                "reading",
            ]
        ):

            numeric = pd.to_numeric(
                sample[col],
                errors="coerce"
            )

            if numeric.notna().mean() >= 0.40:
                candidates.append(col)

    # Generic Value often exists.
    value_col = detect_column(
        sample.columns,
        VALUE_WORDS
    )

    if (
        value_col
        and value_col not in excluded
        and value_col not in candidates
    ):

        numeric = pd.to_numeric(
            sample[value_col],
            errors="coerce"
        )

        if numeric.notna().mean() >= 0.40:
            candidates.insert(
                0,
                value_col
            )

    # Last fallback: select plausible numeric measurement columns,
    # excluding IDs, geographic coordinates and administrative codes.
    if not candidates:

        for col in sample.columns:

            if col in excluded:
                continue

            lc = str(col).lower()

            if any(
                x in lc
                for x in [
                    "latitude",
                    "longitude",
                    "code",
                    "id",
                    "year",
                    "month",
                    "district",
                    "state",
                ]
            ):
                continue

            numeric = pd.to_numeric(
                sample[col],
                errors="coerce"
            )

            if (
                numeric.notna().mean() >= 0.80
                and numeric.nunique(dropna=True) >= 5
            ):
                candidates.append(col)

    # Deduplicate.
    out = []

    for c in candidates:
        if c not in out:
            out.append(c)

    return out[:6]


def inspect_dataset(path):

    sample = pd.read_csv(
        path,
        nrows=500,
        low_memory=False
    )

    name_col = detect_column(
        sample.columns,
        NAME_WORDS
    )

    code_col = detect_column(
        sample.columns,
        CODE_WORDS
    )

    parameter_col = detect_column(
        sample.columns,
        PARAMETER_WORDS
    )

    unit_col = detect_column(
        sample.columns,
        UNIT_WORDS
    )

    date_col = detect_column(
        sample.columns,
        DATE_WORDS
    )

    if not date_col:

        date_col = detect_date_by_content(
            sample,
            {
                name_col,
                code_col,
                parameter_col,
                unit_col
            }
        )

    measurement_cols = detect_measurement_columns(
        sample,
        name_col,
        code_col,
        date_col,
        parameter_col,
        unit_col
    )

    return {
        "name_col": name_col,
        "code_col": code_col,
        "date_col": date_col,
        "parameter_col": parameter_col,
        "unit_col": unit_col,
        "measurement_cols": measurement_cols,
        "columns": list(sample.columns)
    }


def update_aggregate(
    store,
    key,
    count,
    total,
    sumsq,
    minimum,
    maximum,
    first_date=None,
    last_date=None,
    latest_value=None
):

    if key not in store:

        store[key] = {
            "count": int(count),
            "sum": float(total),
            "sumsq": float(sumsq),
            "min": float(minimum),
            "max": float(maximum),

            "first_date":
                first_date,

            "last_date":
                last_date,

            "latest_value":
                latest_value,
        }

        return

    current = store[key]

    current["count"] += int(count)
    current["sum"] += float(total)
    current["sumsq"] += float(sumsq)

    current["min"] = min(
        current["min"],
        float(minimum)
    )

    current["max"] = max(
        current["max"],
        float(maximum)
    )

    if first_date is not None:

        if (
            current["first_date"] is None
            or first_date < current["first_date"]
        ):
            current["first_date"] = first_date

    if last_date is not None:

        if (
            current["last_date"] is None
            or last_date > current["last_date"]
        ):
            current["last_date"] = last_date
            current["latest_value"] = latest_value


async def main():

    if not MATCH_FILE.exists():
        raise RuntimeError(
            "Step 2 match CSV not found."
        )

    match_df = pd.read_csv(
        MATCH_FILE,
        low_memory=False
    )

    # Only use already defensible matches.
    match_df = match_df[
        match_df["match_status"].isin(
            [
                "MATCHED_HIGH",
                "MATCHED_REVIEW"
            ]
        )
    ].copy()

    match_df["source_name"] = (
        match_df["source_name"]
        .astype(str)
        .str.strip()
    )

    log("=" * 110)
    log(
        "SIMRAS STEP 3 - BUILD REAL AP DAM/BARRAGE ML FEATURE DATASET"
    )
    log("=" * 110)

    csv_files = sorted(
        p
        for p in RAW.rglob("*.csv")
        if ".partial." not in p.name.lower()
        and p.stat().st_size > 1000
    )

    log("")
    log(f"Government hydrology files: {len(csv_files)}")

    aggregate = {}
    dataset_reports = []

    # ==============================================================
    # PROCESS EACH GOVERNMENT DATASET
    # ==============================================================

    for path in csv_files:

        log("")
        log("-" * 110)
        log(path.name)

        try:
            meta = inspect_dataset(
                path
            )

        except Exception as exc:

            log(
                f"[SKIP] Schema read failed: {exc}"
            )

            dataset_reports.append({
                "dataset": path.name,
                "status": "SCHEMA_FAILED",
                "error": str(exc)
            })

            continue

        log(
            f"name       : {meta['name_col']}"
        )

        log(
            f"code       : {meta['code_col']}"
        )

        log(
            f"date       : {meta['date_col']}"
        )

        log(
            f"parameter  : {meta['parameter_col']}"
        )

        log(
            f"values     : {meta['measurement_cols']}"
        )

        if (
            not meta["name_col"]
            or not meta["measurement_cols"]
        ):

            log(
                "[SKIP] Insufficient measurement schema."
            )

            dataset_reports.append({
                "dataset": path.name,
                "status": "NO_MEASUREMENT_SCHEMA",
                **meta
            })

            continue

        dataset_matches = match_df[
            match_df["dataset"]
            == path.name
        ].copy()

        if dataset_matches.empty:

            log(
                "[SKIP] No defensible SIMRAS asset match."
            )

            dataset_reports.append({
                "dataset": path.name,
                "status": "NO_MATCHED_ASSETS",
                **meta
            })

            continue

        # Same source name may appear once per SCADA parameter.
        # It should still map to the same SIMRAS asset.
        source_map = (
            dataset_matches
            .sort_values(
                "match_score",
                ascending=False
            )
            .drop_duplicates(
                "source_name"
            )
            .set_index(
                "source_name"
            )["asset_id"]
            .to_dict()
        )

        usecols = [
            x for x in [
                meta["name_col"],
                meta["code_col"],
                meta["date_col"],
                meta["parameter_col"],
                meta["unit_col"],
                *meta["measurement_cols"]
            ]
            if x
        ]

        # Deduplicate columns.
        usecols = list(
            dict.fromkeys(usecols)
        )

        parsed_rows = 0
        matched_rows = 0

        chunk_number = 0

        for chunk in pd.read_csv(
            path,
            usecols=usecols,
            chunksize=125000,
            low_memory=False
        ):

            chunk_number += 1
            parsed_rows += len(chunk)

            source_names = (
                chunk[
                    meta["name_col"]
                ]
                .astype(str)
                .str.strip()
            )

            chunk["__asset_id"] = (
                source_names.map(
                    source_map
                )
            )

            matched_chunk = chunk[
                chunk["__asset_id"]
                .notna()
            ].copy()

            if matched_chunk.empty:
                continue

            matched_rows += len(
                matched_chunk
            )

            if meta["date_col"]:

                matched_chunk[
                    "__dt"
                ] = pd.to_datetime(
                    matched_chunk[
                        meta["date_col"]
                    ],
                    errors="coerce",
                    dayfirst=True,
                    utc=True
                )

            else:
                matched_chunk[
                    "__dt"
                ] = pd.NaT

            # ------------------------------------------------------
            # LONG FORMAT: parameter + value
            # ------------------------------------------------------

            if (
                meta["parameter_col"]
                and len(
                    meta["measurement_cols"]
                ) >= 1
            ):

                # Prefer explicit Value-style column.
                value_col = (
                    detect_column(
                        meta[
                            "measurement_cols"
                        ],
                        VALUE_WORDS
                    )
                    or meta[
                        "measurement_cols"
                    ][0]
                )

                values = pd.to_numeric(
                    matched_chunk[
                        value_col
                    ],
                    errors="coerce"
                )

                metrics = (
                    matched_chunk[
                        meta[
                            "parameter_col"
                        ]
                    ]
                    .astype(str)
                    .map(clean_metric)
                )

                working = pd.DataFrame({
                    "asset_id":
                        matched_chunk[
                            "__asset_id"
                        ].astype(int),

                    "metric":
                        metrics,

                    "value":
                        values,

                    "dt":
                        matched_chunk[
                            "__dt"
                        ]
                })

                working = working[
                    working["value"].notna()
                ]

                groups = working.groupby(
                    [
                        "asset_id",
                        "metric"
                    ],
                    dropna=False
                )

                for (
                    asset_id,
                    metric
                ), g in groups:

                    vals = (
                        g["value"]
                        .astype(float)
                    )

                    dated = g[
                        g["dt"].notna()
                    ]

                    first_date = None
                    last_date = None
                    latest_value = None

                    if not dated.empty:

                        first_date = (
                            dated["dt"].min()
                        )

                        latest_idx = (
                            dated["dt"].idxmax()
                        )

                        last_date = (
                            dated.loc[
                                latest_idx,
                                "dt"
                            ]
                        )

                        latest_value = float(
                            dated.loc[
                                latest_idx,
                                "value"
                            ]
                        )

                    update_aggregate(
                        aggregate,
                        (
                            int(asset_id),
                            clean_metric(metric)
                        ),
                        len(vals),
                        vals.sum(),
                        np.square(
                            vals
                        ).sum(),
                        vals.min(),
                        vals.max(),
                        first_date,
                        last_date,
                        latest_value
                    )

            # ------------------------------------------------------
            # WIDE / SINGLE-METRIC FORMAT
            # ------------------------------------------------------

            else:

                for value_col in meta[
                    "measurement_cols"
                ]:

                    values = pd.to_numeric(
                        matched_chunk[
                            value_col
                        ],
                        errors="coerce"
                    )

                    generic = (
                        clean_metric(
                            value_col
                        )
                    )

                    if generic in {
                        "value",
                        "reading",
                        "observed_value"
                    }:
                        metric = (
                            infer_file_metric(
                                path.name
                            )
                        )
                    else:
                        metric = generic

                    working = pd.DataFrame({
                        "asset_id":
                            matched_chunk[
                                "__asset_id"
                            ].astype(int),

                        "value":
                            values,

                        "dt":
                            matched_chunk[
                                "__dt"
                            ]
                    })

                    working = working[
                        working["value"].notna()
                    ]

                    for asset_id, g in (
                        working.groupby(
                            "asset_id"
                        )
                    ):

                        vals = (
                            g["value"]
                            .astype(float)
                        )

                        dated = g[
                            g["dt"].notna()
                        ]

                        first_date = None
                        last_date = None
                        latest_value = None

                        if not dated.empty:

                            first_date = (
                                dated["dt"].min()
                            )

                            latest_idx = (
                                dated["dt"].idxmax()
                            )

                            last_date = (
                                dated.loc[
                                    latest_idx,
                                    "dt"
                                ]
                            )

                            latest_value = float(
                                dated.loc[
                                    latest_idx,
                                    "value"
                                ]
                            )

                        update_aggregate(
                            aggregate,
                            (
                                int(asset_id),
                                metric
                            ),
                            len(vals),
                            vals.sum(),
                            np.square(
                                vals
                            ).sum(),
                            vals.min(),
                            vals.max(),
                            first_date,
                            last_date,
                            latest_value
                        )

        log(
            f"rows read    : {parsed_rows:,}"
        )

        log(
            f"matched rows : {matched_rows:,}"
        )

        dataset_reports.append({
            "dataset": path.name,
            "status": "PROCESSED",
            "rows_read": parsed_rows,
            "matched_rows": matched_rows,
            **meta
        })

    # ==============================================================
    # CONVERT DYNAMIC AGGREGATES INTO FEATURES
    # ==============================================================

    dynamic_rows = []

    now = pd.Timestamp.now(
        tz="UTC"
    )

    for (
        asset_id,
        metric
    ), x in aggregate.items():

        count = max(
            int(x["count"]),
            1
        )

        mean = (
            x["sum"]
            / count
        )

        variance = max(
            (
                x["sumsq"]
                / count
            )
            - mean ** 2,
            0
        )

        std = math.sqrt(
            variance
        )

        latest = x.get(
            "latest_value"
        )

        zscore = None

        if (
            latest is not None
            and std > 1e-12
        ):
            zscore = (
                latest - mean
            ) / std

        freshness_days = None

        if x.get(
            "last_date"
        ) is not None:

            try:
                freshness_days = (
                    now
                    - x["last_date"]
                ).total_seconds() / 86400.0
            except Exception:
                pass

        dynamic_rows.append({
            "asset_id":
                asset_id,

            "metric":
                metric,

            "observation_count":
                count,

            "mean":
                mean,

            "std":
                std,

            "min":
                x["min"],

            "max":
                x["max"],

            "latest":
                latest,

            "latest_zscore":
                zscore,

            "first_observation":
                x["first_date"],

            "last_observation":
                x["last_date"],

            "freshness_days":
                freshness_days,
        })

    dynamic_df = pd.DataFrame(
        dynamic_rows
    )

    dynamic_df.to_csv(
        OUT_DYNAMIC,
        index=False
    )

    # ==============================================================
    # DATABASE + STATIC ENGINEERING FEATURES
    # ==============================================================

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv(
            "SQLALCHEMY_DATABASE_URI"
        )
        or os.getenv(
            "POSTGRES_URL"
        )
    )

    if not db_url:
        raise RuntimeError(
            "DATABASE_URL unavailable"
        )

    if db_url.startswith(
        "postgresql://"
    ):
        db_url = db_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    engine = create_async_engine(
        db_url,
        pool_pre_ping=True
    )

    async with engine.begin() as conn:

        asset_cols = {
            r[0]
            for r in (
                await conn.execute(
                    text("""
                        SELECT column_name
                        FROM information_schema.columns
                        WHERE table_schema='public'
                          AND table_name='assets'
                    """)
                )
            )
        }

        type_col = next(
            x
            for x in [
                "asset_type",
                "type",
                "infrastructure_type"
            ]
            if x in asset_cols
        )

        asset_result = await conn.execute(

                text(f"""
                    SELECT
                        a.id AS asset_id,
                        a.asset_code,
                        a.name AS asset_name,
                        CAST(
                            a."{type_col}"
                            AS TEXT
                        ) AS asset_type,

                        a.built_year,

                        e.completion_year,
                        e.commencement_year,
                        e.age_years,

                        e.dam_height_m,
                        e.dam_length_m,
                        e.dam_volume_source_value,

                        e.gate_count,
                        e.gate_type,

                        e.design_flood_source_value,
                        e.spillway_capacity_source_value,
                        e.spillway_level_m,
                        e.spillway_length_m,
                        e.spillway_type,

                        e.river_name,
                        e.dam_type,
                        e.seismic_zone,
                        e.registry_status,

                        e.nrld_no,
                        e.structure_code,

                        e.engineering_fields_available,
                        e.engineering_completeness,

                        e.confidence_score
                            AS engineering_source_confidence,

                        e.authority_level,
                        e.origin,
                        e.quality_flag

                    FROM public.assets a

                    LEFT JOIN
                    public.asset_engineering_evidence_normalized e
                      ON e.asset_id = a.id

                    WHERE UPPER(
                        CAST(
                            a."{type_col}"
                            AS TEXT
                        )
                    ) IN (
                        'DAM',
                        'BARRAGE'
                    )

                    ORDER BY a.id
                """)
        )
        asset_rows = asset_result.mappings().all()

        static_df = pd.DataFrame(
            [
                dict(x)
                for x in asset_rows
            ]
        )

        # ----------------------------------------------------------
        # AUDIT BUILT-YEAR ISSUE
        # ----------------------------------------------------------

        missing_built = int(
            static_df[
                "built_year"
            ].isna().sum()
        )

        missing_built_with_completion = int(
            (
                static_df[
                    "built_year"
                ].isna()
                &
                static_df[
                    "completion_year"
                ].notna()
            ).sum()
        )

        year_mismatch = int(
            (
                static_df[
                    "built_year"
                ].notna()
                &
                static_df[
                    "completion_year"
                ].notna()
                &
                (
                    pd.to_numeric(
                        static_df[
                            "built_year"
                        ],
                        errors="coerce"
                    )
                    !=
                    pd.to_numeric(
                        static_df[
                            "completion_year"
                        ],
                        errors="coerce"
                    )
                )
            ).sum()
        )

        # ----------------------------------------------------------
        # PIVOT DYNAMIC FEATURES
        # ----------------------------------------------------------

        feature_df = static_df.copy()

        dynamic_json_by_asset = {}

        if not dynamic_df.empty:

            for asset_id, subset in (
                dynamic_df.groupby(
                    "asset_id"
                )
            ):

                dynamic_json_by_asset[
                    int(asset_id)
                ] = {}

                for _, row in subset.iterrows():

                    metric = clean_metric(
                        row["metric"]
                    )

                    prefix = (
                        "hydro_"
                        + metric
                    )

                    values = {
                        "count":
                            row[
                                "observation_count"
                            ],

                        "mean":
                            row["mean"],

                        "std":
                            row["std"],

                        "min":
                            row["min"],

                        "max":
                            row["max"],

                        "latest":
                            row["latest"],

                        "latest_zscore":
                            row[
                                "latest_zscore"
                            ],

                        "freshness_days":
                            row[
                                "freshness_days"
                            ],
                    }

                    dynamic_json_by_asset[
                        int(asset_id)
                    ][metric] = values

                    for suffix, value in values.items():

                        feature_df.loc[
                            feature_df[
                                "asset_id"
                            ]
                            == asset_id,
                            f"{prefix}_{suffix}"
                        ] = value

        feature_df[
            "has_direct_hydrology"
        ] = (
            feature_df[
                "asset_id"
            ]
            .astype(int)
            .isin(
                dynamic_json_by_asset.keys()
            )
        )

        feature_df[
            "feature_version"
        ] = (
            "ap_dam_barrage_state_v1"
        )

        feature_df[
            "generated_at"
        ] = (
            datetime.now(
                timezone.utc
            ).isoformat()
        )

        feature_df.to_csv(
            OUT_FEATURES,
            index=False
        )

        # ----------------------------------------------------------
        # STORE SNAPSHOTS
        # ----------------------------------------------------------

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.dam_barrage_feature_snapshots
                (
                    asset_id BIGINT PRIMARY KEY,

                    asset_code TEXT,
                    asset_name TEXT,
                    asset_type TEXT,

                    feature_version TEXT
                        NOT NULL,

                    static_features JSONB
                        NOT NULL,

                    hydrology_features JSONB
                        NOT NULL,

                    has_direct_hydrology BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    generated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.dam_barrage_feature_snapshots
            """)
        )

        insert_snapshot = text("""
            INSERT INTO
            public.dam_barrage_feature_snapshots
            (
                asset_id,
                asset_code,
                asset_name,
                asset_type,
                feature_version,
                static_features,
                hydrology_features,
                has_direct_hydrology,
                generated_at
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,
                :asset_type,
                :feature_version,

                CAST(
                    :static_features
                    AS JSONB
                ),

                CAST(
                    :hydrology_features
                    AS JSONB
                ),

                :has_direct_hydrology,
                NOW()
            )
        """)

        dynamic_prefixes = tuple(
            [
                "hydro_"
            ]
        )

        for _, row in feature_df.iterrows():

            record = row.to_dict()

            static_features = {}

            for key, value in record.items():

                if key.startswith(
                    dynamic_prefixes
                ):
                    continue

                if key in {
                    "asset_id",
                    "asset_code",
                    "asset_name",
                    "asset_type",
                    "feature_version",
                    "generated_at",
                    "has_direct_hydrology"
                }:
                    continue

                if pd.isna(value):
                    value = None

                if hasattr(
                    value,
                    "item"
                ):
                    value = value.item()

                static_features[
                    key
                ] = value

            asset_id = int(
                record[
                    "asset_id"
                ]
            )

            hydrology_features = (
                dynamic_json_by_asset.get(
                    asset_id,
                    {}
                )
            )

            await conn.execute(
                insert_snapshot,
                {
                    "asset_id":
                        asset_id,

                    "asset_code":
                        record.get(
                            "asset_code"
                        ),

                    "asset_name":
                        record.get(
                            "asset_name"
                        ),

                    "asset_type":
                        record.get(
                            "asset_type"
                        ),

                    "feature_version":
                        "ap_dam_barrage_state_v1",

                    "static_features":
                        json.dumps(
                            static_features,
                            default=str
                        ),

                    "hydrology_features":
                        json.dumps(
                            hydrology_features,
                            default=str
                        ),

                    "has_direct_hydrology":
                        bool(
                            record.get(
                                "has_direct_hydrology"
                            )
                        ),
                }
            )

    # ==============================================================
    # FINAL REPORT
    # ==============================================================

    dynamic_assets = (
        dynamic_df[
            "asset_id"
        ].nunique()
        if not dynamic_df.empty
        else 0
    )

    metrics = (
        sorted(
            dynamic_df[
                "metric"
            ].dropna()
            .astype(str)
            .unique()
            .tolist()
        )
        if not dynamic_df.empty
        else []
    )

    report = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "total_assets":
            int(len(feature_df)),

        "assets_with_engineering_evidence":
            int(
                feature_df[
                    "engineering_completeness"
                ].notna().sum()
            ),

        "assets_with_dynamic_hydrology":
            int(dynamic_assets),

        "dynamic_hydrology_coverage_percent":
            round(
                dynamic_assets
                / max(
                    len(feature_df),
                    1
                )
                * 100,
                2
            ),

        "hydrology_metrics":
            metrics,

        "hydrology_metric_count":
            len(metrics),

        "missing_built_year_assets":
            missing_built,

        "missing_built_year_with_completion_year":
            missing_built_with_completion,

        "built_year_completion_year_mismatches":
            year_mismatch,

        "feature_version":
            "ap_dam_barrage_state_v1",

        "feature_csv":
            str(OUT_FEATURES),

        "dynamic_csv":
            str(OUT_DYNAMIC),

        "database_table":
            "dam_barrage_feature_snapshots",

        "dataset_processing":
            dataset_reports,
    }

    REPORT_JSON.write_text(
        json.dumps(
            report,
            indent=2,
            default=str
        ),
        encoding="utf-8"
    )

    log("")
    log("=" * 110)
    log("STEP 3 RESULT")
    log("=" * 110)

    log(
        f"Total dams+barrages              : "
        f"{len(feature_df)}"
    )

    log(
        f"Engineering feature assets       : "
        f"{report['assets_with_engineering_evidence']}"
    )

    log(
        f"Dynamic hydrology assets         : "
        f"{dynamic_assets}"
    )

    log(
        f"Dynamic hydrology coverage       : "
        f"{report['dynamic_hydrology_coverage_percent']:.2f}%"
    )

    log(
        f"Hydrology metrics discovered     : "
        f"{len(metrics)}"
    )

    for metric in metrics:
        log(
            f"  - {metric}"
        )

    log("")
    log(
        f"Assets missing built_year        : "
        f"{missing_built}"
    )

    log(
        f"Missing built_year + WRIS year   : "
        f"{missing_built_with_completion}"
    )

    log(
        f"Year mismatches to review        : "
        f"{year_mismatch}"
    )

    log("")
    log(
        "Feature version:"
    )

    log(
        "ap_dam_barrage_state_v1"
    )

    log("")
    log(
        "ML-ready CSV:"
    )

    log(
        str(OUT_FEATURES)
    )

    log("")
    log(
        "Database table:"
    )

    log(
        "public.dam_barrage_feature_snapshots"
    )

    log("=" * 110)

    REPORT_TXT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    await engine.dispose()


asyncio.run(main())

