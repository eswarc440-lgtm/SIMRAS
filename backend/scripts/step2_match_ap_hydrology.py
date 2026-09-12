from __future__ import annotations

import os
import re
import json
import math
import asyncio
from pathlib import Path
from collections import defaultdict
from difflib import SequenceMatcher
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


ROOT = Path("/app")

RAW_ROOT = ROOT / "data" / "official" / "dam" / "hydrology"
OUT_ROOT = ROOT / "data" / "processed" / "dam_barrage"
REPORT_ROOT = ROOT / "reports"

OUT_ROOT.mkdir(parents=True, exist_ok=True)
REPORT_ROOT.mkdir(parents=True, exist_ok=True)

MATCH_CSV = OUT_ROOT / "AP_HYDROLOGY_ASSET_MATCHES.csv"
ENTITY_CSV = OUT_ROOT / "AP_HYDROLOGY_SOURCE_ENTITIES.csv"

REPORT_JSON = REPORT_ROOT / "STEP2_AP_HYDROLOGY_MATCH_REPORT.json"
REPORT_TXT = REPORT_ROOT / "STEP2_AP_HYDROLOGY_MATCH_REPORT.txt"

lines = []


def log(msg=""):
    print(msg, flush=True)
    lines.append(str(msg))


def norm(value):
    if value is None:
        return ""

    s = str(value).lower().strip()

    replacements = {
        "&": " and ",
        "/": " ",
        "-": " ",
        "_": " ",
        ",": " ",
        ".": " ",
        "(": " ",
        ")": " ",
    }

    for a, b in replacements.items():
        s = s.replace(a, b)

    s = re.sub(
        r"\b(dam|reservoir|barrage|project|scheme|lake)\b",
        " ",
        s
    )

    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s)

    return s.strip()


def similarity(a, b):
    a = norm(a)
    b = norm(b)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    return SequenceMatcher(
        None,
        a,
        b
    ).ratio()


def haversine(lat1, lon1, lat2, lon2):

    if None in (lat1, lon1, lat2, lon2):
        return None

    try:
        lat1 = float(lat1)
        lon1 = float(lon1)
        lat2 = float(lat2)
        lon2 = float(lon2)
    except Exception:
        return None

    r = 6371.0088

    p1 = math.radians(lat1)
    p2 = math.radians(lat2)

    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)

    a = (
        math.sin(dp / 2) ** 2
        + math.cos(p1)
        * math.cos(p2)
        * math.sin(dl / 2) ** 2
    )

    return (
        2
        * r
        * math.atan2(
            math.sqrt(a),
            math.sqrt(1 - a)
        )
    )


def detect_column(columns, patterns):

    lower = {
        str(c).lower().strip(): c
        for c in columns
    }

    # Exact/strong match first.
    for pattern in patterns:
        for lc, original in lower.items():
            if lc == pattern:
                return original

    for pattern in patterns:
        for lc, original in lower.items():
            if pattern in lc:
                return original

    return None


NAME_PATTERNS = [
    "reservoir_name",
    "reservoir",
    "project_name",
    "project",
    "dam_name",
    "station_name",
    "station",
    "site_name",
    "site",
    "location_name",
    "location",
    "name",
]

LAT_PATTERNS = [
    "latitude",
    "lat",
]

LON_PATTERNS = [
    "longitude",
    "long",
    "lon",
    "lng",
]

CODE_PATTERNS = [
    "station_code",
    "reservoir_code",
    "project_code",
    "site_code",
    "code",
]

PARAMETER_PATTERNS = [
    "parameter_name",
    "parameter",
    "param_type",
    "parameter_type",
]

DATE_PATTERNS = [
    "acquisition_time",
    "observation_time",
    "observed_at",
    "timestamp",
    "datetime",
    "date_time",
    "date",
]


def inspect_csv(path):

    try:
        sample = pd.read_csv(
            path,
            nrows=30,
            low_memory=False
        )

    except Exception as exc:

        return {
            "path": str(path),
            "status": "READ_FAILED",
            "error": str(exc)
        }

    return {
        "path": str(path),
        "status": "OK",
        "columns": list(sample.columns),
        "name_col": detect_column(
            sample.columns,
            NAME_PATTERNS
        ),
        "lat_col": detect_column(
            sample.columns,
            LAT_PATTERNS
        ),
        "lon_col": detect_column(
            sample.columns,
            LON_PATTERNS
        ),
        "code_col": detect_column(
            sample.columns,
            CODE_PATTERNS
        ),
        "parameter_col": detect_column(
            sample.columns,
            PARAMETER_PATTERNS
        ),
        "date_col": detect_column(
            sample.columns,
            DATE_PATTERNS
        ),
    }


def extract_entities(path, metadata):

    name_col = metadata.get("name_col")
    lat_col = metadata.get("lat_col")
    lon_col = metadata.get("lon_col")
    code_col = metadata.get("code_col")
    parameter_col = metadata.get("parameter_col")

    if not name_col:
        return []

    usecols = [
        c for c in [
            name_col,
            lat_col,
            lon_col,
            code_col,
            parameter_col,
        ]
        if c
    ]

    entities = {}

    chunk_size = 150000

    for chunk in pd.read_csv(
        path,
        usecols=usecols,
        chunksize=chunk_size,
        low_memory=False
    ):

        for row in chunk.itertuples(
            index=False,
            name=None
        ):

            record = dict(
                zip(
                    usecols,
                    row
                )
            )

            raw_name = record.get(
                name_col
            )

            if pd.isna(raw_name):
                continue

            raw_name = str(
                raw_name
            ).strip()

            if not raw_name:
                continue

            source_code = None

            if code_col:
                value = record.get(code_col)
                if not pd.isna(value):
                    source_code = str(value)

            parameter = None

            if parameter_col:
                value = record.get(parameter_col)
                if not pd.isna(value):
                    parameter = str(value)

            lat = None
            lon = None

            if lat_col:
                value = pd.to_numeric(
                    record.get(lat_col),
                    errors="coerce"
                )
                if not pd.isna(value):
                    lat = float(value)

            if lon_col:
                value = pd.to_numeric(
                    record.get(lon_col),
                    errors="coerce"
                )
                if not pd.isna(value):
                    lon = float(value)

            key = (
                norm(raw_name),
                source_code or "",
                parameter or ""
            )

            if key not in entities:

                entities[key] = {
                    "dataset": path.name,
                    "source_name": raw_name,
                    "normalized_name": norm(raw_name),
                    "source_code": source_code,
                    "parameter": parameter,
                    "latitude": lat,
                    "longitude": lon,
                    "row_count": 1,
                }

            else:

                entities[key][
                    "row_count"
                ] += 1

                if (
                    entities[key]["latitude"]
                    is None
                    and lat is not None
                ):
                    entities[key]["latitude"] = lat

                if (
                    entities[key]["longitude"]
                    is None
                    and lon is not None
                ):
                    entities[key]["longitude"] = lon

    return list(
        entities.values()
    )


async def main():

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
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

    log("=" * 105)
    log(
        "SIMRAS STEP 2 - MATCH AP GOVERNMENT HYDROLOGY "
        "TO DAM / BARRAGE ASSETS"
    )
    log("=" * 105)

    # ---------------------------------------------------------
    # FILE DISCOVERY
    # ---------------------------------------------------------

    csv_files = sorted(
        p
        for p in RAW_ROOT.rglob("*.csv")
        if ".partial." not in p.name.lower()
        and p.stat().st_size > 1000
    )

    log("")
    log("1. GOVERNMENT DATASETS")
    log("-" * 105)

    metadata = []

    for path in csv_files:

        info = inspect_csv(
            path
        )

        metadata.append(
            info
        )

        log("")
        log(path.name)

        if info["status"] != "OK":
            log(
                f"  READ FAILED: "
                f"{info.get('error')}"
            )
            continue

        log(
            f"  name       : "
            f"{info.get('name_col')}"
        )

        log(
            f"  code       : "
            f"{info.get('code_col')}"
        )

        log(
            f"  latitude   : "
            f"{info.get('lat_col')}"
        )

        log(
            f"  longitude  : "
            f"{info.get('lon_col')}"
        )

        log(
            f"  parameter  : "
            f"{info.get('parameter_col')}"
        )

        log(
            f"  date       : "
            f"{info.get('date_col')}"
        )

    # ---------------------------------------------------------
    # LOAD SIMRAS DAM/BARRAGE ASSETS
    # ---------------------------------------------------------

    async with engine.connect() as conn:

        asset_cols_result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='assets'
            """)
        )

        asset_cols = {
            r[0]
            for r in asset_cols_result
        }

        type_col = next(
            (
                x for x in [
                    "asset_type",
                    "type",
                    "infrastructure_type"
                ]
                if x in asset_cols
            ),
            None
        )

        if not type_col:
            raise RuntimeError(
                "Asset type column not found"
            )

        selected = [
            c for c in [
                "id",
                "asset_code",
                "name",
                type_col,
                "latitude",
                "longitude",
                "built_year",
                "district",
            ]
            if c in asset_cols
        ]

        qcols = ",".join(
            '"' + c + '"'
            for c in selected
        )

        query = text(
            f"""
            SELECT {qcols}
            FROM public.assets
            WHERE UPPER(CAST("{type_col}" AS TEXT))
                  IN ('DAM','BARRAGE')
            """
        )

        assets = [
            dict(r)
            for r in (
                await conn.execute(query)
            ).mappings().all()
        ]

        log("")
        log("2. SIMRAS ASSETS")
        log("-" * 105)
        log(
            f"Dams/barrages loaded: "
            f"{len(assets)}"
        )

        # -----------------------------------------------------
        # LOAD WRIS / OFFICIAL EVIDENCE ALIASES
        # -----------------------------------------------------

        aliases = defaultdict(set)

        for asset in assets:

            aid = asset["id"]

            aliases[aid].add(
                asset.get("name") or ""
            )

            aliases[aid].add(
                asset.get(
                    "asset_code"
                ) or ""
            )

        tables = {
            r[0]
            for r in (
                await conn.execute(
                    text("""
                        SELECT table_name
                        FROM information_schema.tables
                        WHERE table_schema='public'
                    """)
                )
            )
        }

        if "official_evidence" in tables:

            evidence_rows = (
                await conn.execute(
                    text("""
                        SELECT
                            asset_id,
                            text_value,
                            extraction_metadata
                        FROM public.official_evidence
                        WHERE asset_id IS NOT NULL
                    """)
                )
            ).mappings().all()

            for row in evidence_rows:

                aid = row[
                    "asset_id"
                ]

                if aid not in aliases:
                    continue

                if row.get(
                    "text_value"
                ):
                    aliases[aid].add(
                        str(
                            row["text_value"]
                        )
                    )

                metadata_json = row.get(
                    "extraction_metadata"
                )

                if not isinstance(
                    metadata_json,
                    dict
                ):
                    continue

                props = metadata_json.get(
                    "properties",
                    {}
                )

                if not isinstance(
                    props,
                    dict
                ):
                    continue

                for key in [
                    "dm_name",
                    "strucode",
                    "nrld_no",
                    "rivcode",
                ]:

                    value = props.get(
                        key
                    )

                    if value:
                        aliases[aid].add(
                            str(value)
                        )

    # ---------------------------------------------------------
    # EXTRACT SOURCE ENTITIES
    # ---------------------------------------------------------

    log("")
    log("3. EXTRACT UNIQUE HYDROLOGY ENTITIES")
    log("-" * 105)

    all_entities = []

    for path, info in zip(
        csv_files,
        metadata
    ):

        if (
            info.get("status")
            != "OK"
        ):
            continue

        if not info.get(
            "name_col"
        ):
            log(
                f"[SKIP] {path.name}: "
                f"no station/reservoir name "
                f"column detected"
            )
            continue

        log(
            f"Reading unique names from "
            f"{path.name} ..."
        )

        entities = extract_entities(
            path,
            info
        )

        log(
            f"  unique source entities: "
            f"{len(entities)}"
        )

        all_entities.extend(
            entities
        )

    pd.DataFrame(
        all_entities
    ).to_csv(
        ENTITY_CSV,
        index=False
    )

    # ---------------------------------------------------------
    # MATCH SOURCE ENTITIES → SIMRAS ASSETS
    # ---------------------------------------------------------

    log("")
    log("4. MATCH HYDROLOGY SOURCES TO ASSETS")
    log("-" * 105)

    matches = []

    matched_assets = set()

    for entity in all_entities:

        source_name = entity[
            "source_name"
        ]

        source_norm = norm(
            source_name
        )

        best = None

        for asset in assets:

            aid = asset["id"]

            alias_scores = [
                similarity(
                    source_name,
                    alias
                )
                for alias in aliases[aid]
                if alias
            ]

            name_score = (
                max(alias_scores)
                if alias_scores
                else 0.0
            )

            distance_km = haversine(
                entity.get(
                    "latitude"
                ),
                entity.get(
                    "longitude"
                ),
                asset.get(
                    "latitude"
                ),
                asset.get(
                    "longitude"
                ),
            )

            coordinate_score = 0.0

            if distance_km is not None:

                if distance_km <= 0.5:
                    coordinate_score = 1.0

                elif distance_km <= 2:
                    coordinate_score = 0.95

                elif distance_km <= 5:
                    coordinate_score = 0.85

                elif distance_km <= 15:
                    coordinate_score = 0.65

            if (
                name_score >= 0.98
            ):

                final_score = max(
                    name_score,
                    coordinate_score
                )

                method = "EXACT_OR_ALIAS_NAME"

            elif (
                name_score >= 0.78
                and coordinate_score >= 0.65
            ):

                final_score = (
                    0.65 * name_score
                    + 0.35 * coordinate_score
                )

                method = (
                    "NAME_PLUS_COORDINATE"
                )

            elif name_score >= 0.88:

                final_score = name_score

                method = (
                    "HIGH_CONFIDENCE_NAME"
                )

            elif coordinate_score >= 0.95:

                final_score = (
                    0.75 * coordinate_score
                    + 0.25 * name_score
                )

                method = (
                    "HIGH_CONFIDENCE_COORDINATE"
                )

            else:

                final_score = name_score

                method = (
                    "FUZZY_NAME"
                )

            candidate = {
                "score": float(
                    final_score
                ),
                "name_score": float(
                    name_score
                ),
                "coordinate_score": float(
                    coordinate_score
                ),
                "distance_km": distance_km,
                "method": method,
                "asset": asset,
            }

            if (
                best is None
                or candidate["score"]
                > best["score"]
            ):
                best = candidate

        if best is None:
            continue

        if best["score"] >= 0.82:

            status = (
                "MATCHED_HIGH"
                if best["score"] >= 0.92
                else "MATCHED_REVIEW"
            )

            matched_assets.add(
                best["asset"]["id"]
            )

        else:

            status = "UNMATCHED"

        matches.append({
            **entity,

            "asset_id":
                best["asset"]["id"]
                if status != "UNMATCHED"
                else None,

            "asset_code":
                best["asset"].get(
                    "asset_code"
                )
                if status != "UNMATCHED"
                else None,

            "asset_name":
                best["asset"].get(
                    "name"
                )
                if status != "UNMATCHED"
                else None,

            "asset_type":
                best["asset"].get(
                    type_col
                )
                if status != "UNMATCHED"
                else None,

            "match_score":
                round(
                    best["score"],
                    4
                ),

            "name_score":
                round(
                    best["name_score"],
                    4
                ),

            "coordinate_score":
                round(
                    best[
                        "coordinate_score"
                    ],
                    4
                ),

            "distance_km":
                (
                    round(
                        best[
                            "distance_km"
                        ],
                        3
                    )
                    if best[
                        "distance_km"
                    ] is not None
                    else None
                ),

            "match_method":
                best["method"],

            "match_status":
                status,
        })

    match_df = pd.DataFrame(
        matches
    )

    match_df.to_csv(
        MATCH_CSV,
        index=False
    )

    # ---------------------------------------------------------
    # WRITE MATCHES INTO POSTGRES
    # ---------------------------------------------------------

    async with engine.begin() as conn:

        await conn.execute(
            text("""
            CREATE TABLE IF NOT EXISTS
            public.asset_hydrology_source_matches
            (
                id BIGSERIAL PRIMARY KEY,

                asset_id BIGINT,

                asset_code TEXT,

                asset_name TEXT,

                asset_type TEXT,

                dataset TEXT NOT NULL,

                source_name TEXT NOT NULL,

                source_code TEXT,

                parameter TEXT,

                latitude DOUBLE PRECISION,

                longitude DOUBLE PRECISION,

                source_row_count BIGINT,

                match_score DOUBLE PRECISION,

                name_score DOUBLE PRECISION,

                coordinate_score DOUBLE PRECISION,

                distance_km DOUBLE PRECISION,

                match_method TEXT,

                match_status TEXT,

                provenance TEXT
                    DEFAULT
                    'AP_NWDP_GOVERNMENT_DATA',

                created_at TIMESTAMPTZ
                    DEFAULT NOW()
            )
            """)
        )

        # Replace only this generated matching layer.
        await conn.execute(
            text("""
            TRUNCATE TABLE
            public.asset_hydrology_source_matches
            RESTART IDENTITY
            """)
        )

        insert_sql = text("""
            INSERT INTO
            public.asset_hydrology_source_matches
            (
                asset_id,
                asset_code,
                asset_name,
                asset_type,
                dataset,
                source_name,
                source_code,
                parameter,
                latitude,
                longitude,
                source_row_count,
                match_score,
                name_score,
                coordinate_score,
                distance_km,
                match_method,
                match_status
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,
                :asset_type,
                :dataset,
                :source_name,
                :source_code,
                :parameter,
                :latitude,
                :longitude,
                :source_row_count,
                :match_score,
                :name_score,
                :coordinate_score,
                :distance_km,
                :match_method,
                :match_status
            )
        """)

        for row in matches:

            await conn.execute(
                insert_sql,
                {
                    "asset_id":
                        row.get(
                            "asset_id"
                        ),

                    "asset_code":
                        row.get(
                            "asset_code"
                        ),

                    "asset_name":
                        row.get(
                            "asset_name"
                        ),

                    "asset_type":
                        row.get(
                            "asset_type"
                        ),

                    "dataset":
                        row.get(
                            "dataset"
                        ),

                    "source_name":
                        row.get(
                            "source_name"
                        ),

                    "source_code":
                        row.get(
                            "source_code"
                        ),

                    "parameter":
                        row.get(
                            "parameter"
                        ),

                    "latitude":
                        row.get(
                            "latitude"
                        ),

                    "longitude":
                        row.get(
                            "longitude"
                        ),

                    "source_row_count":
                        int(
                            row.get(
                                "row_count",
                                0
                            )
                        ),

                    "match_score":
                        row.get(
                            "match_score"
                        ),

                    "name_score":
                        row.get(
                            "name_score"
                        ),

                    "coordinate_score":
                        row.get(
                            "coordinate_score"
                        ),

                    "distance_km":
                        row.get(
                            "distance_km"
                        ),

                    "match_method":
                        row.get(
                            "match_method"
                        ),

                    "match_status":
                        row.get(
                            "match_status"
                        ),
                }
            )

    # ---------------------------------------------------------
    # REPORT
    # ---------------------------------------------------------

    matched_high = int(
        (
            match_df[
                "match_status"
            ]
            == "MATCHED_HIGH"
        ).sum()
    ) if not match_df.empty else 0

    matched_review = int(
        (
            match_df[
                "match_status"
            ]
            == "MATCHED_REVIEW"
        ).sum()
    ) if not match_df.empty else 0

    unmatched = int(
        (
            match_df[
                "match_status"
            ]
            == "UNMATCHED"
        ).sum()
    ) if not match_df.empty else 0

    dam_barrage_ids = {
        x["id"]
        for x in assets
    }

    asset_coverage = (
        len(matched_assets)
        / len(dam_barrage_ids)
        * 100
        if dam_barrage_ids
        else 0.0
    )

    report = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "government_csv_files":
            len(csv_files),

        "source_entities":
            len(all_entities),

        "simras_dam_barrage_assets":
            len(assets),

        "matched_asset_count":
            len(matched_assets),

        "asset_coverage_percent":
            round(
                asset_coverage,
                2
            ),

        "matched_high_entities":
            matched_high,

        "matched_review_entities":
            matched_review,

        "unmatched_entities":
            unmatched,

        "database_table":
            "asset_hydrology_source_matches",

        "match_csv":
            str(MATCH_CSV),

        "entity_csv":
            str(ENTITY_CSV),
    }

    REPORT_JSON.write_text(
        json.dumps(
            report,
            indent=2
        ),
        encoding="utf-8"
    )

    log("")
    log("=" * 105)
    log("STEP 2 RESULT")
    log("=" * 105)

    log(
        f"Government CSV files        : "
        f"{len(csv_files)}"
    )

    log(
        f"Unique hydrology entities   : "
        f"{len(all_entities)}"
    )

    log(
        f"SIMRAS dams+barrages        : "
        f"{len(assets)}"
    )

    log(
        f"Matched SIMRAS assets       : "
        f"{len(matched_assets)}"
    )

    log(
        f"Asset coverage              : "
        f"{asset_coverage:.2f}%"
    )

    log(
        f"High-confidence matches     : "
        f"{matched_high}"
    )

    log(
        f"Review matches              : "
        f"{matched_review}"
    )

    log(
        f"Unmatched source entities   : "
        f"{unmatched}"
    )

    log("")
    log(
        "Database table:"
    )

    log(
        "public.asset_hydrology_source_matches"
    )

    log("")
    log(
        f"Match report:"
    )

    log(
        str(MATCH_CSV)
    )

    log("=" * 105)

    REPORT_TXT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    await engine.dispose()


asyncio.run(main())
