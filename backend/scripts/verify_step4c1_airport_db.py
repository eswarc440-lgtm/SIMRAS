import os
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not db_url:
        raise RuntimeError(
            "DATABASE_URL / SQLALCHEMY_DATABASE_URI / POSTGRES_URL not available"
        )

    if db_url.startswith("postgresql://"):
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

        # ----------------------------------------------------------
        # VERIFY TABLE EXISTS
        # ----------------------------------------------------------

        exists_result = await conn.execute(
            text("""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name =
                          'airport_maintenance_evidence_verified'
                )
            """)
        )

        table_exists = bool(
            exists_result.scalar()
        )

        print()
        print("=" * 95)
        print("STEP 4C.1 DATABASE VERIFICATION")
        print("=" * 95)
        print()
        print(
            f"Table exists : "
            f"{'YES' if table_exists else 'NO'}"
        )

        if not table_exists:
            raise RuntimeError(
                "airport_maintenance_evidence_verified table does not exist"
            )

        # ----------------------------------------------------------
        # COUNTS BY AIRPORT
        # ----------------------------------------------------------

        result = await conn.execute(
            text("""
                SELECT
                    icao_code,
                    COUNT(*) AS events,

                    COUNT(*) FILTER (
                        WHERE maintenance_significance = 'HIGH'
                    ) AS high_events,

                    COALESCE(
                        SUM(estimated_cost_inr),
                        0
                    ) AS known_cost_inr

                FROM
                    public.airport_maintenance_evidence_verified

                GROUP BY
                    icao_code

                ORDER BY
                    icao_code
            """)
        )

        rows = result.mappings().all()

        total_events = 0
        total_high = 0

        for row in rows:

            events = int(
                row["events"] or 0
            )

            high = int(
                row["high_events"] or 0
            )

            cost = float(
                row["known_cost_inr"] or 0
            )

            total_events += events
            total_high += high

            print(
                f"{row['icao_code']:<6} | "
                f"events={events:<2} | "
                f"high={high:<2} | "
                f"known_cost=INR {cost:,.0f}"
            )

        # ----------------------------------------------------------
        # OVERALL COUNTS
        # ----------------------------------------------------------

        overall_result = await conn.execute(
            text("""
                SELECT
                    COUNT(*) AS total_rows,
                    COUNT(DISTINCT icao_code) AS airports,
                    COUNT(*) FILTER (
                        WHERE maintenance_significance = 'HIGH'
                    ) AS high_rows
                FROM
                    public.airport_maintenance_evidence_verified
            """)
        )

        overall = overall_result.mappings().one()

        db_rows = int(
            overall["total_rows"] or 0
        )

        db_airports = int(
            overall["airports"] or 0
        )

        db_high = int(
            overall["high_rows"] or 0
        )

        print()
        print("-" * 95)
        print(f"Airports in database     : {db_airports}")
        print(f"Maintenance records      : {db_rows}")
        print(f"High-significance records: {db_high}")
        print("-" * 95)

        # ----------------------------------------------------------
        # VERIFY EXPECTED CURRENT STEP 4C.1 DATASET
        # ----------------------------------------------------------

        expected = {
            "VOBZ": 2,
            "VOCP": 2,
            "VOKU": 1,
            "VORY": 2,
            "VOTP": 1,
            "VOVZ": 1,
        }

        actual = {
            str(row["icao_code"]): int(row["events"])
            for row in rows
        }

        problems = []

        for icao, expected_count in expected.items():

            actual_count = actual.get(
                icao,
                0
            )

            if actual_count != expected_count:

                problems.append(
                    f"{icao}: expected {expected_count}, "
                    f"found {actual_count}"
                )

        if db_airports != 6:

            problems.append(
                f"Expected 6 airports, found {db_airports}"
            )

        if db_rows != 9:

            problems.append(
                f"Expected 9 records, found {db_rows}"
            )

        if db_high != 3:

            problems.append(
                f"Expected 3 HIGH records, found {db_high}"
            )

        print()

        if problems:

            print("[FAIL] STEP 4C.1 DATABASE CONTENT DOES NOT MATCH")
            print()

            for problem in problems:
                print(f" - {problem}")

            raise RuntimeError(
                "Airport maintenance evidence verification mismatch"
            )

        print("[PASS] STEP 4C.1 DATABASE VERIFIED")
        print("[PASS] 6 physical airports")
        print("[PASS] 9 verified procurement/maintenance records")
        print("[PASS] 3 high-significance records")
        print()
        print("=" * 95)

    await engine.dispose()


asyncio.run(main())
