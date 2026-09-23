import os
import csv
import json
import asyncio
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")
DATA_DIR = ROOT / "data" / "bridge_inspections"

DATA_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


def async_database_url(value: str) -> str:
    if value.startswith("postgresql://"):
        return value.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    return value


DDL = r"""
CREATE TABLE IF NOT EXISTS public.ml_bridge_inspections_v1 (
    id BIGSERIAL PRIMARY KEY,

    asset_id BIGINT NOT NULL
        REFERENCES public.assets(id)
        ON DELETE CASCADE,

    asset_code TEXT NOT NULL,

    inspection_date DATE NOT NULL,

    inspection_type TEXT NOT NULL,

    inspection_authority TEXT NOT NULL,

    inspector_reference TEXT,

    source_document TEXT NOT NULL,

    source_url TEXT,

    source_record_id TEXT,

    evidence_class TEXT NOT NULL
        CHECK (
            evidence_class IN (
                'GOVERNMENT_INSPECTION',
                'OFFICIAL_ENGINEERING_INSPECTION',
                'FIELD_INSPECTION_VERIFIED'
            )
        ),

    rating_system TEXT,

    overall_rating_text TEXT,

    overall_rating_numeric DOUBLE PRECISION,

    condition_class TEXT,

    condition_numeric DOUBLE PRECISION,

    structural_condition_label BOOLEAN NOT NULL
        DEFAULT FALSE,

    scour_observed BOOLEAN,
    corrosion_observed BOOLEAN,
    cracking_observed BOOLEAN,
    spalling_observed BOOLEAN,
    leakage_observed BOOLEAN,
    bearing_distress_observed BOOLEAN,
    foundation_distress_observed BOOLEAN,

    maintenance_required BOOLEAN,

    remarks TEXT,

    source_hash TEXT,

    is_synthetic BOOLEAN NOT NULL
        DEFAULT FALSE
        CHECK (is_synthetic = FALSE),

    verified_for_ml BOOLEAN NOT NULL
        DEFAULT FALSE,

    verification_notes TEXT,

    imported_at TIMESTAMPTZ NOT NULL
        DEFAULT NOW(),

    UNIQUE (
        asset_id,
        inspection_date,
        inspection_authority,
        source_document,
        source_record_id
    )
);


CREATE INDEX IF NOT EXISTS
    ix_ml_bridge_inspections_asset
ON public.ml_bridge_inspections_v1 (
    asset_id
);


CREATE INDEX IF NOT EXISTS
    ix_ml_bridge_inspections_date
ON public.ml_bridge_inspections_v1 (
    inspection_date
);


CREATE TABLE IF NOT EXISTS public.ml_bridge_component_inspections_v1 (
    id BIGSERIAL PRIMARY KEY,

    inspection_id BIGINT NOT NULL
        REFERENCES public.ml_bridge_inspections_v1(id)
        ON DELETE CASCADE,

    component TEXT NOT NULL,

    subcomponent TEXT,

    rating_text TEXT,

    rating_numeric DOUBLE PRECISION,

    defect_type TEXT,

    defect_extent TEXT,

    defect_severity TEXT,

    measurement_value DOUBLE PRECISION,

    measurement_unit TEXT,

    observation TEXT,

    photo_reference TEXT,

    verified BOOLEAN NOT NULL
        DEFAULT FALSE
);


CREATE INDEX IF NOT EXISTS
    ix_ml_bridge_component_inspection
ON public.ml_bridge_component_inspections_v1 (
    inspection_id
);


CREATE OR REPLACE VIEW
public.ml_bridge_prediction_readiness_v1
AS
WITH evidence AS (
    SELECT
        asset_id,

        COUNT(*) FILTER (
            WHERE
                verified_for_ml = TRUE
                AND is_synthetic = FALSE
        ) AS verified_inspections,

        COUNT(*) FILTER (
            WHERE
                verified_for_ml = TRUE
                AND is_synthetic = FALSE
                AND structural_condition_label = TRUE
                AND condition_class IS NOT NULL
        ) AS labelled_inspections,

        COUNT(DISTINCT inspection_date) FILTER (
            WHERE
                verified_for_ml = TRUE
                AND is_synthetic = FALSE
                AND structural_condition_label = TRUE
                AND condition_class IS NOT NULL
        ) AS labelled_dates,

        MIN(inspection_date) FILTER (
            WHERE
                verified_for_ml = TRUE
                AND is_synthetic = FALSE
                AND structural_condition_label = TRUE
        ) AS first_label_date,

        MAX(inspection_date) FILTER (
            WHERE
                verified_for_ml = TRUE
                AND is_synthetic = FALSE
                AND structural_condition_label = TRUE
        ) AS last_label_date

    FROM public.ml_bridge_inspections_v1

    GROUP BY asset_id
)

SELECT
    a.id AS asset_id,
    a.asset_code,
    a.name,
    a.district,

    COALESCE(
        e.verified_inspections,
        0
    ) AS verified_inspections,

    COALESCE(
        e.labelled_inspections,
        0
    ) AS labelled_inspections,

    COALESCE(
        e.labelled_dates,
        0
    ) AS labelled_dates,

    e.first_label_date,
    e.last_label_date,

    CASE
        WHEN COALESCE(
            e.labelled_inspections,
            0
        ) >= 1
        THEN TRUE
        ELSE FALSE
    END AS current_condition_ml_eligible,

    CASE
        WHEN COALESCE(
            e.labelled_dates,
            0
        ) >= 2
        THEN TRUE
        ELSE FALSE
    END AS temporal_risk_ml_eligible,

    CASE
        WHEN COALESCE(
            e.labelled_dates,
            0
        ) >= 3
        THEN TRUE
        ELSE FALSE
    END AS deterioration_curve_candidate

FROM public.assets a

LEFT JOIN evidence e
    ON e.asset_id = a.id

WHERE
    LOWER(CAST(a.asset_type AS TEXT)) = 'bridge'
    AND a.asset_code LIKE 'AP_BR_%';
"""


TEMPLATE_COLUMNS = [
    "asset_code",
    "inspection_date",
    "inspection_type",
    "inspection_authority",
    "inspector_reference",
    "source_document",
    "source_url",
    "source_record_id",
    "evidence_class",
    "rating_system",
    "overall_rating_text",
    "overall_rating_numeric",
    "condition_class",
    "condition_numeric",
    "structural_condition_label",
    "scour_observed",
    "corrosion_observed",
    "cracking_observed",
    "spalling_observed",
    "leakage_observed",
    "bearing_distress_observed",
    "foundation_distress_observed",
    "maintenance_required",
    "remarks",
]


async def main():

    database_url = os.environ[
        "DATABASE_URL"
    ]

    engine = create_async_engine(
        async_database_url(
            database_url
        )
    )


    async with engine.begin() as conn:

        print()
        print(
            "===== EXISTING INSPECTION-LIKE TABLES ====="
        )

        rows = (
            await conn.execute(
                text(
                    """
                    SELECT
                        table_name
                    FROM information_schema.tables
                    WHERE table_schema='public'
                    AND (
                        table_name ILIKE '%inspect%'
                        OR table_name ILIKE '%condition%'
                    )
                    ORDER BY table_name
                    """
                )
            )
        ).scalars().all()

        for row in rows:
            print(row)

        if not rows:
            print(
                "NONE"
            )


        print()
        print(
            "===== CREATE REAL EVIDENCE FOUNDATION ====="
        )

        ddl_statements = [
            statement.strip()
            for statement in DDL.split(";")
            if statement.strip()
        ]

        if len(ddl_statements) != 6:
            raise RuntimeError(
                f"Expected 6 DDL statements, "
                f"found {len(ddl_statements)}."
            )

        for index, ddl_statement in enumerate(
            ddl_statements,
            start=1,
        ):
            print(
                f"DDL {index}/"
                f"{len(ddl_statements)}"
            )

            await conn.exec_driver_sql(
                ddl_statement
            )


    async with engine.connect() as conn:

        total_bridges = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.assets
                WHERE
                    LOWER(
                        CAST(asset_type AS TEXT)
                    )='bridge'
                    AND asset_code LIKE 'AP_BR_%'
                """
            )
        )


        inspection_count = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.ml_bridge_inspections_v1
                """
            )
        )


        synthetic_count = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.ml_bridge_inspections_v1
                WHERE is_synthetic=TRUE
                """
            )
        )


        current_ready = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.ml_bridge_prediction_readiness_v1
                WHERE current_condition_ml_eligible=TRUE
                """
            )
        )


        temporal_ready = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.ml_bridge_prediction_readiness_v1
                WHERE temporal_risk_ml_eligible=TRUE
                """
            )
        )


        deterioration_ready = await conn.scalar(
            text(
                """
                SELECT COUNT(*)
                FROM public.ml_bridge_prediction_readiness_v1
                WHERE deterioration_curve_candidate=TRUE
                """
            )
        )


        godavari = (
            await conn.execute(
                text(
                    """
                    SELECT *
                    FROM public.ml_bridge_prediction_readiness_v1
                    WHERE asset_code='AP_BR_00001'
                    LIMIT 1
                    """
                )
            )
        ).mappings().first()


        print()
        print(
            "===== ML-8A READINESS ====="
        )

        print(
            "AP_BRIDGES =",
            total_bridges,
        )

        print(
            "REAL_INSPECTION_ROWS =",
            inspection_count,
        )

        print(
            "SYNTHETIC_ROWS =",
            synthetic_count,
        )

        print(
            "CURRENT_CONDITION_READY =",
            current_ready,
        )

        print(
            "TEMPORAL_RISK_READY =",
            temporal_ready,
        )

        print(
            "DETERIORATION_CURVE_CANDIDATES =",
            deterioration_ready,
        )


        print()
        print(
            "===== GODAVARI ====="
        )

        print(
            json.dumps(
                dict(godavari)
                if godavari
                else None,
                indent=2,
                default=str,
            )
        )


    template = (
        DATA_DIR
        / "bridge_inspection_import_template.csv"
    )

    if not template.exists():

        with template.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=TEMPLATE_COLUMNS,
            )

            writer.writeheader()


    policy = {
        "schema_version":
            "ml_bridge_inspection_v1",

        "synthetic_labels_allowed":
            False,

        "asset_condition_is_training_label":
            False,

        "osm_is_condition_label":
            False,

        "government_inspection_allowed":
            True,

        "official_engineering_inspection_allowed":
            True,

        "current_condition_minimum":
            "1 verified labelled inspection",

        "temporal_risk_minimum":
            "2 verified labelled dates for same asset",

        "rul_policy":
            (
                "RUL remains withheld until "
                "longitudinal deterioration evidence "
                "and validation gates are established."
            ),
    }


    (
        DATA_DIR
        / "evidence_policy.json"
    ).write_text(
        json.dumps(
            policy,
            indent=2,
        ),
        encoding="utf-8",
    )


    print()
    print(
        "TEMPLATE =",
        template,
    )

    print(
        "POLICY =",
        DATA_DIR
        / "evidence_policy.json",
    )


    await engine.dispose()


asyncio.run(
    main()
)