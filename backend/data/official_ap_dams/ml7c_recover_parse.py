import csv
import json
import math
import re
from pathlib import Path

import pdfplumber


WORK = Path("/work")
PDF = WORK / "cwc_nrld_2019.pdf"
OUT = WORK / "cwc_nrld_2019_ap_166.csv"

PIC_RE = re.compile(r"^AP\d{2}[A-Z]{2}\d{4}$", re.I)


def clean(value):
    if value is None:
        return ""
    value = str(value).replace("\n", " ")
    return re.sub(r"\s+", " ", value).strip()


def numeric(value):
    value = clean(value)

    if not value or value.upper() in {"-", "NA", "N/A"}:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value.replace(",", ""),
    )

    if not match:
        return None

    try:
        result = float(match.group(0))
        return result if math.isfinite(result) else None
    except Exception:
        return None


def integer(value):
    value = numeric(value)
    return int(round(value)) if value is not None else None


def coordinate(value):
    value = clean(value)

    nums = re.findall(r"\d+(?:\.\d+)?", value)

    if not nums:
        return None

    deg = float(nums[0])
    minute = float(nums[1]) if len(nums) > 1 else 0.0
    second = float(nums[2]) if len(nums) > 2 else 0.0

    result = deg + minute / 60.0 + second / 3600.0

    if "S" in value.upper() or "W" in value.upper():
        result *= -1

    return result


if not PDF.exists():
    raise RuntimeError("CWC NRLD 2019 PDF missing")


records = {}

settings_variants = [
    {
        "vertical_strategy": "lines",
        "horizontal_strategy": "lines",
        "snap_tolerance": 4,
        "join_tolerance": 4,
        "intersection_tolerance": 5,
    },
    {
        "vertical_strategy": "text",
        "horizontal_strategy": "text",
        "snap_tolerance": 4,
        "join_tolerance": 4,
        "intersection_tolerance": 5,
    },
]


print()
print("=" * 100)
print("PARSE CWC NRLD 2019 - ANDHRA PRADESH")
print("=" * 100)


with pdfplumber.open(PDF) as pdf:

    print("PDF pages:", len(pdf.pages))

    # Official AP section in this PDF is PDF pages P57-P63.
    for page_index in range(57, 64):

        page = pdf.pages[page_index]

        page_records_before = len(records)

        for settings in settings_variants:

            tables = page.extract_tables(settings) or []

            for table in tables:

                for raw in table:

                    if not raw:
                        continue

                    cells = [clean(x) for x in raw]

                    pic_index = None

                    for index, cell in enumerate(cells):

                        candidate = re.sub(
                            r"\s+",
                            "",
                            cell,
                        ).upper()

                        if PIC_RE.fullmatch(candidate):
                            pic_index = index
                            break

                    if pic_index is None:
                        continue

                    values = cells[pic_index:]

                    # PIC + 18 official fields
                    if len(values) < 19:
                        continue

                    pic = re.sub(
                        r"\s+",
                        "",
                        values[0],
                    ).upper()

                    gross_m3 = numeric(values[14])
                    effective_m3 = numeric(values[16])

                    row = {
                        "pic": pic,
                        "name": clean(values[1]),
                        "operator": clean(values[2]),

                        "latitude_text": clean(values[3]),
                        "longitude_text": clean(values[4]),

                        "latitude": coordinate(values[3]),
                        "longitude": coordinate(values[4]),

                        "completion_year": integer(values[5]),

                        "river_basin": clean(values[6]),
                        "river": clean(values[7]),
                        "nearest_city": clean(values[8]),
                        "seismic_zone": clean(values[9]),
                        "dam_type": clean(values[10]),

                        "height_m": numeric(values[11]),
                        "length_m": numeric(values[12]),
                        "dam_volume_m3": numeric(values[13]),

                        "gross_storage_mcm": (
                            gross_m3 / 1_000_000.0
                            if gross_m3 is not None
                            else None
                        ),

                        "reservoir_area_m2": numeric(values[15]),

                        "effective_storage_mcm": (
                            effective_m3 / 1_000_000.0
                            if effective_m3 is not None
                            else None
                        ),

                        "purpose": clean(values[17]),

                        "spillway_capacity_cumecs":
                            numeric(values[18]),

                        "source_authority":
                            "Government of India / Central Water Commission",

                        "source_document":
                            "National Register of Large Dams 2019",

                        "source_url":
                            "https://www.cwc.gov.in/sites/default/files/nrld-2019.pdf",

                        "evidence_class":
                            "GOVERNMENT_FACT",
                    }

                    records[pic] = row

            if len(records) > page_records_before:
                break

        print(
            "PDF page",
            page_index,
            "cumulative AP rows:",
            len(records),
        )


rows = sorted(
    records.values(),
    key=lambda row: row["pic"],
)


print()
print("Parsed AP records:", len(rows))


if len(rows) != 166:
    raise RuntimeError(
        "Expected exactly 166 AP CWC rows; extracted "
        + str(len(rows))
        + ". Database write blocked."
    )


prakasam = next(
    (
        row
        for row in rows
        if row["pic"] == "AP01MH0009"
    ),
    None,
)


if not prakasam:
    raise RuntimeError(
        "AP01MH0009 Prakasam Barrage missing"
    )


checks = {
    "name":
        "PRAKASAM" in prakasam["name"].upper(),

    "river":
        "KRISHNA" in prakasam["river"].upper(),

    "completion_year":
        prakasam["completion_year"] == 1957,

    "height":
        prakasam["height_m"] is not None
        and abs(prakasam["height_m"] - 22.25) < 0.01,

    "length":
        prakasam["length_m"] is not None
        and abs(prakasam["length_m"] - 1233.0) < 0.1,

    "spillway":
        prakasam["spillway_capacity_cumecs"] is not None
        and abs(
            prakasam["spillway_capacity_cumecs"] - 33697.0
        ) < 1.0,
}


print()
print("Prakasam validation:")
print(json.dumps(checks, indent=2))


if not all(checks.values()):
    raise RuntimeError(
        "Prakasam anchor validation failed"
    )


fields = list(rows[0].keys())

with OUT.open(
    "w",
    encoding="utf-8",
    newline="",
) as handle:

    writer = csv.DictWriter(
        handle,
        fieldnames=fields,
    )

    writer.writeheader()
    writer.writerows(rows)


print()
print("PRAKASAM")
print(json.dumps(prakasam, indent=2))

print()
print("CWC_166_PARSE=PASS")