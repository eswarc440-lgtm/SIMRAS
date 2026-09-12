from __future__ import annotations

import os
import csv
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

OUT = (
    ROOT
    / "data"
    / "processed"
    / "airport"
    / "AP_AIRPORT_MAINTENANCE_EVIDENCE_VERIFIED.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP4C1_AIRPORT_MAINTENANCE_RECOVERY.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP4C1_AIRPORT_MAINTENANCE_RECOVERY.json"
)


# ------------------------------------------------------------------
# IMPORTANT
#
# These are procurement / maintenance-plan records verified against
# official AAI / APADCL public sources.
#
# They are NOT pavement condition surveys.
# They are NOT PCI values.
# They are NOT proof that the work was completed.
# ------------------------------------------------------------------

records = [

    {
        "icao_code": "VOBZ",
        "canonical_airport": "Vijayawada Airport",
        "event_title":
            "Resurfacing of damaged portion of Runway between "
            "chainage 2286m and 2610m at Vijayawada Airport",
        "evidence_category": "RUNWAY_REHABILITATION",
        "maintenance_significance": "HIGH",
        "record_date": "2025-09-22",
        "estimated_cost_inr": 3539537,
        "procurement_id": "2025_AAI_248371_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI Tender in Progress September 2025; "
            "Tender 2025_AAI_248371_1",
    },

    {
        "icao_code": "VOBZ",
        "canonical_airport": "Vijayawada Airport",
        "event_title":
            "Annual Painting contract for Runway, Taxiways and "
            "Apron Markings at Vijayawada Airport during 2025-26",
        "evidence_category": "RUNWAY_MARKING_MAINTENANCE",
        "maintenance_significance": "MEDIUM",
        "record_date": "2025-08-23",
        "estimated_cost_inr": 5527963,
        "procurement_id": "2025_AAI_243502_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI Tender in Progress August 2025; "
            "Tender 2025_AAI_243502_1",
    },

    {
        "icao_code": "VOCP",
        "canonical_airport": "Kadapa Airport",
        "event_title":
            "A/R & M/O Civil works 2026-27 - "
            "Maintenance works for Operational Area at Kadapa Airport",
        "evidence_category": "OPERATIONAL_AREA_MAINTENANCE",
        "maintenance_significance": "MEDIUM",
        "record_date": "2026-03-05",
        "estimated_cost_inr": 7000000,
        "procurement_id": "2026_AAI_267028_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI March 2026 procurement; "
            "Tender 2026_AAI_267028_1",
    },

    {
        "icao_code": "VOCP",
        "canonical_airport": "Kadapa Airport",
        "event_title":
            "Mechanized re-painting of Runway, Taxi Track, "
            "Isolation Bay and Apron Markings at Kadapa Airport",
        "evidence_category": "RUNWAY_MARKING_MAINTENANCE",
        "maintenance_significance": "MEDIUM",
        "record_date": "2025-06-04",
        "estimated_cost_inr": 3309215,
        "procurement_id": "2025_AAI_229279_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI Tender record; Tender 2025_AAI_229279_1",
    },

    {
        "icao_code": "VOKU",
        "canonical_airport": "Kurnool Airport",
        "event_title":
            "Runway End Safety Area at Kurnool Airport "
            "and Other Maintenance Works",
        "evidence_category": "RUNWAY_SAFETY_AREA_MAINTENANCE",
        "maintenance_significance": "HIGH",
        "record_date": "2025-04-29",
        "estimated_cost_inr": None,
        "procurement_id":
            "NIT No.3/APADCL/Kurnool Airport/2025-26",
        "source_authority":
            "Andhra Pradesh Airports Development Corporation Limited",
        "source_system": "APADCL Tender Portal",
        "source_locator":
            "APADCL Kurnool Airport tender register; "
            "NIT No.3/APADCL/Kurnool Airport/2025-26",
    },

    {
        "icao_code": "VORY",
        "canonical_airport": "Rajahmundry Airport",
        "event_title":
            "Rejuvenation of damaged runway surfaces by applying "
            "Polymer Modified Emulsion Rejuvenator - Phase III",
        "evidence_category": "RUNWAY_REHABILITATION",
        "maintenance_significance": "HIGH",
        "record_date": "2026-05-07",
        "estimated_cost_inr": None,
        "procurement_id": "2026_AAI_276499_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI Rajahmundry tender; 2026_AAI_276499_1",
    },

    {
        "icao_code": "VORY",
        "canonical_airport": "Rajahmundry Airport",
        "event_title":
            "Annual Rate Contract for Runway and Apron Marking "
            "including retro-reflective painting of Taxiways "
            "and Apron during 2026-27",
        "evidence_category": "RUNWAY_MARKING_MAINTENANCE",
        "maintenance_significance": "MEDIUM",
        "record_date": "2026-05-14",
        "estimated_cost_inr": None,
        "procurement_id": "2026_AAI_276905_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI Rajahmundry tender; 2026_AAI_276905_1",
    },

    {
        "icao_code": "VOTP",
        "canonical_airport": "Tirupati Airport",
        "event_title":
            "A/R & M/O Civil works 2026-27 - "
            "Annual Maintenance Contract for Operational Area "
            "at Tirupati Airport",
        "evidence_category": "OPERATIONAL_AREA_MAINTENANCE",
        "maintenance_significance": "MEDIUM",
        "record_date": "2026-02-06",
        "estimated_cost_inr": 12500000,
        "procurement_id": "2026_AAI_265739_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI February 2026 procurement; "
            "Tender 2026_AAI_265739_1",
    },

    {
        "icao_code": "VOVZ",
        "canonical_airport": "Visakhapatnam Airport",
        "event_title":
            "Special repairs to Terminal Building, Cargo Building, "
            "Apron Joint Filling and other miscellaneous works "
            "at Visakhapatnam Airport",
        "evidence_category": "APRON_REPAIR",
        "maintenance_significance": "MEDIUM",
        "record_date": "2024-12-06",
        "estimated_cost_inr": 12216040,
        "procurement_id": "2024_AAI_216384_1",
        "source_authority": "Airports Authority of India",
        "source_system": "AAI / CPP Procurement",
        "source_locator":
            "AAI Visakhapatnam Engineering tender; "
            "2024_AAI_216384_1",
    },
]


for r in records:

    r["verification_method"] = (
        "WEB_VERIFIED_PRIMARY_GOVERNMENT_SOURCE"
    )

    r["local_fetch_status"] = (
        "DNS_BLOCKED_ON_SIMRAS_HOST"
    )

    r["work_completion_confirmed"] = False

    r["is_structural_condition_label"] = False

    r["is_pavement_condition_label"] = False

    r["is_maintenance_procurement_evidence"] = True


OUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

with OUT.open(
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(
        f,
        fieldnames=records[0].keys()
    )

    writer.writeheader()
    writer.writerows(records)


async def main():

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not db_url:
        raise RuntimeError(
            "DATABASE_URL unavailable"
        )

    if db_url.startswith(
        "postgresql://"
    ):

        db_url = db_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    engine = create_async_engine(
        db_url,
        pool_pre_ping=True
    )

    async with engine.begin() as conn:

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.airport_maintenance_evidence_verified
                (
                    id BIGSERIAL PRIMARY KEY,

                    icao_code TEXT NOT NULL,
                    canonical_airport TEXT NOT NULL,

                    event_title TEXT NOT NULL,
                    evidence_category TEXT NOT NULL,
                    maintenance_significance TEXT,

                    record_date DATE,

                    estimated_cost_inr
                        DOUBLE PRECISION,

                    procurement_id TEXT,

                    source_authority TEXT NOT NULL,
                    source_system TEXT,
                    source_locator TEXT,

                    verification_method TEXT,

                    local_fetch_status TEXT,

                    work_completion_confirmed
                        BOOLEAN NOT NULL DEFAULT FALSE,

                    is_structural_condition_label
                        BOOLEAN NOT NULL DEFAULT FALSE,

                    is_pavement_condition_label
                        BOOLEAN NOT NULL DEFAULT FALSE,

                    is_maintenance_procurement_evidence
                        BOOLEAN NOT NULL DEFAULT TRUE,

                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.airport_maintenance_evidence_verified
                RESTART IDENTITY
            """)
        )

        insert = text("""
            INSERT INTO
            public.airport_maintenance_evidence_verified
            (
                icao_code,
                canonical_airport,
                event_title,
                evidence_category,
                maintenance_significance,
                record_date,
                estimated_cost_inr,
                procurement_id,
                source_authority,
                source_system,
                source_locator,
                verification_method,
                local_fetch_status,
                work_completion_confirmed,
                is_structural_condition_label,
                is_pavement_condition_label,
                is_maintenance_procurement_evidence
            )
            VALUES
            (
                :icao_code,
                :canonical_airport,
                :event_title,
                :evidence_category,
                :maintenance_significance,
                CAST(:record_date AS DATE),
                :estimated_cost_inr,
                :procurement_id,
                :source_authority,
                :source_system,
                :source_locator,
                :verification_method,
                :local_fetch_status,
                :work_completion_confirmed,
                :is_structural_condition_label,
                :is_pavement_condition_label,
                :is_maintenance_procurement_evidence
            )
        """)

        for record in records:

            db_record = dict(record)

            if isinstance(
                db_record.get("record_date"),
                str
            ):
                db_record["record_date"] = (
                    datetime.strptime(
                        db_record["record_date"],
                        "%Y-%m-%d"
                    ).date()
                )

            await conn.execute(
                insert,
                db_record
            )

        result = await conn.execute(
            text("""
                SELECT
                    icao_code,
                    COUNT(*) AS event_count,
                    COUNT(*) FILTER (
                        WHERE
                        maintenance_significance='HIGH'
                    ) AS high_count,

                    SUM(
                        COALESCE(
                            estimated_cost_inr,
                            0
                        )
                    ) AS known_cost_inr

                FROM
                    public.airport_maintenance_evidence_verified

                GROUP BY
                    icao_code

                ORDER BY
                    icao_code
            """)
        )

        summary = [
            dict(x)
            for x in result.mappings().all()
        ]

    await engine.dispose()

    airports = {
        r["icao_code"]
        for r in records
    }

    high = sum(
        1
        for r in records
        if r["maintenance_significance"]
        == "HIGH"
    )

    lines = [
        "=" * 100,
        "SIMRAS STEP 4C.1 - VERIFIED AIRPORT MAINTENANCE RECOVERY",
        "=" * 100,
        "",
        f"Unique AP airports covered       : {len(airports)} / 6",
        f"Verified procurement records     : {len(records)}",
        f"High-significance records        : {high}",
        "",
    ]

    for row in summary:

        lines.append(
            f"{row['icao_code']:<6} | "
            f"events={row['event_count']:<2} | "
            f"high={row['high_count']:<2} | "
            f"known_cost=INR {row['known_cost_inr'] or 0:,.0f}"
        )

    lines += [
        "",
        "Database table:",
        " public.airport_maintenance_evidence_verified",
        "",
        "IMPORTANT SEMANTICS:",
        " These rows prove official procurement / maintenance activity.",
        " They do NOT prove that the work was completed.",
        " They are NOT PCI or structural-condition ground truth.",
        "",
        "Local AAI document download status:",
        " DNS_BLOCKED_ON_SIMRAS_HOST",
        "=" * 100,
    ]

    REPORT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "airports_covered":
                    len(airports),

                "records":
                    len(records),

                "high_significance":
                    high,

                "summary":
                    summary,

                "interpretation":
                    "Official procurement evidence, not condition labels."
            },
            indent=2,
            default=str
        ),
        encoding="utf-8"
    )

    print(
        "\n".join(lines)
    )


asyncio.run(main())

