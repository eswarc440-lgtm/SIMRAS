import asyncio
import csv
import json
import math
import os
import re

from collections import Counter, defaultdict
from datetime import datetime, date
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


LEVEL_FILE = Path(
    os.environ["ML9A1_LEVEL"]
)

STORAGE_FILE = Path(
    os.environ["ML9A1_STORAGE"]
)

OUT = Path(
    os.environ["ML9A1_OUT"]
)

ASOF = date.fromisoformat(
    os.environ["ML9A1_ASOF"]
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


LEVEL_DATE_COLUMN = (
    "Data Acquisition Time"
)

LEVEL_ENTITY_COLUMN = (
    "Station"
)

LEVEL_TARGET_COLUMN = (
    "Manual Daily Reservoir water level (m)"
)


STORAGE_DATE_COLUMN = (
    "Data Acquisition Time"
)

STORAGE_ENTITY_COLUMN = (
    "Station"
)

STORAGE_TARGET_COLUMN = (
    "Manual Daily Reservoir storage (mcm)"
)


def clean(value):

    if value is None:
        return ""

    return str(value).strip()


def normalize(value):

    value = clean(value).upper()

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


def numeric(value):

    raw = clean(value)

    if not raw:
        return None

    raw = raw.replace(
        ",",
        "",
    )

    raw = raw.replace(
        "%",
        "",
    )

    try:

        result = float(
            raw
        )

    except Exception:

        return None


    if not math.isfinite(
        result
    ):
        return None

    return result


def parse_datetime(value):

    raw = clean(value)

    if not raw:
        return None


    # --------------------------------------------------------
    # ISO parsing first
    # --------------------------------------------------------

    candidate = raw.replace(
        "Z",
        "+00:00",
    )

    try:

        parsed = datetime.fromisoformat(
            candidate
        )

        return parsed

    except Exception:

        pass


    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M",

        "%d-%m-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M",

        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",

        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",

        "%d-%b-%Y %H:%M:%S",
        "%d-%b-%Y %H:%M",

        "%d %b %Y %H:%M:%S",
        "%d %b %Y %H:%M",

        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%d.%m.%Y",
        "%d-%b-%Y",
        "%d %b %Y",
    ]


    for fmt in formats:

        try:

            return datetime.strptime(
                raw,
                fmt,
            )

        except Exception:

            pass


    # --------------------------------------------------------
    # Last conservative attempt:
    # isolate leading date portion.
    # --------------------------------------------------------

    patterns = [
        r"^(\d{4}-\d{2}-\d{2})",
        r"^(\d{2}-\d{2}-\d{4})",
        r"^(\d{2}/\d{2}/\d{4})",
    ]


    for pattern in patterns:

        match = re.search(
            pattern,
            raw,
        )

        if not match:
            continue

        value = match.group(
            1
        )

        for fmt in [
            "%Y-%m-%d",
            "%d-%m-%Y",
            "%d/%m/%Y",
        ]:

            try:

                return datetime.strptime(
                    value,
                    fmt,
                )

            except Exception:

                pass


    return None


def read_csv(path):

    for encoding in [
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ]:

        try:

            with path.open(
                "r",
                encoding=encoding,
                newline="",
            ) as handle:

                reader = csv.DictReader(
                    handle
                )

                rows = list(
                    reader
                )

                columns = (
                    reader.fieldnames
                    or []
                )

                return columns, rows

        except UnicodeDecodeError:

            continue


    raise RuntimeError(
        f"Unable to decode {path}"
    )


def write_csv(
    path,
    rows,
):

    if not rows:

        path.write_text(
            "",
            encoding="utf-8",
        )

        return


    fields = []

    seen = set()


    for row in rows:

        for key in row:

            if key not in seen:

                seen.add(
                    key
                )

                fields.append(
                    key
                )


    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


def profile(
    path,
    dataset_type,
    date_column,
    entity_column,
    target_column,
):

    columns, rows = read_csv(
        path
    )


    # --------------------------------------------------------
    # Hard fail if known government schema changed.
    # --------------------------------------------------------

    required = [
        date_column,
        entity_column,
        target_column,
    ]


    missing = [
        column
        for column in required
        if column not in columns
    ]


    if missing:

        raise RuntimeError(
            f"{dataset_type}: required columns missing: "
            f"{missing}"
        )


    print()
    print(
        "================================================"
    )

    print(
        "DATASET =",
        dataset_type,
    )

    print(
        "ROWS =",
        len(rows),
    )

    print(
        "DATE_COLUMN =",
        date_column,
    )

    print(
        "ENTITY_COLUMN =",
        entity_column,
    )

    print(
        "TARGET_COLUMN =",
        target_column,
    )


    print()
    print(
        "===== RAW SAMPLE ====="
    )


    for row in rows[:5]:

        print(
            "STATION =",
            clean(
                row.get(
                    entity_column
                )
            ),
            "| TIME =",
            clean(
                row.get(
                    date_column
                )
            ),
            "| VALUE =",
            clean(
                row.get(
                    target_column
                )
            ),
        )


    parsed_rows = []

    invalid_dates = []

    missing_values = 0

    future_rows = []

    observed_rows = []

    station_counts = Counter()

    station_dates = defaultdict(
        set
    )

    station_observed_dates = defaultdict(
        set
    )

    duplicate_daily = Counter()


    for row_number, row in enumerate(
        rows,
        start=2,
    ):

        station = clean(
            row.get(
                entity_column
            )
        )

        station_key = normalize(
            station
        )

        raw_time = clean(
            row.get(
                date_column
            )
        )

        parsed_time = parse_datetime(
            raw_time
        )

        value = numeric(
            row.get(
                target_column
            )
        )


        if station_key:

            station_counts[
                station_key
            ] += 1


        if parsed_time is None:

            invalid_dates.append(
                {
                    "row_number":
                        row_number,

                    "station":
                        station,

                    "raw_time":
                        raw_time,

                    "raw_value":
                        clean(
                            row.get(
                                target_column
                            )
                        ),
                }
            )

            continue


        observation_date = (
            parsed_time.date()
        )


        if value is None:

            missing_values += 1


        if station_key:

            station_dates[
                station_key
            ].add(
                observation_date
            )


        duplicate_daily[
            (
                station_key,
                observation_date,
            )
        ] += 1


        parsed = {
            "row_number":
                row_number,

            "station":
                station,

            "station_key":
                station_key,

            "observation_time":
                parsed_time.isoformat(),

            "observation_date":
                observation_date.isoformat(),

            "value":
                value,

            "district":
                clean(
                    row.get(
                        "District"
                    )
                ),

            "river":
                clean(
                    row.get(
                        "River"
                    )
                ),

            "basin":
                clean(
                    row.get(
                        "Basin"
                    )
                ),

            "latitude":
                numeric(
                    row.get(
                        "Latitude"
                    )
                ),

            "longitude":
                numeric(
                    row.get(
                        "Longitude"
                    )
                ),

            "agency":
                clean(
                    row.get(
                        "Agency"
                    )
                ),
        }


        parsed_rows.append(
            parsed
        )


        if observation_date > ASOF:

            future_rows.append(
                parsed
            )

        else:

            observed_rows.append(
                parsed
            )

            if station_key:

                station_observed_dates[
                    station_key
                ].add(
                    observation_date
                )


    eligible = [
        row
        for row in observed_rows
        if row[
            "value"
        ] is not None
        and row[
            "station_key"
        ]
    ]


    duplicate_keys = sum(
        1
        for value
        in duplicate_daily.values()
        if value > 1
    )


    observed_dates = [
        date.fromisoformat(
            row[
                "observation_date"
            ]
        )
        for row in observed_rows
    ]


    all_dates = [
        date.fromisoformat(
            row[
                "observation_date"
            ]
        )
        for row in parsed_rows
    ]


    result = {
        "dataset":
            dataset_type,

        "rows":
            len(rows),

        "unique_stations":
            len(
                station_counts
            ),

        "parsed_date_rows":
            len(
                parsed_rows
            ),

        "invalid_date_rows":
            len(
                invalid_dates
            ),

        "observed_rows":
            len(
                observed_rows
            ),

        "future_rows":
            len(
                future_rows
            ),

        "eligible_rows":
            len(
                eligible
            ),

        "missing_target_rows":
            missing_values,

        "duplicate_station_date_keys":
            duplicate_keys,

        "date_min":
            (
                min(
                    all_dates
                ).isoformat()
                if all_dates
                else None
            ),

        "date_max":
            (
                max(
                    all_dates
                ).isoformat()
                if all_dates
                else None
            ),

        "observed_min":
            (
                min(
                    observed_dates
                ).isoformat()
                if observed_dates
                else None
            ),

        "observed_max":
            (
                max(
                    observed_dates
                ).isoformat()
                if observed_dates
                else None
            ),

        "stations_30_days":
            sum(
                1
                for dates
                in station_observed_dates.values()
                if len(dates) >= 30
            ),

        "stations_90_days":
            sum(
                1
                for dates
                in station_observed_dates.values()
                if len(dates) >= 90
            ),

        "stations_180_days":
            sum(
                1
                for dates
                in station_observed_dates.values()
                if len(dates) >= 180
            ),

        "stations_365_days":
            sum(
                1
                for dates
                in station_observed_dates.values()
                if len(dates) >= 365
            ),
    }


    print()
    print(
        "UNIQUE_STATIONS =",
        result[
            "unique_stations"
        ],
    )

    print(
        "PARSED_DATE_ROWS =",
        result[
            "parsed_date_rows"
        ],
    )

    print(
        "INVALID_DATE_ROWS =",
        result[
            "invalid_date_rows"
        ],
    )

    print(
        "DATE_RANGE =",
        result[
            "date_min"
        ],
        "to",
        result[
            "date_max"
        ],
    )

    print(
        "OBSERVED_RANGE =",
        result[
            "observed_min"
        ],
        "to",
        result[
            "observed_max"
        ],
    )

    print(
        "OBSERVED_ROWS =",
        result[
            "observed_rows"
        ],
    )

    print(
        "FUTURE_ROWS =",
        result[
            "future_rows"
        ],
    )

    print(
        "ELIGIBLE_ROWS =",
        result[
            "eligible_rows"
        ],
    )

    print(
        "STATIONS_30_DAYS =",
        result[
            "stations_30_days"
        ],
    )

    print(
        "STATIONS_90_DAYS =",
        result[
            "stations_90_days"
        ],
    )

    print(
        "STATIONS_180_DAYS =",
        result[
            "stations_180_days"
        ],
    )

    print(
        "STATIONS_365_DAYS =",
        result[
            "stations_365_days"
        ],
    )


    return (
        result,
        eligible,
        invalid_dates,
        station_observed_dates,
    )


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


async def load_assets():

    engine = create_async_engine(
        database_url()
    )


    async with engine.connect() as conn:

        records = (
            await conn.execute(
                text(
                    """
                    SELECT
                        id,
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
                    ORDER BY asset_code
                    """
                )
            )
        ).mappings().all()


    await engine.dispose()


    return [
        dict(row)
        for row in records
    ]


async def main():

    (
        level_profile,
        level_rows,
        level_invalid,
        level_dates,
    ) = profile(
        LEVEL_FILE,
        "LEVEL",
        LEVEL_DATE_COLUMN,
        LEVEL_ENTITY_COLUMN,
        LEVEL_TARGET_COLUMN,
    )


    (
        storage_profile,
        storage_rows,
        storage_invalid,
        storage_dates,
    ) = profile(
        STORAGE_FILE,
        "STORAGE",
        STORAGE_DATE_COLUMN,
        STORAGE_ENTITY_COLUMN,
        STORAGE_TARGET_COLUMN,
    )


    assets = await load_assets()


    print()
    print(
        "CANONICAL_DAM_BARRAGE_ASSETS =",
        len(assets),
    )


    assets_by_name = defaultdict(
        list
    )


    for asset in assets:

        key = normalize(
            asset.get(
                "name"
            )
        )

        if key:

            assets_by_name[
                key
            ].append(
                asset
            )


    # ========================================================
    # SOURCE STATIONS
    # ========================================================

    source_station_names = {}


    for row in (
        level_rows
        + storage_rows
    ):

        key = row[
            "station_key"
        ]

        if key:

            source_station_names[
                key
            ] = row[
                "station"
            ]


    exact_matches = []

    unmatched = []


    for key, station in sorted(
        source_station_names.items()
    ):

        matches = assets_by_name.get(
            key,
            [],
        )


        if len(matches) == 1:

            asset = matches[0]

            exact_matches.append(
                {
                    "station":
                        station,

                    "asset_code":
                        asset[
                            "asset_code"
                        ],

                    "asset_name":
                        asset[
                            "name"
                        ],

                    "asset_type":
                        str(
                            asset[
                                "asset_type"
                            ]
                        ),

                    "district":
                        asset[
                            "district"
                        ],

                    "identity_status":
                        str(
                            asset[
                                "identity_status"
                            ]
                        ),

                    "match_method":
                        "EXACT_NORMALIZED_NAME",
                }
            )

        else:

            unmatched.append(
                {
                    "station":
                        station,

                    "normalized_station":
                        key,

                    "exact_asset_candidates":
                        len(
                            matches
                        ),

                    "status":
                        (
                            "AMBIGUOUS"
                            if len(matches) > 1
                            else "NO_EXACT_MATCH"
                        ),
                }
            )


    # ========================================================
    # LEVEL + STORAGE OVERLAP
    # ========================================================

    level_keys = {
        (
            row[
                "station_key"
            ],
            row[
                "observation_date"
            ],
        )
        for row in level_rows
    }


    storage_keys = {
        (
            row[
                "station_key"
            ],
            row[
                "observation_date"
            ],
        )
        for row in storage_rows
    }


    common = (
        level_keys
        & storage_keys
    )


    common_by_station = Counter(
        station
        for station, _
        in common
    )


    readiness = []


    for station_key, station_name in sorted(
        source_station_names.items()
    ):

        level_count = len(
            level_dates.get(
                station_key,
                set(),
            )
        )

        storage_count = len(
            storage_dates.get(
                station_key,
                set(),
            )
        )

        common_count = common_by_station.get(
            station_key,
            0,
        )


        if common_count >= 180:

            status = (
                "STRONG_TEMPORAL_CANDIDATE"
            )

        elif common_count >= 90:

            status = (
                "TEMPORAL_CANDIDATE"
            )

        elif common_count >= 30:

            status = (
                "SHORT_SERIES_CANDIDATE"
            )

        else:

            status = (
                "INSUFFICIENT_TEMPORAL_HISTORY"
            )


        readiness.append(
            {
                "station":
                    station_name,

                "level_days":
                    level_count,

                "storage_days":
                    storage_count,

                "common_days":
                    common_count,

                "readiness":
                    status,
            }
        )


    strong = sum(
        1
        for row in readiness
        if row[
            "readiness"
        ]
        == "STRONG_TEMPORAL_CANDIDATE"
    )


    temporal_90 = sum(
        1
        for row in readiness
        if row[
            "common_days"
        ] >= 90
    )


    write_csv(
        OUT
        / "ml9a1_exact_asset_matches.csv",
        exact_matches,
    )

    write_csv(
        OUT
        / "ml9a1_unmatched_stations.csv",
        unmatched,
    )

    write_csv(
        OUT
        / "ml9a1_entity_readiness.csv",
        readiness,
    )

    write_csv(
        OUT
        / "ml9a1_level_invalid_dates.csv",
        level_invalid,
    )

    write_csv(
        OUT
        / "ml9a1_storage_invalid_dates.csv",
        storage_invalid,
    )


    summary = {
        "version":
            "ml9a1_corrected_reservoir_audit_v1",

        "as_of_date":
            ASOF.isoformat(),

        "level":
            level_profile,

        "storage":
            storage_profile,

        "canonical_assets":
            len(
                assets
            ),

        "source_stations":
            len(
                source_station_names
            ),

        "exact_asset_matches":
            len(
                exact_matches
            ),

        "unmatched_stations":
            len(
                unmatched
            ),

        "common_level_storage_observations":
            len(
                common
            ),

        "common_level_storage_stations":
            len(
                common_by_station
            ),

        "strong_temporal_candidates":
            strong,

        "temporal_candidates_90_plus":
            temporal_90,

        "database_modified":
            False,

        "model_trained":
            False,

        "predictions_persisted":
            False,
    }


    (
        OUT
        / "ml9a1_summary.json"
    ).write_text(
        json.dumps(
            summary,
            indent=2,
        ),
        encoding="utf-8",
    )


    print()
    print(
        "================================================"
    )

    print(
        " ML-9A.1 CORRECTED AUDIT SUMMARY"
    )

    print(
        "================================================"
    )

    print(
        "SOURCE_STATIONS =",
        len(
            source_station_names
        ),
    )

    print(
        "EXACT_ASSET_MATCHES =",
        len(
            exact_matches
        ),
    )

    print(
        "COMMON_LEVEL_STORAGE_OBSERVATIONS =",
        len(
            common
        ),
    )

    print(
        "COMMON_LEVEL_STORAGE_STATIONS =",
        len(
            common_by_station
        ),
    )

    print(
        "STRONG_TEMPORAL_CANDIDATES =",
        strong,
    )

    print(
        "TEMPORAL_CANDIDATES_90_PLUS =",
        temporal_90,
    )

    print()
    print(
        "DATABASE_MODIFIED = NO"
    )

    print(
        "MODEL_TRAINED = NO"
    )

    print(
        "PREDICTIONS_PERSISTED = NO"
    )

    print()
    print(
        "ML9A1_AUDIT=PASS"
    )


asyncio.run(
    main()
)