from __future__ import annotations

import asyncio

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.entities import Asset, DataSource


AIRPORTS = [
    {
        "code": "AP_AIR_AAI_VIJAYAWADA",
        "search": "vijayawada",
        "name": "Vijayawada Airport",
        "district": "Krishna",
        "owner": "Airports Authority of India",
        "lat": 16.5304,
        "lon": 80.7968,
    },
    {
        "code": "AP_AIR_AAI_VISAKHAPATNAM",
        "search": "visakhapatnam",
        "name": "Visakhapatnam Airport",
        "district": "Visakhapatnam",
        "owner": "Indian Navy / Airports Authority of India Civil Enclave",
        "lat": 17.7212,
        "lon": 83.2245,
    },
    {
        "code": "AP_AIR_AAI_RAJAHMUNDRY",
        "search": "rajahmundry",
        "name": "Rajahmundry Airport",
        "district": "East Godavari",
        "owner": "Airports Authority of India",
        "lat": 17.1104,
        "lon": 81.8182,
    },
    {
        "code": "AP_AIR_AAI_TIRUPATI",
        "search": "tirupati airport",
        "name": "Tirupati Airport",
        "district": "Tirupati",
        "owner": "Airports Authority of India",
        "lat": 13.6325,
        "lon": 79.5433,
    },
    {
        "code": "AP_AIR_AAI_KADAPA",
        "search": "kadapa airport",
        "name": "Kadapa Airport",
        "district": "YSR Kadapa",
        "owner": "Airports Authority of India",
        "lat": 14.5101,
        "lon": 78.7728,
    },
    {
        "code": "AP_AIR_AAI_KURNOOL",
        "search": "kurnool airport",
        "name": "Kurnool Airport",
        "district": "Kurnool",
        "owner": "Government of Andhra Pradesh",
        "lat": 15.7163,
        "lon": 78.1692,
    },
]


TEMPLES = [
    {
        "code": "AP_TEMPLE_TIRUMALA",
        "search": "venkateswara swamy temple, tirumala",
        "name": "Sri Venkateswara Swamy Temple, Tirumala",
        "district": "Tirupati",
        "owner": "Tirumala Tirupati Devasthanams",
        "lat": 13.6831,
        "lon": 79.3469,
    },
    {
        "code": "AP_TEMPLE_SRISAILAM",
        "search": "mallikarjuna swamy temple",
        "name": "Sri Mallikarjuna Swamy Temple, Srisailam",
        "district": "Nandyal",
        "owner": "Srisaila Devasthanam",
        "lat": 16.0833,
        "lon": 78.8667,
    },
    {
        "code": "AP_TEMPLE_KANAKA_DURGA",
        "search": "durga malleswara",
        "name": "Sri Durga Malleswara Swamy Varla Devasthanam",
        "district": "NTR",
        "owner": "Sri Durga Malleswara Swamy Varla Devasthanam",
        "lat": 16.5154,
        "lon": 80.6059,
    },
    {
        "code": "AP_TEMPLE_SIMHACHALAM",
        "search": "simhachalam",
        "name": "Sri Varaha Lakshmi Narasimha Temple, Simhachalam",
        "district": "Visakhapatnam",
        "owner": "Simhachalam Devasthanam",
        "lat": 17.7664,
        "lon": 83.2505,
    },
    {
        "code": "AP_TEMPLE_ANNAVARAM",
        "search": "annavaram",
        "name": "Sri Veera Venkata Satyanarayana Swamy Temple, Annavaram",
        "district": "Kakinada",
        "owner": "Annavaram Devasthanam",
        "lat": 17.2825,
        "lon": 82.4042,
    },
    {
        "code": "AP_TEMPLE_SRIKALAHASTI",
        "search": "kalahasti",
        "name": "Sri Kalahasteeswara Swamy Temple",
        "district": "Tirupati",
        "owner": "Sri Kalahasteeswara Swamy Vari Devasthanam",
        "lat": 13.7502,
        "lon": 79.7002,
    },
    {
        "code": "AP_TEMPLE_DWARAKA_TIRUMALA",
        "search": "dwaraka tirumala",
        "name": "Sri Venkateswara Swamy Temple, Dwaraka Tirumala",
        "district": "Eluru",
        "owner": "Dwaraka Tirumala Devasthanam",
        "lat": 16.9545,
        "lon": 81.2566,
    },
]


async def source(
    session,
    *,
    code: str,
    name: str,
    organisation: str,
    url: str,
) -> DataSource:
    existing = await session.scalar(
        select(DataSource).where(DataSource.code == code)
    )

    if existing:
        existing.name = name
        existing.organisation = organisation
        existing.source_type = "GOVERNMENT_REGISTRY"
        existing.url = url
        existing.is_authoritative = True
        return existing

    row = DataSource(
        code=code,
        name=name,
        organisation=organisation,
        source_type="GOVERNMENT_REGISTRY",
        url=url,
        licence="Public government information",
        refresh_policy="MANUAL_VERIFIED",
        is_authoritative=True,
    )

    session.add(row)
    await session.flush()
    return row


async def find_existing(session, search_text: str) -> Asset | None:
    return await session.scalar(
        select(Asset)
        .where(func.lower(Asset.name).contains(search_text.lower()))
        .order_by(Asset.id)
        .limit(1)
    )


async def upsert_asset(
    session,
    *,
    record: dict,
    asset_type: str,
    subtype: str,
    source_row: DataSource,
) -> tuple[str, str]:
    existing = await find_existing(session, record["search"])

    if existing is None:
        existing = await session.scalar(
            select(Asset).where(Asset.asset_code == record["code"])
        )

    geom = WKTElement(
        f"POINT({record['lon']} {record['lat']})",
        srid=4326,
    )

    if existing:
        existing.asset_type = asset_type
        existing.subtype = subtype
        existing.district = record["district"]
        existing.owner = record["owner"]
        existing.status = "ACTIVE"
        existing.identity_status = "VERIFIED"
        existing.source_id = source_row.id
        existing.confidence_score = 0.95
        existing.is_estimated = False

        if existing.representative_geometry is None:
            existing.representative_geometry = geom

        return "updated", existing.asset_code

    asset = Asset(
        asset_code=record["code"],
        name=record["name"],
        asset_type=asset_type,
        subtype=subtype,
        district=record["district"],
        owner=record["owner"],
        status="ACTIVE",
        identity_status="VERIFIED",
        representative_geometry=geom,
        source_id=source_row.id,
        confidence_score=0.95,
        is_estimated=False,
    )

    session.add(asset)
    await session.flush()
    return "inserted", asset.asset_code


async def main() -> None:
    async with SessionLocal() as session:
        aai = await source(
            session,
            code="AAI_OPERATIONAL_AP_2026",
            name="Operational Airports in Andhra Pradesh",
            organisation="Airports Authority of India",
            url=(
                "https://www.aai.aero/sites/default/files/rtidir/"
                "RTI%20Reply%20-%20Offline%20-%20Sanjay%20Jayakumar%20Patravali.pdf"
            ),
        )

        tourism = await source(
            session,
            code="AP_TOURISM_TEMPLES",
            name="Andhra Pradesh Temples and Pilgrimage References",
            organisation="Andhra Pradesh Tourism Development Corporation",
            url=(
                "https://tourism.ap.gov.in/assets/img/Brochures/"
                "AP%20Temples%20Brochure.pdf"
            ),
        )

        counts = {
            "airport_inserted": 0,
            "airport_updated": 0,
            "temple_inserted": 0,
            "temple_updated": 0,
        }

        for record in AIRPORTS:
            action, code = await upsert_asset(
                session,
                record=record,
                asset_type="airport",
                subtype="airport",
                source_row=aai,
            )
            counts[f"airport_{action}"] += 1
            print("AIRPORT", action.upper(), code, record["name"])

        for record in TEMPLES:
            action, code = await upsert_asset(
                session,
                record=record,
                asset_type="temple",
                subtype="heritage_temple",
                source_row=tourism,
            )
            counts[f"temple_{action}"] += 1
            print("TEMPLE", action.upper(), code, record["name"])

        await session.commit()

        print("=" * 72)
        print("AIRPORT/TEMPLE REGISTRY UPDATE COMPLETE")
        for key, value in counts.items():
            print(f"{key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())