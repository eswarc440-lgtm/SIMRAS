import csv
import json
import re
from pathlib import Path
from datetime import datetime


ROOT = Path(
    "/app"
)

INCOMING = (
    ROOT
    / "data"
    / "bridge_inspections"
    / "official_sources"
    / "ml8j_mbui_acquisition"
    / "incoming_mbui"
)

OUT = (
    ROOT
    / "data"
    / "bridge_inspections"
    / "official_sources"
    / "ml8j_mbui_acquisition"
    / "ml8k_validation"
)

OUT.mkdir(
    parents=True,
    exist_ok=True,
)


SUPPORTED = {
    ".csv",
}


IDENTITY_FIELDS = {
    "asset_code",
    "official_bridge_id",
    "bridge_number",
    "chainage",
}


PROVENANCE_FIELDS = {
    "inspection_authority",
    "source_document",
}


CONDITION_FIELDS = {
    "overall_condition",
    "overall_rating_numeric",
    "condition_approach",
    "condition_signs",
    "condition_debris",
    "condition_joint",
    "condition_deck",
    "condition_rails",
    "condition_protection",
    "condition_stream",
    "condition_superstructure",
    "condition_piers",
    "condition_abutment",
    "cracking",
    "spalling",
    "corrosion",
    "scour",
    "settlement",
    "bearing_distress",
    "foundation_distress",
}


BAD_TEXT = re.compile(
    r"\b("
    r"SYNTHETIC|"
    r"DEMO|"
    r"DEMONSTRATION|"
    r"DUMMY|"
    r"MOCK|"
    r"FAKE|"
    r"TEST DATA|"
    r"SAMPLE DATA"
    r")\b",
    re.IGNORECASE,
)


def value(row, key):

    return (
        row.get(key)
        or ""
    ).strip()


def has_any(
    row,
    fields,
):

    return any(
        value(
            row,
            field,
        )
        for field in fields
    )


def valid_date(raw):

    raw = (
        raw
        or ""
    ).strip()

    if not raw:
        return False

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:

        try:
            datetime.strptime(
                raw,
                fmt,
            )

            return True

        except ValueError:
            pass

    return False


files = sorted(
    path
    for path in INCOMING.iterdir()
    if (
        path.is_file()
        and path.suffix.lower()
        in SUPPORTED
    )
)


print(
    "REAL_FILES_FOUND =",
    len(files),
)


all_rows = []

accepted = []

rejected = []


for file in files:

    print()
    print(
        "FILE =",
        file.name,
    )


    with file.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:

        reader = csv.DictReader(
            handle
        )

        for number, row in enumerate(
            reader,
            start=2,
        ):

            all_rows.append(
                row
            )

            reasons = []


            combined = " ".join(
                str(v or "")
                for v in row.values()
            )


            # ================================================
            # SYNTHETIC / DEMO CHECK
            # ================================================

            if BAD_TEXT.search(
                combined
            ):

                reasons.append(
                    "SYNTHETIC_OR_DEMO_MARKER"
                )


            # ================================================
            # BRIDGE IDENTITY
            # ================================================

            if not has_any(
                row,
                IDENTITY_FIELDS,
            ):

                reasons.append(
                    "NO_BRIDGE_IDENTITY"
                )


            # ================================================
            # DATE
            # ================================================

            inspection_date = value(
                row,
                "inspection_date",
            )


            if not valid_date(
                inspection_date
            ):

                reasons.append(
                    "NO_VALID_INSPECTION_DATE"
                )


            # ================================================
            # PROVENANCE
            # ================================================

            for required in PROVENANCE_FIELDS:

                if not value(
                    row,
                    required,
                ):

                    reasons.append(
                        "MISSING_"
                        + required.upper()
                    )


            # ================================================
            # CONDITION EVIDENCE
            # ================================================

            if not has_any(
                row,
                CONDITION_FIELDS,
            ):

                reasons.append(
                    "NO_CONDITION_EVIDENCE"
                )


            record = {
                "file":
                    file.name,

                "row_number":
                    number,

                "asset_code":
                    value(
                        row,
                        "asset_code",
                    ),

                "official_bridge_id":
                    value(
                        row,
                        "official_bridge_id",
                    ),

                "bridge_number":
                    value(
                        row,
                        "bridge_number",
                    ),

                "chainage":
                    value(
                        row,
                        "chainage",
                    ),

                "inspection_date":
                    inspection_date,

                "inspection_authority":
                    value(
                        row,
                        "inspection_authority",
                    ),

                "source_document":
                    value(
                        row,
                        "source_document",
                    ),

                "overall_condition":
                    value(
                        row,
                        "overall_condition",
                    ),

                "validation_status":
                    (
                        "CANDIDATE_REAL_EVIDENCE"
                        if not reasons
                        else "REJECTED"
                    ),

                "rejection_reasons":
                    "; ".join(
                        reasons
                    ),

                "database_written":
                    False,

                "verified_for_ml":
                    False,
            }


            if reasons:

                rejected.append(
                    record
                )

            else:

                accepted.append(
                    record
                )


# ============================================================
# WRITE AUDIT RESULTS
# ============================================================

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


    fields = list(
        rows[0].keys()
    )


    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
        )

        writer.writeheader()

        writer.writerows(
            rows
        )


write_csv(
    OUT
    / "accepted_real_evidence_candidates.csv",
    accepted,
)


write_csv(
    OUT
    / "rejected_inspection_rows.csv",
    rejected,
)


summary = {
    "version":
        "ml8k_real_inspection_gate_v1",

    "files_found":
        len(files),

    "rows_seen":
        len(all_rows),

    "candidate_real_rows":
        len(accepted),

    "rejected_rows":
        len(rejected),

    "rows_imported":
        0,

    "database_modified":
        False,

    "structural_model_unlocked":
        False,
}


(
    OUT
    / "ml8k_summary.json"
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
    "ML-8K REAL INSPECTION GATE"
)

print(
    "================================================"
)


print(
    "ROWS_SEEN =",
    len(all_rows),
)

print(
    "CANDIDATE_REAL_ROWS =",
    len(accepted),
)

print(
    "REJECTED_ROWS =",
    len(rejected),
)

print(
    "ROWS_IMPORTED = 0"
)

print(
    "DATABASE_MODIFIED = NO"
)


if accepted:

    print(
        "STRUCTURAL_MODEL_UNLOCKED = REVIEW_REQUIRED"
    )

else:

    print(
        "STRUCTURAL_MODEL_UNLOCKED = NO"
    )


print()
print(
    "ML8K_GATE=PASS"
)