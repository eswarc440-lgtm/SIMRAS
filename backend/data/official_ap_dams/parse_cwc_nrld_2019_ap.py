import csv
import json
import math
import re
from pathlib import Path

import pdfplumber


WORK = Path("/work")

PDF = WORK / "cwc_nrld_2019.pdf"
CSV_PATH = WORK / "cwc_nrld_2019_ap_166.csv"
AUDIT_PATH = WORK / "cwc_nrld_2019_ap_audit.json"

SOURCE_URL = (
    "https://www.cwc.gov.in/"
    "sites/default/files/nrld-2019.pdf"
)

PIC_RE = re.compile(
    r"^AP\d{2}[A-Z]{2}\d{4}$",
    re.I,
)


def clean(value):

    if value is None:
        return ""

    value = str(value)

    value = value.replace(
        "\n",
        " ",
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value.strip()


def number(value):

    value = clean(value)

    if not value:
        return None

    if value.upper() in {
        "-",
        "NA",
        "N/A",
        "NULL",
        "NONE",
    }:
        return None

    value = value.replace(
        ",",
        "",
    )

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value,
    )

    if not match:
        return None

    try:

        result = float(
            match.group(0)
        )

        if math.isfinite(result):
            return result

    except Exception:
        pass

    return None


def integer(value):

    value = number(value)

    if value is None:
        return None

    return int(
        round(value)
    )


def dms_decimal(value):

    value = clean(value)

    if not value:
        return None

    numbers = re.findall(
        r"\d+(?:\.\d+)?",
        value,
    )

    if not numbers:
        return None

    degree = float(numbers[0])

    minute = (
        float(numbers[1])
        if len(numbers) >= 2
        else 0.0
    )

    second = (
        float(numbers[2])
        if len(numbers) >= 3
        else 0.0
    )

    result = (
        degree
        + minute / 60.0
        + second / 3600.0
    )

    upper = value.upper()

    if (
        "S" in upper
        or "W" in upper
    ):
        result = -result

    return result


if not PDF.exists():

    raise RuntimeError(
        "CWC NRLD 2019 PDF missing."
    )


records = {}


# Official Andhra Pradesh section:
# printed pages 42-48
# PDF indexes 57-63.
PAGE_INDEXES = range(
    57,
    64,
)


table_settings = {
    "vertical_strategy":
        "lines",

    "horizontal_strategy":
        "lines",

    "snap_tolerance":
        3,

    "join_tolerance":
        3,

    "intersection_tolerance":
        5,

    "text_tolerance":
        3,
}


print()
print("=" * 100)
print("PARSE CWC NRLD 2019 - ANDHRA PRADESH")
print("=" * 100)


with pdfplumber.open(PDF) as pdf:

    print(
        "PDF pages:",
        len(pdf.pages),
    )

    for page_index in PAGE_INDEXES:

        if page_index >= len(pdf.pages):
            continue

        page = pdf.pages[
            page_index
        ]

        tables = page.extract_tables(
            table_settings
        ) or []

        print(
            "PDF page",
            page_index + 1,
            "tables:",
            len(tables),
        )


        for table in tables:

            for raw_row in table:

                if not raw_row:
                    continue

                cells = [
                    clean(cell)
                    for cell in raw_row
                ]

                pic_index = None

                for index, cell in enumerate(cells):

                    candidate = re.sub(
                        r"\s+",
                        "",
                        cell,
                    ).upper()

                    if PIC_RE.fullmatch(
                        candidate
                    ):

                        pic_index = index
                        break


                if pic_index is None:
                    continue


                remaining = cells[
                    pic_index:
                ]


                # Columns beginning at PIC:
                #
                # 0 PIC
                # 1 Name
                # 2 Operator
                # 3 Latitude
                # 4 Longitude
                # 5 Completion year
                # 6 Basin
                # 7 River
                # 8 Nearest city
                # 9 Seismic zone
                # 10 Dam type
                # 11 Height
                # 12 Length
                # 13 Dam volume
                # 14 Gross storage
                # 15 Reservoir area
                # 16 Effective storage
                # 17 Purpose
                # 18 Designed spillway capacity

                if len(remaining) < 19:
                    continue


                pic = re.sub(
                    r"\s+",
                    "",
                    remaining[0],
                ).upper()


                gross_m3 = number(
                    remaining[14]
                )

                effective_m3 = number(
                    remaining[16]
                )


                record = {
                    "pic":
                        pic,

                    "name":
                        clean(
                            remaining[1]
                        ),

                    "operator":
                        clean(
                            remaining[2]
                        ),

                    "latitude_text":
                        clean(
                            remaining[3]
                        ),

                    "longitude_text":
                        clean(
                            remaining[4]
                        ),

                    "latitude":
                        dms_decimal(
                            remaining[3]
                        ),

                    "longitude":
                        dms_decimal(
                            remaining[4]
                        ),

                    "completion_year":
                        integer(
                            remaining[5]
                        ),

                    "river_basin":
                        clean(
                            remaining[6]
                        ),

                    "river":
                        clean(
                            remaining[7]
                        ),

                    "nearest_city":
                        clean(
                            remaining[8]
                        ),

                    "seismic_zone":
                        clean(
                            remaining[9]
                        ),

                    "dam_type":
                        clean(
                            remaining[10]
                        ),

                    "height_m":
                        number(
                            remaining[11]
                        ),

                    "length_m":
                        number(
                            remaining[12]
                        ),

                    "dam_volume_m3":
                        number(
                            remaining[13]
                        ),

                    "gross_storage_m3":
                        gross_m3,

                    "gross_storage_mcm":
                        (
                            gross_m3 / 1_000_000.0
                            if gross_m3 is not None
                            else None
                        ),

                    "reservoir_area_m2":
                        number(
                            remaining[15]
                        ),

                    "effective_storage_m3":
                        effective_m3,

                    "effective_storage_mcm":
                        (
                            effective_m3 / 1_000_000.0
                            if effective_m3 is not None
                            else None
                        ),

                    "purpose":
                        clean(
                            remaining[17]
                        ),

                    "spillway_capacity_cumecs":
                        number(
                            remaining[18]
                        ),

                    "source_page":
                        page_index + 1,

                    "source_authority":
                        (
                            "Government of India / "
                            "Central Water Commission"
                        ),

                    "source_document":
                        (
                            "National Register of "
                            "Large Dams 2019"
                        ),

                    "source_url":
                        SOURCE_URL,

                    "evidence_class":
                        "GOVERNMENT_FACT",
                }


                records[
                    pic
                ] = record


rows = sorted(
    records.values(),
    key=lambda item:
        item["pic"],
)


print()
print(
    "Parsed AP rows:",
    len(rows),
)


# The official AP section contains 166 rows.
if len(rows) != 166:

    print()
    print(
        "EXPECTED=166"
    )

    print(
        "ACTUAL=",
        len(rows),
    )

    raise RuntimeError(
        "CWC AP extraction must contain exactly 166 rows. "
        "Database loading is blocked."
    )


prakasam = [
    row
    for row in rows
    if row[
        "pic"
    ] == "AP01MH0009"
]


if len(prakasam) != 1:

    raise RuntimeError(
        "Prakasam Barrage AP01MH0009 not found exactly once."
    )


p = prakasam[0]


# Anchor validation prevents shifted-column parsing.
anchor_checks = {
    "name":
        "PRAKASAM" in p[
            "name"
        ].upper(),

    "river":
        "KRISHNA" in p[
            "river"
        ].upper(),

    "completion_year":
        p[
            "completion_year"
        ] == 1957,

    "height":
        (
            p[
                "height_m"
            ] is not None
            and abs(
                p[
                    "height_m"
                ] - 22.25
            ) < 0.01
        ),

    "length":
        (
            p[
                "length_m"
            ] is not None
            and abs(
                p[
                    "length_m"
                ] - 1233.0
            ) < 0.1
        ),

    "spillway":
        (
            p[
                "spillway_capacity_cumecs"
            ] is not None
            and abs(
                p[
                    "spillway_capacity_cumecs"
                ] - 33697.0
            ) < 1.0
        ),
}


if not all(
    anchor_checks.values()
):

    raise RuntimeError(
        "Prakasam anchor validation failed: "
        + json.dumps(
            anchor_checks
        )
    )


fields = list(
    rows[0].keys()
)


with CSV_PATH.open(
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


audit = {
    "rows":
        len(rows),

    "prakasam_anchor":
        anchor_checks,

    "field_coverage": {
        "river":
            sum(
                bool(row["river"])
                for row in rows
            ),

        "completion_year":
            sum(
                row[
                    "completion_year"
                ] is not None
                for row in rows
            ),

        "height_m":
            sum(
                row[
                    "height_m"
                ] is not None
                for row in rows
            ),

        "length_m":
            sum(
                row[
                    "length_m"
                ] is not None
                for row in rows
            ),

        "gross_storage_mcm":
            sum(
                row[
                    "gross_storage_mcm"
                ] is not None
                for row in rows
            ),

        "effective_storage_mcm":
            sum(
                row[
                    "effective_storage_mcm"
                ] is not None
                for row in rows
            ),

        "spillway_capacity_cumecs":
            sum(
                row[
                    "spillway_capacity_cumecs"
                ] is not None
                for row in rows
            ),
    },
}


AUDIT_PATH.write_text(
    json.dumps(
        audit,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print("=" * 100)
print("CWC PARSE AUDIT")
print("=" * 100)

print(
    json.dumps(
        audit,
        indent=2,
    )
)


print()
print("=" * 100)
print("PRAKASAM CWC ANCHOR")
print("=" * 100)

print(
    json.dumps(
        p,
        indent=2,
    )
)

print()
print(
    "CWC_PARSE_166=PASS"
)