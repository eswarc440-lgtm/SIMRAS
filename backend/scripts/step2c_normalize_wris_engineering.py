from __future__ import annotations

import os
import re
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


ROOT = Path("/app")

OUT_CSV = (
    ROOT
    / "data"
    / "processed"
    / "dam_barrage"
    / "AP_DAM_BARRAGE_ENGINEERING_FEATURES.csv"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP2C_ENGINEERING_EVIDENCE_REPORT.json"
)

REPORT_TXT = (
    ROOT
    / "reports"
    / "STEP2C_ENGINEERING_EVIDENCE_REPORT.txt"
)

lines = []


def log(x=""):
    print(x, flush=True)
    lines.append(str(x))


def num(value):
    if value is None:
        return None

    s = str(value).strip()

    if not s:
        return None

    # Preserve the first valid numeric component.
    match = re.search(r"-?\d+(?:\.\d+)?", s)

    if not match:
        return None

    try:
        return float(match.group())
    except Exception:
        return None


def integer(value):
    v = num(value)

    if v is None:
        return None

    try:
        return int(round(v))
    except Exception:
        return None


def year(value):
    v = integer(value)

    if v is None:
        return None

    if 1800 <= v <= 2035:
        return v

    return None


async def main():

    url = (
        os.getenv("DATABASE_URL")
        or os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("POSTGRES_URL")
    )

    if not url:
        raise RuntimeError("DATABASE_URL not available")

    if url.startswith("postgresql://"):
        url = url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    engine = create_async_engine(
        url,
        pool_pre_ping=True
    )

    log("=" * 110)
    log("SIMRAS STEP 2C - NORMALIZE WRIS ENGINEERING EVIDENCE")
    log("=" * 110)

    async with engine.begin() as conn:

        # ----------------------------------------------------------
        # ASSET SCHEMA
        # ----------------------------------------------------------

        asset_cols = {
            r[0]
            for r in (
                await conn.execute(text("""
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_schema='public'
                      AND table_name='assets'
                """))
            )
        }

        type_col = next(
            (
                x for x in [
                    "asset_type",
                    "type",
                    "infrastructure_type"
                ]
                if x in asset_cols
            ),
            None
        )

        if not type_col:
            raise RuntimeError("Asset type column not found")

        wanted = [
            x for x in [
                "id",
                "asset_code",
                "name",
                type_col,
                "built_year",
                "latitude",
                "longitude",
                "district"
            ]
            if x in asset_cols
        ]

        qcols = ",".join(
            f'"{x}"'
            for x in wanted
        )

        assets = [
            dict(r)
            for r in (
                await conn.execute(text(f"""
                    SELECT {qcols}
                    FROM public.assets
                    WHERE UPPER(CAST("{type_col}" AS TEXT))
                          IN ('DAM','BARRAGE')
                """))
            ).mappings()
        ]

        assets_by_id = {
            a["id"]: a
            for a in assets
        }

        log("")
        log(f"Dam/barrage assets: {len(assets)}")

        # ----------------------------------------------------------
        # LOAD OFFICIAL EVIDENCE
        # ----------------------------------------------------------

        rows = (
            await conn.execute(text("""
                SELECT
                    id,
                    asset_id,
                    document_id,
                    source_id,
                    evidence_type,
                    field_name,
                    text_value,
                    authority_level,
                    origin,
                    quality_flag,
                    confidence_score,
                    is_official,
                    is_derived,
                    is_synthetic,
                    extraction_metadata
                FROM public.official_evidence
                WHERE asset_id IS NOT NULL
                  AND COALESCE(is_synthetic,false)=false
            """))
        ).mappings().all()

        normalized = []

        for row in rows:

            aid = row["asset_id"]

            asset = assets_by_id.get(aid)

            if not asset:
                continue

            metadata = row.get(
                "extraction_metadata"
            )

            if not isinstance(metadata, dict):
                continue

            props = metadata.get(
                "properties",
                {}
            )

            if not isinstance(props, dict):
                continue

            # WRIS fields.
            completion_year = year(
                props.get("dm_cmp_yr")
            )

            commencement_year = year(
                props.get("dm_cmn_yr")
            )

            dam_height_m = num(
                props.get("dm_height")
            )

            dam_length_m = num(
                props.get("dm_length")
            )

            dam_volume = num(
                props.get("dam_vol")
            )

            gate_count = integer(
                props.get("dm_gate_no")
            )

            design_flood = num(
                props.get("dm_flod_des")
            )

            spillway_capacity = num(
                props.get("dm_spil_cap")
            )

            spillway_level = num(
                props.get("dm_spil_lev")
            )

            spillway_length = num(
                props.get("dm_spil_leng")
            )

            river = props.get("rivcode")
            dam_type = props.get("dm_type")
            seismic_zone = props.get("dm_ses_zone")
            gate_type = props.get("dm_gate_type")
            spillway_type = props.get("dm_spil_type")
            status = props.get("dm_status")
            nrld_no = props.get("nrld_no")
            structure_code = props.get("strucode")
            gate_size = props.get("dm_gate_sz")
            city = props.get("dm_ncity")
            operating_agency = props.get(
                "dm_oper_main_age"
            )

            useful = any(
                value is not None
                for value in [
                    completion_year,
                    commencement_year,
                    dam_height_m,
                    dam_length_m,
                    gate_count,
                    design_flood,
                    spillway_capacity,
                    spillway_level,
                    dam_type,
                    seismic_zone,
                    river,
                    nrld_no,
                    structure_code
                ]
            )

            if not useful:
                continue

            normalized.append({
                "asset_id": aid,
                "asset_code": asset.get("asset_code"),
                "asset_name": asset.get("name"),
                "asset_type": asset.get(type_col),

                "document_id": row.get("document_id"),
                "source_id": row.get("source_id"),
                "evidence_id": row.get("id"),

                "completion_year": completion_year,
                "commencement_year": commencement_year,

                "dam_height_m": dam_height_m,
                "dam_length_m": dam_length_m,
                "dam_volume_source_value": dam_volume,

                "gate_count": gate_count,
                "gate_size_raw": gate_size,
                "gate_type": gate_type,

                "design_flood_source_value": design_flood,
                "spillway_capacity_source_value": spillway_capacity,
                "spillway_level_m": spillway_level,
                "spillway_length_m": spillway_length,
                "spillway_type": spillway_type,

                "river_name": river,
                "dam_type": dam_type,
                "seismic_zone": seismic_zone,
                "registry_status": status,

                "nrld_no": nrld_no,
                "structure_code": structure_code,
                "nearest_city": city,
                "operating_agency": operating_agency,

                "authority_level": row.get("authority_level"),
                "origin": row.get("origin"),
                "quality_flag": row.get("quality_flag"),
                "confidence_score": row.get("confidence_score"),
                "is_official": row.get("is_official"),
                "is_derived": row.get("is_derived"),
            })

        df = pd.DataFrame(normalized)

        if df.empty:
            raise RuntimeError(
                "No usable WRIS engineering evidence extracted."
            )

        # ----------------------------------------------------------
        # KEEP BEST EVIDENCE ROW PER ASSET
        # ----------------------------------------------------------

        df["confidence_sort"] = pd.to_numeric(
            df["confidence_score"],
            errors="coerce"
        ).fillna(0)

        df = (
            df.sort_values(
                [
                    "asset_id",
                    "confidence_sort"
                ],
                ascending=[
                    True,
                    False
                ]
            )
            .drop_duplicates(
                "asset_id",
                keep="first"
            )
            .drop(
                columns=["confidence_sort"]
            )
        )

        # ----------------------------------------------------------
        # DIRECT HYDROLOGY COVERAGE
        # ----------------------------------------------------------

        hydrology_assets = set()

        tables = {
            r[0]
            for r in (
                await conn.execute(text("""
                    SELECT table_name
                    FROM information_schema.tables
                    WHERE table_schema='public'
                """))
            )
        }

        if "asset_hydrology_source_matches" in tables:

            hydrology_assets = {
                int(r[0])
                for r in (
                    await conn.execute(text("""
                        SELECT DISTINCT asset_id
                        FROM public.asset_hydrology_source_matches
                        WHERE asset_id IS NOT NULL
                          AND match_status IN (
                              'MATCHED_HIGH',
                              'MATCHED_REVIEW'
                          )
                    """))
                )
                if r[0] is not None
            }

        df["has_direct_hydrology"] = (
            df["asset_id"]
            .isin(hydrology_assets)
        )

        # ----------------------------------------------------------
        # DERIVED AGE
        # ----------------------------------------------------------

        current_year = datetime.now(
            timezone.utc
        ).year

        df["age_years"] = (
            current_year
            - pd.to_numeric(
                df["completion_year"],
                errors="coerce"
            )
        )

        df.loc[
            (
                df["age_years"] < 0
            )
            |
            (
                df["age_years"] > 300
            ),
            "age_years"
        ] = None

        # ----------------------------------------------------------
        # COMPLETENESS SCORE
        # ----------------------------------------------------------

        engineering_fields = [
            "completion_year",
            "dam_height_m",
            "dam_length_m",
            "gate_count",
            "design_flood_source_value",
            "spillway_capacity_source_value",
            "spillway_level_m",
            "river_name",
            "dam_type",
            "seismic_zone"
        ]

        df["engineering_fields_available"] = (
            df[engineering_fields]
            .notna()
            .sum(axis=1)
        )

        df["engineering_completeness"] = (
            df["engineering_fields_available"]
            / len(engineering_fields)
        ).round(3)

        # ----------------------------------------------------------
        # CREATE NORMALIZED EVIDENCE TABLE
        # ----------------------------------------------------------

        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS
            public.asset_engineering_evidence_normalized
            (
                asset_id BIGINT PRIMARY KEY,
                asset_code TEXT,
                asset_name TEXT,
                asset_type TEXT,

                document_id BIGINT,
                source_id BIGINT,
                evidence_id BIGINT,

                completion_year INTEGER,
                commencement_year INTEGER,

                dam_height_m DOUBLE PRECISION,
                dam_length_m DOUBLE PRECISION,
                dam_volume_source_value DOUBLE PRECISION,

                gate_count INTEGER,
                gate_size_raw TEXT,
                gate_type TEXT,

                design_flood_source_value DOUBLE PRECISION,
                spillway_capacity_source_value DOUBLE PRECISION,
                spillway_level_m DOUBLE PRECISION,
                spillway_length_m DOUBLE PRECISION,
                spillway_type TEXT,

                river_name TEXT,
                dam_type TEXT,
                seismic_zone TEXT,
                registry_status TEXT,

                nrld_no TEXT,
                structure_code TEXT,
                nearest_city TEXT,
                operating_agency TEXT,

                age_years DOUBLE PRECISION,

                engineering_fields_available INTEGER,
                engineering_completeness DOUBLE PRECISION,

                has_direct_hydrology BOOLEAN,

                authority_level TEXT,
                origin TEXT,
                quality_flag TEXT,
                confidence_score DOUBLE PRECISION,

                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))

        await conn.execute(text("""
            TRUNCATE TABLE
            public.asset_engineering_evidence_normalized
        """))

        insert_sql = text("""
            INSERT INTO
            public.asset_engineering_evidence_normalized
            (
                asset_id,
                asset_code,
                asset_name,
                asset_type,

                document_id,
                source_id,
                evidence_id,

                completion_year,
                commencement_year,

                dam_height_m,
                dam_length_m,
                dam_volume_source_value,

                gate_count,
                gate_size_raw,
                gate_type,

                design_flood_source_value,
                spillway_capacity_source_value,
                spillway_level_m,
                spillway_length_m,
                spillway_type,

                river_name,
                dam_type,
                seismic_zone,
                registry_status,

                nrld_no,
                structure_code,
                nearest_city,
                operating_agency,

                age_years,

                engineering_fields_available,
                engineering_completeness,

                has_direct_hydrology,

                authority_level,
                origin,
                quality_flag,
                confidence_score
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,
                :asset_type,

                :document_id,
                :source_id,
                :evidence_id,

                :completion_year,
                :commencement_year,

                :dam_height_m,
                :dam_length_m,
                :dam_volume_source_value,

                :gate_count,
                :gate_size_raw,
                :gate_type,

                :design_flood_source_value,
                :spillway_capacity_source_value,
                :spillway_level_m,
                :spillway_length_m,
                :spillway_type,

                :river_name,
                :dam_type,
                :seismic_zone,
                :registry_status,

                :nrld_no,
                :structure_code,
                :nearest_city,
                :operating_agency,

                :age_years,

                :engineering_fields_available,
                :engineering_completeness,

                :has_direct_hydrology,

                :authority_level,
                :origin,
                :quality_flag,
                :confidence_score
            )
        """)

        for row in df.to_dict(
            orient="records"
        ):

            cleaned = {}

            for k, v in row.items():

                if pd.isna(v):
                    cleaned[k] = None
                elif hasattr(v, "item"):
                    cleaned[k] = v.item()
                else:
                    cleaned[k] = v

            await conn.execute(
                insert_sql,
                cleaned
            )

        # ----------------------------------------------------------
        # SAFE BUILT-YEAR BACKFILL
        # ----------------------------------------------------------

        built_year_updates = 0

        if "built_year" in asset_cols:

            result = await conn.execute(text("""
                UPDATE public.assets a
                SET built_year = e.completion_year
                FROM public.asset_engineering_evidence_normalized e
                WHERE a.id = e.asset_id
                  AND a.built_year IS NULL
                  AND e.completion_year BETWEEN 1800 AND 2035
                RETURNING a.id
            """))

            built_year_updates = len(
                result.fetchall()
            )

        # ----------------------------------------------------------
        # EXPORT
        # ----------------------------------------------------------

        df.to_csv(
            OUT_CSV,
            index=False
        )

        total_assets = len(assets)
        evidence_assets = len(df)

        coverage = (
            evidence_assets
            / total_assets
            * 100
            if total_assets
            else 0
        )

        with_year = int(
            df["completion_year"]
            .notna()
            .sum()
        )

        with_height = int(
            df["dam_height_m"]
            .notna()
            .sum()
        )

        with_length = int(
            df["dam_length_m"]
            .notna()
            .sum()
        )

        with_gate = int(
            df["gate_count"]
            .notna()
            .sum()
        )

        with_flood = int(
            df[
                "design_flood_source_value"
            ]
            .notna()
            .sum()
        )

        with_spillway = int(
            df[
                "spillway_capacity_source_value"
            ]
            .notna()
            .sum()
        )

        with_seismic = int(
            df["seismic_zone"]
            .notna()
            .sum()
        )

        direct_hydrology = int(
            df[
                "has_direct_hydrology"
            ]
            .sum()
        )

        report = {
            "generated_at":
                datetime.now(
                    timezone.utc
                ).isoformat(),

            "total_dam_barrage_assets":
                total_assets,

            "assets_with_normalized_engineering_evidence":
                evidence_assets,

            "engineering_evidence_coverage_percent":
                round(
                    coverage,
                    2
                ),

            "completion_year_assets":
                with_year,

            "height_assets":
                with_height,

            "length_assets":
                with_length,

            "gate_count_assets":
                with_gate,

            "design_flood_assets":
                with_flood,

            "spillway_capacity_assets":
                with_spillway,

            "seismic_zone_assets":
                with_seismic,

            "assets_with_direct_hydrology":
                direct_hydrology,

            "built_year_updates":
                built_year_updates,

            "database_table":
                "asset_engineering_evidence_normalized"
        }

        REPORT_JSON.write_text(
            json.dumps(
                report,
                indent=2
            ),
            encoding="utf-8"
        )

        log("")
        log("=" * 110)
        log("STEP 2C RESULT")
        log("=" * 110)

        log(
            f"Total dams+barrages              : "
            f"{total_assets}"
        )

        log(
            f"Engineering evidence assets      : "
            f"{evidence_assets}"
        )

        log(
            f"Engineering evidence coverage    : "
            f"{coverage:.2f}%"
        )

        log(
            f"Completion year available        : "
            f"{with_year}"
        )

        log(
            f"Height available                 : "
            f"{with_height}"
        )

        log(
            f"Length available                 : "
            f"{with_length}"
        )

        log(
            f"Gate count available             : "
            f"{with_gate}"
        )

        log(
            f"Design flood available           : "
            f"{with_flood}"
        )

        log(
            f"Spillway capacity available      : "
            f"{with_spillway}"
        )

        log(
            f"Seismic zone available           : "
            f"{with_seismic}"
        )

        log(
            f"Direct hydrology assets          : "
            f"{direct_hydrology}"
        )

        log(
            f"assets.built_year backfilled     : "
            f"{built_year_updates}"
        )

        log("")
        log(
            "Database table:"
        )
        log(
            "public.asset_engineering_evidence_normalized"
        )

        log("=" * 110)

        REPORT_TXT.write_text(
            "\n".join(lines),
            encoding="utf-8"
        )

    await engine.dispose()


asyncio.run(main())
