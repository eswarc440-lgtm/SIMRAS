from __future__ import annotations

import os
import re
import csv
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

OUT = (
    ROOT
    / "data"
    / "processed"
    / "temple"
    / "AP_TEMPLE_SOURCE_PLAN.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP5A_AP_TEMPLE_INVENTORY.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP5A_AP_TEMPLE_INVENTORY.json"
)


def normalize(value):

    value = str(
        value or ""
    ).lower()

    replacements = {
        "&": " and ",
        "sri ": "",
        "sree ": "",
        "shri ": "",
        "srI ": "",
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new
        )

    value = re.sub(
        r"\btemple\b",
        " ",
        value
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    ).strip()

    return value


def source_strategy(name):

    n = normalize(name)

    strategy = []

    # Every AP temple should be checked against state Endowments first.
    strategy.append(
        "AP_ENDOWMENTS"
    )

    # ASI should also be checked for historic/protected sites.
    strategy.append(
        "ASI_PROTECTED_MONUMENTS"
    )

    # Government procurement is useful for restoration/repair history.
    strategy.append(
        "CPPP_EPROCURE_CONSERVATION"
    )

    return ";".join(strategy)


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

    async with engine.connect() as conn:

        col_result = await conn.execute(
            text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='assets'
            """)
        )

        columns = {
            row[0]
            for row in col_result
        }

        type_col = next(
            (
                col
                for col in [
                    "asset_type",
                    "type",
                    "infrastructure_type"
                ]
                if col in columns
            ),
            None
        )

        if not type_col:
            raise RuntimeError(
                "Could not identify asset type column."
            )

        desired = [
            "id",
            "asset_code",
            "name",
            type_col,
            "district",
            "latitude",
            "longitude",
            "built_year",
            "material",
            "design_life_years"
        ]

        selected = [
            c
            for c in desired
            if c in columns
        ]

        sql_cols = ", ".join(
            f'a."{c}"'
            for c in selected
        )

        result = await conn.execute(
            text(f"""
                SELECT
                    {sql_cols}
                FROM
                    public.assets a
                WHERE
                    UPPER(
                        CAST(
                            a."{type_col}"
                            AS TEXT
                        )
                    ) = 'TEMPLE'
                ORDER BY
                    a.name
            """)
        )

        assets = [
            dict(row)
            for row in result.mappings().all()
        ]

    rows = []

    for asset in assets:

        name = asset.get(
            "name"
        )

        rows.append({

            "asset_id":
                asset.get("id"),

            "asset_code":
                asset.get("asset_code"),

            "asset_name":
                name,

            "normalized_name":
                normalize(name),

            "district":
                asset.get("district"),

            "latitude":
                asset.get("latitude"),

            "longitude":
                asset.get("longitude"),

            "built_year":
                asset.get("built_year"),

            "material":
                asset.get("material"),

            "design_life_years":
                asset.get("design_life_years"),

            "source_strategy":
                source_strategy(name),

            "identity_status":
                "PENDING_GOVERNMENT_MATCH",

            "endowments_match":
                "PENDING",

            "asi_match":
                "PENDING",

            "conservation_evidence":
                "PENDING",
        })

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if rows:

        with OUT.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as f:

            writer = csv.DictWriter(
                f,
                fieldnames=rows[0].keys()
            )

            writer.writeheader()
            writer.writerows(rows)

    else:

        OUT.write_text(
            "",
            encoding="utf-8"
        )

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
        k: v
        for k, v in duplicate_groups.items()
        if len(v) > 1
    }

    lines = [
        "=" * 105,
        "SIMRAS STEP 5A - ANDHRA PRADESH TEMPLE INVENTORY",
        "=" * 105,
        "",
        f"Temple assets found          : {len(rows)}",
        f"Unique normalized temples    : {len(duplicate_groups)}",
        f"Potential duplicate groups   : {len(duplicates)}",
        "",
    ]

    for row in rows:

        lines.append(
            f"{row['asset_code']} | "
            f"{row['asset_name']} | "
            f"district={row['district']} | "
            f"built_year={row['built_year']} | "
            f"lat={row['latitude']} | "
            f"lon={row['longitude']}"
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
                    f"    - {row['asset_code']} | "
                    f"{row['asset_name']}"
                )

    lines += [
        "",
        "Government evidence plan:",
        "  1. AP Endowments / TMS identity",
        "  2. ASI protected-monument registry",
        "  3. Government conservation / restoration procurement",
        "",
        f"Source plan: {OUT}",
        "=" * 105,
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

                "temple_assets":
                    len(rows),

                "unique_normalized_temples":
                    len(duplicate_groups),

                "potential_duplicate_groups":
                    len(duplicates),

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

    await engine.dispose()


asyncio.run(main())
