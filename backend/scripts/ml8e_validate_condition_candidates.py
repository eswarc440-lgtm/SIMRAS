import csv
import json
import os
import re
from pathlib import Path
from collections import Counter, defaultdict

from pypdf import PdfReader


BASE = Path(
    os.environ["ML8E_BASE"]
)

DOCS = BASE / "documents"
INPUT_DIR = BASE / "input"
OUT = BASE / "output"

CANDIDATE_FILE = (
    INPUT_DIR
    / "bridge_level_condition_candidates.csv"
)

MATCH_FILE = (
    INPUT_DIR
    / "canonical_asset_name_matches.csv"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# HELPERS
# ============================================================

def compact(value):
    return re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()


def split_values(value):
    if not value:
        return []

    return [
        item.strip()
        for item in str(value).split(";")
        if item.strip()
    ]


def unique(values):
    result = []
    seen = set()

    for value in values:
        key = value.strip().upper()

        if not key:
            continue

        if key not in seen:
            seen.add(key)
            result.append(value.strip())

    return result


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
    known = set()

    for row in rows:
        for key in row.keys():
            if key not in known:
                known.add(key)
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
        writer.writerows(rows)


# ============================================================
# STRICT CONDITION WORDS
#
# Detection only.
# These are NEVER automatically converted into labels.
# ============================================================

CONDITION_PATTERNS = {
    "GOOD":
        r"\bGOOD\b",

    "FAIR":
        r"\bFAIR\b",

    "POOR":
        r"\bPOOR\b",

    "SATISFACTORY":
        r"\bSATISFACTORY\b",

    "UNSATISFACTORY":
        r"\bUNSATISFACTORY\b",

    "SEVERE":
        r"\bSEVERE\b",

    "SERIOUS":
        r"\bSERIOUS\b",

    "CRITICAL":
        r"\bCRITICAL\b",
}


DEFECT_PATTERNS = {
    "CRACKING":
        r"\bCRACK(?:S|ED|ING)?\b",

    "SPALLING":
        r"\bSPALL(?:ING|ED)?\b",

    "CORROSION":
        r"\bCORROSION\b",

    "RUST":
        r"\bRUST(?:ING|ED)?\b",

    "DELAMINATION":
        r"\bDELAMINATION\b",

    "LEACHING":
        r"\bLEACHING\b",

    "SCOUR":
        r"\bSCOUR(?:ING)?\b",

    "LEAKAGE":
        r"\bLEAK(?:AGE|ING)?\b",

    "DEFORMATION":
        r"\bDEFORMATION\b",

    "SETTLEMENT":
        r"\bSETTLEMENT\b",
}


INSPECTION_PATTERNS = [
    r"\bINSPECTION\b",
    r"\bINSPECTED\b",
    r"\bCONDITION SURVEY\b",
    r"\bDETAILED SURVEY\b",
    r"\bCONDITION RATING\b",
    r"\bHEALTH INDEX\b",
]


RATING_PATTERNS = [
    r"\b(?:CONDITION|RATING)\s*[:=-]\s*[0-9]+(?:\.[0-9]+)?\b",
    r"\bNRS\s*[:=-]?\s*[0-9]+(?:\.[0-9]+)?\b",
    r"\bCRN\s*[:=-]?\s*[0-9]+(?:\.[0-9]+)?\b",
    r"\bORN\s*[:=-]?\s*[0-9]+(?:\.[0-9]+)?\b",
    r"\bBHI\s*[:=-]?\s*[0-9]+(?:\.[0-9]+)?\b",
]


IDENTIFIER_PATTERNS = [
    r"\bBRIDGE\s*(?:NO\.?|NUMBER)\s*[:\-]?\s*[A-Z0-9./\-]+",
    r"\bBR\.?\s*NO\.?\s*[:\-]?\s*[A-Z0-9./\-]+",
    r"\bCHAINAGE\s*[:\-]?\s*[0-9.+\-]+",
    r"\bCH\.?\s*[:\-]?\s*[0-9.+\-]+",
    r"\bKM\s*[:\-]?\s*[0-9.+\-]+",
]


def detect_dictionary(
    text,
    patterns,
):
    upper = text.upper()

    found = []

    for label, pattern in patterns.items():
        if re.search(
            pattern,
            upper,
            flags=re.IGNORECASE,
        ):
            found.append(label)

    return found


def detect_any(
    text,
    patterns,
):
    return any(
        re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )
        for pattern in patterns
    )


def extract_patterns(
    text,
    patterns,
):
    values = []

    for pattern in patterns:

        for match in re.findall(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):

            if isinstance(
                match,
                tuple,
            ):
                match = " ".join(match)

            values.append(
                compact(str(match))
            )

    return unique(values)


def snippet(
    text,
    max_chars=1300,
):
    text = compact(text)

    if len(text) <= max_chars:
        return text

    return text[:max_chars]


# ============================================================
# READ INPUT
# ============================================================

with CANDIDATE_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as handle:

    candidates = list(
        csv.DictReader(handle)
    )


with MATCH_FILE.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as handle:

    asset_matches = list(
        csv.DictReader(handle)
    )


print(
    "RAW_ML8D_CANDIDATES =",
    len(candidates),
)


# ============================================================
# ASSET MATCHES BY DOCUMENT + PAGE
# ============================================================

matches_by_page = defaultdict(list)

for row in asset_matches:

    key = (
        row.get("document", ""),
        str(row.get("page", "")),
    )

    matches_by_page[key].append(row)


# ============================================================
# PDF CACHE
# ============================================================

reader_cache = {}
text_cache = {}


def get_page_text(
    document,
    page_number,
):

    key = (
        document,
        page_number,
    )

    if key in text_cache:
        return text_cache[key]

    path = DOCS / document

    if not path.exists():
        raise RuntimeError(
            f"PDF missing: {document}"
        )

    if document not in reader_cache:
        reader_cache[document] = PdfReader(
            str(path)
        )

    reader = reader_cache[
        document
    ]

    index = page_number - 1

    if (
        index < 0
        or index >= len(reader.pages)
    ):
        raise RuntimeError(
            f"Invalid page {page_number} "
            f"for {document}"
        )

    try:
        value = (
            reader.pages[index].extract_text()
            or ""
        )

    except Exception:
        value = ""

    value = compact(value)

    text_cache[key] = value

    return value


# ============================================================
# REVIEW
# ============================================================

review_rows = []

for candidate in candidates:

    document = candidate.get(
        "document",
        "",
    )

    source_id = candidate.get(
        "source_id",
        "",
    )

    page = int(
        candidate.get(
            "page",
            0,
        )
        or 0
    )

    classification = candidate.get(
        "classification",
        "",
    )

    page_text = get_page_text(
        document,
        page,
    )


    condition_words = detect_dictionary(
        page_text,
        CONDITION_PATTERNS,
    )

    defect_words = detect_dictionary(
        page_text,
        DEFECT_PATTERNS,
    )

    inspection_context = detect_any(
        page_text,
        INSPECTION_PATTERNS,
    )

    rating_values = extract_patterns(
        page_text,
        RATING_PATTERNS,
    )

    identifiers = extract_patterns(
        page_text,
        IDENTIFIER_PATTERNS,
    )


    key = (
        document,
        str(page),
    )

    page_matches = matches_by_page.get(
        key,
        [],
    )


    canonical_codes = unique(
        [
            row.get(
                "asset_code",
                "",
            )
            for row in page_matches
        ]
        +
        split_values(
            candidate.get(
                "matched_asset_codes",
                "",
            )
        )
    )


    canonical_names = unique(
        [
            row.get(
                "asset_name",
                "",
            )
            for row in page_matches
        ]
        +
        split_values(
            candidate.get(
                "matched_asset_names",
                "",
            )
        )
    )


    exact_asset_count = len(
        canonical_codes
    )

    explicit_condition = bool(
        condition_words
    )

    explicit_defect = bool(
        defect_words
    )

    explicit_rating = bool(
        rating_values
    )

    explicit_identifier = bool(
        identifiers
    )


    # ========================================================
    # TRIAGE
    #
    # No tier automatically becomes a training label.
    # ========================================================

    if (
        exact_asset_count == 1
        and inspection_context
        and explicit_condition
    ):
        tier = (
            "A_EXACT_ASSET_CONDITION_REVIEW"
        )

    elif (
        exact_asset_count == 1
        and inspection_context
        and explicit_rating
    ):
        tier = (
            "A_EXACT_ASSET_RATING_REVIEW"
        )

    elif (
        exact_asset_count == 1
        and inspection_context
        and explicit_defect
    ):
        tier = (
            "B_EXACT_ASSET_DEFECT_REVIEW"
        )

    elif (
        exact_asset_count == 0
        and explicit_identifier
        and inspection_context
        and (
            explicit_condition
            or explicit_rating
            or explicit_defect
        )
    ):
        tier = (
            "B_IDENTIFIER_NEEDS_ASSET_LINK"
        )

    elif exact_asset_count > 1:
        tier = (
            "C_AMBIGUOUS_MULTI_ASSET_PAGE"
        )

    else:
        tier = (
            "D_INSUFFICIENT_FOR_LABEL"
        )


    review_rows.append(
        {
            "source_id":
                source_id,

            "document":
                document,

            "page":
                page,

            "ml8d_classification":
                classification,

            "review_tier":
                tier,

            "canonical_asset_count":
                exact_asset_count,

            "canonical_asset_codes":
                "; ".join(
                    canonical_codes
                ),

            "canonical_asset_names":
                "; ".join(
                    canonical_names
                ),

            "inspection_context":
                inspection_context,

            "condition_words":
                "; ".join(
                    condition_words
                ),

            "rating_values":
                "; ".join(
                    rating_values
                ),

            "defect_words":
                "; ".join(
                    defect_words
                ),

            "bridge_identifiers":
                "; ".join(
                    identifiers
                ),

            "candidate_training_label":
                False,

            "verified_for_ml":
                False,

            "manual_review_required":
                True,

            "page_text_excerpt":
                snippet(
                    page_text
                ),
        }
    )


# ============================================================
# DEDUPLICATE REVIEW ROWS
# ============================================================

deduped = []

seen = set()

for row in review_rows:

    key = (
        row["source_id"],
        row["document"],
        row["page"],
        row["canonical_asset_codes"],
        row["bridge_identifiers"],
        row["review_tier"],
    )

    if key in seen:
        continue

    seen.add(key)

    deduped.append(row)


review_rows = deduped


high_priority = [
    row
    for row in review_rows
    if row["review_tier"].startswith(
        "A_"
    )
]


identifier_candidates = [
    row
    for row in review_rows
    if row["review_tier"]
    == "B_IDENTIFIER_NEEDS_ASSET_LINK"
]


ambiguous = [
    row
    for row in review_rows
    if row["review_tier"]
    == "C_AMBIGUOUS_MULTI_ASSET_PAGE"
]


insufficient = [
    row
    for row in review_rows
    if row["review_tier"]
    == "D_INSUFFICIENT_FOR_LABEL"
]


# ============================================================
# WRITE RESULTS
# ============================================================

write_csv(
    OUT
    / "ml8e_all_candidate_review.csv",
    review_rows,
)

write_csv(
    OUT
    / "ml8e_high_priority_review.csv",
    high_priority,
)

write_csv(
    OUT
    / "ml8e_identifier_needs_asset_link.csv",
    identifier_candidates,
)

write_csv(
    OUT
    / "ml8e_ambiguous_multi_asset.csv",
    ambiguous,
)

write_csv(
    OUT
    / "ml8e_insufficient_candidates.csv",
    insufficient,
)


tier_counts = Counter(
    row["review_tier"]
    for row in review_rows
)


documents = Counter(
    row["document"]
    for row in review_rows
)


summary = {
    "version":
        "ml8e_candidate_validation_v1",

    "policy": {
        "database_modified":
            False,

        "training_labels_created":
            0,

        "predictions_created":
            0,

        "automatic_label_promotion":
            False,

        "manual_review_required":
            True,
    },

    "counts": {
        "raw_ml8d_candidates":
            len(candidates),

        "deduplicated_candidates":
            len(review_rows),

        "high_priority_exact_asset":
            len(high_priority),

        "identifier_needs_asset_link":
            len(identifier_candidates),

        "ambiguous_multi_asset":
            len(ambiguous),

        "insufficient":
            len(insufficient),

        "labels_created":
            0,
    },

    "tier_counts":
        dict(tier_counts),

    "document_counts":
        dict(documents),
}


(
    OUT
    / "ml8e_summary.json"
).write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


# ============================================================
# OUTPUT
# ============================================================

print()
print(
    "================================================"
)

print(
    "ML-8E CANDIDATE VALIDATION SUMMARY"
)

print(
    "================================================"
)

print(
    "RAW_CANDIDATES =",
    len(candidates),
)

print(
    "DEDUPLICATED_CANDIDATES =",
    len(review_rows),
)

print(
    "HIGH_PRIORITY_EXACT_ASSET =",
    len(high_priority),
)

print(
    "IDENTIFIER_NEEDS_ASSET_LINK =",
    len(identifier_candidates),
)

print(
    "AMBIGUOUS_MULTI_ASSET =",
    len(ambiguous),
)

print(
    "INSUFFICIENT_FOR_LABEL =",
    len(insufficient),
)


print()
print(
    "===== REVIEW TIERS ====="
)

for key, value in sorted(
    tier_counts.items()
):
    print(
        key,
        "=",
        value,
    )


print()
print(
    "===== HIGH PRIORITY SAMPLE ====="
)

for row in high_priority[:20]:

    print()

    print(
        row["document"],
        "PAGE",
        row["page"],
    )

    print(
        "ASSET =",
        row[
            "canonical_asset_codes"
        ],
        row[
            "canonical_asset_names"
        ],
    )

    print(
        "CONDITION =",
        row[
            "condition_words"
        ],
    )

    print(
        "RATING =",
        row[
            "rating_values"
        ],
    )

    print(
        "DEFECTS =",
        row[
            "defect_words"
        ],
    )


print()
print(
    "TRAINING_LABELS_CREATED = 0"
)

print(
    "DATABASE_MODIFIED = NO"
)

print(
    "ML8E_VALIDATION=PASS"
)