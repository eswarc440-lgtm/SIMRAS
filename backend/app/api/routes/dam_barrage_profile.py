from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.assets import get_db


router = APIRouter(
    prefix="/api/v1/assets",
    tags=["assets"],
)


@router.get("/{asset_code}/dam-barrage-profile")
async def get_dam_barrage_profile(
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
                    identity_status
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

    engineering = await session.scalar(
        text(
            """
            SELECT to_jsonb(p)
            FROM public.dam_barrage_engineering_profiles p
            WHERE p.asset_id=:asset_id
            LIMIT 1
            """
        ),
        {"asset_id": int(asset["id"])},
    )

    hydrology = await session.scalar(
        text(
            """
            SELECT to_jsonb(h)
            FROM public.dam_barrage_current_hydrology h
            WHERE h.asset_id=:asset_id
            LIMIT 1
            """
        ),
        {"asset_id": int(asset["id"])},
    )

    return {
        "available": bool(engineering or hydrology),

        "asset": {
            "asset_code": asset["asset_code"],
            "name": asset["name"],
            "district": asset["district"],
            "asset_type": str(
                asset["asset_type"] or ""
            ).lower(),
            "built_year": asset["built_year"],
            "identity_status": (
                str(asset["identity_status"])
                if asset["identity_status"] is not None
                else None
            ),
            "latitude": (
                engineering.get("cwc_latitude")
                if isinstance(engineering, dict)
                else None
            ),
            "longitude": (
                engineering.get("cwc_longitude")
                if isinstance(engineering, dict)
                else None
            ),
        },

        "engineering": (
            engineering
            if isinstance(engineering, dict)
            else None
        ),

        "hydrology": (
            hydrology
            if isinstance(hydrology, dict)
            else None
        ),

        "prediction_policy": {
            "health": "WITHHELD",
            "risk": "WITHHELD",
            "confidence": "WITHHELD",
            "rul": "WITHHELD",
        },
    }