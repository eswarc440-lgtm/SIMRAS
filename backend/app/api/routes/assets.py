from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from geoalchemy2.elements import WKTElement
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_key
from app.db.session import get_db
from app.models.entities import Asset, AssetModel
from app.schemas.twin import AssetListResponse, AssetSummary, GeoJSONFeatureCollection, TwinResponse
from app.services.twin_service import build_asset_summary, build_twin, get_asset_row

router = APIRouter(prefix="/assets", tags=["assets"])


class AssetRegistrationRequest(BaseModel):
    asset_code: str | None = Field(default=None, max_length=50)
    name: str = Field(min_length=1, max_length=250)
    asset_type: str = Field(pattern="^(bridge|dam|barrage|airport|temple)$")
    subtype: str | None = Field(default=None, max_length=80)
    district: str = Field(min_length=1, max_length=120)
    state: str = "Andhra Pradesh"
    latitude: float = Field(ge=12, le=20)
    longitude: float = Field(ge=76, le=85)
    dimensions: dict = Field(default_factory=dict)
    built_year: int | None = Field(default=None, ge=1800, le=2100)
    material: str | None = Field(default=None, max_length=100)
    dimension_authority: str | None = Field(default=None, max_length=200)
    condition: str | None = Field(default=None, max_length=100)
    health_score: float | None = Field(default=None, ge=0, le=100)
    risk_score: float | None = Field(default=None, ge=0, le=100)
    priority: int | None = Field(default=2, ge=1, le=5)
    source_url: str | None = None
    submitted_by: str = Field(min_length=1, max_length=200)
    submitted_role: str = Field(pattern="^(OFFICER|ADMIN)$")

    @field_validator("asset_code", "name", "district", mode="before")
    @classmethod
    def trim_text(cls, value):
        if value is None:
            return value
        return str(value).strip()


@router.post("", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin_key)])
async def register_asset(
    request: AssetRegistrationRequest,
    session: AsyncSession = Depends(get_db),
) -> dict:
    prefix = "BR" if request.asset_type == "bridge" else request.asset_type[:3].upper()
    asset_code = request.asset_code or f"AP_{prefix}_{uuid4().hex[:12]}"
    exists = await session.scalar(select(Asset.id).where(Asset.asset_code == asset_code))
    if exists is not None:
        raise HTTPException(status_code=409, detail=f"Asset code {asset_code} already exists")

    asset = Asset(
        asset_code=asset_code,
        name=request.name,
        asset_type=request.asset_type,
        subtype=request.subtype or f"standard_{request.asset_type}",
        district=request.district,
        owner=request.state,
        status="PENDING_REVIEW",
        identity_status="PENDING_VERIFICATION",
        built_year=request.built_year,
        material=request.material,
        condition=request.condition or "Not assessed",
        representative_geometry=WKTElement(
            f"POINT({request.longitude} {request.latitude})", srid=4326
        ),
        confidence_score=None,
        is_estimated=False,
    )
    session.add(asset)
    await session.flush()
    session.add(
        AssetModel(
            asset_id=asset.id,
            model_uri=None,
            format="procedural",
            version="1",
            fidelity_level="L1_SOURCE_BACKED_PENDING_ASSET_MODEL",
            model_source=request.dimension_authority or "Officer registration",
            source_url=request.source_url,
            dimensions={**request.dimensions, "_registration": {"created_by": request.submitted_by, "created_at": datetime.now(timezone.utc).isoformat(), "status": "PENDING_REVIEW", "assessment_status": "WITHHELD"}},
            is_asset_specific=False,
            is_active=True,
        )
    )
    try:
        await session.commit()
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Asset registration conflicts with an existing database record") from error

    return {"asset_code": asset.asset_code, "name": asset.name, "status": "PENDING_REVIEW",
            "identity_status": "PENDING_VERIFICATION", "created_by": request.submitted_by,
            "created_at": asset.created_at.isoformat(), "assessment_status": "WITHHELD",
            "health_score": None, "risk_score": None, "rul_years": None}


@router.get("/registrations", dependencies=[Depends(require_admin_key)])
async def registrations(session: AsyncSession = Depends(get_db)):
    rows = (await session.execute(select(Asset, AssetModel).join(AssetModel, Asset.id == AssetModel.asset_id).where(AssetModel.is_active.is_(True)))).all()
    return [{"asset_code": asset.asset_code, "name": asset.name, "district": asset.district,
             **model.dimensions["_registration"]}
            for asset, model in rows if isinstance(model.dimensions, dict) and "_registration" in model.dimensions]


class RegistrationReview(BaseModel):
    status: str = Field(pattern="^(APPROVED|REJECTED)$")
    comments: str = Field(min_length=1, max_length=4000)
    reviewed_by: str = Field(min_length=1)
    reviewer_role: str = Field(pattern="^(REVIEWER|ADMIN)$")


@router.patch("/registrations/{asset_code}", dependencies=[Depends(require_admin_key)])
async def review_registration(asset_code: str, request: RegistrationReview, session: AsyncSession = Depends(get_db)):
    asset = await session.scalar(select(Asset).where(Asset.asset_code == asset_code).with_for_update())
    if asset is None:
        raise HTTPException(status_code=404, detail="Registration not found")
    model = await session.scalar(select(AssetModel).where(AssetModel.asset_id == asset.id, AssetModel.is_active.is_(True)))
    meta = dict((model.dimensions or {}).get("_registration", {})) if model else {}
    if not meta:
        raise HTTPException(status_code=404, detail="Registration metadata unavailable")
    if meta.get("created_by") == request.reviewed_by:
        raise HTTPException(status_code=403, detail="You cannot review your own registration")
    if asset.status != "PENDING_REVIEW":
        raise HTTPException(status_code=409, detail="Registration is no longer pending review")
    if not request.comments.strip():
        raise HTTPException(status_code=422, detail="Review comments are required")
    asset.status = "VERIFIED" if request.status == "APPROVED" else "REJECTED"
    asset.identity_status = asset.status
    meta.update(status=asset.status, reviewed_by=request.reviewed_by, reviewed_at=datetime.now(timezone.utc).isoformat(), review_comments=request.comments)
    model.dimensions = {**model.dimensions, "_registration": meta}
    await session.commit()
    return {"asset_code": asset_code, **meta}


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
        Asset.status.notin_(["PENDING_REVIEW", "REJECTED"]),
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
                Asset.asset_code == asset_code,
                Asset.status.notin_(["PENDING_REVIEW", "REJECTED"]),
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
                    AND status NOT IN ('PENDING_REVIEW', 'REJECTED')
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


from app.services.assessment_engine import build_asset_assessment


@router.get("/{asset_code}/assessment")
async def get_asset_assessment(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
):
    return await build_asset_assessment(session, asset_code)
