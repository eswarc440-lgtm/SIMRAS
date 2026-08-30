from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


router = APIRouter(
    prefix="/twin-catalog",
    tags=["digital-twin"],
)


def _dimension_count(value: Any) -> int:
    if isinstance(value, dict):
        return len(value)
    return 0


def _quality_score(
    *,
    fidelity: str,
    has_model_uri: bool,
    is_asset_specific: bool,
    has_source: bool,
    dimension_count: int,
    identity_status: str,
) -> int:
    base = {
        "L4": 95,
        "L3": 90,
        "L2": 82,
        "L1": 68,
        "L0": 18,
        "NO_MODEL": 0,
    }.get(fidelity, 0)

    score = base

    if has_model_uri:
        score += 8

    if is_asset_specific:
        score += 6

    if has_source:
        score += 6

    score += min(dimension_count, 8)

    if identity_status == "VERIFIED":
        score += 4

    return min(100, int(score))


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
                    am.fidelity_level,
                    am.is_asset_specific,
                    am.model_uri,
                    am.model_source,
                    am.source_url,
                    am.dimensions
                FROM assets a
                LEFT JOIN LATERAL (
                    SELECT m.*
                    FROM asset_models m
                    WHERE m.asset_id = a.id
                      AND m.is_active = TRUE
                    ORDER BY
                        m.updated_at DESC NULLS LAST,
                        m.id DESC
                    LIMIT 1
                ) am ON TRUE
                ORDER BY a.name
                """
            )
        )
    ).mappings().all()

    items: list[dict[str, Any]] = []

    for row in rows:
        dimensions = row["dimensions"]
        if not isinstance(dimensions, dict):
            dimensions = {}

        fidelity = str(row["fidelity_level"] or "NO_MODEL")
        identity_status = str(row["identity_status"] or "UNKNOWN")
        is_asset_specific = bool(row["is_asset_specific"])
        has_model_uri = bool(row["model_uri"])
        has_source = bool(row["source_url"])
        dimension_count = _dimension_count(dimensions)

        representation = str(
            dimensions.get(
                "representation",
                "NO_REPRESENTATION",
            )
        )

        template = str(
            dimensions.get(
                "template",
                "generic",
            )
        )

        representation_lower = representation.lower()

        source_backed = bool(
            fidelity not in {"L0", "NO_MODEL"}
            and is_asset_specific
            and (
                has_source
                or has_model_uri
                or "source_backed" in representation_lower
                or "source_extracted" in representation_lower
            )
        )

        score = _quality_score(
            fidelity=fidelity,
            has_model_uri=has_model_uri,
            is_asset_specific=is_asset_specific,
            has_source=has_source,
            dimension_count=dimension_count,
            identity_status=identity_status,
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

        items.append(
            {
                "asset_code": row["asset_code"],
                "name": row["name"],
                "asset_type": row["asset_type"],
                "subtype": row["subtype"],
                "district": row["district"],
                "identity_status": identity_status,
                "fidelity_level": fidelity,
                "is_asset_specific": is_asset_specific,
                "has_model_uri": has_model_uri,
                "has_source": has_source,
                "dimension_count": dimension_count,
                "representation": representation,
                "template": template,
                "model_source": (
                    row["model_source"]
                    or "No source-backed model"
                ),
                "source_url": row["source_url"],
                "source_backed": source_backed,
                "twin_quality_score": score,
                "twin_quality": quality,
                "twin_group": group,
                "twin_quality_label": label,
            }
        )

    items.sort(
        key=lambda item: (
            -int(item["twin_quality_score"]),
            0 if item["identity_status"] == "VERIFIED" else 1,
            str(item["name"]).lower(),
        )
    )

    return {
        "items": items,
        "counts": {
            "best": sum(
                1 for item in items
                if item["twin_group"] == "BEST"
            ),
            "improving": sum(
                1 for item in items
                if item["twin_group"] == "IMPROVING"
            ),
            "basic": sum(
                1 for item in items
                if item["twin_group"] == "BASIC"
            ),
            "total": len(items),
        },
    }