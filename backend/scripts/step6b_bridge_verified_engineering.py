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
    / "bridge"
    / "AP_BRIDGE_SOURCE_PLAN.csv"
)

EVIDENCE_CSV = (
    ROOT
    / "data"
    / "processed"
    / "bridge"
    / "AP_BRIDGE_ENGINEERING_EVIDENCE.csv"
)

FEATURE_CSV = (
    ROOT
    / "data"
    / "processed"
    / "bridge"
    / "AP_BRIDGE_ENGINEERING_FEATURES.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP6B_BRIDGE_ENGINEERING_REPORT.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP6B_BRIDGE_ENGINEERING_REPORT.json"
)


# ==============================================================
# SOURCE TIERS
#
# A1 = primary government engineering/procurement
# A2 = government public information
# B1 = professional technical engineering reference
# C1 = peer-reviewed project case study
# C2 = industry project technical disclosure
#
# None of these are being treated as current-condition labels.
# ==============================================================


EVIDENCE = [

    # ==========================================================
    # GODAVARI ARCH BRIDGE
    # ==========================================================

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "CONSTRUCTION_HISTORY",
        "feature_name": "construction_start_year",
        "numeric_value": 1991,
        "text_value": None,
        "unit": "YEAR",
        "component": "WHOLE_BRIDGE",
        "source_tier": "A2_GOVERNMENT_PUBLIC_INFORMATION",
        "source_authority": "East Godavari District Administration",
        "source_key": "EAST_GODAVARI_ENGINEERING_TOURISM",
        "source_title": "Engineering Tourism - Arch Bridge",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "CONSTRUCTION_HISTORY",
        "feature_name": "construction_completion_year",
        "numeric_value": 1997,
        "text_value": None,
        "unit": "YEAR",
        "component": "WHOLE_BRIDGE",
        "source_tier": "A2_GOVERNMENT_PUBLIC_INFORMATION",
        "source_authority": "East Godavari District Administration",
        "source_key": "EAST_GODAVARI_ENGINEERING_TOURISM",
        "source_title": "Engineering Tourism - Arch Bridge",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "OPERATION_HISTORY",
        "feature_name": "full_operation_year",
        "numeric_value": 2003,
        "text_value": None,
        "unit": "YEAR",
        "component": "WHOLE_BRIDGE",
        "source_tier": "A2_GOVERNMENT_PUBLIC_INFORMATION",
        "source_authority": "East Godavari District Administration",
        "source_key": "EAST_GODAVARI_ENGINEERING_TOURISM",
        "source_title": "Engineering Tourism - Arch Bridge",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "GEOMETRY",
        "feature_name": "reported_total_length_m",
        "numeric_value": 2745.0,
        "text_value": None,
        "unit": "M",
        "component": "WHOLE_BRIDGE",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian Engineering Heritage Technical Reference",
        "source_key": "GODAVARI_ARCH_TECH_REFERENCE",
        "source_title": "Technical design reference for Godavari Arch Bridge",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "arch_span_count",
        "numeric_value": 28,
        "text_value": None,
        "unit": "SPANS",
        "component": "ARCH_SUPERSTRUCTURE",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "pier_count",
        "numeric_value": 28,
        "text_value": None,
        "unit": "PIERS",
        "component": "SUBSTRUCTURE",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian Railway technical reference chain",
        "source_key": "GODAVARI_ARCH_PIER_REFERENCE",
        "source_title": "Godavari Arch Bridge technical specifications",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "main_span_m",
        "numeric_value": 97.552,
        "text_value": None,
        "unit": "M",
        "component": "ARCH_SPAN",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "STRUCTURAL_SYSTEM",
        "feature_name": "bridge_type",
        "numeric_value": None,
        "text_value": "BOW_STRING_GIRDER_PRESTRESSED_RCC_ARCH",
        "unit": None,
        "component": "SUPERSTRUCTURE",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "MATERIAL",
        "feature_name": "arch_concrete_grade",
        "numeric_value": 45,
        "text_value": "M45_REINFORCED_CONCRETE",
        "unit": "MPA_GRADE",
        "component": "TWIN_ARCHES",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "arch_width_m",
        "numeric_value": 0.8,
        "text_value": None,
        "unit": "M",
        "component": "TWIN_ARCHES",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "arch_depth_springing_m",
        "numeric_value": 1.7,
        "text_value": None,
        "unit": "M",
        "component": "TWIN_ARCHES",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "arch_depth_crown_m",
        "numeric_value": 1.15,
        "text_value": None,
        "unit": "M",
        "component": "TWIN_ARCHES",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00001",
        "evidence_type": "DESIGN_PARAMETER",
        "feature_name": "design_train_speed_kmph",
        "numeric_value": 160,
        "text_value": None,
        "unit": "KM_PER_HOUR",
        "component": "WHOLE_BRIDGE",
        "source_tier": "B1_TECHNICAL_ENGINEERING_REFERENCE",
        "source_authority": "Indian National Academy of Engineering reference",
        "source_key": "INAE_GODAVARI_ARCH_REFERENCE",
        "source_title": "Indian Engineering Heritage - Railways",
        "is_derived": False,
    },


    # ==========================================================
    # KANAKA DURGA FLYOVER
    # ==========================================================

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "PROJECT_GEOMETRY",
        "feature_name": "nh65_project_corridor_length_m",
        "numeric_value": 5122,
        "text_value": None,
        "unit": "M",
        "component": "NH65_PROJECT_CORRIDOR",
        "source_tier": "A1_PRIMARY_GOVERNMENT",
        "source_authority": "Ministry of Road Transport and Highways",
        "source_key": "MORTH_KANAKA_DURGA_PROJECT",
        "source_title": "Andhra Pradesh infrastructure project booklet",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "GEOMETRY",
        "feature_name": "elevated_flyover_length_m",
        "numeric_value": 2600,
        "text_value": None,
        "unit": "M",
        "component": "ELEVATED_FLYOVER",
        "source_tier": "C1_PEER_REVIEWED_PROJECT_CASE_STUDY",
        "source_authority": "Materials Today: Proceedings project case study",
        "source_key": "KDF_MATERIALS_TODAY_2021",
        "source_title": "Kanaka Durga Flyover project case study",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "pier_count",
        "numeric_value": 45,
        "text_value": None,
        "unit": "PIERS",
        "component": "ELEVATED_FLYOVER",
        "source_tier": "C1_PEER_REVIEWED_PROJECT_CASE_STUDY",
        "source_authority": "Materials Today: Proceedings project case study",
        "source_key": "KDF_MATERIALS_TODAY_2021",
        "source_title": "Kanaka Durga Flyover project case study based on project reports",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "abutment_count",
        "numeric_value": 2,
        "text_value": None,
        "unit": "ABUTMENTS",
        "component": "ELEVATED_FLYOVER",
        "source_tier": "C1_PEER_REVIEWED_PROJECT_CASE_STUDY",
        "source_authority": "Materials Today: Proceedings project case study",
        "source_key": "KDF_MATERIALS_TODAY_2021",
        "source_title": "Kanaka Durga Flyover project case study based on project reports",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "GEOMETRY",
        "feature_name": "lane_count",
        "numeric_value": 6,
        "text_value": "SIX_LANE",
        "unit": "LANES",
        "component": "ELEVATED_FLYOVER",
        "source_tier": "C2_INDUSTRY_PROJECT_TECHNICAL_DISCLOSURE",
        "source_authority": "Tata Steel",
        "source_key": "TATA_KANAKA_DURGA_2020",
        "source_title": "Kanaka Durga Flyover technical project release",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "GEOMETRY",
        "feature_name": "flyover_width_m",
        "numeric_value": 23.7744,
        "text_value": "SOURCE_REPORTED_78_FT",
        "unit": "M",
        "component": "ELEVATED_FLYOVER",
        "source_tier": "C2_INDUSTRY_PROJECT_TECHNICAL_DISCLOSURE",
        "source_authority": "Tata Steel",
        "source_key": "TATA_KANAKA_DURGA_2020",
        "source_title": "Kanaka Durga Flyover technical project release",
        "is_derived": True,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "STRUCTURAL_GEOMETRY",
        "feature_name": "reported_span_between_pillars_m",
        "numeric_value": 45,
        "text_value": None,
        "unit": "M",
        "component": "ELEVATED_FLYOVER",
        "source_tier": "C2_INDUSTRY_PROJECT_TECHNICAL_DISCLOSURE",
        "source_authority": "Tata Steel",
        "source_key": "TATA_KANAKA_DURGA_2020",
        "source_title": "Kanaka Durga Flyover technical project release",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "MATERIAL",
        "feature_name": "lrpc_strands_quantity_t",
        "numeric_value": 2000,
        "text_value": "LOW_RELAXATION_PRESTRESSED_CONCRETE_STRANDS",
        "unit": "METRIC_TONNES",
        "component": "FLYOVER_STRUCTURE",
        "source_tier": "C2_INDUSTRY_PROJECT_TECHNICAL_DISCLOSURE",
        "source_authority": "Tata Steel",
        "source_key": "TATA_KANAKA_DURGA_2020",
        "source_title": "Kanaka Durga Flyover technical project release",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "MATERIAL",
        "feature_name": "tmt_steel_quantity_t",
        "numeric_value": 10000,
        "text_value": "TMT_REINFORCEMENT_STEEL",
        "unit": "METRIC_TONNES",
        "component": "FLYOVER_STRUCTURE",
        "source_tier": "C2_INDUSTRY_PROJECT_TECHNICAL_DISCLOSURE",
        "source_authority": "Tata Steel",
        "source_key": "TATA_KANAKA_DURGA_2020",
        "source_title": "Kanaka Durga Flyover technical project release",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "OPERATION_HISTORY",
        "feature_name": "opening_year",
        "numeric_value": 2020,
        "text_value": None,
        "unit": "YEAR",
        "component": "WHOLE_FLYOVER",
        "source_tier": "C2_INDUSTRY_PROJECT_TECHNICAL_DISCLOSURE",
        "source_authority": "Tata Steel",
        "source_key": "TATA_KANAKA_DURGA_2020",
        "source_title": "Kanaka Durga Flyover technical project release",
        "is_derived": False,
    },

    {
        "asset_code": "AP_BR_00002",
        "evidence_type": "MAINTENANCE_PROCUREMENT",
        "feature_name": "short_term_maintenance_2025",
        "numeric_value": 25151174,
        "text_value":
            "Short Term Maintenance to Kanaka Durga Flyover / NH-65 missing-link corridor",
        "unit": "INR",
        "component": "FLYOVER_CORRIDOR",
        "source_tier": "A1_PRIMARY_GOVERNMENT",
        "source_authority": "Government of India eProcurement / R&B NH Division Vijayawada",
        "source_key": "GOI_EPROCURE_KDF_2025",
        "source_title": "2025 Short Term Maintenance tender",
        "is_derived": False,
    },
]


FEATURES = {

    "AP_BR_00001": {

        "structure_mode":
            "RAIL",

        "length_m":
            2745.0,

        "width_m":
            None,

        "pier_count":
            28,

        "abutment_count":
            None,

        "span_count":
            28,

        "max_reported_span_m":
            97.552,

        "lane_or_track_count":
            1,

        "material_summary":
            "PRESTRESSED_RCC_TWIN_ARCHES_M45",

        "completion_year_evidence":
            1997,

        "full_operation_year":
            2003,

        "current_maintenance_procurement":
            False,
    },


    "AP_BR_00002": {

        "structure_mode":
            "ROAD",

        "length_m":
            2600.0,

        "width_m":
            23.7744,

        "pier_count":
            45,

        "abutment_count":
            2,

        "span_count":
            None,

        "max_reported_span_m":
            45.0,

        "lane_or_track_count":
            6,

        "material_summary":
            "LRPC_STRANDS_AND_TMT_REINFORCEMENT",

        "completion_year_evidence":
            2020,

        "full_operation_year":
            2020,

        "current_maintenance_procurement":
            True,
    },
}


async def main():

    if not PLAN.exists():

        raise RuntimeError(
            "Step 6A bridge source plan missing."
        )

    plan = pd.read_csv(
        PLAN,
        low_memory=False
    )

    asset_map = {

        str(row["asset_code"]).strip():
            {
                "asset_id":
                    int(row["asset_id"]),

                "asset_name":
                    row["asset_name"],

                "district":
                    row.get("district"),

                "existing_built_year":
                    row.get("built_year"),

                "existing_design_life":
                    row.get(
                        "design_life_years"
                    ),
            }

        for _, row
        in plan.iterrows()
    }

    evidence_rows = []

    now = datetime.now(
        timezone.utc
    )

    for item in EVIDENCE:

        code = item[
            "asset_code"
        ]

        if code not in asset_map:

            raise RuntimeError(
                f"Unknown bridge asset: {code}"
            )

        evidence_rows.append({

            "asset_id":
                asset_map[
                    code
                ][
                    "asset_id"
                ],

            "asset_name":
                asset_map[
                    code
                ][
                    "asset_name"
                ],

            **item,

            "verification_method":
                "WEB_VERIFIED_SOURCE_REVIEW",

            "is_synthetic":
                False,

            "is_current_condition_label":
                False,

            "is_health_label":
                False,

            "is_risk_label":
                False,

            "is_rul_label":
                False,

            "verified_at":
                now,
        })

    evidence_df = pd.DataFrame(
        evidence_rows
    )

    EVIDENCE_CSV.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    evidence_df.to_csv(
        EVIDENCE_CSV,
        index=False
    )

    # ==========================================================
    # FEATURE SUMMARY
    # ==========================================================

    feature_rows = []

    for code, base in asset_map.items():

        f = FEATURES.get(
            code
        )

        if not f:

            continue

        subset = evidence_df[
            evidence_df[
                "asset_code"
            ] == code
        ]

        government_rows = int(
            subset[
                "source_tier"
            ]
            .astype(str)
            .str.startswith(
                "A"
            )
            .sum()
        )

        technical_rows = int(
            len(subset)
            - government_rows
        )

        design_life = base[
            "existing_design_life"
        ]

        if (
            design_life is not None
            and not pd.isna(
                design_life
            )
        ):
            rul_status = (
                "PLANNING_BASIS_AVAILABLE_NOT_VALIDATED"
            )
        else:
            rul_status = (
                "WITHHOLD_RUL"
            )

        feature_rows.append({

            "asset_id":
                base[
                    "asset_id"
                ],

            "asset_code":
                code,

            "asset_name":
                base[
                    "asset_name"
                ],

            "district":
                base[
                    "district"
                ],

            **f,

            "government_evidence_rows":
                government_rows,

            "technical_reference_rows":
                technical_rows,

            "current_structural_condition_labels":
                0,

            "health_ml_readiness":
                "NO_REAL_STRUCTURAL_INSPECTION",

            "risk_ml_readiness":
                "NO_AP_STRUCTURAL_FAILURE_LABEL",

            "rul_readiness":
                rul_status,

            "feature_version":
                "ap_bridge_engineering_v1",
        })

    feature_df = pd.DataFrame(
        feature_rows
    )

    feature_df.to_csv(
        FEATURE_CSV,
        index=False
    )

    # ==========================================================
    # DATABASE
    # ==========================================================

    db_url = (
        os.getenv(
            "DATABASE_URL"
        )
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
                public.bridge_engineering_evidence_verified
                (
                    id BIGSERIAL PRIMARY KEY,

                    asset_id BIGINT NOT NULL,

                    asset_code TEXT NOT NULL,
                    asset_name TEXT,

                    evidence_type TEXT,
                    feature_name TEXT,

                    numeric_value
                        DOUBLE PRECISION,

                    text_value TEXT,
                    unit TEXT,

                    component TEXT,

                    source_tier TEXT,

                    source_authority TEXT,
                    source_key TEXT,
                    source_title TEXT,

                    is_derived BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    verification_method TEXT,

                    is_synthetic BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_current_condition_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_health_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_risk_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    is_rul_label BOOLEAN
                        NOT NULL DEFAULT FALSE,

                    verified_at TIMESTAMPTZ,

                    created_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.bridge_engineering_evidence_verified
                RESTART IDENTITY
            """)
        )

        insert = text("""
            INSERT INTO
            public.bridge_engineering_evidence_verified
            (
                asset_id,
                asset_code,
                asset_name,

                evidence_type,
                feature_name,

                numeric_value,
                text_value,
                unit,

                component,

                source_tier,

                source_authority,
                source_key,
                source_title,

                is_derived,

                verification_method,

                is_synthetic,

                is_current_condition_label,

                is_health_label,
                is_risk_label,
                is_rul_label,

                verified_at
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,

                :evidence_type,
                :feature_name,

                :numeric_value,
                :text_value,
                :unit,

                :component,

                :source_tier,

                :source_authority,
                :source_key,
                :source_title,

                :is_derived,

                :verification_method,

                :is_synthetic,

                :is_current_condition_label,

                :is_health_label,
                :is_risk_label,
                :is_rul_label,

                :verified_at
            )
        """)

        for row in evidence_rows:

            clean = dict(
                row
            )

            for key, value in list(
                clean.items()
            ):

                if (
                    value is not None
                    and not isinstance(
                        value,
                        (
                            str,
                            bool,
                            int,
                            float,
                            datetime
                        )
                    )
                ):

                    if pd.isna(
                        value
                    ):
                        clean[
                            key
                        ] = None

                    elif hasattr(
                        value,
                        "item"
                    ):

                        clean[
                            key
                        ] = (
                            value.item()
                        )

            await conn.execute(
                insert,
                clean
            )


        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.bridge_engineering_features_verified
                (
                    asset_id BIGINT PRIMARY KEY,

                    asset_code TEXT NOT NULL,
                    asset_name TEXT,

                    district TEXT,

                    structure_mode TEXT,

                    length_m
                        DOUBLE PRECISION,

                    width_m
                        DOUBLE PRECISION,

                    pier_count INTEGER,

                    abutment_count INTEGER,

                    span_count INTEGER,

                    max_reported_span_m
                        DOUBLE PRECISION,

                    lane_or_track_count INTEGER,

                    material_summary TEXT,

                    completion_year_evidence
                        INTEGER,

                    full_operation_year INTEGER,

                    current_maintenance_procurement
                        BOOLEAN,

                    government_evidence_rows
                        INTEGER,

                    technical_reference_rows
                        INTEGER,

                    current_structural_condition_labels
                        INTEGER,

                    health_ml_readiness TEXT,

                    risk_ml_readiness TEXT,

                    rul_readiness TEXT,

                    feature_version TEXT,

                    updated_at TIMESTAMPTZ
                        NOT NULL DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.bridge_engineering_features_verified
            """)
        )

        feature_insert = text("""
            INSERT INTO
            public.bridge_engineering_features_verified
            (
                asset_id,
                asset_code,
                asset_name,
                district,

                structure_mode,

                length_m,
                width_m,

                pier_count,
                abutment_count,
                span_count,

                max_reported_span_m,

                lane_or_track_count,

                material_summary,

                completion_year_evidence,
                full_operation_year,

                current_maintenance_procurement,

                government_evidence_rows,
                technical_reference_rows,

                current_structural_condition_labels,

                health_ml_readiness,
                risk_ml_readiness,
                rul_readiness,

                feature_version
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,
                :district,

                :structure_mode,

                :length_m,
                :width_m,

                :pier_count,
                :abutment_count,
                :span_count,

                :max_reported_span_m,

                :lane_or_track_count,

                :material_summary,

                :completion_year_evidence,
                :full_operation_year,

                :current_maintenance_procurement,

                :government_evidence_rows,
                :technical_reference_rows,

                :current_structural_condition_labels,

                :health_ml_readiness,
                :risk_ml_readiness,
                :rul_readiness,

                :feature_version
            )
        """)

        for row in feature_rows:

            clean = dict(
                row
            )

            for key, value in list(
                clean.items()
            ):

                if value is None:
                    continue

                try:

                    if pd.isna(
                        value
                    ):
                        clean[
                            key
                        ] = None

                except Exception:
                    pass

                if hasattr(
                    clean.get(
                        key
                    ),
                    "item"
                ):

                    clean[
                        key
                    ] = clean[
                        key
                    ].item()

            await conn.execute(
                feature_insert,
                clean
            )


        verify = await conn.execute(
            text("""
                SELECT

                    COUNT(*) AS assets,

                    COUNT(*) FILTER (
                        WHERE length_m IS NOT NULL
                    ) AS with_length,

                    COUNT(*) FILTER (
                        WHERE pier_count IS NOT NULL
                    ) AS with_piers,

                    COUNT(*) FILTER (
                        WHERE width_m IS NOT NULL
                    ) AS with_width,

                    SUM(
                        current_structural_condition_labels
                    ) AS structural_labels

                FROM
                    public.bridge_engineering_features_verified
            """)
        )

        result = dict(
            verify.mappings().one()
        )


        ecount = await conn.execute(
            text("""
                SELECT
                    COUNT(*) AS rows
                FROM
                    public.bridge_engineering_evidence_verified
            """)
        )

        evidence_count = int(
            ecount.scalar()
            or 0
        )

    await engine.dispose()


    # ==========================================================
    # REPORT
    # ==========================================================

    lines = [
        "=" * 110,
        "SIMRAS STEP 6B - VERIFIED BRIDGE ENGINEERING RESULT",
        "=" * 110,
        "",
        f"Bridge assets covered             : {result['assets']} / 2",
        f"Verified engineering evidence     : {evidence_count}",
        f"Assets with verified length       : {result['with_length']} / 2",
        f"Assets with verified pier count   : {result['with_piers']} / 2",
        f"Assets with verified width        : {result['with_width']} / 2",
        f"Current structural labels         : {result['structural_labels'] or 0}",
        "",
    ]

    for row in feature_rows:

        lines.append(
            f"{row['asset_code']} | "
            f"{row['asset_name']} | "
            f"length={row['length_m']} m | "
            f"width={row['width_m']} | "
            f"piers={row['pier_count']} | "
            f"spans={row['span_count']} | "
            f"max_span={row['max_reported_span_m']} m | "
            f"mode={row['structure_mode']}"
        )

    lines += [
        "",
        "Database tables:",
        " public.bridge_engineering_evidence_verified",
        " public.bridge_engineering_features_verified",
        "",
        "Feature version:",
        " ap_bridge_engineering_v1",
        "",
        "IMPORTANT:",
        " Geometry/material/maintenance evidence is now available.",
        " Current real structural inspection labels remain 0.",
        " Therefore bridge Health ML is still NOT AP-validated.",
        "=" * 110,
    ]

    REPORT.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8"
    )

    REPORT_JSON.write_text(
        json.dumps(
            {
                "generated_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "evidence_rows":
                    evidence_count,

                "summary":
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
        "\n".join(
            lines
        )
    )


asyncio.run(main())
