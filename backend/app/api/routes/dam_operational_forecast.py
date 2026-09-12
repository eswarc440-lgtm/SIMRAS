from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.db.session import engine


router = APIRouter(
    prefix="/api/v1/assets",
    tags=["Dam Operational Forecast"],
)


@router.get(
    "/{asset_code}/operational-forecast"
)
async def operational_forecast(
    asset_code: str,
):
    async with engine.connect() as conn:

        asset = (
            await conn.execute(
                text(
                    """
                    SELECT
                        asset_code,
                        name,
                        asset_type,
                        district
                    FROM public.assets
                    WHERE asset_code=:asset_code
                    LIMIT 1
                    """
                ),
                {
                    "asset_code":
                        asset_code
                },
            )
        ).mappings().first()


        if not asset:
            raise HTTPException(
                status_code=404,
                detail="Asset not found",
            )


        asset_type = str(
            asset[
                "asset_type"
            ]
        ).lower()


        if asset_type not in {
            "dam",
            "barrage",
        }:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Operational reservoir forecast "
                    "applies only to dams/barrages"
                ),
            )


        prediction = (
            await conn.execute(
                text(
                    """
                    SELECT *
                    FROM
                    public.dam_barrage_operational_predictions_v1
                    WHERE asset_code=:asset_code
                    LIMIT 1
                    """
                ),
                {
                    "asset_code":
                        asset_code
                },
            )
        ).mappings().first()


    if not prediction:

        return {
            "asset_code":
                asset_code,

            "asset_name":
                asset[
                    "name"
                ],

            "status":
                "WITHHELD",

            "reason":
                (
                    "No operational ML model has passed "
                    "held-out validation for this asset."
                ),

            "prediction_semantics":
                (
                    "NEXT_DAY_RESERVOIR_OPERATIONAL_FORECAST"
                ),

            "structural_prediction":
                False,
        }


    return {
        "asset_code":
            asset_code,

        "asset_name":
            asset[
                "name"
            ],

        "district":
            asset[
                "district"
            ],

        **dict(
            prediction
        ),

        "structural_prediction":
            False,

        "structural_health":
            "WITHHELD",

        "structural_failure_risk":
            "WITHHELD",

        "rul":
            "WITHHELD",
    }