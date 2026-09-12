import csv
import json
import os
import re
from pathlib import Path

from pypdf import PdfReader


DOCS = Path(
    os.environ["ML8I_DOCS"]
)

OUT = Path(
    os.environ["ML8I_OUT"]
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


TARGET_FILES = [
    "NHAI_Tada_Nellore_NH5_Vol_II.pdf",
    "NHAI_Tada_Nellore_Project_Agreement_N0400715001AP.pdf",
]


def compact(value):
    return re.sub(
        r"\s+",
        " ",
        value or "",
    ).strip()


def write_csv(path, rows):

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


appendix_patterns = [
    r"APPENDIX\s*A\s*5[\.\- ]*4",
    r"APPENDIX\s*A5[\.\- ]*4",
]


bridge_row_patterns = [
    r"\bMAJOR\s+BRIDGE\b",
    r"\bMINOR\s+BRIDGE\b",
    r"\bBRIDGE\s+NO\.?\b",
    r"\bCHAINAGE\b",
    r"\bCONDITION\b",
    r"\bCRACK(?:ING|S)?\b",
    r"\bSPALLING\b",
    r"\bCORROSION\b",
]


results = []

documents = []


for filename in TARGET_FILES:

    path = DOCS / filename

    if not path.exists():

        documents.append(
            {
                "document":
                    filename,

                "exists":
                    False,

                "pages":
                    0,

                "appendix_reference_pages":
                    0,

                "possible_appendix_content_pages":
                    0,
            }
        )

        continue


    reader = PdfReader(
        str(path)
    )


    reference_pages = 0
    content_pages = 0


    for page_number, page in enumerate(
        reader.pages,
        start=1,
    ):

        try:
            raw = (
                page.extract_text()
                or ""
            )

        except Exception:
            raw = ""


        text = compact(
            raw
        )

        upper = text.upper()


        appendix_found = any(
            re.search(
                pattern,
                upper,
                flags=re.IGNORECASE,
            )
            for pattern
            in appendix_patterns
        )


        feasibility_found = (
            "FINAL FEASIBILITY REPORT"
            in upper
        )


        list_bridges_found = (
            "LIST OF BRIDGES"
            in upper
        )


        condition_survey_found = (
            "BRIDGE INVENTORY AND CONDITION SURVEY"
            in upper
            or
            "INVENTORY AND CONDITION SURVEY"
            in upper
        )


        bridge_signal_count = sum(
            1
            for pattern
            in bridge_row_patterns
            if re.search(
                pattern,
                upper,
                flags=re.IGNORECASE,
            )
        )


        if (
            appendix_found
            or (
                feasibility_found
                and condition_survey_found
            )
            or list_bridges_found
        ):

            reference_pages += 1


            # A genuine appendix page should normally
            # contain more than a simple narrative reference.
            likely_content = (
                appendix_found
                and bridge_signal_count >= 3
            )


            if likely_content:
                content_pages += 1


            results.append(
                {
                    "document":
                        filename,

                    "page":
                        page_number,

                    "appendix_a54_text":
                        appendix_found,

                    "final_feasibility_report":
                        feasibility_found,

                    "bridge_condition_survey":
                        condition_survey_found,

                    "list_of_bridges":
                        list_bridges_found,

                    "bridge_signal_count":
                        bridge_signal_count,

                    "likely_appendix_content":
                        likely_content,

                    "text_excerpt":
                        text[:1800],
                }
            )


    documents.append(
        {
            "document":
                filename,

            "exists":
                True,

            "pages":
                len(reader.pages),

            "appendix_reference_pages":
                reference_pages,

            "possible_appendix_content_pages":
                content_pages,
        }
    )


actual_content = [
    row
    for row in results
    if row[
        "likely_appendix_content"
    ]
]


if actual_content:

    overall_status = (
        "POSSIBLE_APPENDIX_A54_CONTENT_FOUND"
    )

else:

    overall_status = (
        "APPENDIX_A54_REFERENCED_BUT_NOT_PRESENT"
    )


write_csv(
    OUT
    / "appendix_a54_search_results.csv",
    results,
)


write_csv(
    OUT
    / "appendix_a54_document_summary.csv",
    documents,
)


summary = {
    "version":
        "ml8i_appendix_search_v1",

    "documents":
        documents,

    "reference_pages":
        len(results),

    "possible_appendix_content_pages":
        len(actual_content),

    "status":
        overall_status,

    "training_labels_created":
        0,

    "database_modified":
        False,
}


(
    OUT
    / "ml8i_summary.json"
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
    "ML-8I APPENDIX A5.4 SEARCH"
)

print(
    "================================================"
)


for document in documents:

    print()

    print(
        "DOCUMENT =",
        document[
            "document"
        ],
    )

    print(
        "PAGES =",
        document[
            "pages"
        ],
    )

    print(
        "REFERENCE_PAGES =",
        document[
            "appendix_reference_pages"
        ],
    )

    print(
        "POSSIBLE_APPENDIX_CONTENT_PAGES =",
        document[
            "possible_appendix_content_pages"
        ],
    )


print()
print(
    "===== APPENDIX REFERENCES ====="
)


for row in results[:30]:

    print()

    print(
        row[
            "document"
        ],
        "PAGE",
        row[
            "page"
        ],
    )

    print(
        "A5.4 =",
        row[
            "appendix_a54_text"
        ],
    )

    print(
        "SIGNALS =",
        row[
            "bridge_signal_count"
        ],
    )

    print(
        "CONTENT =",
        row[
            "likely_appendix_content"
        ],
    )

    print(
        "TEXT =",
        row[
            "text_excerpt"
        ][:900],
    )


print()
print(
    "STATUS =",
    overall_status,
)

print(
    "TRAINING_LABELS_CREATED = 0"
)

print(
    "DATABASE_MODIFIED = NO"
)

print(
    "ML8I_APPENDIX_SEARCH=PASS"
)