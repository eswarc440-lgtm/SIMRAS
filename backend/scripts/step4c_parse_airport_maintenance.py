from __future__ import annotations

import os
import re
import json
import html
import asyncio
import hashlib
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine


ROOT = Path("/app")

RAW = (
    ROOT
    / "data"
    / "official"
    / "airport"
    / "maintenance"
    / "aai_tenders"
)

PLAN = (
    ROOT
    / "data"
    / "processed"
    / "airport"
    / "AP_AIRPORT_SOURCE_PLAN.csv"
)

OUT = (
    ROOT
    / "data"
    / "processed"
    / "airport"
    / "AP_AIRPORT_MAINTENANCE_EVIDENCE.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP4C_AIRPORT_MAINTENANCE_REPORT.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP4C_AIRPORT_MAINTENANCE_REPORT.json"
)


AIRPORTS = {
    "VOBZ": ["vijayawada", "gannavaram"],
    "VOCP": ["kadapa", "cuddapah"],
    "VOKU": ["kurnool", "orvakal", "orvakallu"],
    "VORY": ["rajahmundry", "rajamahendravaram"],
    "VOTP": ["tirupati", "renigunta"],
    "VOVZ": ["visakhapatnam", "vizag"],
}


HIGH_VALUE = [
    "resurfacing",
    "runway",
    "pavement",
    "rehabilitation",
    "strengthening",
    "rejuvenation",
    "repair of runway",
    "damaged runway",
]

MEDIUM_VALUE = [
    "apron",
    "taxiway",
    "operational area",
    "civil works",
    "repair",
    "maintenance",
    "a/r & m/o",
    "a/r and m/o",
    "marking painting",
    "joint sealing",
    "crack sealing",
]

LOW_VALUE = [
    "terminal building",
    "technical block",
    "building maintenance",
    "drainage",
    "fencing",
    "approach road",
]

EXCLUDE = [
    "retail",
    "advertisement",
    "restaurant",
    "food",
    "medical",
    "manpower",
    "housekeeping",
    "security contract",
    "parking license",
    "shop",
    "sweets",
    "apparel",
    "vehicle insurance",
]


def strip_html(raw: str) -> str:

    raw = re.sub(
        r"(?is)<script.*?</script>",
        " ",
        raw
    )

    raw = re.sub(
        r"(?is)<style.*?</style>",
        " ",
        raw
    )

    raw = re.sub(
        r"(?i)<br\s*/?>",
        "\n",
        raw
    )

    raw = re.sub(
        r"(?i)</(?:p|div|li|h1|h2|h3|h4|tr)>",
        "\n",
        raw
    )

    raw = re.sub(
        r"(?s)<[^>]+>",
        " ",
        raw
    )

    raw = html.unescape(raw)

    raw = raw.replace("\xa0", " ")

    lines = []

    for line in raw.splitlines():

        line = re.sub(
            r"\s+",
            " ",
            line
        ).strip()

        if line:
            lines.append(line)

    return "\n".join(lines)


def classify(text_value: str):

    t = text_value.lower()

    if any(x in t for x in EXCLUDE):
        return None, None

    if any(x in t for x in HIGH_VALUE):

        if (
            "damaged runway" in t
            or "resurfacing" in t
            or "rehabilitation" in t
            or "rejuvenation" in t
            or "strengthening" in t
        ):
            return "RUNWAY_REHABILITATION", "HIGH"

        return "RUNWAY_OPERATIONAL_MAINTENANCE", "HIGH"

    if any(x in t for x in MEDIUM_VALUE):

        if (
            "apron" in t
            or "taxiway" in t
            or "operational area" in t
        ):
            return "AIRFIELD_MAINTENANCE", "MEDIUM"

        return "CIVIL_MAINTENANCE", "MEDIUM"

    if any(x in t for x in LOW_VALUE):
        return "FACILITY_MAINTENANCE", "LOW"

    return None, None


def extract_cost(block):

    patterns = [
        r"Estimated Costs?\s*:\s*INR\s*([0-9,.]+)",
        r"Minimum Support Price\s*:\s*INR\s*([0-9,.]+)",
        r"Value Of Tender.*?([0-9][0-9,.]+)",
    ]

    for pattern in patterns:

        m = re.search(
            pattern,
            block,
            flags=re.I
        )

        if m:

            try:
                return float(
                    m.group(1)
                    .replace(",", "")
                )
            except Exception:
                pass

    return None


def extract_date(block):

    m = re.search(
        r"Last Sale Date\s*:\s*"
        r"(\d{1,2}-[A-Za-z]{3}-\d{4})",
        block,
        flags=re.I
    )

    if m:
        return m.group(1)

    m = re.search(
        r"Upload Date\s*:\s*"
        r"(\d{1,2}-[A-Za-z]{3}-\d{4})",
        block,
        flags=re.I
    )

    if m:
        return m.group(1)

    return None


def extract_bid(block):

    m = re.search(
        r"E-Bid No\s*:\s*([^\n]+)",
        block,
        flags=re.I
    )

    if not m:
        return None

    value = m.group(1).strip()

    # Stop accidental metadata capture.
    value = re.split(
        r"\s+(?:Status|Description|Download)",
        value,
        maxsplit=1,
        flags=re.I
    )[0].strip()

    return value[:120]


def derive_title(block, airport):

    lines = [
        x.strip()
        for x in block.splitlines()
        if x.strip()
    ]

    metadata_tokens = [
        "region / airport",
        "last sale date",
        "department",
        "tender type",
        "tender is",
        "estimated cost",
        "minimum support",
        "bid type",
        "e-bid",
        "status",
        "description",
        "download",
        "corrigendum",
        "important dates",
        "awarded",
    ]

    candidates = []

    for line in lines:

        lc = line.lower()

        if any(
            token in lc
            for token in metadata_tokens
        ):
            continue

        if len(line) < 20:
            continue

        if (
            airport.lower() in lc
            or any(x in lc for x in HIGH_VALUE)
            or any(x in lc for x in MEDIUM_VALUE)
        ):
            candidates.append(line)

    if candidates:

        # Prefer work-like descriptive sentence.
        candidates.sort(
            key=lambda x: (
                int(
                    any(k in x.lower()
                        for k in HIGH_VALUE + MEDIUM_VALUE)
                ),
                len(x)
            ),
            reverse=True
        )

        return candidates[0][:1000]

    return None


def blocks_for_airport(text_value, airport_names):

    lines = text_value.splitlines()

    indexes = []

    for i, line in enumerate(lines):

        lc = line.lower()

        if any(
            name in lc
            for name in airport_names
        ):

            indexes.append(i)

    blocks = []

    for idx in indexes:

        start = max(
            0,
            idx - 12
        )

        end = min(
            len(lines),
            idx + 20
        )

        block = "\n".join(
            lines[start:end]
        )

        blocks.append(block)

    return blocks


async def main():

    plan = pd.read_csv(
        PLAN,
        low_memory=False
    )

    records = []

    for icao, aliases in AIRPORTS.items():

        folder = RAW / icao

        if not folder.exists():
            continue

        aliases = [
            x.lower()
            for x in aliases
        ]

        for file in sorted(
            folder.glob("*.html")
        ):

            raw = file.read_text(
                encoding="utf-8",
                errors="ignore"
            )

            plain = strip_html(raw)

            source_sha = hashlib.sha256(
                file.read_bytes()
            ).hexdigest()

            for block in blocks_for_airport(
                plain,
                aliases
            ):

                category, severity = classify(
                    block
                )

                if not category:
                    continue

                canonical = (
                    plan.loc[
                        plan["icao_code"] == icao,
                        "aai_canonical_name"
                    ]
                    .dropna()
                    .astype(str)
                    .iloc[0]
                    if (
                        "icao_code" in plan
                        and
                        (
                            plan["icao_code"]
                            == icao
                        ).any()
                    )
                    else icao
                )

                title = derive_title(
                    block,
                    canonical.replace(
                        " Airport",
                        ""
                    )
                )

                if not title:

                    title = derive_title(
                        block,
                        aliases[0]
                    )

                if not title:
                    continue

                page_match = re.search(
                    r"search_page_(\d+)",
                    file.name
                )

                page_no = (
                    int(page_match.group(1))
                    if page_match
                    else None
                )

                records.append({
                    "icao_code":
                        icao,

                    "canonical_airport":
                        canonical,

                    "event_title":
                        title,

                    "evidence_category":
                        category,

                    "maintenance_significance":
                        severity,

                    "event_date_raw":
                        extract_date(block),

                    "estimated_cost_inr":
                        extract_cost(block),

                    "e_bid_no":
                        extract_bid(block),

                    "source_authority":
                        "Airports Authority of India",

                    "source_system":
                        "AAI Tender Portal",

                    "source_page":
                        page_no,

                    "source_local_file":
                        str(file),

                    "source_sha256":
                        source_sha,

                    "evidence_status":
                        "OFFICIAL_AAI_PUBLIC_TENDER",

                    "is_structural_condition_label":
                        False,

                    "is_maintenance_evidence":
                        True,

                    "raw_context":
                        block[:5000],
                })

    df = pd.DataFrame(
        records
    )

    if not df.empty:

        # Dedupe repeated blocks/pages.
        df["dedupe"] = (
            df["icao_code"]
            .fillna("")
            .astype(str)
            + "|"
            + df["event_title"]
            .fillna("")
            .astype(str)
            .str.lower()
            .str.replace(
                r"\s+",
                " ",
                regex=True
            )
        )

        df = (
            df.sort_values(
                [
                    "icao_code",
                    "maintenance_significance"
                ],
                ascending=[
                    True,
                    True
                ]
            )
            .drop_duplicates(
                "dedupe",
                keep="first"
            )
            .drop(
                columns=["dedupe"]
            )
        )

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_csv(
        OUT,
        index=False
    )

    # ----------------------------------------------------------
    # DATABASE
    # ----------------------------------------------------------

    db_url = (
        os.getenv("DATABASE_URL")
        or
        os.getenv(
            "SQLALCHEMY_DATABASE_URI"
        )
        or
        os.getenv("POSTGRES_URL")
    )

    if not db_url:
        raise RuntimeError(
            "DATABASE_URL unavailable"
        )

    if db_url.startswith(
        "postgresql://"
    ):

        db_url = db_url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1
        )

    engine = create_async_engine(
        db_url,
        pool_pre_ping=True
    )

    async with engine.begin() as conn:

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.airport_maintenance_evidence
                (
                    id BIGSERIAL PRIMARY KEY,

                    icao_code TEXT,
                    canonical_airport TEXT,

                    event_title TEXT NOT NULL,

                    evidence_category TEXT,
                    maintenance_significance TEXT,

                    event_date_raw TEXT,

                    estimated_cost_inr
                        DOUBLE PRECISION,

                    e_bid_no TEXT,

                    source_authority TEXT,
                    source_system TEXT,
                    source_local_file TEXT,
                    source_sha256 TEXT,

                    evidence_status TEXT,

                    is_structural_condition_label
                        BOOLEAN DEFAULT FALSE,

                    is_maintenance_evidence
                        BOOLEAN DEFAULT TRUE,

                    raw_context TEXT,

                    created_at TIMESTAMPTZ
                        DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.airport_maintenance_evidence
                RESTART IDENTITY
            """)
        )

        if not df.empty:

            insert = text("""
                INSERT INTO
                public.airport_maintenance_evidence
                (
                    icao_code,
                    canonical_airport,
                    event_title,
                    evidence_category,
                    maintenance_significance,
                    event_date_raw,
                    estimated_cost_inr,
                    e_bid_no,
                    source_authority,
                    source_system,
                    source_local_file,
                    source_sha256,
                    evidence_status,
                    is_structural_condition_label,
                    is_maintenance_evidence,
                    raw_context
                )
                VALUES
                (
                    :icao_code,
                    :canonical_airport,
                    :event_title,
                    :evidence_category,
                    :maintenance_significance,
                    :event_date_raw,
                    :estimated_cost_inr,
                    :e_bid_no,
                    :source_authority,
                    :source_system,
                    :source_local_file,
                    :source_sha256,
                    :evidence_status,
                    :is_structural_condition_label,
                    :is_maintenance_evidence,
                    :raw_context
                )
            """)

            for record in df.to_dict(
                orient="records"
            ):

                clean = {}

                for key, value in record.items():

                    if pd.isna(value):
                        value = None

                    if hasattr(
                        value,
                        "item"
                    ):
                        value = value.item()

                    clean[key] = value

                await conn.execute(
                    insert,
                    clean
                )

    # ----------------------------------------------------------
    # REPORT
    # ----------------------------------------------------------

    counts = {}

    if not df.empty:

        for icao in AIRPORTS:

            counts[icao] = int(
                (
                    df["icao_code"]
                    == icao
                ).sum()
            )

    else:

        counts = {
            x: 0
            for x in AIRPORTS
        }

    high = int(
        (
            df[
                "maintenance_significance"
            ]
            == "HIGH"
        ).sum()
        if not df.empty
        else 0
    )

    medium = int(
        (
            df[
                "maintenance_significance"
            ]
            == "MEDIUM"
        ).sum()
        if not df.empty
        else 0
    )

    airports_with_events = sum(
        1
        for x in counts.values()
        if x > 0
    )

    report = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "unique_airports":
            len(AIRPORTS),

        "airports_with_maintenance_evidence":
            airports_with_events,

        "maintenance_events":
            int(len(df)),

        "high_significance_events":
            high,

        "medium_significance_events":
            medium,

        "events_by_airport":
            counts,

        "database_table":
            "airport_maintenance_evidence",

        "important_limitation":
            (
                "Tender/maintenance evidence is not a "
                "pavement condition index or structural inspection label."
            ),
    }

    REPORT_JSON.write_text(
        json.dumps(
            report,
            indent=2
        ),
        encoding="utf-8"
    )

    lines = [
        "=" * 100,
        "SIMRAS STEP 4C - AIRPORT MAINTENANCE RESULT",
        "=" * 100,
        "",
        f"Unique AP airports                 : {len(AIRPORTS)}",
        f"Airports with maintenance evidence : {airports_with_events}",
        f"Maintenance events extracted       : {len(df)}",
        f"High-significance events            : {high}",
        f"Medium-significance events          : {medium}",
        "",
    ]

    for icao in sorted(counts):

        lines.append(
            f"{icao:<6}: {counts[icao]} events"
        )

    lines += [
        "",
        "Database table:",
        " public.airport_maintenance_evidence",
        "",
        "IMPORTANT:",
        "Maintenance/tender evidence may support maintenance age and",
        "rehabilitation history, but is NOT itself a PCI or structural",
        "inspection ground-truth label.",
        "=" * 100,
    ]

    print(
        "\n".join(lines)
    )

    REPORT.write_text(
        "\n".join(lines),
        encoding="utf-8"
    )

    await engine.dispose()


asyncio.run(main())
