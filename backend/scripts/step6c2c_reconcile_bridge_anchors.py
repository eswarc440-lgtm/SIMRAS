from __future__ import annotations

import os
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ANCHORS = [
    "AP_BR_00001",
    "AP_BR_00002",
]


async def main():

    db_url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not db_url:
        raise RuntimeError("DATABASE_URL unavailable")

    if db_url.startswith("postgresql://"):
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

        print("=" * 105)
        print("VERIFIED ANCHOR STATUS BEFORE REPAIR")
        print("=" * 105)

        assets = await conn.execute(
            text("""
                SELECT
                    a.id,
                    a.asset_code,
                    a.name,
                    ST_Y(a.representative_geometry) AS latitude,
                    ST_X(a.representative_geometry) AS longitude,

                    EXISTS (
                        SELECT 1
                        FROM public.bridge_digital_twin_profiles p
                        WHERE p.asset_id=a.id
                    ) AS has_twin,

                    EXISTS (
                        SELECT 1
                        FROM public.bridge_report_readiness r
                        WHERE r.asset_id=a.id
                    ) AS has_report

                FROM public.assets a

                WHERE a.asset_code = ANY(:codes)

                ORDER BY a.asset_code
            """),
            {
                "codes": ANCHORS
            }
        )

        asset_rows = [
            dict(r)
            for r in assets.mappings()
        ]

        if len(asset_rows) != 2:
            raise RuntimeError(
                f"Expected 2 verified bridge anchors, found {len(asset_rows)}"
            )

        for asset in asset_rows:

            print(
                f"{asset['asset_code']} | "
                f"{asset['name']} | "
                f"twin={asset['has_twin']} | "
                f"report={asset['has_report']}"
            )

            match_result = await conn.execute(
                text("""
                    SELECT
                        osm_way_id,
                        source_name,
                        bridge_type,
                        length_m_derived,
                        anchor_asset_code,
                        canonical_asset_id

                    FROM public.bridge_osm_catalog

                    WHERE
                        anchor_asset_code=:asset_code

                    ORDER BY
                        length_m_derived DESC NULLS LAST
                """),
                {
                    "asset_code":
                        asset["asset_code"]
                }
            )

            matches = [
                dict(r)
                for r in match_result.mappings()
            ]

            print(
                f"  Explicit OSM anchor matches: {len(matches)}"
            )

            for match in matches[:10]:

                print(
                    f"    w{match['osm_way_id']} | "
                    f"{match['source_name']} | "
                    f"{match['bridge_type']} | "
                    f"{match['length_m_derived']} m"
                )

        # ------------------------------------------------------
        # ENSURE ALL EXPLICIT OSM ANCHOR ROWS POINT TO
        # THEIR VERIFIED CANONICAL ASSET.
        # ------------------------------------------------------

        await conn.execute(
            text("""
                UPDATE
                    public.bridge_osm_catalog c

                SET
                    canonical_asset_id=a.id,
                    asset_code=a.asset_code

                FROM
                    public.assets a

                WHERE
                    c.anchor_asset_code=a.asset_code
                    AND
                    a.asset_code = ANY(:codes)
            """),
            {
                "codes": ANCHORS
            }
        )

        # ------------------------------------------------------
        # CREATE / REPLACE PROFILE FOR ANY VERIFIED ANCHOR
        # WITH AN OSM MATCH.
        #
        # Longest mapped matching way is used as primary
        # visual alignment.
        # ------------------------------------------------------

        await conn.execute(
            text("""
                INSERT INTO
                    public.bridge_digital_twin_profiles
                (
                    asset_id,
                    osm_way_id,
                    structure_key,
                    bridge_type,

                    actual_length_m,
                    reported_width_m,
                    render_width_m,
                    width_basis,

                    latitude,
                    longitude,

                    actual_geometry,
                    geometry_source,

                    lanes_reported,
                    material_reported,

                    verified_pier_count,
                    pier_count_status,

                    rendering_strategy,
                    rendering_estimated,

                    profile_version
                )

                SELECT DISTINCT ON (a.id)

                    a.id,

                    c.osm_way_id,

                    c.structure_key,

                    COALESCE(
                        c.bridge_type,
                        f.structure_mode
                    ),

                    COALESCE(
                        f.length_m,
                        c.length_m_derived
                    ),

                    COALESCE(
                        f.width_m,
                        c.width_m_reported
                    ),

                    COALESCE(
                        f.width_m,
                        c.render_width_m
                    ),

                    CASE
                        WHEN f.width_m IS NOT NULL
                        THEN 'VERIFIED_ENGINEERING_EVIDENCE'
                        ELSE c.render_width_basis
                    END,

                    c.latitude,
                    c.longitude,

                    c.geometry_json,

                    'OPENSTREETMAP',

                    c.lanes_reported,

                    COALESCE(
                        f.material_summary,
                        c.material_reported
                    ),

                    f.pier_count,

                    CASE
                        WHEN f.pier_count IS NOT NULL
                        THEN 'VERIFIED_ENGINEERING_EVIDENCE'
                        ELSE 'UNKNOWN_DO_NOT_REPORT'
                    END,

                    'REAL_OSM_ALIGNMENT_WITH_VERIFIED_ENGINEERING',

                    CASE
                        WHEN
                            f.width_m IS NOT NULL
                            AND f.pier_count IS NOT NULL
                        THEN FALSE
                        ELSE TRUE
                    END,

                    'ap_bridge_twin_v1'

                FROM
                    public.assets a

                JOIN
                    public.bridge_osm_catalog c
                ON
                    c.anchor_asset_code=a.asset_code

                LEFT JOIN
                    public.bridge_engineering_features_verified f
                ON
                    f.asset_id=a.id

                WHERE
                    a.asset_code = ANY(:codes)

                ORDER BY
                    a.id,
                    c.length_m_derived DESC NULLS LAST

                ON CONFLICT (asset_id)
                DO UPDATE SET

                    osm_way_id=
                        EXCLUDED.osm_way_id,

                    structure_key=
                        EXCLUDED.structure_key,

                    bridge_type=
                        EXCLUDED.bridge_type,

                    actual_length_m=
                        EXCLUDED.actual_length_m,

                    reported_width_m=
                        EXCLUDED.reported_width_m,

                    render_width_m=
                        EXCLUDED.render_width_m,

                    width_basis=
                        EXCLUDED.width_basis,

                    latitude=
                        EXCLUDED.latitude,

                    longitude=
                        EXCLUDED.longitude,

                    actual_geometry=
                        EXCLUDED.actual_geometry,

                    geometry_source=
                        EXCLUDED.geometry_source,

                    lanes_reported=
                        EXCLUDED.lanes_reported,

                    material_reported=
                        EXCLUDED.material_reported,

                    verified_pier_count=
                        EXCLUDED.verified_pier_count,

                    pier_count_status=
                        EXCLUDED.pier_count_status,

                    rendering_strategy=
                        EXCLUDED.rendering_strategy,

                    rendering_estimated=
                        EXCLUDED.rendering_estimated,

                    profile_version=
                        EXCLUDED.profile_version,

                    updated_at=NOW()
            """),
            {
                "codes": ANCHORS
            }
        )

        # ------------------------------------------------------
        # IF AN ANCHOR STILL HAS NO OSM ALIGNMENT,
        # CREATE A VERIFIED ENGINEERING FALLBACK PROFILE.
        #
        # No fake geometry or pier count is created.
        # ------------------------------------------------------

        await conn.execute(
            text("""
                INSERT INTO
                    public.bridge_digital_twin_profiles
                (
                    asset_id,

                    osm_way_id,

                    structure_key,

                    bridge_type,

                    actual_length_m,

                    reported_width_m,

                    render_width_m,

                    width_basis,

                    latitude,

                    longitude,

                    actual_geometry,

                    geometry_source,

                    lanes_reported,

                    material_reported,

                    verified_pier_count,

                    pier_count_status,

                    rendering_strategy,

                    rendering_estimated,

                    profile_version
                )

                SELECT
                    a.id,

                    NULL,

                    'VERIFIED_ANCHOR::'
                    || a.asset_code,

                    f.structure_mode,

                    f.length_m,

                    f.width_m,

                    f.width_m,

                    CASE
                        WHEN f.width_m IS NOT NULL
                        THEN 'VERIFIED_ENGINEERING_EVIDENCE'
                        ELSE 'UNKNOWN_DO_NOT_REPORT'
                    END,

                    ST_Y(
                        a.representative_geometry
                    ),

                    ST_X(
                        a.representative_geometry
                    ),

                    NULL,

                    'NO_OSM_ALIGNMENT_MATCH',

                    f.lane_or_track_count,

                    f.material_summary,

                    f.pier_count,

                    CASE
                        WHEN f.pier_count IS NOT NULL
                        THEN 'VERIFIED_ENGINEERING_EVIDENCE'
                        ELSE 'UNKNOWN_DO_NOT_REPORT'
                    END,

                    'VERIFIED_ENGINEERING_PROCEDURAL_FALLBACK',

                    TRUE,

                    'ap_bridge_twin_v1'

                FROM
                    public.assets a

                JOIN
                    public.bridge_engineering_features_verified f
                ON
                    f.asset_id=a.id

                WHERE
                    a.asset_code = ANY(:codes)

                    AND NOT EXISTS
                    (
                        SELECT 1
                        FROM
                            public.bridge_digital_twin_profiles p
                        WHERE
                            p.asset_id=a.id
                    )

                ON CONFLICT (asset_id)
                DO NOTHING
            """),
            {
                "codes": ANCHORS
            }
        )

        # ------------------------------------------------------
        # ENSURE BOTH HAVE REPORT READINESS
        # ------------------------------------------------------

        await conn.execute(
            text("""
                INSERT INTO
                    public.bridge_report_readiness
                (
                    asset_id,

                    health_score,
                    health_status,

                    risk_score,
                    risk_level,
                    risk_status,

                    confidence,
                    confidence_status,

                    rul_years,
                    rul_status,

                    geometry_status,
                    engineering_status,
                    evidence_status,

                    report_version
                )

                SELECT
                    a.id,

                    NULL,
                    'WITHHELD_NO_REAL_STRUCTURAL_INSPECTION',

                    NULL,
                    NULL,
                    'WITHHELD_NO_AP_STRUCTURAL_RISK_LABEL',

                    NULL,
                    'NOT_A_MODEL_CONFIDENCE',

                    NULL,

                    CASE
                        WHEN
                            a.asset_code='AP_BR_00001'
                        THEN
                            'PLANNING_BASIS_AVAILABLE_NOT_VALIDATED'
                        ELSE
                            'WITHHELD_NO_VALIDATED_RUL_BASIS'
                    END,

                    CASE
                        WHEN
                            p.actual_geometry IS NOT NULL
                        THEN
                            'REAL_OSM_ALIGNMENT_AVAILABLE'
                        ELSE
                            'VERIFIED_ENGINEERING_GEOMETRY_ONLY'
                    END,

                    'VERIFIED_ENGINEERING_ANCHOR',

                    'VERIFIED_ENGINEERING_EVIDENCE',

                    'ap_bridge_report_v1'

                FROM
                    public.assets a

                JOIN
                    public.bridge_digital_twin_profiles p
                ON
                    p.asset_id=a.id

                WHERE
                    a.asset_code = ANY(:codes)

                ON CONFLICT (asset_id)
                DO UPDATE SET

                    health_status=
                        EXCLUDED.health_status,

                    risk_status=
                        EXCLUDED.risk_status,

                    rul_status=
                        EXCLUDED.rul_status,

                    geometry_status=
                        EXCLUDED.geometry_status,

                    engineering_status=
                        EXCLUDED.engineering_status,

                    evidence_status=
                        EXCLUDED.evidence_status,

                    report_version=
                        EXCLUDED.report_version,

                    updated_at=NOW()
            """),
            {
                "codes": ANCHORS
            }
        )

        # ------------------------------------------------------
        # FINAL SYSTEM COUNTS
        # ------------------------------------------------------

        result = await conn.execute(
            text("""
                SELECT
                    COUNT(*) AS bridge_assets,

                    COUNT(p.asset_id) AS twin_profiles,

                    COUNT(r.asset_id) AS report_rows

                FROM
                    public.assets a

                LEFT JOIN
                    public.bridge_digital_twin_profiles p
                ON
                    p.asset_id=a.id

                LEFT JOIN
                    public.bridge_report_readiness r
                ON
                    r.asset_id=a.id

                WHERE
                    UPPER(
                        CAST(
                            a.asset_type
                            AS TEXT
                        )
                    )='BRIDGE'
            """)
        )

        totals = dict(
            result.mappings().one()
        )

        print()
        print("=" * 105)
        print("FINAL STATEWIDE BRIDGE COVERAGE")
        print("=" * 105)

        print(
            f"Canonical bridge assets : "
            f"{totals['bridge_assets']:,}"
        )

        print(
            f"Digital Twin profiles   : "
            f"{totals['twin_profiles']:,}"
        )

        print(
            f"Report readiness rows   : "
            f"{totals['report_rows']:,}"
        )

        print()
        print("VERIFIED ANCHORS:")

        check = await conn.execute(
            text("""
                SELECT
                    a.asset_code,
                    a.name,

                    p.osm_way_id,
                    p.geometry_source,
                    p.rendering_strategy,

                    p.actual_length_m,
                    p.reported_width_m,
                    p.verified_pier_count,

                    r.geometry_status,
                    r.engineering_status

                FROM
                    public.assets a

                LEFT JOIN
                    public.bridge_digital_twin_profiles p
                ON
                    p.asset_id=a.id

                LEFT JOIN
                    public.bridge_report_readiness r
                ON
                    r.asset_id=a.id

                WHERE
                    a.asset_code = ANY(:codes)

                ORDER BY
                    a.asset_code
            """),
            {
                "codes": ANCHORS
            }
        )

        for row in check.mappings():

            print(
                f"{row['asset_code']} | "
                f"{row['name']} | "
                f"osm_way={row['osm_way_id']} | "
                f"geometry={row['geometry_source']} | "
                f"length={row['actual_length_m']} | "
                f"width={row['reported_width_m']} | "
                f"piers={row['verified_pier_count']} | "
                f"{row['geometry_status']}"
            )

        if (
            int(totals["bridge_assets"])
            != int(totals["twin_profiles"])
        ):

            raise RuntimeError(
                "Not every bridge has a Digital Twin profile."
            )

        if (
            int(totals["bridge_assets"])
            != int(totals["report_rows"])
        ):

            raise RuntimeError(
                "Not every bridge has a report readiness row."
            )

        print()
        print(
            "[PASS] ALL BRIDGE ASSETS HAVE DIGITAL TWIN + REPORT RECORDS"
        )

        print("=" * 105)

    await engine.dispose()


asyncio.run(main())
