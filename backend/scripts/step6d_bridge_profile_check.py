import os
import asyncio
import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


async def main():

    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not url:
        raise RuntimeError("DATABASE_URL missing")

    if url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    engine = create_async_engine(url)

    async with engine.connect() as conn:

        result = await conn.execute(
            text("""
                SELECT *
                FROM public.bridge_digital_twin_profiles
                WHERE asset_id = (
                    SELECT id
                    FROM public.assets
                    WHERE asset_code='AP_BR_00001'
                    LIMIT 1
                )
            """)
        )

        row = result.mappings().first()

        if not row:
            print("NO BRIDGE PROFILE")
            return

        value = dict(row)

        for key, item in value.items():

            if item is None:
                continue

            text_value = str(item)

            if len(text_value) > 1500:
                text_value = (
                    text_value[:1500]
                    + "...[TRUNCATED]"
                )

            print(
                f"{key} = {text_value}"
            )

    await engine.dispose()


asyncio.run(main())
