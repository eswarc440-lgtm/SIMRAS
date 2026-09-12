from __future__ import annotations

import asyncio
import hashlib
import json
import re
from difflib import SequenceMatcher
from pathlib import Path

from sqlalchemy import select, text

from app.db.session import get_db
from app.models.entities import DataSource


ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = ROOT / "data" / "raw" / "wris"

DAM_FILE = DATA_DIR / "WRIS_Dams.geojsonl"
ANICUT_FILE = DATA_DIR / "WRIS_Anicuts.geojsonl"


SOURCE_CODE = "INDIA_WRIS_MIRROR"

SOURCE_NAME = (
    "India-WRIS water structures via indian_water_features"
)

SOURCE_ORGANISATION = (
    "India-WRIS / NWIC data republished by indian_water_features"
)


def normalize_name(value: str | None) -> str:
    if not value:
        return ""

    value = value.lower()

    value = value.replace("&", " and ")

    value = re.sub(
        r"\b(project|reservoir|dam|barrage|anicut|weir)\b",
        " ",
        value,
    )

    value = re.sub(
        r"[^a-z0-9]+",
        " ",
        value,
    )

    return " ".join(
        value.split()
    )


def similarity(
    first: str | None,
    second: str | None,
) -> float:
    a = normalize_name(first)
    b = normalize_name(second)

    if not a or not b:
        return 0.0

    if a == b:
        return 1.0

    return SequenceMatcher(
        None,
        a,
        b,
    ).ratio()


def integer_year(
    value,
) -> int | None:
    if value is None:
        return None

    try:
        year = int(
            str(value).strip()
        )

        if 1800 <= year <= 2100:
            return year

    except Exception:
        pass

    return None


def status_value(
    value: str | None,
) -> str:
    normalized = (
        value or ""
    ).strip().lower()

    if normalized == "completed":
        return "ACTIVE"

    if "construction" in normalized:
        return "CONSTRUCTION"

    if "proposed" in normalized:
        return "PROPOSED"

    return "UNKNOWN"


def clean_code(
    value: str,
) -> str:
    return re.sub(
        r"[^A-Za-z0-9]+",
        "_",
        value,
    ).strip("_").upper()


def sha256_file(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for block in iter(
            lambda: handle.read(
                1024 * 1024
            ),
            b"",
        ):
            digest.update(block)

    return digest.hexdigest()


def load_ap_records(
    path: Path,
) -> list[dict]:

    result: list[dict] = []

    with path.open(
        encoding="utf-8",
    ) as handle:

        for line in handle:

            if not line.strip():
                continue

            record = json.loads(
                line
            )

            props = record.get(
                "properties",
                {},
            )

            if props.get("state") != "AP":
                continue

            geometry = record.get(
                "geometry",
                {},
            )

            coordinates = geometry.get(
                "coordinates",
            )

            if (
                geometry.get("type") != "Point"
                or not coordinates
                or len(coordinates) < 2
            ):
                continue

            lon = float(
                coordinates[0]
            )

            lat = float(
                coordinates[1]
            )

            if not (
                76.0 <= lon <= 85.5
                and 12.0 <= lat <= 20.5
            ):
                continue

            result.append(
                record
            )

    return result


async def get_source(
    session,
) -> DataSource:

    source = await session.scalar(
        select(DataSource).where(
            DataSource.code
            == SOURCE_CODE
        )
    )

    if source is not None:
        return source

    source = DataSource(
        code=SOURCE_CODE,
        name=SOURCE_NAME,
        organisation=SOURCE_ORGANISATION,
        source_type="GOVERNMENT_DERIVED_MIRROR",
        refresh_policy="Monthly verification against India-WRIS",
        is_authoritative=False,
    )

    session.add(
        source
    )

    await session.flush()

    return source


async def get_or_create_document(
    session,
    source_id: int,
    *,
    source_record_id: str,
    title: str,
    path: Path,
) -> int:

    existing = await session.execute(
        text(
            """
            SELECT id
            FROM source_documents
            WHERE source_id = :source_id
              AND source_record_id = :record_id
            LIMIT 1
            """
        ),
        {
            "source_id": source_id,
            "record_id": source_record_id,
        },
    )

    row = existing.first()

    if row is not None:
        return int(
            row.id
        )

    checksum = sha256_file(
        path
    )

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
                published_at,
                retrieved_at,
                checksum,
                licence,
                raw_uri,
                metadata_json,
                quality_flag,
                is_authoritative,
                created_at,
                updated_at
            )
            VALUES (
                :source_id,
                :agency,
                :title,
                'DATASET_RELEASE',
                :url,
                :record_id,
                NULL,
                NOW(),
                :checksum,
                :licence,
                :raw_uri,
                CAST(:metadata AS jsonb),
                'SOURCE_PRESERVED',
                FALSE,
                NOW(),
                NOW()
            )
            RETURNING id
            """
        ),
        {
            "source_id": source_id,
            "agency": SOURCE_ORGANISATION,
            "title": title,
            "url": (
                "https://github.com/"
                "ramSeraph/"
                "indian_water_features/"
                "releases"
            ),
            "record_id": source_record_id,
            "checksum": checksum,
            "licence": (
                "Retain India-WRIS/original government "
                "source attribution and verify release terms "
                "before publication"
            ),
            "raw_uri": str(
                path
            ),
            "metadata": json.dumps(
                {
                    "original_source": "India-WRIS",
                    "state_filter": "AP",
                    "mirror": (
                        "ramSeraph/"
                        "indian_water_features"
                    ),
                }
            ),
        },
    )

    return int(
        result.scalar_one()
    )


async def existing_identifier_asset(
    session,
    *,
    source_id: int,
    external_id: str,
) -> int | None:

    result = await session.execute(
        text(
            """
            SELECT asset_id
            FROM asset_identifiers
            WHERE source_id = :source_id
              AND external_id = :external_id
            LIMIT 1
            """
        ),
        {
            "source_id": source_id,
            "external_id": external_id,
        },
    )

    value = result.scalar_one_or_none()

    return (
        int(value)
        if value is not None
        else None
    )


async def nearby_candidates(
    session,
    *,
    asset_type: str,
    lon: float,
    lat: float,
) -> list[dict]:

    result = await session.execute(
        text(
            """
            SELECT
                id,
                asset_code,
                name,
                district,
                identity_status,
                ST_DistanceSphere(
                    representative_geometry,
                    ST_SetSRID(
                        ST_MakePoint(
                            :lon,
                            :lat
                        ),
                        4326
                    )
                ) AS distance_m
            FROM assets
            WHERE asset_type = :asset_type
              AND ST_DWithin(
                    representative_geometry::geography,
                    ST_SetSRID(
                        ST_MakePoint(
                            :lon,
                            :lat
                        ),
                        4326
                    )::geography,
                    10000
              )
            ORDER BY distance_m
            LIMIT 10
            """
        ),
        {
            "asset_type": asset_type,
            "lon": lon,
            "lat": lat,
        },
    )

    return [
        dict(row._mapping)
        for row in result
    ]


async def resolve_asset(
    session,
    *,
    source_id: int,
    external_id: str,
    external_name: str,
    asset_type: str,
    lon: float,
    lat: float,
) -> tuple[
    int | None,
    str,
    float,
]:

    by_identifier = (
        await existing_identifier_asset(
            session,
            source_id=source_id,
            external_id=external_id,
        )
    )

    if by_identifier is not None:
        return (
            by_identifier,
            "EXTERNAL_ID",
            1.0,
        )

    candidates = (
        await nearby_candidates(
            session,
            asset_type=asset_type,
            lon=lon,
            lat=lat,
        )
    )

    best = None
    best_score = 0.0

    for candidate in candidates:

        name_score = similarity(
            external_name,
            candidate["name"],
        )

        distance = float(
            candidate["distance_m"]
            or 999999
        )

        if (
            name_score == 1.0
            and distance <= 10000
        ):
            score = 0.95

        elif (
            name_score >= 0.82
            and distance <= 3000
        ):
            score = (
                0.70
                + name_score * 0.20
                + max(
                    0,
                    1 - distance / 3000,
                )
                * 0.10
            )

        else:
            score = 0.0

        if score > best_score:
            best_score = score
            best = candidate

    if (
        best is not None
        and best_score >= 0.85
    ):
        return (
            int(best["id"]),
            "NAME_SPATIAL",
            round(
                best_score,
                3,
            ),
        )

    return (
        None,
        "NEW_SOURCE_RECORD",
        0.80,
    )


async def ensure_identifier(
    session,
    *,
    asset_id: int,
    source_id: int,
    external_id: str,
    external_name: str,
    method: str,
    confidence: float,
) -> None:

    existing = await session.execute(
        text(
            """
            SELECT id
            FROM asset_identifiers
            WHERE source_id = :source_id
              AND external_id = :external_id
            LIMIT 1
            """
        ),
        {
            "source_id": source_id,
            "external_id": external_id,
        },
    )

    if existing.first():
        return

    await session.execute(
        text(
            """
            INSERT INTO asset_identifiers (
                asset_id,
                source_id,
                external_id,
                external_name,
                match_method,
                match_confidence
            )
            VALUES (
                :asset_id,
                :source_id,
                :external_id,
                :external_name,
                :method,
                :confidence
            )
            """
        ),
        {
            "asset_id": asset_id,
            "source_id": source_id,
            "external_id": external_id,
            "external_name": external_name,
            "method": method,
            "confidence": confidence,
        },
    )


async def ensure_registry_evidence(
    session,
    *,
    asset_id: int,
    document_id: int,
    source_id: int,
    name: str,
    properties: dict,
    geometry: dict,
) -> None:

    existing = await session.execute(
        text(
            """
            SELECT id
            FROM official_evidence
            WHERE asset_id = :asset_id
              AND document_id = :document_id
              AND field_name = 'wris_registry_record'
            LIMIT 1
            """
        ),
        {
            "asset_id": asset_id,
            "document_id": document_id,
        },
    )

    if existing.first():
        return

    metadata = {
        "properties": properties,
        "geometry": geometry,
    }

    await session.execute(
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
                valid_from,
                valid_to,
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
                :asset_id,
                :document_id,
                :source_id,
                'ASSET_REGISTRY',
                'wris_registry_record',
                NULL,
                :name,
                NULL,
                NULL,
                NULL,
                NULL,
                NULL,
                'B2',
                'GOVERNMENT_DERIVED_MIRROR',
                'SOURCE_PRESERVED',
                0.80,
                FALSE,
                FALSE,
                FALSE,
                'AP state filter + external ID + spatial/name resolution',
                CAST(:metadata AS jsonb),
                NOW(),
                NOW()
            )
            """
        ),
        {
            "asset_id": asset_id,
            "document_id": document_id,
            "source_id": source_id,
            "name": name,
            "metadata": json.dumps(
                metadata
            ),
        },
    )


async def create_asset(
    session,
    *,
    source_id: int,
    asset_code: str,
    name: str,
    asset_type: str,
    subtype: str | None,
    district: str | None,
    owner: str | None,
    status: str,
    built_year: int | None,
    lon: float,
    lat: float,
) -> int:

    existing = await session.execute(
        text(
            """
            SELECT id
            FROM assets
            WHERE asset_code = :asset_code
            LIMIT 1
            """
        ),
        {
            "asset_code": asset_code,
        },
    )

    existing_id = (
        existing.scalar_one_or_none()
    )

    if existing_id is not None:
        return int(
            existing_id
        )

    result = await session.execute(
        text(
            """
            INSERT INTO assets (
                asset_code,
                name,
                asset_type,
                subtype,
                district,
                owner,
                status,
                identity_status,
                built_year,
                design_life_years,
                material,
                condition,
                representative_geometry,
                source_id,
                confidence_score,
                is_estimated,
                created_at,
                updated_at
            )
            VALUES (
                :asset_code,
                :name,
                :asset_type,
                :subtype,
                :district,
                :owner,
                :status,
                'CANDIDATE',
                :built_year,
                NULL,
                NULL,
                NULL,
                ST_SetSRID(
                    ST_MakePoint(
                        :lon,
                        :lat
                    ),
                    4326
                ),
                :source_id,
                0.80,
                FALSE,
                NOW(),
                NOW()
            )
            RETURNING id
            """
        ),
        {
            "asset_code": asset_code,
            "name": name,
            "asset_type": asset_type,
            "subtype": subtype,
            "district": district,
            "owner": owner,
            "status": status,
            "built_year": built_year,
            "lon": lon,
            "lat": lat,
            "source_id": source_id,
        },
    )

    return int(
        result.scalar_one()
    )


async def enrich_existing_asset(
    session,
    *,
    asset_id: int,
    district: str | None,
    owner: str | None,
    built_year: int | None,
) -> None:

    await session.execute(
        text(
            """
            UPDATE assets
            SET
                district = COALESCE(
                    district,
                    :district
                ),
                owner = COALESCE(
                    owner,
                    :owner
                ),
                built_year = COALESCE(
                    built_year,
                    :built_year
                ),
                updated_at = NOW()
            WHERE id = :asset_id
            """
        ),
        {
            "asset_id": asset_id,
            "district": district,
            "owner": owner,
            "built_year": built_year,
        },
    )


async def import_dams(
    session,
    *,
    source_id: int,
    document_id: int,
) -> dict:

    records = load_ap_records(
        DAM_FILE
    )

    stats = {
        "records": len(records),
        "created": 0,
        "matched": 0,
    }

    for record in records:

        props = record[
            "properties"
        ]

        coordinates = record[
            "geometry"
        ][
            "coordinates"
        ]

        lon = float(
            coordinates[0]
        )

        lat = float(
            coordinates[1]
        )

        name = (
            props.get("dm_name")
            or "Unnamed WRIS Dam"
        )

        external_id = (
            props.get("nrld_no")
            or props.get("strucode")
            or str(
                props.get("objectid")
            )
        )

        district = props.get(
            "dtcode"
        )

        owner = props.get(
            "dm_oper_main_age"
        )

        built_year = integer_year(
            props.get(
                "dm_cmp_yr"
            )
        )

        asset_id, method, confidence = (
            await resolve_asset(
                session,
                source_id=source_id,
                external_id=external_id,
                external_name=name,
                asset_type="dam",
                lon=lon,
                lat=lat,
            )
        )

        if asset_id is None:

            asset_code = (
                "AP_DAM_WRIS_"
                + clean_code(
                    external_id
                )
            )

            asset_id = await create_asset(
                session,
                source_id=source_id,
                asset_code=asset_code,
                name=name,
                asset_type="dam",
                subtype=(
                    props.get(
                        "dm_type"
                    )
                ),
                district=district,
                owner=owner,
                status=status_value(
                    props.get(
                        "dm_status"
                    )
                ),
                built_year=built_year,
                lon=lon,
                lat=lat,
            )

            stats[
                "created"
            ] += 1

        else:

            await enrich_existing_asset(
                session,
                asset_id=asset_id,
                district=district,
                owner=owner,
                built_year=built_year,
            )

            stats[
                "matched"
            ] += 1

        await ensure_identifier(
            session,
            asset_id=asset_id,
            source_id=source_id,
            external_id=external_id,
            external_name=name,
            method=method,
            confidence=confidence,
        )

        await ensure_registry_evidence(
            session,
            asset_id=asset_id,
            document_id=document_id,
            source_id=source_id,
            name=name,
            properties=props,
            geometry=record[
                "geometry"
            ],
        )

    return stats


async def import_barrages(
    session,
    *,
    source_id: int,
    document_id: int,
) -> dict:

    all_records = load_ap_records(
        ANICUT_FILE
    )

    #
    # The WRIS file also contains weirs and anicuts.
    # Current SIMRAS canonical schema supports "barrage",
    # so only records explicitly named as barrages are promoted.
    #
    records = []

    for record in all_records:

        props = record[
            "properties"
        ]

        name = (
            props.get("bwa_name")
            or ""
        )

        if (
            "barrage"
            not in name.lower()
        ):
            continue

        records.append(
            record
        )

    stats = {
        "records": len(records),
        "created": 0,
        "matched": 0,
    }

    for record in records:

        props = record[
            "properties"
        ]

        coordinates = record[
            "geometry"
        ][
            "coordinates"
        ]

        lon = float(
            coordinates[0]
        )

        lat = float(
            coordinates[1]
        )

        name = (
            props.get("bwa_name")
            or "Unnamed WRIS Barrage"
        )

        external_id = (
            props.get("strucode")
            or str(
                props.get("objectid")
            )
        )

        district = props.get(
            "dtcode"
        )

        owner = props.get(
            "bwa_oper_main_age"
        )

        built_year = integer_year(
            props.get(
                "bwa_cmp_yr"
            )
        )

        asset_id, method, confidence = (
            await resolve_asset(
                session,
                source_id=source_id,
                external_id=external_id,
                external_name=name,
                asset_type="barrage",
                lon=lon,
                lat=lat,
            )
        )

        if asset_id is None:

            asset_code = (
                "AP_BAR_WRIS_"
                + clean_code(
                    external_id
                )
            )

            asset_id = await create_asset(
                session,
                source_id=source_id,
                asset_code=asset_code,
                name=name,
                asset_type="barrage",
                subtype="barrage",
                district=district,
                owner=owner,
                status=status_value(
                    props.get(
                        "bwa_status"
                    )
                ),
                built_year=built_year,
                lon=lon,
                lat=lat,
            )

            stats[
                "created"
            ] += 1

        else:

            await enrich_existing_asset(
                session,
                asset_id=asset_id,
                district=district,
                owner=owner,
                built_year=built_year,
            )

            stats[
                "matched"
            ] += 1

        await ensure_identifier(
            session,
            asset_id=asset_id,
            source_id=source_id,
            external_id=external_id,
            external_name=name,
            method=method,
            confidence=confidence,
        )

        await ensure_registry_evidence(
            session,
            asset_id=asset_id,
            document_id=document_id,
            source_id=source_id,
            name=name,
            properties=props,
            geometry=record[
                "geometry"
            ],
        )

    return stats


async def main() -> None:

    if not DAM_FILE.exists():
        raise FileNotFoundError(
            DAM_FILE
        )

    if not ANICUT_FILE.exists():
        raise FileNotFoundError(
            ANICUT_FILE
        )

    async for session in get_db():

        source = await get_source(
            session
        )

        dam_document_id = (
            await get_or_create_document(
                session,
                source.id,
                source_record_id=(
                    "WRIS_Dams.geojsonl"
                ),
                title=(
                    "India-WRIS Dams "
                    "GeoJSONL mirror"
                ),
                path=DAM_FILE,
            )
        )

        barrage_document_id = (
            await get_or_create_document(
                session,
                source.id,
                source_record_id=(
                    "WRIS_Anicuts.geojsonl"
                ),
                title=(
                    "India-WRIS Anicuts, "
                    "Weirs and Barrages "
                    "GeoJSONL mirror"
                ),
                path=ANICUT_FILE,
            )
        )

        dam_stats = await import_dams(
            session,
            source_id=source.id,
            document_id=dam_document_id,
        )

        barrage_stats = (
            await import_barrages(
                session,
                source_id=source.id,
                document_id=(
                    barrage_document_id
                ),
            )
        )

        await session.commit()

        print(
            "=== WRIS AP IMPORT COMPLETE ==="
        )

        print(
            "DAMS:",
            dam_stats,
        )

        print(
            "BARRAGES:",
            barrage_stats,
        )

        break


if __name__ == "__main__":
    asyncio.run(
        main()
    )