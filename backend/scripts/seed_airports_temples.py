from __future__ import annotations

import asyncio

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.entities import Asset, DataSource


# AAI operational-airport list, as on 16-Jan-2026, identifies these six
# Andhra Pradesh operational airports.
AIRPORTS = [
    ("AP_AIR_AAI_KADAPA", "kadapa airport", "Kadapa Airport", "YSR Kadapa", "Airports Authority of India", 14.5101, 78.7728),
    ("AP_AIR_AAI_KURNOOL", "kurnool airport", "Kurnool Airport", "Kurnool", "Government of Andhra Pradesh", 15.7163, 78.1692),
    ("AP_AIR_AAI_RAJAHMUNDRY", "rajahmundry airport", "Rajahmundry Airport", "East Godavari", "Airports Authority of India", 17.1104, 81.8182),
    ("AP_AIR_AAI_TIRUPATI", "tirupati airport", "Tirupati Airport", "Tirupati", "Airports Authority of India", 13.6325, 79.5433),
    ("AP_AIR_AAI_VIJAYAWADA", "vijayawada airport", "Vijayawada Airport", "Krishna", "Airports Authority of India", 16.5304, 80.7968),
    ("AP_AIR_AAI_VISAKHAPATNAM", "visakhapatnam airport", "Visakhapatnam Airport", "Visakhapatnam", "Indian Navy / Airports Authority of India Civil Enclave", 17.7212, 83.2245),
]

# Famous pilgrimage assets referenced by official AP Tourism materials.
# Coordinates are project-curated representative points; the source verifies
# the place identity, not survey-grade geometry.
TEMPLES = [
    ("AP_TEMPLE_TIRUMALA", "venkateswara swamy temple", "Sri Venkateswara Swamy Temple, Tirumala", "Tirupati", "Tirumala Tirupati Devasthanams", 13.6831, 79.3469),
    ("AP_TEMPLE_SRISAILAM", "mallikarjuna swamy temple", "Sri Mallikarjuna Swamy Temple, Srisailam", "Nandyal", "Srisaila Devasthanam", 16.0833, 78.8667),
    ("AP_TEMPLE_KANAKA_DURGA", "durga malleswara", "Sri Durga Malleswara Swamy Varla Devasthanam", "NTR", "Sri Durga Malleswara Swamy Varla Devasthanam", 16.5154, 80.6059),
    ("AP_TEMPLE_SIMHACHALAM", "simhachalam", "Sri Varaha Lakshmi Narasimha Temple, Simhachalam", "Visakhapatnam", "Simhachalam Devasthanam", 17.7664, 83.2505),
    ("AP_TEMPLE_ANNAVARAM", "annavaram", "Sri Veera Venkata Satyanarayana Swamy Temple, Annavaram", "Kakinada", "Annavaram Devasthanam", 17.2825, 82.4042),
    ("AP_TEMPLE_SRIKALAHASTI", "srikalahasti", "Sri Kalahasteeswara Swamy Temple", "Tirupati", "Sri Kalahasteeswara Swamy Vari Devasthanam", 13.7502, 79.7002),
    ("AP_TEMPLE_DWARAKA_TIRUMALA", "dwaraka tirumala", "Sri Venkateswara Swamy Temple, Dwaraka Tirumala", "Eluru", "Dwaraka Tirumala Devasthanam", 16.9545, 81.2566),
]


async def get_or_create_source(
    session,
    *,
    code: str,
    name: str,
    organisation: str,
    url: str,
) -> DataSource:
    source = await session.scalar(
        select(DataSource).where(DataSource.code == code)
    )

    if source is None:
        source = DataSource(
            code=code,
            name=name,
            organisation=organisation,
            source_type="GOVERNMENT_REFERENCE",
            url=url,
            licence="Public government information",
            refresh_policy="MANUAL_VERIFIED",
            is_authoritative=True,
        )
        session.add(source)
        await session.flush()
    else:
        source.name = name
        source.organisation = organisation
        source.source_type = "GOVERNMENT_REFERENCE"
        source.url = url
        source.is_authoritative = True

    return source


async def find_existing(session, code: str, search_text: str) -> Asset | None:
    by_code = await session.scalar(
        select(Asset).where(Asset.asset_code == code)
    )
    if by_code is not None:
        return by_code

    return await session.scalar(
        select(Asset)
        .where(func.lower(Asset.name).contains(search_text.lower()))
        .order_by(Asset.id)
        .limit(1)
    )


async def upsert(
    session,
    *,
    row: tuple,
    asset_type: str,
    subtype: str,
    source: DataSource,
) -> tuple[str, str]:
    code, search_text, name, district, owner, lat, lon = row
    asset = await find_existing(session, code, search_text)

    geometry = WKTElement(
        f"POINT({lon} {lat})",
        srid=4326,
    )

    if asset is None:
        asset = Asset(
            asset_code=code,
            name=name,
            asset_type=asset_type,
            subtype=subtype,
            district=district,
            owner=owner,
            status="ACTIVE",
            identity_status="VERIFIED",
            representative_geometry=geometry,
            source_id=source.id,
            confidence_score=0.90,
            # Representative points are project-curated, not survey geometry.
            is_estimated=True,
        )
        session.add(asset)
        await session.flush()
        return "INSERTED", asset.asset_code

    asset.asset_type = asset_type
    asset.subtype = subtype
    asset.source_id = source.id
    asset.district = asset.district or district
    asset.owner = asset.owner or owner
    asset.status = asset.status or "ACTIVE"
    asset.identity_status = asset.identity_status or "VERIFIED"
    asset.confidence_score = max(float(asset.confidence_score or 0), 0.90)

    # Preserve any existing geometry/provenance rather than overwriting it.
    if asset.representative_geometry is None:
        asset.representative_geometry = geometry
        asset.is_estimated = True

    return "UPDATED", asset.asset_code


async def main() -> None:
    async with SessionLocal() as session:
        aai = await get_or_create_source(
            session,
            code="AAI_OPERATIONAL_AP_2026",
            name="Operational Airports in Andhra Pradesh - 16 Jan 2026",
            organisation="Airports Authority of India",
            url=(
                "https://www.aai.aero/sites/default/files/rtidir/"
                "RTI%20Reply%20-%20Offline%20-%20Sanjay%20Jayakumar%20Patravali.pdf"
            ),
        )

        tourism = await get_or_create_source(
            session,
            code="AP_TOURISM_TEMPLES",
            name="Andhra Pradesh Temples / Pilgrimage References",
            organisation="Andhra Pradesh Tourism Development Corporation",
            url="https://tourism.ap.gov.in/brochures",
        )

        airport_count = 0
        temple_count = 0

        for row in AIRPORTS:
            action, code = await upsert(
                session,
                row=row,
                asset_type="airport",
                subtype="airport",
                source=aai,
            )
            airport_count += 1
            print("AIRPORT", action, code, row[2])

        for row in TEMPLES:
            action, code = await upsert(
                session,
                row=row,
                asset_type="temple",
                subtype="heritage_temple",
                source=tourism,
            )
            temple_count += 1
            print("TEMPLE", action, code, row[2])

        await session.commit()

        print("=" * 72)
        print("SEEDED_AIRPORTS", airport_count)
        print("SEEDED_TEMPLES", temple_count)


if __name__ == "__main__":
    asyncio.run(main())