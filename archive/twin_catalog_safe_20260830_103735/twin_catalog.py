from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


router = APIRouter(
    prefix="/twin-catalog",
    tags=["digital-twin"],
)


@router.get("")
async def twin_catalog(
    session: AsyncSession = Depends(get_db),
) -> dict:
    rows = (
        await session.execute(
            text(
                """
                SELECT
                    a.asset_code,
                    a.name,
                    a.asset_type,
                    a.subtype,
                    a.district,
                    a.identity_status,
                    COALESCE(am.fidelity_level, 'NO_MODEL') AS fidelity_level,
                    COALESCE(am.is_asset_specific, FALSE) AS is_asset_specific,
                    (am.model_uri IS NOT NULL AND am.model_uri <> '') AS has_model_uri,
                    (am.source_url IS NOT NULL AND am.source_url <> '') AS has_source,
                    COALESCE(
                        jsonb_object_length(COALESCE(am.dimensions, '{}'::jsonb)),
                        0
                    ) AS dimension_count,
                    COALESCE(
                        am.dimensions->>'representation',
                        'NO_REPRESENTATION'
                    ) AS representation,
                    COALESCE(
                        am.dimensions->>'template',
                        'generic'
                    ) AS template,
                    COALESCE(
                        am.model_source,
                        'No source-backed model'
                    ) AS model_source,
                    am.source_url,
                    LEAST(
                        100,
                        CASE COALESCE(am.fidelity_level, 'NO_MODEL')
                            WHEN 'L4' THEN 95
                            WHEN 'L3' THEN 90
                            WHEN 'L2' THEN 82
                            WHEN 'L1' THEN 68
                            WHEN 'L0' THEN 18
                            ELSE 0
                        END
                        +
                        CASE
                            WHEN am.model_uri IS NOT NULL AND am.model_uri <> ''
                            THEN 8 ELSE 0
                        END
                        +
                        CASE
                            WHEN COALESCE(am.is_asset_specific, FALSE)
                            THEN 6 ELSE 0
                        END
                        +
                        CASE
                            WHEN am.source_url IS NOT NULL AND am.source_url <> ''
                            THEN 6 ELSE 0
                        END
                        +
                        LEAST(
                            COALESCE(
                                jsonb_object_length(COALESCE(am.dimensions, '{}'::jsonb)),
                                0
                            ),
                            8
                        )
                        +
                        CASE
                            WHEN a.identity_status = 'VERIFIED'
                            THEN 4 ELSE 0
                        END
                    )::INTEGER AS twin_quality_score
                FROM assets a
                LEFT JOIN LATERAL (
                    SELECT m.*
                    FROM asset_models m
                    WHERE m.asset_id = a.id
                      AND m.is_active = TRUE
                    ORDER BY m.updated_at DESC NULLS LAST, m.id DESC
                    LIMIT 1
                ) am ON TRUE
                ORDER BY
                    twin_quality_score DESC,
                    CASE WHEN a.identity_status = 'VERIFIED' THEN 0 ELSE 1 END,
                    a.name
                """
            )
        )
    ).mappings().all()

    items = []

    for row in rows:
        item = dict(row)
        score = int(item["twin_quality_score"] or 0)
        fidelity = str(item["fidelity_level"] or "NO_MODEL")
        representation = str(
            item["representation"] or ""
        ).lower()

        source_backed = bool(
            fidelity not in {"L0", "NO_MODEL"}
            and item["is_asset_specific"]
            and (
                item["has_source"]
                or item["has_model_uri"]
                or "source_backed" in representation
                or "source_extracted" in representation
            )
        )

        if score >= 90 and source_backed:
            quality = "EXCELLENT"
            group = "BEST"
            label = "High-quality source-backed twin"
        elif score >= 70 and source_backed:
            quality = "READY"
            group = "BEST"
            label = "Source-backed digital twin"
        elif score >= 40:
            quality = "PARTIAL"
            group = "IMPROVING"
            label = "Partial geometry / more source data needed"
        else:
            quality = "BASIC"
            group = "BASIC"
            label = "Illustrative / source geometry incomplete"

        item["source_backed"] = source_backed
        item["twin_quality"] = quality
        item["twin_group"] = group
        item["twin_quality_label"] = label
        items.append(item)

    return {
        "items": items,
        "counts": {
            "best": sum(1 for x in items if x["twin_group"] == "BEST"),
            "improving": sum(1 for x in items if x["twin_group"] == "IMPROVING"),
            "basic": sum(1 for x in items if x["twin_group"] == "BASIC"),
            "total": len(items),
        },
    }