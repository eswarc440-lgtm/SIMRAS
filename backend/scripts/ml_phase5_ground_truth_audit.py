from __future__ import annotations

import asyncio
import csv
import json
import os
import re
from pathlib import Path

import asyncpg


ASSET_TYPES = [
    "dam",
    "barrage",
    "bridge",
    "road",
    "airport",
    "temple",
]


LABEL_PATTERN = re.compile(
    r"(health|risk|condition|rating|inspection|damage|defect|"
    r"failure|failed|rul|remaining|service_life|remaining_life|"
    r"pci|iri|deterior|score|label|target|severity|crack|"
    r"corrosion|distress|seepage|settlement)",
    re.I,
)


DOMAIN_PATTERN = re.compile(
    r"(dam|reservoir|barrage|bridge|road|highway|pavement|"
    r"airport|runway|temple|heritage|inspection|prediction|"
    r"hydrology|condition|structural|asset)",
    re.I,
)


def qi(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


async def main():

    conn = await asyncpg.connect(
        host=os.getenv("SIMRAS_DB_HOST", "db"),
        port=int(os.getenv("SIMRAS_DB_PORT", "5432")),
        user=os.environ["SIMRAS_DB_USER"],
        password=os.getenv("SIMRAS_DB_PASSWORD", ""),
        database=os.environ["SIMRAS_DB_NAME"],
    )

    try:

        # ----------------------------------------------------
        # ASSETS TABLE COLUMNS
        # ----------------------------------------------------

        column_records = await conn.fetch(
            """
            SELECT
                column_name,
                data_type,
                udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'assets'
            ORDER BY ordinal_position
            """
        )

        columns = [
            {
                "column_name": r["column_name"],
                "data_type": r["data_type"],
                "udt_name": r["udt_name"],
            }
            for r in column_records
        ]

        column_names = {
            r["column_name"]
            for r in columns
        }


        print()
        print("=" * 120)
        print("ASSETS TABLE COLUMNS")
        print("=" * 120)

        for item in columns:
            print(
                f"{item['column_name']:<35}"
                f"{item['data_type']:<30}"
                f"{item['udt_name']}"
            )


        # ----------------------------------------------------
        # FIND EXPLICIT LAT/LON
        # ----------------------------------------------------

        latitude_candidates = [
            "latitude",
            "lat",
            "asset_latitude",
            "y",
        ]

        longitude_candidates = [
            "longitude",
            "lon",
            "lng",
            "asset_longitude",
            "x",
        ]

        lat_col = next(
            (
                c
                for c in latitude_candidates
                if c in column_names
            ),
            None,
        )

        lon_col = next(
            (
                c
                for c in longitude_candidates
                if c in column_names
            ),
            None,
        )


        # ----------------------------------------------------
        # FIND POSTGIS GEOMETRY
        # ----------------------------------------------------

        geometry_records = await conn.fetch(
            """
            SELECT
                f_geometry_column,
                srid,
                type
            FROM geometry_columns
            WHERE f_table_schema = 'public'
              AND f_table_name = 'assets'
            """
        )

        geometry_column = None
        geometry_srid = None

        if geometry_records:
            geometry_column = (
                geometry_records[0]["f_geometry_column"]
            )
            geometry_srid = (
                geometry_records[0]["srid"]
            )


        # Fallback: inspect UDT geometry
        if geometry_column is None:

            for item in columns:
                if str(
                    item["udt_name"]
                ).lower() == "geometry":

                    geometry_column = (
                        item["column_name"]
                    )
                    break


        print()
        print("=" * 120)
        print("COORDINATE DISCOVERY")
        print("=" * 120)

        print("Explicit latitude :", lat_col)
        print("Explicit longitude:", lon_col)
        print("Geometry column   :", geometry_column)
        print("Geometry SRID     :", geometry_srid)


        # ----------------------------------------------------
        # BUILD CANONICAL LOCATION VIEW
        # ----------------------------------------------------

        coordinate_source = None
        lat_expression = "NULL::double precision"
        lon_expression = "NULL::double precision"


        if lat_col and lon_col:

            lat_expression = (
                f"NULLIF(BTRIM({qi(lat_col)}::text), '')"
                f"::double precision"
            )

            lon_expression = (
                f"NULLIF(BTRIM({qi(lon_col)}::text), '')"
                f"::double precision"
            )

            coordinate_source = "ASSET_COLUMNS"


        elif geometry_column:

            g = qi(geometry_column)

            lat_expression = (
                f"CASE WHEN {g} IS NOT NULL "
                f"THEN ST_Y(ST_Transform({g}::geometry,4326)) "
                f"END"
            )

            lon_expression = (
                f"CASE WHEN {g} IS NOT NULL "
                f"THEN ST_X(ST_Transform({g}::geometry,4326)) "
                f"END"
            )

            coordinate_source = "POSTGIS_GEOMETRY"


        else:

            coordinate_source = "NOT_FOUND"


        await conn.execute(
            "DROP VIEW IF EXISTS "
            "public.ml_asset_location_v1"
        )


        create_view = f"""
        CREATE VIEW public.ml_asset_location_v1 AS
        SELECT
            asset_code,
            name,
            LOWER(asset_type) AS asset_type,
            {lat_expression} AS latitude,
            {lon_expression} AS longitude,
            '{coordinate_source}'::text
                AS coordinate_source
        FROM public.assets
        WHERE LOWER(COALESCE(asset_type,'')) IN (
            'dam',
            'barrage',
            'bridge',
            'road',
            'airport',
            'temple'
        )
        """


        await conn.execute(create_view)


        # ----------------------------------------------------
        # LOCATION READINESS
        # ----------------------------------------------------

        location_records = await conn.fetch(
            """
            SELECT
                asset_type,
                COUNT(*) AS assets,
                COUNT(*) FILTER (
                    WHERE latitude IS NOT NULL
                      AND longitude IS NOT NULL
                ) AS location_ready,
                COUNT(*) FILTER (
                    WHERE latitude IS NULL
                       OR longitude IS NULL
                ) AS location_missing
            FROM public.ml_asset_location_v1
            GROUP BY asset_type
            ORDER BY asset_type
            """
        )


        location_rows = [
            dict(r)
            for r in location_records
        ]


        print()
        print("=" * 120)
        print("RECOVERED LOCATION READINESS")
        print("=" * 120)

        print(
            f"{'TYPE':12}"
            f"{'ASSETS':>10}"
            f"{'LOCATION_READY':>18}"
            f"{'MISSING':>12}"
        )

        print("-" * 55)

        for row in location_rows:

            print(
                f"{row['asset_type'].upper():12}"
                f"{row['assets']:>10}"
                f"{row['location_ready']:>18}"
                f"{row['location_missing']:>12}"
            )


        # ----------------------------------------------------
        # ALL PUBLIC TABLE/COLUMN METADATA
        # ----------------------------------------------------

        metadata = await conn.fetch(
            """
            SELECT
                table_name,
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema='public'
            ORDER BY table_name, ordinal_position
            """
        )


        label_candidates = []


        for r in metadata:

            table = r["table_name"]
            column = r["column_name"]

            if not DOMAIN_PATTERN.search(table):
                continue

            if not LABEL_PATTERN.search(column):
                continue

            # Skip obvious identifiers
            if column.lower() in {
                "risk_model_id",
                "inspection_id",
                "health_model_id",
            }:
                continue

            try:

                count_sql = (
                    f"SELECT COUNT(*) "
                    f"FROM public.{qi(table)} "
                    f"WHERE {qi(column)} IS NOT NULL"
                )

                non_null = await conn.fetchval(
                    count_sql
                )

            except Exception:

                non_null = -1


            label_candidates.append(
                {
                    "table_name": table,
                    "column_name": column,
                    "data_type": r["data_type"],
                    "non_null_rows": non_null,
                }
            )


        label_candidates.sort(
            key=lambda x: (
                -int(x["non_null_rows"]),
                x["table_name"],
                x["column_name"],
            )
        )


        print()
        print("=" * 120)
        print("GROUND-TRUTH / TARGET CANDIDATE COLUMNS")
        print("=" * 120)


        for item in label_candidates[:100]:

            print(
                f"{item['table_name']:<48}"
                f"{item['column_name']:<35}"
                f"nonnull={item['non_null_rows']}"
            )


        # ----------------------------------------------------
        # INSPECTION / PREDICTION TABLE COUNTS
        # ----------------------------------------------------

        table_records = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            ORDER BY table_name
            """
        )

        tables = [
            r["table_name"]
            for r in table_records
        ]


        interesting_tables = [
            table
            for table in tables
            if re.search(
                r"(inspection|prediction|feature|hydrology|"
                r"condition|bridge|dam|barrage|road|"
                r"airport|temple|weather|climate)",
                table,
                re.I,
            )
        ]


        table_counts = []

        for table in interesting_tables:

            try:

                count = await conn.fetchval(
                    f"SELECT COUNT(*) "
                    f"FROM public.{qi(table)}"
                )

            except Exception:

                count = -1


            table_counts.append(
                {
                    "table_name": table,
                    "row_count": count,
                }
            )


        table_counts.sort(
            key=lambda x: (
                -int(x["row_count"]),
                x["table_name"],
            )
        )


        print()
        print("=" * 120)
        print("RELEVANT TABLE COUNTS")
        print("=" * 120)


        for item in table_counts:

            print(
                f"{item['table_name']:<65}"
                f"{item['row_count']:>12}"
            )


        # ----------------------------------------------------
        # WRITE OUTPUTS
        # ----------------------------------------------------

        output = Path(
            "/app/data/processed/ml_phase5"
        )

        output.mkdir(
            parents=True,
            exist_ok=True,
        )


        location_csv = (
            output
            / "SIMRAS_LOCATION_READINESS_V1.csv"
        )

        label_csv = (
            output
            / "SIMRAS_LABEL_CANDIDATES_V1.csv"
        )

        table_csv = (
            output
            / "SIMRAS_RELEVANT_TABLE_COUNTS_V1.csv"
        )

        inventory_json = (
            output
            / "SIMRAS_ML_GROUND_TRUTH_AUDIT_V1.json"
        )


        with location_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            fields = [
                "asset_type",
                "assets",
                "location_ready",
                "location_missing",
            ]

            writer = csv.DictWriter(
                f,
                fieldnames=fields,
            )

            writer.writeheader()
            writer.writerows(location_rows)


        with label_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            fields = [
                "table_name",
                "column_name",
                "data_type",
                "non_null_rows",
            ]

            writer = csv.DictWriter(
                f,
                fieldnames=fields,
            )

            writer.writeheader()
            writer.writerows(
                label_candidates
            )


        with table_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            fields = [
                "table_name",
                "row_count",
            ]

            writer = csv.DictWriter(
                f,
                fieldnames=fields,
            )

            writer.writeheader()
            writer.writerows(
                table_counts
            )


        audit = {
            "coordinate_source":
                coordinate_source,

            "latitude_column":
                lat_col,

            "longitude_column":
                lon_col,

            "geometry_column":
                geometry_column,

            "geometry_srid":
                geometry_srid,

            "location_readiness":
                location_rows,

            "label_candidates":
                label_candidates,

            "relevant_table_counts":
                table_counts,
        }


        inventory_json.write_text(
            json.dumps(
                audit,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )


        print()
        print("=" * 120)
        print("STEP 5 DATABASE AUDIT COMPLETE")
        print("=" * 120)

        print(
            "Coordinate source:",
            coordinate_source,
        )

        print(
            "Location CSV     :",
            location_csv,
        )

        print(
            "Label CSV        :",
            label_csv,
        )

        print(
            "Table CSV        :",
            table_csv,
        )

        print(
            "Audit JSON       :",
            inventory_json,
        )

        print("=" * 120)


    finally:

        await conn.close()


asyncio.run(main())
