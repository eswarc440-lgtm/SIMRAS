import csv
import json
import re
import urllib.request
from pathlib import Path

import pdfplumber


OUT = Path("/work")

PDF = OUT / "cwc_nrsd_2025.pdf"

CSV_PATH = OUT / "cwc_ap_register_2025.csv"

AUDIT_PATH = OUT / "cwc_ap_register_2025_audit.json"


URL = (
    "https://dharma.cwc.gov.in/dharma/public/"
    "uploads/front_upload_file/"
    "174860534186541140.pdf"
)


PIC_PATTERN = re.compile(
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

    value = clean(
        value
    )

    if not value:
        return None

    if value in {
        "-",
        "–",
        "—",
        "NA",
        "N/A",
    }:
        return None

    match = re.search(
        r"-?\d+(?:\.\d+)?",
        value.replace(
            ",",
            "",
        ),
    )

    if not match:
        return None

    try:
        return float(
            match.group(0)
        )
    except Exception:
        return None


def integer(value):

    value = number(
        value
    )

    if value is None:
        return None

    return int(
        round(value)
    )


print(
    "Downloading official CWC NRSD 2025..."
)


request = urllib.request.Request(
    URL,
    headers={
        "User-Agent":
            "SIMRAS-Research/1.0"
    },
)


with urllib.request.urlopen(
    request,
    timeout=120,
) as response:

    PDF.write_bytes(
        response.read()
    )


print(
    "Downloaded:",
    PDF,
)


rows = {}


with pdfplumber.open(
    PDF
) as pdf:

    print(
        "PDF pages:",
        len(pdf.pages),
    )

    for page_number, page in enumerate(
        pdf.pages,
        start=1,
    ):

        tables = page.extract_tables() or []

        for table in tables:

            for raw_row in table:

                if not raw_row:
                    continue

                cells = [
                    clean(
                        cell
                    )
                    for cell
                    in raw_row
                ]

                pic_index = None
                pic = None

                for index, cell in enumerate(
                    cells
                ):

                    candidate = re.sub(
                        r"\s+",
                        "",
                        cell,
                    ).upper()

                    if PIC_PATTERN.match(
                        candidate
                    ):

                        pic_index = index
                        pic = candidate
                        break

                if pic_index is None:
                    continue

                # CWC table layout beginning at PIC:
                #
                # PIC
                # Dam name
                # SDSO
                # Owner
                # Lat/Long
                # Completion year
                # River Basin
                # River
                # District
                # Dam Type
                # Height
                # Length
                # Gross Storage
                # Live Storage
                # Spillway Capacity
                # Purpose

                remaining = cells[
                    pic_index:
                ]

                if len(
                    remaining
                ) < 16:

                    continue

                record = {
                    "pic":
                        pic,

                    "name":
                        clean(
                            remaining[1]
                        ),

                    "sdso":
                        clean(
                            remaining[2]
                        ),

                    "owner":
                        clean(
                            remaining[3]
                        ),

                    "coordinates":
                        clean(
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

                    "district":
                        clean(
                            remaining[8]
                        ),

                    "dam_type":
                        clean(
                            remaining[9]
                        ),

                    "height_m":
                        number(
                            remaining[10]
                        ),

                    "length_m":
                        number(
                            remaining[11]
                        ),

                    "gross_storage_mcm":
                        number(
                            remaining[12]
                        ),

                    "live_storage_mcm":
                        number(
                            remaining[13]
                        ),

                    "spillway_capacity_cumecs":
                        number(
                            remaining[14]
                        ),

                    "purpose":
                        clean(
                            remaining[15]
                        ),

                    "source_page":
                        page_number,

                    "source_authority":
                        "Central Water Commission",

                    "source_document":
                        (
                            "National Register of "
                            "Specified Dams 2025"
                        ),

                    "source_url":
                        URL,

                    "evidence_class":
                        "GOVERNMENT_FACT",
                }


                # Basic sanity checks.
                year = record[
                    "completion_year"
                ]

                if (
                    year is not None
                    and not (
                        1400
                        <= year
                        <= 2035
                    )
                ):
                    record[
                        "completion_year"
                    ] = None


                height = record[
                    "height_m"
                ]

                if (
                    height is not None
                    and not (
                        0
                        < height
                        < 500
                    )
                ):
                    record[
                        "height_m"
                    ] = None


                length = record[
                    "length_m"
                ]

                if (
                    length is not None
                    and not (
                        0
                        < length
                        < 100000
                    )
                ):
                    record[
                        "length_m"
                    ] = None


                rows[
                    pic
                ] = record


records = list(
    rows.values()
)


records.sort(
    key=lambda row:
        row[
            "pic"
        ]
)


print()
print(
    "Parsed AP CWC rows:",
    len(records),
)


if len(records) < 100:

    raise RuntimeError(
        "CWC table extraction produced fewer than "
        "100 Andhra Pradesh rows. "
        "Database load is blocked."
    )


fields = [
    "pic",
    "name",
    "sdso",
    "owner",
    "coordinates",
    "completion_year",
    "river_basin",
    "river",
    "district",
    "dam_type",
    "height_m",
    "length_m",
    "gross_storage_mcm",
    "live_storage_mcm",
    "spillway_capacity_cumecs",
    "purpose",
    "source_page",
    "source_authority",
    "source_document",
    "source_url",
    "evidence_class",
]


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
        records
    )


audit = {
    "source":
        URL,

    "parsed_ap_rows":
        len(records),

    "with_year":
        sum(
            row[
                "completion_year"
            ] is not None
            for row
            in records
        ),

    "with_river":
        sum(
            bool(
                row[
                    "river"
                ]
            )
            for row
            in records
        ),

    "with_height":
        sum(
            row[
                "height_m"
            ] is not None
            for row
            in records
        ),

    "with_length":
        sum(
            row[
                "length_m"
            ] is not None
            for row
            in records
        ),

    "with_gross_storage":
        sum(
            row[
                "gross_storage_mcm"
            ] is not None
            for row
            in records
        ),

    "with_live_storage":
        sum(
            row[
                "live_storage_mcm"
            ] is not None
            for row
            in records
        ),

    "with_spillway_capacity":
        sum(
            row[
                "spillway_capacity_cumecs"
            ] is not None
            for row
            in records
        ),
}


AUDIT_PATH.write_text(
    json.dumps(
        audit,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print(
    json.dumps(
        audit,
        indent=2,
    )
)

print()
print(
    "CWC_PARSE=PASS"
)