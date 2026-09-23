import os
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():

    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not url:
        raise RuntimeError("DATABASE_URL unavailable")

    if url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    engine = create_async_engine(
        url,
        pool_pre_ping=True
    )

    async with engine.connect() as conn:

        print("=" * 105)
        print("SIMRAS MAIN INFRASTRUCTURE DATABASE COUNTS")
        print("=" * 105)
        print()

        result = await conn.execute(
            text("""
                SELECT
                    UPPER(
                        CAST(asset_type AS TEXT)
                    ) AS asset_type,
                    COUNT(*) AS count
                FROM public.assets
                GROUP BY
                    UPPER(
                        CAST(asset_type AS TEXT)
                    )
                ORDER BY count DESC
            """)
        )

        rows = list(
            result.mappings()
        )

        counts = {
            str(r["asset_type"]):
                int(r["count"])
            for r in rows
        }

        targets = [
            "DAM",
            "BRIDGE",
            "BARRAGE",
            "AIRPORT",
            "TEMPLE",
        ]

        for t in targets:

            print(
                f"{t:<15}: "
                f"{counts.get(t, 0):,}"
            )

        print()
        print("-" * 105)
        print("BARRAGE ASSETS")
        print("-" * 105)

        barrage_result = await conn.execute(
            text("""
                SELECT
                    id,
                    asset_code,
                    name,
                    district,
                    identity_status,
                    is_estimated
                FROM public.assets
                WHERE
                    UPPER(
                        CAST(asset_type AS TEXT)
                    )='BARRAGE'
                ORDER BY name
            """)
        )

        barrages = list(
            barrage_result.mappings()
        )

        for row in barrages:

            print(
                f"{row['asset_code']} | "
                f"{row['name']} | "
                f"district={row['district']} | "
                f"identity={row['identity_status']} | "
                f"estimated={row['is_estimated']}"
            )

        print()
        print(
            f"TOTAL BARRAGES IN public.assets: "
            f"{len(barrages)}"
        )

        print()

        # Check normalized dam/barrage evidence.
        exists = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema='public'
                      AND table_name=
                          'asset_engineering_evidence_normalized'
                )
            """)
        )

        if exists.scalar():

            evidence = await conn.execute(
                text("""
                    SELECT COUNT(
                        DISTINCT asset_id
                    )
                    FROM
                        public.asset_engineering_evidence_normalized
                """)
            )

            print(
                "Normalized dam/barrage engineering "
                f"assets: {int(evidence.scalar() or 0):,}"
            )

        print()
        print("=" * 105)

    await engine.dispose()


asyncio.run(main())
