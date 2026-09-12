from __future__ import annotations

import os
import re
import json
import asyncio
from pathlib import Path
from html.parser import HTMLParser
from datetime import datetime, timezone

import pandas as pd

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text


ROOT = Path("/app")

PLAN = (
    ROOT
    / "data"
    / "processed"
    / "airport"
    / "AP_AIRPORT_SOURCE_PLAN.csv"
)

MANIFEST = (
    ROOT
    / "reports"
    / "STEP4B_AAI_SOURCE_MANIFEST.csv"
)

RAW = (
    ROOT
    / "data"
    / "official"
    / "airport"
    / "eaip"
)

OUT_RUNWAYS = (
    ROOT
    / "data"
    / "processed"
    / "airport"
    / "AP_AIRPORT_RUNWAY_EVIDENCE.csv"
)

OUT_ASSETS = (
    ROOT
    / "data"
    / "processed"
    / "airport"
    / "AP_AIRPORT_ENGINEERING_FEATURES.csv"
)

DUPLICATES = (
    ROOT
    / "reports"
    / "STEP4B_AIRPORT_DUPLICATE_ASSETS.csv"
)

REPORT = (
    ROOT
    / "reports"
    / "STEP4B_AIRPORT_ENGINEERING_REPORT.txt"
)

REPORT_JSON = (
    ROOT
    / "reports"
    / "STEP4B_AIRPORT_ENGINEERING_REPORT.json"
)


class TableParser(HTMLParser):

    def __init__(self):
        super().__init__()

        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

        self.in_table = False
        self.in_row = False
        self.in_cell = False

        self.page_text = []

    def handle_starttag(self, tag, attrs):

        tag = tag.lower()

        if tag == "table":

            self.in_table = True
            self.table = []

        elif tag == "tr" and self.in_table:

            self.in_row = True
            self.row = []

        elif (
            tag in {"td", "th"}
            and self.in_table
            and self.in_row
        ):

            self.in_cell = True
            self.cell = []

    def handle_data(self, data):

        clean = re.sub(
            r"\s+",
            " ",
            str(data)
        ).strip()

        if clean:
            self.page_text.append(clean)

        if (
            self.in_cell
            and self.cell is not None
        ):
            self.cell.append(data)

    def handle_endtag(self, tag):

        tag = tag.lower()

        if (
            tag in {"td", "th"}
            and self.in_cell
        ):

            value = re.sub(
                r"\s+",
                " ",
                " ".join(
                    self.cell or []
                )
            ).strip()

            self.row.append(value)

            self.in_cell = False
            self.cell = None

        elif tag == "tr" and self.in_row:

            if self.row:
                self.table.append(
                    self.row
                )

            self.in_row = False
            self.row = None

        elif tag == "table" and self.in_table:

            if self.table:
                self.tables.append(
                    self.table
                )

            self.in_table = False
            self.table = None


def dimension(value):

    if not value:
        return None, None

    m = re.search(
        r"(\d{3,4}(?:\.\d+)?)\s*[xX×]\s*(\d{2,3}(?:\.\d+)?)",
        str(value)
    )

    if not m:
        return None, None

    return (
        float(m.group(1)),
        float(m.group(2))
    )


def first_number(value):

    if not value:
        return None

    m = re.search(
        r"-?\d+(?:\.\d+)?",
        str(value)
    )

    if not m:
        return None

    try:
        return float(m.group())
    except Exception:
        return None


def parse_airport(path, icao):

    html = path.read_text(
        encoding="utf-8",
        errors="ignore"
    )

    parser = TableParser()
    parser.feed(html)

    page_text = " ".join(
        parser.page_text
    )

    airport_name = None

    name_match = re.search(
        rf"{re.escape(icao)}\s*-\s*([^|]+?AIRPORT[^|]*?)(?:AD\s*2\.2|$)",
        page_text,
        flags=re.I
    )

    if name_match:
        airport_name = re.sub(
            r"\s+",
            " ",
            name_match.group(1)
        ).strip()

    elevation_ft = None

    elev_match = re.search(
        r"Aerodrome elevation and reference temperature\s+"
        r"(\d+(?:\.\d+)?)\s*FT",
        page_text,
        flags=re.I
    )

    if elev_match:
        elevation_ft = float(
            elev_match.group(1)
        )

    arp_coordinates = None

    arp_match = re.search(
        r"Aerodrome reference point coordinates.*?"
        r"(\d{6}(?:\.\d+)?[NS])\s+"
        r"(\d{7}(?:\.\d+)?[EW])",
        page_text,
        flags=re.I
    )

    if arp_match:
        arp_coordinates = (
            arp_match.group(1)
            + " "
            + arp_match.group(2)
        )

    runway_rows = []

    runway_table_found = False

    for table in parser.tables:

        joined = " ".join(
            " ".join(row)
            for row in table
        ).lower()

        if (
            "dimensions of rwy" not in joined
            and
            "strength of pavement" not in joined
        ):
            continue

        runway_table_found = True

        for row in table:

            if len(row) < 4:
                continue

            designator_raw = str(
                row[0]
            ).strip()

            designator = re.sub(
                r"^\s*RWY\s*",
                "",
                designator_raw,
                flags=re.I
            ).strip()

            if not re.fullmatch(
                r"\d{1,2}[lrcLRC]?",
                designator
            ):
                continue

            dim_index = None

            for i, cell in enumerate(row):

                a, b = dimension(cell)

                if (
                    a is not None
                    and b is not None
                    and a >= 500
                    and b >= 15
                ):
                    dim_index = i
                    break

            if dim_index is None:
                continue

            length_m, width_m = dimension(
                row[dim_index]
            )

            strength_surface = (
                row[dim_index + 1]
                if len(row) > dim_index + 1
                else None
            )

            coords = (
                row[dim_index + 2]
                if len(row) > dim_index + 2
                else None
            )

            bearing = (
                row[1]
                if len(row) > 1
                else None
            )

            surface = None

            if strength_surface:

                for candidate in [
                    "Asphalt",
                    "Concrete",
                    "Concrete/Asphalt",
                    "Asphalt/Concrete",
                    "Bituminous"
                ]:

                    if candidate.lower() in strength_surface.lower():
                        surface = candidate
                        break

            pavement_strength = None

            if strength_surface:

                p = re.search(
                    r"(\d+(?:\.\d+)?/[FR]/[A-D]/[WXYZ]/[TUR])",
                    strength_surface,
                    flags=re.I
                )

                if p:
                    pavement_strength = p.group(1)

                else:

                    p = re.search(
                        r"(\d+(?:\.\d+)?/[FR]/[A-D]/[WXYZ]/[T])",
                        strength_surface,
                        flags=re.I
                    )

                    if p:
                        pavement_strength = p.group(1)

            runway_rows.append({
                "icao_code": icao,
                "runway_designator": designator.upper(),
                "true_bearing_raw": bearing,
                "runway_length_m": length_m,
                "runway_width_m": width_m,
                "pavement_strength_raw":
                    strength_surface,
                "pavement_strength_code":
                    pavement_strength,
                "surface": surface,
                "threshold_coordinates_raw":
                    coords,
            })

    # ------------------------------------------------------------
    # Supplementary runway safety / slope / strip extraction
    # ------------------------------------------------------------

    strip_dims = []

    resa_dims = []

    slopes = []

    for table in parser.tables:

        for row in table:

            row_text = " | ".join(
                row
            )

            if (
                "strip" in row_text.lower()
                or
                "runway end safety" in row_text.lower()
                or
                "slope" in row_text.lower()
            ):

                all_dims = re.findall(
                    r"\d{2,4}(?:\.\d+)?\s*[xX×]\s*"
                    r"\d{2,4}(?:\.\d+)?\s*M?",
                    row_text
                )

                if "strip" in row_text.lower():

                    strip_dims.extend(
                        all_dims
                    )

                if (
                    "runway end safety"
                    in row_text.lower()
                    or "resa" in row_text.lower()
                ):

                    resa_dims.extend(
                        all_dims
                    )

                slopes.extend(
                    re.findall(
                        r"-?\d+(?:\.\d+)?\s*%",
                        row_text
                    )
                )

    return {
        "icao_code": icao,
        "airport_name_from_eaip":
            airport_name,
        "aerodrome_elevation_ft":
            elevation_ft,
        "arp_coordinates_raw":
            arp_coordinates,
        "runway_table_found":
            runway_table_found,
        "runway_rows":
            runway_rows,
        "runway_strip_dimensions_raw":
            " ; ".join(
                dict.fromkeys(strip_dims)
            ) or None,
        "resa_dimensions_raw":
            " ; ".join(
                dict.fromkeys(resa_dims)
            ) or None,
        "runway_slopes_raw":
            " ; ".join(
                dict.fromkeys(slopes)
            ) or None,
    }


async def main():

    plan = pd.read_csv(
        PLAN,
        low_memory=False
    )

    manifest = pd.read_csv(
        MANIFEST,
        low_memory=False
    )

    # ------------------------------------------------------------
    # DUPLICATE ICAO AUDIT
    # ------------------------------------------------------------

    dup = (
        plan[
            plan["icao_code"].notna()
        ]
        .groupby(
            "icao_code",
            dropna=False
        )
        .filter(
            lambda x: len(x) > 1
        )
        .sort_values(
            [
                "icao_code",
                "asset_id"
            ]
        )
    )

    dup.to_csv(
        DUPLICATES,
        index=False
    )

    parsed = {}
    runway_records = []

    for _, source in manifest.iterrows():

        if (
            source.get("Status")
            != "AVAILABLE"
        ):
            continue

        icao = str(
            source["ICAO"]
        ).strip()

        path = (
            RAW
            / f"{icao}.eaip.html"
        )

        if not path.exists():
            continue

        info = parse_airport(
            path,
            icao
        )

        info["source_url"] = (
            source.get("URL")
        )

        info["source_version"] = (
            source.get("Version")
        )

        info["source_sha256"] = (
            source.get("SHA256")
        )

        parsed[icao] = info

        for runway in info[
            "runway_rows"
        ]:

            runway_records.append({
                **runway,

                "source_version":
                    info[
                        "source_version"
                    ],

                "source_url":
                    info[
                        "source_url"
                    ],

                "source_sha256":
                    info[
                        "source_sha256"
                    ],
            })

    runway_df = pd.DataFrame(
        runway_records
    )

    runway_df.to_csv(
        OUT_RUNWAYS,
        index=False
    )

    # ------------------------------------------------------------
    # ATTACH CANONICAL AAI EVIDENCE TO ALL SIMRAS ASSET ROWS
    # ------------------------------------------------------------

    asset_rows = []

    for _, asset in plan.iterrows():

        icao = str(
            asset.get(
                "icao_code"
            ) or ""
        ).strip()

        info = parsed.get(
            icao
        )

        corresponding = (
            runway_df[
                runway_df[
                    "icao_code"
                ] == icao
            ]
            if (
                not runway_df.empty
                and "icao_code"
                in runway_df.columns
            )
            else pd.DataFrame()
        )

        runway_length = None
        runway_width = None
        surface = None
        strength = None

        if not corresponding.empty:

            runway_length = pd.to_numeric(
                corresponding[
                    "runway_length_m"
                ],
                errors="coerce"
            ).max()

            runway_width = pd.to_numeric(
                corresponding[
                    "runway_width_m"
                ],
                errors="coerce"
            ).max()

            surfaces = (
                corresponding[
                    "surface"
                ]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            if surfaces:
                surface = " / ".join(
                    surfaces
                )

            strengths = (
                corresponding[
                    "pavement_strength_raw"
                ]
                .dropna()
                .astype(str)
                .unique()
                .tolist()
            )

            if strengths:
                strength = " ; ".join(
                    strengths
                )

        asset_rows.append({

            "asset_id":
                asset.get(
                    "asset_id"
                ),

            "asset_code":
                asset.get(
                    "asset_code"
                ),

            "asset_name":
                asset.get(
                    "asset_name"
                ),

            "icao_code":
                icao or None,

            "canonical_airport":
                asset.get(
                    "aai_canonical_name"
                ),

            "runway_length_m":
                runway_length,

            "runway_width_m":
                runway_width,

            "runway_surface":
                surface,

            "pavement_strength_raw":
                strength,

            "aerodrome_elevation_ft":
                (
                    info.get(
                        "aerodrome_elevation_ft"
                    )
                    if info
                    else None
                ),

            "arp_coordinates_raw":
                (
                    info.get(
                        "arp_coordinates_raw"
                    )
                    if info
                    else None
                ),

            "runway_strip_dimensions_raw":
                (
                    info.get(
                        "runway_strip_dimensions_raw"
                    )
                    if info
                    else None
                ),

            "resa_dimensions_raw":
                (
                    info.get(
                        "resa_dimensions_raw"
                    )
                    if info
                    else None
                ),

            "runway_slopes_raw":
                (
                    info.get(
                        "runway_slopes_raw"
                    )
                    if info
                    else None
                ),

            "runway_end_records":
                int(
                    len(
                        corresponding
                    )
                ),

            "evidence_available":
                bool(info),

            "source_authority":
                (
                    "Airports Authority of India"
                    if info
                    else None
                ),

            "source_system":
                (
                    "AIM India eAIP"
                    if info
                    else None
                ),

            "source_version":
                (
                    info.get(
                        "source_version"
                    )
                    if info
                    else None
                ),

            "source_url":
                (
                    info.get(
                        "source_url"
                    )
                    if info
                    else None
                ),

            "source_sha256":
                (
                    info.get(
                        "source_sha256"
                    )
                    if info
                    else None
                ),

            "feature_version":
                "ap_airport_engineering_v1",
        })

    assets_df = pd.DataFrame(
        asset_rows
    )

    assets_df.to_csv(
        OUT_ASSETS,
        index=False
    )

    # ------------------------------------------------------------
    # DATABASE
    # ------------------------------------------------------------

    db_url = (
        os.getenv(
            "DATABASE_URL"
        )
        or os.getenv(
            "SQLALCHEMY_DATABASE_URI"
        )
        or os.getenv(
            "POSTGRES_URL"
        )
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
                public.airport_engineering_evidence_normalized
                (
                    asset_id BIGINT PRIMARY KEY,

                    asset_code TEXT,
                    asset_name TEXT,

                    icao_code TEXT,
                    canonical_airport TEXT,

                    runway_length_m
                        DOUBLE PRECISION,

                    runway_width_m
                        DOUBLE PRECISION,

                    runway_surface TEXT,

                    pavement_strength_raw TEXT,

                    aerodrome_elevation_ft
                        DOUBLE PRECISION,

                    arp_coordinates_raw TEXT,

                    runway_strip_dimensions_raw
                        TEXT,

                    resa_dimensions_raw TEXT,

                    runway_slopes_raw TEXT,

                    runway_end_records INTEGER,

                    evidence_available BOOLEAN,

                    source_authority TEXT,

                    source_system TEXT,

                    source_version TEXT,

                    source_url TEXT,

                    source_sha256 TEXT,

                    feature_version TEXT,

                    updated_at TIMESTAMPTZ
                        DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.airport_engineering_evidence_normalized
            """)
        )

        insert = text("""
            INSERT INTO
            public.airport_engineering_evidence_normalized
            (
                asset_id,
                asset_code,
                asset_name,
                icao_code,
                canonical_airport,
                runway_length_m,
                runway_width_m,
                runway_surface,
                pavement_strength_raw,
                aerodrome_elevation_ft,
                arp_coordinates_raw,
                runway_strip_dimensions_raw,
                resa_dimensions_raw,
                runway_slopes_raw,
                runway_end_records,
                evidence_available,
                source_authority,
                source_system,
                source_version,
                source_url,
                source_sha256,
                feature_version
            )
            VALUES
            (
                :asset_id,
                :asset_code,
                :asset_name,
                :icao_code,
                :canonical_airport,
                :runway_length_m,
                :runway_width_m,
                :runway_surface,
                :pavement_strength_raw,
                :aerodrome_elevation_ft,
                :arp_coordinates_raw,
                :runway_strip_dimensions_raw,
                :resa_dimensions_raw,
                :runway_slopes_raw,
                :runway_end_records,
                :evidence_available,
                :source_authority,
                :source_system,
                :source_version,
                :source_url,
                :source_sha256,
                :feature_version
            )
        """)

        for record in asset_rows:

            cleaned = {}

            for key, value in record.items():

                if pd.isna(value):
                    value = None

                if hasattr(
                    value,
                    "item"
                ):
                    value = value.item()

                cleaned[key] = value

            await conn.execute(
                insert,
                cleaned
            )

        await conn.execute(
            text("""
                CREATE TABLE IF NOT EXISTS
                public.airport_runway_evidence
                (
                    id BIGSERIAL PRIMARY KEY,

                    icao_code TEXT,

                    runway_designator TEXT,

                    true_bearing_raw TEXT,

                    runway_length_m
                        DOUBLE PRECISION,

                    runway_width_m
                        DOUBLE PRECISION,

                    pavement_strength_raw TEXT,

                    pavement_strength_code TEXT,

                    surface TEXT,

                    threshold_coordinates_raw
                        TEXT,

                    source_version TEXT,

                    source_url TEXT,

                    source_sha256 TEXT,

                    created_at TIMESTAMPTZ
                        DEFAULT NOW()
                )
            """)
        )

        await conn.execute(
            text("""
                TRUNCATE TABLE
                public.airport_runway_evidence
                RESTART IDENTITY
            """)
        )

        runway_insert = text("""
            INSERT INTO
            public.airport_runway_evidence
            (
                icao_code,
                runway_designator,
                true_bearing_raw,
                runway_length_m,
                runway_width_m,
                pavement_strength_raw,
                pavement_strength_code,
                surface,
                threshold_coordinates_raw,
                source_version,
                source_url,
                source_sha256
            )
            VALUES
            (
                :icao_code,
                :runway_designator,
                :true_bearing_raw,
                :runway_length_m,
                :runway_width_m,
                :pavement_strength_raw,
                :pavement_strength_code,
                :surface,
                :threshold_coordinates_raw,
                :source_version,
                :source_url,
                :source_sha256
            )
        """)

        for record in runway_records:

            cleaned = {}

            for key, value in record.items():

                if pd.isna(value):
                    value = None

                if hasattr(
                    value,
                    "item"
                ):
                    value = value.item()

                cleaned[key] = value

            await conn.execute(
                runway_insert,
                cleaned
            )

    # ------------------------------------------------------------
    # REPORT
    # ------------------------------------------------------------

    unique_icao = int(
        plan[
            "icao_code"
        ].dropna().nunique()
    )

    downloaded = len(
        parsed
    )

    evidence_asset_rows = int(
        assets_df[
            "evidence_available"
        ].sum()
    )

    runway_dimension_assets = int(
        assets_df[
            "runway_length_m"
        ].notna().sum()
    )

    pavement_assets = int(
        assets_df[
            "pavement_strength_raw"
        ].notna().sum()
    )

    duplicate_asset_rows = int(
        len(dup)
    )

    duplicate_icao = int(
        dup[
            "icao_code"
        ].nunique()
        if not dup.empty
        else 0
    )

    report = {
        "generated_at":
            datetime.now(
                timezone.utc
            ).isoformat(),

        "simras_airport_asset_rows":
            int(len(plan)),

        "unique_physical_airports":
            unique_icao,

        "aai_pages_downloaded":
            downloaded,

        "assets_with_aai_evidence":
            evidence_asset_rows,

        "assets_with_runway_dimensions":
            runway_dimension_assets,

        "assets_with_pavement_strength":
            pavement_assets,

        "runway_end_records":
            int(
                len(runway_df)
            ),

        "duplicate_asset_rows":
            duplicate_asset_rows,

        "duplicate_icao_codes":
            duplicate_icao,

        "feature_version":
            "ap_airport_engineering_v1",
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
        "SIMRAS STEP 4B - AIRPORT ENGINEERING RESULT",
        "=" * 100,
        "",
        f"SIMRAS airport asset rows       : {len(plan)}",
        f"Unique physical airports        : {unique_icao}",
        f"AAI eAIP pages downloaded       : {downloaded}",
        f"Assets with AAI evidence        : {evidence_asset_rows}",
        f"Assets with runway dimensions   : {runway_dimension_assets}",
        f"Assets with pavement strength   : {pavement_assets}",
        f"Runway-end records extracted    : {len(runway_df)}",
        "",
        f"Duplicate airport asset rows    : {duplicate_asset_rows}",
        f"ICAO codes with duplicates      : {duplicate_icao}",
        "",
        "Database tables:",
        " public.airport_engineering_evidence_normalized",
        " public.airport_runway_evidence",
        "",
        "Feature version:",
        " ap_airport_engineering_v1",
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

