from __future__ import annotations

import os
import re
import json
import math
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

SOURCE = (
    ROOT
    / "data"
    / "raw"
    / "osm"
    / "andhra_pradesh_bridges.geojsonseq"
)

ALL_CSV = (
    ROOT
    / "data"
    / "processed"
    / "bridge"
    / "AP_ALL_BRIDGES_OSM.csv"
)

NAMED_CSV = (
    ROOT
    / "data"
    / "processed"
    / "bridge"
    / "AP_NAMED_BRIDGES_OSM.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP6C2B_STATEWIDE_BRIDGE_IMPORT.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP6C2B_STATEWIDE_BRIDGE_IMPORT.json"
)


# ==============================================================
# VERIFIED ANCHORS ALREADY EXISTING IN SIMRAS
# ==============================================================

ANCHOR_ALIASES = {

    "AP_BR_00001": {
        "godavari arch bridge",
        "godavari railway arch bridge",
        "third godavari bridge",
    },

    "AP_BR_00002": {
        "kanaka durga flyover",
        "kanakadurga flyover",
    },
}


def normalize(value):

    value = str(
        value or ""
    ).lower()

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def find_anchor(name):

    n = normalize(
        name
    )

    if not n:
        return None

    for asset_code, aliases in ANCHOR_ALIASES.items():

        if n in aliases:
            return asset_code

    return None


def get_way_id(feature, props):

    candidates = [
        feature.get("id"),
        props.get("@id"),
        props.get("id"),
        props.get("osm_id"),
    ]

    for value in candidates:

        if value is None:
            continue

        match = re.search(
            r"(\d+)$",
            str(value)
        )

        if match:
            return int(
                match.group(1)
            )

    return None


def lines(geometry):

    if not geometry:
        return []

    gtype = geometry.get(
        "type"
    )

    coordinates = geometry.get(
        "coordinates"
    )

    if gtype == "LineString":
        return [
            coordinates
        ]

    if gtype == "MultiLineString":
        return coordinates

    return []


def haversine(
    lat1,
    lon1,
    lat2,
    lon2
):

    radius = 6371008.8

    p1 = math.radians(
        lat1
    )

    p2 = math.radians(
        lat2
    )

    dp = math.radians(
        lat2 - lat1
    )

    dl = math.radians(
        lon2 - lon1
    )

    a = (
        math.sin(
            dp / 2
        ) ** 2
        +
        math.cos(
            p1
        )
        *
        math.cos(
            p2
        )
        *
        math.sin(
            dl / 2
        ) ** 2
    )

    return (
        2
        * radius
        * math.asin(
            min(
                1.0,
                math.sqrt(a)
            )
        )
    )


def geometry_length(geometry):

    total = 0.0

    for line in lines(
        geometry
    ):

        for p1, p2 in zip(
            line,
            line[1:]
        ):

            lon1 = float(
                p1[0]
            )

            lat1 = float(
                p1[1]
            )

            lon2 = float(
                p2[0]
            )

            lat2 = float(
                p2[1]
            )

            total += haversine(
                lat1,
                lon1,
                lat2,
                lon2
            )

    return total


def geometry_center(geometry):

    pts = []

    for line in lines(
        geometry
    ):
        pts.extend(
            line
        )

    if not pts:
        return None, None

    lon = sum(
        float(p[0])
        for p in pts
    ) / len(pts)

    lat = sum(
        float(p[1])
        for p in pts
    ) / len(pts)

    return lat, lon


def numeric(value):

    if value in [
        None,
        "",
    ]:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        str(value)
    )

    if not match:
        return None

    try:
        return float(
            match.group(0)
        )
    except Exception:
        return None


def integer(value):

    n = numeric(
        value
    )

    if n is None:
        return None

    if n < 0:
        return None

    return int(
        round(n)
    )


def year(value):

    if value is None:
        return None

    match = re.search(
        r"\b(18|19|20)\d{2}\b",
        str(value)
    )

    if not match:
        return None

    return int(
        match.group(0)
    )


def classify(tags):

    highway = normalize(
        tags.get(
            "highway"
        )
    )

    railway = normalize(
        tags.get(
            "railway"
        )
    )

    bridge_tag = normalize(
        tags.get(
            "bridge"
        )
    )

    if railway:
        return "RAIL"

    if highway in {
        "footway",
        "pedestrian",
        "path",
        "steps",
    }:
        return "PEDESTRIAN"

    if bridge_tag == "aqueduct":
        return "AQUEDUCT"

    if highway:
        return "ROAD"

    return "OTHER"


def render_width(
    reported_width,
    lanes,
    bridge_type
):

    if (
        reported_width is not None
        and 0.5
        <= reported_width
        <= 100
    ):

        return (
            round(
                reported_width,
                2
            ),
            "OSM_REPORTED"
        )

    if (
        lanes is not None
        and lanes > 0
    ):

        return (
            round(
                max(
                    3.5,
                    lanes * 3.5
                ),
                2
            ),
            "ESTIMATED_FROM_LANES_FOR_RENDERING"
        )

    if bridge_type == "RAIL":

        return (
            6.0,
            "VISUALIZATION_ESTIMATE"
        )

    if bridge_type == "PEDESTRIAN":

        return (
            2.5,
            "VISUALIZATION_ESTIMATE"
        )

    if bridge_type == "AQUEDUCT":

        return (
            4.0,
            "VISUALIZATION_ESTIMATE"
        )

    return (
        7.0,
        "VISUALIZATION_ESTIMATE"
    )


def structure_key(
    way_id,
    name,
    ref,
    bridge_type
):

    n = normalize(
        name
    )

    r = normalize(
        ref
    )

    if n:

        return (
            f"NAME::{n}::{bridge_type}"
        )

    if r:

        return (
            f"REF::{r}::{bridge_type}"
        )

    return (
        f"OSM_WAY::{way_id}"
    )


def parse_source():

    rows = []

    skipped_non_lines = 0
    skipped_no_id = 0
    duplicate_way_ids = 0

    seen = set()

    with SOURCE.open(
        "r",
        encoding="utf-8",
        errors="ignore"
    ) as handle:

        for raw_line in handle:

            raw_line = raw_line.lstrip("\x1e").strip()

            if not raw_line:
                continue

            feature = json.loads(
                raw_line
            )

            geometry = feature.get(
                "geometry"
            )

            if not lines(
                geometry
            ):

                skipped_non_lines += 1
                continue

            props = (
                feature.get(
                    "properties"
                )
                or {}
            )

            way_id = get_way_id(
                feature,
                props
            )

            if way_id is None:

                skipped_no_id += 1
                continue

            if way_id in seen:

                duplicate_way_ids += 1
                continue

            seen.add(
                way_id
            )

            name = (
                props.get(
                    "name"
                )
                or props.get(
                    "name:en"
                )
            )

            ref = props.get(
                "ref"
            )

            bridge_type = classify(
                props
            )

            actual_length = geometry_length(
                geometry
            )

            lat, lon = geometry_center(
                geometry
            )

            reported_width = numeric(
                props.get(
                    "width"
                )
            )

            lanes = integer(
                props.get(
                    "lanes"
                )
            )

            render_width_m, width_basis = render_width(
                reported_width,
                lanes,
                bridge_type
            )

            material = (
                props.get(
                    "bridge:material"
                )
                or props.get(
                    "material"
                )
            )

            start_year = year(
                props.get(
                    "start_date"
                )
                or props.get(
                    "opening_date"
                )
            )

            anchor = find_anchor(
                name
            )

            asset_code = (
                anchor
                if anchor
                else
                f"AP_BR_OSM_W{way_id}"
            )

            display_name = (
                str(name).strip()
                if name
                else
                (
                    f"Unnamed {bridge_type.title()} "
                    f"Bridge - OSM {way_id}"
                )
            )

            rows.append({

                "osm_way_id":
                    way_id,

                "asset_code":
                    asset_code,

                "anchor_asset_code":
                    anchor,

                "source_name":
                    name,

                "display_name":
                    display_name,

                "normalized_name":
                    normalize(
                        name
                    ),

                "structure_key":
                    structure_key(
                        way_id,
                        name,
                        ref,
                        bridge_type
                    ),

                "bridge_type":
                    bridge_type,

                "bridge_tag":
                    props.get(
                        "bridge"
                    ),

                "highway":
                    props.get(
                        "highway"
                    ),

                "railway":
                    props.get(
                        "railway"
                    ),

                "ref":
                    ref,

                "length_m_derived":
                    round(
                        actual_length,
                        2
                    ),

                "width_m_reported":
                    reported_width,

                "lanes_reported":
                    lanes,

                "material_reported":
                    material,

                "start_year_reported":
                    start_year,

                "latitude":
                    lat,

                "longitude":
                    lon,

                "is_named":
                    bool(
                        name
                    ),

                "identity_status":
                    "SOURCE_REPORTED",

                "geometry_source":
                    "OPENSTREETMAP",

                "source_dataset":
                    "GEOFABRIK_SOUTHERN_ZONE_OSM",

                "source_relation":
                    2022095,

                "geometry_json":
                    json.dumps(
                        geometry,
                        separators=(
                            ",",
                            ":"
                        )
                    ),

                "tags_json":
                    json.dumps(
                        props,
                        ensure_ascii=False,
                        separators=(
                            ",",
                            ":"
                        )
                    ),

                "render_width_m":
                    render_width_m,

                "render_width_basis":
                    width_basis,

                "verified_pier_count":
                    None,

                "pier_count_status":
                    "UNKNOWN_DO_NOT_REPORT",

                "digital_twin_strategy":
                    "REAL_OSM_ALIGNMENT_PROCEDURAL_3D",

                "rendering_estimated":
                    (
                        width_basis
                        != "OSM_REPORTED"
                    ),
            })

    return (
        rows,
        skipped_non_lines,
        skipped_no_id,
        duplicate_way_ids,
    )


async def get_asset_schema(
    conn
):

    result = await conn.execute(
        text("""
            SELECT
                column_name,
                is_nullable,
                column_default,
                is_identity
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name='assets'
            ORDER BY ordinal_position
        """)
    )

    return [
        dict(row)
        for row
        in result.mappings()
    ]


async def main():

    if not SOURCE.exists():

        raise RuntimeError(
            "AP bridge GeoJSONSeq missing."
        )

    (
        rows,
        skipped_non_lines,
        skipped_no_id,
        duplicate_way_ids,
    ) = parse_source()

    if len(
        rows
    ) < 100:

        raise RuntimeError(
            f"Only {len(rows)} usable bridge ways found."
        )

    df = pd.DataFrame(
        rows
    )

    # ==========================================================
    # CSV EXPORTS
    # ==========================================================

    export_cols = [
        column
        for column in df.columns
        if column not in {
            "geometry_json",
            "tags_json",
        }
    ]

    ALL_CSV.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df[
        export_cols
    ].to_csv(
        ALL_CSV,
        index=False
    )

    named_df = df[
        df[
            "is_named"
        ] == True
    ].copy()

    named_df[
        export_cols
    ].to_csv(
        NAMED_CSV,
        index=False
    )

    # ==========================================================
    # DATABASE
    # ==========================================================

    db_url = (
        os.getenv(
            "DATABASE_URL"
        )
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

    new_assets = 0
    reused_assets = 0
    anchor_rows = 0
    anchor_assets_linked = set()

    async with engine.begin() as conn:

        # ======================================================
        # PRE-FLIGHT ASSETS SCHEMA
        # ======================================================

        schema = await get_asset_schema(
            conn
        )

        asset_columns = {
            row[
                "column_name"
            ]
            for row in schema
        }

        type_column = next(
            (
                name
                for name in [
                    "asset_type",
                    "type",
                    "infrastructure_type",
                ]
                if name
                in asset_columns
            ),
            None
        )

        if not type_column:

            raise RuntimeError(
                "Could not find asset type column."
            )

        supported_required = {
            "asset_code",
            "name",
            type_column,

            # Required SIMRAS asset schema fields handled
            # explicitly during OSM bridge promotion.
            "status",
            "identity_status",
            "representative_geometry",
            "is_estimated",
        }

        dangerous_required = []

        for col in schema:

            name = col[
                "column_name"
            ]

            if (
                col[
                    "is_nullable"
                ] == "NO"
                and col[
                    "column_default"
                ] is None
                and col[
                    "is_identity"
                ] != "YES"
                and name
                not in supported_required
            ):

                dangerous_required.append(
                    name
                )

        if dangerous_required:

            raise RuntimeError(
                "SAFE IMPORT ABORTED. "
                "public.assets has unsupported required columns: "
                +
                ", ".join(
                    dangerous_required
                )
            )

        # ======================================================
        # RAW OSM CATALOG
        # ======================================================

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.bridge_osm_catalog
                (
                    osm_way_id BIGINT PRIMARY KEY,

                    asset_code TEXT NOT NULL,

                    canonical_asset_id BIGINT,

                    anchor_asset_code TEXT,

                    source_name TEXT,

                    display_name TEXT NOT NULL,

                    normalized_name TEXT,

                    structure_key TEXT,

                    bridge_type TEXT,

                    bridge_tag TEXT,

                    highway TEXT,

                    railway TEXT,

                    ref TEXT,

                    length_m_derived
                        DOUBLE PRECISION,

                    width_m_reported
                        DOUBLE PRECISION,

                    lanes_reported INTEGER,

                    material_reported TEXT,

                    start_year_reported INTEGER,

                    latitude
                        DOUBLE PRECISION,

                    longitude
                        DOUBLE PRECISION,

                    is_named BOOLEAN,

                    identity_status TEXT,

                    geometry_source TEXT,

                    source_dataset TEXT,

                    source_relation BIGINT,

                    geometry_json JSONB,

                    tags_json JSONB,

                    render_width_m
                        DOUBLE PRECISION,

                    render_width_basis TEXT,

                    verified_pier_count INTEGER,

                    pier_count_status TEXT,

                    digital_twin_strategy TEXT,

                    rendering_estimated BOOLEAN,

                    imported_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.bridge_osm_catalog
            """)
        )

        catalog_sql = text("""
            INSERT INTO
            public.bridge_osm_catalog
            (
                osm_way_id,

                asset_code,

                anchor_asset_code,

                source_name,

                display_name,

                normalized_name,

                structure_key,

                bridge_type,

                bridge_tag,

                highway,

                railway,

                ref,

                length_m_derived,

                width_m_reported,

                lanes_reported,

                material_reported,

                start_year_reported,

                latitude,

                longitude,

                is_named,

                identity_status,

                geometry_source,

                source_dataset,

                source_relation,

                geometry_json,

                tags_json,

                render_width_m,

                render_width_basis,

                verified_pier_count,

                pier_count_status,

                digital_twin_strategy,

                rendering_estimated
            )

            VALUES
            (
                :osm_way_id,

                :asset_code,

                :anchor_asset_code,

                :source_name,

                :display_name,

                :normalized_name,

                :structure_key,

                :bridge_type,

                :bridge_tag,

                :highway,

                :railway,

                :ref,

                :length_m_derived,

                :width_m_reported,

                :lanes_reported,

                :material_reported,

                :start_year_reported,

                :latitude,

                :longitude,

                :is_named,

                :identity_status,

                :geometry_source,

                :source_dataset,

                :source_relation,

                CAST(
                    :geometry_json
                    AS JSONB
                ),

                CAST(
                    :tags_json
                    AS JSONB
                ),

                :render_width_m,

                :render_width_basis,

                :verified_pier_count,

                :pier_count_status,

                :digital_twin_strategy,

                :rendering_estimated
            )
        """)

        # Batch to avoid oversized asyncpg calls.
        batch_size = 1000

        for start in range(
            0,
            len(rows),
            batch_size
        ):

            batch = rows[
                start:
                start + batch_size
            ]

            await conn.execute(
                catalog_sql,
                batch
            )

        # ======================================================
        # EXISTING ASSET CODES
        # ======================================================

        existing_result = await conn.execute(
            text("""
                SELECT
                    id,
                    asset_code
                FROM
                    public.assets
                WHERE
                    asset_code IS NOT NULL
            """)
        )

        existing = {

            str(
                row[
                    "asset_code"
                ]
            ):
                int(
                    row[
                        "id"
                    ]
                )

            for row
            in existing_result.mappings()
        }

        # ======================================================
        # PROMOTE OSM ROWS TO ASSETS
        #
        # Keep AP_BR_00001 and AP_BR_00002 unchanged.
        # ======================================================

        insertable_columns = [
            "asset_code",
            "name",
            type_column,
        ]

        optional_candidates = [
            "latitude",
            "longitude",
            "built_year",
            "material",
            "length_m",
            "width_m",
        ]

        for column in optional_candidates:

            if column in asset_columns:

                insertable_columns.append(
                    column
                )

        sql_column_names = list(
            insertable_columns
        )

        sql_value_expressions = [
            f":{column}"
            for column
            in insertable_columns
        ]

        if "status" in asset_columns:

            sql_column_names.append(
                "status"
            )

            sql_value_expressions.append(
                """
                (
                    SELECT a.status
                    FROM public.assets a
                    WHERE a.status IS NOT NULL
                    ORDER BY
                        CASE
                            WHEN CAST(a.status AS TEXT) = 'ACTIVE'
                            THEN 0
                            ELSE 1
                        END,
                        a.id
                    LIMIT 1
                )
                """
            )

        if "identity_status" in asset_columns:

            sql_column_names.append(
                "identity_status"
            )

            sql_value_expressions.append(
                """
                (
                    SELECT a.identity_status
                    FROM public.assets a
                    WHERE a.identity_status IS NOT NULL
                    ORDER BY
                        CASE
                            WHEN CAST(
                                a.identity_status
                                AS TEXT
                            ) = 'SOURCE_REPORTED'
                            THEN 0

                            WHEN CAST(
                                a.identity_status
                                AS TEXT
                            ) = 'UNVERIFIED'
                            THEN 1

                            ELSE 2
                        END,
                        a.id
                    LIMIT 1
                )
                """
            )

        if "representative_geometry" in asset_columns:

            sql_column_names.append(
                "representative_geometry"
            )

            sql_value_expressions.append(
                """
                ST_SetSRID(
                    ST_MakePoint(
                        :geom_longitude,
                        :geom_latitude
                    ),
                    4326
                )
                """
            )

        if "is_estimated" in asset_columns:

            sql_column_names.append(
                "is_estimated"
            )

            sql_value_expressions.append(
                "TRUE"
            )

        sql_columns = ", ".join(
            f'"{column}"'
            for column
            in sql_column_names
        )

        sql_values = ", ".join(
            sql_value_expressions
        )

        asset_insert_sql = text(
            f"""
            INSERT INTO
                public.assets
                ({sql_columns})
            VALUES
                ({sql_values})
            RETURNING id
            """
        )

        for index, row in enumerate(
            rows,
            start=1
        ):

            code = row[
                "asset_code"
            ]

            # --------------------------------------------------
            # Verified anchors
            # --------------------------------------------------

            if row[
                "anchor_asset_code"
            ]:

                anchor_rows += 1

                asset_id = existing.get(
                    code
                )

                if asset_id is None:

                    # Anchor should already exist from Steps 6A/6B.
                    # Do not create a replacement automatically.
                    continue

                anchor_assets_linked.add(
                    code
                )

                await conn.execute(
                    text("""
                        UPDATE
                            public.bridge_osm_catalog
                        SET
                            canonical_asset_id=:asset_id
                        WHERE
                            osm_way_id=:way_id
                    """),
                    {
                        "asset_id":
                            asset_id,

                        "way_id":
                            row[
                                "osm_way_id"
                            ],
                    }
                )

                continue

            # --------------------------------------------------
            # Existing deterministic OSM asset
            # --------------------------------------------------

            if code in existing:

                asset_id = existing[
                    code
                ]

                reused_assets += 1

            else:

                params = {

                    "asset_code":
                        code,

                    "name":
                        row[
                            "display_name"
                        ],

                    type_column:
                        "BRIDGE",
                }

                # Coordinates are always available from
                # the actual OSM bridge LineString centroid.
                params["geom_longitude"] = row[
                    "longitude"
                ]

                params["geom_latitude"] = row[
                    "latitude"
                ]

                if "latitude" in insertable_columns:
                    params[
                        "latitude"
                    ] = row[
                        "latitude"
                    ]

                if "longitude" in insertable_columns:
                    params[
                        "longitude"
                    ] = row[
                        "longitude"
                    ]

                if "built_year" in insertable_columns:
                    params[
                        "built_year"
                    ] = row[
                        "start_year_reported"
                    ]

                if "material" in insertable_columns:
                    params[
                        "material"
                    ] = row[
                        "material_reported"
                    ]

                if "length_m" in insertable_columns:
                    params[
                        "length_m"
                    ] = row[
                        "length_m_derived"
                    ]

                if "width_m" in insertable_columns:
                    params[
                        "width_m"
                    ] = row[
                        "width_m_reported"
                    ]

                if "identity_status" in insertable_columns:
                    params[
                        "identity_status"
                    ] = "SOURCE_REPORTED"

                if "is_estimated" in insertable_columns:
                    params[
                        "is_estimated"
                    ] = True

                result = await conn.execute(
                    asset_insert_sql,
                    params
                )

                asset_id = int(
                    result.scalar_one()
                )

                existing[
                    code
                ] = asset_id

                new_assets += 1

            await conn.execute(
                text("""
                    UPDATE
                        public.bridge_osm_catalog
                    SET
                        canonical_asset_id=:asset_id
                    WHERE
                        osm_way_id=:way_id
                """),
                {
                    "asset_id":
                        asset_id,

                    "way_id":
                        row[
                            "osm_way_id"
                        ],
                }
            )

            if (
                index % 2500
                == 0
            ):

                print(
                    f"Promoted/linked "
                    f"{index:,} / "
                    f"{len(rows):,} bridge ways..."
                )

        # ======================================================
        # DIGITAL TWIN PROFILES
        # ======================================================

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.bridge_digital_twin_profiles
                (
                    asset_id BIGINT PRIMARY KEY,

                    osm_way_id BIGINT,

                    structure_key TEXT,

                    bridge_type TEXT,

                    actual_length_m
                        DOUBLE PRECISION,

                    reported_width_m
                        DOUBLE PRECISION,

                    render_width_m
                        DOUBLE PRECISION,

                    width_basis TEXT,

                    latitude
                        DOUBLE PRECISION,

                    longitude
                        DOUBLE PRECISION,

                    actual_geometry JSONB,

                    geometry_source TEXT,

                    lanes_reported INTEGER,

                    material_reported TEXT,

                    verified_pier_count INTEGER,

                    pier_count_status TEXT,

                    rendering_strategy TEXT,

                    rendering_estimated BOOLEAN,

                    profile_version TEXT,

                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.bridge_digital_twin_profiles
            """)
        )

        # Multiple OSM ways can point at a verified anchor.
        # Pick the longest matching geometry for one asset profile.
        await conn.execute(
            text("""
                INSERT INTO
                public.bridge_digital_twin_profiles
                (
                    asset_id,

                    osm_way_id,

                    structure_key,

                    bridge_type,

                    actual_length_m,

                    reported_width_m,

                    render_width_m,

                    width_basis,

                    latitude,

                    longitude,

                    actual_geometry,

                    geometry_source,

                    lanes_reported,

                    material_reported,

                    verified_pier_count,

                    pier_count_status,

                    rendering_strategy,

                    rendering_estimated,

                    profile_version
                )

                SELECT DISTINCT ON (
                    canonical_asset_id
                )

                    canonical_asset_id,

                    osm_way_id,

                    structure_key,

                    bridge_type,

                    length_m_derived,

                    width_m_reported,

                    render_width_m,

                    render_width_basis,

                    latitude,

                    longitude,

                    geometry_json,

                    geometry_source,

                    lanes_reported,

                    material_reported,

                    verified_pier_count,

                    pier_count_status,

                    digital_twin_strategy,

                    rendering_estimated,

                    'ap_bridge_twin_v1'

                FROM
                    public.bridge_osm_catalog

                WHERE
                    canonical_asset_id
                    IS NOT NULL

                ORDER BY
                    canonical_asset_id,
                    length_m_derived DESC NULLS LAST
            """)
        )

        # ======================================================
        # OVERRIDE VERIFIED ANCHOR ENGINEERING FEATURES
        # ======================================================

        await conn.execute(
            text("""
                UPDATE
                    public.bridge_digital_twin_profiles p

                SET
                    actual_length_m =
                        COALESCE(
                            f.length_m,
                            p.actual_length_m
                        ),

                    reported_width_m =
                        COALESCE(
                            f.width_m,
                            p.reported_width_m
                        ),

                    render_width_m =
                        COALESCE(
                            f.width_m,
                            p.render_width_m
                        ),

                    width_basis =
                        CASE
                            WHEN
                                f.width_m
                                IS NOT NULL
                            THEN
                                'VERIFIED_ENGINEERING_EVIDENCE'
                            ELSE
                                p.width_basis
                        END,

                    verified_pier_count =
                        f.pier_count,

                    pier_count_status =
                        CASE
                            WHEN
                                f.pier_count
                                IS NOT NULL
                            THEN
                                'VERIFIED_ENGINEERING_EVIDENCE'
                            ELSE
                                p.pier_count_status
                        END,

                    material_reported =
                        COALESCE(
                            f.material_summary,
                            p.material_reported
                        ),

                    rendering_estimated =
                        CASE
                            WHEN
                                f.width_m IS NOT NULL
                                AND f.pier_count IS NOT NULL
                            THEN
                                FALSE
                            ELSE
                                p.rendering_estimated
                        END,

                    updated_at =
                        NOW()

                FROM
                    public.bridge_engineering_features_verified f

                WHERE
                    p.asset_id =
                    f.asset_id
            """)
        )

        # ======================================================
        # REPORT READINESS
        # ======================================================

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.bridge_report_readiness
                (
                    asset_id BIGINT PRIMARY KEY,

                    health_score
                        DOUBLE PRECISION,

                    health_status TEXT,

                    risk_score
                        DOUBLE PRECISION,

                    risk_level TEXT,

                    risk_status TEXT,

                    confidence
                        DOUBLE PRECISION,

                    confidence_status TEXT,

                    rul_years
                        DOUBLE PRECISION,

                    rul_status TEXT,

                    geometry_status TEXT,

                    engineering_status TEXT,

                    evidence_status TEXT,

                    report_version TEXT,

                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.bridge_report_readiness
            """)
        )

        await conn.execute(
            text("""
                INSERT INTO
                public.bridge_report_readiness
                (
                    asset_id,

                    health_score,
                    health_status,

                    risk_score,
                    risk_level,
                    risk_status,

                    confidence,
                    confidence_status,

                    rul_years,
                    rul_status,

                    geometry_status,

                    engineering_status,

                    evidence_status,

                    report_version
                )

                SELECT

                    c.canonical_asset_id,

                    NULL,

                    'WITHHELD_NO_REAL_STRUCTURAL_INSPECTION',

                    NULL,

                    NULL,

                    'WITHHELD_NO_AP_STRUCTURAL_RISK_LABEL',

                    NULL,

                    'NOT_A_MODEL_CONFIDENCE',

                    NULL,

                    'WITHHELD_NO_VALIDATED_RUL_BASIS',

                    'REAL_OSM_ALIGNMENT_AVAILABLE',

                    CASE
                        WHEN
                            e.asset_id
                            IS NOT NULL
                        THEN
                            'VERIFIED_ENGINEERING_ANCHOR'
                        WHEN
                            c.width_m_reported
                            IS NOT NULL
                            OR
                            c.material_reported
                            IS NOT NULL
                        THEN
                            'OSM_SOURCE_REPORTED_ENGINEERING_FIELDS'
                        ELSE
                            'OSM_GEOMETRY_ONLY'
                    END,

                    CASE
                        WHEN
                            e.asset_id
                            IS NOT NULL
                        THEN
                            'VERIFIED_PLUS_OSM'
                        ELSE
                            'OSM_SOURCE_REPORTED'
                    END,

                    'ap_bridge_report_v1'

                FROM
                (
                    SELECT DISTINCT ON (
                        canonical_asset_id
                    )
                        *

                    FROM
                        public.bridge_osm_catalog

                    WHERE
                        canonical_asset_id
                        IS NOT NULL

                    ORDER BY
                        canonical_asset_id,
                        length_m_derived
                        DESC NULLS LAST

                ) c

                LEFT JOIN
                    public.bridge_engineering_features_verified e

                ON
                    e.asset_id =
                    c.canonical_asset_id
            """)
        )

        # Godavari has a planning design-life basis from previous audit.
        await conn.execute(
            text("""
                UPDATE
                    public.bridge_report_readiness r

                SET
                    rul_status =
                        'PLANNING_BASIS_AVAILABLE_NOT_VALIDATED'

                FROM
                    public.assets a

                WHERE
                    r.asset_id = a.id

                    AND
                    a.asset_code =
                    'AP_BR_00001'
            """)
        )

        # ======================================================
        # GROUPING / RECONCILIATION VIEW
        # ======================================================

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.bridge_structure_groups
                (
                    structure_key TEXT PRIMARY KEY,

                    bridge_type TEXT,

                    normalized_name TEXT,

                    ref TEXT,

                    osm_way_count INTEGER,

                    named BOOLEAN,

                    total_mapped_length_m
                        DOUBLE PRECISION,

                    grouping_status TEXT,

                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.bridge_structure_groups
            """)
        )

        await conn.execute(
            text("""
                INSERT INTO
                public.bridge_structure_groups
                (
                    structure_key,

                    bridge_type,

                    normalized_name,

                    ref,

                    osm_way_count,

                    named,

                    total_mapped_length_m,

                    grouping_status
                )

                SELECT
                    structure_key,

                    MAX(
                        bridge_type
                    ),

                    NULLIF(
                        MAX(
                            normalized_name
                        ),
                        ''
                    ),

                    NULLIF(
                        MAX(
                            ref
                        ),
                        ''
                    ),

                    COUNT(*),

                    BOOL_OR(
                        is_named
                    ),

                    SUM(
                        COALESCE(
                            length_m_derived,
                            0
                        )
                    ),

                    CASE

                        WHEN
                            COUNT(*) = 1
                        THEN
                            'SINGLE_OSM_WAY'

                        WHEN
                            MAX(
                                normalized_name
                            ) IS NOT NULL
                            AND
                            MAX(
                                normalized_name
                            ) <> ''
                        THEN
                            'MULTI_WAY_NAME_GROUP_REVIEW'

                        ELSE
                            'MULTI_WAY_REVIEW'

                    END

                FROM
                    public.bridge_osm_catalog

                GROUP BY
                    structure_key
            """)
        )

        # ======================================================
        # FINAL COUNTS
        # ======================================================

        count_result = await conn.execute(
            text(f"""
                SELECT

                    COUNT(*) AS total_bridge_assets,

                    COUNT(*) FILTER (
                        WHERE name NOT LIKE
                        'Unnamed %Bridge - OSM %'
                    ) AS named_bridge_assets

                FROM
                    public.assets

                WHERE
                    UPPER(
                        CAST(
                            "{type_column}"
                            AS TEXT
                        )
                    ) = 'BRIDGE'
            """)
        )

        counts = dict(
            count_result.mappings().one()
        )

        catalog_result = await conn.execute(
            text("""
                SELECT

                    COUNT(*) AS catalog_rows,

                    COUNT(*) FILTER (
                        WHERE is_named = TRUE
                    ) AS named_rows,

                    COUNT(*) FILTER (
                        WHERE bridge_type='ROAD'
                    ) AS road_rows,

                    COUNT(*) FILTER (
                        WHERE bridge_type='RAIL'
                    ) AS rail_rows,

                    COUNT(*) FILTER (
                        WHERE bridge_type='PEDESTRIAN'
                    ) AS pedestrian_rows,

                    COUNT(*) FILTER (
                        WHERE width_m_reported
                        IS NOT NULL
                    ) AS reported_width_rows,

                    COUNT(*) FILTER (
                        WHERE material_reported
                        IS NOT NULL
                    ) AS material_rows,

                    COUNT(*) FILTER (
                        WHERE start_year_reported
                        IS NOT NULL
                    ) AS year_rows

                FROM
                    public.bridge_osm_catalog
            """)
        )

        catalog_counts = dict(
            catalog_result.mappings().one()
        )

        twin_result = await conn.execute(
            text("""
                SELECT COUNT(*)
                FROM public.bridge_digital_twin_profiles
            """)
        )

        twin_count = int(
            twin_result.scalar()
            or 0
        )

        report_result = await conn.execute(
            text("""
                SELECT COUNT(*)
                FROM public.bridge_report_readiness
            """)
        )

        report_count = int(
            report_result.scalar()
            or 0
        )

        groups_result = await conn.execute(
            text("""
                SELECT
                    COUNT(*) AS groups,

                    COUNT(*) FILTER (
                        WHERE osm_way_count > 1
                    ) AS multi_way_groups

                FROM
                    public.bridge_structure_groups
            """)
        )

        group_counts = dict(
            groups_result.mappings().one()
        )

    await engine.dispose()

    # ==========================================================
    # REPORT
    # ==========================================================

    summary = {

        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "geojson_line_bridge_ways":
            len(rows),

        "skipped_non_line_features":
            skipped_non_lines,

        "skipped_missing_way_id":
            skipped_no_id,

        "duplicate_way_ids_removed":
            duplicate_way_ids,

        "named_osm_bridge_ways":
            int(
                catalog_counts[
                    "named_rows"
                ]
                or 0
            ),

        "road_bridge_ways":
            int(
                catalog_counts[
                    "road_rows"
                ]
                or 0
            ),

        "rail_bridge_ways":
            int(
                catalog_counts[
                    "rail_rows"
                ]
                or 0
            ),

        "pedestrian_bridge_ways":
            int(
                catalog_counts[
                    "pedestrian_rows"
                ]
                or 0
            ),

        "width_reported":
            int(
                catalog_counts[
                    "reported_width_rows"
                ]
                or 0
            ),

        "material_reported":
            int(
                catalog_counts[
                    "material_rows"
                ]
                or 0
            ),

        "start_year_reported":
            int(
                catalog_counts[
                    "year_rows"
                ]
                or 0
            ),

        "new_assets_inserted":
            new_assets,

        "existing_assets_reused":
            reused_assets,

        "anchor_osm_rows":
            anchor_rows,

        "anchor_assets_linked":
            sorted(
                anchor_assets_linked
            ),

        "canonical_bridge_assets":
            int(
                counts[
                    "total_bridge_assets"
                ]
                or 0
            ),

        "canonical_named_bridge_assets":
            int(
                counts[
                    "named_bridge_assets"
                ]
                or 0
            ),

        "digital_twin_profiles":
            twin_count,

        "report_readiness_rows":
            report_count,

        "structure_groups":
            int(
                group_counts[
                    "groups"
                ]
                or 0
            ),

        "multi_way_groups_for_review":
            int(
                group_counts[
                    "multi_way_groups"
                ]
                or 0
            ),
    }

    REPORT_JSON.write_text(
        json.dumps(
            summary,
            indent=2
        ),
        encoding="utf-8"
    )

    lines_report = [
        "=" * 112,
        "SIMRAS STEP 6C.2B - STATEWIDE AP BRIDGE IMPORT RESULT",
        "=" * 112,
        "",
        f"Usable OSM bridge ways             : {len(rows):,}",
        f"Non-line exported features skipped : {skipped_non_lines:,}",
        f"Duplicate way IDs removed          : {duplicate_way_ids:,}",
        "",
        f"Named bridge ways                  : {catalog_counts['named_rows']:,}",
        f"Road bridge ways                   : {catalog_counts['road_rows']:,}",
        f"Rail bridge ways                   : {catalog_counts['rail_rows']:,}",
        f"Pedestrian bridge ways             : {catalog_counts['pedestrian_rows']:,}",
        "",
        f"OSM width reported                 : {catalog_counts['reported_width_rows']:,}",
        f"OSM material reported              : {catalog_counts['material_rows']:,}",
        f"OSM construction/start year        : {catalog_counts['year_rows']:,}",
        "",
        f"New bridge assets inserted         : {new_assets:,}",
        f"Existing OSM assets reused         : {reused_assets:,}",
        f"Anchor OSM rows detected           : {anchor_rows:,}",
        f"Verified anchors linked            : {len(anchor_assets_linked)} / 2",
        "",
        f"Canonical BRIDGE assets now        : {counts['total_bridge_assets']:,}",
        f"Digital Twin profiles              : {twin_count:,}",
        f"Report readiness rows              : {report_count:,}",
        "",
        f"Structure grouping keys            : {group_counts['groups']:,}",
        f"Multi-way groups requiring review  : {group_counts['multi_way_groups']:,}",
        "",
        "Database tables:",
        " public.bridge_osm_catalog",
        " public.bridge_digital_twin_profiles",
        " public.bridge_report_readiness",
        " public.bridge_structure_groups",
        "",
        "Output files:",
        f" {ALL_CSV}",
        f" {NAMED_CSV}",
        "",
        "DIGITAL TWIN POLICY:",
        " - real OSM bridge alignment is stored",
        " - measured/reported width is used when available",
        " - estimated width is rendering-only",
        " - unknown pier counts remain UNKNOWN_DO_NOT_REPORT",
        " - verified Step 6B anchors override OSM engineering fields",
        "",
        "REPORT POLICY:",
        " - every promoted bridge receives a report-readiness row",
        " - Health remains withheld without real structural inspection",
        " - structural Risk remains withheld without AP validation labels",
        " - RUL remains withheld without validated deterioration/design-life basis",
        "",
        "IMPORTANT:",
        " OSM bridge ways are statewide mapped bridge segments.",
        " Multi-way structures are tracked separately for physical-bridge",
        " reconciliation instead of pretending every way is independent.",
        "=" * 112,
    ]

    REPORT.write_text(
        "\n".join(
            lines_report
        ),
        encoding="utf-8"
    )

    print(
        "\n".join(
            lines_report
        )
    )

    # ==========================================================
    # SHOW FIRST 40 NAMED BRIDGES
    # ==========================================================

    print()
    print(
        "FIRST 40 NAMED AP BRIDGE WAYS"
    )
    print("-" * 112)

    if not named_df.empty:

        preview = (
            named_df
            .sort_values(
                [
                    "source_name",
                    "osm_way_id",
                ]
            )
            .head(
                40
            )
        )

        for _, row in preview.iterrows():

            print(
                f"{row['asset_code']} | "
                f"{row['source_name']} | "
                f"{row['bridge_type']} | "
                f"{row['length_m_derived']:.1f} m"
            )


asyncio.run(main())

