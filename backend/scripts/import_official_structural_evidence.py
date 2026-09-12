from __future__ import annotations

import argparse
import asyncio
import math
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db


CWC_SOURCE_CODE = "CWC_NDSA"
RAIL_SOURCE_CODE = "INDIAN_RAILWAYS_SCR"

SRISAILAM_ASSET_CODE = "AP_DAM_NWDP_AP01VH0059"

CWC_DOC = {
    "agency": "Central Water Commission / DRIP",
    "title": "3rd Technical Committee of DRIP II - Andhra Pradesh Dam Safety Act Compliance",
    "document_type": "OFFICIAL_TECHNICAL_COMMITTEE_AGENDA",
    "document_url": "https://drip.cwc.gov.in/ecm-includes/Detailed_Agenda_3rd_TC_meeting.pdf",
    "source_record_id": "CWC_DRIP_TC3_AP_COMPLIANCE",
}

RDSO_DOC = {
    "agency": "Research Designs and Standards Organisation, Indian Railways",
    "title": "Bridges and Structures Directorate - BS-108",
    "document_type": "OFFICIAL_RAILWAY_TECHNICAL_REPORT",
    "document_url": "https://rdso.indianrailways.gov.in/uploads/BS-108.pdf",
    "source_record_id": "RDSO_BS108_GODAVARI_248A",
}


def normalize_name(value: str | None) -> str:
    if not value:
        return ""
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    lat1_r = math.radians(lat1)
    lat2_r = math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)

    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1_r)
        * math.cos(lat2_r)
        * math.sin(dlon / 2) ** 2
    )
    return 2 * radius * math.asin(math.sqrt(a))


async def get_source_id(session: AsyncSession, code: str) -> int:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM data_sources
            WHERE code = CAST(:code AS VARCHAR)
            LIMIT 1
            """
        ),
        {"code": code},
    )
    value = result.scalar_one_or_none()

    if value is None:
        raise RuntimeError(
            f"Required data source {code!r} is not registered. "
            "Run register_government_sources.py first."
        )

    return int(value)


async def get_asset_by_code(
    session: AsyncSession,
    asset_code: str,
) -> dict[str, Any] | None:
    result = await session.execute(
        text(
            """
            SELECT
                id,
                asset_code,
                name,
                asset_type,
                district,
                identity_status,
                confidence_score,
                ST_Y(representative_geometry) AS latitude,
                ST_X(representative_geometry) AS longitude
            FROM assets
            WHERE asset_code = CAST(:asset_code AS VARCHAR)
            LIMIT 1
            """
        ),
        {"asset_code": asset_code},
    )

    row = result.mappings().first()
    return dict(row) if row else None


async def godavari_bridge_candidates(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    result = await session.execute(
        text(
            """
            SELECT
                id,
                asset_code,
                name,
                asset_type,
                district,
                identity_status,
                confidence_score,
                ST_Y(representative_geometry) AS latitude,
                ST_X(representative_geometry) AS longitude
            FROM assets
            WHERE asset_type = 'bridge'
              AND (
                    name ILIKE '%Godavari%'
                 OR name ILIKE '%Rajahmundry%'
                 OR name ILIKE '%Rajamahendravaram%'
                 OR name ILIKE '%Kovvur%'
              )
            ORDER BY name, asset_code
            """
        )
    )

    return [dict(row) for row in result.mappings()]


def bridge_candidate_score(asset: dict[str, Any]) -> float:
    name = normalize_name(asset.get("name"))

    if "arch" in name or "bow string" in name:
        return -1000.0

    if "havelock" in name or "old godavari" in name:
        return -1000.0

    score = 0.0

    if name == "godavari bridge":
        score += 100.0

    if "godavari bridge" in name:
        score += 50.0

    if "road cum rail" in name or "rail cum road" in name:
        score += 80.0

    if (
        "rajahmundry" in name
        or "rajamahendravaram" in name
        or "kovvur" in name
    ):
        score += 20.0

    lat = asset.get("latitude")
    lon = asset.get("longitude")

    if lat is not None and lon is not None:
        d = distance_km(float(lat), float(lon), 17.005, 81.781)

        if d <= 5:
            score += 30.0
        elif d <= 15:
            score += 10.0

    confidence = asset.get("confidence_score")
    if confidence is not None:
        score += min(float(confidence), 1.0) * 5.0

    if str(asset.get("identity_status") or "").upper() == "VERIFIED":
        score += 10.0

    return score


async def resolve_godavari_bridge(
    session: AsyncSession,
    explicit_asset_code: str | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    if explicit_asset_code:
        asset = await get_asset_by_code(session, explicit_asset_code)

        if asset is None:
            raise RuntimeError(
                f"Godavari asset code {explicit_asset_code!r} does not exist."
            )

        if asset["asset_type"] != "bridge":
            raise RuntimeError(
                f"{explicit_asset_code!r} is not a bridge asset."
            )

        return asset, [asset]

    candidates = await godavari_bridge_candidates(session)

    ranked = sorted(
        candidates,
        key=bridge_candidate_score,
        reverse=True,
    )

    usable = [
        item
        for item in ranked
        if bridge_candidate_score(item) > 0
    ]

    if not usable:
        return None, candidates

    top = usable[0]
    top_score = bridge_candidate_score(top)

    if len(usable) == 1:
        return top, ranked

    second_score = bridge_candidate_score(usable[1])

    if top_score - second_score < 20:
        return None, ranked

    return top, ranked


async def ensure_source_document(
    session: AsyncSession,
    *,
    source_id: int,
    doc: dict[str, str],
    commit: bool,
) -> int | None:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM source_documents
            WHERE source_id = CAST(:source_id AS INTEGER)
              AND source_record_id = CAST(:source_record_id AS VARCHAR)
            LIMIT 1
            """
        ),
        {
            "source_id": source_id,
            "source_record_id": doc["source_record_id"],
        },
    )

    existing = result.scalar_one_or_none()

    if existing is not None:
        return int(existing)

    if not commit:
        return None

    result = await session.execute(
        text(
            """
            INSERT INTO source_documents (
                source_id,
                agency,
                title,
                document_type,
                document_url,
                source_record_id,
                retrieved_at,
                quality_flag,
                is_authoritative,
                metadata_json,
                created_at,
                updated_at
            )
            VALUES (
                CAST(:source_id AS INTEGER),
                CAST(:agency AS VARCHAR),
                CAST(:title AS VARCHAR),
                CAST(:document_type AS VARCHAR),
                CAST(:document_url AS VARCHAR),
                CAST(:source_record_id AS VARCHAR),
                NOW(),
                'VERIFIED_OFFICIAL_SOURCE',
                TRUE,
                '{}'::jsonb,
                NOW(),
                NOW()
            )
            RETURNING id
            """
        ),
        {
            "source_id": source_id,
            "agency": doc["agency"],
            "title": doc["title"],
            "document_type": doc["document_type"],
            "document_url": doc["document_url"],
            "source_record_id": doc["source_record_id"],
        },
    )

    return int(result.scalar_one())


async def evidence_exists(
    session: AsyncSession,
    *,
    asset_id: int,
    source_id: int,
    field_name: str,
    processing_method: str,
) -> bool:
    result = await session.execute(
        text(
            """
            SELECT id
            FROM official_evidence
            WHERE asset_id = CAST(:asset_id AS INTEGER)
              AND source_id = CAST(:source_id AS INTEGER)
              AND field_name = CAST(:field_name AS VARCHAR)
              AND COALESCE(processing_method, '') =
                  CAST(:processing_method AS VARCHAR)
            LIMIT 1
            """
        ),
        {
            "asset_id": asset_id,
            "source_id": source_id,
            "field_name": field_name,
            "processing_method": processing_method,
        },
    )

    return result.scalar_one_or_none() is not None


async def insert_evidence(
    session: AsyncSession,
    *,
    asset_id: int,
    document_id: int,
    source_id: int,
    evidence_type: str,
    field_name: str,
    numeric_value: float | None = None,
    text_value: str | None = None,
    unit: str | None = None,
    rating_system: str | None = None,
    authority_level: str,
    origin: str,
    quality_flag: str,
    confidence_score: float,
    is_official: bool,
    is_derived: bool,
    processing_method: str,
    commit: bool,
) -> bool:
    if await evidence_exists(
        session,
        asset_id=asset_id,
        source_id=source_id,
        field_name=field_name,
        processing_method=processing_method,
    ):
        return False

    if not commit:
        return False

    result = await session.execute(
        text(
            """
            INSERT INTO official_evidence (
                asset_id,
                document_id,
                source_id,
                evidence_type,
                field_name,
                numeric_value,
                text_value,
                unit,
                rating_system,
                observed_at,
                authority_level,
                origin,
                quality_flag,
                confidence_score,
                is_official,
                is_derived,
                is_synthetic,
                processing_method,
                extraction_metadata,
                created_at,
                updated_at
            )
            VALUES (
                CAST(:asset_id AS INTEGER),
                CAST(:document_id AS INTEGER),
                CAST(:source_id AS INTEGER),
                CAST(:evidence_type AS VARCHAR),
                CAST(:field_name AS VARCHAR),
                CAST(:numeric_value AS DOUBLE PRECISION),
                CAST(:text_value AS VARCHAR),
                CAST(:unit AS VARCHAR),
                CAST(:rating_system AS VARCHAR),
                NULL,
                CAST(:authority_level AS VARCHAR),
                CAST(:origin AS VARCHAR),
                CAST(:quality_flag AS VARCHAR),
                CAST(:confidence_score AS DOUBLE PRECISION),
                CAST(:is_official AS BOOLEAN),
                CAST(:is_derived AS BOOLEAN),
                FALSE,
                CAST(:processing_method AS VARCHAR),
                '{}'::jsonb,
                NOW(),
                NOW()
            )
            RETURNING id
            """
        ),
        {
            "asset_id": asset_id,
            "document_id": document_id,
            "source_id": source_id,
            "evidence_type": evidence_type,
            "field_name": field_name,
            "numeric_value": numeric_value,
            "text_value": text_value,
            "unit": unit,
            "rating_system": rating_system,
            "authority_level": authority_level,
            "origin": origin,
            "quality_flag": quality_flag,
            "confidence_score": confidence_score,
            "is_official": is_official,
            "is_derived": is_derived,
            "processing_method": processing_method,
        },
    )

    return result.scalar_one_or_none() is not None


async def import_srisailam(
    session: AsyncSession,
    *,
    source_id: int,
    commit: bool,
) -> dict[str, int]:
    stats = {
        "prepared": 0,
        "inserted": 0,
        "skipped": 0,
    }

    asset = await get_asset_by_code(
        session,
        SRISAILAM_ASSET_CODE,
    )

    if asset is None:
        print("SRISAILAM: asset not found; skipping.")
        return stats

    print(
        "SRISAILAM:",
        asset["asset_code"],
        "|",
        asset["name"],
        "|",
        asset["identity_status"],
    )

    document_id = await ensure_source_document(
        session,
        source_id=source_id,
        doc=CWC_DOC,
        commit=commit,
    )

    records = [
        {
            "evidence_type": "DAM_SAFETY_GOVERNANCE",
            "field_name": "emergency_action_plan_status",
            "text_value": "PREPARED_AND_SUBMITTED_TO_CWC",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "CWC_DRIP_TC3_EXPLICIT_STATEMENT",
        },
    ]

    for record in records:
        stats["prepared"] += 1

        if not commit:
            print(
                "  PREPARED:",
                record["field_name"],
                "=",
                record["text_value"],
            )
            continue

        assert document_id is not None

        inserted = await insert_evidence(
            session,
            asset_id=int(asset["id"]),
            document_id=document_id,
            source_id=source_id,
            evidence_type=record["evidence_type"],
            field_name=record["field_name"],
            text_value=record["text_value"],
            authority_level=record["authority_level"],
            origin=record["origin"],
            quality_flag=record["quality_flag"],
            confidence_score=record["confidence_score"],
            is_official=record["is_official"],
            is_derived=record["is_derived"],
            processing_method=record["processing_method"],
            commit=commit,
        )

        if inserted:
            stats["inserted"] += 1
        else:
            stats["skipped"] += 1

    return stats


async def import_godavari_bridge(
    session: AsyncSession,
    *,
    source_id: int,
    commit: bool,
    explicit_asset_code: str | None,
) -> dict[str, int]:
    stats = {
        "prepared": 0,
        "inserted": 0,
        "skipped": 0,
    }

    asset, candidates = await resolve_godavari_bridge(
        session,
        explicit_asset_code,
    )

    print()
    print("GODAVARI BRIDGE CANDIDATES:")

    for candidate in candidates[:20]:
        print(
            " ",
            candidate["asset_code"],
            "|",
            candidate["name"],
            "|",
            candidate["district"],
            "| identity=",
            candidate["identity_status"],
            "| score=",
            round(bridge_candidate_score(candidate), 2),
        )

    if asset is None:
        print()
        print(
            "GODAVARI: no unambiguous rail-cum-road bridge identity. "
            "RDSO evidence will NOT be attached."
        )
        print(
            "Re-run with --godavari-asset-code <EXACT_ASSET_CODE> "
            "after reviewing the candidates."
        )
        return stats

    print()
    print(
        "GODAVARI SELECTED:",
        asset["asset_code"],
        "|",
        asset["name"],
        "|",
        asset["identity_status"],
    )

    document_id = await ensure_source_document(
        session,
        source_id=source_id,
        doc=RDSO_DOC,
        commit=commit,
    )

    records = [
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_91_4m_deflection_status",
            "text_value": "WITHIN_PERMISSIBLE_LIMIT",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_91_4m_superstructure_stress_status",
            "text_value": "WITHIN_PERMISSIBLE_LIMIT",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_91_4m_pier_settlement_status",
            "text_value": "NO_SETTLEMENT_RECORDED",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_91_4m_pier_tilt",
            "numeric_value": 0.038,
            "unit": "degree",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_45_7m_deflection_status",
            "text_value": "WITHIN_PERMISSIBLE_LIMIT",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_45_7m_superstructure_stress_status",
            "text_value": "WITHIN_PERMISSIBLE_LIMIT",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_45_7m_pier_settlement_status",
            "text_value": "NO_SETTLEMENT_RECORDED",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "span_45_7m_pier_tilt",
            "numeric_value": 0.031,
            "unit": "degree",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "RDSO_INSTRUMENTATION",
            "field_name": "fatigue_life_status",
            "text_value": "NOT_MEASURED",
            "authority_level": "A1",
            "origin": "OBSERVED",
            "quality_flag": "OFFICIAL_DOCUMENT",
            "confidence_score": 0.95,
            "is_official": True,
            "is_derived": False,
            "processing_method": "RDSO_BS108_DIRECT_FINDING",
        },
        {
            "evidence_type": "STRUCTURAL_STATE",
            "field_name": "official_condition",
            "text_value": "MONITOR",
            "rating_system": "SIMRAS_RDSO_CONSERVATIVE_DERIVATION_V1",
            "authority_level": "A1",
            "origin": "DERIVED_FROM_OFFICIAL",
            "quality_flag": "DERIVED_FROM_OFFICIAL_RDSO",
            "confidence_score": 0.85,
            "is_official": False,
            "is_derived": True,
            "processing_method": "SIMRAS_RDSO_WITHIN_LIMITS_FATIGUE_UNMEASURED_V1",
        },
    ]

    for record in records:
        stats["prepared"] += 1

        if not commit:
            print(
                "  PREPARED:",
                record["field_name"],
                "=",
                record.get(
                    "text_value",
                    record.get("numeric_value"),
                ),
                "| origin=",
                record["origin"],
            )
            continue

        assert document_id is not None

        inserted = await insert_evidence(
            session,
            asset_id=int(asset["id"]),
            document_id=document_id,
            source_id=source_id,
            evidence_type=record["evidence_type"],
            field_name=record["field_name"],
            numeric_value=record.get("numeric_value"),
            text_value=record.get("text_value"),
            unit=record.get("unit"),
            rating_system=record.get("rating_system"),
            authority_level=record["authority_level"],
            origin=record["origin"],
            quality_flag=record["quality_flag"],
            confidence_score=record["confidence_score"],
            is_official=record["is_official"],
            is_derived=record["is_derived"],
            processing_method=record["processing_method"],
            commit=commit,
        )

        if inserted:
            stats["inserted"] += 1
        else:
            stats["skipped"] += 1

    return stats


async def main() -> None:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--commit",
        action="store_true",
        help="Commit official structural evidence to PostgreSQL.",
    )

    parser.add_argument(
        "--godavari-asset-code",
        default=None,
        help=(
            "Exact canonical asset code for RDSO Bridge No. 248A. "
            "Use this when multiple Godavari bridge candidates exist."
        ),
    )

    args = parser.parse_args()

    async for session in get_db():
        print("=" * 72)
        print("SIMRAS OFFICIAL STRUCTURAL EVIDENCE IMPORTER")
        print("=" * 72)
        print("MODE:", "COMMIT" if args.commit else "DRY RUN")
        print()

        cwc_source_id = await get_source_id(
            session,
            CWC_SOURCE_CODE,
        )

        rail_source_id = await get_source_id(
            session,
            RAIL_SOURCE_CODE,
        )

        srisailam_stats = await import_srisailam(
            session,
            source_id=cwc_source_id,
            commit=args.commit,
        )

        godavari_stats = await import_godavari_bridge(
            session,
            source_id=rail_source_id,
            commit=args.commit,
            explicit_asset_code=args.godavari_asset_code,
        )

        if args.commit:
            await session.commit()
            print()
            print("DATABASE COMMIT COMPLETE")
        else:
            await session.rollback()
            print()
            print("DRY RUN COMPLETE - DATABASE NOT MODIFIED")

        print()
        print("=== SUMMARY ===")
        print("Srisailam:", srisailam_stats)
        print("Godavari :", godavari_stats)

        break


if __name__ == "__main__":
    asyncio.run(main())
