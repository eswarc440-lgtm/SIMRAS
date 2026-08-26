from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


REQUIRED_FIELDS = {"asset_code", "name", "asset_type", "longitude", "latitude"}
ALLOWED_TYPES = {"bridge", "dam", "barrage"}
AP_BOUNDS = (76.5, 12.5, 85.2, 20.0)


@dataclass(slots=True)
class ValidationIssue:
    row_number: int
    field: str
    message: str


@dataclass(slots=True)
class ValidationReport:
    rows: int
    accepted: int
    rejected: int
    issues: list[ValidationIssue]


def validate_csv(path: str | Path) -> ValidationReport:
    issues: list[ValidationIssue] = []
    seen_codes: set[str] = set()
    rows = 0
    accepted = 0
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_FIELDS - set(reader.fieldnames or [])
        if missing:
            return ValidationReport(
                rows=0,
                accepted=0,
                rejected=0,
                issues=[ValidationIssue(1, field, "required column is missing") for field in missing],
            )

        for row_number, record in enumerate(reader, start=2):
            rows += 1
            row_issues = 0
            code = record["asset_code"].strip()
            if not code:
                issues.append(ValidationIssue(row_number, "asset_code", "value is empty"))
                row_issues += 1
            elif code in seen_codes:
                issues.append(ValidationIssue(row_number, "asset_code", "duplicate canonical code"))
                row_issues += 1
            seen_codes.add(code)

            asset_type = record["asset_type"].strip().lower()
            if asset_type not in ALLOWED_TYPES:
                issues.append(
                    ValidationIssue(row_number, "asset_type", f"must be one of {sorted(ALLOWED_TYPES)}")
                )
                row_issues += 1

            try:
                longitude = float(record["longitude"])
                latitude = float(record["latitude"])
                min_lon, min_lat, max_lon, max_lat = AP_BOUNDS
                if not (min_lon <= longitude <= max_lon and min_lat <= latitude <= max_lat):
                    issues.append(
                        ValidationIssue(row_number, "geometry", "coordinate is outside AP validation bounds")
                    )
                    row_issues += 1
            except ValueError:
                issues.append(ValidationIssue(row_number, "geometry", "invalid longitude/latitude"))
                row_issues += 1

            if row_issues == 0:
                accepted += 1

    return ValidationReport(
        rows=rows,
        accepted=accepted,
        rejected=rows - accepted,
        issues=issues,
    )

