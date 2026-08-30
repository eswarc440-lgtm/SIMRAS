from __future__ import annotations

import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal


async def main() -> None:
    async with SessionLocal() as session:
        print("=" * 78)
        print("SIMRAS DIGITAL-TWIN TRUTH AUDIT")
        print("=" * 78)

        rows = (
            await session.execute(
                text(
                    """
                    SELECT
                        a.asset_code,
                        a.name,
                        a.asset_type,
                        a.subtype,
                        a.identity_status,
                        am.fidelity_level,
                        am.is_asset_specific,
                        am.model_source,
                        am.source_url,
                        am.dimensions
                    FROM assets a
                    LEFT JOIN LATERAL (
                        SELECT *
                        FROM asset_models m
                        WHERE m.asset_id = a.id
                          AND m.is_active = TRUE
                        ORDER BY m.updated_at DESC NULLS LAST, m.id DESC
                        LIMIT 1
                    ) am ON TRUE
                    WHERE a.asset_code IN (
                        'AP_DAM_00001',
                        'AP_DAM_NWDP_AP01VH0059',
                        'AP_BR_00001'
                    )
                    ORDER BY a.asset_code
                    """
                )
            )
        ).mappings().all()

        for row in rows:
            print()
            print(dict(row))

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
                        am.source_url
                    FROM asset_models am
                    JOIN assets a ON a.id = am.asset_id
                    WHERE am.is_active = TRUE
                      AND am.fidelity_level <> 'L0'
                      AND (
                            a.identity_status <> 'VERIFIED'
                         OR am.is_asset_specific IS NOT TRUE
                         OR am.source_url IS NULL
                      )
                    ORDER BY a.asset_code
                    """
                )
            )
        ).mappings().all()

        print()
        print("MULTIPLE ACTIVE MODELS:", len(duplicates))
        print("SUSPECT NON-L0 MODELS:", len(suspect))

        for row in duplicates:
            print("DUPLICATE:", dict(row))

        for row in suspect:
            print("SUSPECT:", dict(row))

        print(
            "INTEGRITY RESULT:",
            "PASS" if not duplicates and not suspect else "REVIEW REQUIRED",
        )


if __name__ == "__main__":
    asyncio.run(main())
