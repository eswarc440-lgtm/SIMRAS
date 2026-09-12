from __future__ import annotations

import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

OUT = (
    ROOT
    / "data"
    / "processed"
    / "bridge"
    / "AP_BRIDGE_SOURCE_PLAN.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP6A_BRIDGE_INVENTORY.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP6A_BRIDGE_INVENTORY.json"
)


def normalize_name(value):

    value = str(
        value or ""
    ).lower()

    value = re.sub(
        r"\bbridge\b|\bflyover\b",
        " ",
        value
    )

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


async def table_exists(conn, table_name):

    result = await conn.execute(
        text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema='public'
                  AND table_name=:table_name
            )
        """),
        {
            "table_name":
                table_name
        }
    )

    return bool(
        result.scalar()
    )


async def columns_for(conn, table_name):

    result = await conn.execute(
        text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema='public'
              AND table_name=:table_name
        """),
        {
            "table_name":
                table_name
        }
    )

    return {
        row[0]
        for row in result
    }


async def count_by_asset(
    conn,
    table_name,
    asset_ids
):

    if not asset_ids:
        return {}

    if not await table_exists(
        conn,
        table_name
    ):
        return {}

    cols = await columns_for(
        conn,
        table_name
    )

    if "asset_id" not in cols:
        return {}

    result = await conn.execute(
        text(f"""
            SELECT
                asset_id,
                COUNT(*) AS row_count
            FROM public."{table_name}"
            WHERE asset_id = ANY(:asset_ids)
            GROUP BY asset_id
        """),
        {
            "asset_ids":
                asset_ids
        }
    )

    return {
        int(row["asset_id"]):
            int(row["row_count"])
        for row in result.mappings()
    }


async def main():

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

    async with engine.connect() as conn:

        asset_cols = await columns_for(
            conn,
            "assets"
        )

        if not asset_cols:
            raise RuntimeError(
                "public.assets not found"
            )

        type_col = next(
            (
                col
                for col in [
                    "asset_type",
                    "type",
                    "infrastructure_type"
                ]
                if col in asset_cols
            ),
            None
        )

        if not type_col:
            raise RuntimeError(
                "Asset type column not found."
            )

        wanted = [
            "id",
            "asset_code",
            "name",
            type_col,
            "district",
            "latitude",
            "longitude",

            "built_year",
            "material",
            "design_life_years",

            "length_m",
            "width_m",
            "height_m",

            "condition",
            "status",
        ]

        selected = [
            col
            for col in wanted
            if col in asset_cols
        ]

        select_sql = ", ".join(
            f'a."{col}"'
            for col in selected
        )

        result = await conn.execute(
            text(f"""
                SELECT
                    {select_sql}
                FROM
                    public.assets a
                WHERE
                    UPPER(
                        CAST(
                            a."{type_col}"
                            AS TEXT
                        )
                    ) = 'BRIDGE'
                ORDER BY
                    a.name
            """)
        )

        assets = [
            dict(row)
            for row in result.mappings().all()
        ]

        asset_ids = [
            int(a["id"])
            for a in assets
        ]

        evidence_counts = await count_by_asset(
            conn,
            "official_evidence",
            asset_ids
        )

        inspection_counts = await count_by_asset(
            conn,
            "inspections",
            asset_ids
        )

        prediction_counts = await count_by_asset(
            conn,
            "predictions",
            asset_ids
        )

        # ------------------------------------------------------
        # REAL / SYNTHETIC INSPECTION AUDIT
        # ------------------------------------------------------

        real_inspections = {}
        synthetic_inspections = {}

        if (
            asset_ids
            and await table_exists(
                conn,
                "inspections"
            )
        ):

            inspection_cols = await columns_for(
                conn,
                "inspections"
            )

            # Only apply this classification when the schema
            # contains explicit provenance/synthetic information.
            synthetic_col = next(
                (
                    col
                    for col in [
                        "is_synthetic",
                        "synthetic"
                    ]
                    if col in inspection_cols
                ),
                None
            )

            if synthetic_col:

                r = await conn.execute(
                    text(f"""
                        SELECT
                            asset_id,

                            COUNT(*) FILTER (
                                WHERE COALESCE(
                                    "{synthetic_col}",
                                    FALSE
                                ) = FALSE
                            ) AS real_rows,

                            COUNT(*) FILTER (
                                WHERE COALESCE(
                                    "{synthetic_col}",
                                    FALSE
                                ) = TRUE
                            ) AS synthetic_rows

                        FROM
                            public.inspections

                        WHERE
                            asset_id = ANY(:asset_ids)

                        GROUP BY
                            asset_id
                    """),
                    {
                        "asset_ids":
                            asset_ids
                    }
                )

                for row in r.mappings():

                    real_inspections[
                        int(row["asset_id"])
                    ] = int(
                        row["real_rows"]
                        or 0
                    )

                    synthetic_inspections[
                        int(row["asset_id"])
                    ] = int(
                        row["synthetic_rows"]
                        or 0
                    )

    await engine.dispose()

    # ==========================================================
    # BUILD READINESS DATASET
    # ==========================================================

    rows = []

    for asset in assets:

        aid = int(
            asset["id"]
        )

        built_year = asset.get(
            "built_year"
        )

        material = asset.get(
            "material"
        )

        design_life = asset.get(
            "design_life_years"
        )

        length_m = asset.get(
            "length_m"
        )

        width_m = asset.get(
            "width_m"
        )

        height_m = asset.get(
            "height_m"
        )

        inspections = inspection_counts.get(
            aid,
            0
        )

        actual_real = real_inspections.get(
            aid
        )

        if actual_real is None:

            real_status = (
                "UNKNOWN_PROVENANCE"
                if inspections > 0
                else "NO"
            )

        else:

            real_status = (
                "YES"
                if actual_real > 0
                else "NO"
            )

        # Structural ML requires actual condition evidence.
        if (
            actual_real is not None
            and actual_real > 0
        ):
            health_readiness = (
                "POTENTIAL_FULL_ML_AFTER_LABEL_VALIDATION"
            )

        else:
            health_readiness = (
                "NO_REAL_STRUCTURAL_INSPECTION"
            )

        if design_life not in [
            None,
            "",
        ] and built_year not in [
            None,
            "",
        ]:

            rul_readiness = (
                "PLANNING_BASIS_AVAILABLE"
            )

        else:

            rul_readiness = (
                "WITHHOLD_RUL"
            )

        rows.append({

            "asset_id":
                aid,

            "asset_code":
                asset.get(
                    "asset_code"
                ),

            "asset_name":
                asset.get(
                    "name"
                ),

            "normalized_name":
                normalize_name(
                    asset.get(
                        "name"
                    )
                ),

            "district":
                asset.get(
                    "district"
                ),

            "latitude":
                asset.get(
                    "latitude"
                ),

            "longitude":
                asset.get(
                    "longitude"
                ),

            "built_year":
                built_year,

            "material":
                material,

            "design_life_years":
                design_life,

            "length_m":
                length_m,

            "width_m":
                width_m,

            "height_m":
                height_m,

            "official_evidence_rows":
                evidence_counts.get(
                    aid,
                    0
                ),

            "inspection_rows":
                inspections,

            "real_inspection_rows":
                real_inspections.get(
                    aid
                ),

            "synthetic_inspection_rows":
                synthetic_inspections.get(
                    aid
                ),

            "prediction_rows":
                prediction_counts.get(
                    aid,
                    0
                ),

            "real_inspection_status":
                real_status,

            "health_ml_readiness":
                health_readiness,

            "rul_readiness":
                rul_readiness,

            "recommended_primary_sources":
                (
                    "AP_RB;APRDC;MoRTH_INFRACON;"
                    "NHAI_BICRS;PMGSY_NRIDA"
                ),

            "transfer_learning_source":
                "FHWA_NBI",

            "source_status":
                "PENDING_GOVERNMENT_EVIDENCE_HARVEST",
        })

    df = pd.DataFrame(
        rows
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUT,
        index=False
    )

    # ==========================================================
    # DUPLICATE CHECK
    # ==========================================================

    duplicate_groups = {}

    for row in rows:

        key = row[
            "normalized_name"
        ]

        duplicate_groups.setdefault(
            key,
            []
        ).append(
            row
        )

    duplicates = {
        key: group
        for key, group
        in duplicate_groups.items()
        if len(group) > 1
    }

    # ==========================================================
    # SUMMARY
    # ==========================================================

    total = len(rows)

    with_evidence = sum(
        1
        for row in rows
        if row[
            "official_evidence_rows"
        ] > 0
    )

    with_inspection = sum(
        1
        for row in rows
        if row[
            "inspection_rows"
        ] > 0
    )

    known_real = sum(
        1
        for row in rows
        if row[
            "real_inspection_status"
        ] == "YES"
    )

    with_built_year = sum(
        1
        for row in rows
        if row[
            "built_year"
        ] not in [
            None,
            "",
        ]
    )

    with_material = sum(
        1
        for row in rows
        if row[
            "material"
        ] not in [
            None,
            "",
        ]
    )

    with_length = sum(
        1
        for row in rows
        if row[
            "length_m"
        ] not in [
            None,
            "",
        ]
    )

    with_design_life = sum(
        1
        for row in rows
        if row[
            "design_life_years"
        ] not in [
            None,
            "",
        ]
    )

    lines = [
        "=" * 110,
        "SIMRAS STEP 6A - BRIDGE INVENTORY + ML READINESS RESULT",
        "=" * 110,
        "",
        f"Bridge assets found              : {total}",
        f"Unique normalized bridges        : {len(duplicate_groups)}",
        f"Potential duplicate groups       : {len(duplicates)}",
        "",
        f"Assets with official evidence    : {with_evidence}",
        f"Assets with any inspections      : {with_inspection}",
        f"Assets with confirmed real insp. : {known_real}",
        "",
        f"Built year available             : {with_built_year}",
        f"Material available               : {with_material}",
        f"Length available                 : {with_length}",
        f"Design life available            : {with_design_life}",
        "",
    ]

    for row in rows:

        lines.append(
            f"{row['asset_code']} | "
            f"{row['asset_name']} | "
            f"district={row['district']} | "
            f"built={row['built_year']} | "
            f"material={row['material']} | "
            f"length={row['length_m']} | "
            f"inspection={row['real_inspection_status']} | "
            f"health={row['health_ml_readiness']} | "
            f"rul={row['rul_readiness']}"
        )

    if duplicates:

        lines += [
            "",
            "POTENTIAL DUPLICATES:",
        ]

        for key, group in duplicates.items():

            lines.append(
                f"  {key}"
            )

            for row in group:

                lines.append(
                    f"    {row['asset_code']} | "
                    f"{row['asset_name']}"
                )

    lines += [
        "",
        "Bridge evidence strategy:",
        "  1. AP R&B / APRDC / government DPR and bridge records",
        "  2. MoRTH / INFRACON / NHAI / PMGSY evidence where available",
        "  3. Real structural inspections remain AP validation labels",
        "  4. FHWA NBI is TRANSFER LEARNING ONLY",
        "",
        "IMPORTANT:",
        " NBI predictions must not be presented as Andhra Pradesh",
        " validated predictions without AP held-out condition labels.",
        "",
        f"Source plan: {OUT}",
        "=" * 110,
    ]

    REPORT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "bridge_assets":
                    total,

                "unique_normalized":
                    len(
                        duplicate_groups
                    ),

                "duplicate_groups":
                    len(
                        duplicates
                    ),

                "official_evidence_assets":
                    with_evidence,

                "inspection_assets":
                    with_inspection,

                "confirmed_real_inspection_assets":
                    known_real,

                "built_year_assets":
                    with_built_year,

                "material_assets":
                    with_material,

                "length_assets":
                    with_length,

                "design_life_assets":
                    with_design_life,

                "assets":
                    rows,
            },
            indent=2,
            default=str
        ),
        encoding="utf-8"
    )

    print(
        "\n".join(lines)
    )


asyncio.run(main())
