import csv
import json
import os
import re
from pathlib import Path

from pypdf import PdfReader


PDF = Path(
    os.environ["ML8H_PDF"]
)

OUT = Path(
    os.environ["ML8H_OUT"]
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


def compact(value):
    return re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()


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

    keys = []
    seen = set()

    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                keys.append(key)

    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=keys,
        )

        writer.writeheader()
        writer.writerows(rows)


reader = PdfReader(
    str(PDF)
)


print(
    "PDF_PAGES =",
    len(reader.pages),
)


# ============================================================
# 1. EXTRACT ALL TEXT PAGES
# ============================================================

pages = {}

for page_number, page in enumerate(
    reader.pages,
    start=1,
):

    try:
        text = (
            page.extract_text()
            or ""
        )

    except Exception:
        text = ""

    pages[
        page_number
    ] = text


# ============================================================
# 2. LOCATE TABLE A-5
# ============================================================

table_pages = []

for page_number, text in pages.items():

    upper = text.upper()

    if (
        "TABLE A-5" in upper
        or "TABLE A - 5" in upper
        or "LIST OF BRIDGES ALONG THE PROJECT HIGHWAY"
        in upper
    ):
        table_pages.append(
            page_number
        )


print(
    "TABLE_A5_ANCHOR_PAGES =",
    table_pages,
)


if not table_pages:
    raise RuntimeError(
        "Could not locate Table A-5."
    )


anchor = min(
    table_pages
)


# ============================================================
# 3. EXTRACT WIDE PAGE WINDOW
#
# Tables often continue for several pages.
# ============================================================

start_page = max(
    1,
    anchor - 1,
)

end_page = min(
    len(reader.pages),
    anchor + 12,
)


print(
    "EXTRACT_PAGE_RANGE =",
    f"{start_page}-{end_page}",
)


raw_pages = []


for page_number in range(
    start_page,
    end_page + 1,
):

    text = pages[
        page_number
    ]

    raw_pages.append(
        {
            "page":
                page_number,

            "text":
                text,
        }
    )

    output = (
        OUT
        / f"page_{page_number:03d}.txt"
    )

    output.write_text(
        text,
        encoding="utf-8",
    )


# ============================================================
# 4. DETECT TABLE-LIKE LINES
# ============================================================

chainage_pattern = re.compile(
    r"\b(?:KM|CH(?:AINAGE)?\.?)?"
    r"\s*[:=-]?\s*"
    r"([0-9]{1,3}(?:\.[0-9]{1,3})?)\b",
    re.IGNORECASE,
)


bridge_pattern = re.compile(
    r"\b("
    r"MAJOR\s+BRIDGE|"
    r"MINOR\s+BRIDGE|"
    r"BRIDGE|"
    r"ROB|"
    r"RUB|"
    r"FLYOVER|"
    r"VIADUCT"
    r")\b",
    re.IGNORECASE,
)


condition_pattern = re.compile(
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


defect_pattern = re.compile(
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


candidate_lines = []


for page_number in range(
    start_page,
    end_page + 1,
):

    lines = [
        compact(line)
        for line in pages[
            page_number
        ].splitlines()
        if compact(line)
    ]


    for index, line in enumerate(
        lines
    ):

        upper = line.upper()

        likely_row = (
            bridge_pattern.search(
                line
            )
            or re.search(
                r"\b[0-9]{1,3}\.[0-9]{1,3}\b",
                line,
            )
            or condition_pattern.search(
                line
            )
            or defect_pattern.search(
                line
            )
        )


        if not likely_row:
            continue


        start = max(
            0,
            index - 2,
        )

        end = min(
            len(lines),
            index + 3,
        )


        context = compact(
            " | ".join(
                lines[
                    start:end
                ]
            )
        )


        chainages = [
            value
            for value in
            chainage_pattern.findall(
                context
            )
        ]


        bridge_types = [
            value.upper()
            for value in
            bridge_pattern.findall(
                context
            )
        ]


        conditions = [
            value.upper()
            for value in
            condition_pattern.findall(
                context
            )
        ]


        defects = [
            value.upper()
            for value in
            defect_pattern.findall(
                context
            )
        ]


        candidate_lines.append(
            {
                "page":
                    page_number,

                "line_number":
                    index + 1,

                "chainages":
                    "; ".join(
                        dict.fromkeys(
                            chainages
                        )
                    ),

                "bridge_types":
                    "; ".join(
                        dict.fromkeys(
                            bridge_types
                        )
                    ),

                "conditions":
                    "; ".join(
                        dict.fromkeys(
                            conditions
                        )
                    ),

                "defects":
                    "; ".join(
                        dict.fromkeys(
                            defects
                        )
                    ),

                "text":
                    context,
            }
        )


# ============================================================
# 5. TABLE HEADER / COLUMN DETECTION
# ============================================================

header_terms = [
    "SL NO",
    "CHAINAGE",
    "LOCATION",
    "TYPE",
    "SPAN",
    "WIDTH",
    "CONDITION",
    "REMARKS",
    "BRIDGE NO",
    "STRUCTURE",
]


headers = []


for page_number in range(
    start_page,
    end_page + 1,
):

    lines = [
        compact(line)
        for line in pages[
            page_number
        ].splitlines()
        if compact(line)
    ]


    for line in lines:

        upper = line.upper()

        found = [
            term
            for term in header_terms
            if term in upper
        ]

        if found:

            headers.append(
                {
                    "page":
                        page_number,

                    "matched_terms":
                        "; ".join(
                            found
                        ),

                    "text":
                        line,
                }
            )


# ============================================================
# 6. SURVEY DATE / REPORT DATE SEARCH
# ============================================================

date_context = []


date_patterns = [
    r"\b(?:JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER)\s+[0-9]{4}\b",
    r"\b[0-9]{1,2}[/-][0-9]{1,2}[/-][0-9]{2,4}\b",
    r"\b20[0-9]{2}\b",
]


for page_number in range(
    max(
        1,
        anchor - 5,
    ),
    min(
        len(reader.pages),
        anchor + 5,
    )
    + 1,
):

    lines = [
        compact(line)
        for line in pages[
            page_number
        ].splitlines()
        if compact(line)
    ]


    for line in lines:

        upper = line.upper()

        if (
            "SURVEY" not in upper
            and "INSPECTION" not in upper
            and "REPORT" not in upper
        ):
            continue


        dates = []

        for pattern in date_patterns:

            dates.extend(
                re.findall(
                    pattern,
                    line,
                    flags=re.IGNORECASE,
                )
            )


        if dates:

            date_context.append(
                {
                    "page":
                        page_number,

                    "dates":
                        "; ".join(
                            dict.fromkeys(
                                dates
                            )
                        ),

                    "text":
                        line,
                }
            )


# ============================================================
# 7. CLASSIFY WHETHER TABLE HAS CONDITION LABEL POTENTIAL
# ============================================================

condition_rows = [
    row
    for row in candidate_lines
    if row[
        "conditions"
    ]
]


defect_rows = [
    row
    for row in candidate_lines
    if row[
        "defects"
    ]
]


bridge_rows = [
    row
    for row in candidate_lines
    if (
        row[
            "bridge_types"
        ]
        or row[
            "chainages"
        ]
    )
]


condition_header = any(
    "CONDITION"
    in row[
        "matched_terms"
    ]
    for row in headers
)


if (
    condition_header
    and condition_rows
):
    evidence_status = (
        "POTENTIAL_BRIDGE_LEVEL_CONDITION_TABLE"
    )

elif defect_rows:
    evidence_status = (
        "POTENTIAL_DEFECT_EVIDENCE_TABLE"
    )

elif bridge_rows:
    evidence_status = (
        "BRIDGE_INVENTORY_ONLY_OR_CONDITION_NOT_EXPLICIT"
    )

else:
    evidence_status = (
        "TABLE_EXTRACTION_INCONCLUSIVE"
    )


# ============================================================
# 8. WRITE OUTPUT
# ============================================================

write_csv(
    OUT
    / "table_a5_candidate_rows.csv",
    candidate_lines,
)

write_csv(
    OUT
    / "table_a5_detected_headers.csv",
    headers,
)

write_csv(
    OUT
    / "survey_date_context.csv",
    date_context,
)


summary = {
    "version":
        "ml8h_table_a5_extract_v1",

    "table_anchor_page":
        anchor,

    "page_range":
        [
            start_page,
            end_page,
        ],

    "candidate_lines":
        len(
            candidate_lines
        ),

    "bridge_rows":
        len(
            bridge_rows
        ),

    "condition_rows":
        len(
            condition_rows
        ),

    "defect_rows":
        len(
            defect_rows
        ),

    "detected_headers":
        len(
            headers
        ),

    "condition_column_detected":
        condition_header,

    "date_context_rows":
        len(
            date_context
        ),

    "evidence_status":
        evidence_status,

    "training_labels_created":
        0,

    "database_modified":
        False,
}


(
    OUT
    / "ml8h_summary.json"
).write_text(
    json.dumps(
        summary,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    "================================================"
)

print(
    "ML-8H TABLE A-5 EXTRACTION SUMMARY"
)

print(
    "================================================"
)


print(
    "TABLE_ANCHOR_PAGE =",
    anchor,
)

print(
    "PAGE_RANGE =",
    f"{start_page}-{end_page}",
)

print(
    "CANDIDATE_LINES =",
    len(
        candidate_lines
    ),
)

print(
    "BRIDGE_ROWS =",
    len(
        bridge_rows
    ),
)

print(
    "CONDITION_ROWS =",
    len(
        condition_rows
    ),
)

print(
    "DEFECT_ROWS =",
    len(
        defect_rows
    ),
)

print(
    "CONDITION_COLUMN_DETECTED =",
    condition_header,
)

print(
    "SURVEY_DATE_CONTEXT_ROWS =",
    len(
        date_context
    ),
)

print(
    "EVIDENCE_STATUS =",
    evidence_status,
)


print()
print(
    "===== DETECTED TABLE HEADERS ====="
)

for row in headers[:30]:

    print(
        "PAGE",
        row[
            "page"
        ],
        "|",
        row[
            "matched_terms"
        ],
        "|",
        row[
            "text"
        ],
    )


print()
print(
    "===== POSSIBLE CONDITION ROWS ====="
)

for row in condition_rows[:30]:

    print(
        "PAGE",
        row[
            "page"
        ],
        "|",
        row[
            "chainages"
        ],
        "|",
        row[
            "conditions"
        ],
        "|",
        row[
            "text"
        ][:700],
    )


print()
print(
    "===== POSSIBLE DEFECT ROWS ====="
)

for row in defect_rows[:30]:

    print(
        "PAGE",
        row[
            "page"
        ],
        "|",
        row[
            "chainages"
        ],
        "|",
        row[
            "defects"
        ],
        "|",
        row[
            "text"
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
    "ML8H_TABLE_A5=PASS"
)