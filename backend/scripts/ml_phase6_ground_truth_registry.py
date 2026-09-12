from __future__ import annotations

import asyncio
import csv
import json
import math
import os
import re
from collections import Counter, defaultdict
from pathlib import Path

import asyncpg


ASSET_TYPES = {
    "dam",
    "barrage",
    "bridge",
    "road",
    "airport",
    "temple",
}


# Sources that may contain real observations.
SOURCE_INCLUDE = re.compile(
    r"(inspection|condition|assessment|evidence|survey|"
    r"monitor|maintenance|structural|pavement|bridge|"
    r"dam|barrage|airport|runway|temple|heritage)",
    re.I,
)


# Never train on model outputs.
SOURCE_EXCLUDE = re.compile(
    r"(prediction|forecast|readiness|feature_snapshot|"
    r"model_registry|model_artifact|recommendation|"
    r"raw_|backup|archive)",
    re.I,
)


HEALTH_LABEL = re.compile(
    r"(^health(_score)?$|condition(_score|_rating)?$|"
    r"structural_condition|inspection_score|"
    r"condition_index|condition_rating|"
    r"deck_condition|superstructure_condition|"
    r"substructure_condition|culvert_condition|"
    r"pci$|pavement_condition)",
    re.I,
)


RISK_LABEL = re.compile(
    r"(^risk(_score|_level)?$|failure_risk|"
    r"hazard_score|damage_severity|severity$|"
    r"failure_probability|unsafe_probability|"
    r"deterioration_risk)",
    re.I,
)


RUL_LABEL = re.compile(
    r"(remaining_useful_life|remaining_life|"
    r"rul(_years)?$|service_life_remaining|"
    r"remaining_service_life)",
    re.I,
)


LABEL_EXCLUDE = re.compile(
    r"(confidence|model|version|status|id$|date|time|"
    r"year$|latitude|longitude|length|width|height|"
    r"capacity|count|age$)",
    re.I,
)


BAD_PROVENANCE = re.compile(
    r"\b(synthetic|demo|mock|dummy|test data|"
    r"fabricated|simulated label)\b",
    re.I,
)


OFFICIAL_HINT = re.compile(
    r"(verified|official|government|govt|cwc|wris|"
    r"nwdp|nwic|imd|aai|morth|nhai|fhwa|faa|"
    r"authority|department)",
    re.I,
)


def quote_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def numeric(value):

    if value is None:
        return None

    if isinstance(value, bool):
        return None

    try:
        number = float(value)

        if math.isfinite(number):
            return number

    except Exception:
        return None

    return None


def classify_label(column: str):

    if LABEL_EXCLUDE.search(column):
        return None

    if RUL_LABEL.search(column):
        return "RUL"

    if RISK_LABEL.search(column):
        return "RISK"

    if HEALTH_LABEL.search(column):
        return "HEALTH"

    return None


def provenance_text(row: dict):

    keys = [
        "source",
        "data_source",
        "source_name",
        "source_type",
        "provenance",
        "evidence_source",
        "evidence_status",
        "validation_status",
        "method",
        "notes",
    ]

    values = []

    for key in keys:

        value = row.get(key)

        if value is not None:
            values.append(str(value))

    return " | ".join(values)


def obvious_synthetic(row: dict):

    text = provenance_text(row)

    return bool(
        BAD_PROVENANCE.search(text)
    )


def provenance_class(
    table: str,
    row: dict,
):

    combined = (
        table
        + " "
        + provenance_text(row)
    )

    if OFFICIAL_HINT.search(combined):
        return "OFFICIAL_OR_VERIFIED"

    if re.search(
        r"(inspection|assessment|condition)",
        combined,
        re.I,
    ):
        return "INSPECTION_EVIDENCE"

    return "REVIEW_REQUIRED"


async def main():

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

        # ====================================================
        # CANONICAL ASSET MAP
        # ====================================================

        asset_records = await conn.fetch(
            """
            SELECT to_jsonb(a)::text AS j
            FROM public.assets a
            WHERE LOWER(
                COALESCE(asset_type,'')
            ) IN (
                'dam',
                'barrage',
                'bridge',
                'road',
                'airport',
                'temple'
            )
            """
        )


        assets_by_code = {}
        assets_by_id = {}

        for record in asset_records:

            row = json.loads(
                record["j"]
            )

            asset_type = str(
                row.get(
                    "asset_type",
                    "",
                )
            ).lower()

            if asset_type not in ASSET_TYPES:
                continue

            code = row.get(
                "asset_code"
            )

            if code is not None:
                assets_by_code[
                    str(code)
                ] = row

            asset_id = row.get("id")

            if asset_id is not None:
                assets_by_id[
                    str(asset_id)
                ] = row


        # ====================================================
        # TABLE METADATA
        # ====================================================

        table_records = await conn.fetch(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
              AND table_type='BASE TABLE'
            ORDER BY table_name
            """
        )


        tables = [
            r["table_name"]
            for r in table_records
        ]


        candidates = []

        source_stats = Counter()
        excluded_synthetic = 0
        excluded_unmapped = 0


        # ====================================================
        # SCAN REAL-EVIDENCE CANDIDATES
        # ====================================================

        for table in tables:

            if SOURCE_EXCLUDE.search(
                table
            ):
                continue

            if not SOURCE_INCLUDE.search(
                table
            ):
                continue


            column_records = await conn.fetch(
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


            columns = [
                r["column_name"]
                for r in column_records
            ]


            label_columns = []

            for column in columns:

                label_type = (
                    classify_label(
                        column
                    )
                )

                if label_type:

                    label_columns.append(
                        (
                            column,
                            label_type,
                        )
                    )


            if not label_columns:
                continue


            # Need some way to map observation -> asset.
            code_keys = [
                key
                for key in (
                    "asset_code",
                    "infrastructure_code",
                    "bridge_code",
                    "dam_code",
                )
                if key in columns
            ]


            id_keys = [
                key
                for key in (
                    "asset_id",
                    "infrastructure_id",
                )
                if key in columns
            ]


            if (
                not code_keys
                and not id_keys
            ):
                continue


            try:

                records = await conn.fetch(
                    "SELECT "
                    "to_jsonb(t)::text AS j "
                    f"FROM public."
                    f"{quote_ident(table)} t"
                )

            except Exception as exc:

                print(
                    "SKIP",
                    table,
                    exc,
                )

                continue


            for record in records:

                row = json.loads(
                    record["j"]
                )


                # --------------------------------------------
                # Reject explicit synthetic/demo rows
                # --------------------------------------------

                if obvious_synthetic(row):

                    excluded_synthetic += 1
                    continue


                asset = None


                for key in code_keys:

                    value = row.get(key)

                    if value is None:
                        continue

                    asset = assets_by_code.get(
                        str(value)
                    )

                    if asset:
                        break


                if asset is None:

                    for key in id_keys:

                        value = row.get(key)

                        if value is None:
                            continue

                        asset = assets_by_id.get(
                            str(value)
                        )

                        if asset:
                            break


                if asset is None:

                    excluded_unmapped += 1
                    continue


                asset_type = str(
                    asset.get(
                        "asset_type",
                        "",
                    )
                ).lower()


                if asset_type not in ASSET_TYPES:
                    continue


                provenance = (
                    provenance_class(
                        table,
                        row,
                    )
                )


                for (
                    column,
                    label_type,
                ) in label_columns:

                    raw_value = row.get(
                        column
                    )

                    number = numeric(
                        raw_value
                    )


                    # For training registry we only admit
                    # numeric target values.
                    if number is None:
                        continue


                    candidates.append(
                        {
                            "asset_code":
                                asset.get(
                                    "asset_code"
                                ),

                            "asset_name":
                                asset.get(
                                    "name"
                                ),

                            "asset_type":
                                asset_type,

                            "label_class":
                                label_type,

                            "label_name":
                                column,

                            "numeric_value":
                                number,

                            "source_table":
                                table,

                            "provenance_class":
                                provenance,

                            "source_detail":
                                provenance_text(
                                    row
                                ),
                        }
                    )


                    source_stats[
                        (
                            asset_type,
                            label_type,
                            table,
                            column,
                            provenance,
                        )
                    ] += 1


        # ====================================================
        # CREATE DATABASE REGISTRY
        # ====================================================

        await conn.execute(
            """
            DROP TABLE IF EXISTS
                public.ml_ground_truth_registry_v1
            """
        )


        await conn.execute(
            """
            CREATE TABLE
                public.ml_ground_truth_registry_v1
            (
                id BIGSERIAL PRIMARY KEY,

                asset_code TEXT NOT NULL,

                asset_name TEXT,

                asset_type TEXT NOT NULL,

                label_class TEXT NOT NULL,

                label_name TEXT NOT NULL,

                numeric_value DOUBLE PRECISION
                    NOT NULL,

                source_table TEXT NOT NULL,

                provenance_class TEXT NOT NULL,

                source_detail TEXT,

                created_at TIMESTAMPTZ
                    NOT NULL DEFAULT NOW()
            )
            """
        )


        if candidates:

            await conn.executemany(
                """
                INSERT INTO
                    public.ml_ground_truth_registry_v1
                (
                    asset_code,
                    asset_name,
                    asset_type,
                    label_class,
                    label_name,
                    numeric_value,
                    source_table,
                    provenance_class,
                    source_detail
                )
                VALUES
                (
                    $1,$2,$3,$4,$5,$6,$7,$8,$9
                )
                """,
                [
                    (
                        str(
                            row[
                                "asset_code"
                            ]
                        ),

                        row[
                            "asset_name"
                        ],

                        row[
                            "asset_type"
                        ],

                        row[
                            "label_class"
                        ],

                        row[
                            "label_name"
                        ],

                        row[
                            "numeric_value"
                        ],

                        row[
                            "source_table"
                        ],

                        row[
                            "provenance_class"
                        ],

                        row[
                            "source_detail"
                        ],
                    )
                    for row in candidates
                ],
            )


        # ====================================================
        # TRAINING READINESS
        # ====================================================

        readiness = []


        for asset_type in sorted(
            ASSET_TYPES
        ):

            type_rows = [
                r
                for r in candidates
                if r["asset_type"]
                == asset_type
            ]


            for target in (
                "HEALTH",
                "RISK",
                "RUL",
            ):

                rows = [
                    r
                    for r in type_rows
                    if r[
                        "label_class"
                    ]
                    == target
                ]


                distinct_assets = len(
                    {
                        r["asset_code"]
                        for r in rows
                    }
                )


                official_rows = [
                    r
                    for r in rows
                    if r[
                        "provenance_class"
                    ]
                    == "OFFICIAL_OR_VERIFIED"
                ]


                official_assets = len(
                    {
                        r["asset_code"]
                        for r in official_rows
                    }
                )


                # Conservative minimum gates.
                if len(rows) == 0:

                    status = (
                        "NO_REAL_LABELS"
                    )

                elif (
                    len(rows) < 30
                    or distinct_assets < 5
                ):

                    status = (
                        "INSUFFICIENT_FOR_LOCAL_TRAINING"
                    )

                elif official_assets == 0:

                    status = (
                        "RESEARCH_ONLY"
                    )

                else:

                    status = (
                        "TRAINING_CANDIDATE"
                    )


                readiness.append(
                    {
                        "asset_type":
                            asset_type,

                        "target":
                            target,

                        "label_rows":
                            len(rows),

                        "distinct_assets":
                            distinct_assets,

                        "official_rows":
                            len(
                                official_rows
                            ),

                        "official_assets":
                            official_assets,

                        "training_status":
                            status,
                    }
                )


        # ====================================================
        # EXPORT
        # ====================================================

        output = Path(
            "/app/data/processed/ml_phase6"
        )

        output.mkdir(
            parents=True,
            exist_ok=True,
        )


        registry_csv = (
            output /
            "SIMRAS_GROUND_TRUTH_REGISTRY_V1.csv"
        )

        readiness_csv = (
            output /
            "SIMRAS_LOCAL_TRAINING_READINESS_V1.csv"
        )

        source_csv = (
            output /
            "SIMRAS_LABEL_SOURCE_SUMMARY_V1.csv"
        )

        json_path = (
            output /
            "SIMRAS_GROUND_TRUTH_AUDIT_V1.json"
        )


        registry_fields = [
            "asset_code",
            "asset_name",
            "asset_type",
            "label_class",
            "label_name",
            "numeric_value",
            "source_table",
            "provenance_class",
            "source_detail",
        ]


        with registry_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=
                    registry_fields,
            )

            writer.writeheader()
            writer.writerows(
                candidates
            )


        with readiness_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            fields = [
                "asset_type",
                "target",
                "label_rows",
                "distinct_assets",
                "official_rows",
                "official_assets",
                "training_status",
            ]

            writer = csv.DictWriter(
                f,
                fieldnames=fields,
            )

            writer.writeheader()
            writer.writerows(
                readiness
            )


        source_rows = []

        for (
            (
                asset_type,
                target,
                table,
                column,
                provenance,
            ),
            count,
        ) in sorted(
            source_stats.items()
        ):

            source_rows.append(
                {
                    "asset_type":
                        asset_type,

                    "target":
                        target,

                    "source_table":
                        table,

                    "label_column":
                        column,

                    "provenance_class":
                        provenance,

                    "rows":
                        count,
                }
            )


        with source_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as f:

            fields = [
                "asset_type",
                "target",
                "source_table",
                "label_column",
                "provenance_class",
                "rows",
            ]

            writer = csv.DictWriter(
                f,
                fieldnames=fields,
            )

            writer.writeheader()
            writer.writerows(
                source_rows
            )


        audit = {
            "registry_rows":
                len(candidates),

            "synthetic_rows_excluded":
                excluded_synthetic,

            "unmapped_rows_excluded":
                excluded_unmapped,

            "training_readiness":
                readiness,

            "label_sources":
                source_rows,
        }


        json_path.write_text(
            json.dumps(
                audit,
                indent=2,
            ),
            encoding="utf-8",
        )


        # ====================================================
        # OUTPUT
        # ====================================================

        print()
        print("=" * 112)
        print(
            "SIMRAS VERIFIED GROUND TRUTH"
        )
        print("=" * 112)

        print(
            "Registry rows       :",
            len(candidates),
        )

        print(
            "Synthetic excluded  :",
            excluded_synthetic,
        )

        print(
            "Unmapped excluded   :",
            excluded_unmapped,
        )


        print()
        print(
            f"{'TYPE':10}"
            f"{'TARGET':10}"
            f"{'ROWS':>10}"
            f"{'ASSETS':>10}"
            f"{'OFFICIAL':>12}"
            f"{'OFF_ASSETS':>12}"
            f"  STATUS"
        )

        print("-" * 112)


        for row in readiness:

            print(
                f"{row['asset_type'].upper():10}"
                f"{row['target']:10}"
                f"{row['label_rows']:>10}"
                f"{row['distinct_assets']:>10}"
                f"{row['official_rows']:>12}"
                f"{row['official_assets']:>12}"
                f"  {row['training_status']}"
            )


        print()
        print("TOP LABEL SOURCES")
        print("-" * 112)


        for row in sorted(
            source_rows,
            key=lambda x:
                -int(x["rows"]),
        )[:40]:

            print(
                f"{row['asset_type'].upper():9} "
                f"{row['target']:7} "
                f"{row['source_table']:<45} "
                f"{row['label_column']:<28} "
                f"{row['rows']:>8} "
                f"{row['provenance_class']}"
            )


        print()
        print(
            "Registry  :",
            registry_csv,
        )

        print(
            "Readiness :",
            readiness_csv,
        )

        print(
            "Sources   :",
            source_csv,
        )

        print(
            "Audit     :",
            json_path,
        )

        print("=" * 112)


    finally:

        await conn.close()


asyncio.run(main())
