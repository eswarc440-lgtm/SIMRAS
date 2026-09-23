"""Promote source-backed airport and temple records into showcase twins.

This script is idempotent. Airport geometry and runway dimensions come from
AAI eAIP records. The Tirumala temple is promoted only when its OSM landmark
record is already present; TTD-published dimensions are then attached to its
L1 dimension-derived representation.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from geoalchemy2.elements import WKTElement
from sqlalchemy import select, text

from app.db.session import SessionLocal
from app.models.entities import Asset, AssetModel, DataSource


@dataclass(frozen=True)
class AirportProfile:
    asset_code: str
    name: str
    district: str
    latitude: float
    longitude: float
    heading_deg: float
    source_url: str
    dimensions: dict[str, Any]


AIRPORTS = (
    AirportProfile(
        asset_code="AP_AIR_VOBZ",
        name="Vijayawada Airport",
        district="Krishna",
        latitude=16.533611,
        longitude=80.803333,
        heading_deg=77.75,
        source_url=(
            "https://aim-india.aai.aero/eaip-v2-02-2025/"
            "eAIP/IN-AD%202.1VOBZ-en-GB.html"
        ),
        dimensions={
            "icao_code": "VOBZ",
            "runway_designation": "08/26",
            "runway_length_m": 3360,
            "runway_width_m": 45,
            "runway_strip_length_m": 3480,
            "runway_strip_width_m": 280,
            "runway_surface": "asphalt",
            "representation": "dimension_derived_airport_layout",
        },
    ),
    AirportProfile(
        asset_code="AP_AIR_VOTP",
        name="Tirupati Airport",
        district="Tirupati",
        latitude=13.633056,
        longitude=79.541944,
        heading_deg=81.50,
        source_url=(
            "https://aim-india.aai.aero/eaip-v2-07-2024/"
            "eAIP/IN-AD%202.1VOTP-en-GB.html"
        ),
        dimensions={
            "icao_code": "VOTP",
            "runway_designation": "08/26",
            "runway_length_m": 2285,
            "runway_width_m": 45,
            "runway_strip_length_m": 2405,
            "runway_strip_width_m": 150,
            "old_apron_length_m": 159.5,
            "old_apron_width_m": 120,
            "new_apron_length_m": 364,
            "new_apron_width_m": 144.5,
            "runway_surface": "asphalt",
            "representation": "dimension_derived_airport_layout",
        },
    ),
)


async def ensure_source(session, *, code: str, name: str, url: str) -> DataSource:
    source = await session.scalar(select(DataSource).where(DataSource.code == code))
    if source is None:
        source = DataSource(
            code=code,
            name=name,
            organisation=name,
            source_type="OFFICIAL_PUBLISHED_PROFILE",
            url=url,
            licence="Public information; verify reuse terms",
            refresh_policy="Review on source revision",
            is_authoritative=True,
        )
        session.add(source)
        await session.flush()
    return source


async def upsert_model(
    session,
    *,
    asset: Asset,
    source_url: str,
    model_source: str,
    dimensions: dict[str, Any],
    heading_deg: float | None,
) -> None:
    model = await session.scalar(
        select(AssetModel)
        .where(AssetModel.asset_id == asset.id, AssetModel.is_active.is_(True))
        .order_by(AssetModel.id.desc())
        .limit(1)
    )
    if model is None:
        model = AssetModel(asset_id=asset.id)
        session.add(model)

    model.format = "parametric"
    model.version = "stage6_l1"
    model.fidelity_level = "L1"
    model.model_source = model_source
    model.source_url = source_url
    model.dimensions = dimensions
    model.heading_deg = heading_deg
    model.is_asset_specific = True
    model.is_active = True


async def promote_airports(session) -> list[str]:
    source = await ensure_source(
        session,
        code="AAI_EAIP_SHOWCASE",
        name="Airports Authority of India eAIP",
        url="https://aim-india.aai.aero/",
    )
    promoted: list[str] = []

    for profile in AIRPORTS:
        asset = await session.scalar(
            select(Asset).where(Asset.asset_code == profile.asset_code)
        )
        if asset is None:
            asset = Asset(asset_code=profile.asset_code, name=profile.name)
            session.add(asset)

        asset.name = profile.name
        asset.asset_type = "airport"
        asset.subtype = "civil_airport"
        asset.district = profile.district
        asset.owner = "Airports Authority of India"
        asset.status = "ACTIVE"
        asset.identity_status = "VERIFIED"
        asset.representative_geometry = WKTElement(
            f"POINT({profile.longitude} {profile.latitude})",
            srid=4326,
        )
        asset.source_id = source.id
        asset.confidence_score = 0.98
        asset.is_estimated = False
        await session.flush()

        await upsert_model(
            session,
            asset=asset,
            source_url=profile.source_url,
            model_source="AAI eAIP published aerodrome dimensions",
            dimensions=profile.dimensions,
            heading_deg=profile.heading_deg,
        )
        promoted.append(profile.asset_code)

    return promoted


async def promote_tirumala(session) -> str | None:
    location = (
        await session.execute(
            text(
                """
                SELECT
                    mf.source_id,
                    mf.confidence_score,
                    ST_X(ST_PointOnSurface(mf.geometry)) AS longitude,
                    ST_Y(ST_PointOnSurface(mf.geometry)) AS latitude
                FROM map_features mf
                WHERE mf.feature_type = 'temple'
                  AND COALESCE(mf.name, '') ILIKE ANY(
                      ARRAY[
                          '%Venkateswara%Tirumala%',
                          '%Tirumala%Venkateswara%',
                          '%Venkateswara Swamy Vaari%'
                      ]
                  )
                ORDER BY mf.confidence_score DESC NULLS LAST, mf.id
                LIMIT 1
                """
            )
        )
    ).mappings().first()

    if location is None:
        return None

    asset_code = "AP_TEMPLE_TTD_0001"
    asset = await session.scalar(select(Asset).where(Asset.asset_code == asset_code))
    if asset is None:
        asset = Asset(asset_code=asset_code, name="Sri Venkateswara Swamy Temple")
        session.add(asset)

    asset.name = "Sri Venkateswara Swamy Temple, Tirumala"
    asset.asset_type = "temple"
    asset.subtype = "landmark_temple"
    asset.district = "Tirupati"
    asset.owner = "Tirumala Tirupati Devasthanams"
    asset.status = "ACTIVE"
    asset.identity_status = "SOURCE_REPORTED"
    asset.representative_geometry = WKTElement(
        f"POINT({location['longitude']} {location['latitude']})",
        srid=4326,
    )
    asset.source_id = location["source_id"]
    asset.confidence_score = location["confidence_score"] or 0.80
    asset.is_estimated = False
    await session.flush()

    await upsert_model(
        session,
        asset=asset,
        source_url="https://www.tirumala.org/TTDTempleHistory.aspx",
        model_source="TTD published temple profile with OSM landmark location",
        dimensions={
            "complex_area_acres": 16.2,
            "main_entrance_height_ft": 50,
            "gopuram_tiers": 7,
            "representation": "dimension_derived_temple_profile",
        },
        heading_deg=None,
    )
    return asset_code


async def main() -> None:
    async with SessionLocal() as session:
        airports = await promote_airports(session)
        temple = await promote_tirumala(session)
        await session.commit()

    print({
        "airports_promoted": airports,
        "temple_promoted": temple,
        "temple_note": (
            "Promoted from OSM landmark location plus TTD dimensions"
            if temple
            else "Not promoted: load the statewide OSM temple layer first"
        ),
    })


if __name__ == "__main__":
    asyncio.run(main())
