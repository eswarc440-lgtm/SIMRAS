from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.assets import get_db


router = APIRouter(
    prefix="/api/v1/assets",
    tags=["assets"],
)


@router.get("/{asset_code}/bridge-report-profile")
async def get_bridge_report_profile(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
):
    asset = (
        await session.execute(
            text(
                """
                SELECT
                    id,
                    asset_code,
                    name,
                    district,
                    CAST(asset_type AS TEXT) AS asset_type,
                    built_year,
                    CAST(identity_status AS TEXT) AS identity_status
                FROM public.assets
                WHERE asset_code=:asset_code
                LIMIT 1
                """
            ),
            {"asset_code": asset_code},
        )
    ).mappings().first()

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found",
        )

    asset_type = str(
        asset["asset_type"] or ""
    ).lower()

    if asset_type != "bridge":
        raise HTTPException(
            status_code=400,
            detail="Asset is not a bridge",
        )

    engineering = await session.scalar(
        text(
            """
            SELECT to_jsonb(p)
            FROM public.bridge_digital_twin_profiles p
            WHERE p.asset_id=:asset_id
            LIMIT 1
            """
        ),
        {"asset_id": int(asset["id"])},
    )

    readiness = await session.scalar(
        text(
            """
            SELECT to_jsonb(r)
            FROM public.bridge_report_readiness r
            WHERE r.asset_id=:asset_id
            LIMIT 1
            """
        ),
        {"asset_id": int(asset["id"])},
    )

    return {
        "available": bool(
            engineering or readiness
        ),

        "asset": {
            "asset_code": asset["asset_code"],
            "name": asset["name"],
            "district": asset["district"],
            "asset_type": asset_type,
            "built_year": asset["built_year"],
            "identity_status": asset["identity_status"],
        },

        "engineering": (
            engineering
            if isinstance(engineering, dict)
            else None
        ),

        "readiness": (
            readiness
            if isinstance(readiness, dict)
            else None
        ),

        "report_policy": {
            "reported_width":
                (
                    engineering.get("reported_width_m")
                    if isinstance(engineering, dict)
                    else None
                ),

            "render_width_is_fact":
                False,

            "health":
                "WITHHELD unless real structural inspection evidence exists",

            "risk":
                "Only stored reportable prediction may be shown",

            "confidence":
                "WITHHELD without AP validation",

            "rul":
                "WITHHELD without validated longitudinal deterioration evidence",
        },
    }