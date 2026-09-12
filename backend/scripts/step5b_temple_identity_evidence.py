from __future__ import annotations

import os
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

PLAN = (
    ROOT
    / "data"
    / "processed"
    / "temple"
    / "AP_TEMPLE_SOURCE_PLAN.csv"
)

OUT = (
    ROOT
    / "data"
    / "processed"
    / "temple"
    / "AP_TEMPLE_IDENTITY_EVIDENCE.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP5B_TEMPLE_IDENTITY_REPORT.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP5B_TEMPLE_IDENTITY_REPORT.json"
)


# -------------------------------------------------------------------
# Government / official identity evidence already verified.
#
# DO NOT use these records as:
#   - structural inspection labels
#   - health labels
#   - RUL labels
#
# They establish identity, administration and heritage-screening state.
# -------------------------------------------------------------------

VERIFIED = {

    "AP_TEMPLE_KANAKA_DURGA": {

        "canonical_name":
            "Sri Durga Malleswara Swamy Varla Devasthanam",

        "administrative_authority":
            "Andhra Pradesh Endowments Department",

        "primary_source_system":
            "AP Endowments TMS",

        "primary_source_url":
            "https://tms.ap.gov.in/",

        "official_temple_source_url":
            "https://www.kanakadurgamma.org/",

        "official_identity_status":
            "VERIFIED",

        "asi_screening_status":
            "REVIEW_POSSIBLE_ASSOCIATED_ASI_EVIDENCE",

        "asi_screening_note":
            (
                "Current ASI centrally protected list contains "
                "protected records in Vijayawada / Indrakila Hill, "
                "including an inscribed pillar and slab in a "
                "Mallesvarasvami temple. Association with the current "
                "SIMRAS temple asset requires monument-level review."
            ),

        "historical_description":
            (
                "Official temple source describes Kanaka Durga as an "
                "ancient temple on Indrakeeladri hill on the banks "
                "of the Krishna River."
            ),

        "exact_built_year_verified":
            False,
    },


    "AP_TEMPLE_SRIKALAHASTI": {

        "canonical_name":
            "Sri Kalahastheeswara Swamy Vari Devasthanam",

        "administrative_authority":
            "Andhra Pradesh Endowments Department",

        "primary_source_system":
            "AP Endowments TMS",

        "primary_source_url":
            "https://tms.ap.gov.in/",

        "official_temple_source_url":
            "https://www.srikalahasthitemple.org/",

        "official_identity_status":
            "VERIFIED",

        "asi_screening_status":
            "NO_EXACT_NAME_MATCH_IN_CURRENT_CPM_LIST",

        "asi_screening_note":
            (
                "No exact Srikalahasti/Kalahasti temple-name match "
                "was found in the current ASI centrally protected "
                "monuments list. This does not prove absence of all "
                "heritage protections."
            ),

        "historical_description":
            (
                "Official temple source describes it as an ancient "
                "historical Saivite temple adjoining a hill and "
                "situated on the banks of the Swarnamukhi River."
            ),

        "exact_built_year_verified":
            False,
    },


    "AP_TEMPLE_SRISAILAM": {

        "canonical_name":
            "Sri Bhramaramba Mallikarjuna Swamy Varla Devasthanam",

        "administrative_authority":
            "Andhra Pradesh Endowments Department",

        "primary_source_system":
            "AP Endowments TMS",

        "primary_source_url":
            "https://tms.ap.gov.in/",

        "official_temple_source_url":
            "https://www.srisailadevasthanam.org/en-in/home",

        "official_identity_status":
            "VERIFIED",

        "asi_screening_status":
            "NO_EXACT_NAME_MATCH_IN_CURRENT_CPM_LIST",

        "asi_screening_note":
            (
                "No exact Srisailam temple-name match was found "
                "in the current ASI centrally protected monuments list."
            ),

        "historical_description":
            (
                "Official Devasthanam source describes Srisailam as "
                "very ancient and explicitly states that no historical "
                "evidence establishes an exact origin date."
            ),

        "exact_built_year_verified":
            False,
    },


    "AP_TEMPLE_SIMHACHALAM": {

        "canonical_name":
            "Sri Varaha Lakshmi Narasimha Swamy Vari Devasthanam",

        "administrative_authority":
            "Andhra Pradesh Endowments Department",

        "primary_source_system":
            "AP Endowments TMS",

        "primary_source_url":
            "https://tms.ap.gov.in/",

        "official_temple_source_url":
            "https://svlnsd.com/",

        "official_identity_status":
            "VERIFIED",

        "asi_screening_status":
            "NO_EXACT_NAME_MATCH_IN_CURRENT_CPM_LIST",

        "asi_screening_note":
            (
                "No exact Simhachalam temple-name match was found "
                "in the current ASI centrally protected monuments list."
            ),

        "historical_description":
            (
                "Government Endowments evidence identifies the "
                "Simhachalam Devasthanam. Exact construction year "
                "is not being inferred."
            ),

        "exact_built_year_verified":
            False,
    },


    "AP_TEMPLE_ANNAVARAM": {

        "canonical_name":
            "Sri Veera Venkata Satyanarayana Swamy Vari Devasthanam",

        "administrative_authority":
            "Andhra Pradesh Endowments Department",

        "primary_source_system":
            "AP Endowments TMS / NIC Devasthanam Portal",

        "primary_source_url":
            "https://annavaramdevasthanam.nic.in/Home/Index",

        "official_temple_source_url":
            "https://annavaramdevasthanam.nic.in/Home/Index",

        "official_identity_status":
            "VERIFIED",

        "asi_screening_status":
            "NO_EXACT_NAME_MATCH_IN_CURRENT_CPM_LIST",

        "asi_screening_note":
            (
                "No exact Annavaram temple-name match was found "
                "in the current ASI centrally protected monuments list."
            ),

        "historical_description":
            (
                "NIC-hosted Devasthanam portal verifies the temple "
                "identity at Annavaram/Ratnagiri. Exact structural "
                "construction year is not being assumed."
            ),

        "exact_built_year_verified":
            False,
    },


    "AP_TEMPLE_DWARAKA_TIRUMALA": {

        "canonical_name":
            "Sri Venkateswara Swamy Vari Devasthanam, Dwaraka Tirumala",

        "administrative_authority":
            "Andhra Pradesh Endowments Department",

        "primary_source_system":
            "AP Endowments TMS",

        "primary_source_url":
            "https://tms.ap.gov.in/",

        "official_temple_source_url":
            "https://www.dwarakatirumaladevasthanam.org/",

        "official_identity_status":
            "VERIFIED",

        "asi_screening_status":
            "NO_EXACT_NAME_MATCH_IN_CURRENT_CPM_LIST",

        "asi_screening_note":
            (
                "No exact Dwaraka Tirumala temple-name match was found "
                "in the current ASI centrally protected monuments list."
            ),

        "historical_description":
            (
                "AP Endowments and official temple sources verify "
                "Sri Venkateswara Swamy Vari Devasthanam at "
                "Dwaraka Tirumala."
            ),

        "exact_built_year_verified":
            False,
    },


    "AP_TEMPLE_TIRUMALA": {

        "canonical_name":
            "Sri Venkateswara Swamy Temple, Tirumala",

        "administrative_authority":
            "Tirumala Tirupati Devasthanams",

        "primary_source_system":
            "TTD Official",

        "primary_source_url":
            "https://www.tirumala.org/",

        "official_temple_source_url":
            "https://www.tirumala.org/",

        "official_identity_status":
            "VERIFIED",

        "asi_screening_status":
            "NO_EXACT_NAME_MATCH_IN_CURRENT_CPM_LIST",

        "asi_screening_note":
            (
                "No exact Tirumala/Tirupati main temple-name match "
                "was found in the current ASI centrally protected "
                "monuments list."
            ),

        "historical_description":
            (
                "TTD official sources verify Sri Venkateswara "
                "Swamy Temple at Tirumala. No single construction "
                "year is being inferred for the present temple complex."
            ),

        "exact_built_year_verified":
            False,
    },
}


ASI_SOURCE = (
    "https://asi.nic.in/pdf/CPM_List.pdf"
)


async def main():

    if not PLAN.exists():
        raise RuntimeError(
            "Step 5A temple source plan not found."
        )

    plan = pd.read_csv(
        PLAN,
        low_memory=False
    )

    rows = []

    for _, asset in plan.iterrows():

        code = str(
            asset["asset_code"]
        ).strip()

        verified = VERIFIED.get(
            code
        )

        if not verified:
            raise RuntimeError(
                f"No verified Step 5B mapping for {code}"
            )

        rows.append({

            "asset_id":
                int(asset["asset_id"]),

            "asset_code":
                code,

            "asset_name":
                asset["asset_name"],

            "district":
                asset.get("district"),

            **verified,

            "asi_source":
                ASI_SOURCE,

            "verification_method":
                "WEB_VERIFIED_OFFICIAL_GOVERNMENT_SOURCE",

            "authority_level":
                "A1_PRIMARY_GOVERNMENT_OR_OFFICIAL_AUTHORITY",

            "is_official_identity":
                True,

            "is_structural_condition_evidence":
                False,

            "is_health_label":
                False,

            "is_risk_label":
                False,

            "is_rul_label":
                False,

            "evidence_confidence":
                0.98,

            "feature_version":
                "ap_temple_identity_v1",

            "verified_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),
        })

    df = pd.DataFrame(
        rows
    )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUT,
        index=False
    )

    # ----------------------------------------------------------
    # DATABASE
    # ----------------------------------------------------------

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
                public.temple_identity_evidence_verified
                (
                    asset_id BIGINT PRIMARY KEY,

                    asset_code TEXT NOT NULL,
                    asset_name TEXT NOT NULL,
                    district TEXT,

                    canonical_name TEXT NOT NULL,

                    administrative_authority TEXT NOT NULL,

                    primary_source_system TEXT,
                    primary_source_url TEXT,

                    official_temple_source_url TEXT,

                    official_identity_status TEXT NOT NULL,

                    asi_screening_status TEXT,
                    asi_screening_note TEXT,
                    asi_source TEXT,

                    historical_description TEXT,

                    exact_built_year_verified BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    verification_method TEXT,
                    authority_level TEXT,

                    is_official_identity BOOLEAN
                        NOT NULL DEFAULT TRUE,

                    is_structural_condition_evidence BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_health_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_risk_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_rul_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    evidence_confidence
                        DOUBLE PRECISION,

                    feature_version TEXT,

                    verified_at TIMESTAMPTZ,

                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.temple_identity_evidence_verified
            """)
        )

        insert = text("""
            INSERT INTO
            public.temple_identity_evidence_verified
            (
                asset_id,
                asset_code,
                asset_name,
                district,

                canonical_name,

                administrative_authority,

                primary_source_system,
                primary_source_url,

                official_temple_source_url,

                official_identity_status,

                asi_screening_status,
                asi_screening_note,
                asi_source,

                historical_description,

                exact_built_year_verified,

                verification_method,
                authority_level,

                is_official_identity,

                is_structural_condition_evidence,
                is_health_label,
                is_risk_label,
                is_rul_label,

                evidence_confidence,

                feature_version,

                verified_at
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,
                :district,

                :canonical_name,

                :administrative_authority,

                :primary_source_system,
                :primary_source_url,

                :official_temple_source_url,

                :official_identity_status,

                :asi_screening_status,
                :asi_screening_note,
                :asi_source,

                :historical_description,

                :exact_built_year_verified,

                :verification_method,
                :authority_level,

                :is_official_identity,

                :is_structural_condition_evidence,
                :is_health_label,
                :is_risk_label,
                :is_rul_label,

                :evidence_confidence,

                :feature_version,

                CAST(:verified_at AS TIMESTAMPTZ)
            )
        """)

        for row in rows:

            # asyncpg is strict with native TIMESTAMP types.
            # Send verified_at as a real Python datetime.
            db_row = dict(row)

            db_row["verified_at"] = datetime.fromisoformat(
                db_row["verified_at"]
            )

            await conn.execute(
                insert,
                db_row
            )

        verification = await conn.execute(
            text("""
                SELECT
                    COUNT(*) AS total,
                    COUNT(*) FILTER (
                        WHERE official_identity_status='VERIFIED'
                    ) AS verified,

                    COUNT(*) FILTER (
                        WHERE asi_screening_status=
                        'REVIEW_POSSIBLE_ASSOCIATED_ASI_EVIDENCE'
                    ) AS asi_review,

                    COUNT(*) FILTER (
                        WHERE asi_screening_status=
                        'NO_EXACT_NAME_MATCH_IN_CURRENT_CPM_LIST'
                    ) AS asi_no_exact

                FROM
                    public.temple_identity_evidence_verified
            """)
        )

        result = dict(
            verification.mappings().one()
        )

    await engine.dispose()

    # ----------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------

    lines = [
        "=" * 105,
        "SIMRAS STEP 5B - TEMPLE IDENTITY EVIDENCE RESULT",
        "=" * 105,
        "",
        f"Temple assets                    : {result['total']}",
        f"Official identities verified     : {result['verified']}",
        f"ASI association review required  : {result['asi_review']}",
        f"ASI no-exact-name screening      : {result['asi_no_exact']}",
        "",
    ]

    for row in rows:

        lines.append(
            f"{row['asset_code']} | "
            f"{row['official_identity_status']} | "
            f"{row['administrative_authority']} | "
            f"{row['asi_screening_status']}"
        )

    lines += [
        "",
        "Database table:",
        " public.temple_identity_evidence_verified",
        "",
        "Feature version:",
        " ap_temple_identity_v1",
        "",
        "IMPORTANT:",
        " Identity/history evidence is NOT structural-condition evidence.",
        " No Health Score, structural Risk Score or RUL is created here.",
        "=" * 105,
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

                "summary":
                    result,

                "records":
                    rows,
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
