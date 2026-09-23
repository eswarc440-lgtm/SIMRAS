import asyncio
import csv
import json
import math
import os
import re
import statistics

from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


LEVEL_FILE = Path(
    os.environ["ML9A_LEVEL"]
)

STORAGE_FILE = Path(
    os.environ["ML9A_STORAGE"]
)

OUT = Path(
    os.environ["ML9A_OUT"]
)

ASOF = date.fromisoformat(
    os.environ["ML9A_ASOF"]
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HELPERS
# ============================================================

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


def number(value):

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
        result = float(raw)

    except Exception:
        return None

    if not math.isfinite(result):
        return None

    return result


def parse_date(value):

    raw = clean(value)

    if not raw:
        return None

    iso_value = raw

    if "T" in iso_value:

        iso_value = iso_value.split(
            "T",
            1,
        )[0]

    try:
        return date.fromisoformat(
            iso_value
        )

    except Exception:
        pass


    formats = [
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d.%m.%Y",
        "%Y/%m/%d",
        "%d-%b-%Y",
        "%d %b %Y",
        "%d-%B-%Y",
        "%d %B %Y",
    ]


    for fmt in formats:

        try:
            return datetime.strptime(
                raw,
                fmt,
            ).date()

        except Exception:
            pass

    return None


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

        for key in row.keys():

            if key not in seen:

                seen.add(key)

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


def read_csv(path):

    encodings = [
        "utf-8-sig",
        "utf-8",
        "cp1252",
    ]

    last_error = None

    for encoding in encodings:

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

        except UnicodeDecodeError as exc:

            last_error = exc


    raise RuntimeError(
        f"Could not decode {path}: "
        f"{last_error}"
    )


# ============================================================
# COLUMN DETECTION
# ============================================================

DATE_NAMES = [
    "date",
    "observation_date",
    "observation date",
    "record_date",
    "record date",
    "timestamp",
    "datetime",
    "time",
]


ENTITY_NAMES = [
    "reservoir_name",
    "reservoir name",
    "reservoir",
    "dam_name",
    "dam name",
    "station_name",
    "station name",
    "station",
    "name",
    "site_name",
    "site name",
]


ID_NAMES = [
    "reservoir_id",
    "reservoir id",
    "station_id",
    "station id",
    "site_id",
    "site id",
    "asset_code",
    "dam_id",
    "dam id",
]


LEVEL_TARGET_NAMES = [
    "reservoir_level",
    "reservoir level",
    "water_level",
    "water level",
    "level_m",
    "level m",
    "level",
    "current_level",
    "current level",
]


STORAGE_TARGET_NAMES = [
    "reservoir_storage",
    "reservoir storage",
    "live_storage",
    "live storage",
    "current_storage",
    "current storage",
    "storage_mcm",
    "storage mcm",
    "storage",
]


def find_named_column(
    columns,
    candidates,
):

    normalized = {
        normalize(column):
            column
        for column in columns
    }

    for candidate in candidates:

        key = normalize(
            candidate
        )

        if key in normalized:

            return normalized[
                key
            ]

    return None


def detect_date_column(
    columns,
    rows,
):

    named = find_named_column(
        columns,
        DATE_NAMES,
    )

    if named:
        return named


    best_column = None

    best_count = 0


    for column in columns:

        count = 0

        for row in rows[:500]:

            if parse_date(
                row.get(column)
            ):

                count += 1


        if count > best_count:

            best_count = count

            best_column = column


    if best_count >= 5:

        return best_column

    return None


def detect_numeric_target(
    columns,
    rows,
    preferred_names,
):

    named = find_named_column(
        columns,
        preferred_names,
    )

    if named:
        return named


    ranking = []


    for column in columns:

        nonempty = 0
        numeric = 0


        for row in rows[:1000]:

            raw = clean(
                row.get(column)
            )

            if not raw:
                continue

            nonempty += 1

            if number(raw) is not None:

                numeric += 1


        if nonempty == 0:
            continue


        ratio = (
            numeric
            / nonempty
        )


        ranking.append(
            (
                ratio,
                numeric,
                column,
            )
        )


    ranking.sort(
        reverse=True
    )


    for ratio, count, column in ranking:

        if ratio >= 0.80 and count >= 5:

            return column


    return None


# ============================================================
# PROFILE DATASET
# ============================================================

def profile_dataset(
    path,
    kind,
):

    columns, rows = read_csv(
        path
    )


    date_column = detect_date_column(
        columns,
        rows,
    )


    entity_column = find_named_column(
        columns,
        ENTITY_NAMES,
    )


    id_column = find_named_column(
        columns,
        ID_NAMES,
    )


    target_names = (
        LEVEL_TARGET_NAMES
        if kind == "LEVEL"
        else STORAGE_TARGET_NAMES
    )


    target_column = detect_numeric_target(
        columns,
        rows,
        target_names,
    )


    print()
    print(
        "================================================"
    )

    print(
        "DATASET =",
        kind,
    )

    print(
        "FILE =",
        path.name,
    )

    print(
        "ROWS =",
        len(rows),
    )

    print(
        "COLUMNS =",
        columns,
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
        "ID_COLUMN =",
        id_column,
    )

    print(
        "TARGET_COLUMN =",
        target_column,
    )


    parsed_dates = []

    future_dates = []

    observed_dates = []

    invalid_dates = 0

    numeric_values = []

    missing_target = 0

    entity_counts = Counter()

    entity_dates = defaultdict(
        set
    )

    observed_entity_dates = defaultdict(
        set
    )

    duplicate_counter = Counter()

    usable_rows = []

    future_rows = []


    for row in rows:

        current_date = (
            parse_date(
                row.get(
                    date_column
                )
            )
            if date_column
            else None
        )


        current_value = (
            number(
                row.get(
                    target_column
                )
            )
            if target_column
            else None
        )


        entity = ""

        if entity_column:

            entity = clean(
                row.get(
                    entity_column
                )
            )


        entity_id = ""

        if id_column:

            entity_id = clean(
                row.get(
                    id_column
                )
            )


        entity_key = normalize(
            entity_id
            or entity
        )


        if entity_key:

            entity_counts[
                entity_key
            ] += 1


        if current_date is None:

            invalid_dates += 1

        else:

            parsed_dates.append(
                current_date
            )


            if entity_key:

                entity_dates[
                    entity_key
                ].add(
                    current_date
                )


            duplicate_counter[
                (
                    entity_key,
                    current_date,
                )
            ] += 1


            if current_date > ASOF:

                future_dates.append(
                    current_date
                )

                future_rows.append(
                    row
                )

            else:

                observed_dates.append(
                    current_date
                )

                if entity_key:

                    observed_entity_dates[
                        entity_key
                    ].add(
                        current_date
                    )


        if current_value is None:

            missing_target += 1

        else:

            numeric_values.append(
                current_value
            )


        if (
            current_date is not None
            and current_date <= ASOF
            and current_value is not None
        ):

            usable_rows.append(
                {
                    "entity_key":
                        entity_key,

                    "entity_name":
                        entity,

                    "entity_id":
                        entity_id,

                    "date":
                        current_date.isoformat(),

                    "value":
                        current_value,
                }
            )


    duplicate_keys = sum(
        1
        for count
        in duplicate_counter.values()
        if count > 1
    )


    entities_30 = sum(
        1
        for dates
        in observed_entity_dates.values()
        if len(dates) >= 30
    )


    entities_90 = sum(
        1
        for dates
        in observed_entity_dates.values()
        if len(dates) >= 90
    )


    entities_180 = sum(
        1
        for dates
        in observed_entity_dates.values()
        if len(dates) >= 180
    )


    entities_365 = sum(
        1
        for dates
        in observed_entity_dates.values()
        if len(dates) >= 365
    )


    statistics_data = {}


    if numeric_values:

        sorted_values = sorted(
            numeric_values
        )

        statistics_data = {
            "min":
                min(
                    numeric_values
                ),

            "max":
                max(
                    numeric_values
                ),

            "mean":
                statistics.fmean(
                    numeric_values
                ),

            "median":
                statistics.median(
                    sorted_values
                ),
        }


    result = {
        "kind":
            kind,

        "file":
            path.name,

        "file_size_bytes":
            path.stat().st_size,

        "rows":
            len(rows),

        "columns":
            columns,

        "date_column":
            date_column,

        "entity_column":
            entity_column,

        "id_column":
            id_column,

        "target_column":
            target_column,

        "unique_entities":
            len(
                entity_counts
            ),

        "parsed_date_rows":
            len(
                parsed_dates
            ),

        "invalid_date_rows":
            invalid_dates,

        "observed_date_rows":
            len(
                observed_dates
            ),

        "future_dated_rows":
            len(
                future_dates
            ),

        "missing_target_rows":
            missing_target,

        "numeric_target_rows":
            len(
                numeric_values
            ),

        "eligible_observation_rows":
            len(
                usable_rows
            ),

        "duplicate_entity_date_keys":
            duplicate_keys,

        "date_min":
            (
                min(
                    parsed_dates
                ).isoformat()
                if parsed_dates
                else None
            ),

        "date_max":
            (
                max(
                    parsed_dates
                ).isoformat()
                if parsed_dates
                else None
            ),

        "observed_date_min":
            (
                min(
                    observed_dates
                ).isoformat()
                if observed_dates
                else None
            ),

        "observed_date_max":
            (
                max(
                    observed_dates
                ).isoformat()
                if observed_dates
                else None
            ),

        "entities_with_30_observations":
            entities_30,

        "entities_with_90_observations":
            entities_90,

        "entities_with_180_observations":
            entities_180,

        "entities_with_365_observations":
            entities_365,

        "numeric_statistics":
            statistics_data,
    }


    print(
        "UNIQUE_ENTITIES =",
        result[
            "unique_entities"
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
        "OBSERVED_DATE_RANGE =",
        result[
            "observed_date_min"
        ],
        "to",
        result[
            "observed_date_max"
        ],
    )

    print(
        "OBSERVED_ROWS =",
        result[
            "observed_date_rows"
        ],
    )

    print(
        "FUTURE_DATED_ROWS =",
        result[
            "future_dated_rows"
        ],
    )

    print(
        "ELIGIBLE_OBSERVATION_ROWS =",
        result[
            "eligible_observation_rows"
        ],
    )

    print(
        "DUPLICATE_ENTITY_DATE_KEYS =",
        duplicate_keys,
    )

    print(
        "ENTITIES_30_DAYS =",
        entities_30,
    )

    print(
        "ENTITIES_90_DAYS =",
        entities_90,
    )

    print(
        "ENTITIES_180_DAYS =",
        entities_180,
    )

    print(
        "ENTITIES_365_DAYS =",
        entities_365,
    )


    return (
        result,
        usable_rows,
        observed_entity_dates,
    )


# ============================================================
# DATABASE ASSET IDENTITY AUDIT
# ============================================================

def async_database_url():

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


async def get_dam_assets():

    engine = create_async_engine(
        async_database_url()
    )


    async with engine.connect() as conn:

        rows = (
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
                                asset_type
                                AS TEXT
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
# MAIN
# ============================================================

async def main():

    level_profile, level_rows, level_dates = (
        profile_dataset(
            LEVEL_FILE,
            "LEVEL",
        )
    )


    storage_profile, storage_rows, storage_dates = (
        profile_dataset(
            STORAGE_FILE,
            "STORAGE",
        )
    )


    assets = await get_dam_assets()


    print()
    print(
        "================================================"
    )

    print(
        "CANONICAL DAM/BARRAGE ASSETS =",
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
    # EXACT NORMALIZED NAME MATCH ONLY
    # ========================================================

    source_entities = {}


    for row in (
        level_rows
        + storage_rows
    ):

        key = normalize(
            row.get(
                "entity_name"
            )
        )

        if key:

            source_entities[
                key
            ] = row.get(
                "entity_name"
            )


    exact_matches = []

    unmatched = []


    for key, source_name in sorted(
        source_entities.items()
    ):

        candidates = assets_by_name.get(
            key,
            [],
        )


        if len(candidates) == 1:

            asset = candidates[0]

            exact_matches.append(
                {
                    "source_entity":
                        source_name,

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
                    "source_entity":
                        source_name,

                    "normalized_name":
                        key,

                    "candidate_count":
                        len(
                            candidates
                        ),

                    "status":
                        (
                            "AMBIGUOUS"
                            if len(candidates) > 1
                            else "NO_EXACT_MATCH"
                        ),
                }
            )


    # ========================================================
    # LEVEL/STORAGE TEMPORAL OVERLAP
    # ========================================================

    level_keys = {
        (
            row[
                "entity_key"
            ],
            row[
                "date"
            ],
        )
        for row in level_rows
        if row[
            "entity_key"
        ]
    }


    storage_keys = {
        (
            row[
                "entity_key"
            ],
            row[
                "date"
            ],
        )
        for row in storage_rows
        if row[
            "entity_key"
        ]
    }


    overlap_keys = (
        level_keys
        & storage_keys
    )


    overlap_entities = {
        key[0]
        for key in overlap_keys
    }


    # ========================================================
    # ENTITY READINESS
    # ========================================================

    entity_names = {}


    for row in (
        level_rows
        + storage_rows
    ):

        key = row[
            "entity_key"
        ]

        if key:

            entity_names[
                key
            ] = (
                row[
                    "entity_name"
                ]
                or row[
                    "entity_id"
                ]
            )


    readiness = []


    for key, name in sorted(
        entity_names.items()
    ):

        level_count = len(
            level_dates.get(
                key,
                set(),
            )
        )


        storage_count = len(
            storage_dates.get(
                key,
                set(),
            )
        )


        common_count = sum(
            1
            for entity_key, _
            in overlap_keys
            if entity_key == key
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
                "source_entity":
                    name,

                "normalized_entity":
                    key,

                "level_observation_dates":
                    level_count,

                "storage_observation_dates":
                    storage_count,

                "common_level_storage_dates":
                    common_count,

                "readiness":
                    status,

                "model_trained":
                    False,

                "prediction_persisted":
                    False,
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


    temporal = sum(
        1
        for row in readiness
        if row[
            "readiness"
        ]
        in {
            "STRONG_TEMPORAL_CANDIDATE",
            "TEMPORAL_CANDIDATE",
        }
    )


    # ========================================================
    # OUTPUT
    # ========================================================

    write_csv(
        OUT
        / "ml9a_exact_asset_matches.csv",
        exact_matches,
    )


    write_csv(
        OUT
        / "ml9a_unmatched_source_entities.csv",
        unmatched,
    )


    write_csv(
        OUT
        / "ml9a_entity_readiness.csv",
        readiness,
    )


    summary = {
        "version":
            "ml9a_real_ap_reservoir_audit_v1",

        "as_of_date":
            ASOF.isoformat(),

        "policy": {
            "future_rows_used_as_observations":
                False,

            "database_modified":
                False,

            "model_trained":
                False,

            "predictions_persisted":
                False,

            "structural_failure_prediction":
                False,
        },

        "level":
            level_profile,

        "storage":
            storage_profile,

        "canonical_dam_barrage_assets":
            len(
                assets
            ),

        "source_entities":
            len(
                source_entities
            ),

        "exact_asset_matches":
            len(
                exact_matches
            ),

        "unmatched_source_entities":
            len(
                unmatched
            ),

        "common_level_storage_observations":
            len(
                overlap_keys
            ),

        "common_level_storage_entities":
            len(
                overlap_entities
            ),

        "strong_temporal_candidates":
            strong,

        "temporal_candidates_90_plus":
            temporal,
    }


    (
        OUT
        / "ml9a_audit_summary.json"
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
        "ML-9A REAL AP RESERVOIR AUDIT SUMMARY"
    )

    print(
        "================================================"
    )

    print(
        "AS_OF_DATE =",
        ASOF.isoformat(),
    )

    print(
        "CANONICAL_DAM_BARRAGE_ASSETS =",
        len(
            assets
        ),
    )

    print(
        "SOURCE_ENTITIES =",
        len(
            source_entities
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
            overlap_keys
        ),
    )

    print(
        "COMMON_LEVEL_STORAGE_ENTITIES =",
        len(
            overlap_entities
        ),
    )

    print(
        "STRONG_TEMPORAL_CANDIDATES =",
        strong,
    )

    print(
        "TEMPORAL_CANDIDATES_90_PLUS =",
        temporal,
    )


    print()
    print(
        "MODEL_TRAINED = NO"
    )

    print(
        "PREDICTIONS_PERSISTED = NO"
    )

    print(
        "DATABASE_MODIFIED = NO"
    )

    print()
    print(
        "ML9A_AUDIT=PASS"
    )


asyncio.run(
    main()
)