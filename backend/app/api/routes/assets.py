from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import Asset
from app.schemas.twin import AssetListResponse, AssetSummary, GeoJSONFeatureCollection, TwinResponse
from app.services.twin_service import build_asset_summary, build_twin, get_asset_row

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=AssetListResponse)
async def list_assets(
    asset_type: str | None = Query(default=None, pattern="^(bridge|dam|barrage|airport|temple)$"),
    district: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> AssetListResponse:
    filters = []
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if district:
        filters.append(Asset.district == district)
    if search:
        filters.append(Asset.name.ilike(f"%{search}%"))

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
