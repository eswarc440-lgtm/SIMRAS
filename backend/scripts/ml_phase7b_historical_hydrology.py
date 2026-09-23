from __future__ import annotations

import asyncio
import csv
import json
import os
import re
from pathlib import Path

import asyncpg
import pandas as pd


ROOTS = [
    Path("/app/data"),
]

OUTPUT = Path(
    "/app/data/processed/ml_phase7b"
)

OUTPUT.mkdir(
    parents=True,
    exist_ok=True,
)


FILE_HINT = re.compile(
    r"(hydro|reservoir|water|level|storage|nwdp|wris)",
    re.I,
)

SKIP_HINT = re.compile(
    r"(ml_phase7|audit|prediction|forecast|synthetic|demo)",
    re.I,
)

ASSET_HINTS = [
    "asset_code",
    "asset_id",
    "dam_code",
    "barrage_code",
    "reservoir_code",
    "station_code",
    "station_id",
    "station",
]

DATE_HINTS = [
    "date",
    "datetime",
    "timestamp",
    "time",
    "observation_date",
    "observation_time",
    "measurement_date",
]

LEVEL_HINT = re.compile(
    r"(water.*level|reservoir.*level|level.*m|^level$)",
    re.I,
)

STORAGE_HINT = re.compile(
    r"(storage.*mcm|reservoir.*storage|current.*storage|^storage$)",
    re.I,
)


def normalize(name):
    return re.sub(
        r"[^a-z0-9]+",
        "_",
        str(name).strip().lower(),
    ).strip("_")


def choose_column(columns, exact_candidates):

    norm_map = {
        normalize(c): c
        for c in columns
    }

    for candidate in exact_candidates:

        if candidate in norm_map:
            return norm_map[candidate]

    return None


def first_regex_column(columns, regex):

    for column in columns:

        if regex.search(
            normalize(column)
        ):
            return column

    return None


async def db_metadata():

    conn = await asyncpg.connect(
        host=os.getenv(
            "SIMRAS_DB_HOST",
            "db",
        ),
        port=int(
            os.getenv(
                "SIMRAS_DB_PORT",
                "5432",
            )
        ),
        user=os.environ[
            "SIMRAS_DB_USER"
        ],
        password=os.getenv(
            "SIMRAS_DB_PASSWORD",
            "",
        ),
        database=os.environ[
            "SIMRAS_DB_NAME"
        ],
    )

    try:

        # -----------------------------------------------
        # Engineering profile schema
        # -----------------------------------------------

        profile_columns = await conn.fetch(
            """
            SELECT
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='dam_barrage_engineering_profiles'
            ORDER BY ordinal_position
            """
        )


        # -----------------------------------------------
        # Canonical assets
        # -----------------------------------------------

        assets = await conn.fetch(
            """
            SELECT
                a.asset_code,
                a.name,
                LOWER(a.asset_type) AS asset_type
            FROM public.assets a
            WHERE LOWER(a.asset_type)
                IN ('dam','barrage')
            ORDER BY a.asset_code
            """
        )


        # -----------------------------------------------
        # Profile rows as JSON
        # -----------------------------------------------

        profiles = await conn.fetch(
            """
            SELECT
                to_jsonb(p)::text AS j
            FROM public.dam_barrage_engineering_profiles p
            """
        )


        return (
            [dict(r) for r in profile_columns],
            [dict(r) for r in assets],
            [
                json.loads(r["j"])
                for r in profiles
            ],
        )


    finally:

        await conn.close()


async def main():

    (
        profile_columns,
        assets,
        profiles,
    ) = await db_metadata()


    asset_codes = {
        str(row["asset_code"])
        for row in assets
        if row.get("asset_code")
    }


    print()
    print("=" * 130)
    print("DAM/BARRAGE ENGINEERING PROFILE COLUMNS")
    print("=" * 130)

    for row in profile_columns:

        print(
            f"{row['column_name']:<50}"
            f"{row['data_type']}"
        )


    # ====================================================
    # DISCOVER DESIGN THRESHOLDS
    # ====================================================

    profile_keys = set()

    for row in profiles:
        profile_keys.update(row.keys())


    threshold_keys = sorted(
        key
        for key in profile_keys
        if re.search(
            r"(frl|full.*reservoir|maximum.*water|mwl|"
            r"gross.*storage|effective.*storage|live.*storage|"
            r"capacity)",
            key,
            re.I,
        )
    )


    print()
    print("=" * 130)
    print("DESIGN THRESHOLD / CAPACITY FIELDS")
    print("=" * 130)

    if threshold_keys:

        for key in threshold_keys:

            present = sum(
                1
                for row in profiles
                if row.get(key)
                not in (
                    None,
                    "",
                )
            )

            print(
                f"{key:<55}"
                f"non-null={present}"
            )

    else:

        print(
            "No explicit design threshold fields discovered."
        )


    # ====================================================
    # FILE DISCOVERY
    # ====================================================

    candidate_files = []

    for root in ROOTS:

        if not root.exists():
            continue

        for path in root.rglob("*"):

            if not path.is_file():
                continue

            if path.suffix.lower() not in {
                ".csv",
                ".txt",
            }:
                continue

            path_text = str(path)

            if SKIP_HINT.search(path_text):
                continue

            if not FILE_HINT.search(
                path.name
            ):
                continue


            size_mb = (
                path.stat().st_size
                / 1024
                / 1024
            )

            try:

                sample = pd.read_csv(
                    path,
                    nrows=50,
                    low_memory=False,
                )

            except Exception:

                try:

                    sample = pd.read_csv(
                        path,
                        nrows=50,
                        sep=None,
                        engine="python",
                    )

                except Exception:
                    continue


            columns = list(
                sample.columns
            )


            asset_col = choose_column(
                columns,
                ASSET_HINTS,
            )

            date_col = choose_column(
                columns,
                DATE_HINTS,
            )


            if date_col is None:

                for column in columns:

                    if re.search(
                        r"(date|time)",
                        normalize(column),
                    ):
                        date_col = column
                        break


            level_col = first_regex_column(
                columns,
                LEVEL_HINT,
            )

            storage_col = first_regex_column(
                columns,
                STORAGE_HINT,
            )


            if (
                level_col is None
                and storage_col is None
            ):
                continue


            candidate_files.append(
                {
                    "path":
                        str(path),

                    "file_name":
                        path.name,

                    "size_mb":
                        round(
                            size_mb,
                            3,
                        ),

                    "asset_column":
                        asset_col or "",

                    "date_column":
                        date_col or "",

                    "level_column":
                        level_col or "",

                    "storage_column":
                        storage_col or "",

                    "columns":
                        ";".join(
                            str(c)
                            for c in columns
                        ),
                }
            )


    candidate_files.sort(
        key=lambda x:
            -float(x["size_mb"])
    )


    print()
    print("=" * 130)
    print("HISTORICAL HYDROLOGY FILE CANDIDATES")
    print("=" * 130)


    for item in candidate_files[:50]:

        print()
        print(
            "FILE   :",
            item["path"],
        )

        print(
            "SIZE MB:",
            item["size_mb"],
        )

        print(
            "ASSET  :",
            item["asset_column"],
        )

        print(
            "DATE   :",
            item["date_column"],
        )

        print(
            "LEVEL  :",
            item["level_column"],
        )

        print(
            "STORAGE:",
            item["storage_column"],
        )


    # ====================================================
    # MATERIALIZE FILES THAT ALREADY CONTAIN ASSET_CODE
    # ====================================================

    frames = []

    source_summary = []


    for item in candidate_files:

        asset_col = item[
            "asset_column"
        ]

        date_col = item[
            "date_column"
        ]

        level_col = item[
            "level_column"
        ]

        storage_col = item[
            "storage_column"
        ]


        if not asset_col:
            continue

        if not date_col:
            continue


        path = Path(
            item["path"]
        )


        try:

            df = pd.read_csv(
                path,
                low_memory=False,
            )

        except Exception:

            try:

                df = pd.read_csv(
                    path,
                    sep=None,
                    engine="python",
                )

            except Exception:
                continue


        if asset_col not in df.columns:
            continue

        if date_col not in df.columns:
            continue


        working = pd.DataFrame()

        working["asset_reference"] = (
            df[asset_col]
            .astype(str)
            .str.strip()
        )

        working["observation_time"] = (
            pd.to_datetime(
                df[date_col],
                errors="coerce",
            )
        )


        if (
            level_col
            and level_col in df.columns
        ):

            working["water_level_m"] = (
                pd.to_numeric(
                    df[level_col],
                    errors="coerce",
                )
            )

        else:

            working[
                "water_level_m"
            ] = float("nan")


        if (
            storage_col
            and storage_col in df.columns
        ):

            working[
                "storage_mcm"
            ] = pd.to_numeric(
                df[storage_col],
                errors="coerce",
            )

        else:

            working[
                "storage_mcm"
            ] = float("nan")


        working = working[
            working[
                "observation_time"
            ].notna()
            &
            (
                working[
                    "water_level_m"
                ].notna()
                |
                working[
                    "storage_mcm"
                ].notna()
            )
        ].copy()


        # Direct canonical asset-code matches only.
        direct = working[
            working[
                "asset_reference"
            ].isin(
                asset_codes
            )
        ].copy()


        if len(direct) == 0:
            continue


        direct[
            "asset_code"
        ] = direct[
            "asset_reference"
        ]


        direct[
            "source_file"
        ] = path.name


        frames.append(
            direct[
                [
                    "asset_code",
                    "observation_time",
                    "water_level_m",
                    "storage_mcm",
                    "source_file",
                ]
            ]
        )


        source_summary.append(
            {
                "file_name":
                    path.name,

                "raw_rows":
                    len(df),

                "usable_rows":
                    len(working),

                "direct_asset_matches":
                    len(direct),

                "distinct_assets":
                    direct[
                        "asset_code"
                    ].nunique(),
            }
        )


    if frames:

        observations = pd.concat(
            frames,
            ignore_index=True,
        )

        observations = (
            observations
            .drop_duplicates(
                subset=[
                    "asset_code",
                    "observation_time",
                    "water_level_m",
                    "storage_mcm",
                ]
            )
            .sort_values(
                [
                    "asset_code",
                    "observation_time",
                ]
            )
        )

    else:

        observations = pd.DataFrame(
            columns=[
                "asset_code",
                "observation_time",
                "water_level_m",
                "storage_mcm",
                "source_file",
            ]
        )


    # ====================================================
    # EXPORT
    # ====================================================

    candidates_csv = (
        OUTPUT
        / "SIMRAS_HISTORICAL_HYDROLOGY_FILES_V1.csv"
    )

    observations_csv = (
        OUTPUT
        / "SIMRAS_HISTORICAL_HYDROLOGY_DIRECT_MATCH_V1.csv"
    )

    source_csv = (
        OUTPUT
        / "SIMRAS_HYDROLOGY_DIRECT_MATCH_SUMMARY_V1.csv"
    )

    audit_json = (
        OUTPUT
        / "SIMRAS_HISTORICAL_HYDROLOGY_AUDIT_V1.json"
    )


    with candidates_csv.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        fields = [
            "path",
            "file_name",
            "size_mb",
            "asset_column",
            "date_column",
            "level_column",
            "storage_column",
            "columns",
        ]

        writer = csv.DictWriter(
            f,
            fieldnames=fields,
        )

        writer.writeheader()
        writer.writerows(
            candidate_files
        )


    observations.to_csv(
        observations_csv,
        index=False,
    )


    pd.DataFrame(
        source_summary
    ).to_csv(
        source_csv,
        index=False,
    )


    audit = {
        "canonical_dam_barrage_assets":
            len(asset_codes),

        "profile_rows":
            len(profiles),

        "threshold_fields":
            threshold_keys,

        "candidate_files":
            candidate_files,

        "direct_matched_rows":
            len(observations),

        "direct_matched_assets":
            int(
                observations[
                    "asset_code"
                ].nunique()
            )
            if len(observations)
            else 0,

        "source_summary":
            source_summary,
    }


    audit_json.write_text(
        json.dumps(
            audit,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


    print()
    print("=" * 130)
    print("HISTORICAL DIRECT MATCH RESULT")
    print("=" * 130)

    print(
        "Candidate files       :",
        len(candidate_files),
    )

    print(
        "Canonical assets      :",
        len(asset_codes),
    )

    print(
        "Matched observations  :",
        len(observations),
    )

    if len(observations):

        print(
            "Matched assets        :",
            observations[
                "asset_code"
            ].nunique(),
        )

        print(
            "First observation     :",
            observations[
                "observation_time"
            ].min(),
        )

        print(
            "Latest observation    :",
            observations[
                "observation_time"
            ].max(),
        )

        print(
            "Level observations    :",
            observations[
                "water_level_m"
            ].notna().sum(),
        )

        print(
            "Storage observations  :",
            observations[
                "storage_mcm"
            ].notna().sum(),
        )


    print()
    print("OUTPUTS")
    print("Files        :", candidates_csv)
    print("Observations :", observations_csv)
    print("Sources      :", source_csv)
    print("Audit        :", audit_json)

    print("=" * 130)


asyncio.run(main())
