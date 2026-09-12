from __future__ import annotations

import os
import csv
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, date

import pandas as pd

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

IDENTITY = (
    ROOT
    / "data"
    / "processed"
    / "temple"
    / "AP_TEMPLE_IDENTITY_EVIDENCE.csv"
)

OUT = (
    ROOT
    / "data"
    / "processed"
    / "temple"
    / "AP_TEMPLE_ENGINEERING_EVIDENCE.csv"
)

FEATURES = (
    ROOT
    / "data"
    / "processed"
    / "temple"
    / "AP_TEMPLE_ENGINEERING_FEATURES.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP5C_TEMPLE_ENGINEERING_REPORT.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP5C_TEMPLE_ENGINEERING_REPORT.json"
)


# ==================================================================
# VERIFIED OFFICIAL-SOURCE EVIDENCE
#
# Important:
# - Historical architecture != present structural condition.
# - Tourism development != rehabilitation of historic core.
# - Procurement/development != proof of completed repair unless
#   source explicitly says completed.
# ==================================================================

EVIDENCE = [

    # --------------------------------------------------------------
    # KANAKA DURGA
    # --------------------------------------------------------------

    {
        "asset_code": "AP_TEMPLE_KANAKA_DURGA",

        "evidence_type":
            "HISTORICAL_ARCHITECTURE_CONTEXT",

        "feature_name":
            "historic_hill_temple_context",

        "text_value":
            "Ancient temple complex situated on Indrakeeladri hill.",

        "numeric_value": None,
        "unit": None,

        "event_year": None,

        "material":
            None,

        "component":
            "TEMPLE_COMPLEX",

        "evidence_strength":
            "MODERATE",

        "engineering_use":
            "CONTEXT_ONLY",

        "source_authority":
            "Sri Durga Malleswara Swamy Varla Devasthanam",

        "source_system":
            "Official Devasthanam",

        "source_url":
            "https://www.kanakadurgamma.org/",

        "work_completion_confirmed":
            None,

        "is_structural_condition_label":
            False,

        "notes":
            "No exact verified structural dimension or current condition measurement stored."
    },


    # --------------------------------------------------------------
    # SRIKALAHASTI
    # --------------------------------------------------------------

    {
        "asset_code": "AP_TEMPLE_SRIKALAHASTI",

        "evidence_type":
            "HISTORICAL_ARCHITECTURE",

        "feature_name":
            "southern_gopuram_period",

        "text_value":
            "Official history places construction of the southern gopuram in the 12th century.",

        "numeric_value": 12,
        "unit": "CENTURY_CE",

        "event_year": None,

        "material":
            None,

        "component":
            "SOUTHERN_GOPURAM",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "AGE_CONTEXT",

        "source_authority":
            "Sri Kalahastheeswara Swamy Vari Devasthanam",

        "source_system":
            "Official Temple Website",

        "source_url":
            "https://srikalahasthitemple.org/history",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Historical construction evidence; not current structural condition."
    },

    {
        "asset_code": "AP_TEMPLE_SRIKALAHASTI",

        "evidence_type":
            "HISTORICAL_ARCHITECTURE",

        "feature_name":
            "royal_hall_period",

        "text_value":
            "Official history identifies a royal hall/porch associated with 16th-century Vijayanagara development.",

        "numeric_value": 16,
        "unit": "CENTURY_CE",

        "event_year": 1529,

        "material":
            None,

        "component":
            "ROYAL_HALL_MANDAPAM",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "AGE_CONTEXT",

        "source_authority":
            "Sri Kalahastheeswara Swamy Vari Devasthanam",

        "source_system":
            "Official Temple Website",

        "source_url":
            "https://srikalahasthitemple.org/history",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Historic architectural evidence."
    },

    {
        "asset_code": "AP_TEMPLE_SRIKALAHASTI",

        "evidence_type":
            "MATERIAL_HISTORY",

        "feature_name":
            "brick_historic_components",

        "text_value":
            "Official history records some cave/gopuram-related historical constructions using bricks.",

        "numeric_value": None,
        "unit": None,

        "event_year": None,

        "material":
            "BRICK",

        "component":
            "HISTORIC_COMPONENTS",

        "evidence_strength":
            "MODERATE",

        "engineering_use":
            "MATERIAL_CONTEXT",

        "source_authority":
            "Sri Kalahastheeswara Swamy Vari Devasthanam",

        "source_system":
            "Official Temple Website",

        "source_url":
            "https://srikalahasthitemple.org/history",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Does not imply the entire present temple is brick."
    },


    # --------------------------------------------------------------
    # SRISAILAM
    # --------------------------------------------------------------

    {
        "asset_code": "AP_TEMPLE_SRISAILAM",

        "evidence_type":
            "HISTORICAL_ARCHITECTURE",

        "feature_name":
            "multi_period_gopuram_mandapam",

        "text_value":
            "Official Devasthanam history records multiple gopurams and mandapams constructed or developed under historic dynasties.",

        "numeric_value": None,
        "unit": None,

        "event_year": None,

        "material":
            None,

        "component":
            "GOPURAMS_AND_MANDAPAMS",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "AGE_CONTEXT",

        "source_authority":
            "Sri Bhramaramba Mallikarjuna Swamy Varla Devasthanam",

        "source_system":
            "Official Devasthanam",

        "source_url":
            "https://www.srisailadevasthanam.org/en-in/about/the-temple-history/the-history",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Complex has multiple construction periods; do not assign one built year to whole temple."
    },

    {
        "asset_code": "AP_TEMPLE_SRISAILAM",

        "evidence_type":
            "GOVERNMENT_DEVELOPMENT_PROJECT",

        "feature_name":
            "prashad_project_cost",

        "text_value":
            "Development of Srisailam Temple under PRASHAD; project reported completed.",

        "numeric_value":
            43.08,

        "unit":
            "INR_CRORE",

        "event_year":
            2022,

        "material":
            None,

        "component":
            "PILGRIMAGE_INFRASTRUCTURE",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "DEVELOPMENT_HISTORY",

        "source_authority":
            "Ministry of Tourism, Government of India",

        "source_system":
            "PRASHAD",

        "source_url":
            "https://tourism.gov.in/sites/default/files/2022-12/PressReleasePage_26_Dec.pdf",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Includes tourist infrastructure; not evidence of structural rehabilitation of sanctum."
    },


    # --------------------------------------------------------------
    # SIMHACHALAM
    # --------------------------------------------------------------

    {
        "asset_code": "AP_TEMPLE_SIMHACHALAM",

        "evidence_type":
            "ARCHITECTURAL_COMPONENT",

        "feature_name":
            "natyamandapa_pillar_count",

        "text_value":
            "Official temple source identifies a 16-pillared Natyamandapa.",

        "numeric_value":
            16,

        "unit":
            "PILLARS",

        "event_year":
            None,

        "material":
            None,

        "component":
            "NATYAMANDAPA",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "GEOMETRY_CONTEXT",

        "source_authority":
            "Sri Varaha Lakshmi Narasimha Swamy Devasthanam",

        "source_system":
            "Official Temple Website",

        "source_url":
            "https://svlnsd.com/",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Verified architectural count, not condition."
    },

    {
        "asset_code": "AP_TEMPLE_SIMHACHALAM",

        "evidence_type":
            "ARCHITECTURAL_COMPONENT",

        "feature_name":
            "kalyanamandapa_pillar_count",

        "text_value":
            "Official temple source identifies a 96-pillared Kalyanamandapa.",

        "numeric_value":
            96,

        "unit":
            "PILLARS",

        "event_year":
            None,

        "material":
            None,

        "component":
            "KALYANAMANDAPA",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "GEOMETRY_CONTEXT",

        "source_authority":
            "Sri Varaha Lakshmi Narasimha Swamy Devasthanam",

        "source_system":
            "Official Temple Website",

        "source_url":
            "https://svlnsd.com/",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Verified architectural count."
    },

    {
        "asset_code": "AP_TEMPLE_SIMHACHALAM",

        "evidence_type":
            "GOVERNMENT_DEVELOPMENT_PROJECT",

        "feature_name":
            "prashad_rcc_facilitation_area",

        "text_value":
            "PRASHAD project specifies pilgrimage facilitation halls with RCC structure.",

        "numeric_value":
            2000,

        "unit":
            "SQM",

        "event_year":
            None,

        "material":
            "RCC",

        "component":
            "PILGRIMAGE_FACILITATION_HALLS",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "ANCILLARY_INFRASTRUCTURE",

        "source_authority":
            "Ministry of Tourism, Government of India",

        "source_system":
            "PRASHAD",

        "source_url":
            "https://tourism.gov.in/sites/default/files/2023-08/usq.1751%20for%2003.08.2023.pdf",

        "work_completion_confirmed":
            None,

        "is_structural_condition_label":
            False,

        "notes":
            "RCC area belongs to PRASHAD facilitation halls, not historic temple core."
    },


    # --------------------------------------------------------------
    # ANNAVARAM
    # --------------------------------------------------------------

    {
        "asset_code": "AP_TEMPLE_ANNAVARAM",

        "evidence_type":
            "RECONSTRUCTION_HISTORY",

        "feature_name":
            "reconstruction_1933_1934",

        "text_value":
            "Official NIC Devasthanam history states the temple was reconstructed during 1933-34 using locally available stone.",

        "numeric_value":
            1934,

        "unit":
            "YEAR",

        "event_year":
            1934,

        "material":
            "LOCAL_STONE",

        "component":
            "MAIN_TEMPLE",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "REHABILITATION_HISTORY",

        "source_authority":
            "Sri Veera Venkata Satyanarayana Swamy Vari Devasthanam / NIC",

        "source_system":
            "NIC Devasthanam Portal",

        "source_url":
            "https://annavaramdevasthanam.nic.in/Home/About",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Useful material and reconstruction evidence."
    },

    {
        "asset_code": "AP_TEMPLE_ANNAVARAM",

        "evidence_type":
            "RECONSTRUCTION_HISTORY",

        "feature_name":
            "reconstruction_2011_2012",

        "text_value":
            "Official history states the temple reached a dilapidated condition and was reconstructed during 2011-12.",

        "numeric_value":
            2012,

        "unit":
            "YEAR",

        "event_year":
            2012,

        "material":
            None,

        "component":
            "MAIN_TEMPLE",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "DETERIORATION_AND_REHABILITATION_HISTORY",

        "source_authority":
            "Sri Veera Venkata Satyanarayana Swamy Vari Devasthanam / NIC",

        "source_system":
            "NIC Devasthanam Portal",

        "source_url":
            "https://annavaramdevasthanam.nic.in/Home/About",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Strong historical deterioration/rehabilitation evidence but no numeric condition score."
    },

    {
        "asset_code": "AP_TEMPLE_ANNAVARAM",

        "evidence_type":
            "ARCHITECTURAL_STYLE",

        "feature_name":
            "architectural_style",

        "text_value":
            "Official site identifies the temple as Dravidian style with main temple formed like a chariot with four wheels.",

        "numeric_value":
            4,

        "unit":
            "CHARRIOT_CORNER_WHEELS",

        "event_year":
            None,

        "material":
            None,

        "component":
            "MAIN_TEMPLE",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "GEOMETRY_CONTEXT",

        "source_authority":
            "Sri Veera Venkata Satyanarayana Swamy Vari Devasthanam / NIC",

        "source_system":
            "NIC Devasthanam Portal",

        "source_url":
            "https://annavaramdevasthanam.nic.in/Home/About",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Architectural description, not measured geometry."
    },

    {
        "asset_code": "AP_TEMPLE_ANNAVARAM",

        "evidence_type":
            "GOVERNMENT_DEVELOPMENT_PROJECT",

        "feature_name":
            "prashad_sanction_cost",

        "text_value":
            "Development of Pilgrimage Tourism Infrastructure in Annavaram Temple Town sanctioned under PRASHAD.",

        "numeric_value":
            25.32,

        "unit":
            "INR_CRORE",

        "event_year":
            2024,

        "material":
            None,

        "component":
            "PILGRIMAGE_INFRASTRUCTURE",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "DEVELOPMENT_HISTORY",

        "source_authority":
            "Ministry of Tourism, Government of India",

        "source_system":
            "PRASHAD",

        "source_url":
            "https://tourism.gov.in/sites/default/files/2025-03/usq.3770%20for%2024.03.2025.pdf",

        "work_completion_confirmed":
            False,

        "is_structural_condition_label":
            False,

        "notes":
            "Sanctioned 02-Dec-2024; source states Letter of Acceptance issued 12-Mar-2025."
    },


    # --------------------------------------------------------------
    # DWARAKA TIRUMALA
    # --------------------------------------------------------------

    {
        "asset_code": "AP_TEMPLE_DWARAKA_TIRUMALA",

        "evidence_type":
            "ARCHITECTURE_CONTEXT",

        "feature_name":
            "engineering_detail_status",

        "text_value":
            "Official identity is verified, but no sufficiently precise structural dimension or condition measurement has yet been verified for SIMRAS.",

        "numeric_value":
            None,

        "unit":
            None,

        "event_year":
            None,

        "material":
            None,

        "component":
            "TEMPLE_COMPLEX",

        "evidence_strength":
            "LIMITED",

        "engineering_use":
            "WITHHOLD_ENGINEERING_SCORE",

        "source_authority":
            "Sri Venkateswara Swamy Vari Devasthanam, Dwaraka Tirumala",

        "source_system":
            "Official Temple Source",

        "source_url":
            "https://www.dwarakatirumaladevasthanam.org/",

        "work_completion_confirmed":
            None,

        "is_structural_condition_label":
            False,

        "notes":
            "No fabricated pillar count, dimensions, material or age."
    },


    # --------------------------------------------------------------
    # TIRUMALA
    # --------------------------------------------------------------

    {
        "asset_code": "AP_TEMPLE_TIRUMALA",

        "evidence_type":
            "ARCHITECTURAL_COMPONENT",

        "feature_name":
            "krishnadevaraya_mandapam_pillars",

        "text_value":
            "TTD identifies the Pratima/Krishnadevaraya Mandapam as a 16-pillared granite stone structure.",

        "numeric_value":
            16,

        "unit":
            "PILLARS",

        "event_year":
            None,

        "material":
            "GRANITE_STONE",

        "component":
            "KRISHNADEVARAYA_MANDAPAM",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "GEOMETRY_AND_MATERIAL_CONTEXT",

        "source_authority":
            "Tirumala Tirupati Devasthanams",

        "source_system":
            "TTD News",

        "source_url":
            "https://news.tirumala.org/mantapams-of-srivari-temple/",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Applies to this specific mandapam, not entire complex."
    },

    {
        "asset_code": "AP_TEMPLE_TIRUMALA",

        "evidence_type":
            "HISTORICAL_ARCHITECTURE",

        "feature_name":
            "mahadwaram_gopuram_period",

        "text_value":
            "TTD records the main Mahadwaram gopuram as dating to the 13th century.",

        "numeric_value":
            13,

        "unit":
            "CENTURY_CE",

        "event_year":
            None,

        "material":
            None,

        "component":
            "MAHADWARAM_GOPURAM",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "AGE_CONTEXT",

        "source_authority":
            "Tirumala Tirupati Devasthanams",

        "source_system":
            "TTD Official / TTD News",

        "source_url":
            "https://news.tirumala.org/mandapams-in-tirumala/",

        "work_completion_confirmed":
            True,

        "is_structural_condition_label":
            False,

        "notes":
            "Historical component age, not a single built year for the entire temple."
    },

    {
        "asset_code": "AP_TEMPLE_TIRUMALA",

        "evidence_type":
            "MAINTENANCE_CAPABILITY",

        "feature_name":
            "dedicated_structural_maintenance_wing",

        "text_value":
            "TTD states that a special wing maintains and repairs structures in the main shrine, including sub-temples, mandapams and gopurams.",

        "numeric_value":
            None,

        "unit":
            None,

        "event_year":
            None,

        "material":
            None,

        "component":
            "MAIN_SHRINE_STRUCTURES",

        "evidence_strength":
            "HIGH",

        "engineering_use":
            "MAINTENANCE_CONTEXT",

        "source_authority":
            "Tirumala Tirupati Devasthanams",

        "source_system":
            "TTD News",

        "source_url":
            "https://news.tirumala.org/dwarams-of-srivari-temple-at-tirumala/",

        "work_completion_confirmed":
            None,

        "is_structural_condition_label":
            False,

        "notes":
            "Maintenance capability evidence; not inspection result."
    },
]


async def main():

    if not IDENTITY.exists():
        raise RuntimeError(
            "Step 5B identity evidence CSV not found."
        )

    identity = pd.read_csv(
        IDENTITY,
        low_memory=False
    )

    asset_map = {
        str(r["asset_code"]).strip():
            {
                "asset_id":
                    int(r["asset_id"]),

                "asset_name":
                    r["asset_name"],

                "canonical_name":
                    r["canonical_name"],

                "district":
                    r.get("district"),
            }

        for _, r in identity.iterrows()
    }

    rows = []

    for i, evidence in enumerate(
        EVIDENCE,
        start=1
    ):

        code = evidence[
            "asset_code"
        ]

        if code not in asset_map:

            raise RuntimeError(
                f"Unknown temple asset_code: {code}"
            )

        base = asset_map[
            code
        ]

        row = {

            "evidence_id":
                i,

            "asset_id":
                base["asset_id"],

            "asset_code":
                code,

            "asset_name":
                base["asset_name"],

            "canonical_name":
                base["canonical_name"],

            "district":
                base["district"],

            **evidence,

            "verification_method":
                "WEB_VERIFIED_OFFICIAL_SOURCE",

            "is_synthetic":
                False,

            "is_derived":
                False,

            "is_health_label":
                False,

            "is_risk_label":
                False,

            "is_rul_label":
                False,

            "feature_version":
                "ap_temple_engineering_v1",
        }

        rows.append(
            row
        )

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

    # ==============================================================
    # BUILD PER-ASSET FEATURE SUMMARY
    # ==============================================================

    feature_rows = []

    for code, asset in asset_map.items():

        subset = df[
            df["asset_code"]
            == code
        ].copy()

        high_count = int(
            (
                subset[
                    "evidence_strength"
                ] == "HIGH"
            ).sum()
        )

        structural_labels = int(
            subset[
                "is_structural_condition_label"
            ].fillna(False)
            .astype(bool)
            .sum()
        )

        rehabilitation = int(
            subset[
                "engineering_use"
            ].astype(str)
            .str.contains(
                "REHABILITATION",
                case=False,
                na=False
            )
            .sum()
        )

        pillar_values = subset[
            subset["unit"]
            == "PILLARS"
        ]["numeric_value"]

        verified_pillar_count = (
            int(
                pd.to_numeric(
                    pillar_values,
                    errors="coerce"
                ).sum()
            )
            if not pillar_values.empty
            else None
        )

        materials = (
            subset[
                "material"
            ]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        feature_rows.append({

            "asset_id":
                asset["asset_id"],

            "asset_code":
                code,

            "asset_name":
                asset["asset_name"],

            "canonical_name":
                asset["canonical_name"],

            "engineering_evidence_rows":
                int(len(subset)),

            "high_strength_evidence_rows":
                high_count,

            "verified_pillar_count_sum_specific_components":
                verified_pillar_count,

            "verified_materials":
                ";".join(
                    materials
                )
                if materials
                else None,

            "rehabilitation_history_records":
                rehabilitation,

            "structural_condition_labels":
                structural_labels,

            "health_model_ready":
                False,

            "rul_model_ready":
                False,

            "health_status":
                "NEED_CURRENT_STRUCTURAL_INSPECTION",

            "rul_status":
                "NEED_LONGITUDINAL_CONDITION_OR_DEFENSIBLE_DESIGN_LIFE",

            "feature_version":
                "ap_temple_engineering_v1",
        })

    feature_df = pd.DataFrame(
        feature_rows
    )

    feature_df.to_csv(
        FEATURES,
        index=False
    )

    # ==============================================================
    # DATABASE
    # ==============================================================

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv(
            "SQLALCHEMY_DATABASE_URI"
        )
        or os.getenv(
            "POSTGRES_URL"
        )
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
                public.temple_engineering_evidence_verified
                (
                    id BIGSERIAL PRIMARY KEY,

                    asset_id BIGINT NOT NULL,
                    asset_code TEXT NOT NULL,
                    asset_name TEXT,
                    canonical_name TEXT,
                    district TEXT,

                    evidence_type TEXT NOT NULL,
                    feature_name TEXT NOT NULL,

                    text_value TEXT,

                    numeric_value
                        DOUBLE PRECISION,

                    unit TEXT,

                    event_year INTEGER,

                    material TEXT,

                    component TEXT,

                    evidence_strength TEXT,

                    engineering_use TEXT,

                    source_authority TEXT,

                    source_system TEXT,

                    source_url TEXT,

                    work_completion_confirmed
                        BOOLEAN,

                    is_structural_condition_label
                        BOOLEAN NOT NULL DEFAULT FALSE,

                    notes TEXT,

                    verification_method TEXT,

                    is_synthetic BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_derived BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_health_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_risk_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_rul_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    feature_version TEXT,

                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.temple_engineering_evidence_verified
                RESTART IDENTITY
            """)
        )

        insert = text("""
            INSERT INTO
            public.temple_engineering_evidence_verified
            (
                asset_id,
                asset_code,
                asset_name,
                canonical_name,
                district,

                evidence_type,
                feature_name,

                text_value,
                numeric_value,
                unit,

                event_year,
                material,
                component,

                evidence_strength,
                engineering_use,

                source_authority,
                source_system,
                source_url,

                work_completion_confirmed,

                is_structural_condition_label,

                notes,

                verification_method,

                is_synthetic,
                is_derived,

                is_health_label,
                is_risk_label,
                is_rul_label,

                feature_version
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,
                :canonical_name,
                :district,

                :evidence_type,
                :feature_name,

                :text_value,
                :numeric_value,
                :unit,

                :event_year,
                :material,
                :component,

                :evidence_strength,
                :engineering_use,

                :source_authority,
                :source_system,
                :source_url,

                :work_completion_confirmed,

                :is_structural_condition_label,

                :notes,

                :verification_method,

                :is_synthetic,
                :is_derived,

                :is_health_label,
                :is_risk_label,
                :is_rul_label,

                :feature_version
            )
        """)

        for row in rows:

            db_row = {
                k: v
                for k, v in row.items()
                if k not in {
                    "evidence_id"
                }
            }

            for key, value in list(
                db_row.items()
            ):

                if pd.isna(value):
                    db_row[key] = None

                elif hasattr(
                    value,
                    "item"
                ):
                    db_row[key] = (
                        value.item()
                    )

            await conn.execute(
                insert,
                db_row
            )

        verification = await conn.execute(
            text("""
                SELECT
                    COUNT(*) AS evidence_rows,

                    COUNT(
                        DISTINCT asset_id
                    ) AS assets_covered,

                    COUNT(*) FILTER (
                        WHERE evidence_strength='HIGH'
                    ) AS high_strength,

                    COUNT(*) FILTER (
                        WHERE is_structural_condition_label=TRUE
                    ) AS structural_labels,

                    COUNT(*) FILTER (
                        WHERE engineering_use ILIKE
                        '%REHABILITATION%'
                    ) AS rehabilitation_rows

                FROM
                    public.temple_engineering_evidence_verified
            """)
        )

        result = dict(
            verification.mappings().one()
        )

    await engine.dispose()

    # ==============================================================
    # REPORT
    # ==============================================================

    lines = [
        "=" * 110,
        "SIMRAS STEP 5C - TEMPLE ENGINEERING EVIDENCE RESULT",
        "=" * 110,
        "",
        f"Temple assets covered             : {result['assets_covered']} / 7",
        f"Verified evidence rows            : {result['evidence_rows']}",
        f"High-strength evidence rows       : {result['high_strength']}",
        f"Rehabilitation-history rows       : {result['rehabilitation_rows']}",
        f"Current structural labels         : {result['structural_labels']}",
        "",
    ]

    for feature in feature_rows:

        lines.append(
            f"{feature['asset_code']} | "
            f"evidence={feature['engineering_evidence_rows']} | "
            f"high={feature['high_strength_evidence_rows']} | "
            f"pillars={feature['verified_pillar_count_sum_specific_components']} | "
            f"rehab={feature['rehabilitation_history_records']} | "
            f"health={feature['health_status']}"
        )

    lines += [
        "",
        "Database table:",
        " public.temple_engineering_evidence_verified",
        "",
        "Feature CSV:",
        f" {FEATURES}",
        "",
        "Feature version:",
        " ap_temple_engineering_v1",
        "",
        "IMPORTANT:",
        " Historical architecture and rehabilitation records are now",
        " available as real evidence, but CURRENT structural-condition",
        " labels remain 0. Temple Health/RUL therefore remain withheld",
        " until inspection/condition evidence is available.",
        "=" * 110,
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

                "database_summary":
                    result,

                "features":
                    feature_rows,
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
