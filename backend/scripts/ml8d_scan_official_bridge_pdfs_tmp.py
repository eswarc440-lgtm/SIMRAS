import os
import re
import csv
import json
import asyncio
import hashlib
from pathlib import Path
from collections import Counter

from pypdf import PdfReader

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

BASE = (
    ROOT
    / "data"
    / "bridge_inspections"
    / "official_sources"
)

DOCS = BASE / "documents"

OUT = BASE / "ml8d_scan"

MANIFEST = (
    BASE
    / "official_bridge_source_manifest.csv"
)

# ML8D_RUNTIME_PATHS_V2
BASE = Path(
    os.environ.get(
        "ML8D_BASE",
        str(BASE),
    )
)

DOCS = Path(
    os.environ.get(
        "ML8D_DOCS",
        str(BASE / "documents"),
    )
)

OUT = Path(
    os.environ.get(
        "ML8D_OUT",
        str(BASE / "ml8d_scan"),
    )
)

MANIFEST = Path(
    os.environ.get(
        "ML8D_MANIFEST",
        str(
            BASE
            / "official_bridge_source_manifest.csv"
        ),
    )
)


OUT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# NORMALIZATION
# ============================================================

def normalize(value):
    if value is None:
        return ""

    value = str(value).upper()

    value = re.sub(
        r"[^A-Z0-9]+",
        " ",
        value,
    )

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def compact(value):
    return re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        while True:
            block = handle.read(
                1024 * 1024
            )

            if not block:
                break

            digest.update(block)

    return digest.hexdigest().upper()


# ============================================================
# EVIDENCE TERMS
# ============================================================

BRIDGE_TERMS = [
    "BRIDGE",
    "MAJOR BRIDGE",
    "MINOR BRIDGE",
    "FLYOVER",
    "VIADUCT",
    "ROAD OVER BRIDGE",
    "ROAD UNDER BRIDGE",
    "ROB",
    "RUB",
]


CONDITION_TERMS = [
    "CONDITION",
    "CONDITION RATING",
    "CONDITION INDEX",
    "HEALTH INDEX",
    "BRIDGE HEALTH INDEX",
    "POOR",
    "FAIR",
    "GOOD",
    "SATISFACTORY",
    "UNSATISFACTORY",
    "DISTRESS",
    "DETERIORATION",
    "DEFECT",
    "DAMAGED",
]


DEFECT_TERMS = [
    "CRACK",
    "CRACKING",
    "SPALLING",
    "CORROSION",
    "RUST",
    "DELAMINATION",
    "LEACHING",
    "SCOUR",
    "EROSION",
    "LEAKAGE",
    "SETTLEMENT",
    "DEFORMATION",
    "EXPOSED REINFORCEMENT",
    "BEARING DISTRESS",
]


COMPONENT_TERMS = [
    "FOUNDATION",
    "PIER",
    "PIERS",
    "ABUTMENT",
    "BEARING",
    "BEARINGS",
    "DECK",
    "SUPERSTRUCTURE",
    "SUBSTRUCTURE",
    "GIRDER",
    "SLAB",
    "EXPANSION JOINT",
]


INSPECTION_TERMS = [
    "INSPECTION",
    "INSPECTED",
    "CONDITION SURVEY",
    "DETAILED SURVEY",
    "BRIDGE INSPECTION REGISTER",
    "NRS",
    "NUMERICAL RATING SYSTEM",
    "CRN",
    "CONDITION RATING NUMBER",
    "ORN",
    "OVERALL RATING NUMBER",
]


REPAIR_TERMS = [
    "REPAIR",
    "REPAIRS",
    "REHABILITATION",
    "REHABILITATE",
    "STRENGTHENING",
    "RETROFITTING",
    "REPLACEMENT",
    "MAINTENANCE",
]


GENERIC_ASSET_NAMES = {
    "BRIDGE",
    "ROAD BRIDGE",
    "RAIL BRIDGE",
    "RAILWAY BRIDGE",
    "FLYOVER",
    "ROB",
    "RUB",
    "VIADUCT",
}


def found_terms(
    normalized_text,
    terms,
):
    found = []

    for term in terms:
        normalized_term = normalize(
            term
        )

        if normalized_term in normalized_text:
            found.append(term)

    return found


def make_snippet(
    raw_text,
    terms,
    max_chars=700,
):
    raw = compact(
        raw_text
    )

    if not raw:
        return ""

    upper = raw.upper()

    first = None

    for term in terms:
        position = upper.find(
            term.upper()
        )

        if position >= 0:
            if first is None or position < first:
                first = position

    if first is None:
        return raw[:max_chars]

    start = max(
        0,
        first - 220,
    )

    end = min(
        len(raw),
        start + max_chars,
    )

    return raw[
        start:end
    ]


# ============================================================
# BRIDGE IDENTIFIER EXTRACTION
# ============================================================

IDENTIFIER_PATTERNS = [
    r"\bBRIDGE\s*(?:NO\.?|NUMBER)\s*[:\-]?\s*[A-Z0-9./\-]+",
    r"\bBR\.?\s*NO\.?\s*[:\-]?\s*[A-Z0-9./\-]+",
    r"\bCHAINAGE\s*[:\-]?\s*[0-9.+\-]+",
    r"\bCH\.?\s*[:\-]?\s*[0-9.+\-]+",
    r"\bKM\s*[:\-]?\s*[0-9.+\-]+",
]


def extract_identifiers(
    raw_text,
):
    values = []

    for pattern in IDENTIFIER_PATTERNS:

        values.extend(
            re.findall(
                pattern,
                raw_text,
                flags=re.IGNORECASE,
            )
        )

    cleaned = []

    seen = set()

    for value in values:

        value = compact(
            value
        )

        key = value.upper()

        if key not in seen:
            seen.add(key)
            cleaned.append(value)

    return cleaned[:25]


# ============================================================
# DATABASE
# ============================================================

def database_url():
    value = os.environ[
        "DATABASE_URL"
    ]

    if value.startswith(
        "postgresql://"
    ):
        value = value.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    return value


async def load_bridge_assets():

    engine = create_async_engine(
        database_url()
    )

    async with engine.connect() as conn:

        rows = (
            await conn.execute(
                text(
                    """
                    SELECT
                        id,
                        asset_code,
                        name,
                        district
                    FROM public.assets
                    WHERE
                        LOWER(
                            CAST(asset_type AS TEXT)
                        )='bridge'
                        AND asset_code LIKE 'AP_BR_%'
                        AND name IS NOT NULL
                        AND BTRIM(name) <> ''
                    ORDER BY asset_code
                    """
                )
            )
        ).mappings().all()

    await engine.dispose()

    assets = []

    for row in rows:

        normalized_name = normalize(
            row["name"]
        )

        if (
            len(normalized_name) < 7
            or normalized_name
            in GENERIC_ASSET_NAMES
        ):
            continue

        assets.append(
            {
                "asset_id":
                    int(row["id"]),

                "asset_code":
                    row["asset_code"],

                "name":
                    row["name"],

                "district":
                    row["district"],

                "normalized_name":
                    normalized_name,
            }
        )

    return assets


# ============================================================
# SOURCE MANIFEST
# ============================================================

def read_manifest():

    rows = []

    with MANIFEST.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        reader = csv.DictReader(
            handle
        )

        for row in reader:
            rows.append(row)

    return rows


# ============================================================
# MAIN SCAN
# ============================================================

async def main():

    assets = await load_bridge_assets()

    manifest = read_manifest()

    manifest_by_filename = {}

    for row in manifest:

        local_file = (
            row.get(
                "local_file"
            )
            or ""
        )

        if local_file:
            filename = Path(local_file.replace("\\", "/")).name

            manifest_by_filename[
                filename
            ] = row


    print()
    print(
        "===== CANONICAL BRIDGE NAMES ====="
    )

    print(
        "SEARCHABLE_AP_BRIDGE_NAMES =",
        len(assets),
    )


    pdf_paths = sorted(
        DOCS.glob("*.pdf")
    )

    print(
        "OFFICIAL_PDFS =",
        len(pdf_paths),
    )


    page_hits = []

    asset_matches = []

    bridge_level_candidates = []

    document_summary = []


    for pdf_path in pdf_paths:

        source = manifest_by_filename.get(
            pdf_path.name,
            {},
        )

        source_id = source.get(
            "source_id",
            pdf_path.stem,
        )

        role = source.get(
            "evidence_role",
            "UNKNOWN",
        )


        print()
        print(
            "================================================"
        )

        print(
            "DOCUMENT =",
            pdf_path.name,
        )

        print(
            "SOURCE_ID =",
            source_id,
        )

        print(
            "ROLE =",
            role,
        )


        actual_hash = sha256_file(
            pdf_path
        )

        manifest_hash = (
            source.get(
                "sha256"
            )
            or ""
        ).upper()


        hash_ok = (
            not manifest_hash
            or manifest_hash
            == actual_hash
        )


        print(
            "SHA256_OK =",
            hash_ok,
        )


        if not hash_ok:
            raise RuntimeError(
                f"Hash mismatch: "
                f"{pdf_path.name}"
            )


        reader = PdfReader(
            str(pdf_path)
        )

        pages = len(
            reader.pages
        )


        print(
            "PAGES =",
            pages,
        )


        extracted_pages = 0
        empty_pages = 0
        hit_pages = 0
        matched_assets = set()
        candidate_pages = 0


        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):

            try:
                raw_text = (
                    page.extract_text()
                    or ""
                )

            except Exception:
                raw_text = ""


            raw_text = compact(
                raw_text
            )


            if not raw_text:

                empty_pages += 1
                continue


            extracted_pages += 1

            normalized_text = normalize(
                raw_text
            )


            bridges = found_terms(
                normalized_text,
                BRIDGE_TERMS,
            )

            conditions = found_terms(
                normalized_text,
                CONDITION_TERMS,
            )

            defects = found_terms(
                normalized_text,
                DEFECT_TERMS,
            )

            components = found_terms(
                normalized_text,
                COMPONENT_TERMS,
            )

            inspections = found_terms(
                normalized_text,
                INSPECTION_TERMS,
            )

            repairs = found_terms(
                normalized_text,
                REPAIR_TERMS,
            )


            identifiers = extract_identifiers(
                raw_text
            )


            page_asset_matches = []

            for asset in assets:

                if (
                    asset[
                        "normalized_name"
                    ]
                    in normalized_text
                ):

                    page_asset_matches.append(
                        asset
                    )

                    matched_assets.add(
                        asset[
                            "asset_code"
                        ]
                    )


            has_bridge_context = bool(
                bridges
                or identifiers
                or page_asset_matches
            )


            has_condition_evidence = bool(
                conditions
                or defects
            )


            has_inspection_context = bool(
                inspections
            )


            has_repair_context = bool(
                repairs
            )


            if (
                has_bridge_context
                and (
                    has_condition_evidence
                    or has_inspection_context
                    or has_repair_context
                )
            ):

                hit_pages += 1


                all_terms = (
                    bridges
                    + conditions
                    + defects
                    + inspections
                    + repairs
                )


                page_class = (
                    "GENERAL_ENGINEERING_REFERENCE"
                )


                if role == "INSPECTION_STANDARD":

                    page_class = (
                        "INSPECTION_STANDARD_ONLY"
                    )


                elif (
                    page_asset_matches
                    and has_condition_evidence
                ):

                    page_class = (
                        "BRIDGE_LEVEL_CONDITION_CANDIDATE"
                    )


                elif (
                    identifiers
                    and has_condition_evidence
                ):

                    page_class = (
                        "IDENTIFIED_BRIDGE_CONDITION_CANDIDATE"
                    )


                elif (
                    has_bridge_context
                    and has_repair_context
                ):

                    page_class = (
                        "BRIDGE_REPAIR_ENGINEERING_EVIDENCE"
                    )


                elif (
                    has_bridge_context
                    and has_inspection_context
                ):

                    page_class = (
                        "GENERAL_INSPECTION_OR_SURVEY_TEXT"
                    )


                snippet = make_snippet(
                    raw_text,
                    all_terms,
                )


                hit = {
                    "source_id":
                        source_id,

                    "document":
                        pdf_path.name,

                    "evidence_role":
                        role,

                    "page":
                        page_number,

                    "classification":
                        page_class,

                    "bridge_terms":
                        "; ".join(
                            bridges
                        ),

                    "condition_terms":
                        "; ".join(
                            conditions
                        ),

                    "defect_terms":
                        "; ".join(
                            defects
                        ),

                    "component_terms":
                        "; ".join(
                            components
                        ),

                    "inspection_terms":
                        "; ".join(
                            inspections
                        ),

                    "repair_terms":
                        "; ".join(
                            repairs
                        ),

                    "bridge_identifiers":
                        "; ".join(
                            identifiers
                        ),

                    "matched_asset_codes":
                        "; ".join(
                            x["asset_code"]
                            for x
                            in page_asset_matches
                        ),

                    "matched_asset_names":
                        "; ".join(
                            x["name"]
                            for x
                            in page_asset_matches
                        ),

                    "snippet":
                        snippet,

                    "training_label_candidate":
                        False,

                    "promote_to_ml":
                        False,

                    "manual_review_required":
                        True,
                }


                page_hits.append(
                    hit
                )


                if page_class in {
                    "BRIDGE_LEVEL_CONDITION_CANDIDATE",
                    "IDENTIFIED_BRIDGE_CONDITION_CANDIDATE",
                }:

                    candidate_pages += 1

                    bridge_level_candidates.append(
                        hit.copy()
                    )


            for asset in page_asset_matches:

                asset_matches.append(
                    {
                        "source_id":
                            source_id,

                        "document":
                            pdf_path.name,

                        "page":
                            page_number,

                        "asset_id":
                            asset[
                                "asset_id"
                            ],

                        "asset_code":
                            asset[
                                "asset_code"
                            ],

                        "asset_name":
                            asset[
                                "name"
                            ],

                        "district":
                            asset[
                                "district"
                            ],

                        "condition_context":
                            bool(
                                conditions
                                or defects
                            ),

                        "inspection_context":
                            bool(
                                inspections
                            ),

                        "repair_context":
                            bool(
                                repairs
                            ),

                        "training_label_candidate":
                            False,

                        "promote_to_ml":
                            False,
                    }
                )


        summary = {
            "source_id":
                source_id,

            "document":
                pdf_path.name,

            "role":
                role,

            "pages":
                pages,

            "text_pages":
                extracted_pages,

            "empty_text_pages":
                empty_pages,

            "evidence_hit_pages":
                hit_pages,

            "bridge_level_candidate_pages":
                candidate_pages,

            "canonical_asset_matches":
                len(
                    matched_assets
                ),

            "sha256":
                actual_hash,

            "sha256_verified":
                hash_ok,

            "automatic_training_labels":
                0,

            "automatic_promotions":
                0,
        }


        document_summary.append(
            summary
        )


        print(
            "TEXT_PAGES =",
            extracted_pages,
        )

        print(
            "EMPTY_TEXT_PAGES =",
            empty_pages,
        )

        print(
            "EVIDENCE_HIT_PAGES =",
            hit_pages,
        )

        print(
            "BRIDGE_LEVEL_CANDIDATE_PAGES =",
            candidate_pages,
        )

        print(
            "CANONICAL_ASSET_MATCHES =",
            len(
                matched_assets
            ),
        )


    # ========================================================
    # WRITE OUTPUTS
    # ========================================================

    def write_csv(
        path,
        rows,
    ):

        if not rows:

            path.write_text(
                "",
                encoding="utf-8",
            )

            return


        columns = []

        seen = set()

        for row in rows:

            for key in row.keys():

                if key not in seen:

                    seen.add(key)
                    columns.append(key)


        with path.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=columns,
            )

            writer.writeheader()

            writer.writerows(
                rows
            )


    write_csv(
        OUT
        / "document_summary.csv",
        document_summary,
    )

    write_csv(
        OUT
        / "page_evidence_hits.csv",
        page_hits,
    )

    write_csv(
        OUT
        / "canonical_asset_name_matches.csv",
        asset_matches,
    )

    write_csv(
        OUT
        / "bridge_level_condition_candidates.csv",
        bridge_level_candidates,
    )


    output = {
        "scanner_version":
            "ml8d_official_bridge_pdf_scan_v1",

        "policy": {
            "ocr_used":
                False,

            "synthetic_labels":
                False,

            "automatic_promotion":
                False,

            "automatic_training_label":
                False,

            "manual_review_required":
                True,
        },

        "documents":
            document_summary,

        "counts": {
            "documents":
                len(
                    document_summary
                ),

            "page_evidence_hits":
                len(
                    page_hits
                ),

            "canonical_asset_name_matches":
                len(
                    asset_matches
                ),

            "bridge_level_condition_candidates":
                len(
                    bridge_level_candidates
                ),

            "labels_promoted":
                0,
        },
    }


    (
        OUT
        / "ml8d_scan_summary.json"
    ).write_text(
        json.dumps(
            output,
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )


    # ========================================================
    # CONSOLE SUMMARY
    # ========================================================

    print()
    print(
        "================================================"
    )

    print(
        "ML-8D SCAN SUMMARY"
    )

    print(
        "================================================"
    )


    print(
        "DOCUMENTS =",
        len(
            document_summary
        ),
    )

    print(
        "PAGE_EVIDENCE_HITS =",
        len(
            page_hits
        ),
    )

    print(
        "CANONICAL_ASSET_NAME_MATCHES =",
        len(
            asset_matches
        ),
    )

    print(
        "BRIDGE_LEVEL_CONDITION_CANDIDATES =",
        len(
            bridge_level_candidates
        ),
    )

    print(
        "TRAINING_LABELS_CREATED = 0"
    )

    print(
        "ML_ROWS_PROMOTED = 0"
    )


    print()
    print(
        "===== CANDIDATE CLASSIFICATION ====="
    )

    counts = Counter(
        row[
            "classification"
        ]
        for row in page_hits
    )

    for key, value in sorted(
        counts.items()
    ):

        print(
            key,
            "=",
            value,
        )


    print()
    print(
        "OUTPUT =",
        OUT,
    )

    print()
    print(
        "ML8D_SCAN=PASS"
    )


asyncio.run(
    main()
)