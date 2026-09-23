import csv
import json
import os
import re
from pathlib import Path
from collections import Counter, defaultdict

from pypdf import PdfReader


BASE = Path(
    os.environ["ML8G_BASE"]
)

DOCS = BASE / "documents"

INPUT = (
    BASE
    / "input"
    / "ml8e_identifier_needs_asset_link.csv"
)

OUT = BASE / "output"

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


def normalize(value):
    value = compact(value).upper()

    value = re.sub(
        r"[^A-Z0-9.+/-]+",
        " ",
        value,
    )

    return compact(value)


def write_csv(path, rows):

    if not rows:
        path.write_text(
            "",
            encoding="utf-8",
        )
        return

    columns = []
    seen = set()

    for row in rows:
        for key in row:
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
        writer.writerows(rows)


# ============================================================
# PATTERNS
# ============================================================

BRIDGE_PATTERN = re.compile(
    r"\b("
    r"MAJOR\s+BRIDGE|"
    r"MINOR\s+BRIDGE|"
    r"RAILWAY\s+BRIDGE|"
    r"ROAD\s+BRIDGE|"
    r"BRIDGE|"
    r"FLYOVER|"
    r"ROB|"
    r"RUB|"
    r"VIADUCT"
    r")\b",
    re.IGNORECASE,
)


CHAINAGE_PATTERNS = [
    re.compile(
        r"\b(?:CHAINAGE|CH\.?|KM)\s*"
        r"[:=-]?\s*"
        r"([0-9]{1,3}(?:\.[0-9]{1,3})?)",
        re.IGNORECASE,
    ),

    re.compile(
        r"\b([0-9]{1,3}\+[0-9]{1,3})\b",
        re.IGNORECASE,
    ),
]


BRIDGE_NUMBER_PATTERNS = [
    re.compile(
        r"\bBRIDGE\s*(?:NO\.?|NUMBER)"
        r"\s*[:=-]?\s*([A-Z0-9./-]+)",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bBR\.?\s*NO\.?"
        r"\s*[:=-]?\s*([A-Z0-9./-]+)",
        re.IGNORECASE,
    ),

    re.compile(
        r"\bSTRUCTURE\s*(?:NO\.?|NUMBER)"
        r"\s*[:=-]?\s*([A-Z0-9./-]+)",
        re.IGNORECASE,
    ),
]


CONDITION_PATTERN = re.compile(
    r"\b("
    r"GOOD|"
    r"FAIR|"
    r"POOR|"
    r"SATISFACTORY|"
    r"UNSATISFACTORY|"
    r"SERIOUS|"
    r"SEVERE|"
    r"CRITICAL"
    r")\b",
    re.IGNORECASE,
)


DEFECT_PATTERN = re.compile(
    r"\b("
    r"CRACK(?:S|ED|ING)?|"
    r"SPALL(?:ING|ED)?|"
    r"CORROSION|"
    r"RUST(?:ING|ED)?|"
    r"DELAMINATION|"
    r"LEACHING|"
    r"SCOUR(?:ING)?|"
    r"LEAK(?:AGE|ING)?|"
    r"SETTLEMENT|"
    r"DEFORMATION"
    r")\b",
    re.IGNORECASE,
)


INSPECTION_PATTERN = re.compile(
    r"\b("
    r"INSPECTION|"
    r"INSPECTED|"
    r"CONDITION\s+SURVEY|"
    r"DETAILED\s+SURVEY|"
    r"EXISTING\s+CONDITION"
    r")\b",
    re.IGNORECASE,
)


# ============================================================
# READ CANDIDATES
# ============================================================

with INPUT.open(
    "r",
    encoding="utf-8-sig",
    newline="",
) as handle:

    candidates = list(
        csv.DictReader(handle)
    )


print(
    "ML8E_IDENTIFIER_CANDIDATES =",
    len(candidates),
)


# ============================================================
# PAGE CACHE
# ============================================================

readers = {}
page_cache = {}


def reader_for(document):

    if document not in readers:

        path = DOCS / document

        if not path.exists():
            raise RuntimeError(
                f"Missing PDF: {document}"
            )

        readers[document] = PdfReader(
            str(path)
        )

    return readers[document]


def page_lines(
    document,
    page_number,
):

    key = (
        document,
        page_number,
    )

    if key in page_cache:
        return page_cache[key]

    reader = reader_for(
        document
    )

    index = page_number - 1

    if (
        index < 0
        or index >= len(reader.pages)
    ):
        return []

    try:
        text = (
            reader.pages[index].extract_text()
            or ""
        )

    except Exception:
        text = ""

    lines = [
        compact(line)
        for line in text.splitlines()
        if compact(line)
    ]

    page_cache[key] = lines

    return lines


# ============================================================
# COUNT REPEATED KM VALUES
#
# Project limits often repeat throughout many pages.
# ============================================================

identifier_frequency = Counter()


for candidate in candidates:

    document = candidate.get(
        "document",
        "",
    )

    page_number = int(
        candidate.get(
            "page",
            0,
        )
        or 0
    )

    for offset in range(
        -2,
        3,
    ):

        page = (
            page_number
            + offset
        )

        if page < 1:
            continue

        lines = page_lines(
            document,
            page,
        )

        for line in lines:

            for pattern in CHAINAGE_PATTERNS:

                for value in pattern.findall(
                    line
                ):

                    key = (
                        document,
                        normalize(value),
                    )

                    identifier_frequency[
                        key
                    ] += 1


# ============================================================
# EXTRACT ROW WINDOWS
# ============================================================

rows = []

seen_windows = set()


for candidate in candidates:

    document = candidate.get(
        "document",
        "",
    )

    source_page = int(
        candidate.get(
            "page",
            0,
        )
        or 0
    )


    for page_number in range(
        max(
            1,
            source_page - 3,
        ),
        source_page + 4,
    ):

        lines = page_lines(
            document,
            page_number,
        )


        for index, line in enumerate(
            lines
        ):

            if not BRIDGE_PATTERN.search(
                line
            ):
                continue


            start = max(
                0,
                index - 3,
            )

            end = min(
                len(lines),
                index + 4,
            )


            window_lines = lines[
                start:end
            ]

            window = compact(
                " | ".join(
                    window_lines
                )
            )


            key = (
                document,
                page_number,
                normalize(window),
            )

            if key in seen_windows:
                continue

            seen_windows.add(
                key
            )


            chainages = []

            for pattern in CHAINAGE_PATTERNS:

                for value in pattern.findall(
                    window
                ):

                    chainages.append(
                        value
                    )


            bridge_numbers = []

            for pattern in BRIDGE_NUMBER_PATTERNS:

                bridge_numbers.extend(
                    pattern.findall(
                        window
                    )
                )


            conditions = CONDITION_PATTERN.findall(
                window
            )

            defects = DEFECT_PATTERN.findall(
                window
            )

            inspection = bool(
                INSPECTION_PATTERN.search(
                    window
                )
            )


            chainages = list(
                dict.fromkeys(
                    chainages
                )
            )

            bridge_numbers = list(
                dict.fromkeys(
                    bridge_numbers
                )
            )

            conditions = list(
                dict.fromkeys(
                    x.upper()
                    for x in conditions
                )
            )

            defects = list(
                dict.fromkeys(
                    x.upper()
                    for x in defects
                )
            )


            repeated = []

            local = []

            for chainage in chainages:

                frequency = identifier_frequency[
                    (
                        document,
                        normalize(
                            chainage
                        ),
                    )
                ]


                if frequency >= 4:

                    repeated.append(
                        (
                            chainage,
                            frequency,
                        )
                    )

                else:

                    local.append(
                        (
                            chainage,
                            frequency,
                        )
                    )


            # ================================================
            # CLASSIFY
            # ================================================

            if (
                bridge_numbers
                and (
                    conditions
                    or defects
                )
            ):

                classification = (
                    "HIGH_PRIORITY_BRIDGE_NUMBER_CONDITION"
                )


            elif (
                local
                and (
                    conditions
                    or defects
                )
            ):

                classification = (
                    "HIGH_PRIORITY_LOCAL_CHAINAGE_CONDITION"
                )


            elif (
                local
                and inspection
            ):

                classification = (
                    "POSSIBLE_BRIDGE_INSPECTION_ROW"
                )


            elif (
                repeated
                and not local
            ):

                classification = (
                    "LIKELY_PROJECT_LIMIT_REFERENCE"
                )


            elif bridge_numbers:

                classification = (
                    "BRIDGE_NUMBER_NO_CONDITION"
                )


            else:

                classification = (
                    "BRIDGE_CONTEXT_NEEDS_REVIEW"
                )


            rows.append(
                {
                    "document":
                        document,

                    "candidate_source_page":
                        source_page,

                    "extracted_page":
                        page_number,

                    "classification":
                        classification,

                    "bridge_numbers":
                        "; ".join(
                            bridge_numbers
                        ),

                    "local_chainages":
                        "; ".join(
                            f"{value} "
                            f"(freq={freq})"
                            for value, freq
                            in local
                        ),

                    "repeated_chainages":
                        "; ".join(
                            f"{value} "
                            f"(freq={freq})"
                            for value, freq
                            in repeated
                        ),

                    "conditions":
                        "; ".join(
                            conditions
                        ),

                    "defects":
                        "; ".join(
                            defects
                        ),

                    "inspection_context":
                        inspection,

                    "candidate_training_label":
                        False,

                    "database_modified":
                        False,

                    "text_window":
                        window,
                }
            )


# ============================================================
# PRIORITY GROUPS
# ============================================================

priority_classes = {
    "HIGH_PRIORITY_BRIDGE_NUMBER_CONDITION",
    "HIGH_PRIORITY_LOCAL_CHAINAGE_CONDITION",
    "POSSIBLE_BRIDGE_INSPECTION_ROW",
}


priority = [
    row
    for row in rows
    if row[
        "classification"
    ] in priority_classes
]


project_limits = [
    row
    for row in rows
    if row[
        "classification"
    ]
    == "LIKELY_PROJECT_LIMIT_REFERENCE"
]


review = [
    row
    for row in rows
    if row[
        "classification"
    ] not in priority_classes
    and row[
        "classification"
    ]
    != "LIKELY_PROJECT_LIMIT_REFERENCE"
]


write_csv(
    OUT
    / "ml8g_all_bridge_contexts.csv",
    rows,
)

write_csv(
    OUT
    / "ml8g_high_priority_bridge_rows.csv",
    priority,
)

write_csv(
    OUT
    / "ml8g_likely_project_limits.csv",
    project_limits,
)

write_csv(
    OUT
    / "ml8g_needs_review.csv",
    review,
)


classification_counts = Counter(
    row[
        "classification"
    ]
    for row in rows
)


summary = {
    "version":
        "ml8g_bridge_row_extraction_v1",

    "candidate_pages":
        len(candidates),

    "bridge_context_windows":
        len(rows),

    "high_priority_bridge_rows":
        len(priority),

    "likely_project_limit_rows":
        len(project_limits),

    "needs_review_rows":
        len(review),

    "training_labels_created":
        0,

    "database_modified":
        False,

    "classification_counts":
        dict(
            classification_counts
        ),
}


(
    OUT
    / "ml8g_summary.json"
).write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


# ============================================================
# CONSOLE REPORT
# ============================================================

print()
print(
    "================================================"
)

print(
    "ML-8G OFFICIAL BRIDGE ROW EXTRACTION"
)

print(
    "================================================"
)

print(
    "CANDIDATE_PAGES =",
    len(candidates),
)

print(
    "BRIDGE_CONTEXT_WINDOWS =",
    len(rows),
)

print(
    "HIGH_PRIORITY_BRIDGE_ROWS =",
    len(priority),
)

print(
    "LIKELY_PROJECT_LIMIT_ROWS =",
    len(project_limits),
)

print(
    "NEEDS_REVIEW_ROWS =",
    len(review),
)


print()
print(
    "===== CLASSIFICATION ====="
)

for name, count in sorted(
    classification_counts.items()
):

    print(
        name,
        "=",
        count,
    )


print()
print(
    "===== HIGH PRIORITY SAMPLE ====="
)

for row in priority[:30]:

    print()

    print(
        row[
            "document"
        ],
        "PAGE",
        row[
            "extracted_page"
        ],
    )

    print(
        "TYPE =",
        row[
            "classification"
        ],
    )

    print(
        "BRIDGE_NO =",
        row[
            "bridge_numbers"
        ],
    )

    print(
        "CHAINAGE =",
        row[
            "local_chainages"
        ],
    )

    print(
        "CONDITION =",
        row[
            "conditions"
        ],
    )

    print(
        "DEFECTS =",
        row[
            "defects"
        ],
    )

    print(
        "TEXT =",
        row[
            "text_window"
        ][:700],
    )


print()
print(
    "TRAINING_LABELS_CREATED = 0"
)

print(
    "DATABASE_MODIFIED = NO"
)

print(
    "ML8G_EXTRACTION=PASS"
)