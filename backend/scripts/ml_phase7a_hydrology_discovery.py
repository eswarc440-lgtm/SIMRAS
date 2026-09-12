from __future__ import annotations

import asyncio
import csv
import json
import os
import re
from pathlib import Path

import asyncpg


TABLE_RE = re.compile(
    r"(hydro|reservoir|water|level|storage|dam|barrage)",
    re.I,
)

VALUE_RE = re.compile(
    r"(water.*level|reservoir.*level|level.*m|storage.*mcm|"
    r"reservoir.*storage|storage|inflow|outflow|discharge)",
    re.I,
)

TIME_RE = re.compile(
    r"(date|time|timestamp|observed|measurement)",
    re.I,
)

ASSET_RE = re.compile(
    r"(asset_code|dam_code|barrage_code|station_code|"
    r"reservoir_code|asset_id|station_id)",
    re.I,
)


def q(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


async def main():

    conn = await asyncpg.connect(
        host=os.getenv("SIMRAS_DB_HOST", "db"),
        port=int(os.getenv("SIMRAS_DB_PORT", "5432")),
        user=os.environ["SIMRAS_DB_USER"],
        password=os.getenv("SIMRAS_DB_PASSWORD", ""),
        database=os.environ["SIMRAS_DB_NAME"],
    )

    try:

        tables = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_type='BASE TABLE'
            ORDER BY table_name
            """
        )

        candidates = []

        for tr in tables:

            table = tr["table_name"]

            if not TABLE_RE.search(table):
                continue

            columns = await conn.fetch(
                """
                SELECT
                    column_name,
                    data_type
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name=$1
                ORDER BY ordinal_position
                """,
                table,
            )

            names = [
                r["column_name"]
                for r in columns
            ]

            value_cols = [
                c for c in names
                if VALUE_RE.search(c)
            ]

            time_cols = [
                c for c in names
                if TIME_RE.search(c)
            ]

            asset_cols = [
                c for c in names
                if ASSET_RE.search(c)
            ]

            try:
                rows = await conn.fetchval(
                    f"SELECT COUNT(*) FROM public.{q(table)}"
                )
            except Exception:
                rows = -1

            if (
                rows > 0
                and value_cols
            ):

                candidates.append(
                    {
                        "table_name": table,
                        "rows": int(rows),
                        "asset_columns": ";".join(asset_cols),
                        "time_columns": ";".join(time_cols),
                        "value_columns": ";".join(value_cols),
                    }
                )

        candidates.sort(
            key=lambda x: -x["rows"]
        )

        print()
        print("=" * 130)
        print("REAL HYDROLOGY TABLE CANDIDATES")
        print("=" * 130)

        print(
            f"{'TABLE':55}"
            f"{'ROWS':>12}  "
            f"{'ASSET':25}  "
            f"{'TIME':25}  "
            f"VALUES"
        )

        print("-" * 130)

        for r in candidates[:50]:

            print(
                f"{r['table_name'][:54]:55}"
                f"{r['rows']:>12}  "
                f"{r['asset_columns'][:24]:25}  "
                f"{r['time_columns'][:24]:25}  "
                f"{r['value_columns']}"
            )


        # ----------------------------------------------------
        # Feature snapshot schema
        # ----------------------------------------------------

        snapshot_exists = await conn.fetchval(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_name='dam_barrage_feature_snapshots'
            )
            """
        )

        snapshot_info = []

        if snapshot_exists:

            cols = await conn.fetch(
                """
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='dam_barrage_feature_snapshots'
                ORDER BY ordinal_position
                """
            )

            snapshot_info = [
                dict(r)
                for r in cols
            ]

            count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM public.dam_barrage_feature_snapshots
                """
            )

            print()
            print("=" * 130)
            print("dam_barrage_feature_snapshots")
            print("=" * 130)
            print("Rows:", count)

            for c in snapshot_info:
                print(
                    f"{c['column_name']:<50}"
                    f"{c['data_type']}"
                )


        # ----------------------------------------------------
        # Check AP canonical asset coverage
        # ----------------------------------------------------

        asset_counts = await conn.fetch(
            """
            SELECT
                LOWER(asset_type) AS asset_type,
                COUNT(*) AS assets
            FROM public.assets
            WHERE LOWER(asset_type) IN ('dam','barrage')
            GROUP BY LOWER(asset_type)
            ORDER BY LOWER(asset_type)
            """
        )

        output = Path(
            "/app/data/processed/ml_phase7a"
        )

        output.mkdir(
            parents=True,
            exist_ok=True,
        )

        csv_path = (
            output /
            "SIMRAS_HYDROLOGY_SOURCE_CANDIDATES_V1.csv"
        )

        json_path = (
            output /
            "SIMRAS_HYDROLOGY_SOURCE_AUDIT_V1.json"
        )


        with csv_path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            fields = [
                "table_name",
                "rows",
                "asset_columns",
                "time_columns",
                "value_columns",
            ]

            writer = csv.DictWriter(
                f,
                fieldnames=fields,
            )

            writer.writeheader()
            writer.writerows(candidates)


        payload = {
            "candidate_sources": candidates,
            "feature_snapshot_columns": snapshot_info,
            "canonical_assets": [
                dict(r)
                for r in asset_counts
            ],
        }

        json_path.write_text(
            json.dumps(
                payload,
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )


        print()
        print("=" * 130)
        print("STEP 7A SOURCE DISCOVERY COMPLETE")
        print("=" * 130)

        print("Candidate tables :", len(candidates))

        if candidates:

            best = candidates[0]

            print(
                "Largest candidate :",
                best["table_name"],
            )

            print(
                "Rows              :",
                best["rows"],
            )

        print(
            "CSV               :",
            csv_path,
        )

        print(
            "Audit             :",
            json_path,
        )

        print("=" * 130)

    finally:
        await conn.close()


asyncio.run(main())
