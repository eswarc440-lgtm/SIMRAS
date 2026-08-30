from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal


async def main() -> None:
    async with SessionLocal() as session:
        summary = (
            await session.execute(
                text(
                    """
                    SELECT
                        COALESCE(am.fidelity_level, 'NO_MODEL') AS fidelity,
                        COUNT(*) AS assets
                    FROM assets a
                    LEFT JOIN LATERAL (
                        SELECT *
                        FROM asset_models x
                        WHERE x.asset_id = a.id
                          AND x.is_active = TRUE
                        ORDER BY x.updated_at DESC NULLS LAST, x.id DESC
                        LIMIT 1
                    ) am ON TRUE
                    GROUP BY COALESCE(am.fidelity_level, 'NO_MODEL')
                    ORDER BY fidelity
                    """
                )
            )
        ).mappings().all()

        duplicates = (
            await session.execute(
                text(
                    """
                    SELECT a.asset_code, COUNT(*) AS active_models
                    FROM asset_models am
                    JOIN assets a ON a.id = am.asset_id
                    WHERE am.is_active = TRUE
                    GROUP BY a.asset_code
                    HAVING COUNT(*) > 1
                    """
                )
            )
        ).mappings().all()

        suspect = (
            await session.execute(
                text(
                    """
                    SELECT
                        a.asset_code,
                        a.name,
                        a.identity_status,
                        am.fidelity_level,
                        am.is_asset_specific,
                        am.source_url,
                        am.model_source
                    FROM asset_models am
                    JOIN assets a ON a.id = am.asset_id
                    WHERE am.is_active = TRUE
                      AND am.fidelity_level <> 'L0'
                      AND (
                            a.identity_status <> 'VERIFIED'
                         OR am.is_asset_specific IS NOT TRUE
                      )
                    ORDER BY a.asset_code
                    """
                )
            )
        ).mappings().all()

        print("=" * 72)
        print("SIMRAS REAL-TWIN AUDIT")
        print("=" * 72)

        for row in summary:
            print(dict(row))

        print("multiple_active_models:", len(duplicates))
        print("suspect_non_l0_models:", len(suspect))

        for row in suspect[:20]:
            print("SUSPECT:", dict(row))

        print(
            "AUDIT:",
            "PASS" if not duplicates and not suspect else "REVIEW REQUIRED",
        )


if __name__ == "__main__":
    asyncio.run(main())