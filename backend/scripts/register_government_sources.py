from __future__ import annotations

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import asyncio

from sqlalchemy import select

from app.db.session import get_db
from app.models.entities import DataSource


SOURCES = [
    {
        "code": "APSAC_APSSDI",
        "name": "Andhra Pradesh State Spatial Data Infrastructure",
        "organisation": "Andhra Pradesh Space Applications Centre",
        "url": "https://apsac.ap.gov.in/geoserver/",
        "licence": "Government public geospatial service; preserve source metadata and terms",
        "source_type": "GOVERNMENT_GIS",
        "refresh_policy": "Monthly verification",
        "is_authoritative": True,
    },
    {
        "code": "NWDP_AP_SW",
        "name": "Andhra Pradesh Surface Water - National Water Data Portal",
        "organisation": "NWIC / Andhra Pradesh Surface Water Department",
        "url": "https://www.nwdp.nwic.gov.in/",
        "licence": "Government portal; preserve dataset-specific metadata and terms",
        "source_type": "GOVERNMENT_TELEMETRY",
        "refresh_policy": "According to source publication cadence",
        "is_authoritative": True,
    },
    {
        "code": "CWC_NDSA",
        "name": "Central Water Commission / National Dam Safety Authority",
        "organisation": "Ministry of Jal Shakti, Government of India",
        "url": "https://damsafety.cwc.gov.in/",
        "licence": "Government published records; retain document provenance",
        "source_type": "GOVERNMENT_SAFETY",
        "refresh_policy": "On publication or inspection update",
        "is_authoritative": True,
    },
    {
        "code": "INDIAN_RAILWAYS_SCR",
        "name": "Indian Railways / South Central Railway",
        "organisation": "Ministry of Railways, Government of India",
        "url": "https://scr.indianrailways.gov.in/",
        "licence": "Government published records; retain report provenance",
        "source_type": "GOVERNMENT_INSPECTION",
        "refresh_policy": "On inspection, audit or maintenance publication",
        "is_authoritative": True,
    },
    {
        "code": "PMGSY_OMMAS",
        "name": "PMGSY OMMAS Quality Monitoring",
        "organisation": "Ministry of Rural Development, Government of India",
        "url": "https://pmgsy.dord.gov.in/",
        "licence": "Government public information; retain report provenance",
        "source_type": "GOVERNMENT_ROAD_QUALITY",
        "refresh_policy": "On quality-monitoring update",
        "is_authoritative": True,
    },
]


async def main() -> None:
    async for session in get_db():
        for source_data in SOURCES:
            existing = await session.scalar(
                select(DataSource).where(
                    DataSource.code == source_data["code"]
                )
            )

            if existing is None:
                existing = DataSource(
                    code=source_data["code"],
                    name=source_data["name"],
                    organisation=source_data["organisation"],
                    source_type=source_data["source_type"],
                    refresh_policy=source_data["refresh_policy"],
                    is_authoritative=source_data["is_authoritative"],
                )
                session.add(existing)

            # Set optional fields only if they exist in the current model.
            for optional_field in ("url", "licence"):
                if hasattr(existing, optional_field):
                    setattr(
                        existing,
                        optional_field,
                        source_data[optional_field],
                    )

            print(
                f"{source_data['code']}: "
                f"{source_data['organisation']}"
            )

        await session.commit()
        break


if __name__ == "__main__":
    asyncio.run(main())

