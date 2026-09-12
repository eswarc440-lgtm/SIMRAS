from __future__ import annotations

import os
import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


REQUIRED = {
    "status",
    "identity_status",
    "representative_geometry",
    "is_estimated",
}


async def main():

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not db_url:
        raise RuntimeError("DATABASE_URL unavailable")

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

        result = await conn.execute(
            text("""
                SELECT
                    column_name,
                    data_type,
                    udt_name,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema='public'
                  AND table_name='assets'
                  AND column_name IN
                  (
                      'status',
                      'identity_status',
                      'representative_geometry',
                      'is_estimated'
                  )
                ORDER BY column_name
            """)
        )

        rows = [
            dict(r)
            for r in result.mappings()
        ]

        found = {
            r["column_name"]
            for r in rows
        }

        print("=" * 100)
        print("PUBLIC.ASSETS REQUIRED COLUMN CHECK")
        print("=" * 100)
        print()

        for row in rows:

            print(
                f"{row['column_name']:<26} | "
                f"type={row['data_type']} | "
                f"udt={row['udt_name']} | "
                f"nullable={row['is_nullable']} | "
                f"default={row['column_default']}"
            )

        missing = REQUIRED - found

        if missing:
            raise RuntimeError(
                "Required columns unexpectedly missing: "
                + ", ".join(sorted(missing))
            )

        geom = next(
            r
            for r in rows
            if r["column_name"] == "representative_geometry"
        )

        if geom["udt_name"] not in {
            "geometry",
            "geography",
        }:

            raise RuntimeError(
                "representative_geometry has unsupported type: "
                + str(geom["udt_name"])
            )

        print()
        print("EXISTING ASSET VALUES:")
        print()

        sample = await conn.execute(
            text("""
                SELECT
                    asset_code,
                    CAST(status AS TEXT) AS status,
                    CAST(identity_status AS TEXT) AS identity_status,
                    is_estimated,

                    CASE
                        WHEN representative_geometry IS NULL
                        THEN NULL
                        ELSE GeometryType(representative_geometry)
                    END AS geometry_type,

                    CASE
                        WHEN representative_geometry IS NULL
                        THEN NULL
                        ELSE ST_SRID(representative_geometry)
                    END AS srid

                FROM public.assets

                WHERE
                    asset_code IN
                    (
                        'AP_BR_00001',
                        'AP_BR_00002'
                    )

                ORDER BY asset_code
            """)
        )

        for row in sample.mappings():

            print(
                f"{row['asset_code']} | "
                f"status={row['status']} | "
                f"identity={row['identity_status']} | "
                f"estimated={row['is_estimated']} | "
                f"geometry={row['geometry_type']} | "
                f"srid={row['srid']}"
            )

        print()
        print("[PASS] public.assets schema understood")
        print("=" * 100)

    await engine.dispose()


asyncio.run(main())
