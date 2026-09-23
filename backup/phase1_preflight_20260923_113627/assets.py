from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import Asset
from app.schemas.twin import AssetListResponse, AssetSummary, GeoJSONFeatureCollection, TwinResponse
from app.services.twin_service import build_asset_summary, build_twin, get_asset_row

router = APIRouter(prefix="/assets", tags=["assets"])

MAIN_ASSET_TYPES = (
    "dam",
    "bridge",
    "barrage",
    "airport",
    "temple",
)



@router.get("", response_model=AssetListResponse)
async def list_assets(
    asset_type: str | None = Query(
        default=None,
        pattern="^(bridge|dam|barrage|airport|temple)$",
    ),
    district: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> AssetListResponse:
    filters = [
        func.lower(Asset.asset_type).in_(
            MAIN_ASSET_TYPES
        ),

        # SIMRAS bridge scope:
        # expose only Andhra Pradesh bridge assets.
        #
        # AP bridge identifiers created by the statewide
        # AP bridge pipeline use AP_BR_*.
        or_(
            func.lower(Asset.asset_type) != "bridge",
            Asset.asset_code.ilike("AP_BR_%"),
        ),
    ]

    if asset_type:
        filters.append(
            func.lower(Asset.asset_type)
            == asset_type.lower()
        )

    if district:
        filters.append(
            func.lower(Asset.district)
            == district.lower()
        )

    if search:
        search_pattern = f"%{search}%"

        filters.append(
            or_(
                Asset.name.ilike(search_pattern),
                Asset.asset_code.ilike(search_pattern),
                Asset.district.ilike(search_pattern),
            )
        )

    total = await session.scalar(select(func.count()).select_from(Asset).where(*filters))
    rows = (
        await session.execute(
            select(
                Asset,
                func.ST_X(Asset.representative_geometry).label("longitude"),
                func.ST_Y(Asset.representative_geometry).label("latitude"),
            )
            .where(*filters)
            .order_by(Asset.name)
            .limit(limit)
            .offset(offset)
        )
    ).all()
    items = [AssetSummary.model_validate(await build_asset_summary(session, row)) for row in rows]
    return AssetListResponse(items=items, total=total or 0, limit=limit, offset=offset)


@router.get("/high-risk", response_model=list[AssetSummary])
async def high_risk_assets(
    limit: int = Query(default=10, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
) -> list[AssetSummary]:
    response = await list_assets(
        asset_type=None,
        district=None,
        search=None,
        limit=1000,
        offset=0,
        session=session,
    )
    ranked = sorted(response.items, key=lambda item: item.risk_score or -1, reverse=True)
    return ranked[:limit]


@router.get("/geojson", response_model=GeoJSONFeatureCollection)
async def assets_geojson(
    asset_type: str | None = None,
    session: AsyncSession = Depends(get_db),
) -> GeoJSONFeatureCollection:
    response = await list_assets(
        asset_type=asset_type,
        district=None,
        search=None,
        limit=1000,
        offset=0,
        session=session,
    )
    return GeoJSONFeatureCollection(
        features=[
            {
                "type": "Feature",
                "id": item.asset_code,
                "geometry": item.geometry.model_dump(),
                "properties": item.model_dump(exclude={"geometry"}),
            }
            for item in response.items
        ]
    )



@router.get("/{asset_code}/bridge-profile")
async def get_bridge_profile(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
):
    asset = (
        await session.execute(
            select(Asset).where(
                Asset.asset_code == asset_code
            )
        )
    ).scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail="Asset not found",
        )

    if str(asset.asset_type).lower() != "bridge":
        raise HTTPException(
            status_code=400,
            detail="Asset is not a bridge",
        )

    profile = await session.scalar(
        text("""
            SELECT
                row_to_json(p)::text
            FROM
                public.bridge_digital_twin_profiles p
            WHERE
                p.asset_id = :asset_id
            LIMIT 1
        """),
        {
            "asset_id": asset.id
        },
    )

    engineering = await session.scalar(
        text("""
            SELECT
                row_to_json(e)::text
            FROM
                public.bridge_engineering_features_verified e
            WHERE
                e.asset_id = :asset_id
            LIMIT 1
        """),
        {
            "asset_id": asset.id
        },
    )

    report = await session.scalar(
        text("""
            SELECT
                row_to_json(r)::text
            FROM
                public.bridge_report_readiness r
            WHERE
                r.asset_id = :asset_id
            LIMIT 1
        """),
        {
            "asset_id": asset.id
        },
    )

    return {
        "asset": {
            "id": asset.id,
            "asset_code": asset.asset_code,
            "name": asset.name,
            "district": asset.district,
            "asset_type": asset.asset_type,
            "identity_status": asset.identity_status,
            "is_estimated": asset.is_estimated,
        },
        "profile": profile,
        "engineering": engineering,
        "report": report,
    }



@router.get("/{asset_code}/risk-prediction")
async def get_asset_risk_prediction(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
):
    """
    Return the latest reportable stored Risk prediction.

    RESEARCH_TRANSFER means the model passed temporal
    FHWA NBI validation but has NOT been ground-truth
    validated on Andhra Pradesh bridge inspections.
    """

    import json

    from fastapi import HTTPException
    from sqlalchemy import text

    asset = (
        await session.execute(
            text(
                """
                SELECT
                    id,
                    asset_code,
                    name,
                    CAST(asset_type AS TEXT) AS asset_type
                FROM public.assets
                WHERE asset_code = :asset_code
                LIMIT 1
                """
            ),
            {
                "asset_code": asset_code,
            },
        )
    ).mappings().first()

    if asset is None:
        raise HTTPException(
            status_code=404,
            detail=f"Asset {asset_code!r} not found",
        )

    prediction = (
        await session.execute(
            text(
                """
                SELECT
                    id,
                    asset_id,
                    prediction_time,
                    target,
                    value,
                    predicted_class,
                    lower_bound,
                    upper_bound,
                    confidence_score,
                    model_version,
                    feature_version,
                    status,
                    factors
                FROM public.predictions
                WHERE
                    asset_id = :asset_id
                    AND LOWER(target) = 'risk'
                    AND status IN (
                        'VALIDATED_ML',
                        'RESEARCH_TRANSFER'
                    )
                ORDER BY
                    CASE
                        WHEN status = 'VALIDATED_ML'
                            THEN 0
                        WHEN status = 'RESEARCH_TRANSFER'
                            THEN 1
                        ELSE 2
                    END,
                    prediction_time DESC,
                    id DESC
                LIMIT 1
                """
            ),
            {
                "asset_id": int(
                    asset["id"]
                ),
            },
        )
    ).mappings().first()

    if prediction is None:

        return {
            "available": False,
            "asset_code": asset_code,
            "asset_name": asset["name"],
            "asset_type": str(
                asset["asset_type"]
                or ""
            ).lower(),
            "risk_score": None,
            "risk_level": None,
            "confidence_score": None,
            "status": "WITHHELD",
            "model_version": None,
            "feature_version": None,
            "prediction_time": None,
            "factors": None,
            "interpretation": (
                "No reportable stored Risk prediction "
                "is available for this asset."
            ),
        }

    factors = prediction["factors"]

    if isinstance(
        factors,
        str,
    ):

        try:
            factors = json.loads(
                factors
            )

        except Exception:
            factors = {
                "raw": factors,
            }

    if not isinstance(
        factors,
        dict,
    ):
        factors = {}

    risk_score = (
        float(
            prediction["value"]
        )
        if prediction["value"]
        is not None
        else None
    )

    confidence = (
        float(
            prediction[
                "confidence_score"
            ]
        )
        if prediction[
            "confidence_score"
        ]
        is not None
        else None
    )

    return {
        "available":
            risk_score is not None,

        "asset_code":
            asset_code,

        "asset_name":
            asset["name"],

        "asset_type":
            str(
                asset["asset_type"]
                or ""
            ).lower(),

        "risk_score":
            risk_score,

        "risk_level":
            prediction[
                "predicted_class"
            ],

        "confidence_score":
            confidence,

        "status":
            prediction[
                "status"
            ],

        "model_version":
            prediction[
                "model_version"
            ],

        "feature_version":
            prediction[
                "feature_version"
            ],

        "prediction_time":
            prediction[
                "prediction_time"
            ],

        "factors":
            factors,

        "interpretation":
            (
                "Risk Score is the calibrated probability "
                "of entering the model's POOR condition "
                "class at the next inspection, multiplied "
                "by 100. It is NOT probability of collapse "
                "or structural failure."
            ),
    }


@router.get("/{asset_code}", response_model=AssetSummary)
async def get_asset(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> AssetSummary:
    return AssetSummary.model_validate(
        await build_asset_summary(session, await get_asset_row(session, asset_code))
    )


@router.get("/{asset_code}/twin", response_model=TwinResponse)
async def get_twin(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> TwinResponse:
    return TwinResponse.model_validate(await build_twin(session, asset_code))
