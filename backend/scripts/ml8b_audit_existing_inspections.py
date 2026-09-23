import os
import json
import csv
import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


OUTDIR = Path(
    "/app/data/bridge_inspections/ml8b_audit"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True,
)


def db_url():
    url = os.environ["DATABASE_URL"]

    if url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    return url


def normalize(value):
    if value is None:
        return None

    return str(value).strip()


async def main():

    engine = create_async_engine(
        db_url()
    )

    report = {
        "table": "public.inspections",
        "read_only": True,
    }


    async with engine.connect() as conn:

        # ====================================================
        # TABLE EXISTS
        # ====================================================

        exists = await conn.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema='public'
                    AND table_name='inspections'
                )
                """
            )
        )

        if not exists:
            raise RuntimeError(
                "public.inspections does not exist."
            )


        # ====================================================
        # COLUMN SCHEMA
        # ====================================================

        columns = (
            await conn.execute(
                text(
                    """
                    SELECT
                        column_name,
                        data_type,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema='public'
                    AND table_name='inspections'
                    ORDER BY ordinal_position
                    """
                )
            )
        ).mappings().all()

        column_names = [
            row["column_name"]
            for row in columns
        ]

        report["columns"] = [
            dict(row)
            for row in columns
        ]


        print()
        print(
            "===== INSPECTIONS SCHEMA ====="
        )

        for row in columns:
            print(
                f"{row['column_name']:<30} "
                f"{row['data_type']:<28} "
                f"nullable={row['is_nullable']}"
            )


        # ====================================================
        # COUNTS
        # ====================================================

        total_rows = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.inspections
                """
            )
        )

        report["total_rows"] = total_rows

        print()
        print(
            "===== INSPECTION COUNTS ====="
        )

        print(
            "TOTAL_ROWS =",
            total_rows,
        )


        # ====================================================
        # SAMPLE FULL ROWS
        # ====================================================

        samples = (
            await conn.execute(
                text(
                    """
                    SELECT to_jsonb(i)
                    FROM public.inspections i
                    ORDER BY 1::text
                    LIMIT 20
                    """
                )
            )
        ).scalars().all()

        report["samples"] = samples

        print()
        print(
            "===== SAMPLE ROWS ====="
        )

        for index, row in enumerate(
            samples,
            start=1,
        ):
            print()
            print(
                f"--- SAMPLE {index} ---"
            )
            print(
                json.dumps(
                    row,
                    indent=2,
                    default=str,
                )
            )


        # ====================================================
        # POSSIBLE ASSET LINKAGE
        # ====================================================

        asset_link = None

        if "asset_id" in column_names:
            asset_link = "asset_id"

        elif "asset_code" in column_names:
            asset_link = "asset_code"

        elif "infrastructure_id" in column_names:
            asset_link = "infrastructure_id"


        report["asset_link_column"] = asset_link

        print()
        print(
            "===== ASSET LINKAGE ====="
        )

        print(
            "ASSET_LINK_COLUMN =",
            asset_link,
        )


        bridge_rows = None
        matched_ap_bridges = None


        if asset_link == "asset_id":

            bridge_rows = await conn.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.inspections i
                    JOIN public.assets a
                      ON a.id=i.asset_id
                    WHERE
                        LOWER(
                            CAST(a.asset_type AS TEXT)
                        )='bridge'
                        AND a.asset_code LIKE 'AP_BR_%'
                    """
                )
            )


            matched_ap_bridges = await conn.scalar(
                text(
                    """
                    SELECT COUNT(
                        DISTINCT a.asset_code
                    )
                    FROM public.inspections i
                    JOIN public.assets a
                      ON a.id=i.asset_id
                    WHERE
                        LOWER(
                            CAST(a.asset_type AS TEXT)
                        )='bridge'
                        AND a.asset_code LIKE 'AP_BR_%'
                    """
                )
            )


        elif asset_link == "asset_code":

            bridge_rows = await conn.scalar(
                text(
                    """
                    SELECT COUNT(*)
                    FROM public.inspections i
                    JOIN public.assets a
                      ON a.asset_code=i.asset_code
                    WHERE
                        LOWER(
                            CAST(a.asset_type AS TEXT)
                        )='bridge'
                        AND a.asset_code LIKE 'AP_BR_%'
                    """
                )
            )


            matched_ap_bridges = await conn.scalar(
                text(
                    """
                    SELECT COUNT(
                        DISTINCT a.asset_code
                    )
                    FROM public.inspections i
                    JOIN public.assets a
                      ON a.asset_code=i.asset_code
                    WHERE
                        LOWER(
                            CAST(a.asset_type AS TEXT)
                        )='bridge'
                        AND a.asset_code LIKE 'AP_BR_%'
                    """
                )
            )


        print(
            "AP_BRIDGE_INSPECTION_ROWS =",
            bridge_rows,
        )

        print(
            "AP_BRIDGES_WITH_INSPECTIONS =",
            matched_ap_bridges,
        )

        report[
            "ap_bridge_inspection_rows"
        ] = bridge_rows

        report[
            "ap_bridges_with_inspections"
        ] = matched_ap_bridges


        # ====================================================
        # SUSPECT SYNTHETIC / TEST / DEMO CONTENT
        #
        # This is only a warning audit.
        # No row is deleted or classified automatically.
        # ====================================================

        suspicious = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.inspections i
                WHERE
                    LOWER(
                        to_jsonb(i)::text
                    ) LIKE ANY (
                        ARRAY[
                            '%synthetic%',
                            '%demo%',
                            '%test%',
                            '%dummy%',
                            '%mock%',
                            '%sample%',
                            '%fake%'
                        ]
                    )
                """
            )
        )

        report[
            "suspicious_text_rows"
        ] = suspicious

        print()
        print(
            "===== SYNTHETIC / DEMO HEURISTIC ====="
        )

        print(
            "SUSPICIOUS_TEXT_ROWS =",
            suspicious,
        )

        print(
            "NOTE = heuristic only; no row is promoted or rejected automatically"
        )


        # ====================================================
        # IMPORTANT FIELD AUDIT
        # ====================================================

        candidate_fields = [
            "inspection_date",
            "date",
            "inspected_at",
            "inspection_type",
            "inspection_authority",
            "authority",
            "inspector",
            "source",
            "source_id",
            "source_url",
            "quality_flag",
            "quality_status",
            "condition",
            "condition_rating",
            "condition_score",
            "rating",
            "overall_rating",
            "status",
            "is_synthetic",
            "is_verified",
            "verified",
            "remarks",
            "notes",
        ]


        present_candidates = [
            field
            for field in candidate_fields
            if field in column_names
        ]

        report[
            "candidate_evidence_fields"
        ] = present_candidates


        print()
        print(
            "===== EVIDENCE FIELDS PRESENT ====="
        )

        if present_candidates:
            for value in present_candidates:
                print(value)
        else:
            print(
                "NONE OF THE EXPECTED EVIDENCE FIELDS FOUND"
            )


        # ====================================================
        # DISTINCT VALUE AUDIT
        # ====================================================

        categorical_candidates = [
            "inspection_type",
            "inspection_authority",
            "authority",
            "source",
            "source_id",
            "quality_flag",
            "quality_status",
            "condition",
            "condition_rating",
            "rating",
            "overall_rating",
            "status",
            "is_synthetic",
            "is_verified",
            "verified",
        ]


        distinct_values = {}


        for field in categorical_candidates:

            if field not in column_names:
                continue

            # Field name comes from information_schema,
            # not user input.
            sql = f"""
                SELECT
                    CAST("{field}" AS TEXT) AS value,
                    COUNT(*) AS row_count
                FROM public.inspections
                GROUP BY CAST("{field}" AS TEXT)
                ORDER BY row_count DESC
                LIMIT 30
            """

            rows = (
                await conn.execute(
                    text(sql)
                )
            ).mappings().all()

            distinct_values[field] = [
                dict(row)
                for row in rows
            ]


            print()
            print(
                f"===== VALUES: {field} ====="
            )

            for row in rows:
                print(
                    row["value"],
                    "=",
                    row["row_count"],
                )


        report[
            "distinct_values"
        ] = distinct_values


        # ====================================================
        # GODAVARI INSPECTIONS
        # ====================================================

        godavari_rows = []


        if asset_link == "asset_id":

            godavari_rows = (
                await conn.execute(
                    text(
                        """
                        SELECT to_jsonb(i)
                        FROM public.inspections i
                        JOIN public.assets a
                          ON a.id=i.asset_id
                        WHERE
                            a.asset_code='AP_BR_00001'
                        LIMIT 50
                        """
                    )
                )
            ).scalars().all()


        elif asset_link == "asset_code":

            godavari_rows = (
                await conn.execute(
                    text(
                        """
                        SELECT to_jsonb(i)
                        FROM public.inspections i
                        WHERE
                            i.asset_code='AP_BR_00001'
                        LIMIT 50
                        """
                    )
                )
            ).scalars().all()


        report[
            "godavari_existing_inspections"
        ] = godavari_rows


        print()
        print(
            "===== GODAVARI EXISTING INSPECTIONS ====="
        )

        print(
            "GODAVARI_INSPECTION_ROWS =",
            len(godavari_rows),
        )

        for row in godavari_rows:

            print(
                json.dumps(
                    row,
                    indent=2,
                    default=str,
                )
            )


        # ====================================================
        # OLD ASSET CONDITION MUST NOT BE USED AS LABEL
        # ====================================================

        godavari_condition = await conn.scalar(
            text(
                """
                SELECT condition
                FROM public.assets
                WHERE asset_code='AP_BR_00001'
                LIMIT 1
                """
            )
        )


        print()
        print(
            "===== LABEL SAFETY ====="
        )

        print(
            "GODAVARI_ASSET_CONDITION =",
            godavari_condition,
        )

        print(
            "ASSET_CONDITION_USED_AS_ML_LABEL = NO"
        )


        # ====================================================
        # CURRENT ML-8A TARGET TABLE
        # ====================================================

        target_rows = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.ml_bridge_inspections_v1
                """
            )
        )


        print()
        print(
            "ML8_TARGET_INSPECTION_ROWS =",
            target_rows,
        )

        print(
            "PROMOTED_FROM_OLD_INSPECTIONS = 0"
        )


    # ========================================================
    # WRITE AUDIT FILES
    # ========================================================

    json_path = (
        OUTDIR
        / "existing_inspections_audit.json"
    )

    json_path.write_text(
        json.dumps(
            report,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


    sample_csv = (
        OUTDIR
        / "existing_inspections_samples.csv"
    )


    if samples:

        keys = sorted(
            {
                key
                for row in samples
                if isinstance(row, dict)
                for key in row.keys()
            }
        )

        with sample_csv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=keys,
            )

            writer.writeheader()

            for row in samples:

                flat = {}

                for key in keys:

                    value = row.get(key)

                    if isinstance(
                        value,
                        (dict, list),
                    ):
                        value = json.dumps(
                            value,
                            default=str,
                        )

                    flat[key] = value

                writer.writerow(flat)


    print()
    print(
        "AUDIT_JSON =",
        json_path,
    )

    print(
        "SAMPLE_CSV =",
        sample_csv,
    )

    print()
    print(
        "ML8B_AUDIT=PASS"
    )


    await engine.dispose()


asyncio.run(
    main()
)