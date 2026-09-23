import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(prefix="/map", tags=["map"])


def parse_bbox(value: str | None) -> tuple[float, float, float, float] | None:
    if value is None:
        return None

    try:
        parts = tuple(float(part.strip()) for part in value.split(","))
    except ValueError as exc:
        raise ValueError("bbox must contain four numeric values") from exc

    if len(parts) != 4:
        raise ValueError("bbox must use min_lon,min_lat,max_lon,max_lat")

    min_lon, min_lat, max_lon, max_lat = parts

    if not (-180 <= min_lon < max_lon <= 180):
        raise ValueError("bbox longitude range is invalid")
    if not (-90 <= min_lat < max_lat <= 90):
        raise ValueError("bbox latitude range is invalid")

    return min_lon, min_lat, max_lon, max_lat


@router.get("/summary")
async def map_summary(
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    rows = (
        await session.execute(
            text(
                """
                SELECT feature_type, subtype, count(*) AS records
                FROM map_features
                GROUP BY feature_type, subtype
                ORDER BY feature_type, subtype
                """
            )
        )
    ).mappings().all()

    return {"items": [dict(row) for row in rows]}


@router.get("/features")
async def list_map_features(
    feature_type: str | None = Query(default=None, max_length=30),
    subtype: str | None = Query(default=None, max_length=80),
    search: str | None = Query(default=None, max_length=100),
    bbox: str | None = Query(
        default=None,
        description="min_lon,min_lat,max_lon,max_lat",
    ),
    limit: int = Query(default=500, ge=1, le=5000),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    try:
        bbox_values = parse_bbox(bbox)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}

    if feature_type:
        conditions.append("mf.feature_type = :feature_type")
        params["feature_type"] = feature_type

    if subtype:
        conditions.append("mf.subtype = :subtype")
        params["subtype"] = subtype

    if search:
        conditions.append("COALESCE(mf.name, '') ILIKE :search")
        params["search"] = f"%{search}%"

    if bbox_values:
        min_lon, min_lat, max_lon, max_lat = bbox_values
        conditions.append(
            "ST_Intersects("
            "mf.geometry, "
            "ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)"
            ")"
        )
        params.update(
            {
                "min_lon": min_lon,
                "min_lat": min_lat,
                "max_lon": max_lon,
                "max_lat": max_lat,
            }
        )

    where_clause = (
        "WHERE " + " AND ".join(conditions)
        if conditions
        else ""
    )

    total = await session.scalar(
        text(f"SELECT count(*) FROM map_features mf {where_clause}"),
        params,
    )

    rows = (
        await session.execute(
            text(
                f"""
                SELECT
                    mf.id,
                    mf.external_id,
                    mf.name,
                    mf.feature_type,
                    mf.subtype,
                    mf.attributes,
                    mf.identity_status,
                    mf.confidence_score,
                    mf.retrieved_at,
                    ds.code AS source_code,
                    ds.name AS source_name,
                    ds.url AS source_url,
                    ds.licence,
                    ST_AsGeoJSON(mf.geometry)::jsonb AS geometry
                FROM map_features mf
                JOIN data_sources ds ON ds.id = mf.source_id
                {where_clause}
                ORDER BY mf.feature_type, COALESCE(mf.name, mf.external_id)
                LIMIT :limit OFFSET :offset
                """
            ),
            params,
        )
    ).mappings().all()

    features = []
    for row in rows:
        geometry = row["geometry"]
        if isinstance(geometry, str):
            geometry = json.loads(geometry)

        features.append(
            {
                "type": "Feature",
                "id": row["id"],
                "geometry": geometry,
                "properties": {
                    "external_id": row["external_id"],
                    "name": row["name"],
                    "feature_type": row["feature_type"],
                    "subtype": row["subtype"],
                    "attributes": row["attributes"] or {},
                    "identity_status": row["identity_status"],
                    "confidence_score": row["confidence_score"],
                    "retrieved_at": row["retrieved_at"],
                    "source_code": row["source_code"],
                    "source_name": row["source_name"],
                    "source_url": row["source_url"],
                    "licence": row["licence"],
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
        "total": total or 0,
        "limit": limit,
        "offset": offset,
    }